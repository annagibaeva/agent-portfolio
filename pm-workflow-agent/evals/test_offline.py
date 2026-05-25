"""Offline evals: mock agent.run_intake / run_draft and exercise main.run().

These run on every pytest invocation. They verify pipeline behavior
(intake parsing, low-confidence detection, budget enforcement, atomic
write) without calling the live model. Prompt-quality regressions are
caught by run_live.py instead.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

import agent
import intake
import main
from evals.cases import CASES, EvalCase

OUT_DIR = Path(__file__).parent.parent / "outputs"


def _intake_text(case: EvalCase) -> str:
    """Mock an intake turn: ask one question per missing checklist item.

    For 'rejected' cases, return the reject envelope from intake.md.
    """
    if case.expected == "rejected":
        return '```json\n{"reject": "input is not a product idea", "questions": []}\n```'
    missing = [item for item in intake.COVERAGE_CHECKLIST if item["id"] not in case.answers]
    questions = [
        {"id": f"q{i}", "checklist_item": item["id"], "text": f"What is {item['prompt']}?"}
        for i, item in enumerate(missing, 1)
    ]
    return "```json\n" + json.dumps({"questions": questions}) + "\n```"


def _draft_text(case: EvalCase, qa: list[tuple[str, str]]) -> str:
    """Mock a draft turn: emit a PRD with LOW CONFIDENCE for each 'guess' answer."""
    sections = []
    by_item = {item["id"]: item["prompt"] for item in intake.COVERAGE_CHECKLIST}
    answered_by_item = {}
    for q, a in qa:
        for item_id, prompt in by_item.items():
            if prompt in q:
                answered_by_item[item_id] = a

    for item in intake.COVERAGE_CHECKLIST:
        body = answered_by_item.get(item["id"]) or case.answers.get(item["id"], "guess")
        marker = " [LOW CONFIDENCE]" if body == "guess" else ""
        sections.append(f"## {item['id'].title()}\n{body}{marker}")
    prd = "# PRD: " + case.idea[:60] + "\n\n" + "\n\n".join(sections)
    return "```markdown\n" + prd + "\n```"


@pytest.fixture
def mocked_agent(monkeypatch):
    """Replace agent.run_intake / run_draft with deterministic stubs.

    Returns a closure (set_case) so each test selects which EvalCase
    drives the stub. Usage in main.run() is unchanged.
    """
    state: dict = {"case": None, "draft_usage": {"input_tokens": 100}}

    async def fake_intake(idea: str):
        case = state["case"]
        return _intake_text(case), {"input_tokens": 50, "output_tokens": 50}

    async def fake_draft(idea: str, qa):
        case = state["case"]
        return _draft_text(case, qa), state["draft_usage"]

    monkeypatch.setattr(agent, "run_intake", fake_intake)
    monkeypatch.setattr(agent, "run_draft", fake_draft)

    def configure(case: EvalCase, draft_usage: dict | None = None):
        state["case"] = case
        if draft_usage is not None:
            state["draft_usage"] = draft_usage

    return configure


def _run_case(case: EvalCase) -> int:
    # Always pass a dict (even empty) so main.run skips interactive input
    # and the answer_for resolver fills missing keys with the 'guess' sentinel.
    return asyncio.run(main.run(case.idea, dict(case.answers)))


@pytest.mark.parametrize("case", [c for c in CASES if c.expected == "happy_path"], ids=lambda c: c.id)
def test_happy_path_writes_prd_with_no_low_confidence(mocked_agent, case, capsys):
    mocked_agent(case)
    rc = _run_case(case)
    assert rc == 0
    out = capsys.readouterr().out
    assert "LOW CONFIDENCE" not in out
    prd_path = sorted(OUT_DIR.glob("prd-*.md"), key=lambda p: p.stat().st_mtime)[-1]
    prd = prd_path.read_text(encoding="utf-8")
    for needle in case.must_contain:
        assert needle in prd, f"expected '{needle}' in PRD for {case.id}"


@pytest.mark.parametrize("case", [c for c in CASES if c.expected == "low_confidence"], ids=lambda c: c.id)
def test_low_confidence_cases_flag_min_sections(mocked_agent, case):
    mocked_agent(case)
    rc = _run_case(case)
    assert rc == 0
    prd_path = sorted(OUT_DIR.glob("prd-*.md"), key=lambda p: p.stat().st_mtime)[-1]
    flagged = agent.low_confidence_sections(prd_path.read_text(encoding="utf-8"))
    assert len(flagged) >= case.min_low_confidence, (
        f"expected >={case.min_low_confidence} low-confidence sections, got {len(flagged)}: {flagged}"
    )


def test_budget_exceeded_raises(mocked_agent):
    case = next(c for c in CASES if c.expected == "budget_exceeded")
    mocked_agent(case, draft_usage={"input_tokens": agent.TOKEN_CAP + 1})
    with pytest.raises(agent.BudgetError):
        _run_case(case)


def test_non_idea_is_rejected(mocked_agent):
    case = next(c for c in CASES if c.expected == "rejected")
    mocked_agent(case)
    before = set(OUT_DIR.glob("prd-*.md"))
    with pytest.raises(intake.RejectedIdeaError):
        _run_case(case)
    after = set(OUT_DIR.glob("prd-*.md"))
    assert after == before, "rejected idea must not write a PRD file"
