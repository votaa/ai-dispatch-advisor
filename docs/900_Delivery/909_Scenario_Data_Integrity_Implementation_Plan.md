# Scenario Data Integrity and Critical-Facility Linkage Implementation Plan

## Status

Status: Implemented; isolated sample approved; corrected scenario published as a new version.

Date: 2026-08-24

Implementation review note: generator, runtime, timeline, Copilot, tests, and the formal
data-contract documentation have been updated. The owner approved the isolated POC-026
standard scenario and five-snapshot timeline on 2026-09-13. The validated full-scale
`august-storm-preview-v2` was published on 2026-09-14 without changing or replacing the
original `august-storm-preview` scenario.

This plan addresses scenario components that can become internally inconsistent, beginning
with incidents marked `critical_facility=true` that do not have a matching row in
`CriticalFacilities.csv`. It covers the shared scenario generator, the multi-snapshot
timeline generator, runtime scenario validation, deterministic Copilot answers, and
sample-first fixture regeneration.

## Problem Statement

The current generator synthesizes incident critical-facility flags and facility records
independently. An incident can therefore claim critical-facility impact while no facility
record exists for the same region and feeder. The Copilot then filters facility records
and can omit the incident-level impact from its answer.

The same pattern can recur in timeline snapshots because new arrivals currently use the
general incident generator while the facility catalog remains stable.

## Audit Evidence

The read-only cross-scenario audit found:

| Finding | Evidence | Risk |
| --- | --- | --- |
| Copilot demo orphan | `long-island-copilot-demo` has 2 critical-facility incidents; East Meadow has no matching facility row | High for demo Copilot answers and evidence |
| Timeline/large-scenario orphaning | `august-storm-preview` has 97 critical-facility incidents; 46 have no matching facility row | High for large-scenario Copilot and facility reporting |
| Generator reproduces the issue | A fresh seeded generated sample produced 9 critical incidents and 7 unmatched incidents | High; regeneration can recreate the defect |
| Legacy topology gaps | Older `base`, `storm`, `crew-shortage`, and `critical-facility` fixtures contain incident feeder references absent from `Topology.csv` | Medium; topology is not currently central to scoring but is a broken cross-file contract if consumed |
| Legacy status variation | Older fixtures contain `monitoring` incident status and `staged` crew status | Medium/low; either formalize or normalize before stricter enum validation |
| Existing identity/assignment checks | No duplicate primary IDs or orphan assignment incident/crew references found | No confirmed defect |
| Intentional dual assignments | Repair/TREE incidents have two active crews by design | Not a defect; preserve the documented exception |

All current manifests, required CSV files, CSV headers, primary identifiers, and assignment
foreign keys passed the existing scenario-service validation. That validation does not yet
check critical-facility linkage or incident-to-topology coverage.

## Goals

1. Ensure every generated `critical_facility=true` incident resolves to one or more
   critical-facility records by region and feeder.
2. Ensure every timeline snapshot preserves valid facility linkage, including new arrivals.
3. Prevent scenario activation or publication when stable cross-file integrity rules fail.
4. Make Copilot answers distinguish incident-level critical-facility impact from matched
   facility-record detail.
5. Preserve deterministic recommendation scoring, API envelopes, advisory-only behavior,
   dry-run-first generation, and protected scenario folders.
6. Establish an owner-reviewed critical-facility domain catalog that can be expanded safely.

## Non-Goals

- Adding live GIS, OMS, outage-map, or utility facility data.
- Claiming that synthetic facility names represent real operational assets.
- Introducing DPS Level 1–3 labels without an approved taxonomy and mapping.
- Changing the incident-priority weights or recommendation algorithm.
- Changing timeline recovery, arrival, assignment, crew-rotation, weather, or ETR formulas
  except where required to preserve facility linkage.
- Overwriting `data/scenarios/base` or existing published scenario folders.
- Adding a database migration or changing the public `/api/chat` response envelope.

## Domain and Data Contract

### Current facility catalog

The generator currently draws from these profiles:

| Name suffix | `facility_type` | Current `priority_level` |
| --- | --- | --- |
| Regional Medical Center | `hospital` | `critical` |
| Water Treatment Facility | `water` | `critical` |
| Emergency Services Center | `emergency_services` | `critical` |
| Senior Care Center | `healthcare` | `high` |
| Public Safety Communications Center | `communications` | `critical` |
| Fire District Headquarters | `emergency_services` | `high` |
| Police Precinct | `emergency_services` | `high` |
| Emergency Shelter | `shelter` | `high` |
| Wastewater Pump Station | `water` | `high` |
| Transit Operations Center | `transportation` | `high` |

### Owner-review catalog candidates

The approved POC catalog is:

### Level 1 — Critical to public health and safety

- Hospitals or medical centers.
- Emergency shelters.
- Fire stations and police stations.
- Water treatment plants and water pumping stations.
- Wastewater or sewage treatment plants and pumping stations.
- Mass transit systems.
- 911 or public-safety communications centers.

### Level 2 — Significant public services

- Nursing homes.
- Dialysis centers.
- Prisons or correctional facilities.
- Radio and television communications facilities.

