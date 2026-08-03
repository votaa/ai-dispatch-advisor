# Component Guidelines

## Purpose

This document defines frontend component guidelines for the AI Dispatch Advisor. It establishes conventions for component responsibilities, composition, naming, props, accessibility, styling, and future refactoring of the current POC.

## Current Implementation State

The current POC defines several component-like functions inside `frontend/src/App.tsx`, including:

- `Metric`.
- `PanelTitle`.
- `IncidentTable`.
- `RecommendationPanel`.

These are acceptable for the bootstrap MVP. As the UI grows, these should be extracted into dedicated component files.

## Component Principles

Components should be:

- Focused on a single responsibility.
- Typed with explicit props.
- Reusable where reuse is real.
- Accessible by default.
- Free of hidden backend side effects unless clearly named as data-aware components.
- Styled consistently with the operations-console design language.
- Easy to test when behavior is meaningful.

## Recommended Component Categories

```text
frontend/src/components/
  actions/
  feedback/
  layout/
  metrics/
  recommendations/
  tables/
  crews/
  incidents/
  copilot/
```

## Naming Conventions

Use descriptive PascalCase component names:

- `AppShell`.
- `Sidebar`.
- `Topbar`.
- `MetricCard`.
- `IncidentTable`.
- `CrewCard`.
- `RecommendationPanel`.
- `RecommendationActions`.
- `OverrideReasonForm`.
- `CopilotPanel`.
- `ErrorBanner`.

Avoid vague names such as:

- `Box`.
- `Thing`.
- `Data`.
- `MainCard`.

## Component Responsibility Boundaries

### Presentational Components

Presentational components should:

- Receive data through props.
- Render UI.
- Emit callbacks for user actions.
- Avoid direct API calls.

Examples:

- `MetricCard`.
- `CrewCard`.
- `StatusPill`.
- `PanelTitle`.

### Workflow Components

Workflow components may manage local interaction state.

Examples:

- `RecommendationActions`.
- `OverrideReasonForm`.
- `CopilotPanel`.

Workflow components should still persist meaningful actions through backend services.

### Page Components

Page components should:

- Fetch or coordinate data.
- Compose presentational and workflow components.
- Own page-specific filters, selected records, and loading state.

Examples:

- `DispatchPage`.
- `CrewBoardPage`.
- `StormModePage`.

## Prop Guidelines

Props should:

- Use explicit TypeScript types.
- Prefer domain names over generic names.
- Avoid deeply nested objects unless the domain object is intentionally passed through.
- Use callbacks named for the event.

Example:

```tsx
type RecommendationActionsProps = {
  recommendationId: string;
  incidentId: string;
  crewId?: string;
  onActionRecorded: (eventId: string) => void;
};
```

## API Call Guidelines

Components should not scatter raw `fetch` calls across the application.

Preferred pattern:

```text
Component -> Page or Hook -> API Service -> Backend
```

The current `frontend/src/api.ts` is the correct starting boundary.

## Styling Guidelines

The UI should preserve an enterprise operations-console style:

- Dense but readable.
- Clear visual hierarchy.
- Limited decorative treatment.
- Status text paired with color.
- Predictable panels and tables.
- No marketing hero page.
- No nested decorative card stacks.

Component styles should:

- Use shared class naming patterns.
- Avoid inline style except for dynamic values that are difficult to express otherwise.
- Keep text readable at expected screen sizes.
- Avoid relying on viewport-width font scaling.

## Accessibility Guidelines

Components should:

- Use semantic elements.
- Use real buttons for actions.
- Support keyboard interaction.
- Avoid hover-only controls.
- Provide visible labels for form fields.
- Use text labels with status colors.
- Preserve focus visibility.

Recommendation actions, override forms, and Copilot input require particular attention.

## Table Components

Incident and crew tables should:

- Use table headers.
- Keep row selection visible.
- Support keyboard selection when row interaction matures.
- Provide empty states.
- Avoid hiding important data behind horizontal-only access.

When advanced table behavior grows, consider introducing a data grid library intentionally.

## Recommendation Components

Recommendation components should keep these concerns distinct:

- Recommendation summary.
- Explanation factors.
- Constraints.
- Alternatives.
- User action controls.
- Recent action history.

Do not combine all recommendation behavior into one large component once action recording is implemented.

## Copilot Components

Copilot components should:

- Make advisory boundaries visible.
- Show question and answer history.
- Provide prompt examples.
- Avoid executing operational actions.
- Handle loading and errors clearly.

## Refactor Path From Current POC

Recommended first extractions:

1. Extract `IncidentTable`.
2. Extract `RecommendationPanel`.
3. Extract `RecommendationActions`.
4. Extract `MetricCard`.
5. Extract layout components.
6. Split page components after routing is introduced.

## Testing Guidance

Add component tests when:

- A component has conditional behavior.
- A user action changes state.
- A form validates input.
- A recommendation action is recorded.
- Accessibility behavior is important.

Snapshot tests alone are not sufficient for workflow components.

## Related Documents

- [Frontend Architecture](501_Frontend_Architecture.md)
- [State Management](502_State_Management.md)
- [Routing and Navigation](504_Routing_and_Navigation.md)
- [Accessibility Guidelines](../300_UX/305_Accessibility_Guidelines.md)

