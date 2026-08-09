# Crew API

## Purpose

This document defines the crew and assignment API design for the AI Dispatch Advisor. It covers current POC endpoints and the target API direction for crew availability, crew suitability, and assignment workflows.

## Current Implementation State

Current endpoints:

```text
GET /api/crews
GET /api/assignments
```

Current source data:

```text
data/scenarios/{active-scenario}/Crews.csv
data/scenarios/{active-scenario}/Assignments.csv
```

The current implementation returns synthetic crew and active assignment records for the selected scenario. Accepted recommendations create local SQLite-backed demo assignments, and API responses overlay those assignments onto crew and incident state. It does not support general assignment editing, cancellation, historical assignment queries, or workforce-system writeback.

## Crew Data Model

Current fields:

| Field | Description |
| --- | --- |
| `crew_id` | Synthetic crew identifier |
| `crew_name` | Crew display name |
| `home_region` | Primary operating region |
| `status` | Current demo availability state |
| `capability` | Crew capability or work type |
| `current_location` | Demo location or staging point |
| `shift_remaining_hours` | Remaining shift availability |
| `storm_ready` | Whether crew is storm-ready |
| `travel_minutes_to_selected_incident` | Demo travel estimate used by recommendation logic |

## Assignment Data Model

Current fields:

| Field | Description |
| --- | --- |
| `assignment_id` | Synthetic assignment identifier |
| `incident_id` | Related incident |
| `crew_id` | Assigned crew |
| `status` | Assignment status |
| `assigned_at` | Assignment timestamp |
| `notes` | Assignment notes |

## GET /api/crews

### Purpose

Returns all synthetic crews in the active demo scenario.

### Current Behavior

- Loads `Crews.csv` for the active scenario.
- Applies active seed and accepted demo assignment state.
- Returns assigned incident context for each crew.

### Example Response Shape

```json
[
  {
    "crew_id": "CR-01",
    "crew_name": "North Line Alpha",
    "home_region": "North",
    "status": "available",
    "capability": "line",
    "current_location": "Millbrook Service Center",
    "shift_remaining_hours": 6,
    "storm_ready": true,
    "travel_minutes_to_selected_incident": 18
  }
]
```

### Target Query Parameters

Future versions should support:

| Parameter | Purpose |
| --- | --- |
| `region` | Filter by home or current operating region |
| `status` | Filter by available, assigned, staged, unavailable |
| `capability` | Filter by crew skill or work type |
| `storm_ready` | Filter storm-ready crews |
| `incident_id` | Return suitability context for selected incident |

## GET /api/assignments

### Purpose

Returns active assignment data.

### Current Behavior

- Loads active seed assignments from `Assignments.csv` for the selected scenario.
- Adds accepted demo assignments persisted under that scenario.
- Returns the combined active assignment list with `scenario_id`.

### Target Enhancements

Future assignment APIs should support:

- Historical assignments.
- Assignment modification.
- Assignment cancellation.
- Assignment status update.
- Integration writeback status.
- Audit event linkage.

## Target Assignment Actions

Future endpoints may include:

```text
POST /api/v1/assignments
PATCH /api/v1/assignments/{assignment_id}
POST /api/v1/assignments/{assignment_id}/cancel
```

These endpoints should only be introduced when authorization, audit, and system-of-record behavior are defined.

## Crew Suitability

Crew suitability is currently returned through the recommendation endpoint rather than a dedicated crew endpoint.

Future options:

```text
GET /api/v1/incidents/{incident_id}/crew-options
POST /api/v1/crew-suitability
```

Suitability responses should include:

- Crew identifier.
- Capability match.
- Availability.
- Travel estimate.
- Shift constraints.
- Equipment constraints.
- Safety constraints.
- Suitability score or qualitative rank.

## Source System Direction

Target source systems:

- Crew management system.
- Workforce management system.
- OMS assignments.
- Mobile workforce platform.
- Contractor or mutual assistance roster.

The AI Dispatch Advisor should preserve the system-of-record role of approved utility platforms.

## Data Freshness

Crew data is time-sensitive. Future responses should include:

- Last status update.
- Last location update.
- Source system.
- Confidence or freshness indicator.
- Assignment conflict indicator.

Stale crew status or location should lower recommendation confidence.

## Security Considerations

Crew APIs may expose sensitive workforce information. Future implementation should:

- Enforce role-based access.
- Avoid unnecessary personal details.
- Protect location data.
- Audit assignment changes.
- Limit write actions to authorized roles.

## Related Documents

- [API Overview](402_API_Overview.md)
- [Outage API](403_Outage_API.md)
- [Recommendation API](405_Recommendation_API.md)
- [Integration API](406_Integration_API.md)
