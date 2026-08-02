# AI Dispatch Advisor

AI Dispatch Advisor is an enterprise software project for AI-assisted electric utility outage dispatch optimization. The system is intended to help dispatchers, supervisors, and operations teams evaluate outage events, compare crew assignment options, and act on explainable dispatch recommendations.

The product is designed as a human-in-the-loop decision-support platform. It does not replace dispatcher judgment or existing utility systems of record. Instead, it brings together outage, crew, geospatial, operational, and environmental context so users can make faster, more consistent, and more transparent dispatch decisions.

## Project Goals

- Provide a modern operational console for outage dispatch decision support.
- Generate explainable AI-assisted dispatch recommendations.
- Help users compare outage priority, crew suitability, travel time, safety constraints, customer impact, and restoration benefit.
- Support enterprise utility requirements for auditability, security, reliability, observability, and integration readiness.
- Establish a repository-ready implementation using a React frontend, FastAPI backend, AI recommendation engine, database schema, and documented APIs.

## Planned System Architecture

The implementation is expected to include:

- **Frontend:** React, TypeScript, Vite, routing, operational dashboards, dispatch console, crew board, incident views, scenario comparison, and AI copilot experience.
- **Backend:** FastAPI service layer with typed API contracts, domain services, integration adapters, recommendation endpoints, and audit/event handling.
- **AI and Optimization:** Recommendation engine for outage prioritization, crew matching, dispatch scenario comparison, and structured explainability.
- **Data Layer:** Initial local database and sample utility datasets, evolving toward integration-backed operational data.
- **Integrations:** Adapter-based architecture for OMS, GIS, SCADA, crew/workforce systems, weather data, and other enterprise platforms.
- **Operations:** Documentation and implementation support for testing, observability, deployment, security, and release management.

## Current Status

This repository is in the implementation foundation phase.

Completed planning inputs include:

- Product concept
- System architecture discussions
- Initial design decisions
- Ten UI mockups
- Initial repository documentation batch

The current repository contents begin with documentation artifacts under `docs/`. Application code, sample data, backend services, frontend UI, and developer bootstrap assets will be added in later implementation batches.

## Documentation

The documentation set starts with:

- `docs/000_Document_Index.md`
- `docs/001_Decision_Log.md`
- `docs/100_Product/101_Project_Charter.md`
- `docs/100_Product/102_Product_Vision.md`

The documentation is organized using numeric prefixes so GitHub file browsing preserves the intended reading order.

## Expected Repository Structure

The repository is expected to evolve toward the following structure:

```text
ai-dispatch-advisor/
  docs/
  frontend/
  backend/
  ai/
  optimizer/
  database/
  data/
  scripts/
  tests/
  docker-compose.yml
```

## Development Direction

The next major implementation step is a Developer Bootstrap MVP that makes the project runnable early. The target is to provide a functional application shell with sample data before replacing dummy behavior with real persistence, optimization, and integrations.

Planned early milestones:

1. Add repository documentation foundation.
2. Create runnable React and FastAPI application shell.
3. Add sample outage, crew, assignment, weather, facility, and topology data.
4. Add initial SQLite schema and seed data.
5. Implement first API endpoints for incidents, crews, assignments, dashboard metrics, optimization, and chat.
6. Add CI checks for linting, tests, and builds.
7. Add Docker Compose for local full-stack development.

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

## License

License status is not yet finalized. Until a license is added, all rights are reserved by default.

