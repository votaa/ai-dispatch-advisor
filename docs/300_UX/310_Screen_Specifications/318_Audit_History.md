# Audit History Screen Specification

## Purpose

Provide traceability for recommendation generation, user review, accept/modify/defer/override actions, Copilot advisory activity where required, and integration writeback events.

## Screen Visual

![Audit History screen visual](<../../assets/screenshots/audit-history.svg>)

Screenshot status: Placeholder visual. Approved mockup PNG has not been provided yet.

## Primary User

Dispatch Supervisor, Operations Analyst, Compliance Reviewer

## Layout Specification

- Audit event filters
- Event timeline/table
- Selected event detail
- Recommendation snapshot panel

## Key UI Components

- Event ID
- Timestamp
- User
- Incident
- Action type
- Reason/note
- Recommendation version
- Source data snapshot

## User Actions

- Filter audit events
- Inspect recommendation action
- Review override rationale
- Export event summary in future iteration

## Data Requirements

- Recommendation action events
- Audit event store
- User identity
- Recommendation snapshot
- Source metadata

## Backend and API Dependencies

- `Future: GET /api/audit-events`
- `Future: GET /api/recommendation-actions`
- `Future: GET /api/recommendations/{id}/history`

## AI and Recommendation Behavior

Audit records should capture AI recommendation context, algorithm/model version, and explanation metadata when available.

## Audit Requirements

This screen displays audit data and should itself enforce strict role-based access.

## Accessibility Notes

- Preserve keyboard access for all interactive controls.
- Do not rely on color alone for severity, status, confidence, or integration health.
- Keep dense operational data readable at expected dispatcher workstation sizes.
- Provide visible focus and confirmation states for user actions.

## Acceptance Criteria

- Events are searchable
- Override reasons are visible
- Original recommendation context is preserved
- Sensitive audit data is role-restricted

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
