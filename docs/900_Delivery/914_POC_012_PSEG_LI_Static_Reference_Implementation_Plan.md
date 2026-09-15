# POC-012 PSEG Long Island Static Reference Implementation Plan

## Status

Status: Phase 3 ready; Phases 0-2 completed on 2026-09-15.

Date: 2026-09-14

Phase 0 review updated: 2026-09-15

Phase 2 review updated: 2026-09-15

This plan defines a bounded, SME-maintained static reference for the PSEG Long Island/KUBRA
County/Township/Village hierarchy and customers-served counts. It deliberately avoids a live
runtime dependency on the public outage map and keeps static reference values separate from
synthetic scenario outage data.

## Outcome

Create a reviewed, provenance-bearing reference dataset that allows AI Dispatch Advisor to:

- Resolve PSEG Long Island operating areas from County through Township to Village.
- Answer deterministic questions about customers served at each supported geographic level.
- Calculate a synthetic outage percentage only when the synthetic numerator and static-reference
  denominator are both identified, timestamped, and visibly labeled.
- Continue operating when the reference is missing, stale, or invalid without fabricating values.

POC-012 remains a data-reference enhancement. It does not establish a production integration,
authorize unrestricted reuse of KUBRA data, or make the public outage map a system of record for
dispatch decisions.

## Approved Direction

- Use an SME-controlled export as the initial source.
- Use the separate `votaa/process_kubra_report_village_SC5` repository only as an offline snapshot
  producer; do not import it as an AIDA runtime dependency.
- Publish a minimal static artifact containing hierarchy and customers served, plus a companion
  provenance manifest.
- Preserve KUBRA source values and separately store AIDA-normalized values.
- Require sample-first review and never overwrite an approved reference snapshot implicitly.
- Keep transient customers-affected, outage-count, percentage, and ETR fields outside the initial
  static contract.
- Defer scheduled retrieval and live API integration until source authorization, service levels,
  and an approved interface are documented.

## Feasibility Findings

The existing extractor is suitable as a prototype:

- `sc5_latest_url.py` discovers KUBRA's rotating `interval_generation_data` path from the stable
  public `currentState` endpoint.
- `process_report_village_sc5_latest_url.py` flattens the three source levels and exports
  `cust_s` for County, Township, and Village.
- The evaluated KUBRA snapshot contained three top-level areas, 14 town-level areas, 347 leaf
  records, and 1,158,552 customers served. Leaf, town, and top-level totals reconciled.
- Twenty-three of the 24 locations in AIDA's current Long Island registry matched source village
  names directly. AIDA `Hempstead` requires an explicit alias to source `HEMPSTEAD VILLAGE`.
- Source `ROCKAWAY PENINSULA -> ROCKAWAY PENINSULA -> Village` requires an explicit normalized
  mapping to `Queens -> Rockaway Peninsula -> Village`.
- Several village names occur under more than one township. Village name alone is not a stable
  key.

These observations demonstrate technical feasibility but are not a substitute for the snapshot
approval and validation gates below.

## Source and Repository Boundaries

### Extractor repository

The separate `process_kubra_report_village_SC5` repository owns:

- Retrieval of the current anonymous KUBRA report location.
- Source-schema validation.
- Flattening of the source hierarchy.
- Candidate snapshot and manifest generation.
- Extraction tests and operator-facing failure messages.

It must not write directly into the AIDA repository.

### AI Dispatch Advisor repository

This repository owns:

- The approved static reference artifact and its manifest.
- Normalized geography mappings and aliases.
- Reference validation and typed read-only access.
- Deterministic Copilot query behavior and evidence.
- Freshness, unavailable, and mixed-source presentation.

No AIDA request path may call KUBRA during this POC.

## Static Data Contract

### Reference rows

Recommended file:

`data/reference/pseg-long-island/customers-served.csv`

Required columns:

| Field | Meaning |
| --- | --- |
| `reference_id` | Stable composite identifier derived from the complete source path, not village name alone |
| `source_county` | Exact top-level KUBRA value |
| `source_township` | Exact KUBRA town-level value |
| `source_village` | Exact KUBRA leaf value |
| `county` | AIDA-normalized County |
| `township` | AIDA-normalized Township |
| `village` | AIDA-normalized Village |
| `customers_served` | Non-negative integer from source `cust_s` |

