# PRD: Bulk-Edit Toolbar for Task Lists

**Author:** TBD
**Status:** Draft
**Last updated:** 2026-05-25
**Target release:** v3.1 / Q3 2026

## 1. Summary
TaskFlow users who manage large backlogs — 20+ tasks at a time — currently have no way to update status, assignee, or due date across multiple tasks in one action. They resort to tedious one-by-one edits or workarounds like CSV exports. This feature adds a contextual bulk-edit toolbar to list views, letting users select any number of tasks and apply changes in a single operation. It ships in v3.1, built on top of the Bulk Operations API v2 landing in v3.0, and targets teams that have already outgrown lightweight tools but don't want Jira's overhead.

## 2. Problem & Users
- **Primary persona:** Project leads and team admins at mid-market companies (50–500 employees) managing engineering or cross-functional backlogs of 20+ tasks
- **Current workaround:** Users edit tasks one at a time, or export to a spreadsheet, make changes offline, and re-import — a multi-step, error-prone flow
- **Evidence the problem is real:** TBD — open question; recommend pulling support tickets and session recordings filtered to "list view, multiple task interactions" to quantify frequency

> LOW CONFIDENCE
- **Top 3 use cases and frequency:**
  1. Sprint/milestone kickoff: reassigning a batch of tasks to a new owner when someone joins or leaves a team (likely weekly for active teams)
  2. Status sweep: moving a block of completed tasks from "In Progress" to "Done" after a release (likely per sprint / bi-weekly)
  3. Due-date shift: pushing out a group of tasks when a milestone slips (likely monthly per team)
  *(Frequency estimates are assumptions — validate against analytics before lock-in)*

## 3. Goals & Non-Goals
**Goals**
- 30% of weekly bulk-eligible sessions (sessions where a user visits a list with 20+ tasks) use the bulk-edit toolbar within 60 days of GA
- Zero increase in task-update error rate (server-side validation errors, accidental overwrites) versus baseline single-edit flow

**Non-Goals**
- Bulk-deleting or bulk-archiving tasks (out of scope for v3.1; separate safety review needed)
- Bulk editing custom fields beyond status, assignee, and due date
- Bulk edit from Board or Timeline views — list view only in v3.1
- Mobile/native app support — web only

## 4. Success Metrics
- **North-star:** 30% of weekly bulk-eligible sessions include at least one bulk-edit action within 60 days of GA
- **Guardrail — task update error rate:** must not increase vs. pre-launch baseline (measure via API error responses on PATCH /tasks)
- **Guardrail — p95 bulk-update latency:** bulk operations on up to 100 tasks must complete in ≤ 3 s (ties to Bulk API v2 SLO)
- **Guardrail — single-edit flow regression:** time-on-task for single edits must not increase (toolbar must not clutter the default list UX)

## 5. Requirements

### Must-have (P0)
- Users can select multiple tasks via checkbox (individual click) or shift-click range selection in any list view
- A toolbar appears contextually when ≥ 2 tasks are selected, showing count of selected tasks and actions: Set Status, Set Assignee, Set Due Date
- Each action opens a focused picker (status dropdown, member picker, date picker); on confirm, the change is applied to all selected tasks via Bulk Operations API v2
- Partial failures are surfaced clearly: "18 of 20 tasks updated. 2 failed — [view details]" with task-level error detail
- Deselect all / cancel clears selection and dismisses the toolbar without side effects
- **Acceptance criterion:** A user selects 25 tasks, sets status to "Done," and all 25 tasks reflect the new status within 3 s with no page reload required

### Should-have (P1)
- "Select all" action that selects every task in the current filtered/sorted view (not just visible page)
- Undo support: bulk edits are reversible via Ctrl+Z / Cmd+Z for up to 30 seconds post-action
- Keyboard shortcut to open the bulk toolbar when tasks are selected (e.g., `B`)
- **Acceptance criterion:** Selecting all tasks in a 200-task filtered view and applying a due-date change completes within the 3 s SLO

