# PRD: Manager Visibility Suite

**Author:** TBD
**Status:** Draft
**Last updated:** 2026-05-25
**Target release:** v3.1 (post-Q2, separate from v3.0 milestone — see Risks)

## 1. Summary
TaskFlow is the Goldilocks tool for engineering-led teams, but today it treats everyone on a team the same way — a manager gets the same views as an IC. That's fine when a team has 5 people; it falls apart at 50. This feature adds a dedicated manager experience: a team workload view, cross-project dependency tracking, and exportable status reports — so managers can do their jobs inside TaskFlow instead of exporting data to spreadsheets or building shadow dashboards in Notion.

## 2. Problem & Users

- **Primary persona:** Engineering manager or team lead at a 50–500-person company, overseeing 4–12 direct reports across 1–3 active projects
- **What they do today:** Export task lists to CSV, build manual status updates in Google Sheets or Notion, chase individuals on Slack for blockers — all outside TaskFlow
- **Evidence the problem is real:**

> LOW CONFIDENCE
- No direct user research available. Problem inferred from product positioning and competitive gap analysis. Recommend 5+ manager interviews before moving to In Review status.

- **Top 3 use cases:**
  1. Weekly: "What is my team actually working on this week and who is blocked?" (high frequency)
  2. Weekly: "I need to send a status update to my skip-level — what shipped, what slipped?" (high frequency)
  3. Occasional: "Two projects share the same two engineers — will they conflict next sprint?" (medium frequency)

## 3. Goals & Non-Goals

**Goals**
- Managers can generate a team status report inside TaskFlow without touching a spreadsheet
- Managers can see workload distribution across direct reports in a single view
- Managers can identify cross-project dependency conflicts before they cause slippage

**Non-Goals**
- Performance management, 1:1 tooling, or HR workflows — not a people tool
- Replacing the Advanced Reporting dashboard (v3.0 scope); this is additive, not a redesign
- Mobile-first experience (desktop only for v1)
- Time tracking or capacity planning beyond task-count heuristics

## 4. Success Metrics

> LOW CONFIDENCE
All targets below are estimates. Validate against baseline analytics before committing.

- **North-star:** Manager-role DAU / total manager seats ≥ 40% (up from an assumed ~15% today — verify in analytics.taskflow.io)
- **Guardrail 1:** Overall retention rate must not drop below current 85%
- **Guardrail 2:** P95 page load for the workload view ≤ 2s under normal load
- **Proxy:** "Export to CSV/Sheets" events from manager accounts decrease by ≥ 30% within 60 days of GA

## 5. Requirements

### Must-have (P0)
- **Team Workload View:** A manager can see all open tasks assigned to each of their direct reports, grouped by assignee, filtered by project and date range.
  - *Acceptance:* Given a manager with 6 direct reports across 2 projects, when they open the workload view, they see each report's open tasks with status, due date, and project label — no more than 2 clicks from the main nav.
- **Blocker Surfacing:** Blocked tasks are visually distinguished (e.g., distinct status badge) and sortable to the top of the workload view.
  - *Acceptance:* A task marked "Blocked" by any team member appears in the manager's view with a "Blocked" indicator within 60 seconds of the status change.
- **Status Report Export:** A manager can generate a plain-text or Markdown summary of the week's completions, in-progress work, and blockers for their team, copyable to clipboard.
  - *Acceptance:* Report covers a selectable date range, includes completed and in-flight tasks with owner names, and can be copied to clipboard in ≤ 3 clicks.

### Should-have (P1)
- **Cross-Project Dependency View:** A manager can see tasks marked as dependencies that span two or more projects their team contributes to, with a visual indicator if the upstream task is at risk (overdue or blocked).
  - *Acceptance:* If Task B in Project X depends on Task A in Project Y, and Task A is overdue, the dependency view flags this in the manager's dashboard.
