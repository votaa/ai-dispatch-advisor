# UI Information Architecture

## Purpose

This document defines the user interface information architecture for the AI Dispatch Advisor. It describes the primary navigation model, page responsibilities, information hierarchy, and current-to-target UX evolution.

## Current Implementation State

The Developer Bootstrap MVP currently provides a single React application shell with seven visible sections:

- Dashboard.
- Dispatch.
- Incidents.
- Crew Board.
- Storm Mode.
- Scenario.
- AI Copilot.

These sections are implemented in `frontend/src/App.tsx` and selected through local component state. The current POC does not yet use React Router or separate page modules.

## UX Architecture Goals

The UI architecture should support:

- Fast dispatch triage.
- Low-friction review of AI-assisted recommendations.
- Clear separation between situational awareness, dispatch action, crew management, storm operations, scenarios, and advisory assistance.
- Dense but readable operational data.
- Human review and auditability.
- Future role-specific views for dispatchers, supervisors, analysts, administrators, and reviewers.

## Primary Navigation Model

The target navigation model should preserve the current top-level sections:

| Section | Primary User Need |
| --- | --- |
| Dashboard | Understand current outage operations at a glance |
| Dispatch | Review incidents, recommendations, and dispatch actions |
| Incidents | Search and inspect active outage events |
| Crew Board | Review crew availability, capability, and assignments |
| Storm Mode | Monitor major event conditions and regional impact |
| Scenario | Compare dispatch and restoration alternatives |
| AI Copilot | Ask advisory questions against operational context |

## Page Responsibility Model

### Dashboard

Purpose:

- Provide the primary operations overview.
- Surface system status, major metrics, priority incidents, and active recommendation context.

Should include:

- Customers out.
- Active incidents.
- Available and assigned crews.
- Critical facility incidents.
- High-priority incidents.
- Priority dispatch queue.
- Data freshness or scenario indicator.

Should not include:

- Full incident management workflow.
- Administrative configuration.
- Detailed audit history.

### Dispatch

Purpose:

- Support the core dispatcher workflow: select incident, review context, review recommendation, and take action.

Should include:

- Incident queue.
- Selected incident context.
- Recommendation panel.
- Explanation factors.
- Recommendation actions.
- Recent action or audit feedback.

Should not include:

- Full historical analytics.
- Integration administration.

### Incidents

Purpose:

- Provide a focused active incident list and future incident detail drilldown.

Should include:

- Incident table.
- Filters and sorting.
- Incident status.
- Severity.
- Customer impact.
- Critical facility flag.
- Hazard and ETR context.

Target evolution:

- Add incident detail route.
- Add map or network context.
- Add related events and source data quality indicators.

### Crew Board

Purpose:

- Provide visibility into crew availability, capability, and suitability.

Should include:

- Crew cards or grid.
- Availability state.
- Capability.
- Current location or operating area.
- Shift status.
- Current assignment.
- Suitability for selected incident.

Target evolution:

- Add crew assignment history.
- Add filters by region, capability, and status.
- Add staging and mutual assistance views.

### Storm Mode

Purpose:

- Support high-volume outage operations.

Should include:

- Aggregate customer impact.
- High-priority and critical facility incidents.
- Crew capacity.
- Regional exceptions.
- Weather and access constraints.

Target evolution:

- Add regional drilldown.
- Add mutual assistance views.
- Add storm event scenario comparison.

### Scenario

Purpose:

- Compare dispatch and restoration alternatives.

Should include:

- Base recommendation.
- Alternative option.
- Tradeoff summary.
- Recommendation impact comparison.

Target evolution:

- Add scenario inputs and assumptions.
- Add side-by-side metrics.
- Add save/export scenario support.

### AI Copilot

Purpose:

- Provide advisory responses grounded in operational context.

Should include:

- Prompt examples.
- Conversation-style responses.
- Clear advisory boundary.
- Selected incident awareness.

Should not:

- Execute dispatch actions directly.
- Present advisory output as authoritative without source context.

## Information Hierarchy

The UI should prioritize information in this order:

1. Operational urgency: severity, critical facilities, hazards, customers out, aging incidents.
2. Actionability: recommendation, crew option, current status, next action.
3. Trust context: explanation, confidence, source data, constraints, freshness.
4. Supporting details: topology, weather, historical repair context, alternatives.
5. Audit and history: prior actions, overrides, notes, outcomes.

## Current-to-Target Refactor Path

| Current POC | Target Direction |
| --- | --- |
| Single `App.tsx` handles all sections | Route-level pages and reusable components |
| Local navigation state | React Router or equivalent route model |
| Manual TypeScript types | Types aligned with backend schemas |
| Static layout | Responsive operational shell with role-aware pages |
| Placeholder action buttons | Persisted recommendation action workflow |
| Demo Copilot responses | Controlled AI service with retrieved context |

## Role-Based Navigation Considerations

Future role-aware navigation may include:

| Role | Priority Sections |
| --- | --- |
| Dispatcher | Dashboard, Dispatch, Incidents, Crew Board, AI Copilot |
| Supervisor | Dashboard, Dispatch, Storm Mode, Scenario, audit summaries |
| Storm Coordinator | Storm Mode, Scenario, Crew Board, Dashboard |
| Analyst | Incidents, recommendation history, audit, analytics |
| Administrator | Integration health, configuration, user access |
| Read-only Reviewer | Dashboard, reports, audit views |

## Design Principles

- Show the operational workspace first; do not use a marketing landing page.
- Keep page structure predictable across routine and storm modes.
- Avoid hiding critical constraints behind conversational UI.
- Treat maps and AI as supporting tools, not replacements for dispatch workflow.
- Make recommendation state visibly distinct from approved dispatch action.
- Keep status, confidence, and data freshness visible when relevant.

## Related Documents

- [Dispatch Console Specification](302_Dispatch_Console_Specification.md)
- [Recommendation Experience](303_Recommendation_Experience.md)
- [Explainability and Trust](304_Explainability_and_Trust.md)
- [Accessibility Guidelines](305_Accessibility_Guidelines.md)

