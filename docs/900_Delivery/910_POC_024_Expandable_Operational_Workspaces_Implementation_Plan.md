# POC-024 Expandable Operational Workspaces Implementation Plan

## Status

Status: Implemented; automated and live browser verification passed. Pending owner smoke-test approval before closure.

Date: 2026-09-13

## Implementation Outcome

- Added one reusable accessible expand/restore wrapper used by Dashboard, Dispatch, Active
  Incidents, Crew Board, and Storm Exceptions.
- Retained each existing table or card component instance so search, filters, sort,
  selection, paging, and detail context survive expansion and restoration.
- Explicitly remeasures fitted pagination in each layout and preserves the prior logical
  result position when page size changes.
- Keeps desktop navigation available, uses the full viewport on narrow layouts, locks
  underlying page scrolling, supports `Escape`, announces state changes, and restores focus.
- Scenario and AI Copilot remain excluded because their current content is not a qualifying
  dense operational workspace.
- Frontend tests and production build pass. Live browser verification at 1280×800 confirmed
  the Dashboard increases from 2 to 4 visible rows and reduces 250 pages to 125; Dispatch,
  Active Incidents, and Storm Exceptions show additional rows. A follow-up expanded-density
  correction uses the complete viewport height and compact expanded-only row/card spacing;
  at 1440×800 this increases Dispatch and Active Incidents from 3 to 5 rows, Storm Exceptions
  from 2 to 6 rows, and Crew Board from 8 to 12 cards. At 1280×800, Crew Board increases from
  6 to 12 cards while fitted table rows continue to exclude any partially visible row. The
  768×1024 expanded layout has no page-level horizontal overflow.

This plan captures an enhancement identified during Dashboard smoke testing. Data-heavy
tables and detail workspaces should be temporarily expandable within the application so an
operator can use the full main content area, see more rows, and reduce paging without losing
the current workflow or opening a separate browser window.

## Requested Experience

The annotated feedback requests:

- An expand or popout control for the lower data/detail workspace on the Dashboard and other
  qualifying tabs.
- An expanded view that covers the current tab content and uses all available space to the
  right of the application navigation.
- More visible rows per page and fewer pages when the additional height is available.
- No loss of the workspace's existing functionality while expanded.
- A minimize, close, or restore control that returns the workspace to its normal embedded
  layout.

For implementation, `popout` means an **in-app expanded workspace**. It does not mean a new
browser tab, a separate operating-system window, or `window.open()`.

## Goals

1. Give operators a larger, focused view of dense operational data without leaving the
   current application view.
2. Preserve search, filters, sorting, pagination, record selection, recommendations, and
   detail actions in both normal and expanded modes.
3. Increase the number of visible rows by reusing the existing viewport-aware pagination
   behavior rather than assigning an arbitrary expanded page size.
4. Provide one reusable, accessible interaction pattern across every tab that warrants it.
5. Restore the exact working context when the operator exits expanded mode.

## Non-Goals

- Opening a browser popup, new tab, or independent application window.
- Changing backend APIs, scenario data, incident ranking, recommendation logic, or Copilot
  behavior.
- Replacing the existing search, filtering, sorting, or pagination models.
- Making all cards and small panels expandable regardless of whether expansion adds value.
- Combining this work with POC-023 typeahead implementation.
- Persisting expanded state across a browser refresh unless separately approved.

## Candidate Scope

Apply the behavior to reusable, data-heavy workspaces after confirming that each view gains
meaningful space:

| View | Candidate workspace | Initial recommendation |
| --- | --- | --- |
| Dashboard | Top Priority Incidents table and its controls | Include |
| Dispatch | Incident Queue and recommendation/detail workspace | Include |
| Incidents | Active Incidents table and Incident Details | Include |
| Storm Mode | Storm incident/exception table and related details | Include if it uses the shared table shell |
| Crew Board | Filtered and paginated crew-card workspace | Include if expansion materially increases visible cards |
| AI Copilot | Conversation and composer | Exclude from the initial implementation; evaluate separately |
| Scenario | Scenario selection and metadata | Exclude unless future content becomes data-dense |

