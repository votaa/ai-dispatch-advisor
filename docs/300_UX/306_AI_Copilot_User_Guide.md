# AI Copilot User Guide and Query Cheat Sheet

## Purpose

Use this guide to ask AI Copilot questions with a clear scope and to determine whether a response
was calculated from the complete active scenario, produced from a bounded set of grounded records,
or returned through the rule-based fallback. AI Copilot is advisory only and does not dispatch
crews or update source systems.

This guide documents the current POC behavior, including the transparency implemented by
POC-030 and POC-031. Example values were verified on 2026-09-13 against the repository's synthetic
`august-storm-preview` scenario. That historical scenario is now retained in the non-discovered
regression archive; use `august-storm-preview-v3` for the current full-scale browser walkthrough.
Scenario data and returned values can change in a later update.

## Quick Query Pattern

For an exact calculation, include four parts when they apply:

> **Action + measure + population + filter**

Examples:

- `How many customers are out across all active incidents?`
- `How many active incidents have critical severity?`
- `How many crews are available in the active scenario?`
- `Show available line crews in Eastern Suffolk.`
- `Which crews are assigned to ESD-20260810-0401?`

Words such as **all**, **total**, and **entire scenario** make the requested scope clear, but wording
alone does not give the language model access to every record. A complete-population statistic is
reliable only when AI Copilot recognizes it as a supported deterministic local query. When that
deterministic query is not supported, AI Copilot returns an explicit limitation instead of a
sample-derived total.

## Read the Response Mode First

The mode label below each answer identifies how the response was produced.

| Visible label | What it means | Appropriate interpretation |
| --- | --- | --- |
| **Local scenario query** | Application code calculated or retrieved supported facts from active-scenario data without calling the LLM. | Use the reported total for the stated population and filters. A displayed table may still be a bounded example subset. |
| **Grounded AI · model** | The LLM summarized only the selected and bounded scenario records supplied to it. | Treat it as a supported narrative about that context, not automatically as complete-population analysis. |
| **Rule-based fallback** | The configured AI provider was unavailable or disabled, so a local fallback response was returned. | Read the warning and rely only on the facts and scope stated in the fallback. |

Also check the displayed **Scenario**, **Snapshot**, request time, warning, and expandable
**Evidence** before acting on a response.

## Complete-Population Calculations

Supported deterministic questions bypass the LLM and evaluate the full population named by the
query. A row limit controls presentation, not the calculation.

### Example: all-incident customer total

**Ask**

> How many customers are out across all active incidents?

**Verified `august-storm-preview` result**

- Mode: **Local scenario query**
- Evaluated population: **2,000 active incidents**
- Exact result: **1,000,332 customers out**
- Displayed details: **10 of 2,000 incidents**
- Evidence: one complete-scenario aggregate record plus the same ten displayed incident examples

All 2,000 visible incidents contribute to the total. In this verified scenario, all incidents are
rankable, so the ten displayed rows are the highest operational-priority incidents returned by the
active deterministic incident policy. They are not random and are not sorted solely by customers
out. In a scenario containing ranking-withheld incidents, the current visible ordering places all
ranked incidents first and then withheld incidents by incident ID. A withheld incident remains part
of the complete customer total and can appear in the displayed ten only when fewer than ten
rankable incidents precede it.

The result heading identifies that ranked subset explicitly:

> **Highest-priority rankable incidents (showing 10 of 2,000)**

### Example: incident severity count

**Ask**

> How many active incidents have a severity of critical?

**Verified `august-storm-preview` result**

- Mode: **Local scenario query**
- Exact result: **229 critical incidents**
- Displayed examples: **10 of 229**
- Example order: highest operational priority among the matching critical incidents

Other supported severity words are `high`, `medium`, and `low`.
Ranking-withheld records are outside this rankable severity calculation and do not appear in its
displayed examples.

### Example: complete crew availability count

**Ask**

> How many crews are available in the active scenario?

**Verified `august-storm-preview` result**

- Mode: **Local scenario query**
- Evaluated population: **500 crews**
- Exact result: **395 available and 105 assigned**

This count does not require a ten-row table. To retrieve matching crew records, ask a `show` or
`which` question and provide useful filters.

## Understanding Ten-Row Result Tables

Ten rows means “ten displayed examples,” not “ten records evaluated.” Read the total and heading
together.

| Result type | Records used for the count or calculation | Which rows are currently displayed |
| --- | --- | --- |
| All-incident customer aggregate | Every visible active incident | First ten in visible order: rankable incidents by deterministic operational priority, then withheld incidents by incident ID |
| Severity count | Every rankable incident in the supported severity scope | First ten matching rankable incidents in deterministic operational-priority order |
| Geography-filtered incidents | Every rankable incident matching the resolved geography | First ten matches in deterministic operational-priority order |
| Crew query | Every crew matching the requested filters | First ten matches in scenario source order; there is no general crew ranking |

For example, `Show available crews` returns **395 matches** in `august-storm-preview` but displays
only ten rows. Those ten crews are deterministic, not random, but they are currently the first ten
available crews in scenario order—not the “best” ten crews. The result heading labels this as:

> **Matching crews in scenario order (showing 10 of 395)**

The summary above the heading labels each applied filter once, for example:

> **30 crews match the requested filters: Status: available · Capability: line · Region: Eastern Suffolk.**

Do not infer a ranking from row position unless the response explicitly says the subset is ordered
by operational priority, feasibility, travel time, or another named criterion.

