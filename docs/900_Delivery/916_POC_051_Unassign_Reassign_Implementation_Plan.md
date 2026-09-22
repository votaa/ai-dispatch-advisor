# POC-051 — Unassign and Reassign Crews from Incidents

Status: Implemented in the working tree and committed; durable assignment-mutation history presentation is deferred to POC-052.

## Purpose

POC-051 adds explicit dispatcher actions for changing an existing incident-to-crew assignment. The operator must be able to remove an assignment, replace it with another crew, and understand the resulting state across the Incident, Dispatch, Dashboard, Crew Board, and assignment views.

The feature changes operational assignment state. It does not change the incident's severity, priority score, critical-facility evaluation, recommendation ranking, or synthetic scenario source files.

## Current baseline

The current POC already has:

- scenario-scoped active assignments;
- incident status derived as `assigned` when at least one active assignment exists;
- crew status derived as `assigned` when the crew has at least one active assignment;
- assignment details shown from incident and crew records;
- Accept and selected-alternative assignment actions;
- decision history and assignment records persisted separately from scenario fixtures.

The current Accept/Modify/Defer/Override controls record a recommendation decision. POC-051 adds assignment-management controls for an assignment that already exists. Those controls should not be placed inside the shared contextual-navigation panel, which remains a navigation surface.

## Decisions to make explicit

### Assignment state is authoritative

An assignment is active when its assignment record has `status = active`. Incident and crew status must be recomputed from the complete active assignment set for the active scenario:

| Record | Rule after refresh |
| --- | --- |
| Incident | `assigned` if one or more active assignments remain; otherwise `unassigned` |
| Crew | `assigned` if one or more active assignments remain; otherwise `available` unless an independent source status prevents that label |
| Assignment | Retained for history with a terminal status such as `unassigned` or `reassigned`; it is removed from active assignment results |
| Dashboard | Recomputed from refreshed incidents and crews |

No status should be changed by simply hiding an assignment in the UI. The backend must apply the mutation and return refreshed authoritative state.

### The user's example

If an incident has one active assigned crew and the dispatcher unassigns it successfully:

1. The assignment becomes inactive and remains in history.
2. The incident changes from `assigned` to `unassigned`.
3. The crew changes from `assigned` to `available` if it has no other active assignments and no separate non-available source status.
4. The incident's assigned-crew list becomes empty.
5. The crew's assigned-incident list becomes empty.
6. Incident assignment filters, Crew Board status filters, Dashboard assigned-crew totals, available-crew totals, and visible result counts refresh.
7. Any displayed recommendation is recalculated or explicitly marked stale; it must not silently become an assignment.

If the incident has multiple active crews, unassigning one removes only that relationship. The incident remains `assigned` while another active assignment remains. The removed crew becomes `available` only if it has no other active assignments.

## User actions and UI presentation

### Incident detail and Dispatch

For an assigned incident, the existing assigned-crew section should present each active assignment with:

- crew name and crew ID;
- assignment status and assigned time;
- a compact `Unassign` action adjacent to that assignment;
- a `Reassign` action for the incident-level assignment group.

The actions should be visually secondary to the incident identity and current status, but remain keyboard accessible and clearly distinguishable from navigation links.

For an unassigned incident, the assignment section should present:

- `Unassigned` status;
- no stale assigned-crew links;
- `Assign crew` or `Reassign` as the primary assignment-management action when a crew can be selected;
- a clear empty state when no eligible crew is available.

The recommendation panel should continue to show recommendation actions separately. If an incident has a current recommendation, the assignment-management area should identify it as a recommendation, not as an existing assignment.

### Crew Board and crew detail

For a crew with one or more active assignments, the Crew Board card/detail view should show:

- `Assigned` status;
- the active incident list;
- the assignment count;
- an assignment-level `Unassign from incident` action, subject to the same confirmation and validation rules as the incident view.

For a crew with no active assignments after a successful mutation, the view should show:

