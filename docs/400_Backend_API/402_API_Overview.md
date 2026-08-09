# API Overview

## Purpose

This document provides an overview of the AI Dispatch Advisor API. It describes API principles, current endpoints, request and response conventions, error handling, versioning direction, and future production considerations.

## Current API State

The current FastAPI backend exposes the following endpoints:

```text
GET  /health
GET  /api/dashboard
GET  /api/incidents
GET  /api/incidents/{incident_id}
GET  /api/crews
GET  /api/assignments
GET  /api/weather
GET  /api/critical-facilities
GET  /api/topology
POST /api/optimize
POST /api/chat
```

FastAPI OpenAPI documentation is available locally at:

```text
http://127.0.0.1:8000/docs
```

## API Design Principles

The API should be:

- Domain-oriented.
- Explicitly typed.
- Frontend-consumable.
- Stable enough to document and test.
- Designed for human-in-the-loop dispatch workflows.
- Clear about recommendation versus approved action.
- Auditable for user actions and operational decisions.
- Integration-ready without exposing vendor-specific source schemas.

## API Boundary

The backend API is responsible for:

- Serving operational data to the frontend.
- Generating dispatch recommendations.
- Capturing user actions.
- Providing recommendation explanations.
- Hiding source-system complexity.
- Enforcing security controls when implemented.

The API should not:

- Directly expose source-system credentials.
- Allow frontend code to write directly to source systems.
- Treat Copilot text as an operational command.
- Bypass audit logging for dispatch decisions.

## Current API Groups

| Group | Current Endpoints | Purpose |
| --- | --- | --- |
| Health | `/health` | Local service health |
| Scenarios | `/api/scenarios`, `/api/scenarios/active` | Validated scenario discovery and active-scenario metadata |
| Dashboard | `/api/dashboard` | Summary metrics and top incidents |
| Incidents | `/api/incidents`, `/api/incidents/{incident_id}` | Active incident data |
| Crews | `/api/crews` | Crew availability and capability |
| Assignments | `/api/assignments` | Active assignment data |
| Context | `/api/weather`, `/api/critical-facilities`, `/api/topology` | Supporting operational context |
| Recommendations | `/api/optimize` | Dispatch recommendation generation |
| Copilot | `/api/chat` | Advisory demo response |

## Target API Groups

Target API groups should include:

- Dashboard.
- Incidents and outages.
- Crews and assignments.
- Recommendations.
- Recommendation actions.
- Scenarios.
- Audit events.
- Integration health.
- Configuration and reference data.
- Copilot advisory context.

## Request Conventions

Requests should:

- Use JSON request bodies for non-read operations.
- Use path parameters for specific resource identifiers.
- Use query parameters for filtering, sorting, pagination, and scenario selection.
- Include idempotency keys for future write operations where repeated submission is possible.
- Include user identity through authentication context when security is implemented.

## Response Conventions

Responses should:

- Use JSON.
- Use stable field names.
- Include identifiers for domain resources.
- Include status and timestamps where relevant.
- Include source metadata where data quality matters.
- Include structured explanation fields for recommendations.
- Avoid requiring frontend parsing of free-text values for behavior.

## Error Response Direction

The target API should standardize error responses:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Incident not found",
    "correlation_id": "example-correlation-id",
    "details": {}
  }
}
```

Most current MVP endpoints use FastAPI default error responses. The read-only scenario service establishes the initial structured error contract for missing scenario configuration and invalid manifest or CSV data.

## Versioning Direction

The current MVP uses unversioned `/api/*` routes.

For production, use one of:

```text
/api/v1/incidents
/api/v1/crews
/api/v1/recommendations
```

Versioning should be introduced before external clients or integrations depend on the API contract.

## Pagination and Filtering

Future list endpoints should support:

- `limit`.
- `offset` or cursor.
- `sort`.
- `region`.
- `severity`.
- `status`.
- `critical_facility`.
- `updated_since`.

The current MVP returns full synthetic lists.

## Authentication and Authorization

Current state:

- No production authentication.
- No role-based authorization.

Target state:

- Enterprise identity provider integration.
- Role-aware permissions.
- User identity attached to audit events.
- Backend-enforced authorization for recommendation actions and administrative functions.

## Audit Requirements

API operations that should generate audit events include:

- Recommendation generation.
- Recommendation acceptance.
- Recommendation modification.
- Recommendation deferral.
- Recommendation override.
- Integration writeback.
- Administrative configuration changes.

Audit event design will be expanded in later security and delivery documentation.

## Current API Testing

Current backend tests validate:

- `GET /health`.
- `GET /api/incidents`.
- `POST /api/optimize`.

Additional tests should be added as endpoint behavior matures.

## Related Documents

- [Backend Service Design](401_Backend_Service_Design.md)
- [Outage API](403_Outage_API.md)
- [Crew API](404_Crew_API.md)
- [Recommendation API](405_Recommendation_API.md)
- [Integration API](406_Integration_API.md)
