# Runbook

## Purpose

This runbook provides practical operating steps for running, validating, troubleshooting, and demonstrating the AI Dispatch Advisor. The current focus is the local POC environment. Future versions should expand this runbook for hosted demo, pilot, and production operations.

## Current Operating Mode

The current system is a local POC composed of:

- React frontend.
- FastAPI backend.
- Synthetic CSV demo data.
- Local SQLite database foundation.
- Demo recommendation and Copilot behavior.

The application is not connected to live OMS, GIS, SCADA, crew management, weather, or customer systems.

## Prerequisites

Before running the POC locally, confirm:

- The repository is cloned locally.
- Node.js dependencies have been installed for the frontend.
- Python backend dependencies have been installed.
- The backend service can access local data files.
- No other process is using the frontend or backend ports.

Expected local URLs:

| Service | URL |
| --- | --- |
| Frontend | `http://127.0.0.1:5173/` |
| Backend API docs | `http://127.0.0.1:8000/docs` |

Do not open `frontend/index.html` directly with a `file://` URL. The Vite development server must serve the frontend.

## Start the Application

Start the backend service from the backend project folder using the documented FastAPI startup command.

Start the frontend development server from the frontend project folder using the documented Vite startup command.

Once both services are running, open:

```text
http://127.0.0.1:5173/
```

## Docker Startup

If Docker support is being used, start the application with Docker Compose from the repository root.

Expected result:

- Frontend container starts.
- Backend container starts.
- Local application is reachable through the configured ports.
- API endpoints respond with demo data.

Docker support should be treated as a convenience for the POC until environment configuration, secrets, health checks, and deployment targets are hardened.

## Health Checks

Basic local validation:

- Frontend home page loads.
- Navigation between dashboard, dispatch, incidents, crews, scenario, storm mode, and Copilot works.
- Backend API documentation page loads.
- Incident endpoint returns demo incidents.
- Crew endpoint returns demo crews.
- Assignment endpoint returns demo assignments.
- Dashboard endpoint returns summary data.
- Recommendation endpoint returns a demo recommendation.

If any check fails, use the troubleshooting section below.

## POC Demo Checklist

Before a stakeholder demo:

- Confirm the frontend and backend are both running.
- Confirm the browser is using `http://127.0.0.1:5173/`.
- Refresh the dashboard and confirm outage totals display.
- Use the scenario selector to activate the intended demo scenario and confirm the dashboard totals and active label update.
- If the current scenario has recorded dispatch decisions, confirm that the selector warns before switching and that canceling leaves the current scenario active.
- Open the dispatch view and confirm incidents and recommendations display.
- Open the crew board and confirm crew data displays.
- Open storm mode if that scenario is part of the demo.
- Open Copilot and confirm it responds to a simple advisory prompt.
- Review `docs/004_POC_Feedback_Log.md` for known gaps before presenting functionality as complete.

## Canonical Scenario Regression Test

The four canonical scenarios below are deterministic regression fixtures. They provide stable expected results but do not limit how many scenarios the application supports. Use a fresh local decision database, or account for previously accepted demo assignments when comparing crew counts. Activate each canonical scenario from the frontend selector and confirm:

| Scenario | Active Incidents | Customers Out | Expected Highest-Priority Result |
| --- | ---: | ---: | --- |
| Base Operations | 8 | 8,915 | `INC-1001` recommends `CR-01` |
| Major Storm | 10 | 20,300 | `STM-2001` recommends `SC-06` |
| Crew Shortage | 7 | 7,370 | `CRS-3001` returns Defer and escalate with no available crew |
| Critical Facility | 6 | 3,380 | `CFI-4001` recommends `FC-01` |

For every canonical scenario:

- Confirm the active label, dashboard totals, incident prefixes, and crew board change together.
- Record any discrepancy in `docs/004_POC_Feedback_Log.md`.

## Discovered Scenario Smoke Test

The application discovers valid scenario folders dynamically. It is not limited to the four canonical regression fixtures.

1. Call `GET /api/scenarios` and note every returned scenario.
2. Confirm every returned scenario appears once in the frontend selector.
3. Activate each returned scenario from the selector.
4. Confirm the selected label, dashboard scenario, incident identifiers, totals, crew board, and recommendation refresh together without a backend or browser error.
5. For non-canonical generated scenarios, compare displayed totals with their API responses rather than the canonical table above.
6. Record any discrepancy in `docs/004_POC_Feedback_Log.md`.

## Representative Decision-Isolation Check

Decision persistence and isolation need one representative browser path rather than a repeated decision in every scenario:

1. Start with a fresh local decision database.
2. Activate Base Operations and record a Defer decision with a reason.
3. Switch to Major Storm and confirm the Base Operations decision is not displayed.
4. Switch back to Base Operations and confirm its decision history is restored.
5. Record any discrepancy in `docs/004_POC_Feedback_Log.md`.

The backend suite also verifies scenario-isolated decision and accepted-assignment persistence automatically.

## Loading, Empty, and Error-State Verification

Run the frontend test suite with `npm test`. The Phase 1 suite verifies:

- Purposeful loading messages for Dashboard, Dispatch, Incidents, Crew Board, Storm Mode, and Scenario.
- Explicit empty messages for priority incidents, dispatch incidents, incident lists, crews, storm exceptions, and recommendations.
- A backend-unavailable message with a connection retry.
- A recommendation-specific failure message with a recommendation retry.
- Scenario-activation failure feedback that preserves the current selection.
- Copilot's initial guidance, in-progress label, and inline failure response.

## Phase 1 Closeout Verification Record

