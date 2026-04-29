# Agent Portfolio — Working Style

Shared conventions for agents I develop in this directory.

## Communication
- Always surface the main trade-off, not just the upside.
- Flag assumptions explicitly so I can correct them early.
- Propose structure before writing code on non-trivial tasks.
- Call out what you're *not* doing and why.

## Language & Stack
- Python-first. Official `anthropic` SDK and `claude-agent-sdk`.
- Default model: `claude-sonnet-4-6`. Using Opus requires a one-line justification (cost vs. capability) in the PR or commit.
- Type hints on all signatures. `from __future__ import annotations` at top.
- Prefer stdlib. Third-party deps require justification in the commit body.

## Agent Runtime
- Max 10 turns and 100k tokens per run unless justified. Log both.
- Every external side-effect (email send, PR open, calendar write, file write outside the repo) requires explicit confirmation OR a logged dry-run mode.
- Confidence < 0.8 → escalate, don't proceed.
- Validate at boundaries: ingress (user input), tool inputs, and model outputs before acting on them.

## Prompts & Tools as Assets
- Prompts live in `prompts/*.md`, versioned. No prompt strings inline in agent code.
- Tool schemas live in `tools/`. Schema changes require a note in the PR body.

## Evals
- Every agent has `evals/` with ≥5 golden examples: happy path + 2 failure modes minimum.
- Run evals before any prompt or model change. Diff outputs — don't just check pass/fail.
- A green test suite ≠ correct behavior. If tests pass but eval output looks wrong, **stop** and report.

## Per-Agent Layout
Each agent subdirectory ships with:
- `README.md` — what it does, how to run
- `RUNBOOK.md` — inputs, outputs, failure modes, approximate cost per run
- `requirements.txt`
- `prompts/`, `tools/`, `evals/`
- One-command demo: `python main.py --demo`

## Logging
- Structured JSONL with a `run_id` for every multi-step pipeline.
- Each run also emits a human-readable trace summary: turns used, tools called, tokens, outcome.

## Secrets
- Environment variables or a secrets manager. Never hardcoded, never committed.
