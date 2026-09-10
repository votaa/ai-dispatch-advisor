# POC Feedback Log

## Purpose

This log captures observations, enhancement ideas, defects, demo issues, and new requirements discovered while using the AI Dispatch Advisor proof-of-concept. It is intended to preserve feedback without disrupting the documentation batch plan.

Items in this log should later be reviewed and converted into requirement updates, backlog items, UX revisions, API changes, architecture decisions, or implementation tasks.

## How to Use This Log

Add one row for each observation. Keep entries concise enough to scan, but specific enough to act on later.

Recommended usage:

- Record feedback as soon as it is noticed.
- Do not try to solve or fully specify every item immediately.
- Use clear categories and priority.
- Link to affected docs, files, or app areas when known.
- Review this log during planned revision cycles.

## Status Definitions

| Status | Meaning |
| --- | --- |
| New | Captured but not reviewed |
| Accepted | Agreed that this should become future work |
| Needs Clarification | Requires more detail before action |
| Converted | Converted into a requirement, backlog item, issue, or task |
| Deferred | Valid but intentionally postponed |
| Closed | Addressed or no longer relevant |

## Category Definitions

| Category | Meaning |
| --- | --- |
| Feature | New product capability or workflow |
| Enhancement | Improvement to an existing capability |
| Defect | Something appears broken or misleading |
| UX | Usability, layout, navigation, accessibility, or interaction feedback |
| Data | Demo data, scenario data, data quality, or data model feedback |
| API | Backend contract, endpoint, or integration behavior |
| AI | Recommendation, optimization, explainability, or Copilot behavior |
| Documentation | Documentation gap, inconsistency, or revision need |
| Demo | POC storytelling, scenario, setup, or presentation improvement |

## Priority Definitions

| Priority | Meaning |
| --- | --- |
| P1 | Important for near-term POC credibility or core workflow |
| P2 | Important but can wait until after the current batch or milestone |
| P3 | Useful improvement or future consideration |

## Feedback Items

