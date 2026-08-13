from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..domain.models import Assignment, Incident
from ..recommendations import ranked_incidents
from .assignment_service import AssignmentService
from .errors import EntityNotFoundError


class IncidentService:
    def __init__(
        self,
        *,
        active_scenario_id: Callable[[], str],
        incident_rows: Callable[[], list[dict[str, Any]]],
        crew_rows: Callable[[], list[dict[str, Any]]],
        latest_decisions: Callable[[str], dict[str, dict[str, Any]]],
        assignments: AssignmentService,
    ) -> None:
        self._active_scenario_id = active_scenario_id
        self._incident_rows = incident_rows
        self._crew_rows = crew_rows
        self._latest_decisions = latest_decisions
        self._assignments = assignments

    def list_ranked(self) -> list[Incident]:
        assignments = self._assignments.list_active()
        latest_decisions = self._latest_decisions(self._active_scenario_id())
        crew_names = {
            str(row.get("crew_id")): str(row.get("crew_name"))
            for row in self._crew_rows()
        }
        assignments_by_incident: dict[str, list[Assignment]] = {}
        for assignment in assignments:
            assignments_by_incident.setdefault(assignment.incident_id, []).append(assignment)

        incidents: list[Incident] = []
        for row in self._incident_rows():
            incident_id = str(row.get("incident_id"))
            incident_assignments = assignments_by_incident.get(incident_id, [])
            assigned_crews = [
                {
                    "crew_id": assignment.crew_id,
                    "crew_name": crew_names.get(assignment.crew_id, assignment.crew_id),
                    "assignment_id": assignment.assignment_id,
                    "assigned_at": assignment.assigned_at,
                }
                for assignment in incident_assignments
            ]
            incidents.append(
                Incident.model_validate(
                    {
                        **row,
                        "status": "assigned" if assigned_crews else row.get("status"),
                        "assigned_crews": assigned_crews,
                        "current_decision": latest_decisions.get(incident_id),
                    }
                )
            )

        ranked = ranked_incidents([incident.model_dump() for incident in incidents])
        return [Incident.model_validate(row) for row in ranked]

    def find(self, incident_id: str) -> Incident | None:
        return next(
            (incident for incident in self.list_ranked() if incident.incident_id == incident_id),
            None,
        )

    def get(self, incident_id: str) -> Incident:
        incident = self.find(incident_id)
        if incident is None:
            raise EntityNotFoundError("Incident", incident_id)
        return incident
