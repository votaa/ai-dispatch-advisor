# AI Copilot Screen Specification

## Purpose

Provide advisory natural-language assistance for summarizing dispatch context, explaining recommendations, and answering operational questions against available data.

## Screen Visual

![AI Operations Copilot screen visual](<../../assets/screenshots/Utility Dispatch Advisor Dashboard.png>)

Screenshot status: Approved mockup PNG provided by project owner.

## Primary User

Distribution Dispatcher, Dispatch Supervisor, Operations Analyst

## Layout Specification

- Prompt examples
- Text input
- Ask button
- Question/answer history
- Advisory safety note

## Key UI Components

- Sample prompt chips
- Copilot text area
- Conversation history
- Safety boundary message

## User Actions

- Ask about priority focus
- Ask about crews
- Ask about critical facilities
- Ask why recommendation was made
- Ask storm status

## Data Requirements

- Dashboard summary
- Selected incident
- Recommendation context
- Crew summary
- Critical facility summary

## Backend and API Dependencies

- `POST /api/chat`
- Future: AI service endpoint with retrieval context

## AI and Recommendation Behavior

Current POC is keyword-based. Target implementation should use a governed AI service with retrieved operational context and strict no-action execution boundaries.

## Audit Requirements

Production may audit Copilot prompts/responses depending on policy. Copilot must not dispatch crews or write to source systems.

## Accessibility Notes

- Preserve keyboard access for all interactive controls.
- Do not rely on color alone for severity, status, confidence, or integration health.
- Keep dense operational data readable at expected dispatcher workstation sizes.
- Provide visible focus and confirmation states for user actions.

## Acceptance Criteria

- Prompt examples are visible
- Responses vary by common prompt intent
- Conversation history is readable
- Safety note is visible

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
