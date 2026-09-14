# POC-025 Critical Facility Level Copilot Queries Implementation Plan

## Status

Status: Implemented and validated on 2026-09-14.

Date: 2026-09-12

This plan captures a Copilot capability gap observed after POC-019 level-specific
critical-facility scoring became the default. Before POC-025, the question “What is the breakdown
of Critical Facilities by Level?” routed to the generic critical-facility response. It reported
affected incidents and raw facility priorities such as `critical`, but did not translate, group,
or count those records as Level 1, Level 2, and Level 3.

The implemented deterministic `critical_facility_levels` path uses the complete visible incident
inventory and resolved POC-019/POC-026 incident metadata. It reports highest-level-once
affected-incident counts, separately labeled unique matched facility-record counts, and
unknown/withheld incidents. New result tables use POC-031 headings that identify the evaluated
population, displayed subset, and ordering basis. The existing generic critical-facility route,
API schema, advisory boundary, and scenario data remain unchanged.

## Goal

Allow Ask Copilot to answer critical-facility level questions deterministically from the complete
active scenario while using the same resolved incident-level semantics as POC-019 scoring.

The capability must make a clear distinction between:

- **Affected-incident counts:** each incident is counted once at its highest matched facility
  level, consistent with operational scoring.
- **Facility-record counts:** every matched facility record is counted at its own mapped level, so
  this total may exceed the affected-incident total.
- **Unknown or unresolved impact:** critical-facility incidents with unknown levels or missing
  linkage remain visible as data-quality exceptions and are never counted as no-CF incidents.

## Proposed User Questions

The deterministic handler should support capitalization, punctuation, singular/plural wording,
and common equivalents for at least these requests:

- “What is the breakdown of critical facilities by level?”
- “How many Level 1 critical facilities are affected?”
- “Which incidents affect Level 2 facilities?”
- “Show Level 3 critical-facility incidents.”
- “What critical-facility level applies to this incident?”
- “What level and scoring contribution apply to INC-1001?”
- “Are any critical-facility levels unknown?”

Terms such as `Level One`, `Level Two`, `Level Three`, `L1`, `L2`, `L3`, `tier`, `breakdown`,
and `distribution` should be considered during intent design. The implementation should avoid
matching unrelated uses of words such as `level` or `critical` without critical-facility context.

## Authoritative Semantics

POC-025 must reuse the POC-019 facility-impact result already attached to visible incidents:

- `critical_facility_level`
- `matched_critical_facility_ids`
- `ranking_status`
- `ranking_warning`

The source mapping remains:

| Facility `priority_level` | Operational level | Score contribution |
| --- | ---: | ---: |
| `critical` | Level 1 | `+120` |
| `high` | Level 2 | `+80` |
| `medium` | Level 3 | `+40` |
| blank or unsupported | Unknown | Withheld; no fabricated score |

When multiple facilities match one incident, the incident-level answer must use the highest level
once, exactly as scoring does. The detailed facility-record section may show every matched record
and its individual source level. Copilot must not independently reimplement or reinterpret the
mapping if the shared resolver can supply the result.

## Response Contract

### Scenario-wide breakdown

Return totals first in concise Markdown:

| Applied level | Affected incidents |
| --- | ---: |
| Level 1 | Exact complete-scenario count |
| Level 2 | Exact complete-scenario count |
| Level 3 | Exact complete-scenario count |
| Unknown/withheld | Exact complete-scenario count |

Follow the summary with a bounded incident list containing incident ID, municipality, feeder,
applied level, matched facility IDs, and score contribution. If facility-record totals are useful,
show them in a separate clearly labeled section rather than mixing them with affected-incident
counts.

### One-level filter

For a Level 1, Level 2, or Level 3 request, report the exact affected-incident count first and then
show bounded matching examples. Preserve complete evidence even when the rendered answer is
bounded.

### Selected or explicit incident

Report the applied level, matching facility identities, and applicable scoring contribution. If
the incident has multiple matching facilities, state that scoring uses only the highest level
once. If the incident has no critical-facility impact, say so explicitly.

### Unknown or missing data

Report unknown/missing-link incidents separately with their current warning text and facility IDs
when available. Do not recommend or imply a score for a withheld incident.

## Proposed Backend Design

1. Add level-query detection ahead of the existing generic critical-facility route in
   `CopilotService`.
2. Add a dedicated deterministic response path, such as `critical_facility_levels`, rather than
   sending exact operational counts to the model provider.
3. Use the complete visible incident inventory for critical-facility level questions. The current
   ranked-only inventory excludes withheld unknown-level incidents and is therefore insufficient
   for complete data-quality answers.
4. Continue using ranked incidents for priority and recommendation questions; POC-025 must not
   change ranking selection or the meaning of “focus first.”
5. Correlate resolved matched facility IDs to `CriticalFacilities.csv` records for names, types,
   and individual source levels.
