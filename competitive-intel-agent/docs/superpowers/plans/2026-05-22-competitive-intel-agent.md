# Competitive Intel Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a weekly scheduled agent that watches 5–10 competitor changelogs, diffs week-over-week, and emails a PM-commentary digest backed by Supabase history.

**Architecture:** A Python orchestrator (`main.py`) drives a DB-free stdio MCP server (`changelog-tools`) for fetch/parse/diff, persists to Supabase Postgres, calls `claude-sonnet-4-6` once per run for commentary, and renders a markdown + HTML digest.

**Tech Stack:** Python 3.12+, `mcp`, `anthropic`, `claude-agent-sdk`, `supabase`, `feedparser`, `httpx`, `selectolax`, `pyyaml`, `pytest`.

---

## File Structure

| File | Responsibility |
|---|---|
| `requirements.txt` | Pinned dependencies |
| `.env.example` | Documented env vars (no secrets) |
| `src/config.py` | Load + validate env vars into a frozen `Config` |
| `src/hashing.py` | `normalize`, `content_hash`, `body_hash` — pure functions |
| `src/models.py` | Dataclasses: `Source`, `Entry`, `DiffResult`, `Change` |
| `src/run_logger.py` | Structured JSONL logging keyed by `run_id` + run summary |
| `mcp_server/fetcher.py` | HTTP fetch: timeout, retry, User-Agent |
| `mcp_server/parser.py` | Parse RSS/Atom + HTML into normalized `Entry` list |
| `mcp_server/differ.py` | Classify entries vs `known_hashes` → new/updated |
| `mcp_server/server.py` | MCP stdio server exposing the 3 tools |
| `src/db.py` | Supabase client wrapper: competitors/entries/commentary/runs |
| `src/collector.py` | Drive MCP tools per competitor, isolation, seeding |
| `src/commentary.py` | One Claude call → validated tagged commentary |
| `src/digest.py` | Render markdown + HTML + email subject |
| `src/emailer.py` | SMTP send, dry-run default |
| `main.py` | Orchestration, run lifecycle, escalation, CLI |
| `db/schema.sql` | Idempotent DDL |
| `setup_db.py` | Apply schema, seed competitors |
| `seeds/competitors.yaml` | One-time competitor seed list |
| `prompts/commentary.md` | Versioned commentary prompt |
| `evals/` | Golden cases + runner |
| `tests/` | Unit tests mirroring modules |
| `schedule/competitive-intel.xml` | Windows Task Scheduler task |
| `README.md`, `RUNBOOK.md` | Docs |

---

## Task 1: Project scaffold + config

**Files:**
- Create: `requirements.txt`, `.env.example`, `src/__init__.py`, `mcp_server/__init__.py`, `tests/__init__.py`, `src/config.py`, `tests/test_config.py`

- [ ] **Step 1: Create directory skeleton and dependency files**

`requirements.txt`:
```
anthropic==0.39.0
claude-agent-sdk==0.1.0
mcp==1.2.0
supabase==2.10.0
feedparser==6.0.11
httpx==0.27.2
selectolax==0.3.27
pyyaml==6.0.2
pytest==8.3.3
```

`.env.example`:
```
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
DIGEST_RECIPIENT=
```
Create empty `src/__init__.py`, `mcp_server/__init__.py`, `tests/__init__.py`.

- [ ] **Step 2: Write the failing test**

`tests/test_config.py`:
```python
from __future__ import annotations
import pytest
from src.config import Config, load_config


def test_load_config_reads_env(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY",
              "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "DIGEST_RECIPIENT"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setenv("SMTP_PORT", "587")
    cfg = load_config()
    assert isinstance(cfg, Config)
    assert cfg.smtp_port == 587


def test_load_config_missing_var_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        load_config()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: src.config`.

- [ ] **Step 4: Implement `src/config.py`**

```python
from __future__ import annotations
import os
from dataclasses import dataclass

_REQUIRED = (
    "ANTHROPIC_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY",
    "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "DIGEST_RECIPIENT",
)


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str
    supabase_url: str
    supabase_service_key: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    digest_recipient: str


def load_config() -> Config:
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
    return Config(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        supabase_url=os.environ["SUPABASE_URL"],
        supabase_service_key=os.environ["SUPABASE_SERVICE_KEY"],
        smtp_host=os.environ["SMTP_HOST"],
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_user=os.environ["SMTP_USER"],
        smtp_password=os.environ["SMTP_PASSWORD"],
        digest_recipient=os.environ["DIGEST_RECIPIENT"],
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v` → Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example src tests
git commit -m "feat: project scaffold and config loader"
```

---

## Task 2: Models

**Files:**
- Create: `src/models.py`, `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/models.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Source:
    name: str
    feed_url: str | None
    html_url: str
    css_hint: str | None


@dataclass(frozen=True)
class Entry:
    title: str
    body: str
    entry_date: date
    url: str
    content_hash: str
    body_hash: str


@dataclass(frozen=True)
class Change:
    """An Entry plus how it changed this run."""
    entry: Entry
    kind: str  # "new" | "updated"


@dataclass(frozen=True)
class DiffResult:
    new: list[Change]
    updated: list[Change]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v` → Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: shared dataclasses"
```

---

## Task 3: Hashing

**Files:**
- Create: `src/hashing.py`, `tests/test_hashing.py`

- [ ] **Step 1: Write the failing test**

`tests/test_hashing.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hashing.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/hashing.py`**

```python
from __future__ import annotations
import hashlib
import re
from datetime import date

_WS = re.compile(r"\s+")
_TAG = re.compile(r"<[^>]+>")


def normalize(text: str) -> str:
    """Lowercase, strip tags, collapse whitespace."""
    return _WS.sub(" ", _TAG.sub(" ", text)).strip().lower()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(title: str, entry_date: date, url: str) -> str:
    """Stable identity of an entry. Body deliberately excluded."""
    return _sha(f"{normalize(title)}|{entry_date.isoformat()}|{normalize(url)}")


def body_hash(body: str) -> str:
    """Hash of normalized body — detects edits to an existing entry."""
    return _sha(normalize(body))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_hashing.py -v` → Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/hashing.py tests/test_hashing.py
git commit -m "feat: stable content and body hashing"
```

---

## Task 4: MCP — parser

**Files:**
- Create: `mcp_server/parser.py`, `tests/test_parser.py`, `tests/fixtures/sample_feed.xml`, `tests/fixtures/sample_changelog.html`

- [ ] **Step 1: Create fixtures**

`tests/fixtures/sample_feed.xml`:
```xml
<?xml version="1.0"?>
<rss version="2.0"><channel><title>Linear</title>
<item><title>SSO beta</title><link>http://linear.app/c/1</link>
<pubDate>Mon, 12 May 2026 00:00:00 GMT</pubDate>
<description>SAML SSO is now in beta.</description></item>
<item><title>Faster search</title><link>http://linear.app/c/2</link>
<pubDate>Tue, 13 May 2026 00:00:00 GMT</pubDate>
<description>Search is 2x faster.</description></item>
</channel></rss>
```

`tests/fixtures/sample_changelog.html`:
```html
<html><body><main class="changelog">
<article><h2>Custom fields</h2><time datetime="2026-05-12">May 12</time>
<p>Add custom fields to any project.</p></article>
<article><h2>Bulk edit</h2><time datetime="2026-05-13">May 13</time>
<p>Edit many tasks at once.</p></article>
</main></body></html>
```

- [ ] **Step 2: Write the failing test**

`tests/test_parser.py`:
```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_parser.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Implement `mcp_server/parser.py`**

