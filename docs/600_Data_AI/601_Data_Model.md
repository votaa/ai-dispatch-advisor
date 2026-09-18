# Data Model

## Purpose

This document defines the data model direction for the AI Dispatch Advisor. It describes the current proof-of-concept data assets, target domain entities, ownership boundaries, source metadata, and persistence evolution.

## Current Implementation State

The Developer Bootstrap MVP dynamically discovers manifested synthetic scenarios. Four scenarios are maintained as canonical deterministic regression fixtures:

```text
data/scenarios/
  base/
  storm/
  crew-shortage/
  critical-facility/
```

Each directory contains a `scenario.json` manifest and the seven CSV domain files listed below. The scenarios cover routine blue-sky operations, high-volume storm response, constrained crew capacity, and critical-facility prioritization.

The repository also includes an initial SQLite schema:

```text
database/schema.sql
database/seed.sql
scripts/init_db.py
```

The backend reads incident, crew, assignment, weather, facility, topology, and repair reference data from the active scenario CSV files. SQLite is active only for local recommendation decisions and accepted demo assignments; it is not yet the primary store for the broader domain model.

Each scenario directory includes a `scenario.json` metadata and file-inventory contract as defined in [Scenario Manifest](606_Scenario_Manifest.md). The backend scenario service validates metadata, required files, CSV headers, identifiers, and assignment references before process-local activation. Recommendation decisions and accepted demo assignments are filtered by `scenario_id` so state remains isolated while switching.

Historical full-scale scenarios retained only for backend regression live under
`data/regression-scenarios/`. They keep the same manifest and CSV contract but are outside
the runtime discovery root, so they do not appear in the application scenario selector.

## Phase 4 Persistence Boundary

Decision `D-007` defines the current ownership boundary:

| Data class | Current authority | Mutability |
| --- | --- | --- |
| Scenario manifests and CSV records | Version-controlled scenario folders | Immutable at runtime |
| Incident and crew operational views | Scenario inputs plus computed assignment/decision overlays | Derived, not directly persisted |
| Baseline assignments | Scenario CSV input | Immutable at runtime |
| Accepted assignments | AI Dispatch Advisor SQLite store | Mutable and scenario-scoped |
| Recommendation decisions and audit history | AI Dispatch Advisor SQLite store | Append-only in normal application workflows and scenario-scoped |

The backend must not write runtime changes into scenario folders. CSV identifiers are normalized as strings even when their values contain only digits, preserving stable identifiers across generated and hand-authored scenarios. Future enterprise adapters or normalized persistence may replace scenario-backed incident and crew inputs, but they should map into the same domain contracts. The initial explicit contracts are implemented in `backend/app/domain/models.py`.

## Decision-Store Schema Evolution

Application-owned SQLite tables are managed by consecutively numbered SQL migrations under `backend/app/migrations/`. The backend applies pending migrations at startup and records their version, name, SHA-256 checksum, and application time in `schema_migrations`.

The initial migration history is:

| Version | Purpose |
| --- | --- |
| `001` | Create recommendation audit-event and accepted-assignment tables |
| `002` | Add `scenario_id` scoping with `base` as the legacy-row default |
| `003` | Add scenario-aware audit and active-assignment indexes |

Existing unversioned POC databases matching either the original unscoped schema or the current scenario-scoped schema are baselined and upgraded without removing rows. Unsupported partial or inconsistent schemas cause startup failure so recovery can be handled explicitly.

## Data Model Goals

The data model should:

- Represent outage dispatch workflows clearly.
- Support explainable recommendations.
- Preserve source-system provenance.
- Track data freshness and quality.
- Support auditability for recommendation and user action history.
- Remain adaptable to utility-specific OMS, GIS, SCADA, crew, weather, and AMI integrations.
- Avoid treating the AI Dispatch Advisor as the system of record for domains owned by other platforms.

## Current POC Data Domains

