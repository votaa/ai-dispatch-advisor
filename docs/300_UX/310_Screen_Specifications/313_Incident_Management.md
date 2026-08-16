# Incident Management Screen Specification

## Purpose

Provide a focused view for scanning, selecting, filtering, and inspecting active outage incidents before taking dispatch action.

## Screen Visual

![Incident Detail / Explain Recommendation screen visual](<../../assets/screenshots/Storm Dispatch Incident Dashboard.png>)

Screenshot status: Approved mockup PNG provided by project owner.

## Primary User

Distribution Dispatcher, Dispatch Supervisor

## Layout Specification

- Active incident table
- Priority and severity columns
- Customer impact columns
- Hazard and ETR columns
- Selected row state

## Key UI Components

- Incident ID
- Region
- Municipality
- Feeder
- Customers out
- Severity
- Hazard
- ETR
- Critical facility flag in future detail

## User Actions

- Select incident
- Search incidents by ID, municipality, feeder, or hazard.
- Filter by severity and region.
- Sort directly from sortable table headers (Incident, Region, Customers, Severity, Hazard, Assigned Crews, Decision, and ETR); clicking the active header toggles ascending/descending order. Priority remains the default ordering.
- Paginate large incident lists while preserving selected-incident context.
- Open incident detail in future iteration
- Send selected incident to recommendation workflow

## Data Requirements

- PendingIncidents.csv
- Outage event data
- Customer impact
- Hazard status
- ETR

## Backend and API Dependencies

- `GET /api/incidents`
- `GET /api/incidents/{incident_id}`
- Client-side incident filters and pagination are implemented in the shared incident-table shell; server-side filtering remains a future optimization if data volumes exceed the POC boundary.
- The result summary distinguishes the currently matched set from the full incident set (for example, `Showing 1–1 of 1 matching incidents (5 total)` means one incident matches the active search/filter criteria; clear those criteria to see the other four).

## AI and Recommendation Behavior

Incident ranking can be AI-assisted or rule-based; the UI must make priority and severity drivers inspectable.

## Audit Requirements

Incident selection generally does not require audit. Future recommendation view or action events should be audited.

## Accessibility Notes

- Preserve keyboard access for all interactive controls.
- Do not rely on color alone for severity, status, confidence, or integration health.
- Keep dense operational data readable at expected dispatcher workstation sizes.
- Provide visible focus and confirmation states for user actions.

## Acceptance Criteria

- Active incidents load successfully
- Rows show key dispatch fields
- Selected incident state is visible
- Incident selection can drive recommendation context

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
