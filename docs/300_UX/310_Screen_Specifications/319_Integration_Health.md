# Integration Health Screen Specification

## Purpose

Show operational health, freshness, and degraded-state information for OMS, GIS, SCADA, crew, weather, AMI, identity, and related enterprise integrations.

## Screen Visual

![Integration Health screen visual](<../../assets/screenshots/integration-health.svg>)

Screenshot status: Placeholder visual. Approved mockup PNG has not been provided yet.

## Primary User

Utility IT Administrator, Dispatch Supervisor, Support Engineer

## Layout Specification

- Integration status summary
- System health table
- Freshness indicators
- Recent errors or degraded-state notes

## Key UI Components

- System name
- Status
- Last successful update
- Latency
- Staleness
- Message
- Severity

## User Actions

- Review degraded integrations
- Inspect source freshness
- Escalate support issue
- Future: retry adapter or disable source in non-production

## Data Requirements

- Integration health events
- Adapter status
- Source freshness metadata
- Error logs

## Backend and API Dependencies

- `Future: GET /api/v1/integrations/health`
- `Future: GET /api/v1/integrations/{system}/events`

## AI and Recommendation Behavior

Recommendation confidence should reflect degraded or stale integrations and surface relevant warnings in recommendation explanations.

## Audit Requirements

Administrative actions such as disabling integrations or retrying writeback should be audited.

## Accessibility Notes

- Preserve keyboard access for all interactive controls.
- Do not rely on color alone for severity, status, confidence, or integration health.
- Keep dense operational data readable at expected dispatcher workstation sizes.
- Provide visible focus and confirmation states for user actions.

## Acceptance Criteria

- Health status is clear
- Stale data is visible
- Degraded state can be understood by operations users
- Secrets and sensitive diagnostics are not exposed

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
