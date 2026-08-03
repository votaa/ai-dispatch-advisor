# Storm Mode Screen Specification

## Purpose

Support high-volume outage operations by summarizing storm impact, critical facilities, high-priority incidents, customer impact, and crew capacity.

## Screen Visual

![Storm Mode Command Center screen visual](<../../assets/screenshots/Storm Mode Command Center Dashboard.png>)

Screenshot status: Approved mockup PNG provided by project owner.

## Primary User

Storm Response Coordinator, Dispatch Supervisor

## Layout Specification

- Storm metric band
- Critical facility summary
- High-priority incident list
- Regional exception queue

## Key UI Components

- High priority incidents
- Critical facilities
- Crews assigned
- Customers out
- Storm exceptions table

## User Actions

- Review storm exceptions
- Select critical incident
- Move to dispatch recommendation workflow
- Compare scenarios in future iteration

## Data Requirements

- Incident severity
- CriticalFacilities.csv
- Weather.csv
- Crew capacity
- Assignments

## Backend and API Dependencies

- `GET /api/dashboard`
- `GET /api/incidents`
- `GET /api/weather`
- `GET /api/critical-facilities`

## AI and Recommendation Behavior

Storm prioritization should account for safety hazards, critical facilities, crew capacity, weather, and restoration benefit.

## Audit Requirements

Storm overview does not require audit. Scenario decisions and dispatch actions must be audited.

## Accessibility Notes

- Preserve keyboard access for all interactive controls.
- Do not rely on color alone for severity, status, confidence, or integration health.
- Keep dense operational data readable at expected dispatcher workstation sizes.
- Provide visible focus and confirmation states for user actions.

## Acceptance Criteria

- Storm metrics load
- Critical incidents are surfaced
- Storm exceptions are selectable
- View supports major event storytelling

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
