# Morning Briefing Agent

**Portfolio Agent #1 · Week 1, Day 5 · 21-Day Agent PM Retraining Plan**

---

## Problem

Starting the day well requires loading four things into working memory: what's on the calendar, what email context matters for those meetings, what to learn today, and what's moving in the AI/agent space. Done manually, this takes 10–15 minutes of context-switching across four apps. Done badly, it means walking into a meeting unprepared or skipping the day's learning block because the morning felt chaotic.

---

## User

**Anna Gibaeva** — Singapore. Former Global AI Product Head (Mars Wrigley, $40M+ agentic revenue). Executing a 21-day agent PM retraining plan targeting Anthropic/OpenAI-tier agent PM roles. Needs a daily brief that loads the day's context in one read, without manual aggregation.

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Time to read brief | < 90 seconds | — |
| Brief delivered before 07:20 | 100% of scheduled days | — |
| All sections populated | ≥ 4/5 sections non-empty | — |
| Zero crashes (silent failures) | Fallback fires, email always sent | — |

*Eval results will populate after first 5 runs.*

---

## Architecture

```
briefing.py
│
├── Data gathering (parallel)
│   ├── Google Calendar API ──→ today's events (time, title, attendees)
│   ├── Gmail API ────────────→ meeting threads + Substack newsletters (last 24h)
│   └── HTTP fetch ───────────→ Anthropic engineering blog (latest post)
│
├── Plan loader
│   ├── agent-pm-learning-plan.md ──→ Day N theory, hands-on, quiz tasks
│   └── agent-pm-resources.md ──────→ Day N ★ reading links
│
├── Claude API (claude-sonnet-4-6)
│   └── Composes Meeting Context + AI Pulse sections
│       Target: ~250 words total brief
│
└── Gmail API (send)
    └── HTML email → annagibaeva05@gmail.com at 07:15
```

**Brief structure (top to bottom):**
```
PROGRESS         → Day N of 21 · Week W · X% complete
TODAY'S SCHEDULE → Calendar events with times
MEETING CONTEXT  → Claude-composed summary of relevant email threads
TODAY'S LEARNING → Day N tasks (★ items + hands-on + quiz)
WHAT TO READ     → ★ resource links for the day
AI PULSE         → Anthropic blog + Substack newsletter summaries
```

**Schedule:** 07:15 daily, Mon–Fri + Sun (Saturday excluded)  
**Runner:** Windows Task Scheduler  
**Day tracking:** `progress.json` — calculates current day from start date, logs each run

---

## Eval Results

*To be populated after first 5 runs.*

Planned eval approach (per Day 8 of the learning plan):

- **Unit evals:** Does each data source return non-empty output? Is the brief under 300 words?
- **Trajectory eval:** Did the agent call all four data sources before composing? Did it fall back correctly on failure?
- **LLM-as-judge rubric:** "Is the Meeting Context section actionable or just descriptive?" (binary, scored by Claude on a sample of 10 runs)
- **Golden set:** 10 synthetic inputs (calendar + Gmail snapshots) with known-good brief outputs, run on each code change

---

## Limitations

- No WhatsApp delivery — deferred; no stable free API for personal use
- `actual_mins_spent` per day requires manual entry; no automatic time tracking in v1
- Anthropic blog fetch is a simple HTML scrape — will break if page structure changes
- Gmail Substack filter catches all `@substack.com` senders, not a curated list; may surface low-signal newsletters
- No deduplication if the same Substack newsletter arrives across two days

---

## What I'd Do Next

1. **End-of-day updater** — a second lightweight script at 17:00 that prompts for `actual_mins_spent` and quiz score, appending to `progress.json`. Closes the tracking loop without friction.
2. **WhatsApp delivery** via Twilio sandbox — 2-hour addition once core agent is stable.
3. **Curated Substack list** — replace the domain-filter query with a sender allowlist so only high-signal newsletters (Latent Space, Simon Willison, Anthropic Engineering) surface.
4. **Langfuse instrumentation** — wire every run as a trace with tool-call spans. Makes Day 9's Langfuse hands-on a real exercise rather than a toy example.
5. **Self-improving brief** — after 21 days, analyse which sections were most read (via email open/click tracking) and trim the ones that weren't.

---

## What a PM Should Notice

This agent is a minimal augmented LLM loop: tools gather structured data, Claude adds the one thing tools can't — contextual prose that connects a meeting thread to a talking point, or a newsletter excerpt to today's learning topic. The 90-second read target is a forcing function on scope: every section that doesn't fit gets cut. That constraint is what makes it useful daily rather than occasionally. The architecture is deliberately simple for v1; the `What I'd Do Next` section is where the PM thinking lives.
