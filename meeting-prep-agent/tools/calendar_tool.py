"""Calendar @tool wrappers."""
from __future__ import annotations

import json

from claude_agent_sdk import tool, create_sdk_mcp_server
from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from googleapiclient.errors import HttpError

from auth import get_credentials


def _result(status: str, data=None, error: str | None = None):
    payload = {"status": status, "data": data, "error": error}
    return {"content": [{"type": "text", "text": json.dumps(payload, default=str)}]}


@retry(
    retry=retry_if_exception_type(HttpError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _fetch_event(event_id: str) -> dict:
    creds = get_credentials()
    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return svc.events().get(calendarId="primary", eventId=event_id).execute()


@tool(
    "get_event",
    "Fetch full Google Calendar event details (attendees, description, link) for a given event id.",
    {"event_id": str},
)
async def get_event(args):
    try:
        event = _fetch_event(args["event_id"])
        return _result(
            "ok",
            data={
                "id": event.get("id"),
                "title": event.get("summary"),
                "description": event.get("description"),
                "location": event.get("location"),
                "hangout_link": event.get("hangoutLink"),
                "start": event.get("start"),
                "end": event.get("end"),
                "attendees": event.get("attendees", []),
                "organizer": event.get("organizer", {}),
            },
        )
    except Exception as e:
        return _result("error", error=str(e))


calendar_server = create_sdk_mcp_server(
    name="calendar",
    version="1.0.0",
    tools=[get_event],
)