| Domain | Current Source | Purpose |
| --- | --- | --- |
| Incidents | `PendingIncidents.csv` | Active outage and trouble events |
| Crews | `Crews.csv` | Crew availability, status, capability, and demo travel estimate |
| Assignments | `Assignments.csv` | Active synthetic crew assignments |
| Historical Repairs | `HistoricalRepairs.csv` | Reference repair duration and work type context |
| Weather | `Weather.csv` | Regional weather and hazard context |
| Critical Facilities | `CriticalFacilities.csv` | Priority facilities affected by outages |
| Topology | `Topology.csv` | Simplified feeder and asset connectivity |

### Scenario integrity contract

Scenario incident impact and facility detail are separate records joined by the composite
key `region + feeder`. `critical_facility=true` is valid only when at least one row in
`CriticalFacilities.csv` has the same region and feeder. The runtime scenario service
validates the flag as a boolean and rejects orphan critical-impact incidents before
activation. Copilot counts come from incident records; matching facility rows provide
separate descriptive evidence and are not used as a substitute incident count.

The approved POC synthetic facility catalog uses the following classification mapping:

| Working DPS level | `priority_level` | Incident may set `critical_facility=true` |
| --- | --- | --- |
| Level 1 | `critical` | Yes |
| Level 2 | `high` | Yes |
| Level 3 | `medium` | Yes |

Generated facility names combine a municipality with an approved generic catalog suffix;
they do not assert a real operational facility identity. Facility rows are seeded and
stable within a generated scenario or timeline. Timeline arrivals derive critical impact
from the snapshot-1 facility index, and every snapshot is validated against that index.

POC-026 adds a stricter contract for newly generated data: a critical-impact incident must
match a facility by `region + feeder + municipality`, and each facility's municipality,
feeder, and synthetic name are derived from an incident anchor. Every generated scenario
also reserves three unassigned, low-severity incidents with 1, 19, and 20 customers on the
same linked healthcare/medium Level 3 `Private Health Device (LSE)` facility. These rows
provide deterministic customer-impact boundary coverage in both single-snapshot and
default timeline output. Generation fails when the configured assignment rate does not
leave three unassigned incident slots. The full-scale `august-storm-preview-v2` captured
this contract alongside the unchanged original August scenario. Both historical versions
are retained under `data/regression-scenarios/` for regression testing without appearing
in the runtime selector. Runtime activation retains the backward-compatible
`region + feeder` validation rule described above for legacy fixtures.

POC-032 expands the governed geographic reference to 49 records: all 48
municipalities available to the scenario generator plus Melville. Each record carries a
stable reference ID and preserves both the source and normalized County/Township/Village
paths. Generation and publication fail when an incident municipality is missing from the
reference or resolves to a different operating region. The full-scale
`august-storm-preview-v3` publishes the same seeded scenario CSV content as v2 with this
complete geography contract and updated provenance; v2 remains unchanged in the regression
archive for reproducibility. The SME-approved Floral Park/Hempstead, Commack/Huntington,
Calverton/Riverhead, and Westhampton Beach/Southampton choices are intentional
synthetic-data simplifications. POC-033 tracks stable composite identity for villages that
span townships or counties before real OMS integration.

Topology coverage remains a strict generated-scenario contract. It is not yet a runtime
activation requirement for all legacy fixtures because their fictional topology coverage
is documented as incomplete. Tightening that compatibility rule requires a separate fixture
normalization and owner-review step.

## Core Target Entities

### Incident

Represents an outage, trouble call, hazard, or operational event requiring review.

Target fields:

- `incident_id`.
- `source_system`.
- `source_record_id`.
- `status`.
- `severity`.
- `region`.
- `municipality`.
- `geography_reference_id` (optional for legacy scenarios; required for population-constrained generated scenarios).
- `feeder_id`.
- `customers_out`.
- `critical_facility_impact`.
- `hazard_type`.
- `required_skill`.
- `reported_at`.
- `updated_at`.
- `etr`.
- `location`.
- `data_quality_status`.

### Crew

Represents a field crew or dispatchable resource.

Target fields:

