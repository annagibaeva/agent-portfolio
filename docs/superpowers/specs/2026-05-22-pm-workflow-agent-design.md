# PM Workflow Agent — Design

**Author:** Anna Gibaeva
**Status:** Draft
**Last updated:** 2026-05-22

## 1. Purpose

Turn a raw product idea into a structured PRD draft. The agent ingests an idea,
asks clarifying questions to fill known information gaps, then drafts a PRD using
the existing `prd-writer` Claude Skill. Metrics and open questions are sections
*inside* that PRD (§4 and §9 of the prd-writer template), not separate artifacts.

## 2. Verification spike (completed 2026-05-22)

Before designing further, the riskiest assumption — that the Agent SDK loads and
invokes a user-scope skill — was tested live:

- SDK version: `claude-agent-sdk` 0.1.70.
- `ClaudeAgentOptions.skills=["prd-writer"]` auto-wires `Skill(prd-writer)` into
  `allowed_tools` and defaults `setting_sources` to `["user","project"]`.
- Live `query()` confirmed the agent invoked `Skill` with `{'skill': 'prd-writer'}`.
- `ResultMessage.usage` exposes token counts for budget tracking.

**Result: passed.** The project-local skill-copy fallback is NOT needed. The
agent depends on the user-scope skill at `~/.claude/skills/prd-writer/`.

## 3. Interaction model

Interactive CLI loop, two **stateless** `query()` calls (not a persistent client):

1. **Ingest** — idea via `--idea "..."`, `--idea-file <path>`, or interactive prompt.
2. **Intake turn** — `query()` #1: agent compares the idea to a fixed coverage
   checklist and returns clarifying questions for gaps only, as **strict JSON**.
3. **Interactive loop** — `main.py` prints each question, collects answers via
   `input()`; user may type `skip` or `guess` per question.
4. **Draft turn** — `query()` #2: fresh context = `idea + all Q&A`. Agent invokes
   the `prd-writer` skill and returns the PRD as a single fenced markdown block.
5. **Write + report** — `main.py` writes the PRD to `outputs/`, prints the path,
   emits the JSONL log + trace summary.

The two turns are stateless: nothing is held open across the human pause.

## 4. Architecture

```
pm-workflow-agent/
  main.py            CLI entry; pre-flight checks; intake loop; file write; orchestration
  agent.py           Two stateless query() calls; ClaudeAgentOptions; prompt loading
  intake.py          Coverage checklist + JSON schema for clarifying questions
  logger.py          JSONL run log + human-readable trace summary
  prompts/
    system.md        Role, safety rules, "produce PRD as a markdown block, no file tools"
    intake.md        Gap-analysis instructions; strict-JSON output contract
  evals/             >=5 golden examples (happy path + failure modes)
  outputs/           Generated PRD files (kebab-case .md)
  prd-template.docx  (existing — reference only)
  README.md  RUNBOOK.md  requirements.txt
```

No `tools/` directory. `main.py` writes the PRD file deterministically — the
agent never calls a file tool.

**Coverage checklist** (`intake.py`), one question max per item (~6 total):
problem, primary persona, top success metric + target, dependencies,
scope / non-goals, target release.

## 5. Critical design decisions (folded-in fixes)

1. **Skill loading — verified, not assumed.** See §2. `agent.py` still asserts
   at startup that `skills=["prd-writer"]` resolves; fails loud otherwise.
2. **Two stateless `query()` calls** instead of a persistent `ClaudeSDKClient`
   held across the `input()` pause — no long-lived session state to desync.
3. **Strict-JSON intake output.** Turn 1 returns a single fenced ```json block:
   `{"questions": [{"id","checklist_item","text"}]}`. `main.py` parses JSON, not
   prose. Empty `questions` array → skip the loop, go straight to drafting.
4. **No MCP write tool.** The draft turn returns the PRD as one fenced markdown
   block; `main.py` writes it. `system.md` overrides the skill's
   "write the file yourself" instruction. Removes the path-escape risk and an
   entire MCP server.
5. **Non-interactive mode for evals.** `--answers-file <path>` supplies pre-baked
   answers so the eval runner uses the same code path without `input()`.
   `--demo` is a thin wrapper over a bundled idea + answers file.

## 6. Operational hardening (should-fixes, ranked by expected impact)

Ranked by severity x likelihood — highest first:

1. **Pre-flight checks.** Before any model call, verify `ANTHROPIC_API_KEY` is
   set and the `prd-writer` skill resolves. Misconfig fails fast with a clear
   message, never mid-conversation. *(Blocks every run when wrong; cheap.)*
2. **Windows UTF-8 encoding.** Reconfigure stdio to UTF-8; read `--idea-file` as
   UTF-8 explicitly. The sibling meeting-prep agent already hit the cp1252
   default. *(Near-certain to bite; crashes the run.)*
3. **Budget enforcement.** Set `max_turns=10` in `ClaudeAgentOptions`; sum
   `ResultMessage.usage` tokens across both turns; abort with a clear message if
   the 100k cap is exceeded. Log turns + tokens per portfolio convention.
   *(Runaway cost/loops; high severity.)*
4. **Atomic write + Ctrl-C handling.** Catch `KeyboardInterrupt`, log the partial
   run, exit clean. Write the PRD to a temp file then `os.replace()` — only after
   the draft turn fully succeeds. Never a half-written PRD. *(Data integrity.)*
5. **Question cap.** Bound intake to one question per checklist item (~6 max) so
   a vague idea cannot produce an unusable 20-question interrogation.
6. **Filename collisions.** Suffix the kebab slug with the `run_id` timestamp;
   never overwrite an existing PRD.
7. **Confidence < 0.8 surfacing.** `CLAUDE.md` says escalate. With no escalation
   channel, "escalate" = print a prominent warning listing low-confidence
   sections — not silently buried in §9.
8. **External skill drift.** `prd-writer` lives outside this repo and can change.
   Documented as a dependency in `RUNBOOK.md`.

## 7. Data flow & errors

- Empty / garbage idea → agent asks for a real idea instead of drafting.
- Intake turn returns malformed JSON → one retry, then abort with a clear error.
- Draft turn returns no fenced markdown block → one retry, then abort.
- All branches log to JSONL with a `run_id` (`run-<timestamp>-<hex>`).

## 8. Testing

`evals/` with >=5 golden examples, run via `--answers-file`:

1. Complete idea — few/no questions, clean PRD.
2. Vague idea — many questions (capped at ~6).
3. Non-idea / garbage — rejected, no PRD written.
4. Idea with heavy dependencies — §6 Dependencies populated.
5. Run exercising `skip` / `guess` answers.

Diff PRD outputs across runs — do not rely on pass/fail alone.

## 9. Conventions & constraints

- Model: `claude-sonnet-4-6`. Python-first, type hints, `from __future__ import annotations`.
- Max 10 turns / 100k tokens per run; both logged.
- File writes confined to `outputs/` inside the repo — no external side-effect
  confirmation required.
- Ships with `README.md`, `RUNBOOK.md`, `requirements.txt`, `prompts/`, `evals/`,
  and a one-command demo: `python main.py --demo`.

## 10. Open questions

| Question | Resolution by |
|---|---|
| Should `--idea-file` accept the answers inline (front-matter) to skip the loop entirely? | Before implementation plan |
| Retry count for malformed model output — 1 or 2? | Implementation |
