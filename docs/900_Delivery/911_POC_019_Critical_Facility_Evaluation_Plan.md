# POC-019 Critical Facility Scoring Evaluation

## Purpose

POC-019 provides an isolated, deterministic sample dataset for dispatcher and SME review of
level-specific critical-facility scoring. It does not change the active scoring engine, publish
an operational scoring policy, or replace an existing scenario.

The checked-in implementation generated a small review package first. The SME approved the
revised sample on 2026-09-12, authorizing generation of the isolated complete evaluation
scenario. Production scoring remains unchanged and requires a separate approval.

## Current and Candidate Policies

The evaluation baseline was the then-active `deterministic-scoring-v2` /
`incident-priority-v1` policy. All critical-facility incidents received the flat `+80`
contribution. The approved `incident-priority-cf-level-v1` policy became the runtime default on
2026-09-12 after implementation and smoke-test approval.

The evaluation candidate uses these SME-approved evaluation values:

| Facility classification | Evaluation level | Candidate contribution |
| --- | ---: | ---: |
| `critical` | 1 | 120 |
| `high` | 2 | 80 |
| `medium` | 3 | 40 |

Candidate scoring and ordering exist only in `poc019_evaluation_dataset.py`. They are not
imported into or used by the application optimization engine.

## Sample Coverage

The sample contains controlled comparisons for:

- Level 1, Level 2, Level 3, unknown CF, and no CF.
- Level 3 LSE incidents with 1, 19, 20, and 100 customers affected.
- The 19-to-20 customer scoring boundary both without a CF and with a Level 3 LSE CF.
- Multiple facilities on one feeder, applying only the highest known level once.
- Evaluation score-band values immediately below, at, and above each provisional threshold.
- Customer-count and score boundaries.
- Same-band hazard precedence over a non-hazardous incident regardless of numeric score or
  severity, with a guard case retaining normal score ordering when hazard status matches.
- Severity precedence when score and hazard status match.
- SME-approved CF-before-age behavior when score and severity tie.
- Dispatcher override, modified-alternative, missing-reason, and Escalation reason examples.

An unknown facility classification is deliberately represented as a data-quality case. The
candidate evaluator withholds a numeric result and reports a warning rather than silently
treating it as Level 3 or no CF.

## Generate the Evaluation

Run a dry preview first:

```bash
backend/.venv/bin/python scripts/generate_poc019_evaluation.py
```

The dry run writes nothing. After reviewing the terminal preview, write an isolated package to
a new output root:

```bash
backend/.venv/bin/python scripts/generate_poc019_evaluation.py \
  --output-root /private/tmp/aida-poc019-sme-review \
  --write
```

The writer refuses to replace an existing dataset directory. Use a new dataset ID for every
revision so prior SME evidence remains intact.

After sample approval, preview and write the complete application-compatible dataset:

```bash
backend/.venv/bin/python scripts/generate_poc019_evaluation.py --scope complete
backend/.venv/bin/python scripts/generate_poc019_evaluation.py \
  --scope complete \
  --output-root data/evaluation-previews \
  --write
```

The corrected `poc-019-cf-full-v2` directory contains 2,000 incidents, 500 available crews,
17 approved controlled comparisons, 29 facilities, application scenario files, baseline and
candidate evidence, score bands, override examples, and a hash manifest. It is intentionally
outside `data/scenarios` and is not automatically discoverable by the running application.

`poc-019-cf-full-v1` remains preserved as historical review evidence. During operational-engine
verification, a background-row parsing defect was found in its expected results: CSV text
`"false"` was treated as truthy when candidate facility levels were resolved. That incorrectly
withheld 1,750 background incidents and awarded a level contribution to some other non-CF rows.
The 17 controlled SME cases used actual booleans and were unaffected. `full-v2` correctly contains
1,999 ranked incidents and one approved unknown-level withheld incident, regenerates the hash
manifest and complete expected ranking, and does not overwrite `full-v1`.

## SME Review Record

The SME recorded `Approve sample`, approved all 17 controlled cases and all 10 policy decisions,
and authorized complete evaluation generation. The approved decisions cover:

1. Whether Levels 1-3 should receive differentiated weights.
2. Whether LSE uses ordinary Level 3 treatment and how affected customer count participates.
3. Whether only the highest facility level applies once on a feeder.
4. How unknown facility levels are handled.
5. Hazard precedence within an operational score band and severity precedence when hazard
   status matches.
6. CF level before age when total score and severity tie.
7. Evaluation score bands of 0-99, 100-199, 200-299, and 300+.
8. Escalation as free-text rationale under the existing `overridden` action, without score
   mutation, automatic queue reordering, or a new GUI/API action.

## Approval Gates

1. Completed: generated and reviewed the dry-run sample.
2. Completed: wrote a versioned sample package to an isolated review location.
3. Completed: revised the sample and obtained approval for all controlled cases.
4. Completed: obtained explicit approval and generated the complete evaluation scenario.
5. Completed: drafted the separately gated operational scoring-policy implementation plan in
   `912_POC_019_Operational_Scoring_Policy_Implementation_Plan.md`.
6. Completed: obtained explicit owner approval and implemented the operational policy behind an
   initial opt-in configuration gate.
7. Completed: focused API/UI smoke tests passed and the owner explicitly approved the new policy
   as the default on 2026-09-12.
8. Always: never overwrite `data/scenarios`, `data/scenario-previews`, or a prior evaluation
   package.

## Verification

Focused validation covers deterministic rendering, required case categories, LSE customer-count
boundaries, highest-level-only behavior, unknown-level warnings, score-band edges, hazard and
severity ordering, CF-before-age evidence, Escalation semantics, application scenario validation,
non-overwriting output, and preservation of the active policy object.
