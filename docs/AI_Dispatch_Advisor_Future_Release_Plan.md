# AI Dispatch Advisor Future Release Plan

## Summary

Deliver two releases:

1. **Release 1 — Operational UI and usability:** consistent search, filtering, sorting, reset controls, responsive tables, corrected recommendation layouts, Crew Board filtering, and normalized crew IDs.
2. **Release 2 — LLM-backed AI Copilot:** add a hybrid Copilot that answers supported facts deterministically and uses a configurable model only for grounded advisory synthesis.

## Delivery Sequencing

A contract-neutral POC usability patch was completed on 2026-08-10 before Phase 4. It intentionally changed presentation only and did not add or alter backend data contracts.

Completed in the POC usability patch:

- Wider Dashboard, Dispatch, and Scenario recommendation workspaces on desktop.
- Responsive 2×2 recommendation actions that stack on narrow screens.
- Overflow protection for recommendation text, factors, constraints, forms, and recent actions.
- Full-width Storm Exceptions content.
- One reusable, keyboard-focusable responsive table shell for Dashboard, Dispatch, Incidents, and Storm Exceptions.
- Contained horizontal table scrolling without page-level overflow at desktop, tablet, or mobile widths.

Phase 6 subsequently delivered shared incident search, cascading severity and region filters with remaining counts, sortable operational columns, pagination, Crew Board search and faceted filtering, crew-ID presentation, read-only detail navigation, recommendation comparison, ranked-alternative assignment, and accessibility improvements. The more extensive per-column filtering, match highlighting, and Reset behavior described below remain future refinements rather than Phase 6 blockers.

## Release 1 — UI and Data Presentation

- Build a reusable table experience for Dashboard, Dispatch, Incidents, and Storm Exceptions:
  - Provide a global search field across all searchable displayed columns.
  - Search filters the table to matching rows; it is not merely browser-style find-on-page.
  - Match search terms case-insensitively using partial-text matching.
  - Search incident IDs, regions, customer counts, severities, hazards, crew names/IDs, decisions, and displayed ETR values.
  - Highlight the matching text within retained rows where applicable.
  - Provide typed column filters:
    - Incident and hazard text.
    - Region, severity, assigned crew, and decision selections.
    - Customer-count range.
    - ETR date/time range.
  - Combine global search and column filters using AND logic: a row must satisfy the search and every active filter.
  - Let every column header sort ascending or descending when clicked.
  - Show both sort arrows in a neutral state and emphasize the active direction.
  - Preserve active search, filters, and sorting while the user remains on that tab.
  - Display a clearly labeled **Clear** or **Reset** control whenever search, filters, or non-default sorting is active.
  - Reset clears the search text and all filters, removes search highlighting, and restores that tab’s original default sort order.
  - Disable or hide Reset when the table is already in its default state.
  - Use available screen width; enable horizontal scrolling only when the viewport cannot accommodate minimum readable column widths.
  - Show an explicit “No matching records” state with a Reset action when search or filters return no rows.

- **POC usability patch complete:** Fix the Dashboard, Dispatch, and Scenario recommendation panels:
  - Allocate more desktop width to the recommendation column.
  - Arrange Accept, Modify, Defer, and Override in a responsive 2×2 grid.
  - Stack controls on narrow screens.
  - Prevent buttons, factors, constraints, and recent actions from overflowing their card.

- Enhance Crew Board:
  - Add global crew search that filters cards to matching crews.
  - Search crew name, crew ID, company, status, location, and assigned incident where available.
  - Add filters for status, crew, and company.
  - Support assigned, available, and staged statuses.
  - Combine search and filters using the same AND behavior as the tables.
  - Provide Reset whenever Crew Board search or filters are active.
  - Keep the descriptive crew name and expose a separate alphanumeric crew-ID field.
  - Derive IDs from the source designation and number, including `Tree-4735`, `WW-4739`, `CNTR-3896`, and `MUA-4497`.
  - Do not invent prefixes for crews whose source identifiers are numeric-only; retain their existing presentation.

- Improve visible crew identity without changing recommendation behavior:
  - Display the existing crew ID beside the descriptive crew name on Crew Board cards.
  - Display the existing crew ID beside recommended and assigned crew names in recommendation panels.
  - Keep supervisor-review or no-feasible-crew states free of misleading placeholder IDs.
  - Treat this as a separate UI usability item after the behavior-preserving Phase 5.1 package.

