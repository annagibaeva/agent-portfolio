from __future__ import annotations
import json
from pathlib import Path

from src.models import Change

_MODEL = "claude-sonnet-4-6"
_TAGS = {"Threat", "Parity gap", "Table stakes", "Noise"}
_PROMPT = Path(__file__).parent.parent / "prompts" / "commentary.md"
_MAX_CHANGES = 60

_TOOL = {
    "name": "submit_commentary",
    "description": "Submit per-change tags and the weekly synthesis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "changes": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "so_what": {"type": "string"},
                    "tag": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["index", "so_what", "tag", "confidence"],
            }},
            "synthesis": {"type": "object"},
        },
        "required": ["changes", "synthesis"],
    },
}


class CommentaryError(RuntimeError):
    """Raised when model output fails validation."""


def validate_commentary(payload: dict, n_changes: int) -> dict:
    changes = payload.get("changes", [])
    if len(changes) != n_changes:
        raise CommentaryError(
            f"change count mismatch: got {len(changes)}, expected {n_changes}")
    for c in changes:
        if c.get("tag") not in _TAGS:
            raise CommentaryError(f"invalid tag: {c.get('tag')}")
        conf = c.get("confidence")
        if not isinstance(conf, (int, float)) or not 0.0 <= conf <= 1.0:
            raise CommentaryError(f"confidence out of range: {conf}")
    if "synthesis" not in payload:
        raise CommentaryError("missing synthesis")
    return payload


def _format_changes(changes: list[Change]) -> str:
    lines = []
    for i, c in enumerate(changes):
        lines.append(f"[{i}] ({c.kind}) {c.entry.title} — {c.entry.body[:300]}")
    return "\n".join(lines)


def generate_commentary(api_key: str, changes: list[Change],
                        prior_watchlist: list[str]) -> tuple[dict, int]:
    """Return (validated_payload, tokens_used). Raises CommentaryError on bad output."""
    from anthropic import Anthropic  # lazy import
    if len(changes) > _MAX_CHANGES:
        changes = changes[:_MAX_CHANGES]
    client = Anthropic(api_key=api_key)
    user = (f"Previous watchlist: {prior_watchlist or 'none'}\n\n"
            f"This week's changes:\n{_format_changes(changes)}")
    resp = client.messages.create(
        model=_MODEL, max_tokens=4000,
        system=_PROMPT.read_text(),
        tools=[_TOOL], tool_choice={"type": "tool", "name": "submit_commentary"},
        messages=[{"role": "user", "content": user}],
    )
    tokens = resp.usage.input_tokens + resp.usage.output_tokens
    tool_use = next((b for b in resp.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise CommentaryError("model returned no tool_use block")
    payload = tool_use.input if isinstance(tool_use.input, dict) else \
        json.loads(tool_use.input)
    return validate_commentary(payload, n_changes=len(changes)), tokens