```python
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
    """Parse RSS/Atom feed text into Entry list."""
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
    """Parse an HTML changelog page. css_hint selects entry containers."""
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_parser.py -v` → Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add mcp_server/parser.py tests/test_parser.py tests/fixtures
git commit -m "feat: feed and HTML changelog parsers"
```

---

## Task 5: MCP — fetcher

**Files:**
- Create: `mcp_server/fetcher.py`, `tests/test_fetcher.py`

- [ ] **Step 1: Write the failing test**

`tests/test_fetcher.py`:
```python
from __future__ import annotations
import httpx
import pytest
from mcp_server.fetcher import fetch_url, FetchError


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_url_returns_body_on_200():
    def handler(req):
        return httpx.Response(200, text="hello")
    assert fetch_url("http://x", client=_client(handler)) == "hello"


def test_fetch_url_retries_then_raises():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(500)
    with pytest.raises(FetchError):
        fetch_url("http://x", client=_client(handler), retries=2)
    assert calls["n"] == 3  # initial + 2 retries
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fetcher.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `mcp_server/fetcher.py`**

```python
from __future__ import annotations
import time

import httpx

_UA = "CompetitiveIntelAgent/1.0 (+portfolio)"


class FetchError(RuntimeError):
    """Raised when a URL cannot be fetched after retries."""


def fetch_url(url: str, *, client: httpx.Client | None = None,
              retries: int = 2, timeout: float = 10.0) -> str:
    """GET a URL with retries and backoff. Raises FetchError on failure."""
    owns = client is None
    client = client or httpx.Client(timeout=timeout,
                                    headers={"User-Agent": _UA},
                                    follow_redirects=True)
    try:
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.text
            except (httpx.HTTPError,) as exc:
                last = exc
                if attempt < retries:
                    time.sleep(2 ** attempt)
        raise FetchError(f"{url}: {last}")
    finally:
        if owns:
            client.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fetcher.py -v` → Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_server/fetcher.py tests/test_fetcher.py
git commit -m "feat: HTTP fetcher with retry and backoff"
```

---

## Task 6: MCP — differ

**Files:**
- Create: `mcp_server/differ.py`, `tests/test_differ.py`

- [ ] **Step 1: Write the failing test**

`tests/test_differ.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_differ.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `mcp_server/differ.py`**

```python
from __future__ import annotations
from src.models import Change, DiffResult, Entry


def classify(entries: list[Entry], known: dict[str, str]) -> DiffResult:
    """Split entries into new/updated/unchanged.

    `known` maps content_hash -> body_hash for entries already stored.
    """
    new: list[Change] = []
    updated: list[Change] = []
    for e in entries:
        if e.content_hash not in known:
            new.append(Change(entry=e, kind="new"))
        elif known[e.content_hash] != e.body_hash:
            updated.append(Change(entry=e, kind="updated"))
    return DiffResult(new=new, updated=updated)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_differ.py -v` → Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_server/differ.py tests/test_differ.py
git commit -m "feat: entry diff classifier"
```

---

## Task 7: MCP server wiring

**Files:**
- Create: `mcp_server/server.py`, `tests/test_server.py`

- [ ] **Step 1: Write the failing test**

`tests/test_server.py`:
```python
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
```

Also create empty `tests/fixtures_helper.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_server.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `mcp_server/server.py`**

`collect_source` is the pure core (testable). The MCP stdio wrapper exposes it as a tool.

```python
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
    """Fetch + parse + diff one source. RSS first, HTML fallback.

    Returns {ok, new, updated} or {ok: False, error}.
    """
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
    """MCP tool: fetch/parse/diff a competitor changelog.

    known_hashes maps content_hash -> body_hash for already-stored entries.
    """
    return collect_source(
        feed_url=feed_url, html_url=html_url, css_hint=css_hint,
        known=known_hashes, run_date=date.fromisoformat(run_date),
    )


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_server.py -v` → Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_server/server.py tests/test_server.py tests/fixtures_helper.py
git commit -m "feat: changelog-tools MCP server"
```

---

## Task 8: Database schema + setup

**Files:**
- Create: `db/schema.sql`, `seeds/competitors.yaml`, `setup_db.py`

- [ ] **Step 1: Write `db/schema.sql`**

```sql
-- Idempotent. Created in dependency order.
create extension if not exists "pgcrypto";

create table if not exists competitors (
  id uuid primary key default gen_random_uuid(),
  name text unique not null,
  feed_url text,
  html_url text not null,
  css_hint text,
  active boolean not null default true,
  created_at timestamptz default now()
);

create table if not exists runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz default now(),
  finished_at timestamptz,
  status text not null,
  competitors_ok int default 0,
  competitors_failed int default 0,
  new_entries int default 0,
  tokens int default 0,
  outcome text
);

create table if not exists changelog_entries (
  id uuid primary key default gen_random_uuid(),
  competitor_id uuid references competitors(id),
  title text not null,
  body text,
  entry_date date,
  url text,
  content_hash text not null,
  body_hash text not null,
  first_seen_run uuid references runs(id),
  last_updated_run uuid references runs(id),
  created_at timestamptz default now(),
  unique (competitor_id, content_hash)
);

create table if not exists commentary (
  id uuid primary key default gen_random_uuid(),
  entry_id uuid references changelog_entries(id),
  run_id uuid references runs(id),
  kind text not null check (kind in ('per_change','synthesis')),
  so_what text,
  tag text check (tag in ('Threat','Parity gap','Table stakes','Noise')),
  confidence numeric check (confidence between 0 and 1),
  synthesis jsonb,
  created_at timestamptz default now()
);
```

- [ ] **Step 2: Write `seeds/competitors.yaml`**

```yaml
- name: Linear
  feed_url: https://linear.app/changelog/rss.xml
  html_url: https://linear.app/changelog
  css_hint: null
- name: Asana
  feed_url: null
  html_url: https://asana.com/whats-new
  css_hint: article
- name: Monday.com
  feed_url: null
  html_url: https://support.monday.com/hc/en-us/sections/360002428400
  css_hint: article
- name: Jira
  feed_url: https://jira.atlassian.com/activity
  html_url: https://www.atlassian.com/software/jira/whats-new
  css_hint: article
```

- [ ] **Step 3: Write `setup_db.py`**

```python
"""Apply db/schema.sql and seed the competitors table. Idempotent."""
from __future__ import annotations
from pathlib import Path

import yaml

from src.config import load_config
from src.db import Database


