# POC-036–045 Operations Map Enhancement Implementation Plans

## Status and purpose

This is a documentation-only planning artifact for review and discussion. It does not authorize implementation, fixture publication, dependency installation, or changes to application behavior.

The ten enhancements are tracked separately so that each can be reviewed, accepted, deferred, implemented, and validated independently. They are grouped below into four implementation plans according to shared foundations, delivery risk, and estimated effort.

## Planning assumptions and boundaries

- POC-035 remains the implemented baseline: read-only scenario incidents, approximate crew village centers, clustering, search, basic filters, record selection, and links to existing incident and crew workflows.
- The map remains advisory and read-only. Dispatch, reassignment, recommendation decisions, and operational writes remain in their existing workflows.
- Incident coordinates are synthetic. Crew coordinates are approximate village centers rather than live GPS.
- Resolved metadata and shared contracts remain authoritative. Map work must not create competing severity, critical-facility, geography, assignment, or crew-readiness mappings.
- Unknown, unmapped, incomplete, and ranking-withheld records remain visible and explicitly labeled; they must not be silently inferred or discarded.
- Advanced geography or contextual layers require qualified, validated sources before UI implementation. A manifest filename alone is not proof that a layer is complete or safe to display.
- Every plan requires keyboard access, responsive behavior, scenario-change cleanup, deterministic counts, and regression coverage proportionate to the affected shared behavior.

## Effort scale

| Estimate | Planning meaning |
| --- | --- |
| Small | Localized UI behavior using existing state and authoritative fields; limited shared-contract change |
| Medium | Shared components or cross-view state, multiple affected surfaces, and broader regression coverage |
| Large | New data or geometry contract, backend/API work, source qualification, or substantial map rendering complexity |
| Extra large | Multiple new governed sources or integration boundaries; should be decomposed before approval |

Effort is relative and intentionally non-numeric until each plan is approved and decomposed into implementation tasks.

## Recommended implementation order

| Order | Plan | POCs | Combined effort | Why this order |
| --- | --- | --- | --- | --- |
| 1 | Navigation foundation | POC-041, POC-042, POC-043, POC-045 | Medium–Large | Establishes the reusable entity destinations and state-transfer rules needed by later map drill-down and drill-up work. It also closes the highest-value workflow gaps using existing records. |
| 2 | Operational filters and visual encoding | POC-036, POC-037 | Medium | Uses fields already present in the incident and crew contracts and makes the current map materially more useful without requiring new geography sources. |
| 3 | Relationship and summary exploration | POC-038, POC-044 | Medium–Large | Builds on shared navigation and filter context to connect assignments and move between map subsets and complete operational views. |
| 4 | Advanced geospatial context | POC-039, POC-040 | Large–Extra large | Requires geometry/source qualification and new aggregate or overlay contracts. Deferring it prevents UI work from outrunning data governance. |

Plans 1 and 2 can be reviewed together, but Plan 1 should establish the navigation contract before Plan 3 is implemented. Plan 4 should not begin until its source and ownership decisions are approved.

## Plan 1 — Navigation foundation

### Included enhancements

- **POC-041 — Cross-view Show on Map action**
- **POC-042 — Clickable related operational entities**
- **POC-043 — Preserved cross-view return navigation**
- **POC-045 — Standard contextual navigation panel**

### Goal

Create one predictable entity-navigation model across Dashboard, Dispatch, Incidents, Crew Board, Storm Mode, and Operations Map. A user should be able to move from a record to its detail, related records, map location, or broader summary and then return without losing valid working context.

### Suggested delivery slices

1. **Destination and state contract — Medium**
   - Define supported entity destinations and distinguish `open detail`, `select`, `filter`, `show on map`, and `open summary` behavior.
   - Define which state is transferable and which state is view-local.
   - Define scenario-change invalidation, unmapped-record behavior, browser-history expectations, focus restoration, and accessible link/button semantics.
2. **Show on Map and entity links — Medium**
   - Add the reusable `Show on map` path for incident and crew records.
   - Link authoritative assigned-incident, assigned-crew, municipality, feeder, and critical-facility references only where a deterministic destination exists.
3. **Return path and contextual panel — Medium**
   - Add a bounded return trail that restores valid source-view state.
   - Apply the shared full-detail / related-records / broader-summary-or-map pattern without exposing invalid destinations.

### Acceptance themes

- Cross-view actions resolve the same authoritative record and never depend on display text alone.
- Mapped records are selected and revealed through clustering; unmapped records remain selectable with an explicit unavailable-location result.
- Returning restores filters, result position, selection, and map extent when still valid.
- Scenario changes clear stale entity and return context.
- Pointer, keyboard, focus restoration, narrow layout, and direct tab navigation are covered.

### Non-goals

- URL-addressable deep links, multi-window navigation, dispatch actions, reassignment, or a general-purpose browser-history rewrite.

## Plan 2 — Operational filters and visual encoding

### Included enhancements

- **POC-036 — Operations Map priority filters and symbology**
- **POC-037 — Operations Map crew readiness and capability filters**

### Goal

Bring the map's operational slicing closer to the existing Incident and Crew Board workflows while keeping the map, list, counts, suggestions, legend, and selection synchronized.

