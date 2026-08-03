# Observability

## Purpose

This document defines observability requirements for the AI Dispatch Advisor. It describes logging, metrics, tracing, health checks, integration visibility, and operational diagnostics needed to support enterprise utility environments.

## Current Implementation State

The current POC includes:

- FastAPI health endpoint at `GET /health`.
- Local server logs from Uvicorn.
- GitHub Actions CI checks.
- No centralized logging.
- No metrics.
- No tracing.
- No integration health dashboard.

## Observability Goals

Observability should help teams answer:

- Is the frontend available?
- Is the backend healthy?
- Are integrations healthy?
- Are recommendations being generated successfully?
- Are user actions being recorded?
- Are errors increasing?
- Is source data stale?
- Are AI or optimization services behaving as expected?

## Health Checks

Current:

```text
GET /health
```

Target health checks:

- Backend process health.
- Database connectivity.
- Integration adapter health.
- Recommendation service health.
- AI service health when introduced.
- Scenario data availability in non-production.

Health endpoints should avoid leaking sensitive configuration details.

## Logging

Target logs should be structured and include:

- Timestamp.
- Log level.
- Service name.
- Environment.
- Correlation ID.
- User or service actor when available.
- Route or operation.
- Result.
- Error code when applicable.

Logs should not include:

- Credentials.
- Tokens.
- Sensitive customer data.
- Excessive crew location detail.
- Raw source-system payloads unless explicitly controlled.

## Metrics

Recommended metrics:

### API Metrics

- Request count.
- Request latency.
- Error rate.
- Endpoint usage.

### Recommendation Metrics

- Recommendations generated.
- Recommendation generation latency.
- Recommendation failures.
- Acceptance rate.
- Override rate.
- Deferral rate.

### Integration Metrics

- Last successful sync.
- Source data staleness.
- Adapter error rate.
- Writeback success and failure count.

### Frontend Metrics

- Page load failures.
- API request failures.
- Client-side errors.

## Tracing

Distributed tracing should eventually connect:

- Frontend request.
- Backend API request.
- Recommendation service call.
- Database query.
- Integration adapter call.
- Audit event creation.

Correlation identifiers should be included in logs and error responses.

## Integration Observability

Integration health should show:

- System name.
- Status.
- Last success timestamp.
- Last failure timestamp.
- Staleness.
- Error summary.
- Degraded state reason.

This is especially important for OMS, GIS, SCADA, crew, and weather integrations.

## Alerting

Potential alerts:

- Backend unavailable.
- Database unavailable.
- Integration unavailable.
- Source data stale beyond threshold.
- Recommendation service failing.
- Audit write failures.
- Error rate threshold exceeded.
- Unauthorized action attempts increasing.

Alert thresholds should be tuned for routine and storm operations.

## POC-to-Enterprise Transition

| POC | Enterprise Direction |
| --- | --- |
| Uvicorn console logs | Structured centralized logs |
| Basic `/health` | Component health checks |
| No metrics | API, recommendation, integration, audit metrics |
| No tracing | Request correlation and distributed tracing |
| No integration health | Integration health dashboard and alerts |

## Related Documents

- [Security Architecture](801_Security_Architecture.md)
- [Audit Logging](803_Audit_Logging.md)
- [Deployment and Operations](805_Deployment_and_Operations.md)
- [Integration API](../400_Backend_API/406_Integration_API.md)

