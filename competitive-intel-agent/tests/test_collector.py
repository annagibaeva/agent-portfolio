from __future__ import annotations
from datetime import date
from src.models import Source
from src.collector import collect_all, CompetitorResult


class FakeDB:
    def __init__(self, known):
        self._known = known
        self.inserted, self.updated = [], []

    def known_hashes(self, name):
        return self._known.get(name, {})

    def competitor_id(self, name):
        return f"id-{name}"

    def insert_entry(self, cid, entry, run_id):
        self.inserted.append((cid, entry.title))
        return f"eid-{entry.title}"

    def update_entry_body(self, cid, entry, run_id):
        self.updated.append((cid, entry.title))


def _good_source(monkeypatch, new_titles):
    def fake_collect(**kwargs):
        return {"ok": True,
                "new": [{"kind": "new", "entry": {
                    "title": t, "body": "b", "entry_date": "2026-05-12",
                    "url": "http://x", "content_hash": f"c-{t}",
                    "body_hash": f"b-{t}"}} for t in new_titles],
                "updated": []}
    monkeypatch.setattr("src.collector.collect_source", fake_collect)


def test_cold_start_seeds_without_changes(monkeypatch):
    _good_source(monkeypatch, ["A", "B"])
    db = FakeDB(known={})
    src = Source("Linear", None, "http://h", None)
    results = collect_all([src], db, run_id="r1", run_date=date(2026, 5, 19))
    assert results[0].seeded is True
    assert results[0].changes == []
    assert len(db.inserted) == 2


def test_established_competitor_reports_changes(monkeypatch):
    _good_source(monkeypatch, ["A"])
    db = FakeDB(known={"Linear": {"old": "old"}})
    src = Source("Linear", None, "http://h", None)
    results = collect_all([src], db, run_id="r1", run_date=date(2026, 5, 19))
    assert results[0].seeded is False
    assert [c.entry.title for c in results[0].changes] == ["A"]


def test_failed_source_isolated(monkeypatch):
    monkeypatch.setattr("src.collector.collect_source",
                        lambda **k: {"ok": False, "error": "feed down"})
    db = FakeDB(known={"Linear": {"old": "old"}})
    src = Source("Linear", None, "http://h", None)
    results = collect_all([src], db, run_id="r1", run_date=date(2026, 5, 19))
    assert results[0].ok is False
    assert results[0].error == "feed down"
