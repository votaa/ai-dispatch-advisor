# POC-019 Operational Critical-Facility Scoring Policy Implementation Plan

## Status and Approval Gate

Status: Implemented, smoke-tested, and approved as the default policy.

Date: 2026-09-12

This plan translated the SME-approved POC-019 evaluation policy into an operational POC
implementation. The owner approved implementation on 2026-09-12. After the focused API/UI smoke
test passed, the owner approved `incident-priority-cf-level-v1` as the default policy on the same
date. The evaluation scenario was not published and existing scenario data was not changed.

Default activation occurred only after the separate, evidence-backed owner approval. The prior
`incident-priority-v1` policy remains available as the immediate rollback selector.

## Problem Statement

The prior `deterministic-scoring-v2` / `incident-priority-v1` policy gives every incident marked
as affecting a critical facility the same `+80` contribution. It cannot distinguish Level 1,
Level 2, and Level 3 facilities, cannot use the highest level when multiple facilities match a
feeder, and does not have an operational response for an unknown facility level.

The approved POC-019 evaluation establishes differentiated contributions, score bands, and
ordering precedence. The implementation must make those rules operational without hiding data,
breaking existing API consumers, changing dispatcher decision semantics, or removing the
current policy as an immediate rollback option.

## Approved Policy Contract

### Critical-facility resolution and contribution

For an incident with `critical_facility=true`, match facilities by the existing `region + feeder`
contract and resolve the contribution as follows:

| Facility `priority_level` | Operational level | Contribution |
| --- | ---: | ---: |
| `critical` | Level 1 | `+120` |
| `high` | Level 2 | `+80` |
| `medium` | Level 3 | `+40` |
| No critical-facility impact | None | `0` |

- When multiple facilities match, retain all matches as evidence but apply only the highest
  operational level once. Contributions are never added per facility.
- Level 3 treatment applies normally to an LSE facility, including low-severity and
  single-customer incidents. Customer count remains an independent additive contribution.
- Incident severity does not determine whether the scoring engine recognizes an otherwise valid
  facility level. The standard scenario generator's high/critical-only impact selection at the
  time of POC-019 was a separate data-generation behavior; POC-026 later replaced it with
  municipality-consistent generated linkage and explicit low-severity Level 3 LSE boundaries.
- If any matched facility has an unrecognized or blank `priority_level`, withhold the incident
  from ranked recommendation selection and surface a data-quality warning. Do not guess a level,
  silently treat it as no CF, or fall back to the legacy `+80` contribution.
- A `critical_facility=true` incident with no matching facility is handled through the same
  defensive withheld-and-warning path, even though scenario validation should reject that data
  before activation.

### Total score and operational bands

The additive score remains:

```text
customers_out // 20
+ resolved critical-facility contribution
+ 60 when a hazard is present
+ age_minutes // 10
+ severity contribution (critical 120, high 80, medium 40, low 10)
```

Assign every numeric total to exactly one inclusive operational band:

| Band | Inclusive score range |
| --- | ---: |
| Band 1 | `0-99` |
| Band 2 | `100-199` |
| Band 3 | `200-299` |
| Band 4 | `300+` |

Negative scores remain invalid through policy validation. Unknown-level incidents do not receive
a numeric score or band while withheld.

### Deterministic ranking order

Rank known, valid incidents using the exact precedence exercised by the approved evaluation:

1. Operational score band, highest first.
2. Hazard presence within the same band, hazardous first even when its numeric score or severity
   is lower.
3. Numeric total score, highest first.
4. Severity when hazard status and total score match: critical, high, medium, then low.
5. Resolved critical-facility level when the preceding values match: Level 1, Level 2, Level 3,
   then no CF.
6. Incident age, oldest first.
7. Customers affected, highest first.
8. Stable incident ID, ascending.

This ordering preserves the approved hazard guard: when hazard status matches, the higher numeric
score retains priority. CF-before-age applies when total score and severity tie; it does not
globally override a higher band or numeric score.

### Withheld incident visibility

Withheld incidents must remain operationally visible; withholding is not deletion or filtering
from the incident inventory.

- Return ranked incidents first and withheld incidents afterward in stable incident-ID order.
- Add backward-compatible optional incident metadata for resolved CF level, ranking status, and a
  bounded data-quality warning. Keep all existing incident fields and endpoints unchanged.
- Exclude withheld incidents from automatic top-incident recommendation selection.
- Reject an explicit optimization request for a withheld incident with a typed conflict response
  such as `incident_ranking_withheld`, including the warning reason and matched facility IDs.
- Display a clear non-blocking warning in the operational UI when the active scenario contains
  withheld incidents. Do not show a fabricated score or ranking position.

## Goals

