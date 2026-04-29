# CLAUDE.md — Meeting Prep Agent

Project-specific guidance for Claude Code working in this directory.

## Project
A personal Meeting Prep Agent built on the Claude Agent SDK (Python). Pulls from Google Calendar + Gmail (direct APIs, OAuth), with manual LinkedIn paste. See `../../../.claude/plans/ancient-churning-waffle.md` for the full design.

## Architecture invariants
- Direct Google APIs (`google-api-python-client`) wrapped as in-process MCP servers via SDK `@tool` + `create_sdk_mcp_server` — **not** the `mcp__claude_ai_*` servers. Those are Claude-Code-internal and not callable from a standalone Python script.
- One `query()` call per meeting, `max_turns=12`.
- All Google API calls retried with `tenacity` (3 attempts, exponential backoff).
- `save_brief` and `send_email` are split — a brief survives email failure.
- Per-run attendee cache (`cache.py`) deduplicates Gmail searches across meetings.

## Best practices for Agent SDK apps (lessons from build)

### 1. A "successful" run with zero tool calls is a silent failure
The SDK can return a `ResultMessage` even when the model never called any tools — for example when the API rejects the call ("Credit balance is too low") or the model decides not to act. Always assert the agent actually performed the work it was supposed to do.

In `agent.py` we check `"mcp__briefs__save_brief" not in tool_calls` and convert that to an error. Pattern: **track tool calls, then verify the required ones happened before reporting success.**

### 2. Don't blanket-catch SDK shutdown exceptions
The Agent SDK's subprocess sometimes exits 1 on shutdown after a successful run on Windows. Catching and reporting that as failure hides real errors. Track whether you received a `ResultMessage`; if yes, the run succeeded regardless of shutdown noise. If no, the exception is real.

### 3. Windows console encoding
Default Windows console is `cp1252` and chokes on unicode that the SDK passes through (`≠`, em-dashes, emoji). Reconfigure stdio to UTF-8 at the top of `main.py`:
```python
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
```

### 4. `zoneinfo` needs `tzdata` on Windows
Linux/macOS ship the IANA TZ database; Windows doesn't. Add `tzdata` to `requirements.txt` if any code does `ZoneInfo(...)`.

### 5. Tool return shape: `{status, data, error}`
Every `@tool` returns a JSON-encoded `{"status": "ok"|"empty"|"error", "data": ..., "error": "..."}` payload. Lets the model distinguish "no results" from "tool broke" without inventing data. See `tools/calendar_tool.py` for the pattern.

### 6. Filter your own emails out of "recent context"
The Gmail search query for an attendee includes `-from:me -subject:"[prep]"` — otherwise the next day's run picks up yesterday's `[prep]` brief as "recent context" and the agent summarizes its own output.

### 7. Strip quoted history before passing thread bodies to the model
Gmail thread bodies include the full quoted history of every reply. Without stripping, you waste tokens on duplicate content and the model gets confused about who said what. Regex strip lines starting with `>` and `On <date>, <name> wrote:` blocks.

### 8. Use `python-slugify(allow_unicode=False)` for filenames built from user/calendar data
Display names, meeting titles, and attendee names contain unicode, emoji, apostrophes, and slashes that break filesystem paths. Always slugify before using as a filename.

## Commands
```bash
pip install -r requirements.txt
python main.py --setup-auth                  # one-time Google OAuth
python main.py --meeting "<title fragment>"  # one meeting
python main.py --daily                       # all of today's meetings
```

## Model
All `query()` calls use `claude-sonnet-4-6`.

## Roadmap
- v1.1: Slack, Drive, per-meeting-type prompt routing, priority badge, commitment extraction
- v2: Eval system (golden-set, LLM-as-judge with cross-family model, feedback loop)
