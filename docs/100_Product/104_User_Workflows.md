# User Workflows

## Purpose

This document defines the core user workflows for the AI Dispatch Advisor. These workflows should guide the Developer Bootstrap MVP, frontend routing, backend API design, data model, and future UX documentation.

## Workflow Principles

The workflows are based on the following product principles:

- The system recommends; the human decides.
- Recommendations must be explainable before they are actionable.
- Users must be able to accept, modify, defer, or override recommendations.
- Source data freshness and uncertainty should be visible when they affect decisions.
- Routine operations and storm response require related but distinct views.
- User actions should create an audit trail without excessive manual work.

## Workflow 1: Routine Outage Triage

### Objective

Help a dispatcher evaluate active outage events and determine which incidents require attention first.

### Primary Persona

Distribution Dispatcher

### Trigger

New outage events arrive from the outage management system, customer calls, AMI events, SCADA alarms, or manual entry.

### Main Flow

1. Dispatcher opens the dashboard or dispatch console.
2. System displays active incidents with priority, customer impact, location, status, and data freshness.
3. Dispatcher filters or sorts by region, priority, critical facility impact, outage size, or age.
4. System highlights incidents with recommended next actions.
5. Dispatcher opens an incident detail view.
6. System displays relevant outage, asset, customer, weather, crew, and safety context.
7. Dispatcher reviews recommendation rationale.
8. Dispatcher selects an action: accept, modify, defer, or override.
9. System records the action and associated context.

### Expected Outputs

- Prioritized incident view.
- Incident detail context.
- Recommendation review outcome.
- Audit event for the user action.

### Exception Paths

- Source data is stale or unavailable.
- Incident lacks enough detail for a recommendation.
- Dispatcher knows field information not yet reflected in source systems.
- Incident must be escalated to a supervisor.

## Workflow 2: Crew Assignment Recommendation

### Objective

Help a dispatcher select a suitable crew for an outage or work package.

### Primary Persona

Distribution Dispatcher

### Trigger

An outage event requires field response or reassignment.

### Main Flow

1. Dispatcher opens an incident requiring crew assignment.
2. System retrieves available crews, locations, skills, status, shift constraints, and current assignments.
3. System ranks crew options based on suitability.
4. Dispatcher reviews recommended crew assignment and alternatives.
5. System explains the recommendation, including proximity, capability, travel time, customer impact, safety constraints, and expected restoration benefit.
6. Dispatcher accepts the recommended assignment or selects an alternative.
7. System records assignment decision and reason when applicable.

### Expected Outputs

- Recommended crew assignment.
- Ranked alternative crews.
- Crew suitability explanation.
- Assignment decision record.

### Exception Paths

- No suitable crew is available.
- Crew location is stale or unknown.
- Required skill or equipment data is missing.
- Crew is reassigned due to emergency priority.

## Workflow 3: Recommendation Override

### Objective

Allow a user to reject or modify a recommendation while preserving operational accountability and learning data.

### Primary Persona

Distribution Dispatcher

### Trigger

The dispatcher determines that a recommendation should not be followed.

### Main Flow

1. Dispatcher reviews a recommendation.
2. Dispatcher selects modify or override.
3. System prompts for a concise override category and optional note.
4. Dispatcher records the reason, such as field condition, crew constraint, safety concern, supervisor direction, stale data, or customer priority.
5. System applies the selected user action.
6. System records the original recommendation, user action, override reason, timestamp, user identity, and data context.

### Expected Outputs

- Modified assignment or rejected recommendation.
- Override audit event.
- Data for future recommendation quality review.

### Exception Paths

- Emergency action requires rapid override with minimal input.
- User lacks permission to complete the action.
- Source system rejects the downstream assignment update.

## Workflow 4: Supervisor Monitoring

### Objective

Help a supervisor monitor dispatch operations, identify bottlenecks, and support escalation decisions.

### Primary Persona

Dispatch Supervisor

### Trigger

Supervisor reviews operational status during routine operations or elevated outage conditions.

### Main Flow

1. Supervisor opens the operations dashboard.
2. System displays outage counts, customer impact, crew utilization, recommendation status, escalations, and aging incidents.
3. Supervisor filters by region, operating area, priority, crew status, or incident category.
4. System highlights exceptions such as critical facility impact, unassigned high-priority incidents, stale data, or constrained crews.
5. Supervisor drills into an incident, crew board, or recommendation history.
6. Supervisor takes action or directs dispatchers as needed.

### Expected Outputs

- Operational overview.
- Exception list.
- Escalation and supervision actions.
- Audit record for supervisory intervention when applicable.

### Exception Paths

- Storm mode should be activated.
- Data source degradation reduces confidence.
- Mutual assistance or contractor resources are required.

## Workflow 5: Storm Mode Coordination

### Objective

Support large-scale outage response during major weather or emergency events.

### Primary Persona

Storm Response Coordinator

### Trigger

Outage volume, weather conditions, or operational leadership activates storm response procedures.

### Main Flow

1. Storm coordinator opens storm mode.
2. System displays aggregate outages, customers out, critical facilities, regional impact, crew capacity, and restoration risk.
3. Coordinator reviews AI-assisted prioritization across regions or operating areas.
4. System provides scenario options for crew allocation and restoration sequencing.
5. Coordinator compares scenarios by customer impact, critical facility restoration, travel burden, crew utilization, and expected restoration improvement.
6. Coordinator selects or communicates preferred operating strategy.
7. System records scenario assumptions and selected decisions.

### Expected Outputs

- Storm-level situational awareness.
- Scenario comparison.
- Regional or priority-based strategy.
- Decision record for post-event review.

### Exception Paths

- Weather conditions change rapidly.
- Crew staging assumptions become invalid.
- External mutual assistance resources are added.
- Critical facility restoration overrides standard prioritization.

## Workflow 6: Post-Event Review

### Objective

Review recommendations, decisions, overrides, and outcomes to improve future dispatch performance.

### Primary Persona

Operations Analyst

### Trigger

An outage event, storm period, operating day, or review window has ended.

### Main Flow

1. Analyst opens historical review or analytics view.
2. System displays completed incidents, recommendations, assignments, overrides, and outcomes.
3. Analyst filters by event type, region, date, crew, recommendation type, or override reason.
4. Analyst reviews recommendation acceptance, override patterns, restoration outcomes, and data quality issues.
5. Analyst exports or summarizes findings for operations improvement.

### Expected Outputs

- Recommendation performance review.
- Override trend analysis.
- Data quality issue list.
- Operational improvement findings.

### Exception Paths

- Historical source data is incomplete.
- Outcome data cannot be matched to original recommendations.
- Audit events require restricted access.

## Developer Bootstrap MVP Workflow Coverage

The Developer Bootstrap MVP should represent the following workflows with realistic sample data:

| Workflow | MVP Coverage |
| --- | --- |
| Routine outage triage | Dashboard, dispatch queue, incident detail |
| Crew assignment recommendation | Crew board and ranked recommendation sample |
| Recommendation override | Basic accept, modify, defer, override UI state |
| Supervisor monitoring | Dashboard metrics and exception panels |
| Storm mode coordination | Storm mode page with aggregate sample data |
| Post-event review | Deferred until analytics or audit data exists |

## Related Documents

- [Stakeholders and Personas](103_Stakeholders_and_Personas.md)
- [Product Requirements](105_Product_Requirements.md)
- [Non-Functional Requirements](106_Non_Functional_Requirements.md)

