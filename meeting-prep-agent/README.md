# Meeting Prep Agent

A personal agent that produces a one-page brief for each upcoming meeting. Pulls attendees from Google Calendar, recent threads from Gmail, and any LinkedIn context you've manually pasted into `./context/`. Saves the brief as markdown and emails it to your own inbox so it's visible on mobile.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env       # then edit
# Place credentials.json (see "Google OAuth setup") in the project root
python main.py --setup-auth
python main.py --meeting "<title fragment>"
```

## Modes

| Command | What it does |
|---|---|
| `python main.py --daily` | Briefs every relevant meeting on today's calendar |
| `python main.py --meeting "<query>"` | One meeting matched by title or attendee email substring (next 7d) |
| `python main.py --setup-auth` | One-time Google OAuth flow |

Skip filters for `--daily`: declined events, solo events (<2 attendees), titles matching `Focus|Lunch|Block|OOO|Hold`, all-day events without attendees.

## Output

- **File**: `briefs/YYYY-MM-DD-<title-slug>-<event-id>.md`
- **Email**: subject `[prep] <title> — <time>`, sent to `USER_EMAIL`
- **Log**: `logs/run-<timestamp>-<hex>.jsonl`

## Google OAuth setup

1. Open [Google Cloud Console](https://console.cloud.google.com), create or pick a project
2. Enable APIs: **Google Calendar API** and **Gmail API**
3. **OAuth consent screen** → User Type: External → fill app name + your email → add yourself as a test user
4. **Credentials** → Create Credentials → OAuth client ID → Application type: **Desktop app**
5. Download the JSON, save it as `credentials.json` in this project root
6. Run `python main.py --setup-auth` — a browser opens, consent, done. Token cached at `~/.config/meeting-prep-agent/token.json`

Scopes requested: `calendar.readonly`, `gmail.readonly`, `gmail.send`.

## Manual LinkedIn context

Drop a markdown file at `context/linkedin-<email-localpart>.md`. Example: for `sarah.chen@taskflow.io` → `context/linkedin-sarah.chen.md`. The agent reads it automatically when that person is an attendee.

## Brief structure

```
# <Title> — <YYYY-MM-DD HH:MM TZ>
**Join:** <link or "in-person">

## Attendees
## Recent emails
## Manual context
## Talking points
## Open questions
```

Empty section → `_none found_`. Capped to roughly one printed page.

## Scheduling

Run `./schedule_daily.ps1` in PowerShell once to register a Windows Scheduled Task that runs `--daily` at 7am. Inspect with `Get-ScheduledTask -TaskName MeetingPrepAgent-Daily`.

## Weekly hallucination audit

Every Friday, pick 3 random briefs from `briefs/` and verify each Talking Points / Open Questions claim against the source thread. Log results to `audits/YYYY-WW.md`. Target: <5% fabrication rate. Above that, tighten `prompts/system.md`.

## Architecture

- `main.py` — CLI, env, run_id
- `agent.py` — one Claude Agent SDK `query()` per meeting, `max_turns=12`
- `meetings.py` — Calendar fetch, skip filters, attendee normalization, slug
- `auth.py` — Google OAuth installed-app flow + token refresh
- `tools/` — in-process MCP servers (calendar, gmail, manual_context, briefs)
- `cache.py` — per-run attendee→Gmail-results memoization
- `logger.py` — JSONL run log

Architecture choices documented in `../../../.claude/plans/ancient-churning-waffle.md`.

## Roadmap

- **v1.1** — Slack, Drive, per-meeting-type prompt routing, priority badge, commitment extraction, prior-brief diffing
- **v2** — Eval system: golden-set regression, LLM-as-judge (cross-family), `useful`/`noise` feedback loop, sensitivity classifier

## Privacy

Briefs and email threads are written locally. Tokens cached at `~/.config/meeting-prep-agent/token.json`. Only the user's own Google account is touched. The `[prep]` email goes only to `USER_EMAIL`.
