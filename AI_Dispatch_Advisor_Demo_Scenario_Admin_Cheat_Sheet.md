# AI Dispatch Advisor Demo Scenario Admin Cheat Sheet

Use this temporary procedure to select the synthetic scenario loaded by the local backend. These commands do not modify repository files.

## Available Scenarios

| Value | Demonstration |
| --- | --- |
| `base` | Routine blue-sky dispatch operations |
| `storm` | Major storm with widespread outages |
| `crew-shortage` | No immediately available crews; defer and escalate |
| `critical-facility` | Multiple priority facility outages |

## Start the Backend with a Scenario

If the backend is already running, stop it with `Ctrl+C`. Then run these commands in the same terminal:

```bash
cd /Users/anthonyvota/Projects/ai-dispatch-advisor/backend

export AIDA_DEMO_SCENARIO=storm
export AIDA_DECISION_DB="/tmp/aida-${AIDA_DEMO_SCENARIO}-validation.db"

./.venv/bin/python -c "from app.data_loader import DEFAULT_SCENARIO; print(DEFAULT_SCENARIO)"
./.venv/bin/uvicorn app.main:app
```

The verification command must print the selected value, such as `storm`, before Uvicorn starts.

Keep this terminal open while using the demo.

## Start the Frontend

In a second terminal:

```bash
cd /Users/anthonyvota/Projects/ai-dispatch-advisor/frontend
npm run dev
```

Open the demo at [http://localhost:5173](http://localhost:5173).

## What the Variables Control

| Variable | Purpose |
| --- | --- |
| `AIDA_DEMO_SCENARIO` | Selects the read-only CSV starting situation from `data/scenarios/<scenario>/`. |
| `AIDA_DECISION_DB` | Selects the SQLite file that stores actions taken during the demo, including decisions, audit history, and accepted assignments. |

In short:

```text
AIDA_DEMO_SCENARIO = starting situation
AIDA_DECISION_DB    = actions taken during the demonstration
```

The `/tmp` database keeps validation decisions separate from the normal local database. The operating system may eventually remove temporary files.

## Switch Scenarios

1. Stop the backend with `Ctrl+C`.
2. Set a different scenario value.
3. Recreate the matching temporary database path.
4. Verify the value.
5. Restart Uvicorn.
6. Refresh the browser. The frontend server can remain running.

Example:

```bash
export AIDA_DEMO_SCENARIO=crew-shortage
export AIDA_DECISION_DB="/tmp/aida-${AIDA_DEMO_SCENARIO}-validation.db"

./.venv/bin/python -c "from app.data_loader import DEFAULT_SCENARIO; print(DEFAULT_SCENARIO)"
./.venv/bin/uvicorn app.main:app
```

## Verify the Loaded Data

- Dashboard API: [http://localhost:8000/api/dashboard](http://localhost:8000/api/dashboard)
- Incident API: [http://localhost:8000/api/incidents](http://localhost:8000/api/incidents)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

Incident prefixes:

| Scenario | Incident Prefix |
| --- | --- |
| `base` | `INC-` |
| `storm` | `STM-` |
| `crew-shortage` | `CRS-` |
| `critical-facility` | `CFI-` |

## Current Limitation

The frontend currently displays `Synthetic scenario: base` as a hard-coded label. Confirm the actual loaded scenario using the incident prefixes or API counts until dynamic scenario selection and labeling are implemented.

## Troubleshooting

- **Still seeing old incidents:** Stop the backend completely, verify the exported value, restart it, and refresh the browser.
- **Port 8000 already in use:** Another backend process is running. Return to its terminal and stop it with `Ctrl+C`.
- **Verification prints `base`:** Re-enter the `export AIDA_DEMO_SCENARIO=...` command in the same terminal used to start Uvicorn.
- **Decisions appear from another test:** Use a different temporary `AIDA_DECISION_DB` filename.
- **Variable spelling:** The exact name is `AIDA_DEMO_SCENARIO`.

Environment variables remain active only in the terminal session where they were exported. Closing the terminal removes the exported settings.
