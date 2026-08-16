# Implementation Plan

## Purpose

This document defines the implementation plan for evolving the AI Dispatch Advisor from a runnable POC into a production-ready enterprise application. It organizes work into practical delivery phases while preserving the ability to demonstrate progress after each milestone.

## Current Baseline

The current project baseline includes:

- Repository documentation foundation.
- Runnable React frontend.
- Runnable FastAPI backend.
- Synthetic CSV demo data.
- Five currently version-controlled, dynamically discovered synthetic scenarios, including four canonical regression fixtures.
- Scenario-isolated local SQLite decision and accepted-assignment persistence.
- Initial dashboard, dispatch, incidents, crew board, scenario, storm mode, and Copilot pages.
- Demo-functional recommendation actions with visible status and history.
- Backend scenario validation plus focused frontend workflow and application-state tests.
- Initial CI and Docker structure.
- Enterprise documentation for product, architecture, UX, API, frontend, data, integrations, security, and operations.

This baseline is suitable for POC demonstrations, stakeholder walkthroughs, and iterative requirement discovery.

## Phase Status Overview

| Phase | Status | Current Position |
| --- | --- | --- |
| Phase 1: POC Stabilization | Complete | Startup, sample-data consistency, backend and frontend checks, primary-page loading/empty/error states, canonical regression testing, dynamic-discovery smoke testing, and known-limitations documentation are in place. |
| Phase 2: Dispatch Decision Workflow | Complete | Recommendation actions, required reasons, SQLite persistence, audit history, accepted assignment overlays, and visible status are implemented. |
| Phase 3: Scenario Data and Demo Management | Complete | Multiple manifested scenarios, dynamic discovery, runtime activation, frontend selection, scenario-isolated state, validation, and four canonical deterministic fixtures are implemented. |
| Phase 4: Backend Domain Model | Complete | Phases 4.1–4.4 established the persistence boundary, typed contracts, service boundaries, versioned SQLite migrations, structured errors, request correlation, and API failure-contract coverage. |
| Phase 5: Recommendation and Optimization Engine | Complete | Phases 5.1–5.6 establish versioned policy and engine contracts, structured scoring, deterministic tie-breakers, blocking crew feasibility, nested explanations, replaceable-engine coverage, and scenario/edge-case evaluation evidence. |
| Phase 6: Frontend Workflow Maturity | In progress | Phases 6.1–6.4 add scenario loading-state hardening, shared incident and crew filtering/sorting, paginated large-list handling, crew-ID visibility, read-only detail interactions with cross-navigation, and recommendation comparison with operational tradeoffs. Accessibility and broader tests remain pending. |
| Phase 7: Enterprise Integration Adapters | Pending | Integration documentation exists, but adapter interfaces, mock adapters, contract tests, and degradation handling are not implemented. |
| Phase 8: Security, IAM, and Audit | Pending with POC audit foundation | Local decision auditing exists. Authentication, authorization, enterprise identity, security controls, and production audit handling remain pending. |
| Phase 9: Observability and Deployment | Pending with bootstrap foundation | Basic health, request correlation, CI, Docker, and runbook assets exist. Structured telemetry, readiness, hardened deployment, and operational metrics remain pending. |
| Phase 10: Pilot Readiness | Pending | SME validation, pilot criteria, readiness reviews, release controls, and support procedures remain pending. |

## Delivery Principles

Implementation should follow these principles:

- Keep the application runnable at all times.
- Use small commits organized by functional area.
- Separate documentation commits from application behavior commits.
- Prefer visible workflow progress over hidden infrastructure-only changes.
- Treat dispatcher trust, explainability, and auditability as core product features.
- Avoid pretending demo behavior is production integration.
- Record POC observations in `docs/004_POC_Feedback_Log.md`.
- Update documentation when implementation decisions change.

## Phase 1: POC Stabilization

Objective: make the current MVP reliable for repeated demonstrations.

Status: Complete for the POC baseline as of 2026-08-10.

Scope:

- Confirm local startup instructions work.
- Improve sample data consistency.
- Add smoke tests for core backend endpoints.
- Add frontend build validation.
- Improve demo error handling.
- Ensure pages render useful empty and loading states.
- Document known POC limitations.

Exit criteria:

- Frontend and backend start cleanly.
- Demo data loads without manual repair.
- Dashboard and dispatch views render consistently.
- Known limitations are captured in the feedback log.

## Phase 2: Dispatch Decision Workflow

