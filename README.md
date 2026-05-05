# Agent Portfolio

A portfolio exploring different agent patterns: tool use, MCP servers, scheduled runs, multi-agent orchestration, and evaluation. Each project is a standalone subfolder.

## Status

| # | Project | Status | Notes |
|---|---|---|---|
| 1 | [Morning Briefing Agent](./morning-briefing-agent) | **Built** | Daily 07:15 brief; Calendar + Gmail + news fetch; Claude composes Meeting Context + AI Pulse. |
| 2 | [Meeting Prep Agent](./meeting-prep-agent) | **Built** | Per-meeting one-page brief via Claude Agent SDK; in-process MCP tools for Calendar/Gmail/manual context. |
| 3 | PM Workflow Agent | Planned | Idea → PRD draft using PM OS templates loaded as Claude Skills. |
| 4 | Competitive Intel Agent | Planned | Scheduled diffs across competitor changelogs via custom MCP server. |
| 5 | Data Quality Agent | Planned | CSV / DB profiling → data-readiness memo. |
| 6 | Job Market Agent | Planned | Singapore agent-PM listings, scored against personal criteria. |
| 7 | GitHub Portfolio Reviewer Agent | Planned | Subagent harness; README / test / doc-code review with PM-style readiness report. |
| 8 | Multi-agent Research Crew | Planned | LangGraph or CrewAI; orchestrator + researcher + critic + writer. |
| 9 | Agent Evaluation Harness | Planned | Golden-set runner, Langfuse logging, GitHub PR scorecard. |
| 10 | Snapshot V2 / PM OS agent | Planned | Agentic layer on top of an existing side project. |

## Conventions

Shared working-style and safety rules live in [CLAUDE.md](./CLAUDE.md). Every agent ships with a `README.md`, a `RUNBOOK.md`, `requirements.txt`, and (when applicable) `prompts/`, `tools/`, and `evals/`.

## Running anything here

Each agent has its own quick-start in its README. None of them share a Python environment — install per-agent.