### Level 3 — General public services

- Senior Care Center.
- Health Related Facility.
- Private Health Device (LSE).
- Other approved facilities that provide necessary public functions.

For the POC, map DPS levels to the existing facility priority field as follows:

| DPS level | `priority_level` | `critical_facility` flag |
| --- | --- | --- |
| Level 1 | `critical` | `true` |
| Level 2 | `high` | `true` |
| Level 3 | `medium` | `true` |

The POC uses the supplied DPS Level 1–3 definitions as its working taxonomy. Source
provenance and final terminology should be reviewed before production use.

### Linkage rules

The implementation uses a seeded facility-to-incident-locality index for newly generated
data:

```text
facility record
  region + feeder + municipality
        ↓
incident critical_facility=true
```

Required rules:

- Facility region, municipality, and feeder must be valid for the generated scenario.
- A generated critical-impact incident may only use a region, feeder, and municipality with
  an eligible facility row.
- An incident without an eligible facility remains `critical_facility=false`.
- Every generated `critical_facility=true` incident must match at least one facility row by
  region, feeder, and municipality. Runtime activation retains region-and-feeder validation
  for backward compatibility with published legacy fixtures.
- Facility IDs must remain unique within a scenario.
- Set `critical_facility=true` for incidents linked to eligible Level 1, Level 2, or Level 3 facilities.
- Preserve the active POC-019 Level 1/2/3 critical-facility contributions of
  `+120/+80/+40`; generated LSE boundary data validates the Level 3 path without changing
  the scoring policy.
- Multiple facility rows on one feeder may be supported, but Copilot responses must report
  all matched records without treating the number of facilities as the number of incidents.

## Implementation Scope

### 1. Shared scenario generator

Update `backend/app/scenario_generator.py` to:

- Represent the facility catalog as a named, typed, seeded domain list.
- Generate facility rows before assigning incident criticality, or otherwise build an
  explicit eligible feeder index before incident flags are finalized.
- Remove independent random assignment of `critical_facility=true` from `_base_incident`
  when the generator is operating under the linked scenario contract.
- Preserve explicit Copilot demo overrides, but validate that each override resolves to a
  facility row.
- Generate approved facility names from municipality plus catalog suffix without implying
  real-world facility identity.
- Keep facility rows and classifications stable for the scenario seed.
- Extend `validate_generated_scenario()` with critical-facility linkage checks.
- Add a clear validation error containing incident ID, region, feeder, and available
  matching facility context.

The existing generator’s assignment, topology, and geography rules should remain intact.

### 2. Runtime scenario validation

Update `backend/app/scenario_service.py` to validate checked-in, uploaded, or copied
scenario folders, not only freshly generated in-memory scenarios:

- Validate `critical_facility` as a boolean value.
- Validate incident-to-facility linkage by region and feeder.
- Validate facility region/feeder references against topology where topology is required by
  the scenario contract.
- Decide whether topology coverage is required for all legacy scenarios or only generated
  scenarios; document the compatibility treatment before enforcing it.
- Preserve structured validation errors and scenario activation safety.

The runtime validator must not reject intentionally fictional geography solely because the
legacy scenarios are documented as not having full Long Island geography guarantees.

### 3. Multi-snapshot timeline generator

Update `backend/app/scenario_timeline_generator.py` to:

- Generate and validate a linked snapshot-1 facility catalog.
- Build a stable facility-to-feeder index from the base scenario.
- Derive `critical_facility` for new arrivals from that index instead of calling the
  independent random incident flag.
- Keep `CriticalFacilities.csv` stable across all snapshots.
- Validate every snapshot, including new arrivals, against the linkage contract.
- Preserve stable facility IDs, classifications, region/feeder associations, and rows.

No changes are expected to the time progression of incident age, ETR, assignment phase,
crew rotation, recovery, arrival counts, or weather intensity.

### 4. Deterministic Copilot local answer

Update `backend/app/services/copilot_service.py` so the critical-facility local-query path:

- Counts incidents where `critical_facility=true` from incident records.
- Lists the affected incident IDs/municipalities.
- Separately lists matched facility records.
- Explicitly identifies critical incidents that have no matching facility record, if runtime
  validation allows degraded data to be queried.
- Includes incident evidence for the count and facility evidence for matched facility rows.
- Preserves the existing `critical_facilities` intent, `local_query` mode, API envelope,
  advisory safety note, and provider bypass.

The response must not equate the number of facility records with the number of affected
incidents.

### 5. Scenario fixtures and previews

After code and validation pass in isolation:

- Regenerate the Copilot demo into an isolated preview output.
- Add the approved East Meadow facility record only if its facility details are explicitly
  approved; do not invent operational facility facts.
- Regenerate or repair `august-storm-preview` only through the validated generator.
- Compare row counts, IDs, critical flags, facility mappings, assignments, and manifests
  before publication.
- Do not overwrite `base` or existing live/demo scenario folders during preview.
- Publish scenario data only after owner review of sample records and validation output.

## Test Plan

### Unit and contract tests