### Nice-to-have (P2)
- Saved "bulk action templates" — common combinations (e.g., "sprint close-out: set status Done + clear assignee") reusable across sessions
- Bulk-edit history entry in the activity feed: "Jordan bulk-updated 25 tasks"

## 6. Dependencies
- **Internal — Bulk Operations API v2** (v3.0, shipping Q2 2026): **BLOCKING for GA.** Toolbar must not ship before API v2 is in production. Coordinate with Sarah Chen's team on endpoint contracts, rate limits, and partial-failure response shape.
- **Internal — Design system / component library:** Checkbox selection patterns and toolbar component need sign-off from Marcus Rivera to ensure consistency with existing list components. Non-blocking if done in parallel during design phase.
- **Internal — Feature flag infrastructure:** Toolbar ships behind a flag for internal → beta → GA rollout. Non-blocking; flag infra already exists.
- **External:** None identified.

## 7. UX
Figma file: figma.com/team/taskflow *(link to specific frame TBD — Marcus to create)*

Key flows:
1. **Selection:** User hovers a list row → checkbox appears. Click to select. Shift-click to range-select. Toolbar rises from the bottom of the list view showing "N tasks selected" + action buttons.
2. **Apply action:** User clicks "Set Status" → inline status picker opens → user picks status → confirm → optimistic UI update on all selected rows → success/failure toast.
3. **Partial failure:** Toast shows partial count + "View errors" link → slide-in panel with per-task error detail and option to retry failed tasks.
4. **Deselect:** Click "✕ Clear" in toolbar or press Escape → selection cleared, toolbar dismissed.

## 8. Technical Notes & Rollout
- **API:** All bulk mutations route through `POST /api/v2/tasks/bulk-update` (Bulk Operations API v2). Do not call single-task PATCH endpoints in a loop.
- **Rate limits:** Bulk API v2 rate limit TBD — confirm with backend team before setting UI caps on max selection size. Current working assumption: 200 tasks per bulk call, 10 calls/min per user.
- **Optimistic UI:** Apply visual state change immediately on confirm; roll back per-task on error. Do not block UI on server round-trip.
- **Data model:** No schema changes required; bulk endpoint operates on existing task fields.
- **Flag name:** `bulk_edit_toolbar` — default `off`. Enable for internal team on day 1, opt-in beta on week 2, GA rollout at week 4 if error rate guardrail holds.
- **Phased rollout:**
  | Phase | Audience | Start | Exit criterion |
  |---|---|---|---|
  | Internal | TaskFlow employees | Week 1 post-launch | No P0 bugs after 5 business days |
  | Beta | Opt-in teams (target ~20 teams) | Week 2 | Error rate guardrail holds; adoption signal positive |
  | GA | All teams | Week 4 | 30-day adoption trend on track |
- **Comms:** In-app tooltip on first toolbar appearance. Changelog entry. Optional onboarding email to teams with 20+ tasks in any list (coordinate with product marketing).

## 9. Risks & Open Questions
| Risk / Question | Owner | Resolution by |
|---|---|---|
| Bulk API v2 ships late or changes endpoint contract — toolbar has no fallback | Sarah Chen + Jordan Park | 2026-07-01 |
| Rate limit caps on Bulk API v2 unknown — may force UI-level selection cap | Backend team | 2026-06-15 |
| No quantitative evidence yet on how many sessions are "bulk-eligible" — 30% target may be wrong | Priya Sharma | 2026-06-30 (pull analytics) |
| Undo across 200 tasks within 30 s may be technically expensive — confirm feasibility with backend | Sarah Chen | 2026-07-15 |
| Shift-click range selection UX on sorted/filtered views (non-contiguous task IDs) needs careful spec | Marcus Rivera | Design review by 2026-07-01 |
| "Select all" across paginated results requires API support for "all matching IDs" — confirm Bulk API v2 supports this | Backend team | 2026-06-15 |
