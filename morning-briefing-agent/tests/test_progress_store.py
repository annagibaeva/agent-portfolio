import json
import os
import tempfile
from datetime import date
from src.progress_store import ProgressStore


def make_store(data: dict) -> tuple[ProgressStore, str]:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return ProgressStore(f.name), f.name


def test_current_day_on_start_date():
    store, path = make_store({"start_date": "2026-04-24", "days": {}, "last_anthropic_post": None})
    assert store.current_day(today=date(2026, 4, 24)) == 1
    os.unlink(path)


def test_current_day_five_days_in():
    store, path = make_store({"start_date": "2026-04-24", "days": {}, "last_anthropic_post": None})
    assert store.current_day(today=date(2026, 4, 28)) == 5
    os.unlink(path)


def test_log_run_writes_entry():
    store, path = make_store({"start_date": "2026-04-24", "days": {}, "last_anthropic_post": None})
    store.log_run(day=1, topics=["Claude Code"], sent_at="07:15:03", summary="OK | calendar:3 | gmail:2")
    data = json.loads(open(path).read())
    assert "1" in data["days"]
    assert data["days"]["1"]["topics"] == ["Claude Code"]
    os.unlink(path)


def test_cache_anthropic_post():
    store, path = make_store({"start_date": "2026-04-24", "days": {}, "last_anthropic_post": None})
    store.cache_anthropic_post({"title": "Test post", "url": "https://anthropic.com/engineering/test"})
    data = json.loads(open(path).read())
    assert data["last_anthropic_post"]["title"] == "Test post"
    os.unlink(path)


def test_get_cached_post_returns_none_when_missing():
    store, path = make_store({"start_date": "2026-04-24", "days": {}, "last_anthropic_post": None})
    assert store.get_cached_post() is None
    os.unlink(path)
