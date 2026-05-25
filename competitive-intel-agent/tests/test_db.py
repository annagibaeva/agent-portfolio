from __future__ import annotations
from src.db import Database


class FakeQuery:
    def __init__(self, store, table):
        self.store, self.table = store, table
        self._rows = list(store.get(table, []))

    def select(self, *a):
        return self

    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]
        return self

    def execute(self):
        return type("R", (), {"data": self._rows})()

    def insert(self, rows):
        self.store.setdefault(self.table, []).extend(
            rows if isinstance(rows, list) else [rows])
        return self


class FakeClient:
    def __init__(self):
        self.store = {"competitors": [{"id": "1", "name": "Linear",
                       "feed_url": None, "html_url": "http://x",
                       "css_hint": None, "active": True}]}

    def table(self, name):
        return FakeQuery(self.store, name)


def test_active_competitors_returns_sources():
    db = Database.__new__(Database)
    db.client = FakeClient()
    comps = db.active_competitors()
    assert len(comps) == 1
    assert comps[0].name == "Linear"


def test_known_hashes_empty_for_new_competitor():
    db = Database.__new__(Database)
    db.client = FakeClient()
    assert db.known_hashes("nonexistent") == {}
