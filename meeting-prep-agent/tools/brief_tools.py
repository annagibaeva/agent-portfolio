"""Save brief to disk + send email-to-self via Gmail API."""
from __future__ import annotations

import base64
import json
import os
import re
from email.message import EmailMessage
from pathlib import Path

from claude_agent_sdk import tool, create_sdk_mcp_server
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from auth import get_credentials

BRIEFS_DIR = Path(__file__).parent.parent / "briefs"


def _result(status: str, data=None, error: str | None = None):
    payload = {"status": status, "data": data, "error": error}
    return {"content": [{"type": "text", "text": json.dumps(payload, default=str)}]}


def _extract_title_and_time(markdown: str) -> tuple[str, str]:
    """Pull the H1 title and inline time fragment for the email subject."""
    m = re.search(r"^# (.+)$", markdown, re.MULTILINE)
    if not m:
        return "(meeting)", ""
    full = m.group(1).strip()
    if " — " in full:
        title, time_part = full.split(" — ", 1)
        return title.strip(), time_part.strip()
    return full, ""


@tool(
    "save_brief",
    "Save the final brief markdown to ./briefs/<filename>.md. "
    "Pass `markdown` (the full brief) and `filename` (without extension). "
    "Returns the file path.",
    {"markdown": str, "filename": str},
)
async def save_brief(args):
    try:
        BRIEFS_DIR.mkdir(exist_ok=True)
        filename = args["filename"]
        if not filename.endswith(".md"):
            filename += ".md"
        path = BRIEFS_DIR / filename
        path.write_text(args["markdown"], encoding="utf-8")
        return _result("ok", data={"path": str(path)})
    except Exception as e:
        return _result("error", error=str(e))


@retry(
    retry=retry_if_exception_type(HttpError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _send(svc, raw: str):
    return svc.users().messages().send(userId="me", body={"raw": raw}).execute()


@tool(
    "send_email",
    "Send the saved brief to the user's own inbox with subject '[prep] <title> — <time>'. "
    "Pass the file path returned by save_brief.",
    {"path": str},
)
async def send_email(args):
    try:
        path = Path(args["path"])
        if not path.exists():
            return _result("error", error=f"brief not found at {path}")
        markdown = path.read_text(encoding="utf-8")
        title, time_part = _extract_title_and_time(markdown)

        user_email = os.environ.get("USER_EMAIL", "")
        if not user_email:
            return _result("error", error="USER_EMAIL not set")

        msg = EmailMessage()
        msg["To"] = user_email
        msg["From"] = user_email
        msg["Subject"] = f"[prep] {title} — {time_part}".rstrip(" —")
        msg.set_content(markdown)

        creds = get_credentials()
        svc = build("gmail", "v1", credentials=creds, cache_discovery=False)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        sent = _send(svc, raw)
        return _result("ok", data={"message_id": sent.get("id")})
    except Exception as e:
        return _result("error", error=str(e))


briefs_server = create_sdk_mcp_server(
    name="briefs",
    version="1.0.0",
    tools=[save_brief, send_email],
)
