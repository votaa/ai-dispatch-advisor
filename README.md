# AI Dispatch Advisor

AI Dispatch Advisor is an enterprise software project for AI-assisted electric utility outage dispatch optimization. It helps dispatchers, supervisors, and operations teams evaluate outage events, compare crew assignment options, and act on explainable dispatch recommendations.

The product is designed as a human-in-the-loop decision-support platform. It does not replace dispatcher judgment or existing utility systems of record. Instead, it brings together outage, crew, geospatial, operational, and environmental context so users can make faster, more consistent, and more transparent dispatch decisions.

## Current Status

[![CI](https://github.com/votaa/ai-dispatch-advisor/actions/workflows/ci.yml/badge.svg)](https://github.com/votaa/ai-dispatch-advisor/actions/workflows/ci.yml)

This repository now includes the Developer Bootstrap MVP:

- React + TypeScript + Vite frontend
- FastAPI backend
- Synthetic utility outage demo data
- Initial SQLite schema and database initialization script
- Initial API endpoints for dashboard, incidents, crews, assignments, optimization, and copilot responses
- Demo recommendation action workflow with SQLite-backed decision and audit history
- Docker Compose for local full-stack startup
- GitHub Actions CI for frontend build and backend tests
- Repository documentation under `docs/`

This is a POC foundation, not a production utility dispatch system.

## Local Development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend API:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend app:

```text
http://localhost:5173
```

### Automated Checks

```bash
cd backend
./.venv/bin/python -m pytest

cd ../frontend
npm test
npm run build
```

The backend suite validates scenario manifests and CSV relationships, dynamic discovery, runtime switching, scenario-isolated decisions, generator behavior, and deterministic recommendation fixtures. The frontend suite covers loading, empty, and failure states plus the recorded-decision confirmation workflow when switching scenarios.

### Database Initialization

The first MVP reads directly from CSV scenario files. A local SQLite database can also be created from the sample data:

```bash
python3 scripts/init_db.py
```

This creates:

```text
database/aida.db
```

### Docker Compose

To start the backend and frontend together:

```bash
docker compose up
```

## Demo Data

Synthetic demo data lives under:

```text
data/scenarios/
  base/
  storm/
  crew-shortage/
  critical-facility/
  august-storm-preview/
```

Each scenario contains:

- `scenario.json` (scenario metadata and CSV inventory)
- `PendingIncidents.csv`
- `Crews.csv`
- `Assignments.csv`
- `HistoricalRepairs.csv`
- `Weather.csv`
- `CriticalFacilities.csv`
- `Topology.csv`

The base, storm, crew-shortage, and critical-facility scenarios are the four canonical deterministic regression fixtures. Additional complete scenario folders, including the generated `august-storm-preview`, are discovered dynamically and are not subject to a four-scenario limit. `AIDA_DEMO_SCENARIO` selects the initial scenario at backend startup. The active scenario can then be changed from the frontend selector or through the validated activation API. If the active scenario has recorded dispatch decisions, the frontend asks for confirmation before switching and explains that its decisions remain saved under that scenario.

When running with Docker Compose, `data/scenarios/` is mounted read-only into the backend container. Complete scenario folders added under that directory become discoverable without rebuilding the backend image. Refresh the frontend to reload the scenario selector. The backend can read scenario data but cannot modify or delete the host scenario files through this mount.

The manifest format and authoring rules are defined in `docs/600_Data_AI/606_Scenario_Manifest.md`. The backend validates a manifest and its complete CSV inventory before activating it. Runtime activation is process-local and affects every user of that POC backend instance.

### Generate synthetic Long Island scenarios

The scenario generator is dry-run-first and leaves `data/scenarios/base` protected. This command creates the approved 500-crew and 2,000-incident data in memory and prints sample rows without writing files:

```bash
python scripts/generate_scenario.py \
  --scenario-id august-storm-preview \
  --start-date 2026-08-10
```

After reviewing the preview, add `--write` to create a new folder under `data/scenario-previews/`. The generator refuses to overwrite an existing scenario directory. Use `--output-root` to select another isolated destination.

Use `--crews` and `--incidents` to set the size of each run instead of accepting the default 500 crews and 2,000 incidents:

```bash
python scripts/generate_scenario.py \
  --scenario-id custom-event-preview \
  --start-date 2026-08-10 \
  --crews 300 \
  --incidents 1200
```

The approved crew-type distribution scales proportionally to the requested crew count. Assigned incidents are calculated from `--assignment-rate`, which defaults to `0.05` (5%). Use `--dual-tree-incidents` to specify how many assigned incidents receive an additional TREE crew. For example, 1,200 incidents at the default assignment rate produce 60 assigned incidents; specifying three dual-TREE incidents produces 63 assignment records.

Crew IDs encode the approved operating rules: numeric suffixes `1xxx` through `4xxx` map to Queens-Nassau, Central-Nassau, Western Suffolk, and Eastern Suffolk respectively; unprefixed `5000-5999` and `7000-7999` are internal low-voltage crews; and unprefixed `6000-6999` are internal line crews. The municipality lookup is maintained in `data/generator-lookups/LongIslandMunicipalities.csv`.

By default, 35% of crews start at an approved home facility and the rest use a plain municipality name to represent their last completed job. Adjust that mix with `--start-day-location-rate`. Internal, LKP, WW, and CG crews use the Hewlett, Hicksville, Brentwood, or Riverhead service location for their region; TREE crews use the corresponding Vegetation Staging Area; and MUA/CNTR crews use the configured RDA MUA locations. No generic municipality-based `Staging Area` names are generated.

Each run generates all seven scenario CSVs. `Weather.csv` contains one observation per Long Island operating region. By default, `CriticalFacilities.csv` contains facilities equal to 4% of each region's actual incident count, which produces approximately 80 facilities for a 2,000-incident scenario. Use `--critical-facilities-per-region` to override the percentage with a fixed count for every region; for example, `--critical-facilities-per-region 10` produces 40 facilities. `Topology.csv` creates a substation, switch, and transformer chain for every feeder used by incidents or facilities, and `HistoricalRepairs.csv` provides repair-duration examples for every supported incident type in each region. The generator does not copy these supporting files from `base`, so a generated scenario remains geographically consistent when moved into `data/scenarios/`.

## Initial API Surface

```text
GET  /health
GET  /api/scenarios
GET  /api/scenarios/active
PUT  /api/scenarios/active
GET  /api/dashboard
GET  /api/incidents
GET  /api/incidents/{incident_id}
GET  /api/crews
GET  /api/assignments
GET  /api/weather
GET  /api/critical-facilities
GET  /api/topology
POST /api/optimize
POST /api/recommendation-actions
GET  /api/audit/events
POST /api/chat
```

To activate a validated scenario for the running backend process:

```bash
curl -X PUT http://localhost:8000/api/scenarios/active \
  -H "Content-Type: application/json" \
  -d '{"scenario_id":"storm"}'
```

The active scenario resets to `AIDA_DEMO_SCENARIO` when the backend restarts. Runtime activation is currently global to the single POC backend process rather than scoped to an authenticated user session.

Recommendation actions are POC-grade only. Accept, Modify, Defer, and Override decisions are persisted locally in `database/aida_decisions.db`, including a basic audit history. Decisions and accepted demo assignments are scoped to their scenario so runtime switching does not mix operational state. Existing local rows are migrated to the `base` scenario. Defer and Override require a reason, while Modify can include a short note. The local SQLite database is ignored by Git and is not intended as production persistence.

## Repository Structure

```text
ai-dispatch-advisor/
  backend/
    app/
    tests/
  data/
    scenarios/
      base/
  database/
  docs/
  frontend/
    src/
  scripts/
  .github/
    workflows/
  docker-compose.yml
```

## Product Goals

- Provide a modern operational console for outage dispatch decision support.
- Generate explainable AI-assisted dispatch recommendations.
- Help users compare outage priority, crew suitability, travel time, safety constraints, customer impact, and restoration benefit.
- Support enterprise utility requirements for auditability, security, reliability, observability, and integration readiness.
- Establish a repository-ready implementation using a React frontend, FastAPI backend, AI recommendation engine, database schema, and documented APIs.

## Product Positioning

AI Dispatch Advisor is not intended to be a generic chatbot or a replacement for outage management systems. It is an operational advisor that supports dispatchers with structured recommendations, transparent reasoning, and controlled human approval.

Core product principles:

- Human authority over dispatch actions
- Explainability by default
- Operational workflow fit
- Data transparency
- Actionable recommendations
- Trust through user control
- Enterprise readiness

## Documentation

Start with:

- `docs/000_Document_Index.md`
- `docs/001_Decision_Log.md`
- `docs/002_Documentation_Roadmap.md`
- `docs/100_Product/101_Project_Charter.md`
- `docs/100_Product/102_Product_Vision.md`

## License

License status is not yet finalized. Until a license is added, all rights are reserved by default.
