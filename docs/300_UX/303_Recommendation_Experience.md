# Recommendation Experience

## Purpose

This document defines how AI-assisted dispatch recommendations should be presented, reviewed, acted on, and audited in the AI Dispatch Advisor user experience.

## Recommendation UX Principles

The recommendation experience must follow these principles:

- The system recommends; the human decides.
- Recommendations must be specific enough to support action.
- Explanations must be visible and operationally meaningful.
- Confidence must not be presented as certainty.
- Users must be able to accept, modify, defer, or override.
- Overrides are normal operational behavior, not errors.
- Recommendation actions must be auditable.

## Current Implementation State

The current POC shows:

- Recommended action.
- Recommended crew.
- Confidence.
- Expected impact.
- Explanation factors.
- Constraints.
- Placeholder action buttons.

The next POC feature should make Accept, Modify, Defer, and Override demo-functional.

## Recommendation Object

The user experience should assume each recommendation has:

- Recommendation identifier.
- Incident identifier.
- Recommended action.
- Recommended crew or resource.
- Confidence.
- Expected impact.
- Explanation factors.
- Constraints.
- Alternatives.
- Source data context.
- Timestamp.
- Algorithm or model version, when available.

The current backend returns a subset of this structure.

## Recommendation States

Recommended UI states:

| State | Meaning |
| --- | --- |
| New | Recommendation generated and not yet reviewed |
| Viewed | User has opened or selected the recommendation |
| Accepted | User approved the recommendation |
| Modified | User changed part of the recommendation before approval |
| Deferred | User postponed action |
| Overridden | User rejected the recommendation |
| Superseded | A newer recommendation replaced the prior one |
| Failed | Recommendation could not be generated or saved |

## Action UX

### Accept

Purpose:

- Approve the recommendation as presented.

Expected behavior:

- Record accepted status.
- Show confirmation.
- Add event to recent activity or audit history.
- Preserve recommendation context.

### Modify

Purpose:

- Allow the user to adjust the recommendation while preserving the original suggestion.

Expected behavior:

- Show a simple note or modification input.
- Record modified status.
- Capture the original recommendation and user note.
- Show confirmation.

POC scope:

- A text note is sufficient.

### Defer

Purpose:

- Indicate that the recommendation should be reviewed later or held pending additional context.

Expected behavior:

- Record deferred status.
- Optionally capture deferral reason.
- Keep incident visible as requiring follow-up.

### Override

Purpose:

- Reject the recommendation based on user judgment or external context.

Expected behavior:

- Require an override reason.
- Allow optional note.
- Record overridden status.
- Preserve original recommendation, selected reason, user note, and timestamp.

Recommended override reasons:

- Field condition.
- Safety concern.
- Crew constraint.
- Supervisor direction.
- Stale or missing data.
- Critical customer priority.
- Other operational reason.

## Recommendation Panel Layout

Recommended order:

1. Selected incident context.
2. Recommended action.
3. Recommended crew or resource.
4. Confidence and expected impact.
5. Explanation factors.
6. Constraints and assumptions.
7. Alternatives.
8. Action controls.
9. Recent action history.

## Alternatives

When alternatives exist, the UI should show:

- Alternative crew.
- Suitability score or qualitative ranking.
- Travel time.
- Capability match.
- Tradeoff.

Alternatives should be concise. The primary recommendation should remain visually distinct.

## Confidence Presentation

Confidence should be shown as a decision-support indicator, not a guarantee.

Recommended labels:

- High.
- Medium.
- Low.
- Insufficient data.

Confidence should be accompanied by factors or constraints that explain why confidence is high or low.

## Audit UX

Recommendation action history should show:

- Action type.
- Incident.
- Crew.
- Timestamp.
- User identity when authentication exists.
- Reason or note.
- Recommendation version.

POC scope:

- A recent actions panel with local demo events is sufficient.

Production scope:

- Durable audit events with queryable history.

## Copilot Relationship

The AI Copilot may explain a recommendation but should not be the primary action surface.

Copilot may answer:

- Why was this crew recommended?
- What constraints affected the recommendation?
- What should I focus on first?
- Which critical facilities are affected?

Copilot should not:

- Accept recommendations.
- Override recommendations.
- Dispatch crews.
- Write to systems of record.

## Failure States

Recommendation UX should account for:

- No recommendation available.
- No suitable crew.
- Data stale or missing.
- Backend unavailable.
- User lacks permission.
- Action save failed.
- Recommendation superseded.

Failure states should be clear and operational, not technical stack traces.

## Related Documents

- [Dispatch Console Specification](302_Dispatch_Console_Specification.md)
- [Explainability and Trust](304_Explainability_and_Trust.md)
- [Accessibility Guidelines](305_Accessibility_Guidelines.md)