The implementation review should confirm the final list before coding. Tabs sharing the same
table or workspace component should receive consistent behavior in the same change.

## UX Contract

### Normal mode

- Place an `Expand` control in the workspace header without crowding search, filter, or
  recommendation controls.
- Use an icon plus an accessible label or visible text so the control is understandable
  without relying on icon recognition.
- Preserve the existing embedded height, fitted page size, responsive layout, and all
  current actions.

### Expanded mode

- Fill the application's main content area to the right of the persistent navigation.
- Keep the workspace title, result summary, search, filters, sort controls, pagination,
  selected record, and applicable recommendation/detail actions available.
- Recalculate the fitted page size from the expanded workspace's actual available height.
- Keep the workspace header and restore control visible while its data region scrolls.
- Prevent the underlying main content from scrolling or receiving unintended pointer input.
- Allow at most one workspace to be expanded at a time.

### Restore behavior

- Label the reverse action `Restore` or `Exit expanded view`; a minus or close icon may
  accompany it but must not imply that records or user work will be deleted.
- Restore the prior search term, filters, sort order, selected item, active detail or
  recommendation context, and current logical result position.
- Recalculate the normal fitted page size and clamp the page number only if the smaller
  layout makes the previous page invalid.
- Return keyboard focus to the control that opened the expanded view.
- Support `Escape` to restore when focus is not inside another interaction that consumes
  that key.

## Proposed Frontend Design

### Shared component

Create a reusable wrapper such as `ExpandableWorkspace` around qualifying panels. Its
contract should include:

- Workspace title and accessible label.
- Normal and expanded state.
- Expansion and restoration callbacks.
- A content slot that retains the existing component instance and state.
- Optional header actions for view-specific controls.
- A stable test identifier for cross-view coverage.

Retain the same child component instance where practical. Moving or replacing the child
with a second rendering can reset uncontrolled fields, selection, pagination, or detail
state and should be avoided.

### Layout approach

- Render expanded mode as a fixed application-layer surface bounded by the main content
  region, accounting for the desktop sidebar width.
- When navigation collapses or the viewport becomes narrow, use the full available viewport
  width without creating horizontal page overflow.
- Give the expanded surface an intentional application-layer stacking order above tab
  content and below any existing dialogs or critical alerts.
- Lock underlying content scroll while allowing the workspace's data region to scroll.
- Reuse existing design tokens for backgrounds, borders, spacing, and focus indicators.

### Viewport-aware paging

The current table fit behavior should remain the source of truth. Expanded mode must trigger
remeasurement when:

- Expansion or restoration completes.
- The browser is resized or zoom changes the available layout.
- A filter, result count, header height, or detail area changes.
- Responsive controls wrap to a new line.

Prefer the existing resize-observation or fitted-page-size mechanism. Do not hard-code an
expanded value such as 25 or 50 rows, because available height and row content vary.

## State and Scenario Rules

- Expansion is presentation state only; data queries and result ordering must not change.
- Search, facet filters, sort order, page, selection, and recommendation/detail context must
  share their existing single source of truth.
- If the active scenario changes while a workspace is expanded, restore the view before or
  as the new scenario state is applied, then follow the existing scenario reset rules.
- Loading, empty, error, retry, and zero-match states must render correctly in both modes.
- Long crew names, wrapped incident IDs, ETR values, badges, and narrow viewports must not
  make the restore control inaccessible.

## Accessibility Requirements

- The expand and restore controls must be keyboard reachable and have explicit accessible
  names and visible focus states.
- Announce the expanded/restored state to assistive technology without repeatedly announcing
  table contents.
- Keep heading and table semantics intact; expansion must not turn the workspace into an
  inaccessible visual-only overlay.
- If expanded mode behaves as a modal layer, implement focus containment, background
  inertness, and focus restoration. If navigation is intentionally usable, use a labeled
  region instead and do not claim modal semantics.
- Maintain the existing reduced-motion behavior; expansion must not require animation.

## Implementation Sequence

### Phase 1 — Shared foundation

1. Inventory the shared table shell, fitted-page-size logic, panel headers, and any existing
   overlay or focus-management primitives.