def main() -> None:
    cfg = load_config()
    db = Database(cfg)
    schema = (Path(__file__).parent / "db" / "schema.sql").read_text()
    db.execute_sql(schema)
    seeds = yaml.safe_load(
        (Path(__file__).parent / "seeds" / "competitors.yaml").read_text())
    for s in seeds:
        db.upsert_competitor(s)
    print(f"Schema applied. Seeded {len(seeds)} competitors.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify imports resolve**

Run: `python -c "import ast; ast.parse(open('setup_db.py').read())"`
Expected: no output (valid syntax). `Database` is implemented in Task 9.

- [ ] **Step 5: Commit**

```bash
git add db/schema.sql seeds/competitors.yaml setup_db.py
git commit -m "feat: Supabase schema, competitor seeds, setup script"
```

---

## Task 9: Database wrapper

**Files:**
- Create: `src/db.py`, `tests/test_db.py`

- [ ] **Step 1: Write the failing test**

`src/db.py` wraps `supabase`. Tests inject a fake client so no network is needed.

`tests/test_db.py`:
```python
from __future__ import annotations
from src.db import Database


class FakeQuery:
    def __init__(self, store, table):
        self.store, self.table = store, table
        self._rows = list(store.get(table, []))

    def select(self, *a):
        return self

    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]
        return self

    def execute(self):
        return type("R", (), {"data": self._rows})()

    def insert(self, rows):
        self.store.setdefault(self.table, []).extend(
            rows if isinstance(rows, list) else [rows])
        return self


class FakeClient:
    def __init__(self):
        self.store = {"competitors": [{"id": "1", "name": "Linear",
                       "feed_url": None, "html_url": "http://x",
                       "css_hint": None, "active": True}]}

    def table(self, name):
        return FakeQuery(self.store, name)


def test_active_competitors_returns_sources():
    db = Database.__new__(Database)
    db.client = FakeClient()
    comps = db.active_competitors()
    assert len(comps) == 1
    assert comps[0].name == "Linear"


def test_known_hashes_empty_for_new_competitor():
    db = Database.__new__(Database)
    db.client = FakeClient()
    assert db.known_hashes("nonexistent") == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_db.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/db.py`**

```python
from __future__ import annotations
from datetime import date

from supabase import create_client

from src.config import Config
from src.models import Entry, Source


class Database:
    """Thin Supabase wrapper. All run-time persistence lives here."""

    def __init__(self, cfg: Config) -> None:
        self.client = create_client(cfg.supabase_url, cfg.supabase_service_key)

    # --- competitors ---
    def active_competitors(self) -> list[Source]:
        rows = self.client.table("competitors").select("*").eq(
            "active", True).execute().data
        return [Source(name=r["name"], feed_url=r["feed_url"],
                       html_url=r["html_url"], css_hint=r["css_hint"])
                for r in rows]

    def competitor_id(self, name: str) -> str | None:
        rows = self.client.table("competitors").select("id").eq(
            "name", name).execute().data
        return rows[0]["id"] if rows else None

    def upsert_competitor(self, row: dict) -> None:
        self.client.table("competitors").upsert(
            row, on_conflict="name").execute()

    # --- entries ---
    def known_hashes(self, competitor_name: str) -> dict[str, str]:
        cid = self.competitor_id(competitor_name)
        if not cid:
            return {}
        rows = self.client.table("changelog_entries").select(
            "content_hash, body_hash").eq("competitor_id", cid).execute().data
        return {r["content_hash"]: r["body_hash"] for r in rows}

    def insert_entry(self, competitor_id: str, entry: Entry,
                     run_id: str) -> str:
        row = {
            "competitor_id": competitor_id, "title": entry.title,
            "body": entry.body, "entry_date": entry.entry_date.isoformat(),
            "url": entry.url, "content_hash": entry.content_hash,
            "body_hash": entry.body_hash, "first_seen_run": run_id,
            "last_updated_run": run_id,
        }
        res = self.client.table("changelog_entries").upsert(
            row, on_conflict="competitor_id,content_hash",
            ignore_duplicates=True).execute()
        return res.data[0]["id"] if res.data else ""

    def update_entry_body(self, competitor_id: str, entry: Entry,
                          run_id: str) -> None:
        self.client.table("changelog_entries").update({
            "body": entry.body, "body_hash": entry.body_hash,
            "last_updated_run": run_id,
        }).eq("competitor_id", competitor_id).eq(
            "content_hash", entry.content_hash).execute()

    # --- runs ---
    def open_run(self) -> str:
        res = self.client.table("runs").insert(
            {"status": "running"}).execute()
        return res.data[0]["id"]

    def close_run(self, run_id: str, **fields) -> None:
        self.client.table("runs").update(fields).eq("id", run_id).execute()

    def recent_runs(self, limit: int = 3) -> list[dict]:
        return self.client.table("runs").select("*").order(
            "started_at", desc=True).limit(limit).execute().data

    # --- commentary ---
    def insert_commentary(self, row: dict) -> None:
        self.client.table("commentary").insert(row).execute()

    def last_watchlist(self) -> list[str]:
        rows = self.client.table("commentary").select("synthesis").eq(
            "kind", "synthesis").order(
            "created_at", desc=True).limit(1).execute().data
        if not rows or not rows[0].get("synthesis"):
            return []
        return rows[0]["synthesis"].get("watch_list", [])

    def execute_sql(self, sql: str) -> None:
        """Run raw DDL via the Supabase Postgres RPC `exec_sql`."""
        self.client.rpc("exec_sql", {"sql": sql}).execute()
```

> **Note for executor:** `execute_sql` relies on a Postgres function `exec_sql`.
> If the Supabase project lacks it, `RUNBOOK.md` (Task 15) documents pasting
> `db/schema.sql` into the Supabase SQL editor as the fallback for first setup.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_db.py -v` → Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat: Supabase database wrapper"
```

---

## Task 10: Run logger

**Files:**
- Create: `src/run_logger.py`, `tests/test_run_logger.py`

- [ ] **Step 1: Write the failing test**

`tests/test_run_logger.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_run_logger.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/run_logger.py`**

```python
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path


class RunLogger:
    """Structured JSONL logging keyed by run_id."""

    def __init__(self, run_id: str, log_dir: Path) -> None:
        self.run_id = run_id
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        self.path = log_dir / f"{run_id}.jsonl"

    def event(self, event: str, **fields) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id, "event": event, **fields,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def summary(self, *, competitors_ok: int, competitors_failed: int,
                new_entries: int, tokens: int, outcome: str) -> str:
        line = (f"[{self.run_id}] {outcome} — "
                f"{competitors_ok} ok / {competitors_failed} failed, "
                f"{new_entries} new entries, {tokens} tokens")
        self.event("summary", competitors_ok=competitors_ok,
                   competitors_failed=competitors_failed,
                   new_entries=new_entries, tokens=tokens, outcome=outcome)
        return line
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_run_logger.py -v` → Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/run_logger.py tests/test_run_logger.py
git commit -m "feat: structured JSONL run logger"
```

---

## Task 11: Collector

**Files:**
- Create: `src/collector.py`, `tests/test_collector.py`

The collector calls the MCP `collect_source` core per competitor, isolates failures,
persists new/updated entries, and reports per-competitor status. Cold-start = a
competitor with no `known_hashes`: persist all, mark `seeded`, emit no changes.

- [ ] **Step 1: Write the failing test**

`tests/test_collector.py`:
```python
from __future__ import annotations
from datetime import date
from src.models import Source
from src.collector import collect_all, CompetitorResult


class FakeDB:
    def __init__(self, known):
        self._known = known
        self.inserted, self.updated = [], []

    def known_hashes(self, name):
        return self._known.get(name, {})

    def competitor_id(self, name):
        return f"id-{name}"

    def insert_entry(self, cid, entry, run_id):
        self.inserted.append((cid, entry.title))
        return f"eid-{entry.title}"

    def update_entry_body(self, cid, entry, run_id):
        self.updated.append((cid, entry.title))


def _good_source(monkeypatch, new_titles):
    def fake_collect(**kwargs):
        return {"ok": True,
                "new": [{"kind": "new", "entry": {
                    "title": t, "body": "b", "entry_date": "2026-05-12",
                    "url": "http://x", "content_hash": f"c-{t}",
                    "body_hash": f"b-{t}"}} for t in new_titles],
                "updated": []}
    monkeypatch.setattr("src.collector.collect_source", fake_collect)


def test_cold_start_seeds_without_changes(monkeypatch):
    _good_source(monkeypatch, ["A", "B"])
    db = FakeDB(known={})
    src = Source("Linear", None, "http://h", None)
    results = collect_all([src], db, run_id="r1", run_date=date(2026, 5, 19))
    assert results[0].seeded is True
    assert results[0].changes == []
    assert len(db.inserted) == 2


def test_established_competitor_reports_changes(monkeypatch):
    _good_source(monkeypatch, ["A"])
    db = FakeDB(known={"Linear": {"old": "old"}})
    src = Source("Linear", None, "http://h", None)
    results = collect_all([src], db, run_id="r1", run_date=date(2026, 5, 19))
    assert results[0].seeded is False
    assert [c.entry.title for c in results[0].changes] == ["A"]


def test_failed_source_isolated(monkeypatch):
    monkeypatch.setattr("src.collector.collect_source",
                        lambda **k: {"ok": False, "error": "feed down"})
    db = FakeDB(known={"Linear": {"old": "old"}})
    src = Source("Linear", None, "http://h", None)
    results = collect_all([src], db, run_id="r1", run_date=date(2026, 5, 19))
    assert results[0].ok is False
    assert results[0].error == "feed down"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_collector.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/collector.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date

from mcp_server.server import collect_source
from src.models import Change, Entry, Source


@dataclass
class CompetitorResult:
    name: str
    ok: bool
    seeded: bool = False
    changes: list[Change] = field(default_factory=list)
    error: str | None = None


def _to_entry(d: dict) -> Entry:
    return Entry(title=d["title"], body=d["body"],
                 entry_date=date.fromisoformat(d["entry_date"]),
                 url=d["url"], content_hash=d["content_hash"],
                 body_hash=d["body_hash"])


def collect_all(sources: list[Source], db, run_id: str,
                run_date: date) -> list[CompetitorResult]:
    """Fetch/diff/persist every source. Each source is failure-isolated."""
    results: list[CompetitorResult] = []
    for src in sources:
        try:
            known = db.known_hashes(src.name)
            raw = collect_source(
                feed_url=src.feed_url, html_url=src.html_url,
                css_hint=src.css_hint, known=known, run_date=run_date,
            )
        except Exception as exc:  # isolation: one bad source never kills the run
            results.append(CompetitorResult(src.name, ok=False,
                                            error=f"{type(exc).__name__}: {exc}"))
            continue
        if not raw["ok"]:
            results.append(CompetitorResult(src.name, ok=False,
                                            error=raw.get("error")))
            continue

        cid = db.competitor_id(src.name)
        cold_start = len(known) == 0
        changes: list[Change] = []
        for item in raw["new"]:
            entry = _to_entry(item["entry"])
            db.insert_entry(cid, entry, run_id)
            if not cold_start:
                changes.append(Change(entry=entry, kind="new"))
        for item in raw["updated"]:
            entry = _to_entry(item["entry"])
            db.update_entry_body(cid, entry, run_id)
            changes.append(Change(entry=entry, kind="updated"))

        results.append(CompetitorResult(
            src.name, ok=True, seeded=cold_start, changes=changes))
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_collector.py -v` → Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/collector.py tests/test_collector.py
git commit -m "feat: failure-isolated collector with cold-start seeding"
```

---

## Task 12: Commentary prompt + module

**Files:**
- Create: `prompts/commentary.md`, `src/commentary.py`, `tests/test_commentary.py`

- [ ] **Step 1: Write `prompts/commentary.md`**

```markdown
# Competitive Intel Commentary

You are a competitive analyst for TaskFlow, a mid-market project management tool.
Competitors: Jira, Asana, Monday.com, Linear. TaskFlow's positioning: powerful
enough for engineering-led orgs, clean enough for non-technical teammates.

You receive this week's changelog changes across competitors, plus last week's
watchlist. Produce JSON via the `submit_commentary` tool.

For EACH change provide:
- `so_what`: one sentence on why a TaskFlow PM should care.
- `tag`: exactly one of `Threat`, `Parity gap`, `Table stakes`, `Noise`.
- `confidence`: 0.0–1.0, your certainty in the tag.

Then a weekly `synthesis`:
- `themes`: 1–3 cross-competitor patterns.
- `watch_list`: things to watch next week.
- `suggested_response`: one concrete suggestion for TaskFlow.
- `prior_watchlist_status`: for each item in the supplied previous watchlist,
  state whether it shipped, is still pending, or had no movement.

Be concise and direct. No corporate jargon.
```

- [ ] **Step 2: Write the failing test**

`tests/test_commentary.py`:
```python
from __future__ import annotations
from src.commentary import validate_commentary, CommentaryError


def _valid_payload():
    return {
        "changes": [
            {"index": 0, "so_what": "x", "tag": "Threat", "confidence": 0.9},
        ],
        "synthesis": {
            "themes": ["t"], "watch_list": ["w"],
            "suggested_response": "r", "prior_watchlist_status": [],
        },
    }


def test_validate_accepts_good_payload():
    out = validate_commentary(_valid_payload(), n_changes=1)
    assert out["changes"][0]["tag"] == "Threat"


def test_validate_rejects_bad_tag():
    bad = _valid_payload()
    bad["changes"][0]["tag"] = "Spicy"
    import pytest
    with pytest.raises(CommentaryError, match="tag"):
        validate_commentary(bad, n_changes=1)


def test_validate_rejects_confidence_out_of_range():
    bad = _valid_payload()
    bad["changes"][0]["confidence"] = 1.5
    import pytest
    with pytest.raises(CommentaryError, match="confidence"):
        validate_commentary(bad, n_changes=1)


def test_validate_rejects_change_count_mismatch():
    import pytest
    with pytest.raises(CommentaryError, match="count"):
        validate_commentary(_valid_payload(), n_changes=2)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_commentary.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Implement `src/commentary.py`**

```python
from __future__ import annotations
import json
from pathlib import Path

from anthropic import Anthropic

from src.models import Change

_MODEL = "claude-sonnet-4-6"
_TAGS = {"Threat", "Parity gap", "Table stakes", "Noise"}
_PROMPT = Path(__file__).parent.parent / "prompts" / "commentary.md"
_MAX_CHANGES = 60

_TOOL = {
    "name": "submit_commentary",
    "description": "Submit per-change tags and the weekly synthesis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "changes": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "so_what": {"type": "string"},
                    "tag": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["index", "so_what", "tag", "confidence"],
            }},
            "synthesis": {"type": "object"},
        },
        "required": ["changes", "synthesis"],
    },
}