The initial artifact contains one row per source leaf path. County and Township totals are derived
from those rows and checked against the corresponding source totals during publication.

### Provenance manifest

Recommended file:

`data/reference/pseg-long-island/manifest.json`

Required fields:

- `dataset_id` and `schema_version`.
- Source organization, product, report URL, instance ID, view ID, and report ID.
- Source `updated_at` and extractor `extracted_at`, both offset-aware UTC datetimes.
- Extractor repository URL and exact Git commit.
- Data filename and SHA-256 checksum.
- County, Township, and leaf record counts.
- Total customers served and source-total reconciliation result.
- Applied normalization-rule version.
- SME review status and review date.
- Optional replacement/supersession reference.

The manifest owns freshness. Filesystem timestamps must not be treated as source timestamps.

## Normalization Rules

1. Preserve every raw source hierarchy field without title-casing or reinterpretation.
2. Use a normalized, versioned mapping layer for AIDA presentation and lookup.
3. Map source `ROCKAWAY PENINSULA` top level to normalized County `Queens` and Township
   `Rockaway Peninsula`; preserve the raw source path beside it.
4. Map source `HEMPSTEAD VILLAGE` to normalized Village `Hempstead` under Nassau/Hempstead.
5. Use a composite `reference_id` containing the full source hierarchy or a deterministic hash of
   that hierarchy.
6. When the same village name occurs in several townships, require additional context or return
   every matching path with an explicit breakdown. Do not select one silently.
7. Reject unknown hierarchy depths, blank path components, duplicate composite IDs, negative or
   non-integer customer counts, and unreconciled aggregates.

Normalization mappings must be reviewed independently from the source extraction so that source
changes cannot silently redefine AIDA geography.

## Phase 0 — Governance and Contract Approval

### Approval record

| Decision | Disposition | Status |
| --- | --- | --- |
| POC use | Use an SME-maintained static reference for hierarchy and customers served. | Confirmed |
| Source method | Generate the candidate through the separately maintained `process_kubra_report_village_SC5` extractor and publish only after SME review. | Confirmed |
| Runtime boundary | AIDA must not call or scrape KUBRA at runtime; live or scheduled retrieval requires a separately approved contract. | Confirmed |
| Initial fields | Include source and normalized County/Township/Village plus `customers_served`; exclude customers affected, outage count, affected percentage, ETR, and outage-location detail. | Confirmed |
| Repository boundary | The extractor produces an isolated candidate; AIDA owns only the approved static artifact, manifest, validation, and read-only use. | Confirmed |
| Storage and audience | Commit the minimal derived CSV and manifest under `data/reference/pseg-long-island/` and share them with the same audience as this repository. | Confirmed |
| Refresh cadence | Refresh before formal demonstrations or releases and at least once every 90 days. | Confirmed |
| Stale threshold | Mark the reference stale when its source timestamp is more than 90 days old. | Confirmed |
| Stale behavior | Continue showing hierarchy and customers-served values with a prominent stale warning, but refuse new mixed-source outage-percentage calculations until a refreshed snapshot is approved. | Confirmed |
| Normalization | Approve the versioned Rockaway, Hempstead, composite-key, and ambiguous-name rules in this plan. | Confirmed |
| Review identity | Record reviewer role and UTC review time in the manifest; a personal name is optional and not required by the application. | Confirmed |

“Confirmed” above records the bounded direction already supplied for POC-012. It does not claim
legal approval for broader publication, production reuse, or a live KUBRA integration.

Approval evidence: the PSEG Long Island SME explicitly confirmed all six previously pending
decisions on 2026-09-15. The approval applies to this bounded POC and repository audience.

### Data-handling classification

- The initial artifact contains aggregate geography and customers-served counts only.
- It contains no credentials, account identifiers, customer records, addresses, crew locations,
  outage locations, current customers affected, or ETRs.
- The artifact is reference data, not an operational source of record.
- The manifest identifies provenance and review status without requiring a reviewer name.
- Any future field expansion requires a new data-handling review before extraction or publication.

### Work

- Confirm the SME is authorized to create and provide the static reference for this POC.
- Confirm whether the derived snapshot may be committed to this repository and shared with its
  intended audience.
