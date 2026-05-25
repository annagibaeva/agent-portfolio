from __future__ import annotations
from pathlib import Path
from datetime import date
from mcp_server.parser import parse_feed, parse_html

FIX = Path(__file__).parent / "fixtures"


def test_parse_feed_returns_entries():
    entries = parse_feed((FIX / "sample_feed.xml").read_text())
    assert len(entries) == 2
    assert entries[0].title == "SSO beta"
    assert entries[0].entry_date == date(2026, 5, 12)
    assert entries[0].content_hash and entries[0].body_hash


def test_parse_html_with_css_hint():
    entries = parse_html(
        (FIX / "sample_changelog.html").read_text(),
        css_hint="article", run_date=date(2026, 5, 19),
    )
    assert len(entries) == 2
    assert entries[0].title == "Custom fields"
    assert entries[0].entry_date == date(2026, 5, 12)


def test_parse_html_missing_date_defaults_to_run_date():
    html = "<article><h2>No date</h2><p>body</p></article>"
    entries = parse_html(html, css_hint="article", run_date=date(2026, 5, 19))
    assert entries[0].entry_date == date(2026, 5, 19)
