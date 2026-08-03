# Business Continuity

## Purpose

This document defines business continuity considerations for the AI Dispatch Advisor. It describes continuity goals, current POC limitations, target resilience practices, degraded operation, backup and recovery, and operational expectations for utility outage dispatch contexts.

## Current Implementation State

The current POC is a local development and demo system. It does not include production business continuity controls.

Current limitations:

- No production deployment.
- No high availability.
- No production database.
- No backup or restore process.
- No disaster recovery plan.
- No integration failover.
- No formal operational support model.

## Business Continuity Goals

The target system should:

- Remain useful during degraded data conditions.
- Fail safely when recommendation services are unavailable.
- Preserve audit and recommendation history.
- Avoid blocking utility operations when unavailable.
- Clearly indicate degraded integration states.
- Support recovery from service, database, and integration failures.

## Operational Role During Outages

The AI Dispatch Advisor is a decision-support layer. Existing utility systems and procedures remain authoritative.

If AI Dispatch Advisor is unavailable:

- Dispatch operations should continue through established OMS, crew, and control room procedures.
- The system should not become a single point of failure for outage response.
- Recovery should preserve audit and recommendation history when possible.

## Degraded Operation Modes

Potential degraded modes:

| Degraded Mode | Expected Behavior |
| --- | --- |
| Backend unavailable | Frontend shows service unavailable state |
| Recommendation unavailable | UI shows incident data but no recommendation |
| OMS unavailable | Use last known data only if policy permits and label stale |
| GIS unavailable | Continue without map/topology context |
| Crew data stale | Lower confidence and require user review |
| Weather feed unavailable | Remove weather-dependent claims |
| Audit store unavailable | Block or queue audited actions depending on policy |

## Data Recovery

Production recovery should cover:

- Application database.
- Audit event store.
- Recommendation history.
- Configuration.
- Scenario definitions.
- Integration state or cache where relevant.

Backup requirements should be defined with platform, security, compliance, and operations stakeholders.

## Recovery Objectives

Target recovery objectives must be defined later:

- Recovery Time Objective.
- Recovery Point Objective.
- Maximum acceptable integration staleness.
- Maximum acceptable audit event delay.
- Manual fallback procedures.

The POC does not define formal RTO or RPO.

## Continuity for Recommendations

If recommendation generation fails:

- Users should still see incident and crew data if available.
- UI should clearly show that recommendations are unavailable.
- Users should continue established manual dispatch processes.
- Failures should be logged and observable.

Recommendation service failure should not create unsafe or hidden dispatch behavior.

## Continuity for Audit

Audit continuity is critical. Production design should decide:

- Whether to block recommendation actions when audit persistence fails.
- Whether to queue audit events locally.
- How to reconcile queued events.
- How to alert operations on audit failures.

For high-accountability dispatch decisions, blocking unaudited write actions may be appropriate.

## Continuity for Integrations

Integration continuity should include:

- Health status.
- Last successful sync.
- Stale data labeling.
- Retry behavior.
- Manual refresh.
- Source-system fallback procedures.

Do not silently treat stale data as current.

## POC-to-Enterprise Transition

| POC | Enterprise Direction |
| --- | --- |
| Local process | Managed deployment |
| Synthetic files | Integrated source data and persistence |
| No backup | Database and audit backup process |
| No HA | Resilient service architecture |
| No degraded state model | Explicit degraded operation modes |
| No DR plan | Tested recovery procedures |

## Open Questions

- What availability expectation applies to a decision-support layer?
- Should audited actions be blocked if audit persistence fails?
- What RTO and RPO are required?
- Which source systems have established fallback procedures?
- What storm-mode continuity requirements apply?

## Related Documents

- [Security Architecture](801_Security_Architecture.md)
- [Observability](804_Observability.md)
- [Deployment and Operations](805_Deployment_and_Operations.md)
- [Deployment Architecture](../200_Architecture/206_Deployment_Architecture.md)

