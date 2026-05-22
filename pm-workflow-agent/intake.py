"""Coverage checklist and strict-JSON parsing of clarifying questions."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

MAX_QUESTIONS = 6

COVERAGE_CHECKLIST = [
    {"id": "problem", "prompt": "the problem being solved and the evidence it is real"},
    {"id": "persona", "prompt": "the primary user / persona"},
    {"id": "metric", "prompt": "the top success metric and its target"},
    {"id": "dependencies", "prompt": "known dependencies (teams, vendors, prerequisites)"},
    {"id": "scope", "prompt": "scope and explicit non-goals"},
    {"id": "release", "prompt": "the target release / timeframe"},
]

_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class IntakeParseError(ValueError):
    """Raised when the intake turn output cannot be parsed as question JSON."""


@dataclass(frozen=True)
class Question:
    id: str
    checklist_item: str
    text: str


def parse_questions(text: str) -> list[Question]:
    """Extract the questions array from a fenced JSON block. Caps at MAX_QUESTIONS."""
    match = _FENCE.search(text)
    raw = match.group(1) if match else text
    try:
        data = json.loads(raw)
        items = data["questions"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise IntakeParseError(f"could not parse questions JSON: {exc}") from exc
    out: list[Question] = []
    for item in items[:MAX_QUESTIONS]:
        out.append(
            Question(
                id=str(item["id"]),
                checklist_item=str(item["checklist_item"]),
                text=str(item["text"]),
            )
        )
    return out
