# pm-workflow-agent

Turns a one-line product idea into a structured PRD. Two stateless Claude
Agent SDK turns: an **intake** turn asks ≤6 clarifying questions against
a fixed coverage checklist, then a **draft** turn calls the `prd-writer`
skill to produce a fenced markdown PRD. Sections lacking confident input
are flagged `[LOW CONFIDENCE]` rather than hallucinated.

## Quick start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
python main.py --demo
```

The demo runs a bundled TaskFlow idea with pre-supplied answers and
writes the PRD to `outputs/prd-<slug>-<run_id>.md`.

## Modes

| Flag | Behavior |
|---|---|
| `--demo` | Bundled idea + complete answers. No prompts. |
| `--idea "..."` | Idea on the CLI. Asks clarifying questions interactively. |
| `--idea-file path.txt` | Idea read from a file. Interactive answers. |
| `--idea ... --answers-file ans.txt` | Idea + pre-supplied answers (`key: value` per line). Non-interactive. Missing keys become `guess` and trigger LOW CONFIDENCE markers. |

Answer keys must match the coverage checklist: `problem`, `persona`,
`metric`, `dependencies`, `scope`, `release`.

## Testing

```bash
python -m pytest --tb=short -q          # all 24 tests including offline evals
python -m pytest evals/test_offline.py  # just the eval pipeline checks
```

Offline tests stub `agent.run_intake` and `agent.run_draft`, so they
verify pipeline logic (parsing, low-confidence detection, budget
enforcement, atomic write) without API cost.

## Live evals

```bash
python -m evals.run_live              # diff against checked-in goldens
python -m evals.run_live --update     # overwrite goldens
python -m evals.run_live --case <id>  # one case only
```

Run before any prompt or model change. Approximate cost: $0.25–$1.00 per
full sweep. Goldens live in `evals/goldens/`.

## Project layout

```
pm-workflow-agent/
├── main.py              CLI entry point; orchestrates intake -> draft
├── agent.py             Agent SDK wrapper with retry-once and budget cap
├── intake.py            Coverage checklist + strict-JSON question parsing
├── logger.py            JSONL run logger + trace summary
├── prompts/             Versioned system + intake prompts (no inline strings)
├── evals/               5 golden cases, offline pytest, live runner
├── tests/               Unit tests
└── outputs/             Generated PRDs (gitignored)
```

See `RUNBOOK.md` for inputs, outputs, failure modes, and cost per run.