- `Available` status when eligible;
- zero active assignments;
- updated availability and assignment-count facets;
- a success message naming the incident and crew.

If a crew remains assigned to another incident, it must remain `Assigned`; the UI should report that only one relationship was removed rather than implying that the crew became available.

### Confirmation and reason capture

`Unassign` must open a confirmation step before mutation. The confirmation should state:

> Remove [crew] from [incident]? The incident and crew status may change after the assignment is removed.

The dispatcher should provide a reason or select a governed reason category. Suggested categories are:

- field condition changed;
- crew unavailable;
- assignment entered in error;
- incident priority changed;
- supervisor direction;
- other, with a required note.

`Reassign` should open a controlled selection flow rather than immediately mutating state. The flow should show:

1. current crew, if any;
2. replacement crew candidates;
3. availability, capability, region, storm readiness, shift remaining, and assignment conflicts;
4. the reason for replacing the current assignment;
5. a final action such as `Confirm reassignment`.

The selected replacement must be revalidated on submission. A stale or no-longer-eligible crew must produce an actionable error and leave the current assignment unchanged.

## State-transition flows

### Unassign one active assignment

```text
Assigned incident + active crew assignment
        |
        | Dispatcher selects Unassign
        v
Confirmation + reason
        |
        | Backend validates scenario, assignment, and current state
        v
Assignment terminal state; audit event recorded
        |
        | Refresh authoritative incident, crew, assignment, dashboard data
        v
Incident assigned/unassigned derived from remaining assignments
Crew assigned/available derived from remaining assignments
Counts, facets, lists, and detail panels update
```

### Reassign one active assignment

```text
Current assignment
        |
        | Dispatcher selects Reassign
        v
Candidate crew picker + current assignment context
        |
        | Dispatcher selects eligible replacement and gives reason
        v
Backend atomically validates and changes the relationship
        |
        v
Old assignment terminal; new assignment active
        |
        v
Incident remains assigned
Old crew may become available
New crew becomes assigned
All dependent views and counts refresh together
```

The reassignment operation should be atomic from the user's perspective. The UI must not briefly display an unassigned incident or available replacement crew between the old-assignment removal and new-assignment creation.

## Result matrix

| Action | Incident tab | Crew Board | Dashboard/counts |
| --- | --- | --- | --- |
| Unassign only active crew | `assigned` → `unassigned`; assigned crew list cleared | Crew `assigned` → `available`; incident list cleared | Assigned incident/crew counts decrease; available crew count increases; filters and pagination recalculate |
| Unassign one of multiple crews | Remains `assigned`; remaining crews stay visible | Removed crew may become available; other crews unchanged | Counts change only for the removed relationship and any status transition |
| Reassign to available crew | Remains `assigned`; replacement crew shown | Old crew may become available; new crew becomes `assigned` | Assigned-crew total remains stable; available count moves from new crew to old crew when applicable |
| Reassign to invalid/stale crew | No change | No change | No count change; error explains that the candidate is no longer eligible |
| Unassign crew with another active incident | Incident becomes unassigned if it had no other crew | Crew remains `assigned` with remaining incident(s) | Available count does not increase for that crew |
| No eligible replacement | Current assignment remains unchanged | Current crew remains assigned | No count change; UI offers unassign-only or supervisor follow-up according to policy |

## Backend and contract plan

Add assignment-management operations behind the existing scenario-scoped persistence boundary. The exact route names can be selected during implementation, but the contract should support:

- unassign by `assignment_id` or by a validated incident/crew pair;
- reassign by current assignment plus selected replacement crew;
- scenario identity and correlation/request ID;
- reason category and optional note;
- optimistic concurrency or equivalent stale-state validation;
- an audit event containing actor, timestamp, prior state, resulting state, reason, and affected IDs;
- a response containing refreshed incident, affected crews, assignment records, and dashboard summary, or a documented refetch contract.