1. Make all 17 SME-approved controlled comparisons pass through the operational engine.
2. Resolve Level 1, Level 2, and Level 3 contributions deterministically from scenario facility
   records, including multiple-facility and low-severity LSE cases.
3. Keep every incident visible while preventing unknown facility data from silently influencing
   ranked recommendations.
4. Preserve the existing public API fields, dispatcher actions, recorded decisions, and
   recommendation evidence while adding only optional warning metadata.
5. Provide configuration-based activation and one-restart rollback to
   `incident-priority-v1`.

## Non-Goals

- Changing crew feasibility, crew suitability, travel-time, assignment, or recommendation-action
  logic.
- Creating a new `Escalation` action. Escalation remains free text entered as the reason for the
  existing `overridden` action.
- Mutating a score, reordering the queue, or creating an assignment when an override is recorded.
- Reclassifying facility types or introducing event-specific facility levels.
- Modifying the standard scenario generator's 4% facility-record sizing or 8% linked-impact
  selection in this change.
- Publishing `poc-019-cf-full-v2` into `data/scenarios` or overwriting any scenario.
- Claiming production readiness for the broader application. This is an operational POC policy.

## User Stories

- As a dispatcher, I want an incident affecting a higher-level critical facility to receive the
  approved differentiated contribution so that otherwise comparable incidents are ordered
  consistently.
- As a dispatcher, I want all affected facilities retained as evidence while only the highest
  level contributes so that one feeder is not rewarded repeatedly for multiple facility rows.
- As a dispatcher, I want unknown facility levels visibly withheld from automated ranking so that
  incomplete data cannot create false confidence or disappear from operational awareness.
- As an SME, I want the operational results to reproduce the approved POC-019 cases so that the
  implemented policy is traceable to the reviewed evidence.
- As an operator, I want existing Accept, Modify, Defer, and Override behavior preserved so that a
  scoring-policy update does not change dispatch authority or audit semantics.
- As an owner, I want the previous versioned policy available through configuration so that the
  change can be rolled back without modifying scenario data or recorded decisions.

## Proposed Technical Design

### 1. Versioned policy configuration

Extend the policy model with:

- Level-specific CF weights: Level 1 `120`, Level 2 `80`, Level 3 `40`.
- Inclusive score-band definitions with validation for ordered, contiguous, non-overlapping
  coverage starting at zero and ending with an open upper bound.
- Explicit incident ranking rules for band, hazard presence, numeric score, severity, resolved CF
  level, age, customers, and stable ID.
- Data-quality conditions for missing linkage and unknown facility level.

Retain the existing policy object unchanged as `incident-priority-v1`. Add the candidate as a new
version, proposed as:

- `algorithm_version`: `deterministic-scoring-v3`
- `policy_version`: `incident-priority-cf-level-v1`

Select the policy from the allow-listed `AIDA_INCIDENT_POLICY_VERSION` environment setting.
Following approval, omission selects `incident-priority-cf-level-v1`; explicitly selecting
`incident-priority-v1` performs rollback. Unknown configuration values must fail startup with a
clear error rather than silently selecting another policy.

### 2. Typed facility-impact resolution

Introduce an internal resolver that accepts an incident and the active scenario's facility rows
and returns:

- rankable or withheld status;
- resolved operational level;
- matched facility IDs;
- configured contribution; and
- an optional bounded data-quality warning code and message.

The resolver must be deterministic, side-effect free, and shared by queue ranking and individual
recommendation explanation. It must not load files directly or depend on global scenario state.

### 3. Context-aware scoring and ranking

Preserve the existing `OptimizationEngine` method signatures. `IncidentService` resolves the
active scenario's facility context into typed, optional metadata on each incident before passing
it through the engine boundary. The engine therefore remains independent of files, loaders, and
global scenario state, and injected test/future engines remain source-compatible.

Replace chained stable sorts for the new policy with one documented rank-key construction or an
equivalently testable approach. Keep the `incident-priority-v1` path behavior-identical, including
its current tie-breakers.

The critical-facility score contribution should expose the resolved level as evidence while
retaining the existing `critical_facility` factor ID. Existing consumers must continue receiving
the five established factor IDs and integer total for every rankable incident.

### 4. Service and API behavior

Wire `data_loader.critical_facilities` into the incident-ranking service through the service
container. Separate internal methods for:

- all visible incidents;
- ranked/rankable incidents; and
- withheld incidents and warnings.

`GET /api/incidents` and `GET /api/incidents/{incident_id}` must retain all existing fields and
records. Optional additive metadata may identify `critical_facility_level`, `ranking_status`, and
`ranking_warning`. The dashboard must count every active incident, while its priority subset and
default optimization selection use only rankable incidents.

