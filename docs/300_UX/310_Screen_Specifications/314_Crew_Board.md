# Crew Board Screen Specification

## Purpose

Show crew availability, capability, location, readiness, and assignment context so dispatchers can evaluate recommended and alternative crew options.

## Screen Visual

![Crew Board screen visual](<../../assets/screenshots/Utility Crew Dispatch Dashboard.png>)

Screenshot status: Approved mockup PNG provided by project owner.

## Primary User

Distribution Dispatcher, Field Crew Coordinator, Dispatch Supervisor

## Layout Specification

- Crew card/grid view
- Crew status indicator
- Capability label
- Location/staging point
- Shift availability

## Key UI Components

- Crew name
- Crew ID
- Home region
- Status
- Capability
- Current location
- Shift hours remaining
- Storm-ready flag

## User Actions

- Review available crews
- Compare crew capability
- Identify assigned or staged resources
- Use crew context during recommendation review

## Data Requirements

- Crews.csv
- Assignments.csv
- Crew capability data
- Shift status
- Location data

## Backend and API Dependencies

- `GET /api/crews`
- `GET /api/assignments`
- `Future: GET /api/v1/incidents/{incident_id}/crew-options`

## AI and Recommendation Behavior

Crew recommendations should consider availability, capability match, travel time, shift constraints, equipment, and safety constraints.

## Audit Requirements

Viewing crew board does not require audit. Assignment changes and recommendation actions must be audited.

## Accessibility Notes

- Preserve keyboard access for all interactive controls.
- Do not rely on color alone for severity, status, confidence, or integration health.
- Keep dense operational data readable at expected dispatcher workstation sizes.
- Provide visible focus and confirmation states for user actions.

## Acceptance Criteria

- Crew records load
- Availability state is readable
- Capability is visible
- Assigned and available crews are distinguishable

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
