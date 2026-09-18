# Scenario Manifest

## Purpose

This document defines the metadata contract for synthetic AI Dispatch Advisor demo scenarios. Each scenario directory should contain one `scenario.json` manifest that identifies the scenario, describes its operating conditions, and inventories the CSV files that belong to it.

The backend scenario service loads and validates this contract for discovery, active-scenario inspection, and controlled process-local activation. The frontend uses the validated scenario metadata to populate its runtime selector and active-scenario details.

## Location and Naming

Scenario assets use the following structure:

```text
data/scenarios/<scenario_id>/
  scenario.json
  PendingIncidents.csv
  Crews.csv
  Assignments.csv
  HistoricalRepairs.csv
  Weather.csv
  CriticalFacilities.csv
  Topology.csv
```

The directory name and `scenario_id` value must match.

## Manifest Example

```json
{
  "schema_version": "1.0",
  "scenario_id": "base",
  "name": "Base Operations",
  "description": "Standard blue-sky outage and crew dispatch demonstration.",
  "event_type": "blue_sky",
  "freshness": {
    "updated_at": "2026-08-09T10:41:03-04:00",
    "source": "repository_publish",
    "provenance": "Git commit 001559d"
  },
  "expected_conditions": [
    "Normal staffing levels",
    "Multiple active outages",
    "No major weather constraints"
  ],
  "files": {
    "incidents": "PendingIncidents.csv",
    "crews": "Crews.csv",
    "assignments": "Assignments.csv",
    "historical_repairs": "HistoricalRepairs.csv",
    "weather": "Weather.csv",
    "critical_facilities": "CriticalFacilities.csv",
    "topology": "Topology.csv"
  }
}
```

## Field Definitions

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `schema_version` | String | Yes | Version of the manifest contract. The initial version is `1.0`. |
| `scenario_id` | String | Yes | Stable machine-readable identifier that matches the scenario directory name. |
| `name` | String | Yes | Short user-facing scenario name. |
| `description` | String | Yes | Concise explanation of the scenario's purpose and operating context. |
| `event_type` | String | Yes | Controlled event category used to group and select scenarios. |
| `freshness` | Object or null | No | Authoritative datetime and provenance for the most recent scenario publication or update. Omit it when no authoritative value is available. |
| `expected_conditions` | Array of strings | Yes | Observable operating assumptions or conditions represented by the scenario data. |
| `files` | Object | Yes | Logical data-domain keys mapped to CSV filenames in the same scenario directory. |

The optional `freshness` object is a backward-compatible version `1.0` addition. A missing object is returned through the API as `null` and displayed as `Scenario Last Updated Unavailable`; the service never substitutes filesystem modification time or another inferred timestamp.

### Freshness Metadata

When `freshness` is present, all three fields are required:

| Field | Type | Description |
| --- | --- | --- |
| `freshness.updated_at` | RFC 3339 datetime | Authoritative time of the represented generation, upload, repository publication, or scenario update. A timezone offset is required. |
| `freshness.source` | String | Controlled provenance category: `scenario_generation`, `file_upload`, `repository_publish`, or `scenario_update`. |
| `freshness.provenance` | String | Non-blank identifier for the responsible generator, upload workflow, repository revision, or update process. |

The API preserves the original offset. The operator UI converts valid timestamps to UTC and uses a fixed 24-hour display: `Scenario Last Updated MM/DD/YYYY HH:MM UTC`. UTC makes scenario switching and review output deterministic across browsers and operator locations.

## Event Types

Version `1.0` supports these event types:

| Value | Intended Use |
| --- | --- |
| `blue_sky` | Routine daily outage and dispatch operations |
| `storm` | Elevated outage volume or weather-driven operations |
| `crew_shortage` | Limited crew availability or constrained capabilities |
| `critical_facility` | Outages where critical-facility impact drives prioritization |

Additional event types require a documentation update before use so scenario labels remain consistent.

## CSV File Inventory

All seven logical file entries are required in schema version `1.0`.

| Logical Key | Expected Filename | Data Domain |
| --- | --- | --- |
| `incidents` | `PendingIncidents.csv` | Active outage and trouble incidents |
| `crews` | `Crews.csv` | Crew availability, capability, and location context |
| `assignments` | `Assignments.csv` | Active synthetic crew assignments |
| `historical_repairs` | `HistoricalRepairs.csv` | Reference repair history |
| `weather` | `Weather.csv` | Regional weather and hazard conditions |
| `critical_facilities` | `CriticalFacilities.csv` | Priority facility context |
| `topology` | `Topology.csv` | Simplified feeder and asset relationships |

## Validation Rules

A conforming version `1.0` manifest must meet these rules:

- The file is valid UTF-8 JSON and its root value is an object.
- Every required field is present and uses the documented type.
- `schema_version` is exactly `1.0`.
- `scenario_id` is unique, uses lowercase letters, numbers, hyphens, or underscores, and matches its directory name.
- `name` and `description` are not blank.
- `event_type` is one of the documented version `1.0` values.
- When supplied, `freshness.updated_at` includes a timezone offset, `freshness.source` is a supported value, and `freshness.provenance` is not blank.
- `expected_conditions` contains at least one non-blank entry.
- `files` contains every required logical key exactly once.
- Each file value is a CSV filename relative to the scenario directory; absolute paths and parent-directory traversal are not allowed.
- Every inventoried CSV file exists in the same scenario directory.
- CSV headers conform to the domain definitions in the data model.
- `PendingIncidents.csv` may include `geography_reference_id` after `municipality`; population-constrained generated scenarios require it, while existing version `1.0` fixtures remain compatible without it.
- Identifiers are unique within their domain, and assignment references resolve to existing incident and crew identifiers.
- A crew with an active assignment has `assigned` status, and every crew with `assigned` status has exactly one active assignment.

The backend scenario service automatically enforces these rules when serving `GET /api/scenarios`, `GET /api/scenarios/active`, and `PUT /api/scenarios/active`. A validation failure prevents activation, preserves the current scenario, and returns structured error details.

## Change Management

- Preserve `scenario_id` after a scenario is used in tests, demos, or audit records.
- Update `freshness` only from the workflow that authoritatively generated, uploaded, published, or updated the complete scenario; do not infer it from runtime filesystem timestamps.
- Increment `schema_version` when a manifest contract change is not backward compatible.
- Update this document before introducing new required fields, logical file keys, or event types.
- Keep scenario data synthetic and free of customer personal information, operationally sensitive network details, and live credentials.

## Related Documents

- [Data Model](601_Data_Model.md)
- [Optimization Engine](602_Optimization_Engine.md)
- [Test Strategy](../900_Delivery/901_Test_Strategy.md)
- [Implementation Plan](../900_Delivery/902_Implementation_Plan.md)
