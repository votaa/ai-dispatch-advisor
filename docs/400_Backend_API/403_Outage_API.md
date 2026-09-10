# Outage API

## Purpose

This document defines the outage and incident API design for the AI Dispatch Advisor. It covers the current POC incident endpoints and the target API direction for enterprise outage management use.

## Current Implementation State

Current endpoints:

```text
GET /api/incidents
GET /api/incidents/{incident_id}
GET /api/dashboard
```

Current source data:

```text
data/scenarios/{active-scenario}/PendingIncidents.csv
```

The current API treats active outage records as incidents. Future implementations may distinguish outage events, trouble calls, hazards, work packages, and assignments more explicitly.

## Domain Terms

| Term | Meaning |
| --- | --- |
| Incident | Operational event requiring review or response |
| Outage | Service interruption affecting one or more customers |
| Feeder | Distribution network segment associated with the incident |
| Critical Facility | High-priority facility affected by outage conditions |
| Hazard | Safety or access condition affecting dispatch |
| ETR | Estimated time of restoration |

## Current Incident Fields

The current synthetic incident records include:

| Field | Description |
| --- | --- |
| `incident_id` | Synthetic incident identifier |
| `region` | Operating region |
| `municipality` | Municipality or local area |
| `feeder` | Feeder identifier |
| `severity` | Critical, high, medium, or low |
| `status` | Current demo status |
| `customers_out` | Number of affected customers |
| `critical_facility` | Whether critical facility impact exists |
| `hazard` | Hazard description |
| `required_skill` | Crew skill needed for response |
| `age_minutes` | Age of the incident in minutes |
| `latitude` | Demo latitude |
| `longitude` | Demo longitude |
| `etr` | Estimated restoration timestamp |

## GET /api/incidents

### Purpose

Returns active incidents ranked by the current deterministic POC scoring function.

### Current Behavior

- Loads synthetic CSV incident data.
- Ranks incidents using customer impact, severity, hazard, critical facility impact, and age.
- Returns a JSON array.

### Example Response Shape

```json
[
  {
    "incident_id": "INC-1001",
    "region": "North",
    "municipality": "Millbrook",
    "feeder": "FDR-12",
    "severity": "critical",
    "status": "unassigned",
    "customers_out": 2840,
    "critical_facility": true,
    "hazard": "downed wire",
    "required_skill": "line",
    "age_minutes": 76,
    "latitude": 41.812,
    "longitude": -73.694,
    "etr": "2026-08-02T16:40:00-04:00"
  }
]
```

### Target Query Parameters

Future versions should support:

| Parameter | Purpose |
| --- | --- |
| `region` | Filter by operating region |
| `severity` | Filter by incident severity |
| `status` | Filter by incident status |
| `critical_facility` | Filter critical facility impact |
| `assigned` | Filter assigned or unassigned incidents |
| `limit` | Limit result size |
| `offset` or `cursor` | Pagination |
| `sort` | Sort key |

## GET /api/incidents/{incident_id}

### Purpose

Returns detail for a single incident.

### Current Behavior

- Looks up an incident by `incident_id`.
- Returns `404 Not Found` when absent.

### Target Enhancements

Future incident detail should include:

- Related critical facilities.
- Related crews and assignments.
- Recommendation history.
- Source system metadata.
- Data freshness.
- Weather context.
- Topology and asset context.
- Audit history.

## GET /api/dashboard

### Purpose

Returns outage operations summary metrics for the dashboard.

### Current Response Fields

| Field | Description |
| --- | --- |
| `active_incidents` | Count of active demo incidents |
| `customers_out` | Total affected customers |
| `available_crews` | Count of available crews |
| `assigned_crews` | Count of assigned crews |
| `critical_facility_incidents` | Count of incidents affecting critical facilities |
| `high_priority_incidents` | Count of high and critical incidents |
| `top_incidents` | Up to 50 ranked incidents for the dashboard display-limit selector |
| `scenario` | Demo scenario label |
| `data_freshness` | Current demo freshness note |

## Target Outage API Model

Future outage APIs should distinguish:

- Source outage events.
- Internal incident records.
- Work packages.
- Hazards.
- Customer impact snapshots.
- ETR changes.
- Critical facility impacts.
- Restoration status updates.

## Data Freshness

Future outage responses should include:

- `source_system`.
- `source_record_id`.
- `source_updated_at`.
- `loaded_at`.
- `freshness_status`.
- `quality_warnings`.

This is important because stale outage data should reduce recommendation confidence.

## Error Handling

Expected target error cases:

| Case | Status |
| --- | --- |
| Incident not found | `404` |
| Invalid filter | `422` |
| Source data unavailable | `503` or degraded response |
| Unauthorized access | `401` |
| Forbidden region or role | `403` |

## Related Documents

- [API Overview](402_API_Overview.md)
- [Crew API](404_Crew_API.md)
- [Recommendation API](405_Recommendation_API.md)
