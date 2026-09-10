# Agent Portfolio

**What this is.** A summary of the agents I build and the reliability work around them. Each solves a different customer problem; together they cover the agentic capabilities I've worked with. Every build has its own repo, and most have a PRD and a case study.

## The problem I build against

An agent talking to customers will sometimes be wrong. That's manageable.

The dangerous version is wrong *and* sounding right. "Yes, you've been refunded." "Your dispute has been filed." Nobody catches those. The customer believes it, the dashboard stays green because nothing on it measures this, and the team finds out weeks later from a chargeback or a regulator.

Those answers are expensive and hard to spot, and they don't come from a broken agent loop. The loop works. The problem sits between the agent and the customer, where most systems have nothing.

## Why I build this way

You can't prompt a model into never being wrong, so I stopped trying. A second piece of code sits between the model and the customer. The model proposes an answer; a gate checks it against written policy and decides whether it goes out. The gate contains no AI. It can only approve or block, and it never rewrites.

The trade-off is the point. A gate that blocks nothing isn't checking anything. A gate that blocks too much means paying for an agent that escalates everything anyway. Where you set it is a product decision, and it needs a number attached.

Mine: turning the gate on took hallucination from 10% to 0%, and deflection from 72% to 58%. Deflection is what a support org buys — tickets closed without a human. So safety cost fourteen points of the thing being paid for. That's the trade a CX leader has to sign, and it should be signed with the number visible rather than discovered later.

## The questions this portfolio answers