Verification completed on 2026-08-10 using local frontend and backend processes with an isolated, fresh SQLite decision database.

| Check | Result |
| --- | --- |
| Backend suite | Pass: 33 tests |
| Frontend suite | Pass: 8 tests |
| Frontend production build | Pass |
| Canonical regression | Pass: all four expected incident counts, customer totals, top incident identifiers, and recommendation outcomes matched |
| Dynamic discovery | Pass: all five current `/api/scenarios` results appeared once in the selector and activated without error |
| Generated scenario | Pass: `august-storm-preview` rendered 2,000 incidents, 500 crews, consistent dashboard totals, and a recommendation |
| Primary-page navigation | Pass: Dashboard, Dispatch, Incidents, Crew Board, Storm Mode, Scenario, and AI Copilot rendered without browser errors |
| Representative decision isolation | Pass: a Base Operations Defer decision was absent in Major Storm and restored after switching back |
| Copilot smoke path | Pass: the default advisory prompt returned a scenario-backed response |
| Responsive POC usability | Pass: Dashboard, Dispatch, Scenario, and Storm layouts remained contained at 1440px, 900px, and 390px; actions changed from 2×2 to stacked at the narrow breakpoint |

The closeout review identified the blank/indefinite frontend states and ambiguous four-scenario wording recorded as `POC-003` and `POC-004`; both were resolved. No additional unresolved Phase 1 findings were observed.

## Known POC Limitations

Current limitations:

- Scenario activation is global to the running POC backend process rather than scoped to an authenticated user session.
- Recommendation decisions use a placeholder dispatcher identity and local SQLite persistence.
- Copilot responses are simple advisory demo responses, not production AI reasoning.
- External integrations are mocked or absent.
- Demo data is synthetic and should not be interpreted as real utility operational data.
- Security and IAM controls are documented but not production-complete.

## Troubleshooting

### Frontend Does Not Load

Symptoms:

- Browser shows a blank page.
- Browser opens a local `file://` path.
- Browser cannot connect to the page.

Actions:

- Use `http://127.0.0.1:5173/`, not the local HTML file path.
- Confirm the frontend development server is running.
- Confirm the frontend port shown in the terminal matches the URL being used.
- Restart the frontend service if the server stopped.

### Backend Does Not Respond

Symptoms:

- API docs page does not open.
- Frontend shows missing data.
- Network requests fail.

Actions:

- Confirm the backend service is running.
- Open `http://127.0.0.1:8000/docs`.
- Restart the backend service.
- Confirm backend dependencies are installed.
- Confirm the backend is running on the expected port.

### Frontend Loads but Data Is Missing

Symptoms:

- Dashboard cards are empty.
- Incident or crew lists do not populate.
- Recommendation panel does not show data.

Actions:

- Confirm backend is running.
- Confirm frontend is configured to call the correct backend URL.
- Confirm demo data files exist.
- Confirm the API endpoints return data directly.
- Check whether a recent data file edit introduced missing columns or invalid values.

### Demo Data Looks Wrong

Symptoms:

- Counts do not match the intended scenario.
- Incident statuses appear inconsistent.
- Crew assignments appear unrealistic.

Actions:

- Confirm the intended scenario is selected in the frontend header.
- Review the relevant CSV files.
- Confirm required columns were preserved.
- Check that identifiers match across incident, crew, assignment, topology, and critical facility data.
- Reload or restart the application if data is loaded at startup.
- Record scenario issues in `docs/004_POC_Feedback_Log.md`.

### Recommendation Behavior Looks Unexpected

Symptoms:

- Recommendation priority seems wrong.
- Recommended crew does not appear suitable.
- Explanation does not support the recommendation.

Actions:

- Confirm the scenario data is internally consistent.
- Review incident priority, crew skills, availability, location, and critical facility flags.
- Compare the behavior to the recommendation and optimization documentation.
- Record the issue in the POC feedback log if the behavior needs implementation or documentation review.

### Copilot Response Does Not Vary Enough

Symptoms:

- Copilot returns generic advisory text.
- Response does not meaningfully address the typed prompt.

Actions:

- Treat Copilot as a POC-level advisory placeholder unless a stronger implementation has been added.
- Use prompts that match the supported demo behavior.
- Record needed Copilot improvements in the feedback log.

## Shutdown

For local development:

- Stop the frontend development server.
- Stop the backend service.
- Stop Docker Compose if it was used.
- Confirm no background process is still holding the frontend or backend ports.

## Incident Response for Demo Failures

If the POC fails during a demo:

- State that the issue is with the demo environment, not live utility operations.
- Restart frontend and backend services.
- Fall back to screenshots or documentation walkthroughs if needed.
- Capture the issue in `docs/004_POC_Feedback_Log.md`.
- Create a focused fix commit after the demo rather than making rushed broad changes.

## Future Production Runbook Areas

Before pilot or production, this runbook should be expanded with:

- Environment-specific startup and shutdown steps.
- Deployment procedures.
- Rollback procedures.
- Health check endpoints.
- Monitoring dashboards.
- Alert response procedures.
- Integration outage procedures.
- Data freshness recovery steps.
- Security incident procedures.
- Business continuity mode.
- Support contact model.

## Related Documents

- `README.md`
- `docs/004_POC_Feedback_Log.md`
- `docs/800_Security_Operations/804_Observability.md`
- `docs/800_Security_Operations/805_Deployment_and_Operations.md`
- `docs/800_Security_Operations/806_Business_Continuity.md`
- `docs/900_Delivery/901_Test_Strategy.md`
- `docs/900_Delivery/903_Release_Management.md`