- `crew_id`.
- `source_system`.
- `crew_name`.
- `home_region`.
- `status`.
- `capabilities`.
- `current_location`.
- `shift_start`.
- `shift_end`.
- `equipment`.
- `certifications`.
- `last_location_update`.
- `data_quality_status`.

### Assignment

Represents an assignment of a crew to an incident, work package, patrol, or restoration task.

Target fields:

- `assignment_id`.
- `incident_id`.
- `crew_id`.
- `status`.
- `assigned_at`.
- `assigned_by`.
- `source_system`.
- `writeback_status`.
- `notes`.

### Recommendation

Represents a system-generated dispatch recommendation.

Target fields:

- `recommendation_id`.
- `incident_id`.
- `recommended_action`.
- `recommended_crew_id`.
- `confidence`.
- `expected_impact`.
- `generated_at`.
- `expires_at`.
- `algorithm_version`.
- `model_version`.
- `source_data_snapshot_id`.
- `status`.

### Recommendation Explanation

Represents structured explanation for a recommendation.

Target fields:

- `recommendation_id`.
- `factors`.
- `constraints`.
- `assumptions`.
- `alternatives`.
- `data_quality_warnings`.
- `confidence_rationale`.

### Recommendation Action

Represents a human review action.

Target fields:

- `event_id`.
- `recommendation_id`.
- `incident_id`.
- `crew_id`.
- `action`.
- `reason`.
- `note`.
- `user_id`.
- `created_at`.

Actions:

- Accepted.
- Modified.
- Deferred.
- Overridden.

### Audit Event

Represents traceable system and user activity.

Target fields:

- `event_id`.
- `event_type`.
- `actor_type`.
- `actor_id`.
- `entity_type`.
- `entity_id`.
- `timestamp`.
- `payload`.
- `correlation_id`.

## Source Metadata

Operational data should carry source metadata:

| Field | Purpose |
| --- | --- |
| `source_system` | Identifies OMS, GIS, SCADA, crew, weather, AMI, or internal source |
| `source_record_id` | Original source-system identifier |
| `source_updated_at` | Last update time from source system |
| `loaded_at` | Time ingested or loaded into AI Dispatch Advisor |
| `freshness_status` | Current, stale, missing, conflicting, or unknown |
| `quality_warnings` | Field-level or record-level data quality concerns |

## Data Ownership

| Data Domain | System of Record | AI Dispatch Advisor Role |
| --- | --- | --- |
| Outage state | OMS | Read, normalize, recommend, optionally write approved action |
| Asset topology | GIS | Read and contextualize |
| Device telemetry | SCADA or DMS | Read and constrain recommendations |
| Crew status | Crew or workforce system | Read and recommend assignments |
| Weather | Weather provider | Read and contextualize |
| Recommendation history | AI Dispatch Advisor | Generate and persist |
| User recommendation actions | AI Dispatch Advisor | Capture and audit |

## Current-to-Target Migration

| Current POC | Target Direction |
| --- | --- |
| CSV files | Scenario data plus adapter-fed normalized database |
| Optional local SQLite | Active persistence layer with migrations |
| Manual frontend/backend types | Shared or generated API schemas |
| No recommendation persistence | Recommendation and action history tables |
| Minimal source metadata | Source provenance and freshness tracking |

## Data Quality Requirements

The data model should support validation for:

- Missing required identifiers.
- Stale records.
- Conflicting assignment status.
- Missing crew capability.
- Missing incident location.
- Inconsistent feeder or topology references.
- Missing critical facility linkage.
- Cross-municipality critical-facility linkage in newly generated scenarios.
- Missing generated Level 3 LSE linkage or 1-, 19-, and 20-customer boundary cases.

Data quality should affect recommendation confidence.

## Synthetic Data Policy

POC and demo data must remain fictional. It should not include:

- Real customer data.
- Real crew personal information.
- Sensitive grid infrastructure details.
- Real operational security data.

## Related Documents

- [Optimization Engine](602_Optimization_Engine.md)
- [AI Recommendation Engine](603_AI_Recommendation_Engine.md)
- [Explainability Model](604_Explainability_Model.md)
- [Model Governance](605_Model_Governance.md)