| ID | Date | Category | Priority | Area | Observation | Suggested Next Step | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| POC-001 | 2026-08-02 | UX | P1 | Recommendation actions | Accept, Modify, Defer, and Override controls are visible but not yet demo-functional. | Implemented local decision persistence, required reasons for Defer and Override, visible decision status, recent history, and accepted assignment state. | Closed |
| POC-002 | 2026-08-02 | AI | P2 | AI Copilot | Copilot responses are currently keyword-based demo responses, not real AI model output. | After owner approval, implement the [proposed POC-002 AI Copilot plan](900_Delivery/908_POC_002_AI_Copilot_Implementation_Plan.md): deterministic local answers for operational and geographic facts, grounded Ollama Cloud synthesis for broader free-form questions, and a visible rule-based fallback. Use a generated Long Island demo fixture and keep the Copilot advisory-only. | Converted |
| POC-003 | 2026-08-10 | UX | P1 | Primary page states | Several primary views could render blank content or show an indefinite recommendation-loading message when data was empty or unavailable. | Added explicit loading, empty, error, and retry states with frontend coverage across the POC workflow. | Closed |
| POC-004 | 2026-08-10 | Documentation | P1 | Scenario smoke testing | The four-scenario smoke-test wording could be interpreted as a product limit after dynamic scenario generation and discovery were added. | Retained the four scenarios as deterministic regression fixtures and added a separate test for every dynamically discovered scenario. | Closed |
| POC-005 | 2026-08-10 | UX | P1 | Responsive demo layout | Recommendation panels were too narrow, action buttons crowded into one row, Storm Exceptions did not use the full grid, and tables could force awkward page layouts. | Added wider recommendation workspaces, responsive 2×2/stacked actions, overflow containment, full-width Storm Exceptions, and a shared responsive table shell. | Closed |
| POC-006 | 2026-08-13 | UX | P2 | Crew identity | Crew IDs such as `CR-01`, `SC-06`, and `FC-01` are available in API data but are not visible beside crew names on Crew Board or in the recommendation panel, making manual recommendation verification harder. | In a separate UI usability change after Phase 5.1, display the crew ID beside the descriptive crew name on Crew Board cards and for recommended and assigned crews; preserve the name as the primary label and cover populated and no-crew states with frontend tests. | Closed |
| POC-007 | 2026-08-16 | UX | P2 | Large-scenario loading | `august-storm-preview` can briefly show an empty recommendation state while its large incident set is still loading and ranking. | Keep recommendation state in loading mode during scenario refresh, disable scenario switching while data loads, and provide explicit large-scenario progress messaging with delayed-response frontend coverage. | Closed |
| POC-008 | 2026-08-16 | UX | P2 | Crew Board controls | Crew Board cards do not yet provide the shared incident-queue search, filtering, and sorting workflow. | After the current incident-table fixes, add Crew Board search and status/capability/region/storm-readiness filters with a labeled sort selector and ascending/descending control; preserve the card layout and add pagination for large crew lists. | Closed |
| POC-009 | 2026-08-16 | UX | P2 | Operational faceted filtering | Crew Board filters combined correctly but listed values from the full crew set, and applying different behavior to incident Severity and Region filters would be inconsistent. | Added cascading remaining-result counts, visible disabled zero-result choices, and active-selection preservation to Crew Board and the Dashboard, Dispatch, Incidents, and Storm Mode queues, with counts scoped to each view's dataset. | Closed |
| POC-010 | 2026-08-16 | Data | P2 | Scenario generator crew locations | Generated crew staging locations used inconsistent RDA/MUA formatting, including values such as `RDA7MUA Staging`, `RDA10MUA Staging`, and `RDAMUA16 Staging`, while the frontend correctly displayed the source value verbatim. | Normalized all RDA/MUA location templates to `RDA<number> MUA Staging`, regenerated the affected preview and demo `Crews.csv` files, and added independent regression coverage for the exact approved location set. | Closed |
| POC-011 | 2026-08-16 | Workflow | P1 | Alternative crew assignment | Ranked alternatives were visible for comparison, but the dispatcher could only accept the top recommendation and could not dispatch a lower-ranked feasible crew. | Added explicit alternative selection, required modification rationale, ranked-membership and live-availability validation, selected-crew assignment overlays, and audit evidence preserving both the original recommendation and actual crew choice. | Closed |
| POC-012 | 2026-08-21 | Data | P2 | PSEG Long Island outage-area reference | The public [PSEG Long Island outage-area report](https://outagemap.psegliny.com/reports/be6c533e-409e-4f3a-8d62-799b65331056) exposes a County/Township/Village hierarchy with customers served, customers affected, affected percentage, ETR, and update time that could ground Copilot geographic and customer-impact questions. | Determine whether PSEG Long Island or KUBRA provides an approved structured feed or reuse terms. For the POC, prefer a timestamped, provenance-labeled reference snapshot; later add a read-only adapter with caching, schema-drift detection, freshness metadata, and graceful fallback. The LLM may explain retrieved values but must not scrape the page or supply them from model memory. | New |
| POC-013 | 2026-08-21 | UX | P2 | AI Copilot selected incident and crew context | The selected incident persists across tabs and is sent with Copilot questions, while the selected crew persists for Crew Board/detail navigation but is not sent to Copilot. Neither selection is visible on the Copilot view, so references such as “this incident” or “this crew” can be ambiguous to the operator or during a demo. | Add an accessible, non-editable context banner showing the selected incident and selected crew, for example `Selected incident: ESD-20260821-0002 · Arverne` and `Selected crew: 3533 · Western Suffolk Troubleshooter 3533`. Extend the Copilot request with an optional selected crew ID and use it to resolve crew-relative questions; update or clear both contexts immediately when selections or scenarios change, provide explicit no-selection states, and cover cross-tab selection, crew-relative questions, and scenario-reset behavior with frontend and API tests. | New |
| POC-014 | 2026-08-21 | AI | P2 | AI Copilot Crew Board queries | Copilot supports aggregate crew availability and incident-specific recommendations, but it cannot reliably query every Crew Board parameter; for example, “what crews are not storm ready” is misrouted as a recommended-crew question. | Implemented deterministic local-query support for crew ID/name, availability status, capability, home region, current location, shift hours remaining, storm readiness, assigned incidents and assignment count, and derived travel time to the selected incident. The service now routes Crew Board intents before generic recommendation phrases, distinguishes availability from storm readiness, supports combined filters and bounded result lists, and returns crew-record evidence without using model memory. Covered by backend local-query and API tests. | Closed |
| POC-015 | 2026-08-21 | UX | P2 | AI Copilot composer and response readability | The question field remains populated with the default or last question, the empty-state copy implies that only sample questions are supported, and longer grounded-AI responses render as a dense run-on block even when the response contains paragraph or section breaks. | Added a secondary `Clear` button immediately left of `Ask Copilot`; it clears only the question composer, preserves conversation history, and is disabled for empty or whitespace-only input. Replaced the empty-state copy with: “Ask about incidents, crews, hazards, facilities, geography, travel, or the overall scenario—or choose a sample question. Supported facts are answered from local scenario data; broader summaries and explanations use grounded AI.” Copilot responses retain safe semantic Markdown rendering without raw HTML, with frontend coverage for clearing, revised copy, local answers, execution metadata, and multi-block grounded responses. | Closed |
| POC-016 | 2026-08-24 | Data | P2 | Scenario freshness metadata | When scenario data is updated or a file is uploaded, the operator needs a visible reference to how current the scenario is. | Capture the authoritative file-upload or scenario-update datetime in scenario metadata and expose it in the UI as `Scenario Last Updated MM/DD/YYYY HH:MM` using a documented 24-hour timezone convention; preserve source/provenance and cover scenario switching and unavailable metadata. | New |
| POC-017 | 2026-08-24 | AI | P2 | AI Copilot temporal context | Copilot requests currently lack an explicit request-time context, limiting future time-aware analysis such as identifying expired ETRs or calculating incident age from its created date. | Capture the server-authoritative request datetime in the submitted Copilot context without displaying it in the composer, and echo the timestamp in the response header using the same `MM/DD/YYYY HH:MM` 24-hour convention. Use the timestamp in a future enhancement for ETR expiration and incident-age calculations, with timezone, clock-skew, provenance, and backward-compatible API behavior defined before implementation. | New |
| POC-018 | 2026-08-24 | UX | P2 | Incident queue critical-facility visibility | The Incident Queue and Active Incidents tables do not show the per-incident critical-facility flag; operators must open Incident Details to see whether a critical facility is affected. | Add a compact `Critical Facility` column or badge to the incident tables, and optionally add a critical-facility filter. Preserve the existing Incident Details field and cover visible Yes/No states, filtering, responsive layout, and scenario changes with frontend tests. | New |
| POC-019 | 2026-08-24 | AI | P3 | Level-specific critical-facility scoring | The POC will classify DPS-aligned Level 1, Level 2, and Level 3 facilities as `critical`, `high`, and `medium`, while all remain eligible for the current critical-facility flag and flat recommendation bonus. | Evaluate whether incident-priority scoring should differentiate Level 1, Level 2, and Level 3 facility impacts after owner/SME review and a representative evaluation dataset; preserve the current flat scoring until approved. | New |
| POC-020 | 2026-08-24 | UX | P2 | AI Copilot local-response readability | Deterministic `local_query` responses use the safe Markdown renderer but are assembled as plain text. Large results can therefore render as one dense paragraph; for example, the critical-facility query for `august-storm-preview` displayed 47 incidents and 34 matched facilities inline, followed by 81 evidence records. The incident list and matched-facility list are also presented separately, so an operator cannot readily tell which facility record supports each incident. The grounded-AI Markdown briefing instructions do not apply to this non-LLM path. | Implemented concise deterministic Markdown responses with totals first, short sections, bounded shown-versus-total lists, and expandable complete evidence. Critical-facility results now correlate each displayed facility record with incident ESD ID, municipality, feeder, facility identity, type, and priority, preserving one-to-many matches and identifying unmatched incidents. Provider use, factual calculations, API envelope, grounding, and advisory-only behavior are unchanged. Covered by backend service and frontend response-rendering tests. | Closed |
| POC-021 | 2026-08-24 | AI | P2 | AI Copilot incident severity counts | Questions such as “how many active incidents have a severity of critical?” and “How many severity Low incidents” are not recognized as deterministic local queries. They fall through to grounded AI, whose bounded context includes only five ranked incidents, causing `august-storm-preview` to report 5 critical and 0 low instead of the complete active-scenario counts shown by the incident filters: 229 critical, 972 high, 394 medium, and 405 low. | Implemented deterministic local-query routing for complete active-incident severity counts across `critical`, `high`, `medium`, and `low`. The provider is bypassed, exact totals are reported first, examples are bounded, and incident evidence is retained without placing the full dataset inline. Covered capitalization and natural-language variants, every severity value, empty results, selected-incident context, scenario switching, and provider bypass through backend and frontend tests. | Closed |
| POC-022 | 2026-08-24 | UX | P2 | Dashboard priority incident display limit | The Dashboard panel was labeled `Priority Dispatch Queue`, but the dashboard API returned only the first five deterministically ranked incidents. The label did not disclose that display limit, and the operator could not request a larger ranked subset without navigating away. | Implemented a percentage-based `Incidents shown` selector with 25%, 50%, 75%, and 100% options. The panel label and search label reflect the computed subset, for example `Top 500 Priority Incidents` and `Search Top 500 Incidents Shown` in a 2,000-incident scenario. The Dashboard uses the full active incident collection already loaded by the application, preserves deterministic order and pagination, shows shown-versus-total text, and handles empty scenarios. Added frontend coverage for percentage changes and empty/small scenarios. | Closed |
| POC-023 | 2026-09-10 | UX | P2 | Search typeahead suggestions with match counts | Search fields on the Dashboard, Dispatch, Incidents, Storm Mode, and Crew Board views currently filter only after text is entered. Operators would benefit from typeahead suggestions derived from the active scenario data—for example, entering `FDR-ES-` could suggest `FDR-ES-03 (… matches)`, `FDR-ES-13 (… matches)`, and `FDR-ES-34 (… matches)`, while `East` could suggest matching municipalities such as East Hampton and East Meadow. | Evaluate a reusable accessible **autocomplete/typeahead combobox with grouped facet suggestions and result counts**. Suggestions should be computed from the same filtered dataset and fields already searchable in each view, sorted by descending match count with a deterministic alphabetical/identifier tie-breaker, and show counts in parentheses. Selecting a suggestion should apply it as the search term and preserve existing AND filtering, cascading facet counts, pagination, scenario changes, and shown-versus-total behavior. Prefer a lightweight headless combobox pattern (for example Downshift or React Aria) over a native `datalist`, which does not provide reliable grouped labels, counts, keyboard semantics, or styling. Keep the first implementation client-side for the current POC dataset; move to debounced server-side suggestions only if dataset size or latency requires it. Estimated complexity: medium (shared component, suggestion indexing/counting, keyboard/accessibility behavior, responsive rendering, and cross-view regression coverage). Recommended timing: after current POC smoke-test fixes and before production-scale search; defer provider/API work until measured client-side performance warrants it. | New |

## Review Cadence

Review this log:

- After each major documentation batch.
- After each POC feature enhancement.
- Before revising product requirements.
- Before creating implementation backlog or GitHub issues.
- Before stakeholder demos.

## Conversion Guidance

When an item is ready to act on:

- Convert product behavior into `docs/100_Product/105_Product_Requirements.md`.
- Convert workflow changes into `docs/100_Product/104_User_Workflows.md`.
- Convert UX changes into `docs/300_UX/`.
- Convert API changes into `docs/400_Backend_API/`.
- Convert frontend implementation guidance into `docs/500_Frontend/`.
- Convert AI, data, or optimization changes into `docs/600_Data_AI/`.
- Convert delivery work into `docs/900_Delivery/` or GitHub issues.
- Record major decisions in `docs/001_Decision_Log.md`.

## Related Documents

- [Documentation Index](000_Document_Index.md)
- [Documentation Roadmap](002_Documentation_Roadmap.md)
- [Product Requirements](100_Product/105_Product_Requirements.md)
- [Recommendation Experience](300_UX/303_Recommendation_Experience.md)
