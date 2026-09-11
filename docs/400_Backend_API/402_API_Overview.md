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
POST /api/recommendation-actions
GET  /api/audit/events
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
| Scenarios | `GET /api/scenarios`, `GET /api/scenarios/active`, `PUT /api/scenarios/active` | Validated discovery, active metadata, and process-local activation |
| Dashboard | `/api/dashboard` | Summary metrics and top incidents |
| Incidents | `/api/incidents`, `/api/incidents/{incident_id}` | Active incident data |
| Crews | `/api/crews` | Crew availability and capability |
| Assignments | `/api/assignments` | Active assignment data |
| Context | `/api/weather`, `/api/critical-facilities`, `/api/topology` | Supporting operational context |
| Recommendations | `/api/optimize` | Dispatch recommendation generation |
| Copilot | `/api/chat` | Advisory demo response |

Scenario discovery and activation responses include optional `freshness` metadata:

```json
{
  "freshness": {
    "updated_at": "2026-08-09T10:41:03-04:00",
    "source": "repository_publish",
    "provenance": "Git commit 001559d"
  }
}
```

`updated_at` is authoritative only when supplied by the scenario publication workflow and must include a timezone offset. Legacy manifests remain valid and return `freshness: null`; clients must identify that state as unavailable rather than infer freshness from file modification times. See [Scenario Manifest](../600_Data_AI/606_Scenario_Manifest.md) for the complete contract and controlled source values.

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

Phase 4.1 establishes explicit Pydantic request and response contracts for health, dashboard, incident, crew, assignment, recommendation, recommendation-action, audit-history, scenario, and Copilot operations. Existing JSON field names and shapes are preserved for the frontend. Weather, critical-facility, and topology response contracts remain a later API-hardening task.

Phase 4.2 moves operational composition and workflow logic behind application services. API handlers now delegate to incident, crew, assignment, recommendation, decision, scenario, context, and Copilot services while preserving the established HTTP paths, status codes, and JSON contracts.

## Structured Error Contract

Phase 4.4 standardizes domain, request-validation, scenario, framework HTTP, and unexpected failures under the named `ErrorResponse`, `ApiError`, and `ErrorDetail` OpenAPI schemas:

```json
{
  "error": {
    "code": "entity_not_found",
    "message": "Incident not found",
    "correlation_id": "example-correlation-id",
    "details": [],
    "entity": "Incident",
    "entity_id": "INC-404"
  }
}
```

Every response includes `X-Correlation-ID`. A client-provided identifier is preserved when it contains 1–128 letters, digits, periods, underscores, colons, or hyphens and begins with a letter or digit; otherwise the API generates a UUID. Error bodies repeat the same identifier for support correlation. Validation errors identify the failing request location but do not echo submitted values, and unexpected failures return a safe generic message while logging the correlation identifier server-side.

Current stable error codes include:

| Code | Status | Meaning |
| --- | ---: | --- |
| `decision_reason_required` | 400 | A defer or override decision omitted its required reason |
| `entity_not_found` | 404 | A requested domain entity does not exist |
| `resource_not_found` | 404 | No API route or framework resource matched |
| `decision_incident_mismatch` | 409 | A submitted recommendation belongs to a different incident |
| `request_validation_failed` | 422 | Request path, query, or body validation failed |
| `scenario_not_found` | 404 | The requested scenario directory does not exist |
| `scenario_validation_failed` | 422 | Scenario manifest or CSV validation failed |
| `internal_server_error` | 500 | An unexpected failure was safely concealed from the client |

Clients should branch on `error.code`, display `error.message`, optionally display safe `details`, and retain `correlation_id` for troubleshooting. They should not parse message text to determine behavior.

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
- Recommendation decisions, accepted assignment overlays, and audit history.
- Scenario discovery, validation, activation, and isolation.
- OpenAPI exposure of explicit core response models.
- Rejection of undeclared fields on typed core request models.

Additional tests should be added as endpoint behavior matures.

## Related Documents

- [Backend Service Design](401_Backend_Service_Design.md)
- [Outage API](403_Outage_API.md)
- [Crew API](404_Crew_API.md)
- [Recommendation API](405_Recommendation_API.md)
- [Integration API](406_Integration_API.md)
