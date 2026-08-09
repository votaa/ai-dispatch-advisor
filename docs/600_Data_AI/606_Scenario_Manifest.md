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
| `expected_conditions` | Array of strings | Yes | Observable operating assumptions or conditions represented by the scenario data. |
| `files` | Object | Yes | Logical data-domain keys mapped to CSV filenames in the same scenario directory. |

No optional fields are defined in manifest schema version `1.0`. New fields may be added in a later schema version after their ownership and validation behavior are documented.

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
- `expected_conditions` contains at least one non-blank entry.
- `files` contains every required logical key exactly once.
- Each file value is a CSV filename relative to the scenario directory; absolute paths and parent-directory traversal are not allowed.
- Every inventoried CSV file exists in the same scenario directory.
- CSV headers conform to the domain definitions in the data model.
- Identifiers are unique within their domain, and assignment references resolve to existing incident and crew identifiers.

The backend scenario service automatically enforces these rules when serving `GET /api/scenarios`, `GET /api/scenarios/active`, and `PUT /api/scenarios/active`. A validation failure prevents activation, preserves the current scenario, and returns structured error details.

## Change Management

- Preserve `scenario_id` after a scenario is used in tests, demos, or audit records.
- Increment `schema_version` when a manifest contract change is not backward compatible.
- Update this document before introducing new required fields, logical file keys, or event types.
- Keep scenario data synthetic and free of customer personal information, operationally sensitive network details, and live credentials.

## Related Documents

- [Data Model](601_Data_Model.md)
- [Optimization Engine](602_Optimization_Engine.md)
- [Test Strategy](../900_Delivery/901_Test_Strategy.md)
- [Implementation Plan](../900_Delivery/902_Implementation_Plan.md)
