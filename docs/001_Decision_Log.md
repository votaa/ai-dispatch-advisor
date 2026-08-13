# Decision Log

## Purpose

This decision log records significant product, architecture, technology, security, and delivery decisions for the AI Dispatch Advisor implementation. It is intended to provide traceability for why the system is designed and implemented in a particular way.

Each decision should capture the context, decision, rationale, consequences, and current status. Decisions may be amended, superseded, or retired, but historical entries should not be deleted.

## Status Definitions

| Status | Meaning |
| --- | --- |
| Proposed | Under discussion and not yet accepted |
| Accepted | Approved for implementation |
| Superseded | Replaced by a later decision |
| Deferred | Not decided in the current implementation phase |
| Retired | No longer relevant to the active system |

## Decision Template

```text
## D-###: Decision Title

- Status:
- Date:
- Owners:
- Related Documents:

### Context

### Decision

### Rationale

### Consequences

### Follow-Up Actions
```

## D-001: Use React for the Frontend Application

- Status: Accepted
- Date: 2026-08-02
- Owners: Product engineering, frontend engineering
- Related Documents: `docs/100_Product/101_Project_Charter.md`, `docs/100_Product/102_Product_Vision.md`

### Context

The AI Dispatch Advisor requires a browser-based operational interface for dispatchers, supervisors, and operations users. The interface must support data-dense outage views, maps, crew panels, recommendation explanations, filtering, interaction history, and real-time or near-real-time updates.

### Decision

The frontend application will be implemented using React.

### Rationale

React is suitable for complex enterprise user interfaces with reusable components, stateful interaction, and incremental implementation. It also supports a broad ecosystem for routing, design systems, data fetching, testing, and integration with geospatial and visualization libraries.

### Consequences

- Frontend architecture must define component boundaries, state management conventions, routing, testing, and accessibility practices.
- UX specifications should translate mockups into reusable React component patterns.
- API contracts must be designed to support predictable frontend data loading and refresh behavior.

### Follow-Up Actions

- Define frontend application architecture in `docs/500_Frontend/501_Frontend_Architecture.md`.
- Define component and state management standards in future frontend documentation.

## D-002: Use FastAPI for the Backend Service Layer

- Status: Accepted
- Date: 2026-08-02
- Owners: Backend engineering, solution architecture
- Related Documents: `docs/100_Product/101_Project_Charter.md`

### Context

The system requires backend APIs for outage data, crew data, dispatch recommendations, integration orchestration, authentication context, audit logging, and AI recommendation workflows. The backend must expose clear service boundaries while supporting Python-based optimization and AI components.

### Decision

The backend service layer will be implemented using FastAPI.

### Rationale

FastAPI provides a strong fit for Python-based enterprise APIs, including typed request and response models, OpenAPI generation, asynchronous request handling, and close alignment with Python AI and optimization libraries.

### Consequences

- API models should be defined with explicit schemas and validation.
- OpenAPI documentation should be generated and treated as a reviewable contract.
- Backend code organization must distinguish API routers, domain services, integration clients, optimization services, and persistence layers.

### Follow-Up Actions

- Define backend service design in `docs/400_Backend_API/401_Backend_Service_Design.md`.
- Define API conventions and versioning in `docs/400_Backend_API/402_API_Overview.md`.

## D-003: Provide AI-Assisted Recommendations, Not Fully Autonomous Dispatch

- Status: Accepted
- Date: 2026-08-02
- Owners: Product management, solution architecture, utility operations stakeholders
- Related Documents: `docs/100_Product/102_Product_Vision.md`

### Context

Electric utility outage dispatch is operationally critical and affects public safety, regulatory commitments, service reliability, crew safety, and customer experience. AI can improve prioritization and decision support, but dispatch decisions require human accountability and situational judgment.

### Decision

The system will provide AI-assisted dispatch recommendations and explanations. It will not automatically dispatch crews without human review and approval in the initial implementation phase.

### Rationale

Human-in-the-loop operation improves trust, supports operational accountability, and allows dispatchers to incorporate real-world context that may not be available in source systems. This approach also reduces implementation risk while establishing the foundation for measured automation in later phases.

### Consequences

