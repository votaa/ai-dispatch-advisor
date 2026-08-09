# Optimization Engine

## Purpose

This document defines the optimization engine direction for the AI Dispatch Advisor. It describes the current deterministic POC logic, target optimization responsibilities, inputs, outputs, constraints, objective functions, and validation expectations.

## Current Implementation State

The current POC includes deterministic recommendation logic in:

```text
backend/app/recommendations.py
```

Current behavior:

- Scores incidents using severity, customers out, critical facility impact, hazard, and age.
- Filters crews by availability.
- Scores crew suitability using capability match, demo travel time, and storm readiness.
- Returns a recommended crew and alternatives.

This is intentionally illustrative. It is not operationally validated optimization.

## Optimization Goals

The target optimization engine should:

- Prioritize outage response options.
- Match crews to incidents or work packages.
- Compare dispatch scenarios.
- Surface tradeoffs between competing objectives.
- Respect operational constraints.
- Produce structured outputs that support explanation.
- Preserve human review and approval.

## Optimization Scope

Initial optimization scope:

- Incident prioritization.
- Crew suitability ranking.
- Crew-to-incident recommendation.
- Scenario comparison.

Future scope:

- Multi-crew restoration sequencing.
- Mutual assistance resource allocation.
- Storm mode staging.
- Travel route optimization.
- Switching and topology-aware restoration planning.
- Probabilistic repair duration estimation.

## Inputs

Target inputs include:

| Input | Description |
| --- | --- |
| Incidents | Active outage events, severity, customers out, hazards, age |
| Crews | Availability, capability, location, shift status, equipment |
| Assignments | Active work and crew commitments |
| Critical Facilities | Priority customer or facility impact |
| Weather | Conditions affecting access, safety, and restoration |
| Topology | Feeder, asset, switch, and network relationships |
| Historical Repairs | Expected repair duration by type and conditions |
| Policies | Utility-specific priority rules and constraints |

## Outputs

Target outputs include:

- Recommended action.
- Recommended crew or resource.
- Ranked alternatives.
- Suitability score or qualitative ranking.
- Expected operational impact.
- Estimated travel time.
- Estimated restoration benefit.
- Constraint list.
- Confidence.
- Explanation factors.

## Objective Functions

The optimization engine may balance:

- Customer outage impact reduction.
- Critical facility restoration priority.
- Public safety and hazard response.
- Crew travel time.
- Crew capability match.
- Crew shift constraints.
- Restoration sequence efficiency.
- Regional equity or operating policy.
- Storm response strategy.

The system should avoid hiding tradeoffs. When objectives conflict, the recommendation should explain the tradeoff.

## Constraints

Target constraints include:

- Crew availability.
- Crew capability and certifications.
- Crew shift remaining.
- Required equipment.
- Safety hazards.
- Road or access restrictions.
- Weather conditions.
- Switching dependencies.
- Topology limitations.
- Critical facility priority.
- Existing assignments.
- Mutual assistance rules.

## Candidate Algorithm Progression

### Phase 1: Deterministic Scoring

Use simple weighted scoring for:

- Incident priority.
- Crew suitability.
- Recommendation ranking.

This is the current POC direction.

### Phase 2: Constraint-Aware Ranking

Add explicit constraint handling:

- Exclude infeasible crews.
- Penalize stale data.
- Penalize shift risk.
- Include travel and access constraints.

### Phase 3: Mathematical Optimization

Introduce optimization libraries when the data model supports them:

- OR-Tools for assignment and routing problems.
- NetworkX for graph and topology analysis.
- Pandas for batch scoring and scenario analysis.

### Phase 4: Scenario Simulation

Support comparison of:

- Base dispatch plan.
- Critical facility priority plan.
- Minimum travel plan.
- Storm restoration plan.
- Crew shortage plan.

## Human-in-the-Loop Boundary

The optimization engine recommends; it does not dispatch crews autonomously.

The UI and API must preserve:

- Human approval.
- Modification.
- Deferral.
- Override.
- Audit event capture.

## Explainability Requirements

The optimization engine must return structured explanation inputs:

- Top positive factors.
- Limiting constraints.
- Alternatives considered.
- Data quality warnings.
- Confidence rationale.
- Objective tradeoffs.

Do not rely only on generated natural language.

## Validation Strategy

Optimization behavior should be validated using:

- Known synthetic scenarios.
- Expected recommendation fixtures.
- Edge cases with no available crews.
- Stale data cases.
- Critical facility cases.
- Storm mode cases.
- Regression tests for scoring changes.

## Current Gaps

Known gaps:

- No formal optimization service boundary.
- No optimization library usage.
- No calibration against real operating policy.
- No persistence of recommendation inputs or outputs.
- Only four fixed synthetic validation scenarios.
- No quantitative evaluation metrics.

## Related Documents

- [Data Model](601_Data_Model.md)
- [AI Recommendation Engine](603_AI_Recommendation_Engine.md)
- [Explainability Model](604_Explainability_Model.md)
- [Model Governance](605_Model_Governance.md)
