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
- Priority dispatch queue
- Recommendation context panel
- Scenario/data freshness indicator

## Key UI Components

- Customers out metric
- Active incidents metric
- Available crews metric
- Critical facility event metric
- Top incidents table
- Recommendation summary panel

## User Actions

- Select priority incident
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

## Acceptance Criteria

- Metrics load from backend data
- Top incidents display in priority order
- Selecting an incident updates recommendation context
- Dashboard is usable as first screen

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
