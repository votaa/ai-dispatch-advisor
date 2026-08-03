# Audit Logging

## Purpose

This document defines audit logging requirements for the AI Dispatch Advisor. It describes what should be recorded, why auditability matters, current POC gaps, event types, retention considerations, and target implementation direction.

## Current Implementation State

The current POC does not include durable audit logging. Recommendation actions are not yet persisted unless implemented by a later POC enhancement.

The repository includes an initial SQLite schema concept for recommendation audit events, but the active backend currently reads data from CSV files.

## Audit Goals

Audit logging should:

- Preserve traceability of recommendations.
- Record user review actions.
- Capture override and modification rationale.
- Support post-event review.
- Support compliance and security investigations.
- Support recommendation quality improvement.
- Support source-system writeback traceability.

## Events to Audit

### Recommendation Events

- Recommendation generated.
- Recommendation viewed.
- Recommendation superseded.
- Recommendation expired.
- Recommendation failed.

### User Action Events

- Recommendation accepted.
- Recommendation modified.
- Recommendation deferred.
- Recommendation overridden.
- Override reason submitted.
- Assignment action confirmed.

### Integration Events

- Source data loaded.
- Integration health changed.
- Writeback attempted.
- Writeback succeeded.
- Writeback failed.
- Source data stale or unavailable.

### Security Events

- User login.
- User logout.
- Authorization denied.
- Role or permission changed.
- Administrative configuration changed.

## Target Audit Event Model

Recommended fields:

| Field | Description |
| --- | --- |
| `event_id` | Unique audit event identifier |
| `event_type` | Type of audited event |
| `actor_type` | User, service, system |
| `actor_id` | User or service identifier |
| `actor_role` | Role at time of event |
| `entity_type` | Incident, recommendation, crew, integration, config |
| `entity_id` | Related entity identifier |
| `timestamp` | Event timestamp |
| `correlation_id` | Request or trace correlation identifier |
| `payload` | Structured event details |
| `source_system` | Source system when applicable |
| `result` | Success, failure, denied, degraded |

## Recommendation Action Audit Payload

Example:

```json
{
  "event_type": "recommendation_overridden",
  "incident_id": "INC-1001",
  "recommendation_id": "REC-0001",
  "crew_id": "CR-01",
  "reason": "Field condition",
  "note": "Access road blocked by flooding.",
  "original_recommendation": {
    "recommended_action": "Assign crew",
    "confidence": "high"
  }
}
```

## Audit Storage

POC options:

- In-memory event list.
- Local JSON file.
- SQLite table.

Production direction:

- Durable database-backed audit table.
- Immutable or append-only event model where feasible.
- Export or integration to enterprise logging/SIEM where required.

## Audit Visibility

The UI should eventually provide:

- Recent recommendation actions.
- Incident-specific action history.
- Recommendation-specific history.
- Analyst or supervisor audit view.
- Export support when authorized.

Not every audit event should be visible to every user.

## Retention

Retention requirements should be defined with:

- Utility compliance.
- Legal.
- Cybersecurity.
- Records management.
- Operations leadership.

Retention may differ for:

- Security logs.
- Dispatch decision records.
- Recommendation history.
- Integration diagnostics.
- AI model evaluation records.

## Privacy and Security

Audit logs should not store unnecessary sensitive data. They should avoid:

- Raw credentials.
- Full tokens.
- Sensitive personal details.
- Excessive customer data.
- Unredacted integration payloads.

Audit payloads should be structured and reviewable.

## Current Gaps

Known gaps:

- No durable audit store.
- No authenticated user identity.
- No recommendation action persistence.
- No correlation identifiers.
- No audit UI.
- No retention policy.
- No SIEM integration.

## Related Documents

- [Security Architecture](801_Security_Architecture.md)
- [Identity and Access Management](802_Identity_and_Access_Management.md)
- [Observability](804_Observability.md)
- [Recommendation API](../400_Backend_API/405_Recommendation_API.md)

