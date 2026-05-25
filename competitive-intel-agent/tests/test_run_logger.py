from __future__ import annotations
import json
from src.run_logger import RunLogger


def test_logger_writes_jsonl(tmp_path):
    log = RunLogger(run_id="run-1", log_dir=tmp_path)
    log.event("fetch", competitor="Linear", ok=True)
    log.event("fetch", competitor="Asana", ok=False)
    lines = (tmp_path / "run-1.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["run_id"] == "run-1"
    assert first["event"] == "fetch"
    assert first["competitor"] == "Linear"


def test_summary_counts(tmp_path):
    log = RunLogger(run_id="run-1", log_dir=tmp_path)
    summary = log.summary(competitors_ok=3, competitors_failed=1,
                          new_entries=7, tokens=1200, outcome="success")
    assert "3" in summary and "success" in summary
