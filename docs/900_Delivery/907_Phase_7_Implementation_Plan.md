# Phase 7 Enterprise Integration Adapter Plan

## Objective

Introduce controlled, testable boundaries between the current CSV-backed POC and utility enterprise data sources without coupling domain services or the frontend to vendor-specific schemas.

Phase 7 is a production-readiness foundation, not a full production launch. Initial integrations remain read-only. Authentication and authorization, production audit controls, deployment hardening, and pilot acceptance remain in Phases 8–10.

## Entry Gate

Implementation should begin only after the Phase 6 pause and feedback gate has enough evidence to choose a first integration. The entry decision should identify:

- The source domain and business owner.
- The first read-only workflow and its operational value.
- A documented source contract, representative sample payload, or sandbox.
- Freshness, availability, volume, latency, and retention expectations.
- Credential, network, privacy, and operational-data constraints.
- The system of record and behavior when the source is stale or unavailable.

Scenario-generator cleanup and POC feedback collection may proceed before this gate without starting Phase 7 implementation.

## Recommended Work Packages

### Phase 7.0: Integration Discovery and Readiness

- Review POC and SME feedback for integration-dependent needs.
- Inventory candidate OMS, GIS, SCADA/DMS, crew-management, weather, and AMI sources.
- Select one first read-only vertical slice based on value, access, risk, and testability.
- Record ownership, source contract, freshness expectations, failure modes, and security constraints.
- Define an explicit non-goal for writeback until later governance and IAM controls exist.

Exit: the first source and use case are approved and test inputs are available.

### Phase 7.1: Stable Adapter and Metadata Contracts

- Define typed adapter protocols independent of vendor transports and payloads.
- Define normalized domain inputs and source-record identifiers.
- Define provenance, source timestamp, load timestamp, freshness, quality, and health states.
- Define timeout, retry, partial-data, and error semantics.
- Keep vendor fields inside adapter-specific mapping code.

Exit: domain services can consume a source-neutral contract and distinguish current, stale, degraded, unavailable, disabled, and unknown data.

### Phase 7.2: CSV Adapter and Composition Boundary

- Place current scenario CSV access behind the new contracts.
- Configure adapter selection at the application composition boundary.
- Preserve current API and UI behavior while removing direct source assumptions from domain services.
- Document local and test configuration.

Exit: the POC runs through the same adapter boundary intended for enterprise sources, with existing regression behavior preserved.

### Phase 7.3: Mock Adapters and Contract Test Harness

- Provide deterministic mock adapters for healthy, stale, delayed, partial, malformed, and unavailable responses.
- Run a shared contract suite against CSV, mock, and future real adapters.
- Verify mapping, identifiers, timestamps, quality metadata, timeouts, retries, and sanitized errors.
- Add representative volume and delayed-response fixtures.

Exit: any adapter implementation can be evaluated against one reusable behavioral contract.

### Phase 7.4: First Read-Only Integration Vertical Slice

- Implement the selected adapter against an approved sample, sandbox, or test endpoint.
- Normalize one bounded data flow into the existing domain model.
- Preserve the external platform as system of record.
- Add configuration and secret references without storing credentials in source control.
- Validate reconciliation between source records and normalized records.

Exit: one source-backed read-only workflow operates in an integration environment and passes the shared contract suite. The source should be selected at Phase 7.0 rather than assumed in advance.

### Phase 7.5: Health, Freshness, and Degraded Experience

- Add an integration-health service and authorized API representation.
- Propagate freshness and quality metadata where it affects operational context or recommendation confidence.
- Show clear stale, degraded, unavailable, and last-known-data states without exposing sensitive diagnostics.
- Confirm one failed integration does not unnecessarily block unrelated POC workflows.

Exit: users and operators can identify source condition, and recommendation behavior does not silently treat degraded data as current.

### Phase 7.6: Evaluation and Documentation Closeout

- Run adapter contract, API, degradation, performance, and regression suites.
- Exercise recovery from delayed, stale, malformed, and unavailable sources.
- Review threat-model implications and Phase 8 IAM prerequisites.
- Update architecture, API, data, test, runbook, and feedback documentation.
- Record remaining gaps and the Phase 8 entry decision.

Exit: integration boundaries are explicit, the first vertical slice is evidenced, degraded behavior is visible, and no unapproved operational writeback exists.

## Decisions to Make at Phase 7 Start

The team should not choose these by implementation convenience alone:

- First source domain and vendor/platform.
- Polling, event, file, or hybrid ingestion mode.
- Direct read versus cached/persisted normalized data.
- Freshness thresholds by data type.
- Behavior allowed with last-known data.
- Reconciliation and source-record identity rules.
- Integration environment, credentials owner, and support owner.

## Explicit Non-Goals

- Direct SCADA/DMS control.
- Automatic or unaudited dispatch writeback.
- Production credentials in local configuration or source control.
- Vendor schemas exposed to frontend components.
- Replacing enterprise systems of record.
- Claiming production readiness before Phases 8–10.

## Testing Strategy

- Shared adapter contract tests.
- Mapping and schema-drift fixtures.
- Stale, partial, malformed, slow, timeout, and unavailable source cases.
- Source-to-normalized reconciliation tests.
- API contract and backward-compatibility tests.
- Recommendation tests showing how degraded data affects warnings or confidence.
- Frontend tests for freshness and degraded-state messaging.
- Performance checks using representative record counts and update rates.

## Phase 7 Deliverables

- Approved integration decision record for the first source.
- Typed adapter and source-metadata contracts.
- CSV adapter and application composition boundary.
- Deterministic mock adapters and reusable contract suite.
- One bounded read-only enterprise adapter vertical slice.
- Integration health/freshness behavior and operational guidance.
- Phase 7 evaluation record and Phase 8 prerequisites.

## Related Documents

- `docs/200_Architecture/204_Integration_Architecture.md`
- `docs/400_Backend_API/406_Integration_API.md`
- `docs/800_Security_Operations/801_Security_Architecture.md`
- `docs/900_Delivery/901_Test_Strategy.md`
- `docs/900_Delivery/902_Implementation_Plan.md`
- `docs/900_Delivery/906_Phase_6_Closeout.md`

