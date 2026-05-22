# Competitive Intel Agent — Design Spec

**Date:** 2026-05-22
**Status:** Approved for planning
**Portfolio agent** — sibling of `morning-briefing-agent`. Conventions: agent-portfolio `CLAUDE.md`.

---

## Problem

Tracking competitors means manually checking 5–10 changelogs and release-note pages,
remembering what was there last week, and judging what matters. Done manually it is
slow, inconsistent, and easy to skip. The result is missed competitive moves and no
durable record of how the landscape shifted.

## User

**Anna Gibaeva** — PM for TaskFlow. Competitors: Jira, Asana, Monday.com, Linear
(extensible to 5–10 sources). Wants a weekly digest that surfaces what changed and
what it means for TaskFlow, plus a queryable history of competitive movement.

## Success Metrics

| Metric | Target |
|---|---|
| Time to read digest | < 3 minutes |
| Sources successfully fetched | ≥ 80% per run (rest degrade gracefully) |
| First run / new-competitor run | Seeds cleanly, never floods commentary |
| Re-run after mid-run crash | Resumes; no lost or double-counted weeks |
| Cost per run | ~1 Claude call/week (`claude-sonnet-4-6`) |

---

## Architecture

```
main.py  (orchestrator — weekly, Monday ~07:00 SGT)
│
├─ open run: INSERT runs row (status=running) → run_id
├─ Supabase (supabase-py): read active rows from `competitors`
│
├─ for each competitor (isolated try/except):
│   ├─ MCP server `changelog-tools` (stdio, DB-FREE):
│   │     fetch_changelog(source)              → raw (RSS/Atom, HTML fallback)
│   │     parse_entries(raw)                   → normalized entries + content_hash
│   │     diff(entries, known_hashes)          → entries whose hash is new
│   ├─ orchestrator reads known_hashes from `changelog_entries`
│   └─ orchestrator INSERTs new entries (ON CONFLICT DO NOTHING)
│
├─ select entries needing commentary (no row in `commentary`)
│   ├─ cold-start competitors → seed only, NO commentary
│   └─ established competitors → one batched Claude call
│        prompt: prompts/commentary.md → per-change {so_what, tag, confidence}
│        + weekly {themes, watch_list, suggested_response}
│   └─ validate model output; INSERT commentary rows
│
├─ render digest → digests/YYYY-WW.md   (artifact, source of truth for humans)
├─ send_email(HTML render)              (dry-run unless --send)
└─ close run: UPDATE runs row (status, counts, tokens, outcome)
```

### Approach chosen

Single Python orchestrator + one custom MCP server + Supabase Postgres backend.
The work is deterministic (fetch → diff → comment → deliver); the model's value is
the commentary only. Rejected: pushing orchestration into the SDK tool-loop
(non-deterministic, hard to eval) and split collector/reporter jobs (doubles ops
surface for marginal resilience gain).

---

## Components

| Unit | Responsibility | Depends on |
|---|---|---|
| `db/schema.sql` | Idempotent `CREATE TABLE IF NOT EXISTS` + constraints | — |
| `setup_db.py` | Apply schema; seed `competitors` from `seeds/competitors.yaml` | supabase-py |
| `seeds/competitors.yaml` | One-time seed list (name, feed_url, html_url, css_hint) | — |
| `mcp_server/changelog_tools.py` | `fetch_changelog`, `parse_entries`, `diff`. **No DB, no model.** | `feedparser`, `httpx`, `selectolax` |
| `src/db.py` | Supabase client wrapper: competitors / entries / commentary / runs | supabase-py |
| `src/collector.py` | Drives MCP tools per competitor; per-source isolation | MCP server, `src/db.py` |
| `src/commentary.py` | One batched Claude call → validated tagged commentary | `anthropic`, `prompts/commentary.md` |
| `src/digest.py` | Renders markdown + HTML email | collector + commentary output |
| `src/emailer.py` | SMTP send; dry-run default | config |
| `src/logging.py` | Structured JSONL with `run_id`; human run summary | — |
| `main.py` | Orchestration, run lifecycle, escalation | all of the above |
| `schedule/competitive-intel.xml` | Windows Task Scheduler task | — |

The MCP server is **DB-free and source-agnostic** — a reusable changelog tool. Its
`diff` tool takes `known_hashes: list[str]` as input and returns new entries; all
persistence lives in the orchestrator.

---

## Data Model (Supabase Postgres)

