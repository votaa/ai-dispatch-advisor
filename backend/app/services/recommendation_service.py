from __future__ import annotations

from collections.abc import Callable

from ..api_models import DashboardResponse
from ..domain.models import Recommendation
from ..recommendations import dashboard_summary, recommend_assignment
from .assignment_service import AssignmentService
from .crew_service import CrewService
from .errors import EntityNotFoundError
from .incident_service import IncidentService


class RecommendationService:
    def __init__(
        self,
        *,
        active_scenario_id: Callable[[], str],
        incidents: IncidentService,
        crews: CrewService,
        assignments: AssignmentService,
    ) -> None:
        self._active_scenario_id = active_scenario_id
        self._incidents = incidents
        self._crews = crews
        self._assignments = assignments

    def dashboard(self) -> DashboardResponse:
        summary = dashboard_summary(
            [incident.model_dump() for incident in self._incidents.list_ranked()],
            [crew.model_dump() for crew in self._crews.list()],
            [assignment.model_dump() for assignment in self._assignments.list_active()],
            scenario_id=self._active_scenario_id(),
        )
        return DashboardResponse.model_validate(summary)

    def recommend(self, incident_id: str | None = None) -> Recommendation:
        incidents = self._incidents.list_ranked()
        if incident_id is not None:
            incidents = [incident for incident in incidents if incident.incident_id == incident_id]
        if not incidents:
            raise EntityNotFoundError("Incident", incident_id)

        recommendation = recommend_assignment(
            incidents[0].model_dump(),
            [crew.model_dump() for crew in self._crews.list()],
            [assignment.model_dump() for assignment in self._assignments.list_active()],
        )
        return Recommendation.model_validate(recommendation)