- Approve the row schema, manifest schema, normalization rules, refresh cadence, and stale
  threshold.
- Decide whether an expired snapshot remains visible with a warning or becomes unavailable. The
  recommended POC behavior is visible-but-stale for customers-served reference questions and no
  percentage calculation when policy marks the denominator too old.
- Record that the public KUBRA page and anonymous browser resources are not an approved AIDA live
  service contract.

### Exit gate

- Owner/SME approval of the bounded static-reference use, storage location, fields, and freshness
  policy.
- No credentials, private operational fields, or transient outage details are included.

Phase 0 passed on 2026-09-15: every approval-record row is `Confirmed`, and the plan is Phase 1
ready. Extractor hardening may begin; candidate publication remains gated by the Phase 2 SME
review.

## Phase 1 — Harden the Offline Extractor

### Work

- Consolidate endpoint discovery so `currentState` is requested once per run.
- Add explicit connect/read timeouts, bounded retries, and clear nonzero failure exits.
- Move execution behind a `main()` entry point; importing a module must not perform network calls
  or write files.
- Make instance ID, view ID, report ID, and output location explicit configuration with validated
  defaults.
- Validate the response content type, current-state structure, interval path, report version,
  hierarchy depth, required fields, and numeric types.
- Export only the approved static fields and generate the provenance manifest.
- Write candidate artifacts atomically to a new preview directory. Refuse to overwrite an
  existing approved snapshot.
- Pin or document the `requests` and `pandas` dependencies, or remove `pandas` if standard-library
  CSV output is sufficient.

### Tests

- Successful current-state discovery and report URL construction.
- Timeout, HTTP error, malformed JSON, missing interval path, and unexpected path format.
- Valid three-level flattening and deterministic output ordering.
- Missing, negative, non-integer, and malformed `cust_s` values.
- Duplicate village names retained under distinct composite IDs.
- Rockaway and Hempstead normalization cases.
- Atomic output and no-overwrite behavior.

### Exit gate

- Extractor tests pass in its own repository.
- A dry run prints source identity, timestamps, record counts, totals, and sample rows without
  publishing an artifact.

Phase 1 passed on 2026-09-15 at extractor commit
`f7582aeac0cb204dd1eed0d069fc0b4adc4be63c`: all 11 extractor tests passed, and the clean-worktree
dry run validated 3 counties, 14 townships, 347 leaf records, and 1,158,552 customers served.

## Phase 2 — Generate and Approve the Reference Snapshot

### Work

- Generate a candidate CSV and manifest into an isolated preview directory.
- Compare leaf totals with Township and top-level source totals.
- Review all normalization exceptions, duplicate names, blank fields, zero values, and large
  changes from any previous snapshot.
- Compare every location in `LongIslandGeography.csv` with the candidate reference and resolve
  aliases explicitly.
- Have the SME review the source timestamp, expected totals, hierarchy, mappings, and intended
  refresh cadence.
- Copy the approved pair into AIDA only after review; preserve any prior approved snapshot until
  replacement is accepted.

### Required review evidence

- Extractor commit and invocation.
- Candidate artifact checksums.
- Validation report with counts and reconciliation results.
- Normalization exception report.
- SME approval date and disposition.

### Exit gate

- One approved, checksum-matched CSV/manifest pair exists in AIDA.
- Repository diff contains only the intended reference artifacts and documentation for this
  phase.

Phase 2 passed on 2026-09-15. The PSEG Long Island SME approved the candidate generated from
source timestamp `2026-09-15T23:41:56Z`; the manifest records the reviewer role and UTC approval
time. Validation confirmed 347 unique composite IDs, no blank or zero-value rows, expected
Rockaway and Hempstead normalization, all 24 `LongIslandGeography.csv` paths matched, and the
approved CSV SHA-256 is
`0147f268b7fa63b841a40a13233be5c6bbb593ab233480367ebb2e63a1dd661f`. This first approved
snapshot establishes the baseline for future change comparisons.

## Phase 3 — Add the AIDA Static Reference Boundary

### Work

- Add typed models for reference rows, manifest metadata, and validation results.
- Add a read-only reference service independent of `ScenarioService` and scenario CSV contracts.
- Load and validate the CSV/manifest pair, including checksum, schema version, counts, source
  timestamp, normalization version, unique composite IDs, and aggregate reconciliation.
