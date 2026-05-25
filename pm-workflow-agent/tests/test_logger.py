import json
from pathlib import Path
import logger


def test_new_run_id_format():
    rid = logger.new_run_id()
    assert rid.startswith("run-")
    assert len(rid.split("-")) == 4  # run, date, time, hex


def test_log_appends_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(logger, "LOG_DIR", tmp_path)
    rid = "run-20260522-120000-abcdef"
    logger.log(rid, step="intake", status="ok")
    logger.log(rid, step="draft", status="ok")
    lines = (tmp_path / f"{rid}.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    entry = json.loads(lines[0])
    assert entry["run_id"] == rid and entry["step"] == "intake"


def test_trace_summary_contains_fields():
    s = logger.trace_summary("run-x", turns=2, tokens=1500, outcome="ok")
    assert "run-x" in s and "2" in s and "1500" in s and "ok" in s
