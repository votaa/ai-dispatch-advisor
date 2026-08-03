# Deployment and Operations

## Purpose

This document defines deployment and operations guidance for the AI Dispatch Advisor. It covers the current local POC deployment, target environments, operational responsibilities, release considerations, configuration, and production readiness gaps.

## Current Implementation State

The current POC supports:

- Local frontend development with Vite.
- Local backend development with Uvicorn.
- Docker Compose for local full-stack startup.
- GitHub Actions CI for backend tests and frontend build.
- Local SQLite initialization for demo support.

Current local URLs:

```text
Frontend: http://127.0.0.1:5173/
Backend:  http://127.0.0.1:8000/
API Docs: http://127.0.0.1:8000/docs
```

## Deployment Goals

Deployment and operations should:

- Support reliable local development.
- Support repeatable CI validation.
- Support separate frontend and backend deployment.
- Support environment-specific configuration.
- Keep secrets out of source control.
- Support enterprise observability.
- Support rollback and release traceability.
- Preserve audit data across deployments.

## Environment Model

Recommended environments:

| Environment | Purpose |
| --- | --- |
| Local | Individual development and POC review |
| Development | Shared engineering integration |
| Test / QA | Validation and stakeholder review |
| Staging | Production-like release validation |
| Production | Approved operational use |

## Current Local Operations

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Docker:

```bash
docker compose up
```

## Configuration Management

Current configuration:

- `AIDA_DEMO_SCENARIO`.
- `AIDA_DATA_ROOT`.
- `VITE_API_BASE_URL`.

Target configuration:

- Environment name.
- API base URLs.
- Database connection.
- Identity provider configuration.
- Integration endpoints.
- Secret references.
- Feature flags.
- Logging level.
- Scenario selection for non-production.

Configuration should be environment-specific and should not include raw secrets in source control.

## Release Operations

Future release process should include:

- CI pass.
- Versioned build artifact.
- Deployment approval.
- Environment promotion.
- Smoke testing.
- Rollback plan.
- Release notes.
- Documentation update when behavior changes.

## Operational Ownership

| Area | Likely Owner |
| --- | --- |
| Frontend deployment | Frontend or platform engineering |
| Backend deployment | Backend or platform engineering |
| Database operations | Platform or database team |
| Integration operations | Integration engineering and utility IT |
| Security monitoring | Cybersecurity and platform teams |
| Incident response | SRE, support, utility IT, operations stakeholders |

## Production Readiness Gaps

Known gaps:

- No production hosting configuration.
- No production database.
- No secrets management.
- No identity provider.
- No integration adapters.
- No centralized observability.
- No release promotion workflow.
- No backup or recovery plan.
- No operational runbook.

## Operational Runbook Direction

Future runbooks should cover:

- Startup and shutdown.
- Health checks.
- Failed backend deployment.
- Failed frontend deployment.
- Database unavailable.
- Integration degraded.
- Recommendation service unavailable.
- Audit write failure.
- POC demo recovery.

## Documentation Operations

Major implementation changes should update:

- `README.md`.
- Relevant `docs/` files.
- `002_Documentation_Roadmap.md`.
- `001_Decision_Log.md` when decisions change.
- `004_POC_Feedback_Log.md` when feedback is converted or closed.

## Related Documents

- [Deployment Architecture](../200_Architecture/206_Deployment_Architecture.md)
- [Observability](804_Observability.md)
- [Business Continuity](806_Business_Continuity.md)

