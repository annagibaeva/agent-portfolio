from __future__ import annotations
from datetime import date
from mcp_server.server import collect_source


def test_collect_source_feed_path(monkeypatch):
    from tests import fixtures_helper  # noqa
    feed = '''<rss version="2.0"><channel>
<item><title>X</title><link>http://x</link>
<pubDate>Mon, 12 May 2026 00:00:00 GMT</pubDate>
<description>d</description></item></channel></rss>'''
    monkeypatch.setattr("mcp_server.server.fetch_url", lambda url, **k: feed)
    result = collect_source(
        feed_url="http://f", html_url="http://h", css_hint=None,
        known={}, run_date=date(2026, 5, 19),
    )
    assert result["ok"] is True
    assert len(result["new"]) == 1
    assert result["new"][0]["kind"] == "new"


def test_collect_source_falls_back_to_html(monkeypatch):
    html = '<article><h2>HtmlEntry</h2><p>b</p></article>'

    def fake_fetch(url, **k):
        if url == "http://f":
            from mcp_server.fetcher import FetchError
            raise FetchError("feed down")
        return html
    monkeypatch.setattr("mcp_server.server.fetch_url", fake_fetch)
    result = collect_source(
        feed_url="http://f", html_url="http://h", css_hint="article",
        known={}, run_date=date(2026, 5, 19),
    )
    assert result["ok"] is True
    assert result["new"][0]["entry"]["title"] == "HtmlEntry"


def test_collect_source_all_fail(monkeypatch):
    def fake_fetch(url, **k):
        from mcp_server.fetcher import FetchError
        raise FetchError("down")
    monkeypatch.setattr("mcp_server.server.fetch_url", fake_fetch)
    result = collect_source(feed_url="http://f", html_url="http://h",
                            css_hint=None, known={}, run_date=date(2026, 5, 19))
    assert result["ok"] is False
    assert "error" in result
