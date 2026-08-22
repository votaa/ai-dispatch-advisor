# Test Strategy

## Purpose

This document defines the testing strategy for the AI Dispatch Advisor. The goal is to make the system demonstrable in its current POC form while creating a disciplined path toward enterprise-grade validation for outage dispatch operations.

The strategy covers frontend behavior, backend APIs, data quality, optimization logic, AI-assisted recommendations, integrations, security controls, and operational readiness.

## Testing Objectives

The testing program must demonstrate that the system:

- Presents outage, crew, and recommendation data accurately.
- Produces explainable dispatch recommendations.
- Preserves dispatcher authority over operational actions.
- Handles degraded data and integration failures safely.
- Provides auditable evidence for recommendations, decisions, and overrides.
- Meets expected usability, accessibility, performance, and security standards.
- Can be released and operated without relying on undocumented manual steps.

## Current POC Testing Scope

The current MVP should be treated as a functional demonstration baseline, not a certified production system.

Current testing expectations include:

- Frontend builds successfully.
- Backend service starts successfully.
- Core API endpoints return valid demo data.
- CSV demo data can be loaded into the local application.
- Recommendation views render without blocking the dispatch workflow.
- Demo interactions do not imply live OMS, GIS, SCADA, or crew system writeback.

The POC should remain runnable after each committed change.

## Test Levels

### Unit Tests

Unit tests validate isolated functions and components.

Frontend unit tests should cover:

- Data transformation utilities.
- Recommendation status labels and severity formatting.
- Component rendering for empty, loading, error, and populated states.
- State transitions for accept, modify, defer, and override actions.

Backend unit tests should cover:

- API response shaping.
- CSV or database loading functions.
- Recommendation scoring helpers.
- Validation rules for incidents, crews, and assignments.
- Error handling for invalid request payloads.
- Direct application-service behavior without requiring an HTTP test client.
- Service composition of immutable scenario inputs with scenario-scoped mutable state.
- Optimization policy validation, classification, immutability, and engine consumption.
- Characterized recommendation winners, suitability scores, and alternative ordering for canonical scenarios.
- Exact incident score contributions, configurable-weight effects, and deterministic severity, age, customer-impact, and identifier tie-breakers.
- Rejection of unsupported, duplicate, or inconsistent incident tie-break configuration.

Optimization unit tests should cover:

- Scoring factor calculations.
- Constraint handling.
- Tie-breaking behavior.
- Edge cases such as no available crews, missing travel time, or incomplete outage metadata.

### API Tests

API tests validate service contracts between frontend, backend, and future integrations.

Required API test areas:

- Incident retrieval.
- Crew retrieval.
- Assignment retrieval.
- Dashboard summary retrieval.
- Recommendation generation.
- Recommendation decision capture.
- Copilot request and response handling.
- Named OpenAPI request, success-response, and error-response schemas.
- Structured error responses for malformed input, missing entities, invalid decision state, scenario validation, framework 404s, and unexpected failures.
- Correlation-ID generation and propagation on successful and failed requests.
- Assurance that unexpected failures do not expose internal exception details.

API tests should assert both response structure and business meaning. For example, a dispatch recommendation should include an incident, assigned crew, recommendation reason, confidence, expected impact, and explanation factors.

### Frontend Integration Tests

Frontend integration tests validate that user workflows function across multiple UI components.

Priority workflows:

- Dispatcher reviews dashboard status.
- Dispatcher opens dispatch console.
- Dispatcher reviews an incident and recommendation.
- Dispatcher accepts a recommendation.
- Dispatcher modifies a recommendation.
- Dispatcher defers a recommendation.
- Dispatcher overrides a recommendation with a required reason.
- Dispatcher views the resulting audit or decision state.

The POC currently displays some controls before all actions are fully functional. These gaps should be tracked in `docs/004_POC_Feedback_Log.md`.

### End-to-End Tests

End-to-end tests validate the application as a user would experience it.

Initial E2E scenarios:

- Application loads at the frontend development URL.
- Dashboard summary cards render.
- Incident queue renders demo incidents.
- Crew board renders demo crews.
- Recommendation panel renders at least one recommendation.
- Copilot accepts a prompt and displays a response.
- Dispatch decision actions update visible state once implemented.

