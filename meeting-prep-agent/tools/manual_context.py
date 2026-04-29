"""Manual LinkedIn paste tool: ./context/linkedin-<localpart>.md"""
from __future__ import annotations

import json
from pathlib import Path

from claude_agent_sdk import tool, create_sdk_mcp_server

CONTEXT_DIR = Path(__file__).parent.parent / "context"


def _result(status: str, data=None, error: str | None = None):
    payload = {"status": status, "data": data, "error": error}
    return {"content": [{"type": "text", "text": json.dumps(payload, default=str)}]}


@tool(
    "read",
    "Read manually-pasted LinkedIn context for an attendee. "
    "Pass the email local-part (before @). Returns file content or empty.",
    {"localpart": str},
)
async def read(args):
    try:
        localpart = (args.get("localpart") or "").strip().lower()
        if not localpart:
            return _result("empty", data="")
        path = CONTEXT_DIR / f"linkedin-{localpart}.md"
        if not path.exists():
            return _result("empty", data="")
        return _result("ok", data=path.read_text(encoding="utf-8"))
    except Exception as e:
        return _result("error", error=str(e))


manual_context_server = create_sdk_mcp_server(
    name="manual_context",
    version="1.0.0",
    tools=[read],
)