2. Define the qualifying-view list and the navigation-width/responsive layout contract.
3. Add the shared expandable wrapper, application-layer styling, scroll handling, and
   accessible controls.
4. Add focused component tests for expansion, restoration, focus, and state preservation.

### Phase 2 — Dashboard reference implementation

1. Wrap the Top Priority Incidents workspace without changing its ranking or percentage
   selector.
2. Verify that the dynamic panel and search labels remain correct.
3. Confirm that expansion increases the fitted row count where space permits and reduces
   the page count without changing the matched-result total.
4. Verify that Recommendations still targets the currently selected or first displayed
   incident according to the existing selection rules.

### Phase 3 — Consistent cross-view rollout

1. Apply the shared behavior to Dispatch and Active Incidents.
2. Apply it to Storm Mode and Crew Board only where the additional space materially improves
   the existing workspace.
3. Preserve each view's current filters, selected context, side panels, and scenario-change
   behavior.
4. Add cross-view regression tests instead of introducing view-specific expansion logic.

### Phase 4 — Documentation and smoke-test closeout

1. Update the POC feedback log with the implemented behavior and coverage.
2. Document any excluded views and the reason they were excluded.
3. Run the frontend regression suite and repository validation required for the affected
   files.
4. Smoke test normal, expanded, and restored states in representative small and large
   scenarios before closing POC-024.

## Test Plan

### Automated tests

- Expand and restore controls render with correct names and state.
- Existing search, filters, sort, pagination, selection, and actions work while expanded.
- Expanding triggers a fitted-page-size remeasurement and never changes total result counts.
- Restoring preserves state and returns focus to the triggering control.
- `Escape`, resize, loading, empty, error, and zero-match cases behave safely.
- Scenario changes clear or preserve state according to the existing view contract and do
  not leave an orphaned overlay.
- Only one workspace can be expanded at a time.
- Dashboard, Dispatch, Incidents, and every other included view use the shared behavior.

### Manual smoke tests

- Expand the Dashboard workspace in a small scenario and confirm that controls and text do
  not become disproportionately stretched.
- Expand it in a large scenario and confirm that more rows appear and the page count drops.
- Apply search and multiple filters, select a non-first incident, open its recommendation or
  details, expand and restore, and confirm the same context remains active.
- Repeat on Dispatch and Active Incidents, then on each additional included view.
- Test keyboard-only expansion, restoration, focus return, and `Escape`.
- Test common desktop widths, a narrow viewport, browser zoom, long ETRs, wrapped crew names,
  and no-result states.

## Acceptance Criteria

- A qualifying workspace can expand within the current application and restore without a
  browser popup or navigation change.
- Expanded mode uses the full main area to the right of navigation and does not introduce
  page-level horizontal scrolling.
- All existing workspace controls and actions remain functional.
- Available height is remeasured so more rows or cards are shown where space permits, while
  matched and total result counts remain unchanged.
- Search, filters, sort, selection, detail/recommendation context, and logical result position
  survive expand and restore.
- Keyboard, focus, accessible naming, and responsive-layout requirements pass automated and
  manual checks.
- Behavior is consistent across the approved qualifying tabs and covered by regression tests.
- POC-024 is updated to `Closed` only after implementation and smoke-test approval.

## Complexity, Risks, and Recommended Timing

Estimated complexity: **medium**. The visual toggle itself is small; the work is primarily in
preserving state, remeasuring fitted pagination, managing focus and scrolling, and proving
consistent behavior across multiple responsive views.

Primary risks are duplicated component state, stale page indexes after remeasurement,
overlay stacking conflicts, and inaccessible keyboard/focus behavior. A shared wrapper and
single Dashboard reference implementation should reduce those risks before cross-view use.

Implement POC-023 first because typeahead will change search controls on the same views.
POC-024 can then wrap the settled controls once and validate typeahead behavior in both normal
and expanded modes. No backend or scenario-data work is expected.

## Related Documents

- [POC Feedback Log](../004_POC_Feedback_Log.md)
- [Frontend Architecture](../500_Frontend/501_Frontend_Architecture.md)
- [State Management](../500_Frontend/502_State_Management.md)
- [Test Strategy](901_Test_Strategy.md)
