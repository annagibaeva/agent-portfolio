# RUNBOOK — Competitive Intel Agent

## Inputs

**Environment variables** (see `.env.example`):
- `ANTHROPIC_API_KEY` — Claude API key
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` — Postgres backend
- `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USER`, `SMTP_PASSWORD`
- `DIGEST_RECIPIENT` — email address that receives the weekly digest

**Database**: `competitors` table (seeded once from `seeds/competitors.yaml`).
Add/remove rows directly in Supabase to change tracked sources.

## Outputs

- `digests/YYYY-Www.md` — markdown digest per run
- Email to `DIGEST_RECIPIENT` (only when `--send` is passed; default is dry-run)
- Supabase rows: `runs`, `changelog_entries`, `commentary`
- `logs/<run_id>.jsonl` — structured per-run JSONL log

## Failure modes

| Condition | Behavior |
|---|---|
| All sources fail to fetch/parse | Run marked `failed`, no email, exit 1 |
| Single source fails | Reported in "Sources unavailable" section; other sources continue |
| Claude returns malformed commentary | Logged, fallback to empty commentary, digest still rendered |
| Source returns 0 entries for 3 runs in a row | Flagged in "Sources needing attention" |
| `exec_sql` RPC unavailable in Supabase | See first-setup fallback below |
| Cold-start competitor (no history) | All entries seeded silently; first real digest is week 2 |

## Approximate cost

~1 Claude call per week (`claude-sonnet-4-6`), ~$0.05–0.15 depending on number
of changes. Fetch/parse is local + HTTP only.

## First-setup fallback

If `db.execute_sql()` fails because the Supabase project lacks the `exec_sql`
RPC: open the Supabase SQL editor, paste the contents of `db/schema.sql`, run
it once, then re-run `python setup_db.py` (seeding works via the standard
client and does not need the RPC).

## Historical lookup examples

```sql
-- Every Threat-tagged change for Linear, most recent first
select e.title, e.entry_date, c.so_what
from commentary c
join changelog_entries e on e.id = c.entry_id
join competitors comp on comp.id = e.competitor_id
where comp.name = 'Linear' and c.tag = 'Threat'
order by e.entry_date desc;

-- All synthesis snapshots in date order
select created_at, synthesis
from commentary
where kind = 'synthesis'
order by created_at desc;

-- Token usage trend
select started_at, tokens, status from runs order by started_at desc limit 12;
```

## Scheduling

`schedule/competitive-intel.xml` defines a Windows Task Scheduler task running
`python main.py --send` weekly on Monday at 07:00. Import with:

```powershell
schtasks /Create /XML schedule\competitive-intel.xml /TN "Competitive Intel Agent"
```
