# RUNBOOK — Morning Briefing Agent

Operational reference. For motivation and metrics, see [README.md](./README.md).

## Inputs

| Source | What | Auth |
|---|---|---|
| Google Calendar | Today's events (time, title, attendees) | OAuth installed-app, token cached at `token.json` |
| Gmail | Last 24h of threads relevant to today's meetings + Substack newsletters | Same token |
| Anthropic engineering blog | Latest post (HTML scrape) | None |
| `agent-pm-learning-plan.md` | Day N theory / hands-on / quiz | Local file |
| `agent-pm-resources.md` | Day N ★ reading links | Local file |
| `progress.json` | Run history; computes current day-of-21 from start date | Local file |
| `.env` | `ANTHROPIC_API_KEY`, recipient email | Local file |
| `credentials.json` | Google OAuth client — gitignored | Local file |

## Outputs

| Output | Destination |
|---|---|
| HTML email | `annagibaeva05@gmail.com` at ~07:15 |
| Run log | `logs/` (Python `logging` to file) |
| Updated progress | `progress.json` (run timestamp + day index) |

## Schedule

Mon–Fri + Sun at 07:15 SGT (Saturday excluded). Windows Task Scheduler — task definition in `schedule/morning-briefing.xml`. Register with `schtasks /Create /XML schedule/morning-briefing.xml /TN MorningBriefing`.

## Sections of the brief

```
PROGRESS         Day N of 21 · Week W · X% complete
TODAY'S SCHEDULE Calendar events with times
MEETING CONTEXT  Claude-composed summary of relevant email threads
TODAY'S LEARNING Day N tasks (★ items + hands-on + quiz)
WHAT TO READ     ★ resource links for the day
AI PULSE         Anthropic blog + Substack newsletter summaries
```

Target: ~250 words total, readable in <90 seconds.

## Failure modes

| Failure | Symptom | Handling |
|---|---|---|
| Missing/expired Google token | `auth.py` raises during pipeline start | Run `python auth_setup.py` to refresh |
| Calendar / Gmail API 5xx or quota | Section returns empty | Brief is still composed and sent; that section shows fallback text |
| Anthropic blog HTML structure changes | News fetch returns nothing | AI Pulse drops the blog item; Substack summaries still send |
| Claude API failure during composition | `composer.py` raises | **Currently:** pipeline aborts, no email sent. **TODO:** add fallback that sends a raw-data email with sections from tools only |
| SMTP send failure | No email | Logged in `logs/`; rerun manually |
| Plan/resource markdown missing for current day | Learning / Reading sections empty | Brief still sends; add the day's content to source markdown |

Known gap: silent-failure fallback ("email always sent") is a stated success metric in the README but is not yet wired through `briefing.py`. Tracked in portfolio improvement backlog.

## Safety invariants

- Email goes only to the configured recipient (operator's own inbox).
- Read-only Google scopes for Calendar; Gmail uses `gmail.readonly` + `gmail.send`.
- No external write side-effects beyond the single outbound email.
- `progress.json` is the only persistent state; safe to delete to reset.

## Approximate cost per run

One Claude composition call per day. Inputs: calendar events + 2–4 Gmail thread snippets + 1 blog post + 1–3 Substack snippets + plan/resource markdown for the day ≈ **6–12k input tokens**. Output ≈ 400 tokens.

With `claude-sonnet-4-6` (≈$3 / MTok input, $15 / MTok output) that's roughly **$0.03 per run**, ~$0.80–1.00 per month at the 6-day cadence.

## Recovery checklist

1. Tail `logs/` for the latest run — find the first error.
2. If Google auth → `python auth_setup.py`.
3. If Anthropic API → check key + balance; rerun `python briefing.py`.
4. If `progress.json` is corrupt → delete it; the next run rebuilds from start date in `config.py`.
5. To dry-run without sending: `python briefing.py --dry-run` *(planned — not yet implemented; currently composes and sends in one path)*.

## Local files of note

- `briefing.py` — top-level pipeline (data gather → compose → send)
- `src/calendar_client.py`, `src/gmail_client.py` — Google API wrappers
- `src/news_fetcher.py` — Anthropic blog scrape
- `src/plan_loader.py` — day-N task / resource lookup
- `src/composer.py` — single Claude call composing Meeting Context + AI Pulse
- `src/email_builder.py` — HTML assembly
- `src/progress_store.py` — `progress.json` read/write
- `auth_setup.py` — one-time OAuth bootstrap
- `config.py` — start date, recipient, schedule constants
