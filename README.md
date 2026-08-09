# AI Dispatch Advisor

AI Dispatch Advisor is an enterprise software project for AI-assisted electric utility outage dispatch optimization. It helps dispatchers, supervisors, and operations teams evaluate outage events, compare crew assignment options, and act on explainable dispatch recommendations.

The product is designed as a human-in-the-loop decision-support platform. It does not replace dispatcher judgment or existing utility systems of record. Instead, it brings together outage, crew, geospatial, operational, and environmental context so users can make faster, more consistent, and more transparent dispatch decisions.

## Current Status

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

The scenarios represent routine blue-sky operations, a major storm, constrained crew capacity, and simultaneous critical-facility outages. The backend can load a scenario selected through `AIDA_DEMO_SCENARIO` at startup; a future iteration can add runtime API or UI selection.

The manifest format and authoring rules are defined in `docs/600_Data_AI/606_Scenario_Manifest.md`. The current backend does not yet load or validate the manifest.

## Initial API Surface

```text
GET  /health
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

Recommendation actions are POC-grade only. Accept, Modify, Defer, and Override decisions are persisted locally in `database/aida_decisions.db`, including a basic audit history. Accepted recommendations create local demo assignments that update incident, crew, and dashboard state. Defer and Override require a reason, while Modify can include a short note. The local SQLite database is ignored by Git and is not intended as production persistence.

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