Recommendation explanations must continue reporting algorithm and policy versions. For valid CF
incidents, the existing critical-facility factor evidence should identify the resolved level and
matched facility IDs. Withheld incidents must return the typed conflict response instead of a
recommendation.

### 5. Dispatcher override preservation

Do not change `DecisionService`, decision actions, or persistence unless a regression test exposes
an accidental dependency. Confirm that:

- `overridden` still requires a nonblank reason;
- `Escalation: ...` is accepted as ordinary reason text;
- the original recommendation remains embedded in the decision record;
- no score or queue order is mutated; and
- no assignment is created by an override.

## Expected Implementation Files

| File | Planned responsibility |
| --- | --- |
| `backend/app/optimization/policy.py` | Add validated CF weights, bands, rank precedence, policy registry, and new versions while retaining v1. |
| `backend/app/optimization/contracts.py` | Add the typed facility-resolution contract; preserve existing engine signatures and factor IDs. |
| `backend/app/optimization/critical_facility.py` | New side-effect-free resolver for matching, highest-level-only selection, evidence, and warnings. |
| `backend/app/optimization/deterministic_engine.py` | Apply level-specific scoring, band-aware ranking, and context-aware explanation for the new policy. |
| `backend/app/services/incident_service.py` | Supply facility context and separate visible, rankable, and withheld incident handling. |
| `backend/app/services/recommendation_service.py` | Exclude withheld incidents from automatic selection and reject explicit withheld optimization. |
| `backend/app/services/container.py` | Inject active scenario facility rows and configured policy without global engine/data coupling. |
| `backend/app/domain/models.py` | Add optional, backward-compatible incident resolution and ranking metadata. |
| `backend/app/main.py`, `backend/app/error_contracts.py`, and `backend/app/services/errors.py` | Preserve endpoint contracts and expose the typed withheld conflict path. |
| `frontend/src/types.ts` and `frontend/src/App.tsx` | Consume optional metadata and show withheld warnings without changing dispatcher actions. |
| `docker-compose.yml` and runbook documentation | Declare the allow-listed policy selector and activation/rollback procedure. |
| Optimization, service, API, frontend, and POC-019 tests | Prove policy behavior, compatibility, warnings, and rollback. |

If implementation can preserve warning visibility without adding fields to the public `Incident`
model, that narrower design is preferred, but it must keep incidents visible and warnings
machine-readable. The implementation review must not trade away either requirement merely to
avoid an additive contract.

## Test Plan

### Policy and resolver tests

- Accept exactly the approved Level 1/2/3 weights and band boundaries.
- Reject missing, negative, overlapping, non-contiguous, or ambiguously ordered configuration.
- Map `critical`/`high`/`medium` to Levels 1/2/3.
- Apply the highest known level once across multiple matched facilities.
- Preserve all matched facility IDs as evidence.
- Return zero contribution for a non-CF incident.
- Withhold and warn for blank/unknown levels and missing required linkage.
- Withhold when unknown and known facility rows coexist, matching the approved evaluator.

### Scoring and ranking tests

- Exercise Level 1, Level 2, Level 3, unknown CF, and no-CF controlled pairs.
- Verify low-severity Level 3 LSE incidents at 1, 19, 20, and 100 customers.
- Verify the 19/20 customer boundary with and without Level 3 LSE impact.
- Verify all values immediately below, at, and above the four score-band boundaries.
- Verify same-band hazard precedence and the equal-hazard numeric-score guard.
- Verify severity precedence when band, hazard, and numeric score match.
- Verify Level 1/2/3/no-CF precedence before age when the earlier criteria tie.
- Verify age, customers, and stable ID remain deterministic final criteria.
- Compare operational results with all 17 approved records in
  `poc-019-cf-full-v2/EvaluationCases.csv` and `ExpectedResults.json`.

### Compatibility and regression tests

- Under `incident-priority-v1`, scores, contributions, and order remain byte-for-byte equivalent
  to the current characterized behavior.
- Every existing scenario validates and can be ranked under both selectable policies.
- Existing `/api/incidents`, dashboard, optimize, decision, audit, and Copilot contracts retain
  their required fields and behavior.
- Unknown incidents remain visible but are never selected automatically or assigned a fabricated
  score.
- Accept, Modify, Defer, and Override tests remain green, including the approved Escalation reason
  example.
- Recorded decisions retain the recommendation's original algorithm and policy versions across a
  later policy switch.
- Full backend tests, frontend tests, frontend production build, and `git diff --check` pass.

## Acceptance Criteria

- [x] All 17 approved POC-019 controlled cases pass through the operational engine.
- [x] Level 1/2/3 contributions are exactly `120/80/40` and no-CF contribution is `0`.
- [x] Multiple facilities contribute only the highest level once while retaining all evidence.
- [x] Every numeric score maps to exactly one approved band.
- [x] Ranking follows band, hazard, score, severity, CF level, age, customers, and stable ID in
      the documented order.
