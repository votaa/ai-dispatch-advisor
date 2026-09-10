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
- Labeled `Incidents shown` selector with options 25%, 50%, 75%, and 100%
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

## POC-022 Implementation Notes

- **POC-022 — Dashboard priority incident display limit:** Implemented with an accessible
  `Incidents shown` dropdown (25%, 50%, 75%, 100%). The selected percentage is converted
  to a bounded incident count, and both the panel and search labels reflect that count,
  for example `Top 500 Priority Incidents` and `Search Top 500 Incidents Shown` for 2,000
  active incidents. The Dashboard uses the full active incident collection already loaded
  by the application, preserves deterministic order and pagination, and shows
  `Showing <displayed> of <total>` so the subset is never mistaken for the full collection.
- Empty scenarios show `All 0 Priority Incidents` and disable the selector. Percentage
  choices naturally remain bounded by the active total, including small scenarios.

## Acceptance Criteria

- Metrics load from backend data
- The default implementation is labeled `Top 5 Priority Incidents`
- Top incidents display in deterministic priority order
- The enhanced selector offers 25%, 50%, 75%, and 100% and computes a count from the active-incident total
- The enhanced panel and search labels update with the effective display count
- Empty and small scenarios remain bounded and never display more records than exist
- Selecting an incident updates recommendation context
- Dashboard is usable as first screen

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
