"""Agent SDK orchestration: two stateless query() calls."""
from __future__ import annotations

import os
import re
from pathlib import Path

import intake

from claude_agent_sdk import (
    query, ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage,
)

MODEL = "claude-sonnet-4-6"
MAX_TURNS = 10
TOKEN_CAP = 100_000
SKILL_NAME = "prd-writer"
_PROMPTS = Path(__file__).parent / "prompts"
_MD_FENCE = re.compile(r"```markdown\s*(.*?)\s*```", re.DOTALL)


class PreflightError(RuntimeError):
    """Raised when the agent cannot start (missing key or skill)."""


class DraftError(RuntimeError):
    """Raised when the draft turn output has no PRD markdown block."""


class BudgetError(RuntimeError):
    """Raised when a run exceeds the token cap."""


def preflight() -> None:
    """Fail fast before any model call if config is wrong."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise PreflightError("ANTHROPIC_API_KEY is not set.")
    skill_dir = Path.home() / ".claude" / "skills" / SKILL_NAME / "SKILL.md"
    if not skill_dir.exists():
        raise PreflightError(f"prd-writer skill not found at {skill_dir}")


def _read(name: str) -> str:
    return (_PROMPTS / name).read_text(encoding="utf-8")


def extract_prd_block(text: str) -> str:
    """Return the contents of the single ```markdown fence, or raise DraftError."""
    match = _MD_FENCE.search(text)
    if not match:
        raise DraftError("draft turn returned no ```markdown block")
    return match.group(1).strip()


def low_confidence_sections(prd: str) -> list[str]:
    """Return section headings whose body contains the LOW CONFIDENCE marker."""
    out: list[str] = []
    current = ""
    for line in prd.splitlines():
        if line.startswith("## "):
            current = line.strip()
        elif "LOW CONFIDENCE" in line and current:
            out.append(current)
    return out


def token_total(usages: list[dict]) -> int:
    """Sum every integer token field across usage dicts."""
    keys = (
        "input_tokens", "output_tokens",
        "cache_read_input_tokens", "cache_creation_input_tokens",
    )
    return sum(int(u.get(k, 0)) for u in usages for k in keys)


def merge_usage(usages: list[dict]) -> dict:
    """Sum the token fields across usage dicts into one dict."""
    keys = (
        "input_tokens", "output_tokens",
        "cache_read_input_tokens", "cache_creation_input_tokens",
    )
    return {k: sum(int(u.get(k, 0)) for u in usages) for k in keys}


async def _run_validated(prompt, *, system, use_skill, validate):
    """Run a turn; if validate(text) raises, retry once. Merges usage of both.

    RejectedIdeaError is a model verdict, not a parse failure — re-raise
    immediately without burning a retry.
    """
    usages: list[dict] = []
    last_exc: Exception | None = None
    for _ in range(2):
        text, usage = await _run(prompt, system=system, use_skill=use_skill)
        usages.append(usage)
        try:
            validate(text)
            return text, merge_usage(usages)
        except intake.RejectedIdeaError:
            raise
        except Exception as exc:  # noqa: BLE001 - validator decides what's fatal
            last_exc = exc
    assert last_exc is not None
    raise last_exc


async def _run(prompt: str, *, system: str, use_skill: bool) -> tuple[str, dict]:
    """One stateless query(). Returns (joined assistant text, usage dict)."""
    opts = ClaudeAgentOptions(
        model=MODEL,
        max_turns=MAX_TURNS,
        system_prompt=system,
        skills=[SKILL_NAME] if use_skill else [],
    )
    text_parts: list[str] = []
    usage: dict = {}
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
        elif isinstance(msg, ResultMessage):
            usage = getattr(msg, "usage", {}) or {}
    return "\n".join(text_parts), usage


async def run_intake(idea: str) -> tuple[str, dict]:
    """Intake turn with one retry. Returns (text containing questions JSON, usage)."""
    return await _run_validated(
        f"Product idea:\n{idea}",
        system=_read("intake.md"),
        use_skill=False,
        validate=intake.parse_questions,
    )


async def run_draft(idea: str, qa: list[tuple[str, str]]) -> tuple[str, dict]:
    """Draft turn with one retry. Returns (text containing PRD markdown, usage)."""
    answered = "\n".join(f"- Q: {q}\n  A: {a}" for q, a in qa) or "(none)"
    prompt = (
        f"Product idea:\n{idea}\n\n"
        f"Clarifying answers:\n{answered}\n\n"
        "Draft the PRD now using the prd-writer skill."
    )
    return await _run_validated(
        prompt, system=_read("system.md"), use_skill=True, validate=extract_prd_block,
    )
