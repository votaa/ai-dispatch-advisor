# POC-049 Phase 6 — release review

**Status:** Owner approved the six-folder publication on 2026-10-26. The folders were published locally under new IDs, preflight passed, and local Docker browser smoke passed. They are not yet committed or deployed remotely. Owner commit and personal acceptance remain pending; POC-049 remains open.

## Recommendation and boundary

The owner approved publishing the **small historical review set** as six new, versioned scenario folders: one 24-incident single snapshot and a five-step timeline starting with 80 incidents. The set is about 328 KB, is quick to navigate, and collectively exercises all five Copilot ETR categories, Assessing Conditions conversion, and timeline selection guidance. The 2,000-incident timeline remains an isolated performance preview; its five folders total about 2.3 MB and add volume without a new time-state behavior. Existing checked-in scenarios were not replaced or renamed.

These cutoffs are September 28–30, 2026. At the current October 26 clock, all timed ETRs in this set have passed. The set is useful for **Scenario preview at selected cutoff**, historical progression, and deterministic automated tests. It cannot demonstrate a live current-time Due Soon state today. A fresh generated scenario near the actual test time is required for that specific live-clock demonstration. This is a release limitation, not a reason to relabel a historical snapshot as current.

## Published historical set

The six folders are in `data/scenarios/`. They were copied from the validated Phase 2 single and Phase 3 small timeline previews via an isolated versioned candidate at `/private/tmp/poc049-phase6-release-v1/`. Only `scenario.json` identity, display name, description, and timeline ID changed; the seven CSV files in each folder are byte-identical to their source previews. `ScenarioService` preflight passed before and after publication. The default `base` selection was preserved.

| Published scenario ID | Data as of (Eastern) | Active | Arrivals | Clearances | New NULL-to-ETR conversions | Expired | Due Now | Due Soon | Valid Future | Unavailable |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `poc049-single-20260929-v1` | Sep 29, 6 PM | 24 | 24 | 0 | 0 | 6 | 0 | 0 | 12 | 6 |
| `poc049-timeline-20260928-v1_01` | Sep 28, 8 AM | 80 | 80 | 0 | 0 | 0 | 0 | 3 | 37 | 40 |
| `poc049-timeline-20260928-v1_02` | Sep 28, 8 PM | 75 | 7 | 12 | 3 | 16 | 0 | 1 | 24 | 34 |
| `poc049-timeline-20260928-v1_03` | Sep 29, 8 AM | 54 | 4 | 25 | 2 | 24 | 3 | 0 | 6 | 21 |
| `poc049-timeline-20260928-v1_04` | Sep 29, 8 PM | 31 | 2 | 25 | 2 | 16 | 0 | 1 | 5 | 9 |
| `poc049-timeline-20260928-v1_05` | Sep 30, 8 AM | 20 | 1 | 12 | 1 | 12 | 0 | 0 | 3 | 5 |

The five counts in each row sum to its complete active inventory at that row's simulated cutoff. The timeline's unavailable share falls from 50% to 25% as incidents convert, clear, and arrive; absolute future counts decline as the storm resolves. The step 2 `+12h` conversions reach Due Now at step 3. No new arrival is converted in its first snapshot, and a crew recommendation does not change ETR state.

## Release checks completed

- The committed Phase 5 test gate passed: 282 backend tests, 103 frontend tests, and the production frontend build. Phase 5 browser checks covered a single snapshot, a timeline, explicit preview, and future gating.
- `ScenarioService` validated the staged single and five timeline folders, including CSV schemas and temporal metadata. Every staged CSV matched the source preview byte-for-byte.
- An isolated service smoke using the staged IDs and a fixed **Sep 29, 9 PM Eastern** backend clock returned 24 single-snapshot incidents as **7 Expired, 0 Due Now, 1 Due Soon, 10 Valid Future, 6 Unavailable**. Timeline step 4 returned 31 as **16, 1, 0, 5, 9**. Step 1 blocked current-time counts as stale and suggested step 4; step 5 blocked as future and answered only in explicit preview mode.
- The published root now discovers 13 scenarios, including the six new POC-049 IDs exactly once; `base` remains the default. Existing scenario folders were not changed.
- Every file in the six published folders matches the approved staged candidate byte-for-byte. The backend suite passed again after publication (**282 tests**), and `git diff --check` passed.
- `docker compose up --build -d` rebuilt the backend and started both local services. In the browser, the single snapshot showed 24 incidents, the separate cutoff/freshness labels, and an assigned incident with a synthetic creation time and intentional **Assessing Conditions** ETR. Its Copilot preview returned **6 / 0 / 0 / 12 / 6**.
- The published timeline's step 1 blocked a current-time count as stale and offered step 5; its preview returned **0 / 0 / 3 / 37 / 40**. Step 3 preview returned **24 / 3 / 0 / 6 / 21** and step 4 **16 / 0 / 1 / 5 / 9**. Incident `ESD-20260928-0082` in step 4 showed its unchanged September 28 creation time and September 29 timeline assessment conversion provenance.
- Step 5 was correctly labeled the latest eligible timeline snapshot. At the October 26 real clock its current-time answer returned **15 Expired / 0 Due Now / 0 Due Soon / 0 Valid Future / 5 Unavailable** over 20 incidents and disclosed the September 30 cutoff. Switching to legacy `base` blocked a current-time ETR count because its authoritative cutoff is unavailable.

## Owner smoke steps

The local Compose stack was left running after the agent smoke test. Open `http://localhost:5173/` to repeat the checks below. If the stack has stopped, run `docker compose up --build -d` first; the backend mounts `data/scenarios/` read-only.

1. Confirm the six POC-049 names appear in the scenario selector. Existing scenarios, including `base`, should remain available.
2. Select the single snapshot. Confirm **Scenario data as of: 09/29/2026 18:00 EDT** is distinct from **Scenario Last Updated**. Open one intentional NULL incident and confirm **Assessing Conditions**, creation time, source, and frozen age. In Copilot, choose **Scenario preview at selected cutoff** and ask “How many incidents have expired or coming due soon ETRs?” Expect **6 / 0 / 0 / 12 / 6**, total 24.
3. Select timeline step 1, then steps 2–5. Check the incident inventory and cutoff advance, a continuing incident retains its creation time, and a converted incident shows timeline assessment provenance. In Copilot preview, step 1 should return **0 / 0 / 3 / 37 / 40**, step 3 **24 / 3 / 0 / 6 / 21**, and step 4 **16 / 0 / 1 / 5 / 9**.
4. At a real clock later than Sep 30, select step 1 and ask the same question with **Current time**. It must block the older snapshot and offer step 5. Select step 5; its current-time answer will use the real request time and should disclose the old data cutoff. Do not expect near-due ETRs from historical dates.
5. Switch to `base`: its missing authoritative cutoff must block current-time ETR counts. Return to a POC-049 snapshot and confirm scenario selection and incident details remain consistent. Record owner acceptance before marking the POC closed.

The staged candidate remains a temporary comparison copy. The published files under `data/scenarios/` are the reviewable source to commit.
