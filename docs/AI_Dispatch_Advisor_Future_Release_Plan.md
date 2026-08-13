# AI Dispatch Advisor Future Release Plan

## Summary

Deliver two releases:

1. **Release 1 — Operational UI and usability:** consistent search, filtering, sorting, reset controls, responsive tables, corrected recommendation layouts, Crew Board filtering, and normalized crew IDs.
2. **Release 2 — LLM-backed AI Copilot:** replace canned responses with advisory analysis grounded in current dispatch and scenario data.

## Delivery Sequencing

A contract-neutral POC usability patch was completed on 2026-08-10 before Phase 4. It intentionally changed presentation only and did not add or alter backend data contracts.

Completed in the POC usability patch:

- Wider Dashboard, Dispatch, and Scenario recommendation workspaces on desktop.
- Responsive 2×2 recommendation actions that stack on narrow screens.
- Overflow protection for recommendation text, factors, constraints, forms, and recent actions.
- Full-width Storm Exceptions content.
- One reusable, keyboard-focusable responsive table shell for Dashboard, Dispatch, Incidents, and Storm Exceptions.
- Contained horizontal table scrolling without page-level overflow at desktop, tablet, or mobile widths.

The remaining Release 1 search, filtering, sorting, highlighting, Reset, Crew Board, and crew-identity work should follow the Phase 4 domain and API foundation.

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

- Storm Exceptions now uses the full available content width and shared responsive table shell. Shared search, filter, sort, and Reset behavior remains future Release 1 work.

## Release 2 — Real AI Copilot

- Retain the existing sample questions as shortcuts while allowing free-form questions.
- Send Copilot requests through a server-side LLM service; do not expose credentials in the browser.
- Ground each request in the active scenario and current incidents, crews, recommendations, decisions, hazards, facilities, and ETR data.
- Replace canned answer matching with generated operational analysis that:
  - Answers the dispatcher’s actual question.
  - Distinguishes known data from analysis or uncertainty.
  - Refuses to fabricate unavailable information.
  - Preserves the advisory-only boundary and cannot execute dispatch actions.
- Show loading, empty-data, provider-error, and timeout states.
- Include the data snapshot timestamp in responses so dispatchers understand freshness.
- Log request metadata and failures without storing credentials or unnecessary sensitive prompt content.

## Interfaces and Data Changes

- Standardize each searchable view’s state as:
  - Global search query.
  - Per-column or per-card filters.
  - Active sort column and direction.
  - View-specific default sort definition.
  - Derived indicator showing whether Reset should be available.
- Extend crew presentation data with separate `displayName`, optional normalized `crewId`, `company`, and `status` fields.
- Add a backend Copilot request interface containing the user question and active scenario identifier.
- Return the generated answer, data timestamp, and structured error state from the Copilot service.

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
- Confirm generated Copilot answers change when the selected scenario or underlying data changes.
- Verify Copilot handles unsupported questions, stale or missing data, timeouts, and provider failures safely.
- Confirm Copilot cannot accept, modify, defer, override, or otherwise execute dispatch decisions.

## Assumptions

- Release 1 precedes the AI integration so immediate presentation and usability improvements can ship independently.
- Global search filters results and highlights matches; it is not a simple find-on-page feature.
- Search and column filters combine using AND logic.
- Reset returns each view to its existing view-specific default order rather than imposing one universal order.
- Crew-ID prefixes come from structured scenario data and are never inferred from descriptive crew names.
- The current human-approval requirement remains unchanged.
