# Explainability and Trust

## Purpose

This document defines how the AI Dispatch Advisor should build user trust through explainable recommendations, transparent data context, clear safety boundaries, and auditable user control.

## Trust Model

Dispatchers and supervisors will trust the system when it:

- Shows what it recommends.
- Explains why it recommends it.
- Shows what data was used.
- Shows what constraints or uncertainty apply.
- Lets the user control the final decision.
- Records user decisions without excessive burden.
- Handles stale or missing data honestly.

## Current Implementation State

The current POC recommendation panel displays:

- Recommendation action.
- Recommended crew.
- Confidence.
- Expected impact.
- Factors.
- Constraints.

This is an appropriate first explainability baseline. It should evolve toward more structured and auditable explanations.

## Explanation Content Model

Each material recommendation should include:

| Explanation Element | Purpose |
| --- | --- |
| Primary factors | Shows what drove the recommendation |
| Constraints | Shows what limited the options |
| Assumptions | Shows what the system assumed |
| Data inputs | Shows which source data was considered |
| Data freshness | Shows whether data may be stale |
| Confidence | Summarizes recommendation strength |
| Alternatives | Shows that other options were considered |
| Expected impact | Connects recommendation to operational value |

## Explanation Examples

Examples of useful explanation factors:

- Crew is available.
- Crew capability matches required work.
- Estimated travel time is lower than alternatives.
- Incident affects a critical facility.
- Incident has high customer impact.
- Hazard requires line crew response.
- Weather conditions increase restoration risk.

Examples of useful constraints:

- Human dispatcher approval required.
- Crew location may be stale.
- Required equipment unavailable.
- Road access limited.
- Source data missing or delayed.
- SCADA state not available.

## Confidence Guidelines

Confidence should reflect:

- Data completeness.
- Data freshness.
- Crew suitability.
- Incident severity.
- Constraint clarity.
- Alternative quality.
- Source system health.

Confidence should not imply:

- Guaranteed restoration time.
- Guaranteed crew availability.
- Autonomous operational authority.
- Regulatory approval.

## Data Transparency

The UX should disclose data limitations when they matter.

Data transparency indicators may include:

- Last updated timestamp.
- Source system name.
- Integration health.
- Missing data warning.
- Stale data label.
- Conflicting source values.

The current POC uses synthetic data and a scenario label. Future iterations should add source metadata to API responses.

## Human Control

Human control is central to trust. The UI must make clear that:

- Recommendations are advisory.
- Dispatchers can accept, modify, defer, or override.
- Overrides are expected and supported.
- User rationale is captured for review.
- Copilot responses cannot execute actions.

## Trust Risks

| Risk | UX Mitigation |
| --- | --- |
| User sees recommendation as a black box | Show factors, constraints, confidence, and alternatives |
| User assumes AI has authority | Label recommendations as advisory and require user action |
| User distrusts stale data | Show freshness and source warnings |
| User cannot correct the system | Provide modify and override workflows |
| User is overloaded by explanation detail | Show concise summary first, then progressive detail |
| User cannot reconstruct decisions later | Record audit events and recent action history |

## Progressive Disclosure

Recommendation explanations should use layered detail:

1. Summary: recommended action, crew, confidence.
2. Operational reason: expected impact and top factors.
3. Detail: constraints, assumptions, alternatives, source data.
4. Audit: recommendation version, user action, timestamp.

This prevents the console from overwhelming dispatchers while preserving reviewability.

## Copilot Trust Boundary

The AI Copilot should:

- Explain current data and recommendations.
- Summarize priority context.
- Clarify factors and constraints.
- Refer to visible system data.

The AI Copilot should not:

- Dispatch crews.
- Accept or override recommendations.
- Hide uncertainty.
- Present unverifiable conclusions as facts.

## Production Trust Requirements

Before production use, the system should add:

- Durable recommendation history.
- Audit event model.
- Source data provenance.
- Data freshness metadata.
- Role-based access.
- Recommendation versioning.
- Model or algorithm version tracking.
- Post-event review capabilities.

## Related Documents

- [Recommendation Experience](303_Recommendation_Experience.md)
- [Dispatch Console Specification](302_Dispatch_Console_Specification.md)
- [Accessibility Guidelines](305_Accessibility_Guidelines.md)

