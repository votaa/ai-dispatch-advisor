# Stakeholders and Personas

## Purpose

This document identifies the stakeholders and representative user personas for the AI Dispatch Advisor. It is intended to guide product requirements, workflow design, user experience decisions, security role design, and implementation priorities.

## Stakeholder Overview

The AI Dispatch Advisor affects multiple utility functions because outage dispatch decisions involve operations, field resources, customer impact, reliability performance, public safety, technology, cybersecurity, and compliance.

| Stakeholder Group | Primary Interest |
| --- | --- |
| Distribution dispatch | Clear, fast, trustworthy dispatch recommendations |
| Dispatch supervision | Workload visibility, crew allocation, escalation control |
| Field operations | Practical assignments, safe work packaging, accurate context |
| Storm response leadership | Large-event prioritization, resource coordination, restoration progress |
| Reliability and operations analytics | Performance review, recurring constraints, outcome analysis |
| Customer operations | Customer impact awareness and restoration communication support |
| Utility IT | Maintainable architecture, integration support, platform operations |
| Cybersecurity | Access control, auditability, secure integration patterns |
| Compliance and audit | Traceable decisions and defensible operating process |
| Executive leadership | Restoration performance, operational resilience, customer and regulatory outcomes |

## Primary Personas

### Distribution Dispatcher

The distribution dispatcher is the primary day-to-day user. This persona reviews outage events, evaluates crew availability, assigns work, responds to changing field conditions, and coordinates restoration activity.

Goals:

- Understand which outage events need attention first.
- Select appropriate crews quickly.
- See relevant outage, asset, customer, and safety context in one place.
- Trust but verify AI-assisted recommendations.
- Modify or override recommendations when field knowledge requires it.
- Maintain an accurate operational record.

Pain points:

- Outage, crew, asset, and field data may be spread across multiple systems.
- Source data may be stale, incomplete, or conflicting.
- High outage volume creates prioritization pressure.
- Manual comparison of crew options can be slow.
- Recommendations are not useful unless the reasoning is visible.

System needs:

- Prioritized incident queue.
- Crew suitability indicators.
- Clear recommendation explanations.
- Fast accept, modify, defer, and override actions.
- Data freshness and source confidence indicators.
- Audit trail with minimal extra user burden.

### Dispatch Supervisor

The dispatch supervisor monitors dispatch operations across users, regions, crews, and outage categories. This persona is responsible for balancing workload, resolving escalations, and maintaining operational performance.

Goals:

- Maintain visibility into active outages and crew utilization.
- Identify bottlenecks, high-risk events, and priority conflicts.
- Review recommendation patterns and user overrides.
- Support dispatchers during high-pressure operations.
- Coordinate across operating areas and storm response roles.

Pain points:

- Workload and resource constraints may not be obvious from a single system.
- Escalation risk can be hard to detect early.
- Storm conditions can overwhelm routine dispatch views.
- Manual status aggregation is time-consuming.

System needs:

- Operational dashboard with key metrics.
- Regional and priority-based filtering.
- Crew workload and availability views.
- Recommendation history and override visibility.
- Storm mode summaries and exception views.

### Storm Response Coordinator

The storm response coordinator manages large-scale outage response involving high outage volumes, changing weather, resource constraints, mutual assistance, and executive reporting.

Goals:

- Prioritize restoration work across regions and customer impact categories.
- Coordinate internal crews, contractors, and mutual assistance resources.
- Understand restoration risk and resource gaps.
- Monitor changing weather and operational constraints.
- Support clear communication to leadership.

Pain points:

- Routine dispatch workflows may not scale to storm volume.
- Crew availability and travel logistics become more complex.
- Restoration priorities can shift quickly as new information arrives.
- Critical facilities and public safety concerns require special handling.

System needs:

- Storm mode view with aggregate situational awareness.
- Scenario comparison for resource allocation decisions.
- Critical facility and safety indicators.
- Crew staging and regional capacity visibility.
- Recommendation explanations suitable for leadership review.

### Operations Analyst

The operations analyst reviews outage response performance, recommendation quality, user actions, overrides, and restoration outcomes after events.

Goals:

- Understand how dispatch decisions affected restoration outcomes.
- Identify recurring data quality issues and operational constraints.
- Evaluate recommendation acceptance and override patterns.
- Support continuous improvement of dispatch policies and models.

Pain points:

- Historical decision context may be incomplete.
- Outcomes may be difficult to connect back to recommendations.
- Override reasons may be inconsistent or missing.
- Data lineage may be hard to reconstruct after the event.

System needs:

- Recommendation and decision history.
- Audit event search and filtering.
- Outcome and performance metrics.
- Exportable data for analysis.
- Clear source and data quality metadata.

## Secondary Personas

### Field Crew Coordinator

The field crew coordinator supports crew scheduling, readiness, staging, and assignment feasibility.

System needs:

- Crew capability and availability visibility.
- Work package context.
- Assignment status and constraints.
- Practical information about location, access, and hazards.

### Utility IT Administrator

The utility IT administrator supports system configuration, environment management, integrations, access control, and operational support.

System needs:

- Clear deployment and configuration model.
- Integration health visibility.
- Role and permission administration.
- Logs, metrics, and support diagnostics.

### Cybersecurity Reviewer

The cybersecurity reviewer evaluates whether the system meets enterprise security expectations.

System needs:

- Documented authentication and authorization model.
- Audit logging coverage.
- Data protection controls.
- Secure integration patterns.
- Environment and secret management practices.

### Compliance and Audit Reviewer

The compliance and audit reviewer evaluates decision traceability, policy alignment, and evidence retention.

System needs:

- Recommendation history.
- User action records.
- Override rationale.
- Data source references.
- Reportable audit events.

## Role Implications

The following initial roles should be considered during implementation:

| Role | Typical Users | Capabilities |
| --- | --- | --- |
| Dispatcher | Distribution dispatchers | View incidents, review recommendations, accept or modify assignments, record overrides |
| Supervisor | Dispatch supervisors, storm leads | View broader operations, manage escalations, review recommendation and override patterns |
| Analyst | Operations analysts, reliability analysts | Review historical recommendations, outcomes, and performance data |
| Administrator | IT and system administrators | Configure users, integrations, environments, and operational settings |
| Read-only Reviewer | Leadership, audit, compliance | View selected dashboards, reports, and audit information |

## Design Implications

The user experience should be optimized for operational clarity:

- Dispatchers need fast scanning and low-friction action.
- Supervisors need aggregate visibility and exception management.
- Storm users need high-volume prioritization and regional context.
- Analysts need history, filtering, and traceability.
- Administrators need configuration and health visibility without interfering with dispatch workflows.

## Related Documents

- [Project Charter](101_Project_Charter.md)
- [Product Vision](102_Product_Vision.md)
- [User Workflows](104_User_Workflows.md)
- [Product Requirements](105_Product_Requirements.md)

