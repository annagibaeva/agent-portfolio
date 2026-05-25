"""One-command demo: python main.py --demo. No DB, no network."""
from __future__ import annotations
from datetime import date
from pathlib import Path

from src.collector import collect_all
from src.digest import render_digest
from src.models import Source

FIX = Path(__file__).parent / "tests" / "fixtures"


class InMemoryDB:
    def __init__(self):
        self._entries: dict[str, dict[str, str]] = {}

    def known_hashes(self, name):
        return self._entries.get(name, {})

    def competitor_id(self, name):
        return f"demo-{name}"

    def insert_entry(self, cid, entry, run_id):
        name = cid.replace("demo-", "")
        self._entries.setdefault(name, {})[entry.content_hash] = entry.body_hash
        return f"e-{entry.content_hash}"

    def update_entry_body(self, cid, entry, run_id):
        pass


def run_demo() -> int:
    import mcp_server.server as server
    feed = (FIX / "demo_feed.xml").read_text()
    server.fetch_url = lambda url, **k: feed

    db = InMemoryDB()
    sources = [Source("DemoCorp", "http://feed", "http://html", None)]

    collect_all(sources, db, run_id="demo-r1", run_date=date(2026, 5, 12))
    results = collect_all(sources, db, run_id="demo-r2", run_date=date(2026, 5, 19))

    commentary = {"changes": [], "synthesis": {
        "themes": ["Demo mode — commentary stubbed"],
        "watch_list": [], "suggested_response": "Run with real config.",
        "prior_watchlist_status": []}}
    md = render_digest(results, commentary, week="2026-W21",
                       failed=[], stale=[])
    print(md)
    return 0