Objective: make Accept, Modify, Defer, and Override demo-functional.

Status: Complete for the POC baseline as of 2026-08-09.

Scope:

- Add recommendation decision state.
- Define decision types and required fields.
- Add backend endpoint for decision capture.
- Persist decisions locally.
- Update frontend controls to reflect selected action.
- Require override or defer reason where appropriate.
- Show action history or status in the UI.
- Add basic audit event generation.

Exit criteria:

- Each recommendation action changes visible state.
- Decisions survive page refresh if local persistence is used.
- Override and defer actions capture a reason.
- The decision model aligns with API and audit documentation.

## Phase 3: Scenario Data and Demo Management

Objective: support multiple repeatable demo scenarios.

Status: Complete for the POC baseline as of 2026-08-09.

Scope:

- Organize sample CSV files into scenario folders.
- Provide a clear scenario loading mechanism.
- Add scenario metadata.
- Support blue-sky, storm, crew shortage, and critical facility scenarios.
- Validate scenario data before loading.
- Update README and runbook instructions.

Exit criteria:

- A user can switch demo scenarios without code changes.
- Data files remain understandable and editable.
- Scenario behavior is repeatable for stakeholder demos.

## Phase 4: Backend Domain Model

Objective: move from demo-oriented endpoints toward a durable backend model.

Status: Complete. Phases 4.1–4.4 completed on 2026-08-13, including persistence and domain contracts, service-layer boundaries, versioned migrations, centralized structured errors, request correlation, and expanded contract and failure-path tests.

Scope:

- Define persistent entities for incidents, crews, assignments, recommendations, decisions, audit events, and scenario metadata.
- Replace hard-coded demo data paths with service-layer access patterns.
- Add validation boundaries using Pydantic models.
- Add database migration approach.
- Add structured error responses.
- Add API tests for core endpoints.

Exit criteria:

- Backend business objects are explicit.
- API contracts are stable enough for frontend development.
- Data persistence is testable.

## Phase 5: Recommendation and Optimization Engine

Objective: make recommendation generation explainable, testable, and configurable.

Status: Complete. Phases 5.1–5.6 completed on 2026-08-16: versioned scoring policy, configurable incident prioritization, blocking crew feasibility, a backward-compatible nested explanation contract, replaceable-engine contract coverage, and manifested-scenario/edge-case evaluation evidence. SME review is documented as a follow-up review activity.

Scope:

- Implement scoring factors for priority, criticality, crew skill, availability, travel, and restoration impact.
- Separate hard constraints from soft scoring factors.
- Add explanation payloads for recommendation output.
- Add confidence and uncertainty handling.
- Add scenario-based validation tests.
- Prepare the interface for future OR-Tools or advanced optimization support.

Exit criteria:

- Recommendations are deterministic for known test scenarios.
- Explanation factors are visible and API-backed.
- Constraints and assumptions are documented.
- Recommendation output can be reviewed by dispatch SMEs.

## Phase 6: Frontend Workflow Maturity

Objective: improve the dispatcher experience from demo shell to operational workflow.

Status: In progress. Phases 6.1–6.4 completed on 2026-08-16: scenario refreshes now show explicit loading/progress feedback, recommendation panels avoid transient empty states, incident queues support shared search, severity/region filters, sorting, and pagination, Crew Board cards support search, filters, sorting, pagination, and crew-ID visibility, read-only incident and crew details support assignment cross-navigation, and recommendation panels compare ranked alternatives with operational tradeoffs. Accessibility and broader tests remain.

Scope:

- Refine navigation and page hierarchy.
- Improve incident queue filtering and sorting.
- Add recommendation comparison views.
- Add crew detail and incident detail interactions.
- Add decision history.
- Add scenario and storm-mode controls.
- Improve accessibility and keyboard handling.
- Add frontend workflow tests.

Exit criteria:

- Primary dispatcher workflows can be completed without dead controls.
- Recommendation state is clear.
- UI behavior supports repeated operational use.

## Phase 7: Enterprise Integration Adapters

Objective: prepare for controlled integration with utility systems.

Status: Pending.

Scope:

- Define adapter interfaces for OMS, GIS, SCADA/DMS, crew management, and weather data.
- Implement mock adapters for local and integration testing.
- Add contract tests.
- Add freshness, source, and quality metadata.
- Add integration failure handling.
- Keep control-system boundaries read-only unless formally approved.

Exit criteria:

- Integration boundaries are explicit.
- Mock and real adapters can share contracts.
- The system can identify stale or degraded source data.

