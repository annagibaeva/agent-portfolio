from __future__ import annotations
from datetime import date
from src.models import Entry
from mcp_server.differ import classify


def _e(title, body):
    from src.hashing import body_hash, content_hash
    d = date(2026, 5, 1)
    return Entry(title=title, body=body, entry_date=d, url=f"http://x/{title}",
                 content_hash=content_hash(title, d, f"http://x/{title}"),
                 body_hash=body_hash(body))


def test_classify_new_entry():
    e = _e("A", "body")
    result = classify([e], known={})
    assert [c.entry.title for c in result.new] == ["A"]
    assert result.updated == []


def test_classify_updated_when_body_hash_differs():
    e = _e("A", "new body")
    known = {e.content_hash: "old-body-hash"}
    result = classify([e], known=known)
    assert result.new == []
    assert [c.entry.title for c in result.updated] == ["A"]


def test_classify_unchanged_skipped():
    e = _e("A", "body")
    known = {e.content_hash: e.body_hash}
    result = classify([e], known=known)
    assert result.new == [] and result.updated == []