## When Grounded AI Uses a Bounded Context

Open-ended explanation and briefing questions may use the configured LLM. Examples include:

- `Summarize storm status.`
- `Explain the main operational concerns.`
- `Describe the dispatch tradeoffs for this incident.`

The current grounded context can contain:

- The selected incident and selected crew, when present
- Up to **five ranked incidents**
- The recommendation for a selected incident, when present
- Up to **six crews**
- Up to **eight critical-facility records**
- Up to **four weather records**
- No more than the configured overall context-record limit

This is designed for concise, relevant synthesis. It is not a statistically representative sample
and must not be used to calculate an all-scenario total. The selected incident can also be supplied
separately from the five ranked incidents, so “five ranked incidents” does not necessarily mean
that exactly five unique incident records appear in every prompt.

Each grounded response displays a dynamically derived scope label based on the records actually
supplied after applying the configured limit, for example:

> **Response scope: Bounded grounded context: 1 selected incident + 5 ranked incidents + 1 recommendation + 6 crews + 8 critical-facility records + 4 weather records (25 of 30 record limit used)**

The counts come from the generated context payload and are not hard-coded in UI copy.

## PSEG Long Island Static Reference Queries

Copilot can answer deterministic questions about the approved PSEG Long Island County,
Township, and Village hierarchy and customers-served counts. These answers use an SME-reviewed
static reference and never call KUBRA or the model provider at runtime. Examples include:

- `How many customers are served in Nassau County?`
- `How many customers are served in the Town of Hempstead?`
- `Show the PSEG Long Island hierarchy for Rockaway Peninsula.`
- `Which townships or villages match Calverton?`

Each answer labels the normalized AIDA scope, KUBRA source scope, source timestamp, extraction
timestamp, and freshness state. Ambiguous village names return every matching Township path and
do not silently combine customer counts. Stale reference values remain visible with a warning.

An area outage percentage is available only when Copilot can aggregate every active synthetic
incident into the same approved reference geography and both timestamps are available. The
answer displays the synthetic numerator, static denominator, calculation, timestamps, and a
prominent statement that the result is not a live utility outage percentage. Stale, unavailable,
invalid, zero-denominator, partial-coverage, and missing-timestamp cases refuse the calculation.

## Unsupported Population Calculations

Do not treat a plausible narrative number as a complete-scenario result when:

- The response is labeled **Grounded AI**.
- The requested measure is not stated as a supported deterministic calculation.
- The response does not identify the evaluated population.
- The answer uses phrases such as “based on the provided incidents” or reports missing context.

For example, this request does not identify an aligned geographic scope:

> What percentage of all customers served are without power?

The correct behavior is to request a County, Township, Village, or selected incident rather than
combine an all-scenario synthetic numerator with an unspecified static denominator. Unsupported
all-scope requests state the limitation and suggest an available exact query, such as:

> I cannot calculate the percentage because the request does not identify an aligned geographic
> scope. Try: “What percentage of customers in Melville are affected?”

## Prompt Cheat Sheet

| Goal | Recommended wording | Expected mode and scope |
| --- | --- | --- |
| Total customer impact | `How many customers are out across all active incidents?` | Local scenario query; complete visible incident inventory |
| Static customers served | `How many customers are served in Nassau County?` | Local reference query; approved static County aggregate |
| Mixed-source area percentage | `What percentage of customers in Melville are affected?` | Local calculation; complete aligned synthetic numerator plus current static denominator |
| Reference hierarchy | `Show the PSEG Long Island hierarchy for Rockaway Peninsula.` | Local reference query; source and normalized paths |
| Count incidents by severity | `How many active incidents have critical severity?` | Local scenario query; complete supported severity scope |
| Count available crews | `How many crews are available in the active scenario?` | Local scenario query; complete crew inventory |
| List filtered crews | `Show available line crews in Eastern Suffolk.` | Local scenario query; all matches counted, first ten shown in scenario order |
| Inspect one incident | `What is the outage status of ESD-20260810-0401?` | Selected-incident local response |
| Explain one recommendation | `Why was this crew recommended for the selected incident?` | Local deterministic explanation using the selected recommendation |
| Request a briefing | `Summarize storm status.` | Grounded AI when configured; bounded synthesis context |
| Request an unavailable statistic | Name the measure and complete scope explicitly. | Copilot should disclose the limitation rather than extrapolate from a sample |

## Operator Checklist

Before relying on a Copilot answer:

1. Confirm the active scenario and data snapshot.
2. Read the response mode: local query, grounded AI, or fallback.
3. For a total, confirm that the evaluated population is stated.
4. Treat `showing 10 of N` as a display subset; identify its stated ordering basis.
5. Expand Evidence when you need to inspect supporting records.
6. Do not interpret a grounded subset as an all-scenario total.
7. Remember that every response is advisory and requires operator judgment.
8. Treat customers-served values as static reference data and mixed-source percentages as synthetic POC calculations, not live outage statistics.

## Related POC Items

- **POC-020:** readable local-query Markdown and bounded displays
- **POC-021:** deterministic incident severity counts
- **POC-028:** deterministic all-incident customer aggregates
- **POC-030:** query-scope guidance, dynamic scope labels, and bounded-synthesis disclosure
- **POC-031:** explicit result-subset and ordering headings

See the [POC Feedback Log](../004_POC_Feedback_Log.md) and
[AI Copilot Screen Specification](310_Screen_Specifications/317_AI_Copilot.md) for status and
implementation acceptance details.