6. Reuse the POC-019 resolver or a shared public mapping helper. Do not maintain a second mapping
   table inside the Copilot service.
7. Preserve `execution_mode=local_query`, active scenario ID, request time, snapshot time, advisory
   safety note, and incident/facility evidence.

The initial implementation should retain the current `POST /api/chat` request and response
schemas. The existing Markdown renderer and evidence envelope can present the proposed result, so
no frontend contract addition is expected unless implementation identifies a concrete need.

## Proposed Frontend Scope

The response requires no new visual component. The current safe Markdown table renderer and
expandable evidence list are sufficient.

For discoverability, replace or supplement the current sample prompt “What critical facilities
are affected?” with “Break down critical facilities by level.” The generic affected-facilities
question must remain supported as typed free-form input.

No new dispatcher action, score-edit control, or Copilot write capability is included.

## Non-Goals

- Changing Level 1/2/3 definitions, mappings, or scoring contributions.
- Modifying incident ranking, score bands, recommendation precedence, or dispatcher overrides.
- Publishing or changing scenario data.
- Asking the model provider to calculate complete operational counts.
- Inferring a facility level from its name or type when `priority_level` is missing or unsupported.
- Combining incident-impact counts and facility-record counts into one ambiguous number.
- Allowing Copilot to execute dispatch or modify an incident, facility, score, or decision.

## Test Plan

### Intent routing

- Level breakdown, exact level, abbreviation, spelled-number, selected-incident, and unknown-level
  variants route to the deterministic level handler.
- Generic “What critical facilities are affected?” behavior remains supported.
- Severity `critical`, incident priority, crew, hazard, and unrelated uses of `level` do not
  misroute.
- The provider is not called for supported critical-facility level questions.

### Data and calculation behavior

- Level 1, Level 2, and Level 3 counts use the complete active scenario.
- A low-severity Level 3 LSE incident is included.
- An incident with several facilities is counted once at the highest applied level.
- Facility-record counts remain separate and include all matched records.
- No-CF incidents are excluded from all level counts.
- Unknown-level and missing-link incidents remain visible in an unknown/withheld category.
- Switching scenarios changes results without retaining prior scenario records.

### API and frontend behavior

- `POST /api/chat` returns `local_query`, the active scenario ID, timestamps, and complete bounded
  evidence without changing the public schema.
- Markdown tables render accessibly and remain usable at supported viewport sizes.
- The optional sample prompt fills the composer and submits through the existing workflow.
- Copilot remains advisory and cannot mutate scoring, ordering, assignments, or decisions.

## Manual Smoke Test

1. Open AI Copilot on `base` and ask for the level breakdown.
2. Confirm the response reports three Level 1 affected incidents—`INC-1001`, `INC-1007`, and
   `INC-1004`—and zero Level 2, Level 3, and unknown incidents for that scenario.
3. Switch to a scenario containing Level 2 and Level 3 records and verify each exact count against
   the incident and facility data.
4. Ask for one level, an explicit incident, and “this incident” after selecting an incident.
5. Exercise a controlled multiple-facility case and confirm the incident is counted once at its
   highest level while all facility records remain visible.
6. Exercise an unknown-level fixture and confirm it appears as withheld with a warning rather than
   disappearing or receiving a score.
7. Confirm the response label is `Local scenario query` and that no dispatcher state changes.

## Acceptance Criteria

- Supported Level 1–3 questions are answered deterministically from the complete active scenario.
- Scenario-wide output gives exact incident counts for Level 1, Level 2, Level 3, and
  unknown/withheld.
- Incident counts use the highest matched level once; facility-record counts are separately
  labeled.
- Selected and explicit incident questions report the resolved level, matched facilities, and
  scoring contribution.
- Unknown and missing-link incidents remain visible with data-quality warnings.
- Existing generic critical-facility, ranking, recommendation, provider, API, and frontend
  behavior remains compatible.
- Automated backend/API/frontend coverage and manual scenario smoke tests pass before POC-025 is
  marked closed.

## Complexity and Risks

Estimated complexity: **small to medium**. The data and resolver already exist; the main work is
intent specificity, complete-inventory handling, response semantics, and regression coverage.

Primary risks are ambiguous wording, accidentally counting facility rows as incidents, duplicating
the Level mapping, and hiding withheld incidents by using ranked-only data. A dedicated local
intent, shared resolution logic, and explicit count labels mitigate these risks.

## Related Documents

- [POC Feedback Log](../004_POC_Feedback_Log.md)
- [AI Copilot Screen Specification](../300_UX/310_Screen_Specifications/317_AI_Copilot.md)
- [Recommendation API](../400_Backend_API/405_Recommendation_API.md)
- [Optimization Engine](../600_Data_AI/602_Optimization_Engine.md)
- [POC-019 Operational Scoring Policy Implementation Plan](912_POC_019_Operational_Scoring_Policy_Implementation_Plan.md)
- [Test Strategy](901_Test_Strategy.md)
