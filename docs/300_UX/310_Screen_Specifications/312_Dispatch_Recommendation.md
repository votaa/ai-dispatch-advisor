# Dispatch Recommendation Screen Specification

## Purpose

Present an AI-generated restoration or dispatch recommendation that explains what action should be taken, why it is recommended, and expected customer impact while keeping the dispatcher in control.

## Screen Visual

![Dispatch Recommendation screen visual](<../../assets/screenshots/AI Dispatch Advisor Dashboard.png>)

Screenshot status: Approved mockup PNG provided by project owner. Supplemental dispatch-operations variant is included below.

## Supplemental Visual

![Dispatch Operations supplemental visual](<../../assets/screenshots/AI Dispatch Operations Dashboard.png>)

This alternate approved PNG shows a wider dispatch operations variant with AI explanation, policy references, restoration enablement, and alerts/constraints.

## Primary User

Electric Distribution Dispatcher / Control Room Operator

## Layout Specification

- Incident summary context
- AI recommended action panel
- Expected impact section
- Explanation factors and constraints
- Dispatcher action bar

## Key UI Components

- Selected incident identifier
- Recommended crew or switching action
- Confidence indicator
- Confidence uses title-case levels (for example, `High` or `Low`) with the supporting rationale on a separate line.
- Ranked feasible alternatives are compared with the recommended crew using suitability score, travel time, capability match, remaining shift time, storm readiness, and concise tradeoff language.
- Expected restoration or customer impact
- Factors list
- Constraints list
- Accept / Modify / Defer / Override controls

## User Actions

- Accept recommendation
- Modify recommendation with note
- Select a ranked feasible alternative and record the assignment as a modification with a required reason
- Defer recommendation
- Override recommendation with reason
- Review alternative options

## Data Requirements

- Incident record
- Crew suitability
- Network or feeder context
- Customer impact
- Critical facility impact
- SCADA/GIS/OMS context in future production implementation

## Backend and API Dependencies

- `POST /api/optimize`
- `POST /api/recommendation-actions`
- `GET /api/audit/events`

## AI and Recommendation Behavior

Recommendation output must include structured explanation factors, constraints, alternatives, confidence, and expected impact. Copilot may explain the recommendation but must not execute it.

## Audit Requirements

Every accept, modify, defer, or override action must create an audit event with timestamp, incident, user, recommendation state, reason/note when applicable, and original recommendation context.

For a modified alternative assignment, the audit event must retain the original recommended crew and ranked alternatives while separately recording the crew actually selected by the dispatcher.

## Accessibility Notes

- Preserve keyboard access for all interactive controls.
- Do not rely on color alone for severity, status, confidence, or integration health.
- Keep dense operational data readable at expected dispatcher workstation sizes.
- Provide visible focus and confirmation states for user actions.

## Acceptance Criteria

- Recommendation is clearly advisory
- Expected impact is visible
- Confidence and reasoning are visible
- The recommended crew remains visually distinct while ranked alternatives and their operational tradeoffs are visible when provided by the optimization response.
- Selecting an alternative visibly changes the pending crew choice, disables plain Accept, and requires a reason before the selected crew can be assigned.
- A stale, unavailable, or unranked crew selection is rejected without creating an assignment.
- Dispatcher action controls are explicit
- Override requires rationale once actions are implemented

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
