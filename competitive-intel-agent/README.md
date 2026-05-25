# Competitive Intel Agent

Weekly scheduled agent that watches competitor changelogs, diffs week-over-week,
and emails a PM-commentary digest backed by Supabase history.

## Problem

TaskFlow's competitors (Jira, Asana, Monday.com, Linear) ship updates faster
than a PM can read. Manually trawling 4+ changelogs every week is tedious and
misses cross-competitor patterns.

## User

A TaskFlow PM. Wants one short email on Monday morning: "Here's what shipped
last week, what matters, and what to watch."

## Success metrics

- Digest delivered every Monday with < 5% missed changes vs. manual review.
- Every flagged "Threat" reviewed by a PM within 48h.
- Zero hand-curation between runs.

## Architecture

```
+-------------+    +---------------------+    +-----------+
|  main.py    |--->| changelog-tools MCP |--->|  fetch    |
| (weekly)    |    |  (stdio, DB-free)   |    |  parse    |
+-------------+    +---------------------+    |  diff     |
       |                                      +-----------+
       |  per-competitor known_hashes
       v
+-------------+    +-------------+    +-----------+
|  Supabase   |    |  Claude     |    |  SMTP     |
|  (history)  |    |  sonnet-4-6 |    |  digest   |
+-------------+    +-------------+    +-----------+
```

Per-run flow: fetch each competitor → diff vs. stored hashes → persist new/
updated entries → one Claude call tags every change + writes a synthesis →
render markdown + HTML digest → send (or dry-run).

## Run

```bash
pip install -r requirements.txt
cp .env.example .env       # fill in values
python setup_db.py         # one-time: schema + competitor seeds
python main.py --demo      # offline demo (no DB, no network)
python main.py             # dry-run (no email)
python main.py --send      # full run with email
python evals/run_evals.py  # 7 golden cases
python -m pytest -q        # unit tests
```

## Project layout

```
main.py                 orchestrator + CLI
demo.py                 --demo mode (in-memory DB, stubbed fetch)
setup_db.py             one-time DB setup + competitor seed
src/                    config, models, hashing, db, collector,
                        commentary, digest, emailer, run_logger, staleness
mcp_server/             changelog-tools MCP server (fetch/parse/diff)
prompts/commentary.md   versioned commentary prompt
db/schema.sql           Supabase DDL
seeds/competitors.yaml  starting competitor list
evals/                  7 golden cases + runner
tests/                  unit tests mirroring src/
schedule/               Windows Task Scheduler definition
docs/                   spec, plan
```

See `RUNBOOK.md` for inputs, outputs, failure modes, and cost.