- [x] Unknown or missing CF level never receives a guessed contribution or ranked recommendation.
- [x] Withheld incidents remain visible with a machine-readable and operator-visible warning.
- [x] The existing incident fields, endpoints, dispatcher actions, and audit records remain
      compatible.
- [x] Escalation remains reason text under `overridden` and cannot mutate scoring or queue order.
- [x] `incident-priority-v1` remains selectable and reproduces its current results.
- [x] The new policy remained inactive until post-implementation evidence and smoke-test results
      were reviewed and default activation was explicitly approved.

## Implementation Sequence

1. Completed: added policy schema, policy registry, validation, and opt-in configuration selection.
2. Completed: added the typed facility-impact resolver and focused unit tests.
3. Completed: implemented new-policy scoring and explicit configured rank precedence.
4. Completed: wired active scenario facility context through incident and recommendation services.
5. Completed: added withheld visibility, typed API behavior, and the minimal frontend warning presentation.
6. Completed: ran the approved POC-019 evaluation as an operational acceptance oracle.
7. Completed: ran baseline-policy and full application regressions.
8. Completed: reviewed the implementation diff and verification evidence with the owner.
9. Completed: selected `incident-priority-cf-level-v1` for a focused API/UI smoke test; the owner
   reported that the smoke tests passed and then explicitly approved it as the default.

## Rollout Safeguards

- Landed the initial implementation with `incident-priority-v1` selected until smoke-test and
  activation approval completed.
- Refuse unknown policy selectors at startup.
- Record algorithm and policy versions in every new recommendation explanation and persisted
  decision snapshot.
- Validate all active scenario facility linkages before activation.
- Do not rewrite scenarios, historical decisions, or audit events.
- Capture pre-activation ranked-order snapshots for the selected smoke scenario and document
  expected POC-019 changes.
- Treat unexpected withheld incidents in existing scenarios as an activation blocker.

## Implementation Verification

Implementation verification completed on 2026-09-12 before default activation:

- Backend suite: `185 passed`.
- Frontend suite: `43 passed`.
- TypeScript check and Vite production build: passed.
- Docker Compose configuration validation: passed.
- `git diff --check`: passed.
- All 17 approved controlled comparisons matched the operational engine results.
- The corrected `poc-019-cf-full-v2` operational order exactly matched all 1,999 expected ranked
  incident IDs and retained only the single approved unknown-level incident as withheld. The
  original `full-v1` package remains preserved and documented as superseded because its evaluator
  misread CSV text `"false"` values.
- All six published scenarios returned the same incident count under both policies and produced
  zero withheld incidents. The opt-in policy changed the top incident only for
  `august-storm-preview`, from `ESD-20260810-0866` to `ESD-20260810-0765`; the other five scenario
  leaders were unchanged.
- An in-process API check with the opt-in selector returned
  `deterministic-scoring-v3` / `incident-priority-cf-level-v1` in recommendation evidence.
- The owner subsequently reported that the focused API/UI smoke tests passed, restored the prior
  default, and committed the gated implementation before separately approving default activation.

## Rollback

1. Set `AIDA_INCIDENT_POLICY_VERSION=incident-priority-v1`.
2. Restart the backend process.
3. Verify health, active scenario, top-ranked incidents, and one recommendation explanation.
4. Confirm new decisions report `incident-priority-v1`; retain earlier decisions with their
   original policy versions.

Rollback requires no data migration, scenario replacement, or decision deletion. Removing code is
not the first rollback action; the versioned policy selector is.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Facility context is unavailable at the current engine boundary | Add typed, injected context; do not let the engine load scenario files. |
| Unknown incidents disappear from operational awareness | Separate visible inventory from rankable selection and test both paths. |
| Stable-sort changes alter unrelated ties | Use explicit rank keys and retain characterized v1 regression snapshots. |
| Existing scenarios reorder more broadly than expected | Produce before/after rank evidence and require activation approval. |
| API additions break strict clients | Keep existing fields/endpoints, use optional additive metadata, and add contract tests. |
| Overrides become mistaken for score changes | Preserve decision semantics and assert no score/queue mutation. |
| Generator severity correlation is mistaken for scoring policy | Keep generator behavior out of scope and test low-severity LSE through the approved fixture. |

## Activation Approval

The owner explicitly approved `incident-priority-cf-level-v1` as the default on 2026-09-12 after
the implementation review and focused smoke tests passed. Omission of
`AIDA_INCIDENT_POLICY_VERSION` now selects it. The prior `incident-priority-v1` policy remains
allow-listed for immediate rollback.