Future E2E scenarios should include authenticated sessions, role-based permissions, integration failure states, and release smoke tests.

### Accessibility Tests

Accessibility testing should validate:

- Keyboard navigation.
- Visible focus indicators.
- Color contrast.
- Screen reader labels for controls.
- Form validation announcements.
- Map and geospatial fallback information.
- Non-color-only severity indicators.

Accessibility requirements are defined in `docs/300_UX/305_Accessibility_Guidelines.md`.

### Security Tests

Security testing should include:

- Authentication and authorization tests once IAM is implemented.
- Role-based access checks.
- Input validation and injection resistance.
- Sensitive data handling.
- Audit logging coverage.
- API error response review.
- Dependency vulnerability scanning.
- Container image scanning when Docker images are introduced into CI/CD.

Security controls are defined in `docs/800_Security_Operations/801_Security_Architecture.md`.

### Performance Tests

Performance tests should focus on dispatcher workflow responsiveness during normal and storm operating conditions.

Target areas:

- Dashboard load time.
- Incident queue filtering and sorting.
- Recommendation generation latency.
- Map rendering performance.
- Bulk outage and crew data loading.
- Backend API response time.
- Optimization engine runtime under large event counts.

The POC may use synthetic thresholds. Production thresholds must be validated with utility-specific operating volumes.

### Data Quality Tests

Data quality tests should validate:

- Required fields are present.
- Identifiers are stable and unique.
- Incident status values are valid.
- Crew capability values are valid.
- Coordinates are valid where geospatial display is required.
- Timestamps are parseable and timezone-aware.
- Critical facility references resolve correctly.
- Demo scenario data remains internally consistent.

Data modeling expectations are defined in `docs/600_Data_AI/601_Data_Model.md`.

### Recommendation Validation

Recommendation testing must evaluate both the recommendation output and the reasoning behind it.

Validation should include:

- Recommendation includes required explanation factors.
- Recommendation respects hard constraints.
- Phase 5.3 feasibility tests verify capability and travel-within-shift blocking rules and assert typed exclusion reasons for each rejected crew.
- Phase 5.4 explanation tests verify nested schemas, confidence rationale, policy/version metadata, assumptions, warnings, and no-feasible-crew explanations.
- Phase 5.5 contract tests run the same engine expectations against the deterministic and fake adapters and verify services can be wired without implementation-specific changes.
- Phase 5.6 evaluation tests run recommendation invariants across every manifested scenario and explicit edge-case fixtures; SME review evidence is maintained in `docs/900_Delivery/905_Phase_5_SME_Review_Checklist.md`.
- Phase 6.1 frontend tests hold the recommendation panel in a loading state during delayed scenario refreshes, prevent transient empty-state text, and verify the scenario selector is disabled until refresh completion.
- Phase 6.2 frontend tests verify shared incident search, severity and region filtering, sortable table-header direction toggles across incident columns, deterministic default ordering, pagination, responsive controls, and no-match messaging with large-list fixtures.
- Phase 6.3 frontend tests verify Crew Board search, status filtering, crew-ID visibility, result summaries, sort-direction controls, read-only incident and crew detail panels, and assignment cross-navigation.
- Phase 6.4 frontend tests verify recommended-versus-alternative crew presentation and plain-language travel, suitability, shift, capability, and storm-readiness tradeoffs.
- Phase 6.4.1 frontend and API tests verify alternative selection, required rationale, ranked-membership and live-availability validation, modified assignment overlays, and preservation of original recommendation evidence beside the actual selected crew.
- Phase 6.5 frontend tests verify cascading facet counts and disabled zero-result choices across Crew Board and every incident-queue view, current-page navigation and focus movement, skip navigation, labeled Copilot input, semantic incident selection, accessible reason validation, and keyboard-focused Defer and Override workflows.
- POC-015 frontend tests verify exact Copilot helper copy, clearing the default and typed composer values, whitespace-only disabled state, preservation of conversation history, local execution metadata, and safe multi-block grounded-AI Markdown rendering.
- Phase 6.6 closeout verification passed 92 backend tests, 17 frontend tests, and the frontend production build on 2026-08-16; the detailed evaluation is recorded in `docs/900_Delivery/906_Phase_6_Closeout.md`.
- Confidence is not overstated when input data is incomplete.
- Critical facilities are prioritized appropriately.
- Crew skills match incident requirements.
- Travel and availability assumptions are visible.
- Override behavior is captured for later review.

