# Agent Portfolio

A portfolio of 10 agents exploring different patterns: tool use, MCP servers, scheduled runs, multi-agent orchestration, and evaluation. Each project is a standalone subfolder.

## Projects

1. **Morning Briefing Agent** — you already have a version. Rebuild it properly: Claude Code + Gmail MCP + Google Calendar MCP + a news fetch tool. Success metric: time-to-read-brief under 90 seconds.

2. **Meeting Prep Agent** — pulls attendees from calendar, recent emails with them, LinkedIn context (manual paste is fine), prior meeting notes from Notion/Drive. Output: one-page brief with talking points and open threads.

3. **PM Workflow Agent** — ingests a product idea, produces a PRD draft using your PM OS templates, suggests metrics, lists open questions. Uses Claude Skills to load your PRD template.

4. **Competitive Intel Agent** — scheduled run: watches 5–10 competitor domains / changelogs / release notes, surfaces weekly diff with PM-relevant commentary. Uses a custom MCP server for changelog parsing.

5. **Data Quality Agent** — point it at a CSV or a database connection, it profiles the data, flags issues (nulls, outliers, schema drift), drafts a data-readiness memo. Directly plays your Mars "fix data before AI" muscle.

6. **Job Market Agent** — scrapes/queries agent-PM job listings in Singapore, scores them against your criteria (remote-friendly, local hours, agent focus, stage), drafts tailored cover-letter starting points.

7. **GitHub Portfolio Reviewer Agent** — a subagent harness in Claude Code. Given a repo, it reviews README quality, test coverage, doc-code alignment, and produces a PM-style readiness report. You'll use it on your own portfolio.

8. **Multi-agent Research Crew** — LangGraph or CrewAI. Topic in, research brief out. Orchestrator + researcher + critic + writer subagents. This is your multi-agent showcase piece.

9. **Agent Evaluation Harness** — not an agent, a tool for evaluating agents. Runs a golden set against one of your agents above, logs to Langfuse, posts a scorecard to GitHub on each PR. This is the artefact that most clearly signals "I understand productionisation."

10. **Snapshot V2 / PM OS agent** — pick one of your existing side projects (Snapshot school finder or PM OS) and add an agentic layer. Shows you can ship *and* then agent-ify an existing product.
