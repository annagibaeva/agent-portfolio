# PRD: Command Palette (Cmd+K)

**Author:** TBD
**Status:** Draft
**Last updated:** 2026-05-25
**Target release:** v3.0 / Q2 2026

## 1. Summary
TaskFlow users waste time hunting through sidebars and menus to reach projects,
tasks, and settings they know exist. A command palette — triggered by Cmd+K
(Ctrl+K on Windows) — gives every user a single, keyboard-driven entry point to
search and jump to anything in the product, and to fire common actions without
lifting hands from the keyboard. This is a high-visibility quality-of-life win
that complements the v3.0 enterprise push by making TaskFlow feel fast and
polished to the power users who evaluate tools for their teams.

## 2. Problem & Users

- **Primary persona:** Power users — engineers, project leads, and ops managers
  at mid-market companies (50–500 employees) who live in TaskFlow all day and
  know what they want but can't get there fast.
- **Secondary persona:** New teammates who don't yet know the navigation and
  would benefit from a search-first UX.
- **Current workaround:** Multi-click navigation through the left sidebar, or
  using browser Cmd+F to scan long task lists. Neither is fast; neither works
  across entity types.
- **Evidence the problem is real:**

> LOW CONFIDENCE
  - No direct user-research data available at time of drafting. Proxy signal:
    command palettes are a table-stakes feature in every direct competitor
    (Linear, Notion, GitHub). Absence is a known friction point in the
    "too shallow" criticism of tools like Asana. Add to Open Questions.

- **Top use cases (estimated frequency):**
  1. Jump to a project by name — daily
  2. Open a specific task without navigating to its project first — daily
  3. Fire a quick action (create task, assign, change status) — several times
     per week

## 3. Goals & Non-Goals

**Goals**
- Give users a single keyboard shortcut (Cmd+K / Ctrl+K) to reach any project,
  task, or person in their workspace.
- Reduce average navigation clicks-to-target by a measurable amount (target
  TBD — see Open Questions).
- Ship as part of v3.0 so it's in front of enterprise evaluators during the Q2
  push.

**Non-Goals**
- Full-text search inside task descriptions or comments at launch (that's a
  separate search infrastructure project).
- Mobile / touch support in v1 — keyboard-first only.
- AI-assisted suggestions or natural-language commands — future iteration.
- Replacing the existing sidebar navigation — palette is additive, not a
  redesign.

## 4. Success Metrics

> LOW CONFIDENCE
- **North-star:** ≥ 30% of weekly active users trigger Cmd+K at least once per
  week within 60 days of GA. (Baseline: 0%; target is a guess — validate with
  Jordan/Sarah before locking.)
- **Engagement depth:** Median session includes ≥ 2 palette-initiated
  navigations within 30 days of first use.
- **Guardrail — page load performance:** p95 time-to-first-result in the palette
  ≤ 150 ms. Overall app p95 LCP must not regress.
- **Guardrail — support volume:** No increase in "can't find X" support tickets
  post-launch.

## 5. Requirements

### Must-have (P0)
- Cmd+K (Mac) / Ctrl+K (Windows/Linux) opens the palette from anywhere in the
  app. Escape closes it.
- Palette is modal and overlays current content; background is not interactive
  while open.
- Search scope at launch: **projects**, **tasks** (by title), **people**
  (teammates in the workspace).
- Results appear within 150 ms of keystroke on a warm index.
- Keyboard-only navigation: arrow keys to move, Enter to select, Tab to cycle
  sections.
- Selecting a result navigates to that entity's page.
- Palette is accessible (ARIA role `dialog`, focus trap, screen-reader
  announcements on result changes).
- Works on all paid tiers; also available on free tier (scope TBD — see Open
  Questions).

### Should-have (P1)
- Recent items section shown before the user types anything (last 5–10 visited
  entities).
- Quick actions surfaced as results: "Create task," "Invite teammate,"
  "Open settings."
- Keyboard shortcut hint visible in the top nav or sidebar so users discover
  the feature.
- Fuzzy / typo-tolerant matching (e.g., "retro" matches "Retrospective Q1").

### Nice-to-have (P2)
- Inline action execution from the palette (e.g., change a task's status
  without navigating away).