The system should be tested against known scenarios with expected recommendation patterns, not only randomly generated demo data.

## Test Data Strategy

The repository should maintain version-controlled synthetic data sets for repeatable testing and demos.

Recommended scenario data sets:

- Blue-sky daily operations.
- Moderate storm event.
- Major storm event.
- Critical facility outage.
- Crew shortage.
- Communication or integration outage.
- Conflicting data quality scenario.
- No feasible dispatch recommendation scenario.

Synthetic data must not include real customer personal information, operationally sensitive network details, or live utility credentials.

## Test Environments

Recommended environments:

| Environment | Purpose |
| --- | --- |
| Local development | Developer validation and POC demo testing |
| CI test environment | Automated checks on each pull request or push |
| Shared demo environment | Stable stakeholder demonstrations |
| Integration test environment | OMS, GIS, SCADA, weather, and crew system contract validation |
| Pre-production | Release candidate validation using production-like configuration |
| Production | Controlled operational deployment |

The current POC primarily supports local development.

## Phase 7 Integration Test Direction

Phase 7 should add a reusable contract suite before connecting to a live or sandbox enterprise source. The same behavioral expectations should run against the current CSV adapter, deterministic mocks, and each future real adapter.

Coverage should include:

- Vendor-payload mapping into normalized domain contracts.
- Stable source identifiers, provenance, source timestamps, load timestamps, freshness, quality, and health states.
- Healthy, stale, delayed, partial, malformed, timeout, unavailable, disabled, and recovery paths.
- Source-to-normalized reconciliation and schema-drift detection.
- Sanitized integration errors and correlation identifiers.
- API backward compatibility when the configured adapter changes.
- Recommendation warnings or confidence effects when required data is stale or degraded.
- Frontend freshness and degraded-state messaging.
- Representative source volumes and update rates.

The first integration test plan must use requirements from the selected source owner and an approved sample payload or sandbox. Writeback tests remain out of scope until later IAM, authorization, audit, acknowledgement, and recovery controls are approved.

## Quality Gates

Before merging implementation changes:

- Tests relevant to the changed area should pass.
- Frontend build should pass.
- Backend tests should pass.
- Linting should pass where configured.
- API contract changes should be documented.
- User-facing workflow changes should update relevant documentation.
- POC feedback items should be linked when a change resolves a known demo gap.

Before release:

- Regression tests should pass.
- Release notes should be prepared.
- Known limitations should be reviewed.
- Rollback procedure should be confirmed.
- Runbook should be current.

## Test Automation Roadmap

| Stage | Automation Focus |
| --- | --- |
| POC | Build checks, backend scenario/API tests, canonical deterministic recommendation fixtures, dynamic-discovery checks, and focused frontend workflow/state tests |
| MVP | Expanded unit tests, API contract tests, and frontend workflow coverage |
| Pilot | Integration tests, E2E tests, accessibility checks, security scanning |
| Enterprise release | Performance tests, disaster recovery drills, audit evidence capture |

## Open Gaps

Current gaps to close as the POC matures:

- Copilot behavior is currently demo-oriented and rule-based.
- Recommendation validation needs broader scoring, constraint, and edge-case fixtures beyond the four canonical regression scenarios; generated scenarios expand data coverage but do not replace deterministic expected-result fixtures.
- Integration adapters are not yet connected to live systems.
- Security, IAM, and audit controls are documented but not fully implemented.
- CI should expand from basic checks to release-grade gates.

## Related Documents

- `docs/004_POC_Feedback_Log.md`
- `docs/300_UX/303_Recommendation_Experience.md`
- `docs/400_Backend_API/402_API_Overview.md`
- `docs/600_Data_AI/602_Optimization_Engine.md`
- `docs/600_Data_AI/603_AI_Recommendation_Engine.md`
- `docs/800_Security_Operations/801_Security_Architecture.md`