Validation must fail closed when:

- the assignment is not active;
- the assignment belongs to another scenario;
- the incident or crew no longer exists;
- the replacement crew is unavailable, already assigned where concurrent assignment is prohibited, capability-ineligible, or otherwise blocked;
- the request is based on stale assignment data.

The implementation must preserve the original recommendation and any prior decision event. Unassigning an assignment is not equivalent to deleting or rewriting the recommendation history.

### Audit-history boundary and follow-up

POC-051 persists assignment mutations with the action, affected assignment and incident/crew IDs, reason category, optional note, actor, and timestamp. The current implementation returns those fields from the mutation response, but it does not yet expose a durable assignment-mutation history endpoint or an in-product Audit / Assignment History panel. The existing `/api/audit/events` route and recommendation history UI remain scoped to recommendation decisions.

This audit-history presentation is tracked as POC-052. Until that follow-up is implemented, operators can see the resulting assignment state and a transient success message in the Incident or Crew views, but cannot review the selected category or note after the mutation flow closes.

## Refresh and count behavior

After a successful mutation, refresh the authoritative data used by all affected views in one coordinated update:

- incident collection and selected incident detail;
- crew collection and selected crew detail;
- active assignments;
- Dashboard summary;
- recommendation context for the selected incident;
- incident and crew facet counts;
- map records and assignment relationships, if Operations Map is active.

The UI should preserve the user's current tab and selection when the record still exists. It should clear or update stale assignment controls when the record's state changes. Pagination should be clamped after filtering changes, and a selected record should remain visible in its detail panel even if its current filter no longer matches until the user closes or clears that context.

## Acceptance criteria

### Unassign

- A dispatcher can unassign an active assignment from Incident detail and Crew detail.
- Confirmation and reason capture occur before mutation.
- The operation is scenario-scoped and auditable.
- A single-assignment incident becomes `unassigned`.
- A crew with no remaining active assignments becomes `available` when eligible.
- Multiple-assignment and multi-incident cases update only the affected relationship.
- Incident, crew, assignment, Dashboard, facet, and map data agree after refresh.

### Reassign

- A dispatcher can select a replacement crew from a filtered, evidence-bearing candidate list.
- The current assignment remains unchanged when validation fails.
- A successful reassignment records the old relationship as terminal and creates the new active relationship atomically.
- The incident remains `assigned`.
- The old and new crews receive the correct derived statuses and incident lists.
- The replacement reason and prior recommendation evidence remain available in history.

### Safety and usability

- No action implies that a recommendation automatically changes assignment state.
- No coordinates, availability, capability, or assignment eligibility are inferred when source data is missing.
- Keyboard, focus, loading, error, and retry states are covered.
- Rapid repeated submission cannot create duplicate active assignments.
- Scenario activation does not carry assignment mutations across scenarios.

## Validation plan

Implement and validate in independently reviewable slices:

1. Assignment transition and persistence contract.
2. Backend unassign operation and audit event.
3. Backend reassign operation with atomic validation.
4. Incident and Dispatch controls.
5. Crew Board and crew-detail controls.
6. Coordinated refresh and count/facet updates.
7. Regression and browser validation across assigned, unassigned, multiple-assignment, stale-candidate, no-eligible-crew, and scenario-switch cases.

Required test scenarios include:

- one assigned incident / one crew;
- one incident / multiple crews;
- one crew / multiple incidents;
- unassigned incident with an eligible replacement;
- no eligible replacement;
- stale assignment and stale replacement candidate;
- failed mutation with no partial state change;
- Dashboard and both Incident and Crew Board filters before and after mutation;
- selected detail state and keyboard focus after refresh.

## Scope boundaries

POC-051 does not include live OMS writeback, role-based authorization, production dispatch integration, route optimization, automatic recommendation acceptance, or changes to scenario fixture CSVs. Those boundaries should remain explicit in the implementation and demo messaging.
