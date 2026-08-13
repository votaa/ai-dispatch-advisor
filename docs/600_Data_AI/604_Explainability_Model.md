# Explainability Model

## Purpose

This document defines the explainability model for AI Dispatch Advisor recommendations. It describes the structured explanation data that should accompany recommendations and how explanations should support trust, auditability, and human-in-the-loop dispatch decisions.

## Current Implementation State

The current POC recommendation response includes:

- `confidence`.
- `expected_impact`.
- `factors`.
- `constraints`.
- `alternatives`.

The frontend displays these values in the recommendation panel. This is an appropriate first baseline, but future implementation should make explanation data more structured and auditable.

Phase 5.2 now produces typed incident-score contributions internally, including factor identifiers, raw values, configured values, calculation types, and point contributions. These internal objects establish the source evidence for Phase 5.4; they are intentionally not yet added to public recommendation responses or rendered by the frontend.

## Explainability Goals

The explainability model should:

- Help dispatchers understand why a recommendation was made.
- Expose important constraints and assumptions.
- Show what data influenced the recommendation.
- Identify stale or missing data when relevant.
- Support override and review decisions.
- Support post-event review and model governance.
- Avoid relying only on free-text narrative.

## Explanation Object

Target explanation object:

```json
{
  "recommendation_id": "REC-0001",
  "summary": "Assign North Line Alpha to INC-1001.",
  "confidence": "high",
  "confidence_rationale": "Crew capability matches required line work and travel time is shortest among available crews.",
  "factors": [],
  "constraints": [],
  "assumptions": [],
  "alternatives": [],
  "data_quality_warnings": [],
  "source_references": []
}
```

## Factor Model

Factors explain what drove the recommendation.

Target factor fields:

- `factor_type`.
- `label`.
- `description`.
- `direction`.
- `weight` or `importance`.
- `source`.

Example:

```json
{
  "factor_type": "crew_capability",
  "label": "Crew capability matches required work",
  "description": "Incident requires line crew response and CR-01 has line capability.",
  "direction": "supports",
  "importance": "high",
  "source": "crew_management"
}
```

## Constraint Model

Constraints explain limits or risks.

Target constraint fields:

- `constraint_type`.
- `label`.
- `description`.
- `severity`.
- `blocking`.
- `source`.

Example:

```json
{
  "constraint_type": "human_approval",
  "label": "Human approval required",
  "description": "The system cannot dispatch crews without dispatcher approval.",
  "severity": "required",
  "blocking": true,
  "source": "policy"
}
```

## Assumption Model

Assumptions explain what the recommendation depends on.

Examples:

- Crew status is current.
- Travel time estimate is valid.
- Incident customer count is accurate.
- Weather conditions have not changed.
- Source data is not stale.

Assumptions should be visible when they materially affect confidence.

## Alternative Model

Alternatives should show other feasible options.

Target fields:

- `alternative_id`.
- `crew_id`.
- `action`.
- `rank`.
- `tradeoff`.
- `suitability_score`.
- `estimated_travel_minutes`.
- `capability_match`.
- `reason_not_selected`.

## Data Quality Warnings

Warnings should identify data issues affecting recommendation trust.

Examples:

- Crew location stale.
- Incident location missing.
- Critical facility linkage uncertain.
- SCADA state unavailable.
- Weather feed degraded.
- Assignment conflict detected.

Warnings should lower confidence when relevant.

## Confidence Model

Recommended confidence labels:

- `high`.
- `medium`.
- `low`.
- `insufficient_data`.

Confidence should be calculated from:

- Constraint satisfaction.
- Data quality.
- Alternative strength.
- Crew suitability.
- Objective alignment.
- Source freshness.

## Explanation Presentation

The frontend should present explanation in layers:

1. Recommendation summary.
2. Confidence and expected impact.
3. Top factors.
4. Constraints and assumptions.
5. Alternatives.
6. Source data and audit details.

This supports fast dispatch workflows while preserving reviewability.

## Copilot Relationship

The Copilot may convert structured explanations into natural language, but structured explanation data should remain authoritative.

The Copilot should not invent explanation factors that are not present in the recommendation data.

## Audit Requirements

Persisted recommendations should preserve:

- Explanation factors.
- Constraints.
- Assumptions.
- Data quality warnings.
- Alternatives.
- Source references.
- Algorithm and model versions.

This allows post-event review and decision traceability.

## Related Documents

- [Data Model](601_Data_Model.md)
- [Optimization Engine](602_Optimization_Engine.md)
- [AI Recommendation Engine](603_AI_Recommendation_Engine.md)
- [Model Governance](605_Model_Governance.md)
