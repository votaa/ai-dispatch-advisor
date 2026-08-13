# Backend Service Design

## Purpose

This document defines the backend service design for the AI Dispatch Advisor. It describes the current FastAPI implementation, intended service boundaries, domain responsibilities, and target evolution from POC backend to enterprise-ready backend architecture.

## Current Implementation State

The Developer Bootstrap MVP includes a FastAPI backend under:

```text
backend/
  app/
    __init__.py
    api_models.py
    data_loader.py
    database_migrations.py
    decision_store.py
    domain/
      models.py
    main.py
    recommendations.py
    scenario_service.py
    migrations/
      001_create_decision_store.sql
      002_add_scenario_scope.sql
      003_add_decision_indexes.sql
    services/
      assignment_service.py
      context_service.py
      copilot_service.py
      crew_service.py
      decision_service.py
      incident_service.py
      recommendation_service.py
      scenario_management_service.py
  tests/
    test_api.py
  requirements.txt
  pytest.ini
```

The current backend:

- Exposes basic REST endpoints.
- Loads synthetic CSV scenario data.
- Produces deterministic recommendation responses.
- Provides keyword-based Copilot demo responses.
- Validates core request and response contracts with Pydantic domain models.
- Persists scenario-scoped recommendation decisions and accepted assignments in SQLite.
- Applies versioned SQLite migrations before serving API requests.
- Delegates state composition and workflow behavior from API handlers to directly testable services.
- Supports local CORS for the React frontend.
- Includes API, persistence, scenario, and recommendation tests.

The current backend is intentionally POC-grade. It is not yet production-persistent, authenticated, authorized, integrated with source systems, or connected to a real AI service.

## Backend Design Goals

The backend should:

- Provide stable API contracts for the frontend.
- Encapsulate dispatch domain logic.
- Separate API handlers from recommendation and data services.
- Support explainable recommendations.
- Preserve human-in-the-loop dispatch workflows.
- Support auditability and traceability.
- Isolate enterprise integrations through adapters.
- Support local POC operation and future production deployment.

## Current Backend Components

| Component | File | Responsibility |
| --- | --- | --- |
| FastAPI app | `backend/app/main.py` | API routes, CORS, and request orchestration |
| API contracts | `backend/app/api_models.py` | Core request and composite response models |
| Domain contracts | `backend/app/domain/models.py` | Explicit incident, crew, assignment, recommendation, decision, audit, and scenario entities |
| Data loader | `backend/app/data_loader.py` | Reads and coerces synthetic CSV scenario data |
| Migration runner | `backend/app/database_migrations.py` | Discovers, validates, baselines, and transactionally applies numbered SQL migrations |
| SQL migrations | `backend/app/migrations/` | Immutable application-owned decision-store schema history |
| Decision store | `backend/app/decision_store.py` | Persists scenario-scoped decisions and accepted assignments in SQLite |
| Recommendation logic | `backend/app/recommendations.py` | Ranks incidents, recommends crews, builds dashboard summary |
| Scenario service | `backend/app/scenario_service.py` | Discovers and validates manifested scenario inputs |
| Application services | `backend/app/services/` | Compose scenario inputs and mutable state into typed incident, crew, assignment, recommendation, decision, scenario, context, and Copilot workflows |
| Service container | `backend/app/services/container.py` | Wires current CSV and SQLite adapters into application services |
| Tests | `backend/tests/` | Validates API contracts, services, scenarios, persistence, and recommendation behavior |

## Current Service Boundaries

Phase 4.2 introduces the following application-service ownership:

| Service | Responsibility |
| --- | --- |
| Assignment service | Merge active baseline and accepted assignments, deduplicate them, and apply scenario identity |
| Incident service | Compose ranked incidents with assigned crews and latest decisions |
| Crew service | Compose crews with active assigned-incident context |
| Recommendation service | Produce dashboard summaries and typed recommendations from current operational state |
| Decision service | Validate recommendation actions, record decisions, and retrieve bounded recent history |
| Scenario management service | Discover, read, and activate validated scenarios |
| Operational context service | Expose weather, critical-facility, and topology inputs without leaking loaders into API handlers |
| Copilot service | Produce advisory responses using incident and recommendation services |

Services receive data, persistence, or peer-service dependencies through their constructors. `container.py` is the composition root for the current local adapters. FastAPI handlers validate HTTP input, delegate to a service, map service errors to the existing HTTP behavior, and return declared response models.

## Target Backend Structure

As implementation matures, routers, configuration, persistence repositories, and integration adapters should be separated further:

