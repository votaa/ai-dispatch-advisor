# Scenario Comparison Screen Specification

## Purpose

Allow dispatch supervisors and storm coordinators to compare restoration or dispatch options and understand operational tradeoffs.

## Screen Visual

![What-If Scenario Analysis screen visual](<../../assets/screenshots/Scenario Analysis Dashboard.png>)

Screenshot status: Approved mockup PNG provided by project owner.

## Primary User

Dispatch Supervisor, Storm Response Coordinator

## Layout Specification

- Base recommendation summary
- Alternative option summary
- Tradeoff explanation
- Recommendation context panel

## Key UI Components

- Base recommendation
- Alternative strategy
- Tradeoff text
- Expected impact
- Confidence and constraints

## User Actions

- Review base recommendation
- Review alternative
- Use comparison to guide dispatcher instruction
- Future: save or approve scenario

## Data Requirements

- Selected incident
- Recommendation object
- Crew alternatives
- Customer impact
- Critical facility impact

## Backend and API Dependencies

- `POST /api/optimize`
- `Future: POST /api/scenarios/compare`
- `Future: GET /api/scenarios/{scenario_id}`

## AI and Recommendation Behavior

Scenario comparison should show why one option is preferred and what operational cost or risk is introduced by alternatives.

## Audit Requirements

Scenario selection or approval should create an audit event once scenario workflows become actionable.

## Accessibility Notes

- Preserve keyboard access for all interactive controls.
- Do not rely on color alone for severity, status, confidence, or integration health.
- Keep dense operational data readable at expected dispatcher workstation sizes.
- Provide visible focus and confirmation states for user actions.

## Acceptance Criteria

- Base and alternative options are visible
- Tradeoff language is clear
- Recommendation context remains available
- Scenario remains advisory until approved

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