| Question | Build |
|---|---|
| How do you stop an agent giving a confident wrong answer, and what does that safety cost? | [wismo-returns](#wismo-returns-reliability-agent) |
| How do you decide whether a change is safe to ship? | [payments-harness](#payments-harness) |
| How do you find failures that already shipped looking successful? | [Silent-failure-detector](#silent-failure-detector) |
| Can the business owner change the agent's policy without an engineer? | [whatsapp-commerce-agent](#whatsapp-commerce-agent) |
| What does the agent check against when the truth lives in a chat thread? | [business-state](#business-state) |

---

## Where this applies

| Sector | The customer problem | Build |
|---|---|---|
| E-commerce, retail, marketplaces | Return policy is complex, so the agent tells customers they're refunded when they aren't. That creates a refund liability and a ticket a human has to unwind. | [wismo-returns](#wismo-returns-reliability-agent), [Return-and-Exchange](https://github.com/annagibaeva/Return-and-Exchange-agent) |
| Payments, BNPL, banking | The agent confirms a dispute that was never filed, or quotes a fee that doesn't exist. In a regulated setting that's an incident, not a bug. | [payments-harness](#payments-harness), [Silent-failure-detector](#silent-failure-detector) |
| SaaS, subscriptions | The agent confirms a cancellation that failed. The customer keeps getting billed while believing they cancelled. | [Silent-failure-detector](#silent-failure-detector) |
| Beauty, clinics, fitness | Booking rules exist for safety, not convenience. The agent books past a requirement the customer was never asked about. | [whatsapp-commerce-agent](#whatsapp-commerce-agent) |
| Chat commerce | Inventory truth lives in the chat thread, so the last unit gets sold twice. | [business-state](#business-state) |

The pattern is the same every time. The agent is fluent, the customer is satisfied, and something underneath is wrong.

---

## The calls I made

| Decision | Why | Built into | Read more |
|---|---|---|---|
| **Treat fabrication as its own severity class** | Accuracy can tolerate one honest miss. Fabrication can't. A made-up fee is a compliance event; a wrong answer is a bug. | payments-harness | [threshold rationale](https://github.com/annagibaeva/payments-harness/blob/main/docs/threshold-rationale.md) |
| **Pay for safety in deflection, deliberately** | 72% → 58%, published as a price rather than hidden. If a client won't pay it, better to know before deployment than after. | wismo-returns | [case study](https://github.com/annagibaeva/wismo-returns-reliability-agent/blob/main/docs/case-study.md) |
| **Make the success criteria ungameable first** | Hallucination, recall and handoff precision have to clear at once. Each one alone is gamed by answering everything or refusing everything. | wismo-returns | [win condition](https://github.com/annagibaeva/wismo-returns-reliability-agent#the-win-condition) |
| **Keep the model off the gate path** | Scoring is fully deterministic. No LLM decides ship or no-ship. An LLM judge is a deferred V2, advisory only. | payments-harness, whatsapp | [threshold rationale](https://github.com/annagibaeva/payments-harness/blob/main/docs/threshold-rationale.md) |
| **Hold policy as data, not code** | Rules live in JSON, each carrying the sentence it came from. Changing policy is an edit, not a deploy, so a non-engineer can own it. | whatsapp-commerce-agent | [PRD](https://github.com/annagibaeva/whatsapp-commerce-agent/blob/master/docs/PRD-whatsapp-commerce-agent.md) |
| **Publish the runs that failed** | The regression that caught me, plus a "what this does not demonstrate" table in each repo naming the assumption that would hurt most if false. | every build | [case study](https://github.com/annagibaeva/payments-harness/blob/main/docs/case-study.md) |

---

## The builds

Same four fields each: the problem, what I built, what it produced, and what to watch out for.

### [wismo-returns-reliability-agent](https://github.com/annagibaeva/wismo-returns-reliability-agent)

**Problem.** "Can I return this" is policy reasoning: return windows, final sale, electronics, defects, and rules that contradict each other. It's where an agent gets confidently wrong. "Yes, you've been refunded," said to someone outside the window, creates a refund the business never agreed to and a ticket a human has to unwind.

**Solution.** The agent resolves what it can ground in policy and hands off what it can't. Intent router → order lookup → rule retrieval → the model proposes an outcome with cited rule IDs → a deterministic gate runs four grounding checks plus a precedence check for conflicting rules → resolve or hand off, reason logged either way. Python, no framework. The point is to let you choose where you sit between automating everything and eating the wrong answers, and to know what the position costs.

**Output.** Three targets have to clear at once, because each alone is gameable: hallucination ≤ 2%, resolution recall ≥ 80%, handoff precision ≥ 85%.

| | Gate OFF | Gate ON |
|---|---|---|
| Hallucination | 10% | **0%** |
| Resolution precision | 81% | **100%** |
| Policy-error rate | 10% | **0%** |
| Resolution recall | 83% | 83% *(held)* |
| Deflection | 72% | **58%** *(the price)* |

**Watch-outs.** Measured against `--backend stub`, a deliberately naive offline proposer, so this shows the mechanism working rather than a real-model baseline. n=43, directional.

→ [case study](https://github.com/annagibaeva/wismo-returns-reliability-agent/blob/main/docs/case-study.md) · [architecture](https://github.com/annagibaeva/wismo-returns-reliability-agent/blob/main/docs/architecture.md) · [demo](https://github.com/annagibaeva/wismo-returns-reliability-agent/blob/main/docs/demo-script.md)

### [payments-harness](https://github.com/annagibaeva/payments-harness)

**Problem.** A team changes a prompt, a model version, or a temperature setting and ships on "we tested it." Nobody can say whether this release is safer than the last. In payments, an invented fee isn't a user-experience problem, it's a compliance one.

**Solution.** A release gate: every change runs the same benchmark and gets one PASS or FAIL. 19 labelled tasks over mock payments data, each run five times to catch behaviour that only appears intermittently, recorded to a cassette so the run replays identically offline. Deterministic scoring, a registry of hallucination detectors, a canary in the system prompt, enforced in GitHub Actions. Accuracy tolerates an honest miss; fabrication is zero-tolerance and blocks the release on its own. It turns "we tested it" into an artifact risk, compliance or a client can read without trusting the team that built it.

**Output.** One verdict plus a report and dashboard. The golden run replays green: accuracy 1.000, hallucination 0, cost $0.052.

The useful result is the red one. Temperature 0.0 → 1.0, the change a team makes to sound more natural, produced accuracy of **0.973, which passed**. The release failed anyway: the model intermittently invented a fee for a product that doesn't exist. A gate watching only accuracy ships that.

**Watch-outs.** Mock data, not a real ledger. 19 tasks is small. Latency warns rather than blocks, because a flaky blocking gate just gets ignored.

→ [PRD](https://github.com/annagibaeva/payments-harness/blob/main/docs/PRD-payments-assistant-reliability-harness.md) · [threshold rationale](https://github.com/annagibaeva/payments-harness/blob/main/docs/threshold-rationale.md) · [case study](https://github.com/annagibaeva/payments-harness/blob/main/docs/case-study.md) · [use cases + BRD framing](https://github.com/annagibaeva/payments-harness/blob/main/docs/use-cases.md)

### [Silent-failure-detector](https://github.com/annagibaeva/Silent-failure-detector)

**Problem.** Monday morning. 88% deflection, CSAT 4.3, 40,000 weekend conversations, dashboard green. A Friday deploy changed one tool's response format, and since then the agent has been confirming disputes it never filed. Around 200 customers were told their dispute was filed. Zero thumbs-down. Nothing on any chart moved.

**Solution.** Read the traces after the fact, find the ones that look successful but aren't, group them, rank by damage, and hand the owner the one guardrail to ship first. Cheap heuristics run first and produce signals rather than verdicts: a tool returned `success: false` while the reply said otherwise, retrieval scored below threshold, the routed intent doesn't match the real one. An LLM judge then decides, and every verdict must quote an evidence span that appears verbatim in the trace or it's discarded. Failures are grouped by structured signature and ranked by frequency × severity, so the incident surfaces from your own tooling rather than from a regulator.

**Output.** A ranked report with per-failure-mode precision, recall and F1, a confusion matrix, an ablation comparing heuristics alone against heuristics plus judge, and one guardrail with before/after numbers.

**Watch-outs.** Traces are synthetic and I wrote both the generator and the detector, so circularity is the central risk — countered with phrasing from a different model than the judge, a phrasing set frozen before detector work, ~15 hand-written transfer traces, and a ~80%-clean dataset with hard negatives. Weak where a tool returns success but the outcome is semantically wrong.

→ [case study](https://github.com/annagibaeva/Silent-failure-detector/blob/main/docs/case-study.md)

### [whatsapp-commerce-agent](https://github.com/annagibaeva/whatsapp-commerce-agent)

**Problem.** A salon's booking policy lives in the owner's head and a Google Doc. One rule is a safety rule: a first colour appointment needs a patch test 48 hours ahead, because of allergic reactions. An agent that books it 20 hours out, never asking whether it's a first colour visit, has created a safety problem — and a small business can't keep an engineer on hand to encode rules like that.

**Solution.** Policy as data the owner edits, and a gate structurally incapable of doing anything but blocking. Five rules in a JSON file, each with a condition, an outcome, and the sentence from the salon's own document that justifies it; nothing in that file is executed. Two properties are enforced by the build rather than by discipline: the gate can't reach a model, because it imports only rules and read-only calendar views and a test asserts the import graph, and its result type has no field for a corrected booking. A fact nobody established produces a question, not a guess. Bookings are two-phase, a hold then an idempotent commit.

**Output.** 20 cases run with the gate on and off, so the difference is visible. 164 tests pass. Live WhatsApp Cloud API webhook and send path wired up.

**Watch-outs.** The 48-hour rule is my assumption from standard practice, never confirmed with a salon, and several cases depend on it. The live thread hasn't been run. At 20 cases, one case moves a percentage five points. The biggest assumption is that policy elsewhere is rule-shaped like this.

→ [PRD](https://github.com/annagibaeva/whatsapp-commerce-agent/blob/master/docs/PRD-whatsapp-commerce-agent.md) · [live-thread runbook](https://github.com/annagibaeva/whatsapp-commerce-agent/blob/master/docs/live-thread-runbook.md)

### [business-state](https://github.com/annagibaeva/business-state)

**Problem.** Sellers who take orders over chat keep the truth about their stock in the conversation. Two customers ask for the last unit a minute apart and both get a yes. There's nothing for an agent to check against, because the only record is a thread.

**Solution.** Turn the messages into typed events, project them into live inventory state, and have the agent answer and reserve against that state rather than against the conversation. The schema is the boundary: an event that doesn't validate never reaches state, so a misread message can't silently become inventory. State is rebuilt by replaying events, which means it can be audited and reconstructed.

**Output.** 159 tests pass. A demo UI, and an offline command that runs the exit criteria with no network call.

**Watch-outs.** The live extraction path has never run — no API key, so the suite passes against a fake extractor. That proves the wiring and that the schema rejects bad input in principle, not that it survives real model output.

---

## Everything else

- **[Return-and-Exchange-agent](https://github.com/annagibaeva/Return-and-Exchange-agent)** — retail returns agent orchestrating tools against mock systems of record. Tool sequencing and identity refusal under adversarial input; the build the grounding gate came out of. [Case study](https://github.com/annagibaeva/Return-and-Exchange-agent/blob/main/docs/case-study.md).
- **[share-of-answer-monitor](https://github.com/annagibaeva/share-of-answer-monitor)** *(private)* — 56 buying questions × 3 answer engines × 7 days, SEA market. Reports the noise floor next to the trend; where the two are comparable, the trend line isn't interpretable.
- **[superset-fixes-showcase](https://github.com/annagibaeva/superset-fixes-showcase)** — Docker demos of security fixes to my Apache Superset fork. 7 merged PRs, built with Devin; I owned the design calls.
- **[morning-briefing-agent](https://github.com/annagibaeva/morning-briefing-agent)** — daily brief from Calendar, Gmail and AI news. The first one. Scheduled runs, graceful degradation.
- **[meeting-prep-agent](https://github.com/annagibaeva/meeting-prep-agent)** — one-page brief per meeting via the Claude Agent SDK, with in-process MCP tools.
- **[tau2-bench-sierra](https://github.com/annagibaeva/tau2-bench-sierra)** *(fork)* — Sierra's τ²-bench, used to score the returns agent against an external standard.

**Also in this repo**, earlier agents kept for the record: [competitive-intel-agent](./competitive-intel-agent) (weekly competitor changelog diff via a DB-free MCP server; 42 unit tests, 7 golden evals) · [pm-workflow-agent](./pm-workflow-agent) (idea → ≤6 clarifying questions → PRD) · [data-quality-agent](./data-quality-agent) · [meeting-prep-agent](./meeting-prep-agent) · [morning-briefing-agent](./morning-briefing-agent). Conventions: [CLAUDE.md](./CLAUDE.md).

---

## Capabilities

The full map of agentic capabilities and the mechanism behind each — routing, tool use, retrieval, refusal, transactional writes, evals, release gating — plus what these builds don't cover yet: **[CAPABILITIES.md](./CAPABILITIES.md)**.

## On the numbers

Sample sizes are small: 43 tickets, 19 benchmark tasks, 20 salon cases. At that scale a percentage is a handful of events, so intervals are wide and the reports carry them where they're computed. Treat these as directional.

Each README says which claims were checked by running a command and which weren't. business-state opens with the two things it never ran. whatsapp-commerce-agent has a table of what it does *not* demonstrate. That's deliberate: a portfolio that reports only its green runs is the same failure mode these builds exist to catch.

**In progress:** a harder version of the wismo benchmark. The corpus grew to 65 tickets with fault and safety tiers, the success criteria grew from three clauses to five, every metric now carries a 95% confidence interval, and there's an English/Spanish split. Under the tighter definition the agent currently fails two clauses. That result will be published as-is.
