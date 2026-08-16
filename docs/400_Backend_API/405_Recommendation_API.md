# Recommendation API

## Purpose

This document defines the recommendation API design for the AI Dispatch Advisor. It covers the current POC recommendation endpoint and the target API direction for explainable dispatch recommendations, user actions, audit events, and Copilot advisory behavior.

## Current Implementation State

Current endpoints:

```text
POST /api/optimize
POST /api/chat
```

The current recommendation implementation:

- Selects an incident.
- Ranks available crews using deterministic sample logic.
- Returns a recommended crew.
- Includes confidence, expected impact, explanation factors, constraints, and alternatives.
- Runs through the `OptimizationEngine` boundary using active policy `incident-priority-v1` and algorithm `deterministic-scoring-v2`.

Phase 5.2 makes incident-priority contributions and domain tie-breakers structured and configurable inside the engine. Public response fields and canonical scenario recommendations remain unchanged. Algorithm and policy versions currently live in the internal policy contract; Phase 5.4 will expose traceability and richer structured explanation fields through the API.

Phase 5.3 evaluates crew availability, active assignments, required capability, and travel-within-shift feasibility before scoring. Infeasible crews are omitted from `recommended_crew` and `alternatives`; their typed exclusion reasons remain an internal engine result until the Phase 5.4 public explanation contract.

Phase 5.4 exposes those results through an optional nested `explanation` object. It includes confidence rationale, structured scoring factors, satisfied or failed constraints, excluded candidates, assumptions, data-quality warnings, and algorithm/policy versions. Existing flat `factors`, `constraints`, and `confidence` fields remain unchanged for existing clients.

The current Copilot implementation:

- Uses keyword-based logic.
- Returns advisory demo responses.
- Does not call a real AI model.
- Does not execute dispatch actions.

## POST /api/optimize

### Purpose

Generates or retrieves a dispatch recommendation for a selected incident.

### Current Request Shape

```json
{
  "incident_id": "INC-1001"
}
```

`incident_id` is optional in the current POC. When omitted, the backend recommends against the highest-ranked incident.

### Current Response Shape

```json
{
  "incident_id": "INC-1001",
  "recommended_action": "Assign crew",
  "recommended_crew": {
    "crew_id": "CR-01",
    "crew_name": "North Line Alpha",
    "home_region": "North",
    "status": "available",
    "capability": "line",
    "current_location": "Millbrook Service Center",
    "shift_remaining_hours": 6,
    "storm_ready": true,
    "travel_minutes_to_selected_incident": 18,
    "suitability_score": 132,
    "capability_match": true,
    "estimated_travel_minutes": 18
  },
  "confidence": "high",
  "expected_impact": "Prioritizes 2840 affected customers with 18 minute estimated travel.",
  "factors": [
    "Crew is available",
    "Crew capability matches required work"
  ],
  "constraints": [
    "Human dispatcher approval required"
  ],
  "alternatives": []
}
```

## Target Recommendation Model

Future recommendation responses should include:

- `recommendation_id`.
- `incident_id`.
- `generated_at`.
- `recommended_action`.
- `recommended_crew_id`.
- `confidence`.
- `expected_impact`.
- `factors`.
- `constraints`.
- `assumptions`.
- `alternatives`.
- `source_data_snapshot_id`.
- `algorithm_version`.
- `model_version`, when AI model output is used.
- `expires_at` or freshness indicator.

## Recommendation Actions

The current POC implements these demo-functional actions:

| Action | Current API Behavior |
| --- | --- |
| Accept | Record recommendation as accepted |
| Modify | Record modification note and action |
| Defer | Require a reason and record deferred status |
| Override | Require override reason and record overridden status |

Current endpoints:

```text
POST /api/recommendation-actions
GET  /api/audit/events
```

Current request shape:

```json
{
  "action": "overridden",
  "incident_id": "INC-1001",
  "reason": "Field condition",
  "recommendation": {
    "recommendation_id": "REC-INC-1001-CR-01",
    "incident_id": "INC-1001",
    "recommended_action": "Assign crew"
  }
}
```

Current response shape includes:

```json
{
  "event_id": "EVT-0001",
  "scenario_id": "base",
  "recommendation_id": "REC-0001",
  "incident_id": "INC-1001",
  "crew_id": "CR-01",
  "action": "overridden",
  "reason": "Access road is blocked by flooding.",
  "note": "Access road is blocked by flooding.",
  "created_at": "2026-08-02T14:30:00-04:00"
}
```

The current POC stores recommendation decisions and accepted demo assignments in local SQLite, scoped by `scenario_id`. Existing pre-migration records are assigned to the `base` scenario. Production must use durable audit persistence with enterprise identity, retention, and access controls.

## POST /api/chat

### Purpose

Returns advisory Copilot text based on operational demo context.

### Current Request Shape

```json
{
  "message": "What should I focus on first?",
  "incident_id": "INC-1001"
}
```

### Current Response Shape

```json
{
  "answer": "Focus first on INC-1001 in Millbrook...",
  "intent": "priority_focus",
  "source": "synthetic-demo-data",
  "safety_note": "This copilot response is advisory and does not execute dispatch actions."
}
```

## Copilot Safety Boundary

The Copilot API should:

- Answer advisory questions.
- Explain recommendations.
- Summarize current operational data.
- Identify relevant source context.

The Copilot API should not:

- Execute dispatch actions.
- Accept recommendations.
- Override recommendations.
- Write to source systems.
- Bypass role-based authorization.

## Recommendation Error Cases

Expected target error cases:

| Case | Status |
| --- | --- |
| Incident not found | `404` |
| No suitable crew | `200` with defer or supervisor-review recommendation, or explicit domain status |
| Invalid action | `422` |
| Override without reason | `422` |
| Recommendation expired | `409 Conflict` |
| Unauthorized action | `401` |
| Forbidden action | `403` |
| Recommendation service unavailable | `503` |

## Audit Requirements

Recommendation APIs must eventually produce durable audit records for:

- Recommendation generated.
- Recommendation viewed.
- Recommendation accepted.
- Recommendation modified.
- Recommendation deferred.
- Recommendation overridden.
- Copilot answer generated, when audit policy requires it.

## Testing Requirements

Tests should cover:

- Recommendation returned for a valid incident.
- Recommendation returned for omitted incident.
- `404` for missing incident.
- No-crew case.
- Action recording once implemented.
- Override reason validation once implemented.
- Copilot intent responses.

## Related Documents

- [API Overview](402_API_Overview.md)
- [Outage API](403_Outage_API.md)
- [Crew API](404_Crew_API.md)
- [Integration API](406_Integration_API.md)