class CommentaryError(RuntimeError):
    """Raised when model output fails validation."""


def validate_commentary(payload: dict, n_changes: int) -> dict:
    changes = payload.get("changes", [])
    if len(changes) != n_changes:
        raise CommentaryError(
            f"change count mismatch: got {len(changes)}, expected {n_changes}")
    for c in changes:
        if c.get("tag") not in _TAGS:
            raise CommentaryError(f"invalid tag: {c.get('tag')}")
        conf = c.get("confidence")
        if not isinstance(conf, (int, float)) or not 0.0 <= conf <= 1.0:
            raise CommentaryError(f"confidence out of range: {conf}")
    if "synthesis" not in payload:
        raise CommentaryError("missing synthesis")
    return payload


def _format_changes(changes: list[Change]) -> str:
    lines = []
    for i, c in enumerate(changes):
        lines.append(f"[{i}] ({c.kind}) {c.entry.title} — {c.entry.body[:300]}")
    return "\n".join(lines)


def generate_commentary(api_key: str, changes: list[Change],
                        prior_watchlist: list[str]) -> tuple[dict, int]:
    """Return (validated_payload, tokens_used). Raises CommentaryError on bad output."""
    if len(changes) > _MAX_CHANGES:
        changes = changes[:_MAX_CHANGES]
    client = Anthropic(api_key=api_key)
    user = (f"Previous watchlist: {prior_watchlist or 'none'}\n\n"
            f"This week's changes:\n{_format_changes(changes)}")
    resp = client.messages.create(
        model=_MODEL, max_tokens=4000,
        system=_PROMPT.read_text(),
        tools=[_TOOL], tool_choice={"type": "tool", "name": "submit_commentary"},
        messages=[{"role": "user", "content": user}],
    )
    tokens = resp.usage.input_tokens + resp.usage.output_tokens
    tool_use = next((b for b in resp.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise CommentaryError("model returned no tool_use block")
    payload = tool_use.input if isinstance(tool_use.input, dict) else \
        json.loads(tool_use.input)
    return validate_commentary(payload, n_changes=len(changes)), tokens
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_commentary.py -v` → Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add prompts/commentary.md src/commentary.py tests/test_commentary.py
git commit -m "feat: commentary prompt, generation, and validation"
```

---

## Task 13: Digest renderer

**Files:**
- Create: `src/digest.py`, `tests/test_digest.py`

- [ ] **Step 1: Write the failing test**

`tests/test_digest.py`:
```python
from __future__ import annotations
from datetime import date
from src.models import Change, Entry
from src.collector import CompetitorResult
from src.digest import render_digest, email_subject


def _change(title, tag, kind="new"):
    e = Entry(title=title, body="b", entry_date=date(2026, 5, 12),
              url="http://x", content_hash="c", body_hash="b")
    return Change(entry=e, kind=kind)


def _commentary(tags):
    return {
        "changes": [{"index": i, "so_what": f"reason {i}", "tag": t,
                     "confidence": 0.9} for i, t in enumerate(tags)],
        "synthesis": {"themes": ["theme one"], "watch_list": ["watch x"],
                      "suggested_response": "do y", "prior_watchlist_status": []},
    }


def test_render_includes_synthesis_and_changes():
    results = [CompetitorResult("Linear", ok=True,
               changes=[_change("SSO", "Threat")])]
    md = render_digest(results, _commentary(["Threat"]),
                       week="2026-W21", failed=[], stale=[])
    assert "2026-W21" in md
    assert "SSO" in md
    assert "Threat" in md
    assert "theme one" in md


def test_render_lists_failed_and_stale_sources():
    md = render_digest([], {"changes": [], "synthesis": {
        "themes": [], "watch_list": [], "suggested_response": "",
        "prior_watchlist_status": []}},
        week="2026-W21", failed=[("Asana", "timeout")], stale=["Jira"])
    assert "Asana" in md and "timeout" in md
    assert "Jira" in md


def test_email_subject_counts_tags():
    subj = email_subject(_commentary(["Threat", "Threat", "Parity gap"]),
                         week="2026-W21")
    assert "W21" in subj
    assert "2 Threat" in subj


def test_email_subject_quiet_week():
    subj = email_subject({"changes": [], "synthesis": {}}, week="2026-W21")
    assert "quiet" in subj.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_digest.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/digest.py`**

```python
from __future__ import annotations
from collections import Counter
from html import escape


def email_subject(commentary: dict, week: str) -> str:
    counts = Counter(c["tag"] for c in commentary.get("changes", [])
                     if c.get("tag") and c["tag"] != "Noise")
    wk = week.split("-")[-1]
    if not counts:
        return f"Competitive Intel {wk} — quiet week"
    parts = [f"{n} {tag}" for tag, n in counts.most_common()]
    return f"Competitive Intel {wk} — " + ", ".join(parts)


def render_digest(results, commentary: dict, week: str,
                  failed: list[tuple[str, str]], stale: list[str]) -> str:
    """Render the weekly digest as markdown."""
    syn = commentary.get("synthesis", {})
    by_index = {c["index"]: c for c in commentary.get("changes", [])}
    lines = [f"# Competitive Intel — {week}", ""]
    ok = sum(1 for r in results if r.ok)
    lines.append(f"Sources: {ok} ok / {len(failed)} failed")
    lines.append("")

    lines.append("## Weekly synthesis")
    for theme in syn.get("themes", []):
        lines.append(f"- **Theme:** {theme}")
    if syn.get("suggested_response"):
        lines.append(f"- **Suggested response:** {syn['suggested_response']}")
    lines.append("")

    if syn.get("prior_watchlist_status"):
        lines.append("## Last week's watchlist")
        for item in syn["prior_watchlist_status"]:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Changes by competitor")
    idx = 0
    for r in results:
        if not r.ok:
            continue
        if r.seeded:
            lines.append(f"### {r.name}\n- _Seeded — tracking starts next week._")
            continue
        if not r.changes:
            lines.append(f"### {r.name}\n- _No changes this week._")
            continue
        lines.append(f"### {r.name}")
        noise = 0
        for ch in r.changes:
            c = by_index.get(idx, {})
            idx += 1
            tag = c.get("tag", "Table stakes")
            if tag == "Noise":
                noise += 1
                continue
            flag = "  ⚠️ needs review" if c.get("confidence", 1.0) < 0.8 else ""
            kind = ch.kind.capitalize()
            lines.append(
                f"- [{tag}] ({kind}) {c.get('so_what','')}  "
                f"({ch.entry.title}, {ch.entry.entry_date}, {ch.entry.url}){flag}")
        if noise:
            lines.append(f"\nNoise this week: {noise} changes (not shown)")
    lines.append("")

    if failed:
        lines.append("## ⚠️ Sources unavailable this week")
        for name, err in failed:
            lines.append(f"- {name} — {err}")
        lines.append("")
    if stale:
        lines.append("## 🔧 Sources needing attention")
        for name in stale:
            lines.append(
                f"- {name} — no entries for 3 consecutive runs; check css_hint / URL")
        lines.append("")
    return "\n".join(lines)


def render_html(markdown_text: str) -> str:
    """Minimal HTML wrapper — preserves the markdown as a <pre> block."""
    return f"<html><body><pre>{escape(markdown_text)}</pre></body></html>"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_digest.py -v` → Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/digest.py tests/test_digest.py
git commit -m "feat: digest renderer and email subject"
```

---

## Task 14: Emailer

**Files:**
- Create: `src/emailer.py`, `tests/test_emailer.py`

- [ ] **Step 1: Write the failing test**

`tests/test_emailer.py`:
```python
from __future__ import annotations
from src.emailer import send_digest


class FakeSMTP:
    sent = []

    def __init__(self, host, port):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        pass

    def login(self, user, pw):
        pass

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


def test_dry_run_does_not_send(monkeypatch):
    FakeSMTP.sent.clear()
    sent = send_digest(subject="s", html="<p>x</p>", recipient="a@b.c",
                       smtp_host="h", smtp_port=587, smtp_user="u",
                       smtp_password="p", dry_run=True, smtp_cls=FakeSMTP)
    assert sent is False
    assert FakeSMTP.sent == []


def test_send_delivers_message(monkeypatch):
    FakeSMTP.sent.clear()
    sent = send_digest(subject="s", html="<p>x</p>", recipient="a@b.c",
                       smtp_host="h", smtp_port=587, smtp_user="u",
                       smtp_password="p", dry_run=False, smtp_cls=FakeSMTP)
    assert sent is True
    assert len(FakeSMTP.sent) == 1
    assert FakeSMTP.sent[0]["Subject"] == "s"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_emailer.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/emailer.py`**

```python
from __future__ import annotations
import smtplib
from email.message import EmailMessage


def send_digest(*, subject: str, html: str, recipient: str,
                smtp_host: str, smtp_port: int, smtp_user: str,
                smtp_password: str, dry_run: bool = True,
                smtp_cls=smtplib.SMTP) -> bool:
    """Send the digest email. Returns True if sent, False if dry-run.

    smtp_cls is injectable for testing.
    """
    if dry_run:
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg.set_content("HTML digest — view in an HTML-capable client.")
    msg.add_alternative(html, subtype="html")
    with smtp_cls(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_emailer.py -v` → Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/emailer.py tests/test_emailer.py
git commit -m "feat: SMTP emailer with dry-run default"
```

---

## Task 15: Stale-source detection

**Files:**
- Create: `src/staleness.py`, `tests/test_staleness.py`

- [ ] **Step 1: Write the failing test**

`tests/test_staleness.py`:
```python
from __future__ import annotations
from src.staleness import stale_sources
from src.collector import CompetitorResult


def test_source_failing_three_runs_is_stale():
    history = {
        "Jira": [0, 0],   # entries in the previous 2 runs
    }
    this_run = [CompetitorResult("Jira", ok=True, seeded=False, changes=[])]
    assert "Jira" in stale_sources(this_run, history, threshold=3)


def test_source_with_recent_activity_not_stale():
    history = {"Linear": [0, 5]}
    this_run = [CompetitorResult("Linear", ok=True, seeded=False, changes=[])]
    assert stale_sources(this_run, history, threshold=3) == []


def test_seeded_source_not_flagged():
    history = {"NewComp": []}
    this_run = [CompetitorResult("NewComp", ok=True, seeded=True, changes=[])]
    assert stale_sources(this_run, history, threshold=3) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_staleness.py -v` → Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/staleness.py`**

```python
from __future__ import annotations
from src.collector import CompetitorResult


def stale_sources(results: list[CompetitorResult],
                  history: dict[str, list[int]],
                  threshold: int = 3) -> list[str]:
    """Return names of sources with zero entries for `threshold` runs in a row.

    `history` maps competitor name -> entry counts of the previous runs
    (most recent first), covering up to threshold-1 prior runs.
    """
    stale: list[str] = []
    for r in results:
        if not r.ok or r.seeded:
            continue
        this_count = len(r.changes)
        prior = history.get(r.name, [])[: threshold - 1]
        if this_count == 0 and len(prior) >= threshold - 1 \
                and all(c == 0 for c in prior):
            stale.append(r.name)
    return stale
```

> **Note:** per-competitor prior counts come from `changelog_entries.first_seen_run`
> grouped by run. `main.py` (Task 16) builds `history` via a `db.entry_counts_by_run`
> helper — add that helper to `src/db.py` in this task.

- [ ] **Step 4: Add `entry_counts_by_run` to `src/db.py`**

Append this method to the `Database` class:
```python
    def entry_counts_by_run(self, competitor_name: str,
                            run_ids: list[str]) -> dict[str, int]:
        """Count entries first seen in each of the given runs."""
        cid = self.competitor_id(competitor_name)
        if not cid or not run_ids:
            return {}
        rows = self.client.table("changelog_entries").select(
            "first_seen_run").eq("competitor_id", cid).in_(
            "first_seen_run", run_ids).execute().data
        counts = {rid: 0 for rid in run_ids}
        for r in rows:
            rid = r["first_seen_run"]
            if rid in counts:
                counts[rid] += 1
        return counts
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_staleness.py -v` → Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add src/staleness.py tests/test_staleness.py src/db.py
git commit -m "feat: stale-source detection"
```

---

## Task 16: Orchestrator (main.py)

**Files:**
- Create: `main.py`, `tests/test_main.py`

- [ ] **Step 1: Write the failing test**

`tests/test_main.py`:
```python
from __future__ import annotations
from datetime import date
import main as m


def test_iso_week_label():
    assert m.iso_week_label(date(2026, 5, 22)) == "2026-W21"


def test_build_history_shapes_counts():
    class DB:
        def recent_runs(self, limit):
            return [{"id": "r2"}, {"id": "r1"}]

        def entry_counts_by_run(self, name, run_ids):
            return {"r2": 0, "r1": 3}
    history = m.build_history(DB(), ["Linear"])
    assert history["Linear"] == [0, 3]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py -v` → Expected: FAIL — `ModuleNotFoundError: main` or attribute error.

- [ ] **Step 3: Implement `main.py`**

```python
"""Competitive Intel Agent — weekly orchestrator.

Usage:
  python main.py                      dry-run (no email)
  python main.py --send               full run, sends email
  python main.py --competitor Linear  re-run one source
  python main.py --demo               run against local fixtures
"""
from __future__ import annotations
import argparse
import sys
from datetime import date
from pathlib import Path

from src.collector import collect_all
from src.commentary import CommentaryError, generate_commentary
from src.config import load_config
from src.db import Database
from src.digest import email_subject, render_digest, render_html
from src.emailer import send_digest
from src.run_logger import RunLogger
from src.staleness import stale_sources

LOG_DIR = Path(__file__).parent / "logs"
DIGEST_DIR = Path(__file__).parent / "digests"


def iso_week_label(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def build_history(db, names: list[str]) -> dict[str, list[int]]:
    """Per-competitor entry counts for the 2 prior runs, most recent first."""
    runs = db.recent_runs(limit=3)
    prior_ids = [r["id"] for r in runs][1:]  # skip the current run if present
    history: dict[str, list[int]] = {}
    for name in names:
        counts = db.entry_counts_by_run(name, prior_ids)
        history[name] = [counts.get(rid, 0) for rid in prior_ids]
    return history


def run(send: bool, only: str | None) -> int:
    cfg = load_config()
    db = Database(cfg)
    run_id = db.open_run()
    log = RunLogger(run_id=run_id, log_dir=LOG_DIR)
    today = date.today()
    week = iso_week_label(today)

    sources = db.active_competitors()
    if only:
        sources = [s for s in sources if s.name == only]
    if not sources:
        db.close_run(run_id, status="failed", outcome="no competitors")
        log.summary(competitors_ok=0, competitors_failed=0, new_entries=0,
                    tokens=0, outcome="failed: no competitors")
        return 1

    names = [s.name for s in sources]
    history = build_history(db, names)
    results = collect_all(sources, db, run_id=run_id, run_date=today)
    for r in results:
        log.event("collect", competitor=r.name, ok=r.ok,
                  seeded=r.seeded, changes=len(r.changes), error=r.error)

    failed = [(r.name, r.error or "unknown") for r in results if not r.ok]
    if len(failed) == len(results):
        db.close_run(run_id, status="failed", competitors_failed=len(failed),
                     outcome="all sources failed")
        log.summary(competitors_ok=0, competitors_failed=len(failed),
                    new_entries=0, tokens=0, outcome="failed: all sources down")
        return 1

    all_changes = [c for r in results for c in r.changes]
    tokens = 0
    commentary: dict = {"changes": [], "synthesis": {}}
    if all_changes:
        try:
            prior = db.last_watchlist()
            commentary, tokens = generate_commentary(
                cfg.anthropic_api_key, all_changes, prior)
            # persist commentary rows
            for i, c in enumerate(commentary["changes"]):
                db.insert_commentary({
                    "run_id": run_id, "kind": "per_change",
                    "so_what": c["so_what"], "tag": c["tag"],
                    "confidence": c["confidence"]})
            db.insert_commentary({"run_id": run_id, "kind": "synthesis",
                                  "synthesis": commentary["synthesis"]})
        except CommentaryError as exc:
            log.event("commentary_failed", error=str(exc))
            commentary = {"changes": [], "synthesis": {}}

    stale = stale_sources(results, history, threshold=3)
    markdown = render_digest(results, commentary, week=week,
                             failed=failed, stale=stale)
    DIGEST_DIR.mkdir(exist_ok=True)
    (DIGEST_DIR / f"{week}.md").write_text(markdown, encoding="utf-8")

    subject = email_subject(commentary, week=week)
    sent = send_digest(
        subject=subject, html=render_html(markdown),
        recipient=cfg.digest_recipient, smtp_host=cfg.smtp_host,
        smtp_port=cfg.smtp_port, smtp_user=cfg.smtp_user,
        smtp_password=cfg.smtp_password, dry_run=not send)

    status = "partial" if failed else "success"
    new_entries = sum(len(r.changes) for r in results)
    db.close_run(run_id, status=status, competitors_ok=len(results) - len(failed),
                 competitors_failed=len(failed), new_entries=new_entries,
                 tokens=tokens, outcome=f"digest written; email sent={sent}")
    print(log.summary(competitors_ok=len(results) - len(failed),
                      competitors_failed=len(failed), new_entries=new_entries,
                      tokens=tokens, outcome=status))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Competitive Intel Agent")
    p.add_argument("--send", action="store_true", help="send the digest email")
    p.add_argument("--competitor", help="re-run a single competitor by name")
    p.add_argument("--demo", action="store_true", help="run against fixtures")
    args = p.parse_args()
    if args.demo:
        from demo import run_demo
        return run_demo()
    return run(send=args.send, only=args.competitor)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_main.py -v` → Expected: 2 passed.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest --tb=short -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: orchestrator with run lifecycle and escalation"
```

---

## Task 17: Demo mode

**Files:**
- Create: `demo.py`, `tests/fixtures/demo_feed.xml`

- [ ] **Step 1: Create `tests/fixtures/demo_feed.xml`**

```xml
<?xml version="1.0"?>
<rss version="2.0"><channel><title>Demo</title>
<item><title>Demo SSO launch</title><link>http://demo/1</link>
<pubDate>Mon, 12 May 2026 00:00:00 GMT</pubDate>
<description>SAML SSO now generally available.</description></item>
</channel></rss>
```

- [ ] **Step 2: Implement `demo.py`**

`demo.py` runs the pipeline with an in-memory fake DB and a stubbed fetcher so
`python main.py --demo` works with no Supabase, no network, no API key beyond
`ANTHROPIC_API_KEY` (commentary is also stubbed if the key is absent).

```python
"""One-command demo: python main.py --demo. No DB, no network."""
from __future__ import annotations
from datetime import date
from pathlib import Path

from src.collector import collect_all
from src.digest import render_digest
from src.models import Source

FIX = Path(__file__).parent / "tests" / "fixtures"


class InMemoryDB:
    def __init__(self):
        self._entries: dict[str, dict[str, str]] = {}

    def known_hashes(self, name):
        return self._entries.get(name, {})

    def competitor_id(self, name):
        return f"demo-{name}"

    def insert_entry(self, cid, entry, run_id):
        name = cid.replace("demo-", "")
        self._entries.setdefault(name, {})[entry.content_hash] = entry.body_hash
        return f"e-{entry.content_hash}"

    def update_entry_body(self, cid, entry, run_id):
        pass


def run_demo() -> int:
    import mcp_server.server as server
    feed = (FIX / "demo_feed.xml").read_text()
    server.fetch_url = lambda url, **k: feed  # stub network

    db = InMemoryDB()
    sources = [Source("DemoCorp", "http://feed", "http://html", None)]

    # First run seeds silently.
    collect_all(sources, db, run_id="demo-r1", run_date=date(2026, 5, 12))
    # Second run would show diffs; for the demo we render the seeded state.
    results = collect_all(sources, db, run_id="demo-r2", run_date=date(2026, 5, 19))

    commentary = {"changes": [], "synthesis": {
        "themes": ["Demo mode — commentary stubbed"],
        "watch_list": [], "suggested_response": "Run with real config.",
        "prior_watchlist_status": []}}
    md = render_digest(results, commentary, week="2026-W21",
                       failed=[], stale=[])
    print(md)
    return 0
```

- [ ] **Step 3: Verify the demo runs**

Run: `python main.py --demo`
Expected: a rendered digest prints to stdout; exit code 0.

- [ ] **Step 4: Commit**

```bash
git add demo.py tests/fixtures/demo_feed.xml
git commit -m "feat: one-command demo mode"
```

---

## Task 18: Evals

**Files:**
- Create: `evals/run_evals.py`, `evals/cases/` (7 JSON cases), `evals/README.md`

- [ ] **Step 1: Create eval cases**

Create `evals/cases/` with one JSON file per case. Each case has `name`, `input`
(raw feed/HTML + known_hashes), and `expect` (predicate description). The 7 cases
mirror the spec's eval list:

`evals/cases/01_happy_path.json`:
```json
{"name": "happy_path",
 "feed": "<rss version=\"2.0\"><channel><item><title>A</title><link>http://x/a</link><pubDate>Mon, 12 May 2026 00:00:00 GMT</pubDate><description>desc</description></item></channel></rss>",
 "known": {},
 "expect_new": 1, "expect_updated": 0, "expect_ok": true}
```

`evals/cases/02_empty_week.json`:
```json
{"name": "empty_week",
 "feed": "<rss version=\"2.0\"><channel></channel></rss>",
 "html": "<html><body></body></html>",
 "known": {}, "expect_ok": false}
```

`evals/cases/03_feed_down.json`:
```json
{"name": "feed_down", "feed_error": true,
 "html": "<article><h2>Fallback</h2><p>b</p></article>",
 "css_hint": "article", "known": {}, "expect_new": 1, "expect_ok": true}
```

`evals/cases/04_html_only.json`:
```json
{"name": "html_only", "feed": null,
 "html": "<article><h2>HtmlEntry</h2><time datetime=\"2026-05-12\"></time><p>b</p></article>",
 "css_hint": "article", "known": {}, "expect_new": 1, "expect_ok": true}
```

`evals/cases/05_cold_start.json`:
```json
{"name": "cold_start",
 "feed": "<rss version=\"2.0\"><channel><item><title>A</title><link>http://x/a</link><pubDate>Mon, 12 May 2026 00:00:00 GMT</pubDate><description>d</description></item></channel></rss>",
 "known": {}, "expect_seeded": true}
```

`evals/cases/06_updated_entry.json`:
```json
{"name": "updated_entry",
 "feed": "<rss version=\"2.0\"><channel><item><title>A</title><link>http://x/a</link><pubDate>Mon, 12 May 2026 00:00:00 GMT</pubDate><description>NEW BODY</description></item></channel></rss>",
 "known_titled": {"title": "A", "url": "http://x/a", "date": "2026-05-12", "old_body": "old body"},
 "expect_new": 0, "expect_updated": 1}
```

`evals/cases/07_malformed_commentary.json`:
```json
{"name": "malformed_commentary",
 "commentary_payload": {"changes": [{"index": 0, "so_what": "x", "tag": "Bogus", "confidence": 0.5}], "synthesis": {}},
 "n_changes": 1, "expect_commentary_error": true}
```

- [ ] **Step 2: Implement `evals/run_evals.py`**

```python
"""Run golden eval cases. Exits non-zero on any failure."""
from __future__ import annotations
import json
import sys
from datetime import date
from pathlib import Path

from mcp_server.server import collect_source
from src.commentary import CommentaryError, validate_commentary
from src.hashing import body_hash, content_hash

CASES = Path(__file__).parent / "cases"


def _known_from_titled(t: dict) -> dict[str, str]:
    ch = content_hash(t["title"], date.fromisoformat(t["date"]), t["url"])
    return {ch: body_hash(t["old_body"])}


def run_case(case: dict) -> tuple[bool, str]:
    if "expect_commentary_error" in case:
        try:
            validate_commentary(case["commentary_payload"], case["n_changes"])
            return False, "expected CommentaryError, none raised"
        except CommentaryError:
            return True, "ok"

    known = case.get("known", {})
    if "known_titled" in case:
        known = _known_from_titled(case["known_titled"])

    # stub fetch
    import mcp_server.server as server
    feed = case.get("feed")
    html = case.get("html", "")

    def fake_fetch(url, **k):
        from mcp_server.fetcher import FetchError
        if case.get("feed_error") and url == "http://feed":
            raise FetchError("feed down")
        return feed if url == "http://feed" and feed else html
    server.fetch_url = fake_fetch

    result = collect_source(
        feed_url="http://feed" if (feed or case.get("feed_error")) else None,
        html_url="http://html", css_hint=case.get("css_hint"),
        known=known, run_date=date(2026, 5, 19))

    if "expect_ok" in case and result["ok"] != case["expect_ok"]:
        return False, f"ok mismatch: {result}"
    if result["ok"]:
        if "expect_new" in case and len(result["new"]) != case["expect_new"]:
            return False, f"new count: {len(result['new'])}"
        if "expect_updated" in case and \
                len(result["updated"]) != case["expect_updated"]:
            return False, f"updated count: {len(result['updated'])}"
    if case.get("expect_seeded"):
        # cold start = known empty + entries present
        if not (not known and result["ok"] and result["new"]):
            return False, "expected seedable cold-start state"
    return True, "ok"


def main() -> int:
    failures = 0
    for path in sorted(CASES.glob("*.json")):
        case = json.loads(path.read_text())
        ok, msg = run_case(case)
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {case['name']}: {msg}")
        if not ok:
            failures += 1
    print(f"\n{failures} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Write `evals/README.md`**

```markdown
# Evals

7 golden cases covering happy path, empty week, feed-down fallback, HTML-only
source, cold start, updated entry, and malformed commentary.

Run: `python evals/run_evals.py`  — exits non-zero on any failure.
Run before any change to `prompts/commentary.md` or the model.
```

- [ ] **Step 4: Run the evals**

Run: `python evals/run_evals.py`
Expected: `[PASS]` for all 7 cases, `0 failure(s).`, exit code 0.

- [ ] **Step 5: Commit**

```bash
git add evals
git commit -m "test: 7 golden eval cases with runner"
```

---

## Task 19: Docs + schedule

**Files:**
- Create: `README.md`, `RUNBOOK.md`, `schedule/competitive-intel.xml`

- [ ] **Step 1: Write `README.md`**

Follow the `morning-briefing-agent` README shape: Problem, User, Success Metrics,
Architecture (ASCII), How to run, Project layout. Include:
```
## Run
pip install -r requirements.txt
cp .env.example .env   # fill in values
python setup_db.py     # one-time: schema + competitor seeds
python main.py --demo  # offline demo
python main.py         # dry-run (no email)
python main.py --send  # full run with email
```

- [ ] **Step 2: Write `RUNBOOK.md`**

Sections: Inputs (env vars, competitors table), Outputs (`digests/YYYY-WW.md`,
email, Supabase rows), Failure modes (all-sources-down → escalation; malformed
commentary → fallback digest; stale source → flagged), Approx cost (~1 Claude
call/week, ~$0.05–0.15), and **Historical lookup examples**:
```sql
-- Every Threat-tagged change for Linear, most recent first
select e.title, e.entry_date, c.so_what
from commentary c
join changelog_entries e on e.id = c.entry_id
join competitors comp on comp.id = e.competitor_id
where comp.name = 'Linear' and c.tag = 'Threat'
order by e.entry_date desc;
```
Also document the **first-setup fallback**: if the `exec_sql` RPC is unavailable,
paste `db/schema.sql` into the Supabase SQL editor, then run `python setup_db.py`
(seeding still works via the client).

- [ ] **Step 3: Write `schedule/competitive-intel.xml`**

A Windows Task Scheduler task definition running `python main.py --send` weekly
on Monday at 07:00, working directory set to the agent folder. Mirror
`morning-briefing-agent/schedule/morning-briefing.xml` structure.

- [ ] **Step 4: Verify the full suite once more**

Run: `python -m pytest --tb=short -q && python evals/run_evals.py`
Expected: all unit tests pass; all 7 evals pass.

- [ ] **Step 5: Commit**

```bash
git add README.md RUNBOOK.md schedule/
git commit -m "docs: README, RUNBOOK, and Task Scheduler definition"
```

---

## Self-Review

**Spec coverage:**
- RSS-first + HTML fallback → Tasks 4, 5, 7. ✓
- DB-free MCP server (fetch/parse/diff) → Tasks 4–7. ✓
- Supabase 4-table schema → Task 8; wrapper Task 9. ✓
- content_hash + body_hash, New/Updated/Unchanged → Tasks 3, 6, 11. ✓
- Cold-start seeding → Task 11. ✓
- Crash-safe idempotent insert (`ON CONFLICT`) → Task 9 (`insert_entry`). ✓
- `runs` lifecycle + escalation → Task 16. ✓
- Per-source isolation + HTTP hardening → Tasks 5, 11. ✓
- Commentary: batched call, tags, validation, fallback → Tasks 12, 16. ✓
- Watchlist carry-over → Tasks 9 (`last_watchlist`), 12, 16. ✓
- Stale-source detection → Task 15. ✓
- Digest markdown + HTML + headline subject → Task 13. ✓
- Email dry-run default → Task 14. ✓
- CLI `--send` / `--competitor` / `--demo` → Tasks 16, 17. ✓
- Evals ≥ 5 goldens → Task 18 (7 cases). ✓
- Logging JSONL + run summary → Task 10. ✓
- README / RUNBOOK / schedule → Task 19. ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code.

**Type consistency:** `Entry`, `Source`, `Change`, `DiffResult`, `CompetitorResult`
used consistently. `collect_source` signature identical in Tasks 7, 11, 17, 18.
`Database` method names (`known_hashes`, `insert_entry`, `update_entry_body`,
`open_run`, `close_run`, `recent_runs`, `entry_counts_by_run`, `last_watchlist`,
`insert_commentary`) consistent across Tasks 9, 15, 16.

**Scope:** Single agent, one coherent plan — appropriately scoped.
