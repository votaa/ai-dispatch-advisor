# Routing and Navigation

## Purpose

This document defines routing and navigation guidance for the AI Dispatch Advisor frontend. It describes the current local navigation model and the target route structure needed as the POC evolves into a maintainable application.

## Current Implementation State

The current POC uses local React state to select one of these views:

- Dashboard.
- Dispatch.
- Incidents.
- Crew Board.
- Operations Map.
- Storm Mode.
- Scenario.
- AI Copilot.

There is no React Router dependency yet. The browser URL does not change when users move between views.

This is acceptable for the Developer Bootstrap MVP. Routing should be introduced when deep links, browser navigation, page-level state, or role-aware navigation become important.

## Navigation Principles

Navigation should:

- Reflect dispatcher workflows.
- Keep the operational dashboard as the first screen.
- Keep dispatch actions easy to reach.
- Separate routine and storm workflows without duplicating core concepts.
- Preserve clear page names.
- Support future deep links to incidents, recommendations, scenarios, and audit records.

## Primary Navigation Items

The current primary navigation model should remain:

| Label | Target Route | Purpose |
| --- | --- | --- |
| Dashboard | `/` or `/dashboard` | Operations overview |
| Dispatch | `/dispatch` | Primary dispatch work surface |
| Incidents | `/incidents` | Active incident list and future detail views |
| Crew Board | `/crews` | Crew availability and assignment context |
| Operations Map | `/map` (future route) | Incident and approximate crew geography; links to existing workflows |
| Storm Mode | `/storm` | Major event operations |
| Scenario | `/scenarios` | Dispatch and restoration scenario comparison |
| AI Copilot | `/copilot` | Advisory operational questions |

## Target Route Structure

Recommended future routes:

```text
/
/dashboard
/dispatch
/dispatch/:incidentId
/incidents
/incidents/:incidentId
/crews
/crews/:crewId
/storm
/scenarios
/scenarios/:scenarioId
/copilot
/audit
/settings
```

`/audit` and `/settings` should not be introduced into primary navigation until the related functionality exists.

## Route Responsibilities

### `/dashboard`

Should show:

- Metrics.
- Priority queue.
- Critical facility count.
- Crew availability summary.
- Scenario and data freshness indicators.

### `/dispatch`

Should show:

- Incident queue.
- Selected recommendation.
- Action controls.
- Recent action history.

### `/dispatch/:incidentId`

Should deep link to dispatch workflow for a specific incident.

### `/incidents`

Should show:

- Incident list.
- Filters.
- Sorting.
- Search.

### `/incidents/:incidentId`

Should show:

- Incident detail.
- Related recommendations.
- Crew options.
- Source data.
- History.

### `/crews`

Should show:

- Crew board.
- Crew filters.
- Availability and capability.

### `/storm`

Should show:

- Regional impact.
- Critical events.
- Crew capacity.
- Storm exceptions.

### `/scenarios`

Should show:

- Scenario comparison.
- Assumptions.
- Impact tradeoffs.

### `/copilot`

Should show:

- Advisory question input.
- Prompt examples.
- Conversation history.
- Safety boundary.

## Selected Incident State

Selected incident can be represented as:

- Local page state for simple interaction.
- Route parameter for deep links.
- Shared state when selected incident affects multiple pages.

Recommended target:

- Use `/dispatch/:incidentId` for dispatch workflow deep links.
- Use `/incidents/:incidentId` for incident detail deep links.
- Keep selected incident route-aware once routing is introduced.

## Browser Behavior

Once routing exists:

- Back and forward buttons should work.
- Refresh should preserve current route.
- Deep links should load relevant data.
- Unknown routes should show a clear not-found page.
- Missing incident identifiers should show a useful not-found or unavailable message.

## Role-Aware Navigation

Future role behavior:

| Role | Navigation Impact |
| --- | --- |
| Dispatcher | Dashboard, Dispatch, Incidents, Crew Board, Copilot |
| Supervisor | Dashboard, Dispatch, Storm, Scenario, audit summaries |
| Analyst | Incidents, audit, reports, recommendation history |
| Administrator | Settings, integration health, role management |
| Read-only Reviewer | Dashboard and read-only reports |

Role-aware navigation should hide or disable inappropriate UI, but backend authorization must still enforce permissions.

## Mobile and Responsive Navigation

The application is desktop-first because dispatch workflows are operational and data-dense.

Responsive behavior should:

- Collapse navigation on narrow screens.
- Preserve page access.
- Avoid overlapping content.
- Keep action buttons reachable.

Mobile is not the primary target for the initial POC.

## Routing Introduction Criteria

Introduce React Router or equivalent when:

- Users need shareable links.
- Browser back/forward behavior matters.
- Incident detail views are added.
- Route-level page components are extracted.
- User roles affect navigation.
- Audit and settings sections are introduced.

## Migration Path

Recommended sequence:

1. Extract page components while keeping local view state.
2. Add React Router.
3. Map current navigation items to routes.
4. Add route parameters for selected incident.
5. Move selected incident logic into route-aware state.
6. Add not-found and loading pages.

## Related Documents

- [Frontend Architecture](501_Frontend_Architecture.md)
- [State Management](502_State_Management.md)
- [Component Guidelines](503_Component_Guidelines.md)
- [UI Information Architecture](../300_UX/301_UI_Information_Architecture.md)

