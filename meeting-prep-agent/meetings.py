"""Calendar fetch, skip filters, attendee normalization, slug helpers."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build
from slugify import slugify

from auth import get_credentials

SKIP_TITLE_RE = re.compile(r"\b(focus|lunch|block|ooo|hold)\b", re.IGNORECASE)

# Friendly TZ labels — %Z returns offsets (+08) for zones without DST abbrevs.
TZ_LABELS = {
    "Asia/Singapore": "SGT",
    "Asia/Hong_Kong": "HKT",
    "Asia/Tokyo": "JST",
    "Asia/Kolkata": "IST",
    "Asia/Dubai": "GST",
    "Australia/Sydney": "AEST",
    "Europe/London": "GMT",
    "Europe/Paris": "CET",
    "America/New_York": "ET",
    "America/Chicago": "CT",
    "America/Denver": "MT",
    "America/Los_Angeles": "PT",
}


@dataclass
class Meeting:
    id: str
    title: str
    start_iso: str
    start_local: str  # human-readable for the brief header
    is_all_day: bool
    join_link: str
    attendees: list[dict] = field(default_factory=list)
    response_status: str = "accepted"
    raw: dict = field(default_factory=dict)

    @property
    def slug(self) -> str:
        date = self.start_iso.split("T")[0]
        return f"{date}-{slugify(self.title, allow_unicode=False, max_length=60)}-{self.id[:8]}"


def _user_emails() -> set[str]:
    primary = os.environ.get("USER_EMAIL", "").strip().lower()
    aliases = os.environ.get("USER_EMAIL_ALIASES", "")
    out = {primary} if primary else set()
    out.update(a.strip().lower() for a in aliases.split(",") if a.strip())
    return out


def normalize_email(email: str) -> str:
    """Lowercase, strip +tag suffix."""
    email = (email or "").strip().lower()
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    local = local.split("+", 1)[0]
    return f"{local}@{domain}"


def is_external(email: str) -> bool:
    return normalize_email(email) not in _user_emails()


def _extract_join_link(event: dict) -> str:
    hangout = event.get("hangoutLink")
    if hangout:
        return hangout
    desc = event.get("description") or ""
    for pat in (r"https?://[^\s]*zoom\.us/j/[^\s<]+", r"https?://meet\.google\.com/[^\s<]+", r"https?://teams\.microsoft\.com/[^\s<]+"):
        m = re.search(pat, desc)
        if m:
            return m.group(0)
    location = event.get("location") or ""
    if location.startswith("http"):
        return location
    return "in-person"


def _to_meeting(event: dict, tz: ZoneInfo) -> Meeting:
    start = event.get("start", {})
    is_all_day = "date" in start and "dateTime" not in start
    if is_all_day:
        start_iso = start.get("date", "")
        start_local = start_iso  # YYYY-MM-DD only
    else:
        start_iso = start.get("dateTime", "")
        try:
            dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00")).astimezone(tz)
            label = TZ_LABELS.get(str(tz), dt.strftime("%Z") or str(tz))
            start_local = dt.strftime("%Y-%m-%d %H:%M ") + label
        except ValueError:
            start_local = start_iso

    user_emails = _user_emails()
    response = "accepted"
    for a in event.get("attendees", []):
        if normalize_email(a.get("email", "")) in user_emails:
            response = a.get("responseStatus", "accepted")
            break

    return Meeting(
        id=event["id"],
        title=event.get("summary", "(no title)"),
        start_iso=start_iso,
        start_local=start_local,
        is_all_day=is_all_day,
        join_link=_extract_join_link(event),
        attendees=event.get("attendees", []),
        response_status=response,
        raw=event,
    )


def _should_skip(m: Meeting) -> tuple[bool, str]:
    if m.response_status == "declined":
        return True, "declined"
    if len(m.attendees) < 2:
        return True, "solo"
    if SKIP_TITLE_RE.search(m.title or ""):
        return True, "skip-list title"
    if m.is_all_day and not m.attendees:
        return True, "all-day no attendees"
    return False, ""


def list_today(tz_name: str | None = None) -> list[Meeting]:
    tz = ZoneInfo(tz_name or os.environ.get("USER_TZ", "Asia/Singapore"))
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    creds = get_credentials()
    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
    events = (
        svc.events()
        .list(
            calendarId="primary",
            timeMin=start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            timeMax=end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    out = []
    for e in events.get("items", []):
        m = _to_meeting(e, tz)
        skip, _reason = _should_skip(m)
        if not skip:
            out.append(m)
    return out


def find_by_query(query: str, tz_name: str | None = None) -> Meeting | None:
    """Substring match on title or attendee email, today + next 7 days."""
    tz = ZoneInfo(tz_name or os.environ.get("USER_TZ", "Asia/Singapore"))
    now = datetime.now(tz)
    end = now + timedelta(days=7)

    creds = get_credentials()
    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
    events = (
        svc.events()
        .list(
            calendarId="primary",
            timeMin=now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            timeMax=end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            singleEvents=True,
            orderBy="startTime",
            q=query,
        )
        .execute()
    )

    needle = query.lower()
    for e in events.get("items", []):
        title = (e.get("summary") or "").lower()
        if needle in title:
            return _to_meeting(e, tz)
        for a in e.get("attendees", []):
            if needle in (a.get("email") or "").lower():
                return _to_meeting(e, tz)
    return None
