# POC-049 large storm scenario runbook

Use this runbook to create a **new, large five-snapshot synthetic storm** with incident creation times, a configurable initial ETR mix, intentional NULL **Assessing Conditions** ETRs, and optional NULL-to-ETR conversions as the timeline advances. It uses the current `scripts/generate_scenario_timeline.py` CLI. The [POC-049 implementation plan](919_POC_049_Incident_Time_and_ETR_Implementation_Plan.md) defines the time contract; the [Phase 6 release review](920_POC_049_Phase_6_Release_Review.md) shows how a smaller historical set was reviewed and published.

## Choose the scenario clock first

Pick a unique, versioned base ID, an Eastern local date and time for snapshot 1, and the number and spacing of snapshots. With **5 snapshots, 12 elapsed hours apart**, an October 27, 2026 8:00 AM Eastern start produces cutoffs at October 27 8:00 AM and 8:00 PM, October 28 8:00 AM and 8:00 PM, and October 29 8:00 AM. Set `--end-date` to the final local date so new incidents may arrive throughout the sequence. The start/end dates bound **incident creation**, while each snapshot cutoff bounds which incidents and updates are visible at that step. The CLI defaults to five 12-hour steps, but both settings can be changed.

For a **current-time** Copilot ETR question, select the latest timeline snapshot whose cutoff is no later than the actual backend time. A future selected step blocks a current-time count; an older step blocks it once a later step becomes eligible. The user selects each step—the app does not advance automatically. **Scenario preview at selected cutoff** evaluates a historical or future step at its own simulated time. As a fixed scenario ages, its current-time ETR categories change even though incident inventory and stored ETRs remain frozen. No fixed-date fixture will keep Due Soon ETRs indefinitely; generate a new version near the intended live test date when that is the goal.

## Recommended large example

Run from the repository root in Bash or zsh. Replace the example ID, dates, and seed for a later storm; do not reuse an existing ID. This configuration uses **2,000 initial incidents, 500 crews**, fast recovery (92% final clearance target), moderate new arrivals (18% of initial incidents), and a 25% share each for 8-hour, 24-hour, 48-hour, and NULL initial ETRs. The mix applies separately to each **new-arrival cohort**, so later active-inventory percentages can differ.

The baseline `10%@24h` rule converts roughly 10% of continuing, active Assessing Conditions incidents at each transition, assigning an ETR **24 elapsed hours after the destination step cutoff**. Step 2 overrides that with `10%@12h` to create a Due Now example at the next 12-hour step; step 4 uses `20%@24h` for a stronger later assessment. Conversion is synthetic scenario progression, not a crew recommendation or an automatic change in the running app. New arrivals keep their initial ETR state in their first snapshot.

```bash
SCENARIO_ID=poc049-large-20261027-v1
START_DATE=2026-10-27
END_DATE=2026-10-29
SEED=20261027
PREVIEW_ROOT=/private/tmp/aida-poc049-large-preview
mkdir -p "$PREVIEW_ROOT"

scenario_args=(
  --scenario-id "$SCENARIO_ID"
  --start-date "$START_DATE"
  --end-date "$END_DATE"
  --start-time 08:00
  --snapshots 5
  --hours-apart 12
  --incidents 2000
  --crews 500
  --assignment-rate 5
  --dual-tree-incidents 5
  --start-day-location-rate 35
  --recovery-profile fast
  --arrival-profile moderate
  --arrival-decay 0.60
  --repair-duration-variation 25
  --etr-mix '8h=25,24h=25,48h=25,null=25'
  --assessing-conversion '10%@24h'
  --assessing-conversion-overrides '2=10%@12h,4=20%@24h'
  --seed "$SEED"
  --output-root "$PREVIEW_ROOT"
  --preview-rows 3
  --no-prompt
)

backend/.venv/bin/python scripts/generate_scenario_timeline.py "${scenario_args[@]}" \
  > "$PREVIEW_ROOT/$SCENARIO_ID-dry-run.txt"
```

The first command is a **dry run**: it writes only the redirected text report, not scenario folders. Review the resolved configuration, all five cutoffs, arrival and clearance counts, requested versus realized ETR mix, Assessing Conditions pool and conversion counts, all five ETR categories, and example incident IDs. The report's `clock_state` is relative to when the dry run ran and can change later. An intentional warning for step 2 says its `+12h` conversion reaches **Due Now** at the next 12-hour cutoff.

