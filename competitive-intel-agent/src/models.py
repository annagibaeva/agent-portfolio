from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Source:
    name: str
    feed_url: str | None
    html_url: str
    css_hint: str | None


@dataclass(frozen=True)
class Entry:
    title: str
    body: str
    entry_date: date
    url: str
    content_hash: str
    body_hash: str


@dataclass(frozen=True)
class Change:
    entry: Entry
    kind: str  # "new" | "updated"


@dataclass(frozen=True)
class DiffResult:
    new: list[Change]
    updated: list[Change]
