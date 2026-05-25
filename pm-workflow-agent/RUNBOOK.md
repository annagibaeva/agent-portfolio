# RUNBOOK — pm-workflow-agent

## Inputs

| Source | Required | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` env var | yes | Loaded from environment or `.env`. Preflight fails if missing. |
| `prd-writer` skill | yes | Must be installed at `~/.claude/skills/prd-writer/SKILL.md`. Preflight fails if missing. |
| Product idea | yes | 1–3 sentence description. Passed via `--idea`, `--idea-file`, `--demo`, or stdin prompt. |
| Answers | no | Either interactive (default) or via `--answers-file` with `key: value` per line. Missing keys → `guess` sentinel → LOW CONFIDENCE in output. |

## Outputs

| Artifact | Path | Notes |
|---|---|---|
| PRD | `outputs/prd-<slug>-<run_id>.md` | Atomic write (`.tmp` + rename). Slug derived from idea, capped at 40 chars. |
| Run log | `logs/<run_id>.jsonl` | One JSON line per step (`intake`, `draft`) with status, tokens, output path. |
| Trace summary | stdout | `--- run <id> --- turns / tokens / outcome`. |
| Low-confidence banner | stdout | `!! LOW CONFIDENCE — review these sections:` followed by section headings. |

## Failure modes

| Failure | Detection | Behavior | Exit code |
|---|---|---|---|
| Missing API key | `agent.preflight()` | Print message, exit before any model call | 2 |
| Missing `prd-writer` skill | `agent.preflight()` | Print message, exit | 2 |
| Non-idea input | Intake turn returns `{"reject": "..."}`; `intake.parse_questions` raises `RejectedIdeaError` | No retry (model verdict, not parse failure). No PRD written. Logged as `status: rejected` with reason. | 3 |
| Malformed intake JSON | `intake.parse_questions` raises in validator | Retry the intake turn once. If still bad → `IntakeParseError`, exit | 1 |
| Malformed draft (no `markdown` fence) | `agent.extract_prd_block` raises in validator | Retry the draft turn once. If still bad → `DraftError`, exit | 1 |
| Token budget exceeded | Sum of usages > `agent.TOKEN_CAP` (100k) | `BudgetError`, no PRD written, logged as `budget_exceeded` | 1 |
| Low-confidence sections | `agent.low_confidence_sections(prd)` | PRD is still written. Banner printed. No exit failure — user reviews. | 0 |
| User interrupt | `KeyboardInterrupt` | Print "Interrupted — no PRD written" | 130 |

## Cost per run

Typical run: 2 Claude Sonnet 4.6 turns, ~5–15k input tokens (idea + system prompts + skill), ~2–5k output tokens.
Approximate cost: **$0.05–$0.20 per run**. Long ideas or repeated retries can push higher; the 100k token cap is the hard ceiling (~$0.50 worst case).

Live eval sweep (5 cases): $0.25–$1.00.

## Safety invariants

- Two stateless turns only. `MAX_TURNS = 10` per turn is a ceiling, not a target.
- `TOKEN_CAP = 100_000` enforced after the draft turn; run aborts before file write if exceeded.
- All file writes are atomic (`.tmp` + `os.replace`).
- No external side-effects beyond local file writes under `outputs/` and `logs/`.
- Confidence proxy: any section the model marks `LOW CONFIDENCE` triggers a visible banner. Per the agent-portfolio convention (`confidence < 0.8 → escalate`), the human reviewer is the escalation path here.

## Operational notes

- `outputs/` is gitignored. Test runs accumulate files there; periodic cleanup is fine.
- `logs/<run_id>.jsonl` is the source of truth for what happened in a run. Each entry has `run_id`, `step`, and timing.
- Prompt files live in `prompts/`. Edits there require running `python -m evals.run_live` before merging to catch quality regressions.
