from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..domain.models import Assignment, Incident
from ..optimization.contracts import OptimizationEngine
from ..optimization.critical_facility import resolve_critical_facility_impact
from ..optimization.deterministic_engine import DeterministicOptimizationEngine
from .assignment_service import AssignmentService
from .errors import EntityNotFoundError


class IncidentService:
    def __init__(
        self,
        *,
        active_scenario_id: Callable[[], str],
        incident_rows: Callable[[], list[dict[str, Any]]],
        crew_rows: Callable[[], list[dict[str, Any]]],
        critical_facility_rows: Callable[[], list[dict[str, Any]]] | None = None,
        latest_decisions: Callable[[str], dict[str, dict[str, Any]]],
        assignments: AssignmentService,
        optimization_engine: OptimizationEngine | None = None,
    ) -> None:
        self._active_scenario_id = active_scenario_id
        self._incident_rows = incident_rows
        self._crew_rows = crew_rows
        self._critical_facility_rows = critical_facility_rows or (lambda: [])
        self._latest_decisions = latest_decisions
        self._assignments = assignments
        self._optimization_engine = optimization_engine or DeterministicOptimizationEngine()

    def list_ranked(self) -> list[Incident]:
        return self._optimization_engine.rank_incidents(self._list_incidents())

    def list_visible(self) -> list[Incident]:
        incidents = self._list_incidents()
        ranked = self._optimization_engine.rank_incidents(incidents)
        ranked_ids = {incident.incident_id for incident in ranked}
        withheld = sorted(
            (incident for incident in incidents if incident.incident_id not in ranked_ids),
            key=lambda incident: incident.incident_id,
        )
        return [*ranked, *withheld]

    def list_withheld(self) -> list[Incident]:
        return [
            incident
            for incident in self.list_visible()
            if incident.ranking_status == "withheld"
        ]

    def _list_incidents(self) -> list[Incident]:
        assignments = self._assignments.list_active()
        latest_decisions = self._latest_decisions(self._active_scenario_id())
        crew_names = {
            str(row.get("crew_id")): str(row.get("crew_name"))
            for row in self._crew_rows()
        }
        assignments_by_incident: dict[str, list[Assignment]] = {}
        for assignment in assignments:
            assignments_by_incident.setdefault(assignment.incident_id, []).append(assignment)

        level_scoring_enabled = bool(
            self._optimization_engine.policy.incident_scoring.critical_facility_weights
        )
        facilities = self._critical_facility_rows() if level_scoring_enabled else []
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
            incident = Incident.model_validate(
                {
                    **row,
                    "status": "assigned" if assigned_crews else row.get("status"),
                    "assigned_crews": assigned_crews,
                    "current_decision": latest_decisions.get(incident_id),
                }
            )
            if level_scoring_enabled:
                impact = resolve_critical_facility_impact(
                    incident,
                    facilities,
                )
                incident = incident.model_copy(
                    update={
                        "critical_facility_level": impact.level,
                        "matched_critical_facility_ids": impact.matched_facility_ids,
                        "ranking_status": impact.ranking_status,
                        "ranking_warning": impact.warning_message,
                    }
                )
            incidents.append(incident)

        return incidents

    def find(self, incident_id: str) -> Incident | None:
        return next(
            (incident for incident in self.list_visible() if incident.incident_id == incident_id),
            None,
        )

    def get(self, incident_id: str) -> Incident:
        incident = self.find(incident_id)
        if incident is None:
            raise EntityNotFoundError("Incident", incident_id)
        return incident
