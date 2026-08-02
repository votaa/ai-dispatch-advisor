# Project Charter

## Project Name

AI Dispatch Advisor

## Project Summary

The AI Dispatch Advisor is an enterprise software system for electric utility outage management. It assists dispatchers, supervisors, and operations teams by analyzing outage events, crew availability, network context, operational constraints, and external conditions to recommend effective dispatch actions.

The system is designed as a human-in-the-loop decision-support platform. It does not replace dispatcher judgment. Instead, it improves decision quality, consistency, situational awareness, and speed during outage response by making recommendations explainable, auditable, and operationally actionable.

## Business Context

Electric utilities manage outage response across complex operational environments. Dispatchers must balance public safety, critical customers, crew availability, travel time, switching constraints, restoration sequencing, weather conditions, regulatory expectations, and customer impact. These decisions often depend on fragmented information across outage management, geospatial, SCADA, weather, and workforce systems.

The AI Dispatch Advisor addresses this challenge by consolidating operational context and presenting prioritized, explainable dispatch recommendations within a purpose-built user experience.

## Problem Statement

Outage dispatch decisions are frequently made under time pressure with incomplete, rapidly changing information. Dispatchers must evaluate many competing priorities and constraints while coordinating crews and maintaining service restoration performance. Existing systems provide important operational data, but they may not provide integrated, explainable recommendations that help users compare dispatch options and understand tradeoffs.

The project will implement a repository-ready system foundation for an AI-assisted dispatch optimization product using a React frontend, FastAPI backend, AI recommendation engine, and enterprise integration architecture.

## Project Objectives

The project has the following objectives:

- Provide a modern dispatch decision-support interface for outage management operations.
- Integrate outage, asset, geospatial, crew, and operational telemetry context into a unified recommendation workflow.
- Generate explainable dispatch recommendations that support human review and approval.
- Support prioritization based on customer impact, critical loads, safety risk, estimated restoration benefit, crew capability, location, and operational constraints.
- Establish a scalable technical foundation using React, FastAPI, and modular backend services.
- Define clear API, data, integration, security, and operational documentation suitable for a GitHub repository.
- Support enterprise governance through auditability, traceability, role-based access, and observable system behavior.

## In Scope

The implementation phase includes:

- Repository-ready Markdown documentation.
- Product charter, vision, requirements, and workflow documentation.
- React frontend architecture and user interface implementation.
- FastAPI backend service architecture and implementation.
- AI recommendation and optimization engine design.
- Explainability model for dispatch recommendations.
- Database schema and domain data model.
- API specifications for frontend and integration use.
- Integration architecture for OMS, GIS, SCADA, weather, and crew management systems.
- Security, audit, observability, and deployment documentation.
- GitHub-ready project assets and engineering conventions.

## Out of Scope for Initial Implementation

The following are out of scope unless explicitly added through later decisions:

- Fully autonomous crew dispatch without human approval.
- Production integration with a specific utility vendor system unless implementation credentials, environments, and contracts are provided.
- Replacement of the utility outage management system of record.
- Replacement of GIS, SCADA, AMI, or workforce management platforms.
- Real-time control of grid devices.
- Final regulatory certification or utility-specific compliance approval.
- Mobile field crew application implementation, unless later added as a defined product module.

## Target Users

Primary users include:

- Distribution dispatchers who evaluate outage events and assign field crews.
- Dispatch supervisors who monitor workload, resource allocation, escalation risk, and restoration progress.
- Storm center coordinators who manage large-scale outage events and mutual assistance resources.
- Operations analysts who review dispatch decisions, restoration performance, and recommendation effectiveness.

Secondary users include:

- Field crew coordinators.
- Reliability and outage performance teams.
- Utility IT administrators.
- System operators and control room stakeholders.
- Compliance, audit, and safety reviewers.

## Key Stakeholders

| Stakeholder Group | Interest |
| --- | --- |
| Dispatch operations | Faster, clearer, safer outage response decisions |
| Field operations | Appropriate crew assignments and realistic work packaging |
| Utility leadership | Improved restoration performance and operational resilience |
| Customer operations | Better customer impact awareness and estimated restoration communication |
| IT and enterprise architecture | Maintainable, secure, integrated system design |
| Cybersecurity | Controlled access, auditability, data protection, and secure integrations |
| Compliance and regulatory teams | Traceable decisions, defensible process, and policy alignment |
| Engineering delivery team | Clear requirements, architecture, and implementation sequence |

## Product Outcomes

The project should produce:

- A documented product and architecture foundation.
- A working React frontend for dispatch decision support.
- A FastAPI backend with well-defined domain services and API contracts.
- An AI recommendation engine that produces explainable dispatch options.
- Data model and database schema for outage, crew, recommendation, audit, and integration entities.
- Integration patterns for utility operational systems.
- Security and operational documentation suitable for enterprise review.

## Success Measures

Success should be evaluated across product, technical, and operational dimensions.

| Dimension | Measure |
| --- | --- |
| User value | Dispatchers can compare recommended actions, understand rationale, and approve or override recommendations |
| Recommendation quality | Recommendations reflect operational constraints, source data, priority rules, and restoration objectives |
| Explainability | Each recommendation provides clear factors, constraints, assumptions, and confidence indicators |
| Architecture quality | Frontend, backend, data, AI, and integration boundaries are clearly defined |
| Integration readiness | OMS, GIS, SCADA, crew, and weather integrations have explicit adapter and contract patterns |
| Security readiness | Roles, audit events, sensitive data handling, and access boundaries are documented |
| Repository readiness | Documentation and project assets are organized for GitHub and future implementation work |

## Constraints

The project must account for the following constraints:

- Utility operations require high availability, traceability, and controlled change management.
- Source system data may be incomplete, delayed, conflicting, or unavailable.
- Dispatch workflows vary across utilities and operating regions.
- Recommendations must remain explainable to operational users.
- Human review and approval are required for dispatch actions in the initial implementation.
- Integrations must be designed for vendor variability and enterprise security controls.
- The user interface must support dense operational information without overwhelming users.

## Assumptions

- The implementation will use React for the frontend.
- The implementation will use FastAPI for backend APIs.
- The AI recommendation engine will operate as an application service or backend component, not as an uncontrolled external black box.
- The system will initially act as a decision-support layer beside existing systems of record.
- Utility-specific integration details will be configurable or adapter-based.
- Completed UI mockups and design decisions will inform the frontend and UX documentation.

## Major Risks

| Risk | Potential Impact | Mitigation |
| --- | --- | --- |
| Poor source data quality | Recommendations may be inaccurate or hard to trust | Track data freshness, source confidence, and missing data indicators |
| Opaque recommendations | Dispatchers may reject or misuse AI output | Require structured explainability for every material recommendation |
| Workflow mismatch | System may slow dispatchers instead of helping them | Ground requirements in dispatcher workflows and mockup validation |
| Integration complexity | Implementation may vary significantly by utility | Use modular adapters and explicit integration contracts |
| Over-automation | Operational accountability and safety concerns may block adoption | Preserve human review and approval in the initial phase |
| Security gaps | Enterprise deployment may be delayed or rejected | Define identity, authorization, audit, and data protection early |

## Governance

Major product, architecture, security, and implementation decisions must be recorded in `docs/001_Decision_Log.md`. Documents should be updated when implementation details materially change the product scope, user workflow, system architecture, data model, integration behavior, or security posture.

## Related Documents

- [Documentation Index](../000_Document_Index.md)
- [Decision Log](../001_Decision_Log.md)
- [Product Vision](102_Product_Vision.md)

