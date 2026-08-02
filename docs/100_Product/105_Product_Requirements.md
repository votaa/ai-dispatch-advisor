# Product Requirements

## Purpose

This document defines the initial product requirements for the AI Dispatch Advisor. These requirements are intended to guide implementation of the Developer Bootstrap MVP and provide a foundation for future detailed architecture, API, frontend, data, and AI documentation.

## Requirement Status Definitions

| Status | Meaning |
| --- | --- |
| MVP | Required for the Developer Bootstrap MVP or first runnable shell |
| Planned | Expected after the MVP foundation is established |
| Future | Valuable but not required for early implementation |
| Deferred | Explicitly not included until a later decision |

## Product Scope Summary

The AI Dispatch Advisor will provide an enterprise dispatch decision-support experience for electric utility outage management. It will present active outage context, crew context, AI-assisted recommendations, explainability, scenario comparison, and audit-oriented user actions.

## Functional Requirements

### PR-001: Operational Dashboard

Status: MVP

The system shall provide a dashboard summarizing active outage operations.

The dashboard should include:

- Total active incidents.
- Customers currently affected.
- Available and assigned crews.
- High-priority incidents.
- Critical facility impacts.
- Recommendation status.
- Data freshness or integration health indicators.

### PR-002: Dispatch Queue

Status: MVP

The system shall provide a dispatch queue showing active incidents requiring review or action.

The dispatch queue should support:

- Sorting by priority, customer impact, age, region, and recommendation status.
- Filtering by region, incident type, severity, assigned status, and critical facility impact.
- Visual indication of recommended next action.
- Selection of an incident for detailed review.

### PR-003: Incident Detail View

Status: MVP

The system shall provide an incident detail view with operational context.

Incident detail should include:

- Incident identifier and current status.
- Location and affected area.
- Customer impact.
- Critical facility impact.
- Estimated restoration information when available.
- Related asset or circuit context.
- Weather or hazard context when available.
- Current assignment status.
- Recommendation summary.

### PR-004: Crew Board

Status: MVP

The system shall provide a crew board showing crew availability and assignment context.

The crew board should include:

- Crew identifier and name.
- Crew type or capability.
- Availability status.
- Current assignment.
- Approximate location or operating area.
- Shift or readiness indicator.
- Suitability for selected incidents when applicable.

### PR-005: Dispatch Recommendation

Status: MVP

The system shall generate or display AI-assisted dispatch recommendations for selected incidents.

Recommendations should include:

- Recommended action.
- Recommended crew or work package when applicable.
- Priority rationale.
- Expected operational impact.
- Key constraints.
- Confidence indicator.
- Alternatives when available.

### PR-006: Recommendation Explainability

Status: MVP

The system shall provide structured explanation for each material recommendation.

Explanation should include:

- Primary factors that influenced the recommendation.
- Constraints that limited available options.
- Data inputs used.
- Data freshness or uncertainty indicators.
- Expected tradeoffs.

### PR-007: Human Review Actions

Status: MVP

The system shall allow authorized users to review recommendations and choose an action.

Supported actions should include:

- Accept.
- Modify.
- Defer.
- Override.

### PR-008: Override Reason Capture

Status: MVP

The system shall capture a reason when a user modifies or overrides a recommendation.

Initial reason categories should include:

- Field condition.
- Safety concern.
- Crew constraint.
- Supervisor direction.
- Stale or missing data.
- Customer or critical facility priority.
- Other operational reason.

### PR-009: Scenario Comparison

Status: Planned

The system shall support comparison of dispatch or restoration scenarios.

Scenario comparison should include:

- Alternative crew assignments.
- Alternative prioritization orders.
- Customer impact comparison.
- Critical facility impact comparison.
- Travel and crew utilization implications.
- Recommendation rationale differences.

### PR-010: Storm Mode View

Status: MVP

The system shall provide a storm mode view for high-volume outage conditions.

Storm mode should include:

