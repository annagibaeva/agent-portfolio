from __future__ import annotations
from dataclasses import asdict
from datetime import date

from mcp.server.fastmcp import FastMCP

from mcp_server.differ import classify
from mcp_server.fetcher import FetchError, fetch_url
from mcp_server.parser import parse_feed, parse_html
from src.models import Entry

mcp = FastMCP("changelog-tools")


def _entry_dict(e: Entry) -> dict:
    d = asdict(e)
    d["entry_date"] = e.entry_date.isoformat()
    return d


def collect_source(*, feed_url: str | None, html_url: str, css_hint: str | None,
                    known: dict[str, str], run_date: date) -> dict:
    entries: list[Entry] = []
    errors: list[str] = []
    if feed_url:
        try:
            entries = parse_feed(fetch_url(feed_url))
        except FetchError as exc:
            errors.append(f"feed: {exc}")
    if not entries:
        try:
            entries = parse_html(fetch_url(html_url), css_hint, run_date)
        except FetchError as exc:
            errors.append(f"html: {exc}")
    if not entries:
        return {"ok": False, "error": "; ".join(errors) or "no entries parsed"}
    result = classify(entries, known)
    return {
        "ok": True,
        "new": [{"kind": c.kind, "entry": _entry_dict(c.entry)} for c in result.new],
        "updated": [{"kind": c.kind, "entry": _entry_dict(c.entry)}
                    for c in result.updated],
    }


@mcp.tool()
def collect_changelog(feed_url: str | None, html_url: str, css_hint: str | None,
                      known_hashes: dict[str, str],
                      run_date: str) -> dict:
    """MCP tool: fetch/parse/diff a competitor changelog."""
    return collect_source(
        feed_url=feed_url, html_url=html_url, css_hint=css_hint,
        known=known_hashes, run_date=date.fromisoformat(run_date),
    )


if __name__ == "__main__":
    mcp.run()