- Storm Exceptions uses the full available content width and shared responsive table shell. Shared severity and region facets, counts, sorting, and pagination are implemented; match highlighting, more extensive per-column filters, and Reset behavior remain future Release 1 refinements.

## Release 2 — LLM-Backed POC Copilot

The detailed, controlling scope is the [POC-002 AI Copilot implementation plan](900_Delivery/908_POC_002_AI_Copilot_Implementation_Plan.md). Phase 7 remains paused and is not a dependency for this bounded POC enhancement.

- Retain the existing sample questions as shortcuts while allowing free-form questions.
- Route supported incident, recommendation, crew, hazard, critical-facility, geography, distance, and travel-time questions through deterministic local services without calling the model.
- Use a configurable server-side provider for bounded synthesis and explanation; default to Ollama Cloud with the owner-selected model and keep credentials out of the browser.
- Ground model calls only in selected active-scenario facts and evidence. The model is not an authoritative lookup source for operational, geographic, customer, or demographic facts.
- Normalize canonical demo geography as County to Township to Village, treating villages, hamlets, CDPs, and neighborhoods as the lowest user-facing level.
- Generate and owner-review a purpose-built `long-island-copilot-demo` fixture before publishing it.
- Preserve the current rule-based responder as a visible degraded mode when the provider is disabled or unavailable.
- Show execution mode, source/evidence, data freshness, provider warnings, loading, empty-data, error, and timeout states.
- Preserve the advisory-only boundary; Copilot cannot execute or mutate dispatch actions.
- Keep a future PSEG Long Island customers-served reference or adapter in `POC-012`, outside the POC-002 critical path.

## Interfaces and Data Changes

- Standardize each searchable view’s state as:
  - Global search query.
  - Per-column or per-card filters.
  - Active sort column and direction.
  - View-specific default sort definition.
  - Derived indicator showing whether Reset should be available.
- Extend crew presentation data with separate `displayName`, optional normalized `crewId`, `company`, and `status` fields.
- Preserve the backend Copilot request interface containing the user question and active scenario identifier.
- Extend the response compatibly with execution mode, scenario and snapshot timestamps, bounded evidence, optional provider/model identity, and visible fallback or partial-data warnings.

## Test and Acceptance Plan

- Verify search filters rows or crew cards rather than merely locating text on the page.
- Verify search is case-insensitive, supports partial matches, and highlights matching text in retained results.
- Verify each applicable table can filter and sort every displayed column.
- Verify combined search and filters return only records satisfying all active criteria.
- Verify Reset appears after search, filtering, or non-default sorting.
- Verify Reset clears all active criteria and restores the correct default ordering for each tab.
- Verify the no-results state provides a working Reset action.
- Test text, numeric, enum, and date sorting, including missing values.
- Confirm tables use full desktop width and scroll horizontally without clipping at narrower widths.
- Test Dispatch and Scenario at desktop, tablet, and mobile widths; all four action buttons must remain visible and usable.
- Verify Crew Board status, crew, and company filters individually and together.
- Confirm alphanumeric crew IDs use their source prefixes and numeric-only crews remain unchanged.
- Confirm Crew Board and recommendation panels show each available crew ID beside the correct descriptive name, while no-crew recommendations show no placeholder ID.
- Confirm deterministic factual answers use fixture-expected values and do not call the model provider.
- Confirm grounded synthesis changes when the selected scenario or underlying data changes and cites only supplied evidence.
- Confirm every canonical incident and crew location resolves through the County/Township/Village registry.
- Confirm crew-to-incident distance and travel estimates are deterministic, realistic for the canonical Long Island fixture, and consistent with recommendation inputs.
- Verify Copilot handles unsupported questions, stale or missing data, timeouts, and provider failures safely.
- Confirm Copilot cannot accept, modify, defer, override, or otherwise execute dispatch decisions.

## Assumptions

- Release 1 precedes the AI integration so immediate presentation and usability improvements can ship independently.
- Global search filters results and highlights matches; it is not a simple find-on-page feature.
- Search and column filters combine using AND logic.
- Reset returns each view to its existing view-specific default order rather than imposing one universal order.
- Crew-ID prefixes come from structured scenario data and are never inferred from descriptive crew names.
- The current human-approval requirement remains unchanged.
- The canonical Copilot scenario is generated dry-run-first and is not published until owner review.
