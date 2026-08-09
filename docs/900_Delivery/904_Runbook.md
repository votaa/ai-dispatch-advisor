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

## Known POC Limitations

Current limitations:

- Some visible controls may be partially implemented until the related workflow is completed.
- Accept, Modify, Defer, and Override actions should be made fully demo-functional as a near-term implementation item.
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
