# RUNBOOK — Meeting Prep Agent

Operational reference. For what it does and why, see [README.md](./README.md).

## Inputs

| Source | What | Auth |
|---|---|---|
| Google Calendar | Today's events (or next 7d for `--meeting`) — title, time, attendees, conference link | OAuth installed-app, token cached at `~/.config/meeting-prep-agent/token.json` |
| Gmail | Recent threads with each attendee, last ~30 days, excluding `from:me` and `[prep]` subjects | Same token |
| `context/linkedin-<localpart>.md` | Manually pasted LinkedIn / background context per attendee | Local file |
| `.env` | `USER_EMAIL`, `ANTHROPIC_API_KEY` | Local file |
| `credentials.json` | Google OAuth client (Desktop app) — repo root, gitignored | Local file |

## Outputs

| Output | Path / destination |
|---|---|
| Brief markdown | `briefs/YYYY-MM-DD-<title-slug>-<event-id>.md` |
| Email | Subject `[prep] <title> — <time>`, body = brief, sent to `USER_EMAIL` |
| Run log | `logs/run-<timestamp>-<hex>.jsonl` (structured per-step JSONL) |
| Audits (manual) | `audits/YYYY-WW.md` after Friday hallucination audit |

## Modes

| Command | Behavior |
|---|---|
| `python main.py --setup-auth` | One-time browser OAuth flow; writes token cache |
| `python main.py --meeting "<query>"` | Match one event in next 7d by title or attendee email substring |
| `python main.py --daily` | Brief every relevant meeting on today's calendar |

`--daily` skip filters: declined events, solo events (<2 attendees), titles matching `Focus|Lunch|Block|OOO|Hold`, all-day events without attendees.

## Failure modes

| Failure | Symptom | Handling |
|---|---|---|
| Missing/expired Google token | `auth.py` raises | Re-run `--setup-auth` |
| Gmail / Calendar API quota or 5xx | Tool retries 3× with exponential backoff (`tenacity`); after that, tool returns `{status:"error"}` and the agent records empty section | Run logs the error; rerun later |
| Claude API rejection (e.g. low credit) | SDK returns `ResultMessage` with **zero tool calls** | `agent.py` checks `mcp__briefs__save_brief` was called; if not, raises and exits non-zero. See `CLAUDE.md` lesson #1. |
| SDK subprocess exit-1 on Windows shutdown | Spurious traceback after success | Suppressed if a `ResultMessage` was received. See `CLAUDE.md` lesson #2. |
| SMTP failure on send | Brief is already saved to `briefs/`; only email is lost | Logged; brief survives — `save_brief` and `send_email` are split tools |
| Unicode in titles / names | Filename / console errors | `python-slugify(allow_unicode=False)` for paths; stdio reconfigured to UTF-8 in `main.py` |
| `ZoneInfo` missing TZ data on Windows | `ZoneInfoNotFoundError` | `tzdata` is in `requirements.txt` |

## Safety invariants

- Sends email **only** to `USER_EMAIL` (the operator's own inbox). No external recipients.
- Calendar / Gmail scopes are read-only (`calendar.readonly`, `gmail.readonly`); only `gmail.send` is write.
- One `query()` per meeting, `max_turns=12`. No unbounded loops.
- Every step logged to JSONL with `run_id`.

## Approximate cost per run

Single meeting (typical): ~8–15k input tokens (calendar event + 3–5 thread bodies + LinkedIn context + system prompt), ~600 output tokens. With `claude-sonnet-4-6` (≈$3 / MTok input, $15 / MTok output) that's roughly **$0.04–0.06 per meeting**.

`--daily` with 4 meetings: ~$0.15–0.25 per day. Scheduled at 7am via `schedule_daily.ps1` (Windows Task Scheduler), so monthly cost ~$3–6.

## Scheduling

Register the daily run once: `./schedule_daily.ps1` in PowerShell. Inspect with `Get-ScheduledTask -TaskName MeetingPrepAgent-Daily`. Logs land in `logs/`.

## Recovery checklist

1. `python main.py --setup-auth` — refresh token if Google calls fail.
2. Tail latest `logs/run-*.jsonl` — every step records status; find the first `error`.
3. Re-run `python main.py --meeting "<title>"` for the failed meeting only.
4. If the agent ran but the brief looks fabricated → log it in the weekly audit and tighten `prompts/system.md`.
