from __future__ import annotations
from datetime import date
from src.hashing import normalize, content_hash, body_hash


def test_normalize_collapses_whitespace_and_lowercases():
    assert normalize("  Hello   World\n") == "hello world"


def test_content_hash_stable_across_whitespace():
    a = content_hash("New  SSO", date(2026, 5, 1), "http://x/?utm=1")
    b = content_hash("new sso", date(2026, 5, 1), "http://x/?utm=1")
    assert a == b


def test_content_hash_changes_with_title():
    a = content_hash("A", date(2026, 5, 1), "http://x")
    b = content_hash("B", date(2026, 5, 1), "http://x")
    assert a != b


def test_body_hash_ignores_markup_whitespace():
    assert body_hash("<p>Hello   world</p>") == body_hash("<p>Hello world</p>")


def test_body_hash_changes_with_content():
    assert body_hash("one") != body_hash("two")