Tables are shown below in reading order. `schema.sql` must create them in
dependency order — `runs` and `competitors` first, then `changelog_entries`,
then `commentary` — because of the foreign keys.

```sql
competitors (
  id            uuid pk default gen_random_uuid(),
  name          text unique not null,
  feed_url      text,            -- RSS/Atom; nullable
  html_url      text not null,   -- changelog page (fallback + always stored)
  css_hint      text,            -- optional CSS selector for HTML fallback
  active        boolean not null default true,
  created_at    timestamptz default now()
)

changelog_entries (
  id            uuid pk default gen_random_uuid(),
  competitor_id uuid references competitors(id),
  title         text not null,
  body          text,
  entry_date    date,            -- from feed; defaults to run date if absent
  url           text,
  content_hash  text not null,   -- identity hash; see hashing rule below
  body_hash     text not null,   -- hash of normalized body; detects edits
  first_seen_run uuid references runs(id),
  last_updated_run uuid references runs(id),  -- bumped when body_hash changes
  created_at    timestamptz default now(),
  unique (competitor_id, content_hash)
)

commentary (
  id            uuid pk default gen_random_uuid(),
  entry_id      uuid references changelog_entries(id),  -- null for weekly synthesis
  run_id        uuid references runs(id),
  kind          text not null check (kind in ('per_change','synthesis')),
  so_what       text,
  tag           text check (tag in ('Threat','Parity gap','Table stakes','Noise')),
  confidence    numeric check (confidence between 0 and 1),
  synthesis     jsonb,           -- {themes, watch_list, suggested_response,
                                 --  prior_watchlist_status}
  created_at    timestamptz default now()
)

runs (
  id            uuid pk default gen_random_uuid(),
  started_at    timestamptz default now(),
  finished_at   timestamptz,
  status        text not null,   -- running | success | partial | failed
  competitors_ok int default 0,
  competitors_failed int default 0,
  new_entries   int default 0,
  tokens        int default 0,
  outcome       text
)
```

**content_hash rule:** `sha256(normalize(title) + '|' + entry_date + '|' + canonical_url)`.
`normalize` = lowercase, collapse whitespace, strip. This is the entry's stable
identity — volatile markup must not make a stable entry look new.

**body_hash rule:** `sha256(normalize(body))` where `normalize` strips tags and
collapses whitespace. Used only to detect *edits*: same `content_hash` + different
`body_hash` = an updated entry.

---

## Behavior

### Diff & seeding
- **New** = entries whose `content_hash` is not already in `changelog_entries` for
  that competitor → insert, commentary as "New".
- **Updated** = `content_hash` already present but `body_hash` differs → update the
  row's `body`/`body_hash`/`last_updated_run`, commentary as "Updated". Catches edits
  to existing changelog entries that would otherwise be missed.
- **Unchanged** = both hashes match → skip.
- **Cold start** (a competitor with zero existing rows): insert all entries, generate
  **no commentary**, report "seeded N entries" in the digest. Applies to run #1 *and*
  to any competitor added later. Real diffing begins the following run.

### Crash-safe / resumable
- Entries inserted idempotently (`ON CONFLICT (competitor_id, content_hash) DO NOTHING`).
- "Needs commentary" = entries with **no row in `commentary`** — not "not in the table".
  A run that dies after inserting entries but before commentary resumes correctly.
- Digest file write is an overwrite (idempotent). Email send is gated on `runs.status`
  reaching a sendable state, so a re-run does not double-send.

### Source reliability
- Each competitor is fetched inside its own `try/except`. A failed source is logged,
  listed under "⚠️ Sources unavailable this week" in the digest, and the run continues.
- HTTP client: 10s timeout, 2 retries with exponential backoff, explicit `User-Agent`.
- HTML fallback uses `css_hint` when present; an unparseable page is treated as a
  failed source, not a crash.
- **Stale-source detection:** before sending, query the last 3 `runs` for each
  competitor. A source that produced zero entries (or failed) for 3 consecutive runs
  is flagged in the digest under "🔧 Sources needing attention" — distinguishing a
  genuinely quiet competitor (occasional empty week) from a silently-broken
  `css_hint` or moved URL.