## Phase 8: Security, IAM, and Audit

Objective: add enterprise controls required for pilot readiness.

Status: Pending, with local POC decision-audit persistence already implemented.

Scope:

- Add authentication.
- Add role-based authorization.
- Implement audit event capture.
- Protect sensitive configuration.
- Add structured access controls for dispatch actions.
- Review threat model and security gaps.
- Add security tests and dependency scanning.

Exit criteria:

- User identity is associated with operational actions.
- Dispatch decisions are auditable.
- Access is role-controlled.
- Security limitations are documented.

## Phase 9: Observability and Deployment

Objective: make the system deployable and supportable beyond a local laptop.

Status: Pending, with basic health, CI, Docker, and local runbook foundations already present.

Scope:

- Add structured logging.
- Add health and readiness checks.
- Add metrics for API latency, recommendation latency, data freshness, and errors.
- Add deployment configuration.
- Harden Docker configuration.
- Establish environment configuration patterns.
- Add operational runbooks.

Exit criteria:

- Operators can tell whether the system is healthy.
- Deployment steps are repeatable.
- Basic troubleshooting does not require source-code knowledge.

## Phase 10: Pilot Readiness

Objective: prepare the application for controlled utility pilot evaluation.

Status: Pending.

Scope:

- Validate workflows with dispatch SMEs.
- Finalize pilot success criteria.
- Complete release checklist.
- Review operational constraints.
- Conduct security and integration readiness reviews.
- Confirm rollback and support procedures.
- Document accepted limitations.

Exit criteria:

- Stakeholders understand what is pilot-ready and what is not.
- Pilot workflows are tested.
- Release, support, and escalation procedures are in place.

## Implementation Checklist and Next Sequence

### Completed Foundation

- [x] Establish the React, FastAPI, synthetic-data, SQLite, CI, and Docker bootstrap.
- [x] Implement Accept, Modify, Defer, and Override with required reasons where applicable.
- [x] Persist scenario-scoped decision events and accepted demo assignments in local SQLite.
- [x] Reflect accepted assignments in incident, crew, assignment, and dashboard state.
- [x] Provide dynamically discovered version-controlled scenarios with manifests and complete CSV inventories, including four canonical regression fixtures.
- [x] Add runtime scenario activation, frontend selection, and a recorded-decision switch warning.
- [x] Validate scenario manifests, CSV schemas, identifiers, references, and crew-assignment consistency.
- [x] Add deterministic recommendation fixtures for all four canonical scenarios.
- [x] Add initial frontend scenario-switch workflow coverage.
- [x] Align product, UX, API, frontend, data, audit, test, implementation, and runbook documentation with Phases 2 and 3.
- [x] Complete the contract-neutral pre-Phase 4 POC usability patch for responsive recommendation layouts, contained tables, and full-width Storm Exceptions.

### Phase 1 Closure

- [x] Confirm local frontend and backend startup paths.
- [x] Add core backend API and scenario tests.
- [x] Add frontend build validation and an initial workflow test.
- [x] Correct known scenario data inconsistencies.
- [x] Document current POC limitations and troubleshooting guidance.
- [x] Complete and record the canonical scenario regression and dynamically discovered scenario browser smoke tests in the runbook workflow.
- [x] Verify useful empty, loading, and error states across every primary page.
- [x] Record new smoke-test findings in `docs/004_POC_Feedback_Log.md` and resolve or defer them explicitly.

### Phase 4: Completed Implementation Phase

- [x] Confirm the persistence boundary between version-controlled scenario data and mutable operational entities.
- [x] Define explicit backend entities for incidents, crews, assignments, recommendations, decisions, audit events, and scenario metadata.
- [x] Introduce service-layer boundaries instead of composing domain state directly in API handlers.
- [x] Add Pydantic request and response models for the core API surface.
- [x] Select and document a database migration approach.
- [x] Add structured domain and validation errors consistently across core endpoints.
- [x] Expand API tests for contracts, persistence, invalid state transitions, and failure responses.
- [x] Update architecture, API, and data documentation for the implemented Phase 4 design.

### Phase 5: Current Implementation Phase