### Suggested delivery slices

1. **Shared facet model — Medium**
   - Reuse authoritative incident and crew fields and shared terminology.
   - Define cascading remaining-result counts, zero-result choices, active-value preservation, filter reset, and preset behavior.
2. **Incident facets and encoding — Medium**
   - Add severity, hazard, critical-facility level, ranking status, customer-impact range, assignment state, and age facets.
   - Provide one explicit visual-encoding selector at a time; update the legend and retain distinct incident/crew identity.
3. **Crew facets and presets — Small–Medium**
   - Add status, capability, storm readiness, shift remaining, and assignment-state facets.
   - Add a small set of named presets derived from the same fields rather than separate hidden logic.

### Acceptance themes

- Facets operate over the complete active inventory, not the current page or viewport.
- Counts distinguish filtered records, mapped records, unmapped records, and complete scenario totals.
- Unknown and ranking-withheld values remain visible and accurately described.
- Search suggestions respond to non-text filters consistently with existing faceted-filter behavior.
- Visual encoding is understandable without color alone and remains legible for clusters and overlapping records.

### Non-goals

- New priority scoring, inferred crew readiness, route-based travel calculations, or map-based operational writes.

## Plan 3 — Relationship and summary exploration

### Included enhancements

- **POC-038 — Incident-to-crew relationship layer**
- **POC-044 — Clickable map summaries and drill-up navigation**

### Goal

Let users understand selected assignment relationships in place and move from map subsets to complete operational views without confusing a connector with a route or a displayed subset with an evaluated population.

### Suggested delivery slices

1. **Selection-scoped relationship emphasis — Medium**
   - Highlight assigned records and expose linked-record actions in the selection panel.
   - Handle zero, one, and multiple assignments plus unmapped endpoints.
2. **Optional relationship connectors — Medium**
   - Draw connectors only for the selected entity and label them as assignment relationships.
   - Define behavior for overlapping points, clusters, filtered-out related records, and connector visibility.
3. **Summary navigation — Medium**
   - Make eligible incident, crew, unmapped, and future area totals actionable.
   - Carry a documented filter descriptor into the destination view and display the destination's evaluated population.

### Acceptance themes

- Connectors never claim road routing, travel time, live movement, or electrical connectivity.
- Related records hidden by active filters are disclosed rather than silently absent.
- Summary links state what population will open and do not derive totals from paginated rows or rendered markers.
- Destination views can represent the transferred filter without changing their authoritative ordering rules.

### Non-goals

- Route optimization, travel-path rendering, automatic assignment, recommendation modification, or map-based dispatch.

## Plan 4 — Advanced geospatial context

### Included enhancements

- **POC-039 — Geographic aggregation and regional drill-down**
- **POC-040 — Scenario context layer switcher**

### Goal

Add governed area-level summaries and optional scenario context without presenting synthetic, partial, stale, or reference data as live operational GIS.

### Suggested delivery slices

1. **Source qualification and contracts — Large**
   - Inventory available municipality/region geometry and critical-facility, topology, and weather records.
   - Define stable IDs, coverage, coordinate reference system, timestamps, provenance, completeness, synthetic/reference status, and failure behavior.
   - Decide which sources qualify for the POC before approving rendering work.
2. **Geographic aggregation — Large**
   - Load validated boundaries and define deterministic joins from scenario records.
   - Support one selected metric at a time, such as incident count, customers out, critical-facility incidents, or available crews.
   - Distinguish area aggregates from point clusters and expose evaluated-population details.
3. **Context layer framework — Large; potentially Extra large if several sources are approved together**
   - Add a source-aware layer switcher with loading, unavailable, stale, incomplete, and legend states.
   - Implement approved layers independently so one unavailable source does not invalidate the core map.

### Acceptance themes

- Geometry and scenario records join through governed identifiers rather than unreviewed name matching.
- Area totals use complete deterministic inventories and reconcile with authoritative operational totals.
- Every contextual layer displays source, freshness, completeness, and synthetic/reference status.
- Missing or unqualified inputs disable the layer; no coordinates, boundaries, topology, or weather conditions are guessed.
- Performance is validated against the full-scale scenario and narrow/desktop layouts.

### Non-goals

- Live OMS/GIS/SCADA integration, live GPS, road routing, bulk OpenStreetMap tile use, inferred electrical topology, or production weather operations.

## Approval gates

Each plan should pass the following gates independently:

1. **Scope approval:** confirm included POCs, non-goals, priority, and delivery slices.
2. **Contract approval:** confirm authoritative fields, navigation/state rules, and any required data sources.
3. **Implementation approval:** authorize code changes for only the approved plan or slice.
4. **Validation approval:** review automated results and direct browser evidence before changing a POC status.
5. **Publication and commit approval:** treat documentation, fixture publication, commit, and push as separate decisions.

## Related documents

- [POC Feedback Log](../004_POC_Feedback_Log.md)
- [Operations Map screen specification](../300_UX/310_Screen_Specifications/321_Operations_Map.md)
- [UI Information Architecture](../300_UX/301_UI_Information_Architecture.md)
- [GIS Integration](../700_Integrations/702_GIS_Integration.md)
- [Test Strategy](901_Test_Strategy.md)
