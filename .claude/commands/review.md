---
description: Review agent code against agent-portfolio CLAUDE.md conventions
argument-hint: "[path or agent subdir, optional]"
---

# Agent Code Review

Review target: `$ARGUMENTS` (if empty, review uncommitted + staged changes via `git diff HEAD` and `git status`).

Review against the conventions in `CLAUDE.md` at the repo root. Be direct and opinionated — no hedging, no generic praise. If something is fine, don't mention it.

## What to check

**Runtime safety**
- Loop budgets: max turns / token caps present and logged?
- External side-effects (email send, PR open, calendar write, file writes outside repo) gated by explicit confirmation or dry-run mode?
- Confidence checks: low-confidence paths escalate rather than proceed?
- Boundary validation: user input, tool inputs, and model outputs validated before being acted on?

**Prompts & tools as assets**
- Are prompts in `prompts/*.md`, or inlined as f-strings? Flag inlined prompts.
- Tool schemas in `tools/`? Schema changes noted in commit/PR?

**Evals**
- Does the agent have `evals/` with ≥5 golden examples (happy path + ≥2 failure modes)?
- Are evals run on prompt/model changes, or only unit tests?

**Per-agent layout**
- `README.md`, `RUNBOOK.md`, `requirements.txt`, `prompts/`, `tools/`, `evals/` all present?
- One-command demo (`python main.py --demo`) wired up?

**Stack & style**
- Python, type hints on signatures, `from __future__ import annotations`?
- Default model `claude-sonnet-4-6`? If Opus is used, is there a one-line cost-vs-capability justification in the diff?
- Third-party deps justified in commit body?
- Secrets via env / secrets manager — never hardcoded or committed?

**Logging**
- Structured JSONL with `run_id` for multi-step pipelines?
- Human-readable trace summary per run (turns, tools, tokens, outcome)?

## Output format

Produce a single review with three sections — omit any section that's empty:

### Blockers
Things that must be fixed before merge. Reference file:line.

### Should-fix
Real issues that aren't blockers. Reference file:line.

### Nits
Small improvements. One line each.

End with a one-sentence verdict: ship / fix-then-ship / rework.
