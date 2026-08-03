# Model Governance

## Purpose

This document defines model governance expectations for the AI Dispatch Advisor. It applies to deterministic scoring logic, optimization algorithms, AI-assisted recommendation components, and any future model-backed Copilot capabilities.

## Current Implementation State

The current POC does not include production AI models. It includes:

- Deterministic incident scoring.
- Deterministic crew recommendation logic.
- Keyword-based Copilot demo responses.
- Synthetic demo data.

Even at this early stage, governance concepts should be documented so future AI and optimization work remains traceable, testable, and controlled.

## Governance Goals

Model governance should ensure:

- Recommendations are explainable.
- Algorithm and model versions are traceable.
- Data inputs are auditable.
- Changes are reviewed and tested.
- Human approval remains required for dispatch actions.
- AI output does not bypass operational controls.
- Performance and risk can be reviewed over time.

## Governed Assets

Governance should apply to:

| Asset | Examples |
| --- | --- |
| Scoring Rules | Incident priority weights, crew suitability scoring |
| Optimization Algorithms | Assignment optimization, scenario comparison |
| AI Models | Future predictive or language models |
| Prompts | Future Copilot and explanation prompts |
| Data Features | Derived fields used by recommendations |
| Evaluation Sets | Synthetic scenarios, historical replay cases |
| Explanation Templates | Operator-facing explanation structures |

## Versioning Requirements

Each material recommendation should eventually identify:

- Algorithm version.
- Model version, if applicable.
- Prompt version, if applicable.
- Feature set version.
- Data snapshot reference.
- Configuration version.

This allows teams to determine why a recommendation was produced.

## Change Management

Changes to recommendation behavior should require:

- Description of the change.
- Rationale.
- Expected impact.
- Test evidence.
- Review by product and operations stakeholders when behavior changes materially.
- Decision log entry when the change affects system direction or operational policy.

## Evaluation Approach

Evaluation should include:

- Synthetic test scenarios.
- Edge cases.
- No-available-crew cases.
- Critical facility cases.
- Storm mode cases.
- Stale data cases.
- Dispatcher review.
- Historical replay when data becomes available.

Metrics may include:

- Recommendation acceptance rate.
- Override rate.
- Override reasons.
- Time to dispatch decision.
- Restoration outcome comparison.
- Data quality sensitivity.
- Safety or policy exception rate.

## Human-in-the-Loop Control

Governance must preserve:

- Dispatcher review.
- Supervisor oversight.
- Accept, modify, defer, and override actions.
- Override reason capture.
- Audit event creation.

The system should not autonomously dispatch crews in the initial implementation.

## AI Copilot Governance

Future Copilot model use should include:

- Prompt versioning.
- Grounded context retrieval.
- Safety boundaries.
- No direct action execution.
- Logging and audit policy.
- Response quality evaluation.
- Handling for uncertainty and missing data.

Copilot should be advisory and should not become an ungoverned operational command interface.

## Data Governance

Recommendation quality depends on data governance:

- Synthetic data must remain fictional.
- Production data sources must have clear ownership.
- Sensitive data must be minimized.
- Source data freshness must be tracked.
- Data quality warnings must be surfaced.
- Feature derivation should be documented.

## Risk Controls

| Risk | Control |
| --- | --- |
| Opaque recommendation behavior | Structured explainability and version tracking |
| Poor data quality | Source freshness and data quality warnings |
| Unreviewed scoring changes | Change review and regression tests |
| AI overreach | Human-in-the-loop boundary and action separation |
| Prompt drift | Prompt versioning and evaluation |
| Hidden bias in prioritization | Scenario evaluation and stakeholder review |
| Unsafe automation | No autonomous dispatch without explicit future decision |

## Audit and Record Retention

Persisted recommendation records should include:

- Recommendation request.
- Data snapshot reference.
- Recommendation output.
- Explanation.
- Versions.
- User action.
- Override reason.
- Outcome when available.

Retention requirements should be finalized with utility policy, legal, compliance, and security stakeholders.

## Production Readiness Checklist

Before production AI or optimization use:

- Recommendation versions are tracked.
- Data inputs are auditable.
- Explanation outputs are structured.
- Evaluation set exists.
- Regression tests exist.
- Human approval workflow is enforced.
- Audit events are durable.
- Security and compliance review is complete.
- Model or algorithm changes have review process.

## Related Documents

- [Data Model](601_Data_Model.md)
- [Optimization Engine](602_Optimization_Engine.md)
- [AI Recommendation Engine](603_AI_Recommendation_Engine.md)
- [Explainability Model](604_Explainability_Model.md)

