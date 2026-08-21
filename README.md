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

### Generate a multi-snapshot storm timeline

The separate timeline generator creates 1–10 complete sibling scenario folders while leaving the single-snapshot generator and application behavior unchanged. Run it without flags to use an interactive wizard. Every prompt shows its default, and a supplied command-line flag skips the corresponding prompt:

```bash
python scripts/generate_scenario_timeline.py
```

For automation, use `--no-prompt` and provide a scenario ID. This dry run uses the defaults: five snapshots at 12-hour intervals, 500 crews, 2,000 initial incidents, 5% initially assigned incidents, five dual repair/TREE incidents, 92% final recovery, and new incidents totaling 18% of the initial backlog:

```bash
python scripts/generate_scenario_timeline.py \
  --scenario-id august-storm \
  --start-date 2026-08-10 \
  --no-prompt
```

The recovery profiles are `fast` (92%, default), `balanced` (75%), and `severe` (55%). Arrival profiles are `low` (8%), `moderate` (18%, default), and `persistent` (35%). Percentages apply to the initial incident count. Custom profiles accept either decimal shares or whole percentages:

```bash
python scripts/generate_scenario_timeline.py \
  --scenario-id custom-storm \
  --start-date 2026-08-10 \
  --start-time 06:30 \
  --snapshots 7 \
  --hours-apart 8 \
  --incidents 1200 \
  --crews 300 \
  --dual-tree-incidents 3 \
  --recovery-profile custom \
  --recovery-target 85 \
  --arrival-profile custom \
  --new-incident-share 22 \
  --arrival-decay 0.55 \
  --repair-duration-variation 30 \
  --no-prompt
```

The timeline generator is also dry-run-first. It prints the resolved configuration, per-snapshot counts, and sample rows from the first and final snapshots without creating directories. After review, add `--write` to stage and validate the complete batch before publishing it under `data/scenario-previews/`, or use `--output-root` for another isolated destination. If any target already exists, no snapshot is created. A five-snapshot run produces:

```text
data/scenario-previews/
  august-storm_01/
  august-storm_02/
  august-storm_03/
  august-storm_04/
  august-storm_05/
```

Each folder has its own matching `scenario_id`, `scenario.json`, and all seven CSVs. The `_01`–`_10` suffixes are zero-padded so folders sort chronologically. To inspect the sequence in AIDA, copy the complete sibling folders into `data/scenarios/`, refresh the scenario selector, and select them in order. Do not merge their individual CSV files.

Pending incidents progress through `unassigned → assigned → en_route → onsite → energized`. The incident field-work phase is `onsite`; it is never called `active`. The corresponding `Assignments.csv.status` remains `active` throughout every nonterminal incident phase because the current assignment loader recognizes only `active` rows. Crews remain `assigned` while those rows exist. Cleared/completed incidents and inactive assignments are removed from later snapshots, and released crews return to `available` or `off_shift` according to their staggered 16-hours-on/8-hours-rest rotation.

This feature is generator-only. Raw CSVs preserve the detailed operational incident phase, but the current API can display an incident with an active assignment simply as `assigned`. Decisions recorded while one snapshot is selected remain scoped to that snapshot's scenario ID and do not flow into the next folder. Timeline folders are synthetic preview data; production scenarios must be delivered through a controlled deployment process or managed source rather than copied ad hoc from preview output.

The approved design and lifecycle contract are recorded in `docs/900_Delivery/AI_Dispatch_Advisor_Timeline_Generator_Plan.md`.

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

Recommendation actions are POC-grade only. Accept, Modify, Defer, and Override decisions are persisted locally in `database/aida_decisions.db`, including a basic audit history. Decisions and accepted demo assignments are scoped to their scenario so runtime switching does not mix operational state. The backend applies versioned SQL migrations at startup; supported unversioned local databases are baselined and existing legacy rows are preserved under the `base` scenario. Defer and Override require a reason, while Modify can include a short note. The local SQLite database is ignored by Git and is not intended as production persistence.

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
