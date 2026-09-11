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
- Clear and Ask Copilot buttons
- Question/answer history
- Advisory safety note

## Key UI Components

- Sample prompt chips
- Copilot text area
- Composer action row with `Clear` immediately left of `Ask Copilot`
- Conversation history
- Safety boundary message

## User Actions

- Ask about priority focus
- Ask about crews
- Ask about critical facilities
- Ask why recommendation was made
- Ask storm status
- Clear the default, previous, or partially entered question without clearing conversation history
- Enter free-form questions beyond the sample prompts

## Data Requirements

- Dashboard summary
- Selected incident
- Recommendation context
- Crew summary
- Critical facility summary
- Hazard and assignment context
- County, Township, and Village registry
- Deterministic crew-to-incident distance and estimated travel time
- Scenario and data-snapshot timestamps
- Server-authoritative request time with clock provenance and explicit skew status
- Bounded evidence references and response execution mode

## Backend and API Dependencies

- `POST /api/chat`
- Deterministic local Copilot query service
- Configurable server-side Copilot provider with Ollama Cloud as the POC default
- Rule-based fallback service

## AI and Recommendation Behavior

The current POC uses deterministic local services for supported factual and calculation questions, a grounded model call for bounded synthesis, and rule-based behavior as a visibly labeled fallback. The model must not supply incident, crew, recommendation, geography, distance, travel, customer, or demographic facts from general model knowledge. All modes retain strict no-action execution boundaries.

The empty-history helper copy is: “Ask about incidents, crews, hazards, facilities, geography, travel, or the overall scenario—or choose a sample question. Supported facts are answered from local scenario data; broader summaries and explanations use grounded AI.”

## Audit Requirements

Production may audit Copilot prompts/responses depending on policy. Copilot must not dispatch crews or write to source systems.

## Accessibility Notes

- Preserve keyboard access for all interactive controls.
- Expose Clear as a labeled native button and disable it for empty or whitespace-only composer input.
- Do not rely on color alone for severity, status, confidence, or integration health.
- Keep dense operational data readable at expected dispatcher workstation sizes.
- Provide visible focus and confirmation states for user actions.

## Completed POC Enhancements

- **POC-014 — Deterministic Crew Board queries:** Crew ID/name, status, capability, region,
  location, shift hours, storm readiness, assigned incidents, counts, combined filters, and
  bounded evidence-backed results are handled locally without provider calls. Explicit incident
  IDs and “this/selected incident” assignment questions return every currently assigned crew for
  that incident and remain distinct from available-crew recommendation questions.
- **POC-020 — Deterministic local-response readability:** Local answers now use concise semantic
  Markdown with totals first, bounded shown-versus-total results, expandable evidence, and
  incident-to-facility correlation for critical-facility questions.
- **POC-021 — Deterministic incident severity counts:** Critical, high, medium, and low severity
  counts are calculated from the complete active scenario in `local_query` mode, with bounded
  examples and incident evidence.
- **POC-017 — Temporal Copilot context:** Every new response and grounded provider context carries
  the server-received request time in UTC with `backend_server_clock` provenance and clock skew
  explicitly marked as `not_measured`. The response header displays the value in 24-hour UTC;
  older responses without the optional field remain readable.

## Open POC TODOs

## Acceptance Criteria

- Prompt examples are visible
- Free-form questions and prompt examples are supported
- Clear appears immediately left of Ask Copilot, clears only the composer, and preserves conversation history
- Clear is disabled when the composer contains no non-whitespace text
- The approved helper copy distinguishes local scenario facts from grounded-AI summaries and explanations
- Supported factual questions return active-scenario values without calling the model
- Grounded model responses cite only supplied scenario evidence
- County, Township, and Village answers resolve through the geographic registry
- Distance and travel-time answers use the same deterministic values as recommendations
- Response mode, evidence, data freshness, and advisory safety note are visible
- Server-received request time is visible on each new response and absent from the editable composer
- Provider failure produces an explicit unavailable warning and rule-based fallback when supported
- Conversation history is readable
- Copilot cannot execute or mutate a dispatch decision or assignment

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
- [POC-002 AI Copilot Implementation Plan](../../900_Delivery/908_POC_002_AI_Copilot_Implementation_Plan.md)
