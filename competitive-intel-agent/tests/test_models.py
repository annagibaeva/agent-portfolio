from __future__ import annotations
from datetime import date
from src.models import Source, Entry


def test_entry_is_frozen():
    e = Entry(title="T", body="B", entry_date=date(2026, 5, 1),
              url="http://x", content_hash="c", body_hash="b")
    assert e.title == "T"
    assert e.entry_date == date(2026, 5, 1)


def test_source_optional_feed():
    s = Source(name="Linear", feed_url=None, html_url="http://x", css_hint=None)
    assert s.feed_url is None
