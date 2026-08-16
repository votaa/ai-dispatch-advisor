# Integration API

## Purpose

This document defines the API direction for integration-related backend capabilities in the AI Dispatch Advisor. It covers current POC integration simulation and future API surfaces for source-system status, adapter behavior, data freshness, and writeback governance.

## Current Implementation State

The current POC does not include live integrations. Source systems are simulated by files under:

```text
data/scenarios/base/
```

Current context endpoints:

```text
GET /api/weather
GET /api/critical-facilities
GET /api/topology
```

These endpoints expose synthetic data directly from CSV files.

## Target Integration Domains

The backend should eventually support integration visibility and adapter-backed data access for:

- OMS.
- GIS.
- SCADA or DMS.
- Crew management.
- Weather services.
- AMI.
- Enterprise identity provider.
- Observability and audit platforms.

## Integration API Goals

Integration APIs should:

- Expose integration health to authorized users.
- Show source data freshness.
- Support adapter diagnostics without exposing secrets.
- Provide normalized operational context to frontend and recommendation services.
- Support controlled writeback where approved.
- Make degraded integration state visible.

Integration APIs should not:

- Expose raw credentials.
- Expose vendor-specific payloads directly to normal frontend views.
- Allow unaudited operational writeback.
- Turn Copilot text into source-system actions.

## Current Context Endpoints

### GET /api/weather

Purpose:

- Returns synthetic regional weather data.

Future direction:

- Add forecast horizon.
- Add severe weather alerts.
- Add timestamp and source metadata.
- Support region filtering.

### GET /api/critical-facilities

Purpose:

- Returns synthetic critical facility records.

Future direction:

- Link facilities to incidents, feeders, circuits, and customer impact.
- Add facility category, priority, and source metadata.

### GET /api/topology

Purpose:

- Returns simplified synthetic feeder and asset connectivity.

Future direction:

- Replace with normalized GIS and network model data.
- Support topology queries by feeder, asset, incident, or region.

## Target Integration Health API

Future endpoint:

```text
GET /api/v1/integrations/health
```

Example response:

```json
{
  "systems": [
    {
      "system": "OMS",
      "status": "healthy",
      "last_success_at": "2026-08-02T14:20:00-04:00",
      "latency_ms": 180,
      "staleness_seconds": 30
    },
    {
      "system": "GIS",
      "status": "degraded",
      "last_success_at": "2026-08-02T13:55:00-04:00",
      "latency_ms": 420,
      "staleness_seconds": 1800,
      "message": "Topology cache is stale"
    }
  ]
}
```

## Target Source Metadata

Domain API responses should eventually include source metadata:

```json
{
  "source": {
    "system": "OMS",
    "record_id": "OMS-12345",
    "source_updated_at": "2026-08-02T14:20:00-04:00",
    "loaded_at": "2026-08-02T14:20:30-04:00",
    "freshness": "current"
  }
}
```

## Writeback Governance

Potential writeback actions:

- Approved crew assignment to OMS.
- Assignment status update.
- Recommendation action note.
- Deferred or overridden recommendation note.

Writeback should require:

- Authenticated user.
- Authorized role.
- Validated request.
- Audit event.
- Source-system acknowledgement.
- Error handling and retry strategy.

The current POC does not perform writeback.

Phase 7 implementation remains read-only. Operational writeback requires later authentication, authorization, production audit, source acknowledgement, retry/reconciliation, and governance approval; defining an adapter method here does not authorize its implementation or use.

## Adapter Contract Direction

Each adapter should expose internal methods such as:

```text
get_outages()
get_incident(incident_id)
get_crews()
get_assignments()
get_topology(feeder_id)
get_weather(region)
write_assignment(action)
health()
```

These are backend service contracts, not necessarily public HTTP APIs.

## Degraded State Behavior

Integration APIs should support these states:

| State | Meaning |
| --- | --- |
| Healthy | Source system is reachable and fresh |
| Degraded | Source system reachable but delayed, stale, or partially failing |
| Unavailable | Source system is not reachable |
| Disabled | Integration intentionally disabled in environment |
| Unknown | Integration status cannot be determined |

Recommendation confidence and UI indicators should reflect degraded state.

## Security Requirements

Future integration APIs must:

- Hide credentials.
- Restrict diagnostics to authorized users.
- Avoid leaking sensitive infrastructure details.
- Use structured logs.
- Include correlation identifiers.
- Preserve audit trails for write operations.

## POC-to-Enterprise Transition

| POC Behavior | Enterprise Direction |
| --- | --- |
| CSV-backed source data | Adapter-backed source retrieval |
| Static weather context | Weather provider integration |
| Static topology CSV | GIS/network model integration |
| No health endpoint | Integration health and freshness APIs |
| No writeback | Governed writeback with audit and authorization |

## Related Documents

- [Backend Service Design](401_Backend_Service_Design.md)
- [API Overview](402_API_Overview.md)
- [Outage API](403_Outage_API.md)
- [Crew API](404_Crew_API.md)
- [Recommendation API](405_Recommendation_API.md)
- [Phase 7 Enterprise Integration Adapter Plan](../900_Delivery/907_Phase_7_Implementation_Plan.md)