- Support deterministic lookup by complete path, County, Township, Village, and configured alias.
- Return explicit ambiguous, stale, unavailable, and invalid states.
- Keep startup and existing scenario workflows usable if the optional reference is unavailable.
- Expose the reference only through a bounded API or internal service contract required by the
  Copilot slice; do not add a generic external-data proxy.

### Tests

- Valid load and lookup at all three hierarchy levels.
- Ambiguous village names return all matches or require disambiguation.
- Rockaway and Hempstead normalized/source paths remain distinguishable.
- Checksum, schema, aggregate, duplicate-ID, and timestamp failures are rejected visibly.
- Missing or stale reference data does not break scenario loading, recommendations, or other
  Copilot questions.
- Switching synthetic scenarios never changes the static denominator or its provenance.

### Exit gate

- The approved snapshot is accessible through a typed, read-only boundary.
- No application path contacts KUBRA, mutates the artifact, or treats it as scenario-owned data.

## Phase 4 — Deterministic Copilot Reference Queries

### Initial question families

- “How many customers are served in Nassau County?”
- “How many customers are served in the Town of Hempstead?”
- “How many customers are served in Arverne?”
- “Show the PSEG Long Island hierarchy for Rockaway Peninsula.”
- “Which townships or villages match this name?”
- “What percentage of customers are out in this area?”

### Work

- Add a dedicated deterministic intent for customers-served and source-hierarchy questions.
- Resolve explicit area names and selected-incident geography through the normalized reference
  service without calling the model provider.
- Return the exact source path, normalized path, customers served, source timestamp, extraction
  timestamp, freshness state, and bounded evidence.
- For ambiguous village-only questions, show matching Township paths and request or infer no
  selection beyond available context.
- Calculate percentages only in application code and only when:
  - The numerator is a complete synthetic scenario aggregate for the same normalized area.
  - The denominator is the approved static customers-served value.
  - Both values, timestamps, provenance, and synthetic/reference distinction are displayed.
  - The denominator is nonzero and allowed by the approved freshness policy.
- Refuse or qualify calculations when geographic coverage is partial, the reference is stale or
  unavailable, or the numerator and denominator scopes do not align.
- Keep grounded AI limited to explaining already retrieved evidence; it must not supply customer
  counts from model memory.

### Tests

- County, Township, Village, alias, selected-incident, and ambiguous-name queries.
- Exact expected values from the approved fixture and zero model-provider calls.
- Mixed-source percentage calculations with aligned and misaligned geography.
- Zero denominator, missing numerator, stale reference, missing reference, and invalid reference.
- Evidence contains only the active scenario numerator records and approved reference records.
- Existing all-incident synthetic customer-outage queries remain unchanged.
- Copilot remains advisory-only and cannot mutate reference or dispatch state.

### Exit gate

- Deterministic queries and failure states pass backend/API/frontend regression coverage.
- Response language makes the static-versus-synthetic boundary understandable without opening
  evidence details.

## Phase 5 — Smoke Test, Refresh Procedure, and Closeout

### Manual smoke test

1. Ask for customers served at one County, Township, and Village level and compare each answer
   with the approved snapshot.
2. Ask for `Hempstead` and confirm the explicit `HEMPSTEAD VILLAGE` source alias.
3. Ask for Rockaway hierarchy and confirm source and normalized paths are both visible.
4. Ask about a duplicated village name and confirm Copilot does not silently choose a township.
5. Ask for an aligned synthetic outage percentage and confirm numerator, denominator, timestamps,
   and mixed-source label.
6. Exercise missing, stale, invalid-checksum, and zero-denominator fixtures.
7. Confirm no browser or backend request is sent to KUBRA during AIDA use.
8. Confirm recommendations, scoring, assignments, and decision history are unchanged.

### Refresh procedure

1. Run the extractor in dry-run mode from its own repository.
2. Generate a new candidate in an isolated timestamped preview directory.
3. Compare counts, totals, hierarchy paths, aliases, and normalization exceptions with the current
   approved snapshot.
4. Review unexpected additions, removals, renamed areas, and material customer-count changes.
5. Obtain SME approval and record the review in the new manifest.
6. Replace the approved CSV and manifest together in one reviewed change.
7. Run reference validation, focused Copilot tests, the full relevant suites, and the manual smoke
   test before commit.