The example command was dry-run validated on 2026-10-26 with no `--write`. At each **simulated cutoff**, it produced this review shape; changing dates or seed requires a fresh review:

| Step | Active | New after step 1 | Cleared | Converted at step | Assessing Conditions | Expired | Due Now | Due Soon | Valid Future |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2,000 | — | 0 | 0 | 500 | 0 | 1 | 55 | 1,444 |
| 2 | 1,877 | 165 | 288 | 42 | 426 | 450 | 1 | 2 | 998 |
| 3 | 1,344 | 99 | 632 | 30 | 291 | 584 | 27 | 2 | 440 |
| 4 | 772 | 60 | 632 | 32 | 144 | 335 | 1 | 5 | 287 |
| 5 | 520 | 36 | 288 | 10 | 99 | 256 | 12 | 5 | 148 |

At each step, **Unavailable equals Assessing Conditions** for this generated sample, and the five ETR categories sum to Active. Future-ETR counts need not rise monotonically: older estimates age and incidents clear. A useful review asks whether enough future, near-due, expired, and still-assessing examples remain at the steps you intend to demonstrate. Adjust parameters and rerun the dry run if the story is not useful; do not silently change output rows to force a desired count.

## Write and validate an isolated preview

After reviewing the dry-run report, run the same arguments with `--write`. The generator stages and preflights the complete batch before creating the five folders under `PREVIEW_ROOT`. It refuses an existing destination; use a new versioned ID or a new empty preview root for another run.

```bash
backend/.venv/bin/python scripts/generate_scenario_timeline.py "${scenario_args[@]}" --write \
  > "$PREVIEW_ROOT/$SCENARIO_ID-write.txt"
```

The expected sibling folders are `${SCENARIO_ID}_01` through `${SCENARIO_ID}_05`. Keep all five complete folders; do not merge their CSVs. For an independent post-write check:

```bash
AIDA_PREVIEW_ROOT="$PREVIEW_ROOT" AIDA_SCENARIO_ID="$SCENARIO_ID" PYTHONPATH=backend \
  backend/.venv/bin/python - <<'PY'
import os
from pathlib import Path
from app.scenario_service import ScenarioService

root = Path(os.environ["AIDA_PREVIEW_ROOT"])
base = os.environ["AIDA_SCENARIO_ID"]
ids = [f"{base}_{step:02}" for step in range(1, 6)]
service = ScenarioService(root, ids[0])
for scenario_id in ids:
    descriptor = service.scenario(scenario_id)
    print(scenario_id, descriptor.temporal.as_of_at.isoformat())
PY
```

Compare the written folders with the dry-run summary: incident totals, creation-time ranges, arrivals/clearances, conversions, five ETR categories, and examples should reconcile. Verify a continuing incident keeps its `created_at`; an intentional NULL stays NULL unless the configured conversion selects it; `etr_updated_at` and `etr_source` identify conversions. The published [Phase 6 review](920_POC_049_Phase_6_Release_Review.md) provides browser smoke examples and a smaller, easier-to-navigate comparison set.

## Publish only after review

An isolated preview is **not** visible to the current Docker app: Compose mounts `data/scenarios/`. After owner review, copy all five validated sibling folders under a new versioned ID into `data/scenarios/` without overwriting or deleting existing scenarios. Preflight the copied folders, rebuild the backend with `docker compose up --build -d`, and verify discovery and behavior in `http://localhost:5173/` before committing the scenario data separately from generator code. Keep `base` as the default unless a separate change is approved.

In the browser, check the **Scenario data as of** label, incident creation time and provenance, an intentional **Assessing Conditions** ETR, a converted ETR with update provenance, and Copilot's **Current time** versus **Scenario preview at selected cutoff** answers. For a future selected step, current-time counts must block; for an older step with a later eligible sibling, the app should offer the latest eligible step. The preview counts should match the generation report at each cutoff. Current-time counts use the actual backend request time and therefore need not match the dry-run's simulated-cutoff counts.

This is a synthetic POC workflow. It does not infer an outage onset, auto-advance the selected snapshot, or change an ETR when a crew recommendation is made. For a one-snapshot version, use the standard generator and its explicit `--as-of-at` contract in the [POC-049 plan](919_POC_049_Incident_Time_and_ETR_Implementation_Plan.md).
