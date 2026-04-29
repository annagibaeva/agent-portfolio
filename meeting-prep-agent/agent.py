"""Agent SDK orchestration: one query() per meeting."""
from __future__ import annotations

import os
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock, ToolUseBlock, ResultMessage

import logger
from meetings import Meeting, is_external, normalize_email
from tools.calendar_tool import calendar_server
from tools.gmail_tool import gmail_server
from tools.manual_context import manual_context_server
from tools.brief_tools import briefs_server

PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"


def _system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _user_message(m: Meeting) -> str:
    user_email = os.environ.get("USER_EMAIL", "")
    aliases = os.environ.get("USER_EMAIL_ALIASES", "")
    external = [
        normalize_email(a.get("email", ""))
        for a in m.attendees
        if a.get("email") and is_external(a["email"])
    ]
    return f"""Prepare a brief for this meeting.

- event_id: {m.id}
- title: {m.title}
- when: {m.start_local}   # USE THIS VERBATIM in the brief title. Do not recompute from calendar.get_event.
- join_link: {m.join_link} # USE THIS VERBATIM for the Join: line.
- user_email: {user_email}
- user_aliases: {aliases or "(none)"}
- external_attendees: {external or "(none)"}
- filename: {m.slug}

Steps:
1. Call calendar.get_event with event_id={m.id} to fetch attendee details and description. Do not use its start/end times — they're in the raw event timezone.
2. For each external attendee email above, call gmail.search_threads and manual_context.read (with the local-part).
3. Compose the markdown brief per the system prompt template. Title MUST be: "# {m.title} — {m.start_local}".
4. Call briefs.save_brief with the markdown and filename "{m.slug}".
5. Call briefs.send_email with the returned path.
"""


async def run_for_meeting(m: Meeting, run_id: str) -> dict:
    """Run the agent loop for one meeting. Returns a result dict for logging."""
    options = ClaudeAgentOptions(
        system_prompt=_system_prompt(),
        model="claude-sonnet-4-6",
        max_turns=12,
        mcp_servers={
            "calendar": calendar_server,
            "gmail": gmail_server,
            "manual_context": manual_context_server,
            "briefs": briefs_server,
        },
        allowed_tools=[
            "mcp__calendar__get_event",
            "mcp__gmail__search_threads",
            "mcp__manual_context__read",
            "mcp__briefs__save_brief",
            "mcp__briefs__send_email",
        ],
    )

    tool_calls: list[str] = []
    last_text = ""
    got_result = False
    error: str | None = None

    try:
        async for msg in query(prompt=_user_message(m), options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        tool_calls.append(block.name)
                    elif isinstance(block, TextBlock):
                        last_text = block.text
            elif isinstance(msg, ResultMessage):
                got_result = True
    except Exception as e:
        # Known issue: the SDK subprocess sometimes exits 1 on shutdown after a
        # successful run. Only treat as error if we never received a ResultMessage.
        if not got_result:
            error = str(e)

    # Sanity: a successful run must have called save_brief at minimum.
    if not error and "mcp__briefs__save_brief" not in tool_calls:
        error = f"agent did not call save_brief. last_text: {last_text[:200]}"

    result = {
        "meeting_id": m.id,
        "title": m.title,
        "tool_calls": tool_calls,
        "status": "error" if error else "ok",
        "error": error,
        "last_text": last_text[:500],
    }
    logger.log(run_id, **result)
    return result
