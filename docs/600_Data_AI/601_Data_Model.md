# Data Model

## Purpose

This document defines the data model direction for the AI Dispatch Advisor. It describes the current proof-of-concept data assets, target domain entities, ownership boundaries, source metadata, and persistence evolution.

## Current Implementation State

The Developer Bootstrap MVP uses four synthetic scenarios as source data:

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

The backend currently reads CSV files directly. The SQLite database can be generated locally for development, but it is not yet the active backend data source.

Each scenario directory includes a `scenario.json` metadata and file-inventory contract as defined in [Scenario Manifest](606_Scenario_Manifest.md). The backend scenario service validates metadata, required files, CSV headers, identifiers, and assignment references before process-local activation. Recommendation decisions and accepted demo assignments are filtered by `scenario_id` so state remains isolated while switching.

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
