# Identity and Access Management

## Purpose

This document defines the identity and access management direction for the AI Dispatch Advisor. It describes current POC status, target identity provider integration, role model, authorization boundaries, and access control requirements.

## Current Implementation State

The current POC does not implement authentication or authorization. All local UI and API behavior is unauthenticated and intended only for local development and demo use with synthetic data.

No production utility data or integrations should be connected until IAM is implemented and reviewed.

## IAM Goals

Identity and access management should:

- Authenticate users through enterprise identity.
- Enforce role-based access on the backend.
- Associate user identity with recommendation actions and audit events.
- Restrict operational actions to authorized users.
- Separate dispatcher, supervisor, analyst, administrator, and read-only capabilities.
- Support utility security and compliance review.

## Target Identity Provider

The system should integrate with a utility-approved identity provider such as:

- Microsoft Entra ID.
- Okta.
- Ping Identity.
- Other enterprise SSO provider.

Target authentication pattern:

- Browser receives authenticated session or token.
- Frontend sends authenticated requests to backend.
- Backend validates token or session.
- Backend derives roles and permissions from claims or internal role mapping.

## Initial Role Model

| Role | Description |
| --- | --- |
| Dispatcher | Reviews incidents and recommendation actions |
| Supervisor | Reviews operations, escalations, and broader recommendation history |
| Analyst | Reviews historical recommendations, outcomes, and audit data |
| Administrator | Manages configuration, integrations, and user access settings |
| Read-only Reviewer | Views approved dashboards and reports without operational action rights |

## Permission Model

| Capability | Dispatcher | Supervisor | Analyst | Administrator | Read-only |
| --- | --- | --- | --- | --- | --- |
| View dashboard | Yes | Yes | Yes | Yes | Yes |
| View incidents | Yes | Yes | Yes | Yes | Limited |
| View crews | Yes | Yes | Limited | Yes | Limited |
| Generate recommendation | Yes | Yes | Limited | Yes | No |
| Accept recommendation | Yes | Yes | No | No | No |
| Modify recommendation | Yes | Yes | No | No | No |
| Defer recommendation | Yes | Yes | No | No | No |
| Override recommendation | Yes | Yes | No | No | No |
| View audit history | Limited | Yes | Yes | Yes | Limited |
| Configure integrations | No | No | No | Yes | No |

This is an initial model and should be validated with utility stakeholders.

## Backend Authorization Boundary

Authorization must be enforced by the backend. Frontend role-aware navigation is helpful for usability but is not sufficient security.

Backend write operations should verify:

- Authenticated user.
- Required role.
- Required permission.
- Valid request payload.
- Audit event creation.

## User Identity in Audit Events

Audit events should eventually include:

- User identifier.
- Display name or service account identifier when allowed.
- Role at time of action.
- Action type.
- Timestamp.
- Related incident, crew, recommendation, or integration.

## Service Accounts

Service accounts may be needed for:

- OMS adapter.
- GIS adapter.
- SCADA or DMS adapter.
- Crew system adapter.
- Weather provider adapter.
- Background workers.

Service accounts should:

- Use least privilege.
- Rotate credentials.
- Be stored in managed secrets.
- Be distinguishable from human users in audit logs.

## Local Development

Local development may continue without full IAM while using synthetic data. However:

- Local-only behavior must be clearly documented.
- Production-like environments should not disable security by default.
- Mock identity may be introduced for testing role behavior.

## Open Questions

- Which enterprise identity provider will be used first?
- Which roles are required for the first stakeholder demo?
- Which roles can view crew location data?
- Who can approve writeback to OMS or workforce systems?
- What audit identity fields are permitted by policy?

## Related Documents

- [Security Architecture](801_Security_Architecture.md)
- [Audit Logging](803_Audit_Logging.md)
- [Deployment and Operations](805_Deployment_and_Operations.md)

