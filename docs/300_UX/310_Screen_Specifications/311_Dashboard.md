# Dashboard Screen Specification

## Purpose

Provide dispatch users with an at-a-glance operational summary of active outage conditions, customer impact, crew availability, critical facility exposure, and top priority incidents.

## Screen Visual

![Dashboard screen visual](<../../assets/screenshots/Executive Outage Management Dashboard.png>)

Screenshot status: Approved mockup PNG provided by project owner.

## Primary User

Distribution Dispatcher, Dispatch Supervisor

## Layout Specification

- Metric summary band
- Top priority incidents panel
- Recommendation context panel
- Scenario/data freshness indicator

## Key UI Components

- Customers out metric
- Active incidents metric
- Available crews metric
- Critical facility event metric
- Top incidents table with a visible shown-versus-total count
- Labeled `Incidents shown` selector with options 5, 10, 25, and 50
- Recommendation summary panel

## User Actions

- Select priority incident
- Select how many top-ranked incidents to display
- Navigate to Dispatch for recommendation review
- Use dashboard as opening operating picture

## Data Requirements

- Dashboard summary API
- Ranked incidents
- Crew counts
- Assignment counts
- Critical facility flags

## Backend and API Dependencies

- `GET /api/dashboard`
- `GET /api/incidents`
- `POST /api/optimize`

## AI and Recommendation Behavior

Shows the currently selected recommendation context; recommendation generation remains advisory and human-reviewed.

## Audit Requirements

No dashboard-only audit required for the POC. Future audit may record recommendation viewed events.

## Accessibility Notes

- Preserve keyboard access for all interactive controls.
- Do not rely on color alone for severity, status, confidence, or integration health.
- Keep dense operational data readable at expected dispatcher workstation sizes.
- Provide visible focus and confirmation states for user actions.
- Use a native or equivalently accessible select control for the incident display limit; disabled options must remain visibly distinguishable and programmatically unavailable.

## Open POC TODOs

- **POC-022 — Dashboard priority incident display limit:** Rename the current fixed panel
  from `Priority Dispatch Queue` to `Top 5 Priority Incidents` so the five-record subset is
  explicit. As a follow-on enhancement, add a compact labeled `Incidents shown` dropdown
  with 5, 10, 25, and 50 options and update the panel label to match the selected limit.
- Disable and visually gray out limits greater than the active scenario's total incident
  count. Show all incidents and disable the selector when the total is below 5. When a
  scenario switch invalidates the selected limit, reset it to the largest enabled option.
- Keep the rows in deterministic priority order and show `Showing <displayed> of <total>`
  so the subset is never mistaken for the complete active-incident collection.

## Acceptance Criteria

- Metrics load from backend data
- The fixed implementation is labeled `Top 5 Priority Incidents`
- Top incidents display in deterministic priority order
- The enhanced selector offers 5, 10, 25, and 50 and disables limits above the active-incident total
- The enhanced panel label and shown-versus-total text update with the effective display limit
- Small, empty, and scenario-switch states never leave the selector on an invalid value
- Selecting an incident updates recommendation context
- Dashboard is usable as first screen

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