### Commentary
- One batched Claude call per run for all established-competitor changes.
- Each change carries its kind (`New` / `Updated`) into the prompt.
- Per change: `{so_what, tag, confidence}`; `tag ∈ {Threat, Parity gap, Table stakes, Noise}`.
- `Noise`-tagged changes collapse into a count, not listed individually.
- `confidence < 0.8` → change still shown, marked ⚠️ *needs review*.
- **Watchlist carry-over:** the prompt is fed the previous run's `watch_list` (read
  from the most recent `synthesis` row in `commentary`). The model is asked to
  explicitly resolve each prior item — shipped, still pending, or no movement — so the
  digest reads as an ongoing narrative rather than an isolated weekly snapshot.
- Weekly synthesis: `{themes, watch_list, suggested_response, prior_watchlist_status}`.
- Output requested via structured tool-use and **validated** (tag enum, confidence
  range, required fields). On validation failure: fall back to a digest listing raw
  changes with "commentary unavailable" — the run still delivers.
- Entry-count cap per commentary call (default 60) to bound tokens; overflow weeks
  log a warning and prioritise non-`Noise` sources.

### Escalation
- Whole-run escalation email fires only if **all** sources fail or the MCP server /
  Supabase is unreachable. `runs.status` set to `failed`.
- Partial success (some sources failed) → `status = partial`, digest still sent.

---

## Output

`digests/YYYY-WW.md` (ISO week, SGT) and an HTML email of the same content.

**Email subject** is a headline summary, not a static string:
`Competitive Intel W21 — 2 Threats, 1 Parity gap` (counts by tag; "quiet week" when none).

```
# Competitive Intel — Week WW, YYYY
Sources: N ok / M failed

## Weekly synthesis
Themes · Watch list · Suggested TaskFlow response

## Last week's watchlist
- Linear SSO beta → SHIPPED this week
- Asana custom fields → still pending

## Changes by competitor
### Linear
- [Threat] (New) <so_what>      (title, date, link)  ⚠️ needs review
- [Parity gap] (Updated) <so_what>  (title, date, link)
...
Noise this week: 4 changes (not shown)

## ⚠️ Sources unavailable this week
- Monday.com — feed timeout

## 🔧 Sources needing attention
- Jira — no entries for 3 consecutive runs; check css_hint / URL
```

---

## Configuration & Secrets

Env vars only: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `DIGEST_RECIPIENT`.

`competitors` table is the authoritative watch list. `seeds/competitors.yaml` is a
one-time seed consumed by `setup_db.py`; it is not read at run time.

---

## Testing & Evals

- Unit tests per `src/` module and per MCP tool.
- `evals/` — ≥ 5 golden cases, diffed on output not just pass/fail:
  1. Happy path — multiple competitors, mixed tags.
  2. Empty week — no new entries.
  3. Feed down — RSS 500, HTML fallback succeeds.
  4. HTML-only competitor — no feed, `css_hint` parse.
  5. Cold start — empty `changelog_entries`, expect seed + no commentary.
  6. Low-confidence change — `confidence < 0.8` marked ⚠️.
  7. Malformed model JSON — digest falls back to "commentary unavailable".
  8. Updated entry — same `content_hash`, changed `body_hash`, surfaces as "Updated".
  9. Stale source — competitor empty for 3 runs, appears under "needs attention".

## Logging

Structured JSONL keyed by `run_id`. Each run emits a human-readable summary:
competitors ok/failed, new entries, tokens, outcome. Mirrored into the `runs` table.

## CLI

```
python main.py                      # full run, dry-run (no email)
python main.py --send               # full run, sends email — used by the scheduler
python main.py --competitor Linear  # re-run a single source (testing / recovery)
python main.py --demo               # one-command portfolio demo (fixture data)
```

## Schedule

`schedule/competitive-intel.xml` — Windows Task Scheduler, Monday 07:00 SGT,
`python main.py --send`. Without `--send` the run is a dry-run by default.

---

## Out of Scope (v1)

- Daily collection — weekly run re-reads feeds; badly truncated feeds may drop
  mid-week entries (known limitation).
- No web UI; markdown file + Supabase are the only surfaces.
- Historical-lookup queries are supported by the schema but not automated;
  example queries documented in `RUNBOOK.md`.
- No automated changes to TaskFlow's roadmap — the digest is advisory.

## Known Trade-offs

- supabase-py (PostgREST) over direct Postgres: simpler, no pool management;
  complex historical joins are slightly less ergonomic — acceptable, lookups are ad hoc.
- HTML fallback is inherently brittle; `css_hint` + graceful degradation contain it
  but a redesigned competitor page will silently yield a failed source until the hint
  is updated.
