# POC Feedback Log

## Purpose

This log captures observations, enhancement ideas, defects, demo issues, and new requirements discovered while using the AI Dispatch Advisor proof-of-concept. It is intended to preserve feedback without disrupting the documentation batch plan.

Items in this log should later be reviewed and converted into requirement updates, backlog items, UX revisions, API changes, architecture decisions, or implementation tasks.

## How to Use This Log

Add one row for each observation. Keep entries concise enough to scan, but specific enough to act on later.

Recommended usage:

- Record feedback as soon as it is noticed.
- Do not try to solve or fully specify every item immediately.
- Use clear categories and priority.
- Link to affected docs, files, or app areas when known.
- Review this log during planned revision cycles.

## Status Definitions

| Status | Meaning |
| --- | --- |
| New | Captured but not reviewed |
| Accepted | Agreed that this should become future work |
| Needs Clarification | Requires more detail before action |
| Converted | Converted into a requirement, backlog item, issue, or task |
| Deferred | Valid but intentionally postponed |
| Closed | Addressed or no longer relevant |

## Category Definitions

| Category | Meaning |
| --- | --- |
| Feature | New product capability or workflow |
| Enhancement | Improvement to an existing capability |
| Defect | Something appears broken or misleading |
| UX | Usability, layout, navigation, accessibility, or interaction feedback |
| Data | Demo data, scenario data, data quality, or data model feedback |
| API | Backend contract, endpoint, or integration behavior |
| AI | Recommendation, optimization, explainability, or Copilot behavior |
| Documentation | Documentation gap, inconsistency, or revision need |
| Demo | POC storytelling, scenario, setup, or presentation improvement |

## Priority Definitions

| Priority | Meaning |
| --- | --- |
| P1 | Important for near-term POC credibility or core workflow |
| P2 | Important but can wait until after the current batch or milestone |
| P3 | Useful improvement or future consideration |

## Feedback Items

| ID | Date | Category | Priority | Area | Observation | Suggested Next Step | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| POC-001 | 2026-08-02 | UX | P1 | Recommendation actions | Accept, Modify, Defer, and Override controls are visible but not yet demo-functional. | Implemented local decision persistence, required reasons for Defer and Override, visible decision status, recent history, and accepted assignment state. | Closed |
| POC-002 | 2026-08-02 | AI | P2 | AI Copilot | Copilot responses are currently keyword-based demo responses, not real AI model output. | Keep advisory boundary clear; later define LLM-backed Copilot architecture and retrieval model. | New |
| POC-003 | 2026-08-10 | UX | P1 | Primary page states | Several primary views could render blank content or show an indefinite recommendation-loading message when data was empty or unavailable. | Added explicit loading, empty, error, and retry states with frontend coverage across the POC workflow. | Closed |
| POC-004 | 2026-08-10 | Documentation | P1 | Scenario smoke testing | The four-scenario smoke-test wording could be interpreted as a product limit after dynamic scenario generation and discovery were added. | Retained the four scenarios as deterministic regression fixtures and added a separate test for every dynamically discovered scenario. | Closed |

## Review Cadence

Review this log:

- After each major documentation batch.
- After each POC feature enhancement.
- Before revising product requirements.
- Before creating implementation backlog or GitHub issues.
- Before stakeholder demos.

## Conversion Guidance

When an item is ready to act on:

- Convert product behavior into `docs/100_Product/105_Product_Requirements.md`.
- Convert workflow changes into `docs/100_Product/104_User_Workflows.md`.
- Convert UX changes into `docs/300_UX/`.
- Convert API changes into `docs/400_Backend_API/`.
- Convert frontend implementation guidance into `docs/500_Frontend/`.
- Convert AI, data, or optimization changes into `docs/600_Data_AI/`.
- Convert delivery work into `docs/900_Delivery/` or GitHub issues.
- Record major decisions in `docs/001_Decision_Log.md`.

## Related Documents

- [Documentation Index](000_Document_Index.md)
- [Documentation Roadmap](002_Documentation_Roadmap.md)
- [Product Requirements](100_Product/105_Product_Requirements.md)
- [Recommendation Experience](300_UX/303_Recommendation_Experience.md)