- Facility catalog contains only approved types and priorities.
- Seeded generation is deterministic.
- Facility IDs and composite region/feeder references are unique and valid.
- Every critical incident has a matching facility row.
- Incidents on unlinked feeders are not marked critical.
- Copilot demo explicitly covers Arverne and the approved East Meadow case.
- Runtime scenario validation rejects an orphan critical-facility incident.
- Runtime validation reports useful structured error details.
- Existing assignment foreign-key and crew-status checks remain passing.
- Intentional dual repair/TREE assignments remain valid.

### Timeline tests

- Facility rows are identical across snapshots.
- Facility IDs and region/feeder mappings remain stable.
- New incidents never introduce an orphan critical flag.
- Critical status is preserved for surviving incidents.
- Facility linkage validation runs for every snapshot.
- Existing queue-conservation, lifecycle, deterministic-seed, recovery, arrival, crew,
  timezone, and daylight-saving tests remain passing.

### Copilot tests

- “How many incidents have critical facilities on them?” returns the incident count.
- The Copilot demo returns both Arverne and East Meadow when both are approved and linked.
- Matched facility names are returned separately from incident count.
- Missing facility detail is reported as a data limitation, not silently omitted.
- Deterministic local queries do not call the provider.
- Existing facility, hazard, geography, fallback, evidence, and advisory-only behavior is
  unchanged.

### Smoke and review checks

- Run generator dry-run and preview validation before any publication.
- Inspect first and final timeline snapshots.
- Switch between at least two scenarios and verify critical counts and evidence.
- Ask the Copilot count question in the canonical demo and confirm local-query mode.
- Confirm no provider credentials or live operational data are introduced.

## Delivery Sequence

1. Owner approves the facility domain catalog and the `priority_level` rule.
2. Implement generator linkage and generator validation.
3. Implement runtime scenario validation.
4. Implement timeline arrival linkage and per-snapshot validation.
5. Implement the Copilot count/evidence response correction.
6. Run focused tests, full backend tests, and timeline tests.
7. Generate isolated previews and perform sample-first owner review.
8. Regenerate approved fixtures only after preview approval.
9. Run frontend/API smoke checks and review the final diff.
10. Commit only after explicit approval.

## Acceptance Criteria

- No generated or published scenario contains an orphan `critical_facility=true` incident.
- Level 1, Level 2, and Level 3 facility records map to `critical`, `high`, and `medium` respectively, and all linked levels set `critical_facility=true`.
- The canonical demo reports the correct number of critical-facility incidents.
- Facility records and incident flags reconcile across every timeline snapshot.
- Runtime validation rejects or clearly reports broken cross-file linkage.
- Critical-facility domain types and priority mappings are documented and owner-approved.
- Existing recommendation rankings, assignment behavior, timeline lifecycle semantics,
  API contracts, fallback behavior, and advisory-only boundaries remain compatible.
- Existing base data is not overwritten during generation or preview.
- Backend, generator, timeline, and frontend regression checks pass.

## Risks and Decisions Needed

| Decision/risk | Treatment |
| --- | --- |
| East Meadow facility identity is not specified | Obtain approved name/type/priority before adding a row; do not fabricate details |
| DPS Level 1–3 source provenance | Preserve the supplied working taxonomy for the POC and review source attribution and final terminology before production use |
| DPS level-specific scoring | Preserve the current flat score; consider differentiated weights as future POC work |
| Legacy fictional geography | Preserve documented compatibility; do not add unrelated geography requirements to this patch |
| Existing legacy topology gaps | Decide whether to validate now, normalize fixtures first, or track separately |
| Timeline arrival criticality | Use stable facility-to-feeder linkage, not independent random flags |
| Fixture regeneration risk | Use isolated preview, dry-run, validation, diff, and owner approval before publication |

## Files Expected to Change During Implementation

- `backend/app/scenario_generator.py`
- `backend/app/scenario_service.py`
- `backend/app/scenario_timeline_generator.py`
- `backend/app/services/copilot_service.py`
- `backend/tests/test_scenario_generator.py`
- `backend/tests/test_scenario_service.py`
- `backend/tests/test_scenario_timeline_generator.py`
- `backend/tests/test_copilot_local_queries.py`
- `docs/600_Data_AI/601_Data_Model.md` or related data-contract documentation, if the
  linkage rule becomes a formal contract
- `docs/900_Delivery/AI_Dispatch_Advisor_Timeline_Generator_Plan.md`
- Approved isolated scenario preview/output files, followed by published fixtures only after
  review

## Related Documents

- [POC Feedback Log](../004_POC_Feedback_Log.md), including POC-018.
- [Scenario Manifest](../600_Data_AI/606_Scenario_Manifest.md).
- [Data Model](../600_Data_AI/601_Data_Model.md).
- [Optimization Engine](../600_Data_AI/602_Optimization_Engine.md).
- [Timeline Generator Plan](AI_Dispatch_Advisor_Timeline_Generator_Plan.md).
- [POC-002 AI Copilot Plan](908_POC_002_AI_Copilot_Implementation_Plan.md).
- [Runbook](904_Runbook.md).
