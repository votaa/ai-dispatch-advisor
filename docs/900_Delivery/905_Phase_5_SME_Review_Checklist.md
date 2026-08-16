# Phase 5 SME Review Checklist

This checklist is the review evidence package for closing Phase 5. It records the deterministic recommendation behavior, constraint assumptions, and explainability evidence that a dispatch SME can review before pilot planning.

## Scenario coverage

| Scenario | Expected review evidence | Result | SME notes |
| --- | --- | --- | --- |
| `base` | Top incident, selected crew, suitability score, alternatives, explanation factors | Pending review | |
| `storm` | Storm-priority incident, capability-feasible crew, excluded assigned crews | Pending review | |
| `crew-shortage` | `Defer and escalate`, low confidence, failed constraints, excluded candidates | Pending review | |
| `critical-facility` | Critical-facility priority and human-approval boundary | Pending review | |
| `august-storm-preview` | Generated-data invariant checks and explainable recommendation | Pending review | |

## Edge-case evidence

- [x] No feasible crew produces `Defer and escalate` and low confidence.
- [x] Capability mismatch is reported as a blocking exclusion reason.
- [x] Insufficient shift time is reported as a blocking exclusion reason.
- [x] Missing travel estimates generate a data-quality warning and can make a crew infeasible.
- [x] Active assignments are excluded from recommendations and alternatives.
- [x] Incident and crew tie-break behavior is deterministic.
- [x] Existing flat recommendation fields remain compatible with current clients.
- [x] Nested explanation includes factors, constraints, assumptions, exclusions, warnings, and policy metadata.

## Review boundaries

- Recommendations remain advisory; dispatch approval is required.
- Shift sufficiency currently covers estimated travel only because repair duration is not in the scenario contract.
- OR-Tools or another advanced solver is deferred until multi-incident requirements and operational inputs exist.
- Crew IDs are now visible beside descriptive crew names on Crew Board and recommendation surfaces. This later Phase 6 usability change does not alter the Phase 5 recommendation evidence under review.

## SME review record

Reviewer: ____________________  Date: ____________________

Disposition: `Accepted` / `Accepted with follow-up` / `Needs changes`

Follow-up items: ____________________________________________________________