- [x] Phase 5.1: define immutable versioned scoring-policy contracts and classify implemented versus planned factors, blocking constraints, assumptions, and data-quality conditions.
- [x] Phase 5.1: introduce a typed optimization request and replaceable engine protocol consumed by incident and recommendation services.
- [x] Phase 5.1: characterize canonical winners, suitability scores, alternatives, and current stable source-order tie behavior without changing the API contract.
- [x] Phase 5.2: implement configurable incident prioritization with structured factor contributions and explicit domain tie-breakers.
- [x] Phase 5.3: enforce crew feasibility constraints and add transparent internal candidate exclusion and suitability results.
- [x] Phase 5.4: add structured explainability, confidence rationale, assumptions, uncertainty, data-quality warnings, and version metadata.
- [x] Phase 5.5: complete replaceable engine contract tests and document the future advanced-optimization adapter path.
- [x] Phase 5.6: expand scenario and edge-case evaluation, prepare SME review evidence, and close Phase 5 documentation.

### Phase 6: Current Implementation Phase

- [x] Phase 6.1: keep recommendation panels in an explicit loading state during scenario refreshes and prevent transient empty-state messaging.
- [x] Phase 6.1: add large-scenario loading/progress feedback and disable scenario switching while operational data refreshes.
- [x] Phase 6.1: add delayed-response frontend coverage for scenario activation and recommendation loading.
- [x] Phase 6.2: add shared incident queue search, severity/region filters, deterministic sorting, and pagination for large lists.
- [x] Phase 6.2: add frontend coverage for filtering, sorting, pagination, and no-match states.
- [x] Phase 6.3.1: add Crew Board search, status/capability/region/storm-readiness filters, labeled sorting, result summaries, and large-list pagination.
- [ ] Phase 6.3.1 follow-up: add faceted Crew Board filter cascading and remaining-result counts, disable zero-result choices, and preserve active selections (POC-009).
- [x] Phase 6.3.2: display crew IDs beside crew names on Crew Board and Recommendation surfaces.
- [x] Phase 6.3.3: add read-only incident and crew detail interactions with assignment cross-navigation and keyboard-selectable incident rows.
- [x] Phase 6.4: add recommendation comparison and tradeoff presentation.
- [ ] Phase 6.5: improve navigation, accessibility, and broader browser workflow coverage.
- [ ] Phase 6.6: complete Phase 6 evaluation and documentation closeout.

### Later Pending Phases

- [ ] Phase 6: mature dispatcher navigation, filtering, comparison, detail, accessibility, and frontend test coverage.
- [ ] Phase 7: implement enterprise integration adapter contracts, mocks, quality metadata, and failure handling.
- [ ] Phase 8: implement authentication, role authorization, enterprise audit controls, configuration protection, and security tests.
- [ ] Phase 9: add structured logs, readiness, metrics, hardened deployment, environment configuration, and operational support tooling.
- [ ] Phase 10: complete SME validation, pilot success criteria, readiness reviews, release controls, rollback, and support procedures.

The sequence now continues with Phase 6 frontend maturity, Phase 7 integrations, Phase 8 security, Phase 9 operations, and Phase 10 pilot readiness.

## Definition of Done

A work item is complete when:

- User-visible behavior works as intended.
- Relevant tests pass.
- Edge cases and failure states are handled.
- Documentation is updated if behavior, API, data, or architecture changed.
- POC feedback log is updated if the work resolves or creates a known demo issue.
- No unrelated changes are bundled into the commit.

## Delivery Risks

| Risk | Mitigation |
| --- | --- |
| Demo controls outpace real behavior | Tie visible controls to explicit state and audit records |
| Synthetic data hides integration complexity | Add integration metadata and scenario-based validation early |
| Recommendation logic becomes hard to trust | Keep explanations structured and testable |
| Documentation drifts from implementation | Update docs as part of definition of done |
| Security is deferred too long | Add identity, roles, and audit before pilot readiness |
| Optimization becomes too complex too soon | Start with deterministic scoring and add advanced optimization incrementally |

## Documentation Revision Cycle

As the POC reveals new requirements, the team should:

- Record observations in `docs/004_POC_Feedback_Log.md`.
- Triage each item as enhancement, defect, requirement gap, design issue, or documentation issue.
- Implement high-value POC behavior in focused commits.
- Revise affected product, UX, API, data, or architecture documents.
- Close or update the feedback entry with the resulting decision.

## Related Documents

- `docs/004_POC_Feedback_Log.md`
- `docs/100_Product/105_Product_Requirements.md`
- `docs/100_Product/106_Non_Functional_Requirements.md`
- `docs/200_Architecture/202_Solution_Architecture.md`
- `docs/900_Delivery/901_Test_Strategy.md`
- `docs/900_Delivery/903_Release_Management.md`