- The user experience must clearly distinguish recommendations from approved dispatch actions.
- Recommendations must include rationale, confidence, constraints, and relevant tradeoffs.
- The system must preserve user review, override, acceptance, and audit events.

### Follow-Up Actions

- Define recommendation interaction patterns in `docs/300_UX/303_Recommendation_Experience.md`.
- Define audit logging requirements in `docs/800_Security_Operations/803_Audit_Logging.md`.

## D-004: Require Explainability for Dispatch Recommendations

- Status: Accepted
- Date: 2026-08-02
- Owners: AI engineering, product management, operations stakeholders
- Related Documents: `docs/100_Product/102_Product_Vision.md`

### Context

Dispatch users need to understand why the system recommends a crew assignment, restoration sequence, priority change, or resource allocation. Enterprise utility users are unlikely to trust opaque recommendations during high-pressure outage events.

### Decision

Every material dispatch recommendation must include explainability information appropriate for operational users.

### Rationale

Explainability supports trust, regulatory review, operational learning, and safe adoption. It also helps dispatchers identify when a recommendation is based on stale, incomplete, or conflicting data.

### Consequences

- Recommendation responses must include factors, constraints, assumptions, and relevant data inputs.
- The frontend must expose explanations without overwhelming time-sensitive workflows.
- AI and optimization components must produce structured explanation metadata, not only free text.

### Follow-Up Actions

- Define explainability model in `docs/600_Data_AI/604_Explainability_Model.md`.
- Define trust-oriented UX patterns in `docs/300_UX/304_Explainability_and_Trust.md`.

## D-005: Treat OMS, GIS, SCADA, and Crew Systems as Enterprise Integrations

- Status: Accepted
- Date: 2026-08-02
- Owners: Solution architecture, integration engineering
- Related Documents: `docs/100_Product/101_Project_Charter.md`

### Context

The AI Dispatch Advisor depends on operational data from existing utility platforms. These platforms may vary by utility, may expose different interfaces, and may have different latency, reliability, and data ownership characteristics.

### Decision

OMS, GIS, SCADA, and crew or workforce management platforms will be treated as enterprise system integrations with explicit contracts, adapters, error handling, observability, and data quality controls.

### Rationale

Dispatch optimization quality depends on timely and accurate source data. Treating integrations as first-class architecture concerns reduces coupling, improves testability, and makes utility-specific implementation more manageable.

### Consequences

- Integration adapters should isolate vendor-specific protocols and schemas from domain services.
- Data freshness, source confidence, and integration health should be visible to the application.
- The system must handle partial data availability and degraded integration states.

### Follow-Up Actions

- Define integration architecture in `docs/200_Architecture/204_Integration_Architecture.md`.
- Create dedicated integration documents under `docs/700_Integrations/`.

## D-006: Optimize for Human Operational Workflow Before Automation Depth

- Status: Accepted
- Date: 2026-08-02
- Owners: Product management, UX, engineering leadership
- Related Documents: `docs/100_Product/102_Product_Vision.md`

### Context

The system is intended for dispatchers and operations users working under time pressure during outage events. A technically sophisticated recommendation engine will not create value unless its outputs fit naturally into the operational workflow.

### Decision

The initial implementation will prioritize operational usability, recommendation clarity, workflow fit, and auditability before pursuing deep automation.

### Rationale

Enterprise adoption depends on trust and low-friction integration into existing work practices. A focused, usable decision-support experience is more valuable than broad automation that operators cannot confidently evaluate.

### Consequences

- Product requirements should be organized around dispatcher and supervisor workflows.
- AI capabilities should be surfaced as actionable recommendations with clear supporting evidence.
- UI implementation should support fast scanning, comparison, filtering, acceptance, and override.

### Follow-Up Actions

- Define user workflows in `docs/100_Product/104_User_Workflows.md`.
- Map completed UI mockups to functional requirements in future UX documentation.

## D-007: Separate Immutable Scenario Inputs from Mutable Operational State

- Status: Accepted
- Date: 2026-08-13
- Owners: Backend engineering, solution architecture, data engineering
- Related Documents: `docs/400_Backend_API/401_Backend_Service_Design.md`, `docs/600_Data_AI/601_Data_Model.md`, `docs/900_Delivery/902_Implementation_Plan.md`

