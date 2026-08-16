# Accessibility Guidelines

## Purpose

This document defines accessibility guidelines for the AI Dispatch Advisor frontend. The product is an enterprise operational tool and should support accessible, readable, keyboard-friendly, and low-friction workflows.

## Accessibility Goals

The UI should:

- Support keyboard navigation.
- Maintain readable contrast.
- Avoid color-only meaning.
- Provide visible focus states.
- Use semantic structure for pages, tables, controls, and forms.
- Keep text legible in dense operational layouts.
- Avoid unexpected layout shifts.
- Make critical actions clear and confirmable.

## Current Implementation State

The current POC includes:

- A skip link, main landmark, page heading focus on view changes, and `aria-current` primary navigation state.
- Semantic buttons for navigation, incident and crew selection, sorting, pagination, and recommendation actions.
- Tables with sortable-column state and labeled horizontally scrollable regions for incident data.
- Text labels for severity and status.
- Visible focus indicators and responsive layout rules.
- Live loading and result summaries, assertive failure feedback, labeled validation errors, and required-state semantics for dispatcher reasons.
- Labeled Crew Board and incident filter groups whose remaining-result counts and disabled zero-result choices are available in native select controls.

Accessibility should be reviewed more deeply as the frontend is split into production components.

## Keyboard Navigation

The application should support:

- Tab navigation through primary navigation.
- Keyboard activation of buttons.
- Focus movement into forms and action panels.
- Clear focus indicators.
- No keyboard traps.

Recommendation action controls must be usable by keyboard.

## Color and Status Indicators

Color should not be the only status indicator.

Severity should use:

- Text label.
- Color treatment.
- Consistent visual style.

Examples:

- `critical` should display the word "critical."
- `high` should display the word "high."
- Crew statuses should display text such as "available" or "assigned."

## Contrast and Readability

The interface should maintain sufficient contrast for:

- Navigation text.
- Table text.
- Metric labels and values.
- Status pills.
- Recommendation panels.
- Error banners.
- Prompt buttons.

Dense operational pages should avoid small, low-contrast text for critical information.

## Tables and Data Grids

Incident and crew data should support:

- Clear column headers.
- Consistent row selection.
- Visible selected state.
- Keyboard-friendly row interaction when implemented.
- Avoidance of horizontal-only interaction on small screens.

The current incident tables use semantic selection buttons in the Incident column so keyboard users do not need to focus an entire table row. Filter summaries and pagination controls are labeled by their owning queue.

For future advanced grids, ensure sorting, filtering, and selection are accessible.

## Forms and Inputs

Forms should include:

- Visible labels or accessible labels.
- Clear validation errors.
- Required field indication.
- Helpful placeholder text only as secondary support.
- Keyboard-accessible submission.

Override and modification workflows should clearly identify required reason fields.

## Recommendation Action Accessibility

Accept, Modify, Defer, and Override actions should:

- Use real button elements.
- Have clear text labels.
- Provide confirmation feedback.
- Avoid relying only on color.
- Require explicit confirmation for override when appropriate.
- Announce or visibly display action result.

## Copilot Accessibility

The Copilot panel should:

- Provide visible prompt examples.
- Use a labeled text area.
- Display question and answer history in reading order.
- Avoid auto-executing actions from natural language.
- Provide clear advisory safety text.

Future enhancements should consider screen reader announcements for new Copilot responses.

## Responsive Behavior

The UI should remain usable on:

- Standard desktop.
- Laptop screens.
- Tablet-width review contexts.

Operational dispatcher workflows are assumed to be desktop-first, but layouts should not break on narrower screens.

## Motion and Alerts

The product should avoid unnecessary animation. Operational alerts should be clear but not distracting.

If future animation is used:

- Respect reduced-motion preferences.
- Avoid flashing.
- Avoid motion that obscures critical content.

## Accessibility Acceptance Criteria

For each major frontend change:

- Primary navigation is keyboard reachable.
- Main action buttons are keyboard reachable.
- Text remains readable.
- Status is communicated with text.
- Forms have labels.
- Error states are visible and understandable.
- No critical workflow depends only on hover.

## Future Accessibility Work

Future work should include:

- Automated accessibility checks.
- Manual keyboard review.
- Screen reader spot checks.
- Color contrast review.
- Accessible map alternatives.
- Data grid accessibility review.
- Modal and dialog accessibility review.

## Related Documents

- [UI Information Architecture](301_UI_Information_Architecture.md)
- [Dispatch Console Specification](302_Dispatch_Console_Specification.md)
- [Recommendation Experience](303_Recommendation_Experience.md)
- [Explainability and Trust](304_Explainability_and_Trust.md)
