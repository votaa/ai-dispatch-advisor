# Multi-Snapshot Storm Progression Generator

## Summary

Add a separate timeline generator that reuses the existing Long Island scenario rules without changing the current generator or AIDA application behavior.

A run creates 1–10 complete, sequentially loadable scenario folders:

```text
<scenario-id>_01/
<scenario-id>_02/
...
<scenario-id>_10/
```

Each folder contains `scenario.json` and all seven required CSVs. Deliver the work as a new follow-up commit on current `main`, without rewriting older generator commits.

## Implementation Tasks

### 1. Add the separate generator

- Add `scripts/generate_scenario_timeline.py` as the user-facing entry point.
- Add `backend/app/scenario_timeline_generator.py` for simulation state, lifecycle progression, and validation.
- Reuse the existing scenario generator for snapshot 1 and shared crew, incident, geographic, ID, facility, topology, and repair-history rules.
- Leave the existing single-snapshot generator unchanged.
- Save this approved plan in `docs/900_Delivery/AI_Dispatch_Advisor_Timeline_Generator_Plan.md` before implementation begins.

### 2. Add interactive and command-line configuration

The interactive wizard prompts for all settings and shows defaults. Explicit command-line flags skip their corresponding prompts. Add `--no-prompt` for automated runs.

Preserve existing parameters and add:

- `--snapshots`: 1–10, default `5`.
- `--hours-apart`: positive whole hours, default `12`.
- `--start-time`: local time for snapshot 1, default `08:00`.
- `--recovery-profile`: `fast`, `balanced`, `severe`, or `custom`.
- `--recovery-target`: custom final clearance percentage.
- `--arrival-profile`: `low`, `moderate`, `persistent`, or `custom`.
- `--new-incident-share`: custom total new-incident percentage.
- `--arrival-decay`: default `0.60` per 12 hours, adjusted for the selected interval.
- `--repair-duration-variation`: default `25%`.
- Existing dry-run, preview, seed, counts, facility, date, assignment, output, and write settings.

Profile defaults:

| Profile | Value |
|---|---:|
| Fast recovery—default | 92% of initial backlog cleared by the final snapshot |
| Balanced recovery | 75% |
| Severe recovery | 55% |
| Low new-outage volume | 8% of initial incidents |
| Moderate arrivals—default | 18% |
| Persistent arrivals | 35% |

Custom profiles accept percentages directly. With one snapshot, recovery and arrival progression are skipped.

### 3. Implement deterministic storm evolution

- Generate snapshot 1 using the original rules, including the default 5% incident assignment rate and five dual-TREE incidents.
- Maintain stable incident, crew, and assignment IDs across snapshots.
- Give new incidents an `ESD-YYYYMMDD-XXXX` ID based on simulated arrival date, with independent daily sequences.
- Distribute continuing outages across later intervals using decreasing geometric weights. Effective decay is `0.60^(hours_apart/12)`.
- Advance the initial backlog toward the selected final recovery target using a seeded, smooth cumulative restoration curve.
- Sample job durations from matching historical repair profiles with the configured variation.
- Use this incident lifecycle:

```text
unassigned → assigned → en_route → onsite → energized → cleared/completed
```

- Use `onsite`, not `active`, for the incident’s field-work phase.
- Keep `Assignments.csv.status=active` throughout `assigned`, `en_route`, `onsite`, and `energized` phases because the current AIDA assignment loader only recognizes `active`.
- Keep `Crews.csv.status=assigned` while a crew has an active assignment.
- At clearance, remove the incident and inactive assignment from the next snapshot, release the crew, and update its `current_location` to the completed incident’s municipality.
- Use `available`, `assigned`, and `off_shift` crew states.
- Model every crew on a seeded, staggered 16-hours-on/8-hours-rest rotation.
- Do not start work that cannot reasonably fit within the crew’s remaining shift.
- Continue enforcing regional ID bands, capabilities, one-active-job-per-crew, single-customer low-voltage work, 40-plus-customer line work, wire-hazard responder rules, and repair/TREE pairings.
- Allow TREE work to finish before its paired repair assignment; release the TREE crew while the repair crew continues.
- Recalculate incident ages, ETRs, shift hours, travel estimates, assignments, and crew availability at every snapshot.
- Update weather timestamps and gradually reduce storm intensity with the arrival curve.
- Keep critical facilities and historical repair reference data stable.
- Keep topology stable by assigning later incidents to the sequence’s existing regional feeder inventory.

Because AIDA changes are excluded, cleared/completed jobs do not remain in later `PendingIncidents.csv` files. Earlier snapshots preserve their previous existence. Raw CSVs retain operational phases, although the current API may display incidents with active assignments simply as `assigned`.

### 4. Add protected batch output

- Write sibling folders such as `august-storm_01` through `august-storm_05`.
- Give each folder a matching `scenario_id` and timestamped description.
- Preflight the complete batch before writing.
- If any target folder exists, fail without creating any snapshots.
- Stage and validate the entire batch before publishing it.
- Preserve dry-run-first behavior.
- Show configuration and per-snapshot timestamp, pending, new, cleared, assigned, available, and off-shift counts.
- Preview sample rows from the first and final snapshots.
- Allow the generated sibling folders to be copied into `data/scenarios/` and selected sequentially in AIDA.

## Validation and Tests

Add coverage for:

- Five default snapshots at 12-hour intervals.
- One-snapshot and ten-snapshot boundaries.
- Zero-padded chronological folder ordering.
- Every snapshot passing existing `ScenarioService` validation.
- Deterministic output for identical seeds.
- Queue conservation: previous pending + arrivals − clearances = current pending.
- Stable IDs for surviving incidents and active assignments.
- No incident resurrection after clearance.
- Unique daily incident and assignment sequences across midnight.
- Non-increasing new-incident arrival counts after rounding.
- Default 92% recovery and 18% arrival targets within rounding tolerance.
- All predefined and custom profiles.
- Correct `assigned → en_route → onsite → energized` incident transitions.
- Assignment status remaining `active` during all nonterminal incident phases.
- Crew 16/8 rotations, staggered coverage, release, reassignment, and location changes.
- Regional, capability, voltage, wire-hazard, and TREE-pairing rules after reassignment.
- No crew with multiple active assignments.
- Protected output, existing-folder refusal, dry-run behavior, invalid prompts, and infeasible configurations.
- Date rollover, timezone-aware timestamps, and daylight-saving boundaries.
- Regression coverage proving the original generator remains unchanged.

## Documentation and Delivery

- Add the approved plan to `docs/900_Delivery/AI_Dispatch_Advisor_Timeline_Generator_Plan.md`.
- Update the README with interactive and non-interactive examples, profiles, output layout, loading order, lifecycle behavior, and the generator-only display limitation.
- Explain the distinction between incident status `onsite` and assignment status `active`.
- Document that timeline folders remain synthetic preview data and production scenarios must come from controlled deployment or a managed source.
- Add examples for custom counts, intervals, recovery targets, and arrival profiles.
- Deliver in a new commit:

```text
feat: add multi-snapshot storm progression generator
```

## Assumptions

- “Files” means complete AIDA scenario folders, not individually suffixed CSVs.
- Folder suffixes use `_01`–`_10`.
- Snapshot 1 retains the original 5%-of-incidents assignment rule.
- Incident field work uses `onsite`; assignment records remain `active` for compatibility.
- Completed jobs are removed from later active scenario files.
- No completion-history sidecar is added.
- No backend API, frontend, manifest-schema, or Docker changes are included.
- Infeasible configurations fail with guidance to add crews, extend the timeline, or lower the recovery target.