```text
backend/app/
  api/
    routers/
      incidents.py
      crews.py
      assignments.py
      recommendations.py
      scenarios.py
      audit.py
      integrations.py
  core/
    config.py
    security.py
    logging.py
  domain/
    models.py
  services/
    incident_service.py
    crew_service.py
    recommendation_service.py
    decision_service.py
  integrations/
    oms_adapter.py
    gis_adapter.py
    scada_adapter.py
    crew_adapter.py
    weather_adapter.py
  persistence/
    repositories.py
    database.py
```

The service package now exists; router, repository, integration, and core-configuration extraction remain target work.

## API Layer Responsibilities

The API layer should:

- Accept HTTP requests.
- Validate request payloads.
- Enforce authentication and authorization when implemented.
- Call domain services.
- Return documented response models.
- Map domain errors to appropriate HTTP status codes.

The API layer should not:

- Contain complex optimization logic.
- Directly embed vendor-specific integration mappings.
- Build frontend-specific display text where structured data is better.
- Bypass audit logging for user decisions.

## Domain Service Responsibilities

Domain services should encapsulate:

- Incident retrieval and prioritization.
- Crew suitability and availability.
- Recommendation generation.
- Scenario comparison.
- User recommendation actions.
- Audit event creation.
- Data freshness and quality evaluation.

Domain services should be testable without running the web server.

## Phase 4 Persistence Boundary

Decision `D-007` establishes two distinct persistence responsibilities:

- Version-controlled scenario manifests and CSV files are immutable inputs for incidents, crews, baseline assignments, weather, facilities, topology, and repair history.
- SQLite owns mutable recommendation decisions, recommendation audit history, and accepted operational assignments.
- Mutable records are isolated by `scenario_id` and overlay scenario inputs when domain state is assembled.
- The backend does not write to scenario files.

Decision `D-008` replaces ad hoc schema initialization with ordered SQL migrations. FastAPI startup applies pending migrations before accepting requests. The `schema_migrations` table records each version, name, checksum, and application timestamp. Existing unversioned POC schemas are recognized and baselined only when both decision tables match a supported shape; unknown or inconsistent schemas fail startup rather than being modified speculatively.

Applied migration files are immutable. Every later schema change must be introduced as the next consecutive migration and include fresh-database, upgrade-path, preservation, and repeat-execution coverage. A future normalized operational store may persist incident and crew projections when integration requirements justify it; that is not part of the current POC boundary.

## Integration Responsibilities

Integration adapters should:

- Connect to OMS, GIS, SCADA, crew, weather, AMI, and identity systems.
- Normalize external payloads.
- Track data provenance and freshness.
- Handle retry, timeout, and failure behavior.
- Avoid leaking vendor-specific schemas into domain services or frontend responses.

## Error Handling Strategy

The backend should provide consistent error behavior:

| Situation | Expected API Behavior |
| --- | --- |
| Resource not found | `404 Not Found` with clear detail |
| Invalid request | `422 Unprocessable Entity` from validation or explicit structured error |
| Unauthorized user | `401 Unauthorized` when authentication exists |
| Forbidden action | `403 Forbidden` when authorization exists |
| Integration unavailable | Controlled degraded response or `503 Service Unavailable` |
| Unexpected server failure | `500 Internal Server Error` with logged correlation identifier |

The current MVP uses FastAPI defaults and limited explicit errors.

## Testing Strategy

Backend tests should cover:

- Health endpoint.
- Core read endpoints.
- Recommendation endpoint.
- User action endpoints once implemented.
- Error responses.
- Data loader behavior.
- Recommendation service edge cases.
- Integration adapter contract tests when adapters exist.

Current tests include API regressions plus direct service tests for typed outputs, state overlays, decision validation, missing entities, scenario activation, and Copilot access to current runtime state.

## Configuration

Current configuration:

- `AIDA_DEMO_SCENARIO` selects the synthetic data scenario.
- `AIDA_DATA_ROOT` can override data location.

Target configuration should include:

- Environment name.
- API CORS origins.
- Database URL.
- Integration endpoints.
- Secret references.
- Logging level.
- Feature flags.
- AI service configuration.

## Security Boundary

The backend is the trust boundary for:

- User action validation.
- Authorization.
- Audit event creation.
- Integration credentials.
- Source-system writeback.
- Recommendation generation.

The frontend should not be trusted to enforce operational permissions.

## Current Gaps

Known gaps:

- No authentication.
- No authorization.
- API routes remain in one module rather than domain routers.
- Production database selection, backup, rollback, and migration operations are not yet defined.
- Structured errors are not yet consistent across all domain endpoints.
- No integration adapters.
- No production logging or correlation IDs.
- Supporting context endpoints do not yet have formal response models.

## Related Documents

- [API Overview](402_API_Overview.md)
- [Outage API](403_Outage_API.md)
- [Crew API](404_Crew_API.md)
- [Recommendation API](405_Recommendation_API.md)
- [Integration API](406_Integration_API.md)