- **Manager Role Designation:** Admins can assign a "Manager" role to any user; that role unlocks the workload and dependency views scoped to their direct reports only.
  - *Acceptance:* A manager cannot see workload data for teams they don't manage; an admin can assign/revoke the role without engineering involvement.

### Nice-to-have (P2)
- Scheduled email digest (weekly) summarizing team workload to the manager's inbox
- Workload heatmap view (by-day task distribution across the team)
- Slack notification when a direct report marks a task as blocked

## 6. Dependencies

- **Internal — Advanced Reporting Dashboard (v3.0, blocking):** The data model changes in v3.0 reporting must ship before Manager Visibility Suite goes to beta; confirm schema compatibility with Sarah Chen before implementation begins.
- **Internal — Custom Workflow Builder (v3.0, non-blocking):** Custom statuses (e.g., "Blocked", "In Review") need to map correctly to the workload view's status logic. Non-blocking for beta, blocking for GA.
- **Internal — Permissions/Roles system (blocking):** Manager role designation requires an update to the existing role model. Scope with Sarah Chen in the first sprint.
- **External — None identified.** No third-party integrations required for v1.

All blocking dependencies must resolve before Manager Visibility Suite enters beta.

## 7. UX

> LOW CONFIDENCE
No Figma links available yet. The following flows are placeholders — Marcus Rivera (designer) needs to own this section before In Review.

**Key flows to design:**
1. Manager lands on team dashboard → sees workload grid → clicks into a blocked task
2. Manager opens "Status Report" → selects date range → copies report to clipboard
3. Admin assigns Manager role to a user in Settings → user gains access to manager views
4. Manager views cross-project dependency tab → sees at-risk upstream task flagged in red

Figma workspace: figma.com/team/taskflow

## 8. Technical Notes & Rollout

> LOW CONFIDENCE
Technical details are speculative; confirm with Sarah Chen before sprint planning.

- **Data model:** Likely requires a `manager_relationships` join table (manager_user_id → report_user_id) and a new `manager` role enum value. All migrations must be reversible per DB rules.
- **API:** New endpoints under `/api/v2/manager/` — workload summary, dependency graph, report export. Standard pagination (default 50, max 200). No raw SQL; use the ORM.
- **Performance:** The workload view aggregates across multiple projects; query planner review required. Index `assignee_id` and `project_id` on the tasks table if not already present.
- **Feature flag:** `manager_visibility_suite_enabled` — default `false`. Enable per-account for beta.
- **Rollout plan:**
  1. Internal dogfood (1 week) — TaskFlow's own eng managers use it
  2. Closed beta (2–3 weeks) — 10–15 manager-heavy accounts, recruited by Jordan Park
  3. GA — all accounts; announce in changelog, in-app tooltip for newly eligible manager-role users, and a "What's new" email to admins
- **Comms:** Jake (DevOps) needs deployment heads-up 1 week before each phase. Maria (QA) runs regression suite before GA.

## 9. Risks & Open Questions

| Risk / Question | Owner | Resolution by |
|---|---|---|
| No confirmed user research backing the problem statement — solution may miss the mark | Jordan Park | Before design kickoff (aim for 2026-06-08) |
| All success metric targets are guesses — baseline manager DAU unknown | Priya Sharma | Pull from analytics.taskflow.io before PRD moves to In Review |
| v3.0 Advanced Reporting schema may not be finalized in time for a v3.1 target | Sarah Chen | Confirm v3.0 ship date and schema freeze by 2026-06-01 |
| "Manager role" definition is fuzzy — does a PM count? A team lead without direct reports? | Jordan Park | Define persona precisely before requirements are locked |
| Cross-project dependency view complexity may be underestimated — could slip to v3.2 | Sarah Chen | Spike (2 days) to estimate before committing to P1 |
| Target release listed as v3.1; if Jordan wants this in v3.0 Q2, scope must shrink significantly | Jordan Park | Alignment conversation needed before 2026-06-01 |
