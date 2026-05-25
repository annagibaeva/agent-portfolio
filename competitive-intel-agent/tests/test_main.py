from __future__ import annotations
from datetime import date
import main as m


def test_iso_week_label():
    assert m.iso_week_label(date(2026, 5, 22)) == "2026-W21"


def test_build_history_shapes_counts():
    class DB:
        def recent_runs(self, limit):
            return [{"id": "r2"}, {"id": "r1"}]

        def entry_counts_by_run(self, name, run_ids):
            return {"r2": 0, "r1": 3}
    history = m.build_history(DB(), ["Linear"])
    assert history["Linear"] == [0, 3]
