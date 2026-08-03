# Dispatch Console Specification

## Purpose

This document defines the dispatch console experience for the AI Dispatch Advisor. The dispatch console is the primary work surface for reviewing outage incidents, evaluating recommendations, comparing crew options, and recording user decisions.

## Current Implementation State

The current POC includes a Dispatch section with:

- Incident queue.
- Selected incident state.
- Recommendation panel.
- Recommendation explanation factors and constraints.
- Visible Accept, Modify, Defer, and Override controls.

The recommendation action buttons may be implemented as a later POC enhancement. When implemented, they should remain lightweight and demo-oriented until production audit and persistence requirements are finalized.

## Primary User

Primary persona:

- Distribution Dispatcher.

Supporting personas:

- Dispatch Supervisor.
- Storm Response Coordinator.
- Field Crew Coordinator.

## Primary Workflow

The dispatch console should support this flow:

1. Review active incident queue.
2. Select an incident.
3. Review incident context.
4. Review recommended action.
5. Inspect explanation, confidence, factors, and constraints.
6. Compare alternative crews or scenarios when available.
7. Accept, modify, defer, or override the recommendation.
8. See action confirmation and recent activity.

## Layout Model

The target dispatch console should use a two- or three-zone layout:

| Zone | Purpose |
| --- | --- |
| Incident Queue | Prioritized incidents requiring review |
| Recommendation Panel | Suggested action, explanation, confidence, and actions |
| Context Panel | Incident details, crew context, map, source data, and history |

In the current POC, the incident queue and recommendation panel are the primary visible zones.

## Incident Queue Requirements

The incident queue should show:

- Incident identifier.
- Region or operating area.
- Municipality or location.
- Feeder or circuit.
- Severity.
- Customer impact.
- Critical facility flag.
- Hazard.
- Status.
- ETR.
- Recommendation status.
- Assignment status.

Target queue controls:

- Sort by priority, severity, customers out, age, region, and recommendation status.
- Filter by region, severity, critical facility impact, hazard, assignment status, and stale data.
- Select incident without navigating away from the dispatch workspace.

## Selected Incident Context

The selected incident context should show:

- Incident summary.
- Customers out.
- Current status.
- Location.
- Feeder or asset context.
- Critical facilities.
- Hazard and safety notes.
- Weather context.
- Data freshness.
- Current assignment if any.

The current POC shows a subset of this context through the incident queue and recommendation panel.

## Recommendation Panel Requirements

The recommendation panel should show:

- Recommended action.
- Recommended crew or resource.
- Confidence.
- Expected operational impact.
- Explanation factors.
- Constraints.
- Alternatives.
- Human approval boundary.

The panel should make clear that the recommendation is advisory until a dispatcher takes action.

## Recommendation Actions

The dispatch console should support:

| Action | UX Behavior |
| --- | --- |
| Accept | Records the recommendation as accepted |
| Modify | Allows a note or changed action before recording |
| Defer | Records that action is delayed or requires later review |
| Override | Requires an override reason before recording |

For the POC, these actions may write to a lightweight backend memory store, JSON file, or SQLite-backed demo table. For production, these actions must create durable audit events and may require writeback to approved systems of record.

## Action Feedback

After a recommendation action, the UI should show:

- Action confirmation.
- Timestamp.
- User action type.
- Incident identifier.
- Crew identifier if applicable.
- Override or modification reason if applicable.
- Recent action history.

The UI should avoid silent action. Every dispatch decision should create visible feedback.

## Error and Edge States

The dispatch console should handle:

- Backend unavailable.
- No incidents available.
- No suitable crew available.
- Recommendation unavailable.
- Stale source data.
- Action save failure.
- Unauthorized action.
- Integration writeback failure.

For the POC, errors may be shown as simple banners. Production should provide role-appropriate support details and correlation identifiers.

## Storm Mode Relationship

Storm mode should not replace the dispatch console. It should provide aggregate situational awareness and exception management, while the dispatch console remains the place for incident-level decision review.

## Map and Geospatial Context

The target dispatch console should include geospatial context when practical:

- Incident location.
- Crew location.
- Critical facilities.
- Feeder or circuit area.
- Weather or access hazard overlays.

The initial POC does not yet include an interactive map.

## Acceptance Criteria

The dispatch console is minimally acceptable when:

- A dispatcher can select an incident.
- The recommendation panel updates for the selected incident.
- Explanation factors and constraints are visible.
- User action controls are visible.
- Action controls provide confirmation once implemented.
- The UI preserves the distinction between recommendation and approved action.

## Related Documents

- [UI Information Architecture](301_UI_Information_Architecture.md)
- [Recommendation Experience](303_Recommendation_Experience.md)
- [Explainability and Trust](304_Explainability_and_Trust.md)
- [Accessibility Guidelines](305_Accessibility_Guidelines.md)