### Context

The POC loads incidents, crews, baseline assignments, weather, facilities, topology, and repair history from version-controlled scenario files. It also records dispatcher decisions and accepted assignments in SQLite. Phase 4 requires an explicit ownership boundary before service and migration work can proceed without accidentally treating demo fixtures as mutable operational records.

### Decision

For the Phase 4 backend foundation:

- Scenario manifests and CSV files remain immutable, version-controlled inputs.
- Incident, crew, and baseline assignment records remain scenario-loaded projections during the POC; the application does not write changes back to scenario files.
- Recommendation decisions, recommendation audit history, and accepted operational assignments are mutable application-owned records persisted in SQLite and scoped by `scenario_id`.
- API responses may combine immutable scenario inputs with mutable application state through domain services.
- A future integration or database import can replace the scenario input adapter without changing the core domain or API contracts.

### Rationale

This boundary preserves deterministic demos, prevents runtime activity from modifying source fixtures, and establishes clear ownership for audit and decision history. Keeping scenario inputs behind an adapter-style boundary also avoids prematurely migrating synthetic source data into a database before enterprise source-system contracts are defined.

### Consequences

- Scenario activation remains process-local and scenario files remain read-only when mounted through Docker.
- Accepted assignments overlay baseline scenario assignments rather than rewriting them.
- Mutable tables are managed through the versioned migration mechanism defined by `D-008`.
- Service-layer composition must preserve `scenario_id` isolation.
- Incident and crew persistence is deferred until a normalized operational-store or integration requirement justifies it.

### Follow-Up Actions

- Maintain the Phase 4.2 incident, crew, assignment, recommendation, and decision service boundaries.
- Maintain migration history and upgrade tests for application-owned SQLite tables.
- Add repository interfaces so scenario inputs and mutable persistence can evolve independently.
- Revisit the boundary before production source-system integration or multi-user deployment.

## D-008: Use Numbered SQL Migrations for the POC Decision Store

- Status: Accepted
- Date: 2026-08-13
- Owners: Backend engineering, solution architecture
- Related Documents: `docs/400_Backend_API/401_Backend_Service_Design.md`, `docs/600_Data_AI/601_Data_Model.md`, `docs/900_Delivery/902_Implementation_Plan.md`

### Context

The application-owned SQLite store uses Python's direct `sqlite3` interface and currently contains two mutable tables. Runtime `CREATE TABLE` and conditional `ALTER TABLE` statements made schema history implicit, did not record applied versions, and could not detect whether an already-applied migration had changed. Phase 4 requires repeatable fresh-database creation and safe upgrades from existing POC databases.

### Decision

Use immutable, consecutively numbered SQL files under `backend/app/migrations/` with a lightweight Python migration runner. The runner:

- Applies migrations in numeric order within explicit transactions.
- Records version, name, SHA-256 checksum, and application timestamp in `schema_migrations`.
- Validates consecutive history and rejects changed or unknown applied migrations.
- Safely baselines the two supported unversioned POC schemas before applying later migrations.
- Runs during FastAPI startup before the backend begins serving requests.

The initial migrations recreate the actual schema history: decision-store creation, addition of scenario scoping, and addition of query indexes.

### Rationale

The current persistence layer does not use SQLAlchemy, and adding an ORM plus Alembic only to migrate two direct-SQL SQLite tables would add disproportionate complexity. Numbered SQL retains transparent database changes, requires no new runtime dependency, and still provides ordering, integrity checks, transactional application, upgrade tests, and auditable history.

### Consequences

- Applied migration files must never be edited; corrections require a new numbered migration.
- Migration versions must remain consecutive from `001`.
- Startup fails rather than guessing when the existing schema or migration history is unsupported.
- Existing unversioned Phase 2 and Phase 3 databases are adopted without deleting decisions or accepted assignments.
- A future move to SQLAlchemy or a production database may justify Alembic or a platform-managed migration tool.

### Follow-Up Actions

- Add a new migration file for every application-owned schema change.
- Preserve upgrade-path, checksum, transaction, and idempotency tests.
- Add backup and rollback procedures before pilot or production deployment.