### Closeout evidence

- Extractor and AIDA automated test results.
- Approved snapshot and matching manifest checksum.
- SME approval and refresh-policy decision.
- Manual smoke-test result.
- Confirmation that runtime network traffic to KUBRA is absent.
- Feedback-log disposition for POC-012.

## Acceptance Criteria

- The approved static artifact represents every accepted source leaf with a stable composite ID.
- Source and normalized hierarchies are both retained and versioned mappings cover all exceptions.
- Customers-served values are non-negative integers and aggregate exactly to reviewed source
  Township and top-level totals.
- The manifest identifies source time, extraction time, extractor commit, checksum, counts,
  normalization version, and SME review status.
- AIDA loads the reference through a typed read-only boundary independent of scenario data.
- Missing, stale, ambiguous, or invalid data produces an explicit limitation and never a
  fabricated value.
- Supported customers-served questions use deterministic local queries and bypass the model.
- Any mixed-source percentage labels the synthetic numerator and static denominator with their
  scopes, sources, and timestamps.
- No POC-012 path changes scoring, recommendations, assignments, decisions, or other operational
  state.
- No AIDA runtime path calls or scrapes the KUBRA outage map.
- Automated tests, owner/SME review, and the manual smoke test pass before POC-012 is closed.

## Non-Goals

- Live KUBRA polling, browser scraping, scheduled refresh, or automatic publication.
- Treating an anonymous browser resource as a supported production API.
- Importing current customers affected, outage counts, percentages, ETRs, or outage locations in
  the initial static reference.
- Replacing scenario `customers_out` or combining live and synthetic outage facts silently.
- Inferring geography or customer counts from model memory.
- Production data licensing, enterprise integration readiness, or source-system certification.
- Modifying POC-019 scoring or any dispatch recommendation behavior.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Undocumented KUBRA browser contract changes | Offline extraction, schema validation, manual review, and last-good approved snapshot |
| Unclear reuse authority | Phase 0 owner/SME approval and no live runtime dependency |
| Duplicate or renamed localities | Full-path composite IDs, alias mapping, ambiguity responses, and snapshot diff review |
| Rockaway hierarchy mismatch | Preserve source values and apply an explicit versioned normalization rule |
| Stale customer denominator | Manifest-owned freshness, visible warning, and approved calculation cutoff |
| Synthetic/reference scope mismatch | Deterministic geographic alignment and refusal when coverage is incomplete |
| Silent file replacement | Isolated preview, checksum pair, no-overwrite generation, and reviewed publication |
| Scope expansion into outage integration | Exclude transient outage fields and gate any future live adapter separately |

## Recommended Commit Sequence

Keep extractor and AIDA changes in separate repositories and reviewable commits:

1. `refactor: harden KUBRA village report snapshot export`
2. `data(reference): add reviewed PSEG LI customers-served snapshot`
3. `feat(reference): load PSEG LI static geography reference`
4. `feat(copilot): answer PSEG LI customers-served queries`
5. `docs(poc-012): record validation and closeout evidence`

## Related Documents

- [POC Feedback Log](../004_POC_Feedback_Log.md)
- [AI Copilot User Guide](../300_UX/306_AI_Copilot_User_Guide.md)
- [AI Copilot Screen Specification](../300_UX/310_Screen_Specifications/317_AI_Copilot.md)
- [Recommendation API](../400_Backend_API/405_Recommendation_API.md)
- [AI Recommendation Engine](../600_Data_AI/603_AI_Recommendation_Engine.md)
- [Model Governance](../600_Data_AI/605_Model_Governance.md)
- [Phase 7 Implementation Plan](907_Phase_7_Implementation_Plan.md)
- [POC-002 AI Copilot Implementation Plan](908_POC_002_AI_Copilot_Implementation_Plan.md)
- [Test Strategy](901_Test_Strategy.md)
- [KUBRA extractor repository](https://github.com/votaa/process_kubra_report_village_SC5)
- [PSEG Long Island outage-area report](https://outagemap.psegliny.com/reports/be6c533e-409e-4f3a-8d62-799b65331056)
- [PSEG Long Island website terms and conditions](https://www.psegliny.com/websitetermsandconditions)
