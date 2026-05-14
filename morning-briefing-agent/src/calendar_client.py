from datetime import date, datetime, timezone
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def build_service(creds: Credentials):
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def list_today_events(creds: Credentials | None = None, today: date | None = None) -> list[dict] | None:
    today = today or date.today()
    time_min = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=timezone.utc).isoformat()
    time_max = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc).isoformat()
    try:
        service = build_service(creds)
        result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = []
        for item in result.get("items", []):
            start = item.get("start", {})
            if "dateTime" in start:
                dt = datetime.fromisoformat(start["dateTime"])
                time_str = dt.strftime("%H:%M")
            else:
                time_str = "All day"
            attendees = [a["email"] for a in item.get("attendees", [])]
            events.append({
                "title": item.get("summary", "(No title)"),
                "time": time_str,
                "attendees": attendees,
            })
        return events
    except Exception:
        return None
