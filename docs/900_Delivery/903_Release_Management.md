# Release Management

## Purpose

This document defines the release management approach for the AI Dispatch Advisor. It describes how changes should move from local development through review, testing, demo readiness, pilot readiness, and eventual production deployment.

## Release Goals

The release process must:

- Keep the application runnable after each release.
- Make release contents clear to product, engineering, and operations stakeholders.
- Separate experimental POC changes from pilot or production commitments.
- Maintain traceability between requirements, code, documentation, tests, and known limitations.
- Support rollback when a release introduces unacceptable behavior.
- Avoid releasing undocumented operational behavior.

## Current Release State

The current project is in POC stage.

Current release characteristics:

- Local development is the primary execution environment.
- Commits are manually created by the project owner.
- GitHub is used as the source repository.
- CI exists as an initial quality gate.
- Docker Compose exists as a local orchestration option.
- Releases are not yet formally tagged, promoted, or deployed.

This is appropriate for the current implementation stage. Formal release controls should increase before pilot or production use.

## Versioning Strategy

Recommended versioning:

| Version Type | Use |
| --- | --- |
| `0.x` | POC and MVP development |
| `0.1.x` | Documentation and bootstrap increments |
| `0.2.x` | Demo-functional dispatch workflows |
| `0.3.x` | Scenario data and persistence maturity |
| `0.4.x` | Recommendation and optimization maturity |
| `0.5.x` | Integration adapter readiness |
| `1.0.0` | First controlled pilot or production candidate, subject to governance approval |

Version numbers should reflect release maturity, not only the number of commits.

## Branching Approach

For the current project stage, a simple branching model is preferred.

Recommended approach:

- `main` holds reviewed, runnable work.
- Short-lived feature branches are used for meaningful changes.
- Documentation batches can be committed directly when reviewed by the owner.
- Functional changes should be committed separately from documentation batches.
- Large features should be split into smaller reviewable increments.

Before pilot readiness, the project may introduce protected branches, pull request requirements, code owners, and required CI checks.

## Commit Hygiene

Each commit should have a clear purpose.

Recommended commit categories:

- Documentation batch.
- Frontend workflow change.
- Backend API change.
- Data model change.
- Demo data scenario change.
- Recommendation logic change.
- Test coverage change.
- Infrastructure or CI change.

Avoid combining unrelated documentation, UI, backend, and infrastructure changes in a single commit unless they are required for one coherent feature.

## Release Types

| Release Type | Description |
| --- | --- |
| Documentation release | Adds or revises repository documentation only |
| POC demo release | Adds visible demo behavior for stakeholder walkthroughs |
| MVP release | Adds working end-to-end functionality with local persistence |
| Integration release | Adds or changes adapter behavior for external systems |
| Pilot release | Candidate for controlled utility evaluation |
| Production release | Operationally approved deployment |
| Hotfix release | Targeted correction for a release-blocking defect |

## Release Checklist

Before creating a release:

- Confirm working tree is clean except intended release changes.
- Confirm frontend builds.
- Confirm backend tests pass.
- Confirm API endpoints required by the demo or release work.
- Confirm known limitations are documented.
- Confirm README and runbook remain accurate.
- Confirm release notes summarize user-visible changes.
- Confirm rollback steps are understood.
- Confirm security and integration limitations are not overstated.

For pilot or production releases, add:

- Security review.
- IAM review.
- Audit logging verification.
- Integration contract review.
- Operational readiness review.
- Business continuity review.
- Stakeholder acceptance.

## CI Gates

The CI pipeline should mature in stages.

POC CI gates:

- Frontend dependency install.
- Frontend build.
- Backend dependency install.
- Backend unit or smoke tests.

MVP CI gates:

- Type checking.
- Linting.
- Backend API tests.
- Frontend component and workflow tests.
- Database migration validation.

Pilot CI gates:

- Security scanning.
- Dependency vulnerability checks.
- Container build checks.
- Integration contract tests.
- Accessibility checks.
- Performance baseline tests.

Production CI gates:

- Release artifact signing where required.
- Deployment approvals.
- Environment promotion checks.
- Rollback validation.

## Release Notes

Release notes should include:

- Release version or identifier.
- Release date.
- Summary of changes.
- User-visible behavior.
- Documentation updates.
- Test evidence.
- Known limitations.
- Upgrade or migration notes.
- Rollback instructions.

For POC releases, known limitations are especially important because stakeholders may otherwise assume demo-visible capabilities are production-ready.

## Environment Promotion

Recommended promotion path:

```text
Local Development
  -> CI Validation
  -> Shared Demo
  -> Integration Test
  -> Pre-Production
  -> Production
```

The current project supports local development and repository-based CI. Later phases should add shared demo and integration test environments.

## Rollback Strategy

Rollback should be simple and documented.

For local POC work:

- Revert to the last known good commit.
- Restart frontend and backend services.
- Reload known-good demo data if needed.

For hosted pilot or production work:

- Redeploy the prior approved release artifact.
- Confirm database compatibility.
- Confirm integration adapter compatibility.
- Preserve audit records.
- Notify operations stakeholders of rollback status.

Rollback must not discard audit history or operational decisions.

## Documentation Updates

Documentation should be updated when a release changes:

- User workflows.
- API contracts.
- Data model.
- Recommendation logic.
- Security behavior.
- Integration behavior.
- Operational procedures.
- Known limitations.

The document index and documentation roadmap should be kept current as batches are added or committed.

## Release Approval

Release approval should scale by maturity:

| Stage | Approval |
| --- | --- |
| POC | Project owner review |
| MVP | Product and engineering review |
| Integration test | Engineering, integration owner, security review as needed |
| Pilot | Product, operations, security, architecture, and utility stakeholder approval |
| Production | Formal change advisory or utility release governance process |

## Related Documents

- `docs/000_Document_Index.md`
- `docs/002_Documentation_Roadmap.md`
- `docs/900_Delivery/901_Test_Strategy.md`
- `docs/900_Delivery/902_Implementation_Plan.md`
- `docs/900_Delivery/904_Runbook.md`
- `docs/800_Security_Operations/805_Deployment_and_Operations.md`
