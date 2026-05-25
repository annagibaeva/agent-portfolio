from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date

from mcp_server.server import collect_source
from src.models import Change, Entry, Source


@dataclass
class CompetitorResult:
    name: str
    ok: bool
    seeded: bool = False
    changes: list[Change] = field(default_factory=list)
    error: str | None = None


def _to_entry(d: dict) -> Entry:
    return Entry(title=d["title"], body=d["body"],
                 entry_date=date.fromisoformat(d["entry_date"]),
                 url=d["url"], content_hash=d["content_hash"],
                 body_hash=d["body_hash"])


def collect_all(sources: list[Source], db, run_id: str,
                run_date: date) -> list[CompetitorResult]:
    """Fetch/diff/persist every source. Each source is failure-isolated."""
    results: list[CompetitorResult] = []
    for src in sources:
        try:
            known = db.known_hashes(src.name)
            raw = collect_source(
                feed_url=src.feed_url, html_url=src.html_url,
                css_hint=src.css_hint, known=known, run_date=run_date,
            )
        except Exception as exc:
            results.append(CompetitorResult(src.name, ok=False,
                                            error=f"{type(exc).__name__}: {exc}"))
            continue
        if not raw["ok"]:
            results.append(CompetitorResult(src.name, ok=False,
                                            error=raw.get("error")))
            continue

        cid = db.competitor_id(src.name)
        cold_start = len(known) == 0
        changes: list[Change] = []
        for item in raw["new"]:
            entry = _to_entry(item["entry"])
            db.insert_entry(cid, entry, run_id)
            if not cold_start:
                changes.append(Change(entry=entry, kind="new"))
        for item in raw["updated"]:
            entry = _to_entry(item["entry"])
            db.update_entry_body(cid, entry, run_id)
            changes.append(Change(entry=entry, kind="updated"))

        results.append(CompetitorResult(
            src.name, ok=True, seeded=cold_start, changes=changes))
    return results