- Regional outage summary.
- Customers out by region or operating area.
- Critical facilities affected.
- Crew availability and staging summary.
- High-priority exceptions.
- Restoration risk indicators.

### PR-011: AI Copilot Experience

Status: MVP

The system shall provide an initial AI copilot experience for operational assistance using sample data.

The initial copilot should support:

- Asking about current incident status.
- Summarizing recommendation rationale.
- Explaining why a crew was recommended.
- Identifying high-priority incidents.
- Providing non-authoritative operational summaries.

The copilot shall not directly execute dispatch actions.

### PR-012: Audit Trail

Status: Planned

The system shall record recommendation generation, user review actions, acceptance, modifications, overrides, and relevant data context.

Audit events should include:

- Timestamp.
- User or system actor.
- Event type.
- Related incident, crew, or recommendation.
- Original recommendation when applicable.
- User-selected action.
- Override reason when applicable.
- Source data context when available.

### PR-013: Sample Utility Data

Status: MVP

The system shall include realistic sample data for local development and demonstration.

Sample data should include:

- Incidents.
- Crews.
- Assignments.
- Historical repairs.
- Weather.
- Critical facilities.
- Network or topology sample data.

### PR-014: Local Database Foundation

Status: MVP

The system shall include an initial local database foundation suitable for development.

The database foundation should include:

- SQLite database for local development.
- Schema definition.
- Seed data.
- Repeatable initialization script.

### PR-015: API Access to Core Data

Status: MVP

The backend shall provide API endpoints for core application data.

Initial endpoint groups should include:

- Incidents.
- Crews.
- Assignments.
- Dashboard metrics.
- Optimization or recommendation request.
- AI copilot request.

### PR-016: Integration Readiness

Status: Planned

The system shall be designed so source-system integrations can be added through adapters.

Initial integration domains should include:

- OMS.
- GIS.
- SCADA.
- Crew or workforce management.
- Weather or external event data.

### PR-017: Role-Based Experience

Status: Planned

The system shall support role-aware access and user experience differences.

Initial roles should include:

- Dispatcher.
- Supervisor.
- Analyst.
- Administrator.
- Read-only reviewer.

### PR-018: Data Quality and Freshness Indicators

Status: Planned

The system shall show data freshness, source status, or quality warnings when they affect recommendation confidence or user decisions.

### PR-019: Post-Event Review

Status: Future

The system should support review of historical recommendations, user actions, overrides, outcomes, and performance metrics.

### PR-020: Production Utility Integration

Status: Deferred

The system shall not assume direct production integration with any specific utility system until implementation environment details, security requirements, and source-system contracts are defined.

## MVP Product Boundary

The Developer Bootstrap MVP should demonstrate the product shape without requiring production integrations.

The MVP should include:

- Runnable frontend shell.
- Runnable backend API.
- Sample operational data.
- Local database.
- Dashboard, dispatch, incident, crew, storm, scenario, and copilot pages.
- Basic recommendation and explanation sample behavior.
- Developer setup documentation.

The MVP does not need to include:

- Production authentication.
- Real OMS, GIS, SCADA, or crew system integration.
- Production AI model deployment.
- Fully accurate optimization.
- Regulatory reporting.
- Real-time grid control.

## Acceptance Criteria for Developer Bootstrap MVP

The MVP should be considered acceptable when:

- A developer can run the frontend locally.
- A developer can run the backend locally.
- The frontend can retrieve sample data from backend endpoints.
- Core pages render with realistic utility outage data.
- A sample recommendation can be displayed with explanation.
- User review actions can be represented in the interface.
- Repository setup instructions are clear.
- Basic automated checks are available or documented.

## Related Documents

- [Project Charter](101_Project_Charter.md)
- [Product Vision](102_Product_Vision.md)
- [Stakeholders and Personas](103_Stakeholders_and_Personas.md)
- [User Workflows](104_User_Workflows.md)
- [Non-Functional Requirements](106_Non_Functional_Requirements.md)

