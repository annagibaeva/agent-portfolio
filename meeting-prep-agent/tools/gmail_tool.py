"""Gmail @tool wrapper: search recent threads with an attendee, with quoted-text stripping."""
from __future__ import annotations

import base64
import json
import os
import re

from claude_agent_sdk import tool, create_sdk_mcp_server
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import cache
from auth import get_credentials

MAX_THREADS = 5
QUOTED_LINE_RE = re.compile(r"^\s*>", re.MULTILINE)
ON_WROTE_RE = re.compile(r"^On .+wrote:\s*$.*", re.MULTILINE | re.DOTALL)


def _result(status: str, data=None, error: str | None = None):
    payload = {"status": status, "data": data, "error": error}
    return {"content": [{"type": "text", "text": json.dumps(payload, default=str)}]}


def _strip_quoted(text: str) -> str:
    text = ON_WROTE_RE.sub("", text)
    text = "\n".join(line for line in text.splitlines() if not QUOTED_LINE_RE.match(line))
    return text.strip()


def _decode_part(part: dict) -> str:
    body = part.get("body", {})
    data = body.get("data")
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_text(payload: dict) -> str:
    if not payload:
        return ""
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        return _decode_part(payload)
    parts = payload.get("parts") or []
    chunks = []
    for p in parts:
        if p.get("mimeType") == "text/plain":
            chunks.append(_decode_part(p))
        elif p.get("parts"):
            chunks.append(_extract_text(p))
    return "\n".join(c for c in chunks if c)


@retry(
    retry=retry_if_exception_type(HttpError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _list_threads(svc, query: str):
    return svc.users().threads().list(userId="me", q=query, maxResults=MAX_THREADS).execute()


@retry(
    retry=retry_if_exception_type(HttpError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _get_thread(svc, tid: str):
    return svc.users().threads().get(userId="me", id=tid, format="full").execute()


def _search(attendee_email: str) -> list[dict]:
    cached = cache.get("gmail_threads", attendee_email)
    if cached is not None:
        return cached

    user_email = os.environ.get("USER_EMAIL", "")
    creds = get_credentials()
    svc = build("gmail", "v1", credentials=creds, cache_discovery=False)

    # Exclude self-sent prep emails to break the email-to-self loop
    query = f'(from:{attendee_email} OR to:{attendee_email}) -from:me -subject:"[prep]" newer_than:30d'
    listing = _list_threads(svc, query)
    threads = listing.get("threads", [])[:MAX_THREADS]

    out = []
    for t in threads:
        try:
            full = _get_thread(svc, t["id"])
        except HttpError:
            continue
        msgs = full.get("messages", [])
        if not msgs:
            continue
        first = msgs[0]
        last = msgs[-1]
        headers = {h["name"].lower(): h["value"] for h in first.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "(no subject)")
        date = headers.get("date", "")
        body = _extract_text(last.get("payload", {}))
        body = _strip_quoted(body)[:2000]  # cap tokens
        out.append({"thread_id": t["id"], "subject": subject, "date": date, "snippet": body})

    cache.set_("gmail_threads", attendee_email, out)
    return out


@tool(
    "search_threads",
    "Search Gmail for the top 5 recent threads (last 30d) involving an attendee. "
    "Excludes self-sent [prep] emails. Strips quoted history. Returns subject, date, snippet.",
    {"attendee_email": str},
)
async def search_threads(args):
    try:
        threads = _search(args["attendee_email"])
        if not threads:
            return _result("empty", data=[])
        return _result("ok", data=threads)
    except Exception as e:
        return _result("error", error=str(e))


gmail_server = create_sdk_mcp_server(
    name="gmail",
    version="1.0.0",
    tools=[search_threads],
)
