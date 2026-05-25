"""PM Workflow Agent — CLI entry point."""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv

import agent
import intake
import logger

OUTPUT_DIR = Path(__file__).parent / "outputs"
DEMO_IDEA = (
    "A keyboard-shortcut palette for TaskFlow so power users can jump to any "
    "project, task, or view without the mouse."
)
DEMO_ANSWERS = {
    "problem": "Power users complain navigation is slow; 8 support asks last quarter.",
    "persona": "Engineering-led teams, daily heavy users.",
    "metric": "40% of weekly-active power users use the palette within 30 days.",
    "dependencies": "None — front-end only.",
    "scope": "In: navigation. Out: command execution, custom shortcuts.",
    "release": "v3.1 / Q3 2026.",
}


def prd_filename(idea_or_title: str, run_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", idea_or_title.lower()).strip("-")[:40].strip("-")
    return f"prd-{slug}-{run_id}.md"


def load_answers_file(path: Path) -> dict[str, str]:
    answers: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            answers[key.strip()] = val.strip()
    return answers


def answer_for(q: intake.Question, answers: dict[str, str]) -> str:
    """Resolve an answer from a pre-supplied dict; 'guess' if absent."""
    return answers.get(q.checklist_item, "guess")


def _collect_interactive(questions: list[intake.Question]) -> list[tuple[str, str]]:
    qa: list[tuple[str, str]] = []
    for q in questions:
        ans = input(f"  [{q.checklist_item}] {q.text}\n  > ").strip()
        qa.append((q.text, ans or "guess"))
    return qa


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


async def run(idea: str, answers: dict[str, str] | None) -> int:
    run_id = logger.new_run_id()
    usages: list[dict] = []
    print(f"Run {run_id}")

    intake_text, u = await agent.run_intake(idea)
    usages.append(u)
    try:
        questions = intake.parse_questions(intake_text)
    except intake.RejectedIdeaError as exc:
        logger.log(run_id, step="intake", status="rejected", reason=str(exc))
        raise
    logger.log(run_id, step="intake", questions=len(questions))

    if not questions:
        qa: list[tuple[str, str]] = []
    elif answers is not None:
        qa = [(q.text, answer_for(q, answers)) for q in questions]
    else:
        print(f"{len(questions)} clarifying question(s):")
        qa = _collect_interactive(questions)

    draft_text, u = await agent.run_draft(idea, qa)
    usages.append(u)
    tokens = agent.token_total(usages)
    if tokens > agent.TOKEN_CAP:
        logger.log(run_id, step="draft", status="budget_exceeded", tokens=tokens)
        raise agent.BudgetError(f"token cap exceeded: {tokens} > {agent.TOKEN_CAP}")

    prd = agent.extract_prd_block(draft_text)
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / prd_filename(idea, run_id)
    _atomic_write(out_path, prd + "\n")

    low = agent.low_confidence_sections(prd)
    if low:
        print("\n!! LOW CONFIDENCE — review these sections:")
        for s in low:
            print(f"   - {s}")

    logger.log(run_id, step="draft", status="ok", tokens=tokens, output=str(out_path))
    print(logger.trace_summary(run_id, turns=len(usages), tokens=tokens, outcome="ok"))
    print(f"\nPRD written to {out_path}")
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PM Workflow Agent")
    p.add_argument("--idea", type=str, help="Product idea text")
    p.add_argument("--idea-file", type=Path, help="File containing the product idea")
    p.add_argument("--answers-file", type=Path, help="Pre-supplied answers (non-interactive)")
    p.add_argument("--demo", action="store_true", help="Run with a bundled idea + answers")
    return p.parse_args()


def main() -> int:
    load_dotenv()
    args = _parse_args()
    try:
        agent.preflight()
    except agent.PreflightError as exc:
        print(f"Pre-flight failed: {exc}", file=sys.stderr)
        return 2

    if args.demo:
        idea, answers = DEMO_IDEA, DEMO_ANSWERS
    else:
        if args.idea_file:
            idea = args.idea_file.read_text(encoding="utf-8").strip()
        elif args.idea:
            idea = args.idea
        else:
            idea = input("Product idea: ").strip()
        answers = load_answers_file(args.answers_file) if args.answers_file else None

    if not idea:
        print("No idea provided.", file=sys.stderr)
        return 2

    try:
        return asyncio.run(run(idea, answers))
    except KeyboardInterrupt:
        print("\nInterrupted — no PRD written.", file=sys.stderr)
        return 130
    except intake.RejectedIdeaError as exc:
        print(f"Idea rejected: {exc}", file=sys.stderr)
        return 3
    except (agent.DraftError, agent.BudgetError, intake.IntakeParseError) as exc:
        print(f"Run failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
