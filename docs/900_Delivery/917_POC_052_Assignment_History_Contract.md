# POC-052 — Assignment Mutation History Contract

Status: Slice 1 implemented. The in-product history panel remains future work.

## Historical record

Each successful unassign or reassign writes a scenario-scoped, immutable mutation row. The history response contains the mutation ID, action, scenario, incident, prior assignment and crew, governed reason category, optional note, actor, and UTC event timestamp. Reassignment rows also contain the replacement assignment and crew IDs. `resulting_incident_status` is the incident status immediately after that action: `assigned` when at least one active assignment remains, otherwise `unassigned`. It is a historical snapshot, not the incident's current status. Crew status is not part of this historical outcome contract.

Migration `006_assignment_mutation_history.sql` preserves existing rows. It recovers replacement IDs for older reassignment rows from their linked demo assignment when available. Their historical incident outcome cannot be established reliably from current state and remains `null`; the future UI should label that value unavailable. Missing legacy replacement links likewise remain `null`, without inference from current assignments.

## Read contract

`GET /api/assignment-actions/history?limit=25&offset=0` returns newest mutations for the active scenario only. The limit is clamped to 1–100 and the offset to zero or greater, allowing the panel to page through complete history. The response is separate from `/api/audit/events`, which remains recommendation-decision history. The endpoint is read-only and returns an empty list when no assignment mutations exist for the active scenario. The future panel should refetch when the scenario changes and after a successful assignment action.

## Persistence

The default SQLite file is `database/aida_decisions.db`. Local backend runs use that ignored repository file. Docker Compose bind-mounts `./database` at `/app/database`, so committed mutations survive backend process restarts and container recreation on the same host. Preserve or back up this directory before moving hosts or removing local state. Runtime active-scenario selection still resets to the configured default when the backend restarts; history for another scenario reappears when that scenario is activated again. This is POC local persistence, not a production multi-user audit store.

**Existing-container handoff:** A backend container created before this mount keeps its database inside the container. Before recreating it with the new Compose configuration, stop writes, take a consistent SQLite backup of `/app/database/aida_decisions.db` from that container, preserve any existing host `database/aida_decisions.db`, and place the container backup at the host path. Then recreate the backend so migration 006 runs against the retained records. On 2026-09-25, the running container had 1 recommendation decision, 2 demo assignments, and 5 assignment mutations; the host database had no decision or assignment rows and no mutation table. Recreating the container against the host file without this handoff would hide the five existing mutations.

## Remaining slice

Add a discoverable Audit / Assignment History panel that shows these records and distinguishes them from recommendation decisions. Display the historical incident outcome separately from current incident status, and make `null` legacy fields explicitly unavailable.