- Scoped search: prefix syntax like `@person` or `#project` to filter results.
- Admin-configurable shortcut override for enterprise customers whose OS or
  browser intercepts Cmd+K.

Each requirement is acceptance-testable: P0 items map directly to integration
and E2E test cases; P1/P2 items require explicit test coverage before merge.

## 6. Dependencies

> LOW CONFIDENCE
- **Internal — Search / indexing service:** It is unclear whether TaskFlow has
  a unified search index today. If not, a lightweight client-side index (e.g.,
  Fuse.js) may be used at launch for title-only search, with a server-side index
  as a follow-on. Sarah Chen to confirm during spec review.
- **Internal — Global keyboard shortcut library:** Need to confirm whether a
  library (e.g., `tinykeys`, `hotkeys-js`) is already in the frontend bundle or
  if one must be added and reviewed. **Blocking for GA.**
- **Internal — Frontend (Sarah's team):** Primary implementors. Capacity in Q2
  sprint plan must be confirmed. **Blocking.**
- **Internal — Design (Marcus Rivera):** Component design and motion spec
  required before eng kickoff. **Blocking.**
- **Internal — Analytics:** Palette open/close and result-selected events must
  be instrumented; Priya Sharma to confirm event schema. Non-blocking for
  launch, blocking for success metric validation.
- **External:** None identified.

## 7. UX

Figma file to be created by Marcus Rivera — link TBD.

Key flows to spec:
1. **Open → search → navigate:** User presses Cmd+K → types "retro" → sees
   fuzzy-matched projects and tasks → presses Enter → lands on entity page.
2. **Open → recent items → select:** Palette opens with no query; shows last
   5 visited items; user arrows down and hits Enter.
3. **Open → quick action → execute:** User types "create" → sees "Create task"
   command → hits Enter → task creation modal opens (or inline form in palette
   if P2 is scoped in).
4. **Dismiss:** Escape or click outside closes palette; user returns to where
   they were with focus restored.

## 8. Technical Notes & Rollout

> LOW CONFIDENCE
- **Frontend:** New `CommandPalette` React component, rendered at the app-root
  level (outside any route subtree) so it's available on every page. CSS module
  for styles; no styled-components per convention.
- **Keyboard handling:** Register shortcut at mount using a lightweight library
  (to be selected — see Dependencies). Must not conflict with browser defaults
  or existing TaskFlow shortcuts.
- **Search strategy (launch):** Client-side fuzzy search over an in-memory
  index of the user's projects, tasks (title only), and teammates. Index built
  on login and refreshed on mutations. If index size becomes a concern (teams
  with 10k+ tasks), fall back to a debounced API call. Long-term: integrate
  with a server-side search service.
- **Accessibility:** `role="dialog"`, `aria-modal="true"`, focus trap on open,
  focus restored on close, live region for result count.
- **Performance:** p95 time-to-first-result ≤ 150 ms client-side; measure via
  Datadog RUM. No regression to app LCP acceptable.
- **Feature flag:** `cmd_k_palette` — default OFF in production until internal
  testing passes.
- **Rollout plan:**
  1. Internal dog-food (team + select beta customers) — 2-week soak.
  2. Opt-in beta via in-app banner — 2 weeks.
  3. GA for all tiers (pending tier decision in Open Questions) — flag flipped
     ON by default.
- **Comms:** Changelog entry, in-app tooltip on first open (dismissible),
  optional onboarding nudge in the nav. No email blast for a QoL feature of
  this scope unless Jordan requests it.

## 9. Risks & Open Questions

| Risk / Question | Owner | Resolution by |
|---|---|---|
| No unified search index exists today — client-side index may not scale to large workspaces | Sarah Chen | 2026-06-06 |
| Cmd+K conflicts with browser or OS shortcuts on some platforms (e.g., Chrome on ChromeOS) | Frontend eng | Before kickoff |
| Success metric targets (adoption %, click reduction %) are guesses — need baseline data or stakeholder alignment | Jordan Park / Priya Sharma | 2026-06-06 |
| Tier availability: should free-tier users get the palette? Affects positioning and engineering scope | Jordan Park | 2026-06-01 |
| Keyboard shortcut library choice: bundle size and license implications need review | Sarah Chen | Before kickoff |
| No user research confirming this is a top friction point — relying on competitive parity signal | Jordan Park | Before Approved status |
