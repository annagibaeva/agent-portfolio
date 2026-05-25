from __future__ import annotations
from datetime import date, datetime

import feedparser
from selectolax.parser import HTMLParser

from src.hashing import body_hash, content_hash
from src.models import Entry


def _entry(title: str, body: str, dt: date, url: str) -> Entry:
    return Entry(
        title=title.strip(), body=body.strip(), entry_date=dt, url=url.strip(),
        content_hash=content_hash(title, dt, url), body_hash=body_hash(body),
    )


def parse_feed(raw_xml: str) -> list[Entry]:
    parsed = feedparser.parse(raw_xml)
    out: list[Entry] = []
    for item in parsed.entries:
        struct = item.get("published_parsed") or item.get("updated_parsed")
        dt = date(*struct[:3]) if struct else date.today()
        body = item.get("summary", "") or item.get("description", "")
        out.append(_entry(item.get("title", "Untitled"), body, dt,
                          item.get("link", "")))
    return out


def parse_html(raw_html: str, css_hint: str | None, run_date: date) -> list[Entry]:
    tree = HTMLParser(raw_html)
    selector = css_hint or "article"
    out: list[Entry] = []
    for node in tree.css(selector):
        heading = node.css_first("h1, h2, h3")
        title = heading.text(strip=True) if heading else "Untitled"
        time_node = node.css_first("time")
        dt = run_date
        if time_node and time_node.attributes.get("datetime"):
            try:
                dt = datetime.fromisoformat(
                    time_node.attributes["datetime"][:10]).date()
            except ValueError:
                dt = run_date
        body = node.text(strip=True)
        link = node.css_first("a")
        url = link.attributes.get("href", "") if link else ""
        out.append(_entry(title, body, dt, url))
    return out
