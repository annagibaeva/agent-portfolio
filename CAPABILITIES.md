# Agentic Capabilities

A map of what the agents in this portfolio actually do, and the mechanism behind each. Overview and build summaries: [README](./README.md).

## What the agent does live

| Capability | Where | How it's done |
|---|---|---|
| Intent routing | wismo-returns | Splits returns, WISMO and out-of-scope. Intent accuracy is reported separately, because a customer routed wrong can never be served right downstream |
| Tool orchestration and sequencing | Return-and-Exchange | lookup → eligibility → inventory → label, with a supervisor checking the trace supports what the reply claims |
| Retrieval and grounded generation | wismo-returns | Rules retrieved per ticket; the proposal must return cited rule IDs, and an uncited claim fails the gate |
| Clarifying questions | whatsapp, wismo-returns | A fact a rule needs but nobody established produces a question, not a guess. Scored as its own action class |
| Refusal and escalation | wismo-returns | Handoff is a first-class outcome with a logged reason, and handoff precision can fail the release |
| Structured extraction | business-state | Chat messages become typed events; anything failing the schema never reaches state |
| Transactional writes | whatsapp-commerce-agent | Hold, then idempotent commit, with a TTL and a reaper for abandoned holds |
| Deadline awareness | whatsapp-commerce-agent | A 24-hour reply window with a 2-hour margin, so the agent knows whether an escalation can still reach a human before promising one |
| Live channel integration | whatsapp-commerce-agent | WhatsApp Cloud API webhook receiver and send path |
| Scheduled autonomous runs | morning-briefing, competitive-intel | Cron-driven, with fallbacks so the brief sends even when a source is down |
| MCP servers | competitive-intel, meeting-prep | A DB-free MCP server with RSS and HTML fallback; in-process MCP tools for Calendar and Gmail |

## What makes the above believable

| Capability | Where | How it's done |
|---|---|---|
| Deterministic verification | wismo-returns, whatsapp | A gate with no model call in it. In whatsapp, a test asserts it can't even import the model path |
| Hallucination detection | payments-harness | A detector registry — canary, amount, action — plus a canary planted in the system prompt |
| Evidence grounding | Silent-failure-detector | Judge verdicts rejected unless the evidence span appears verbatim in the trace |
| Judge calibration | Silent-failure-detector | Confidence calibrated against ground truth, with per-severity thresholds: recall-first on Critical, precision-first on Low |
| Ablation | wismo-returns, Silent-failure-detector | Gate off versus on; heuristics alone versus heuristics plus judge |
| Generalisation testing | wismo-returns, Silent-failure-detector | A held-out paraphrase split, and ~15 transfer traces written without the generator templates |
| Reliability under repetition | payments-harness, Return-and-Exchange | pass^k at k=5, with safety tasks required to pass every run |
| Reproducibility | payments-harness | Cassette record and replay; the golden run replays green offline with no API key |
| Regression control | payments-harness | A pinned baseline with asymmetric tolerance: forgiving on noisy latency, near zero on correctness |
| Cost and latency accounting | payments-harness | Cost computed from token usage and gated at $0.075/run; latency p95 warns |
| Audit trail | wismo-returns, whatsapp | Structured run logs carrying the reason for every block |
| CI enforcement | payments-harness | Gates run in GitHub Actions and exit non-zero on failure |

## What these don't cover

Named because they're the questions I'd ask.

**Multi-turn repair.** Most of these are ticket-shaped: one request, one outcome. A customer who changes their story halfway through, or argues with a refusal, isn't modelled. That's the most common real conversation and the biggest gap here.

**The inline gate.** Everything here runs offline or before release. The hard version runs on the response path inside a latency budget, with a false-block rate someone owns and a shadow-to-enforce rollout.

**Retrieval at scale.** Grounding is against a handful of rules or a small policy set, not hundreds of prose documents that contradict each other and change weekly. Whether the approach survives that is the assumption I'd most want to test next.

**Memory across sessions.** Nothing here remembers a customer between conversations.
