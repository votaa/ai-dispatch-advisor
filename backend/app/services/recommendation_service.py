from __future__ import annotations

from collections.abc import Callable

from ..api_models import DashboardResponse
from ..domain.models import Recommendation
from ..optimization.contracts import OptimizationEngine, OptimizationRequest
from ..optimization.deterministic_engine import DeterministicOptimizationEngine
from ..recommendations import dashboard_summary
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
        optimization_engine: OptimizationEngine | None = None,
    ) -> None:
        self._active_scenario_id = active_scenario_id
        self._incidents = incidents
        self._crews = crews
        self._assignments = assignments
        self._optimization_engine = optimization_engine or DeterministicOptimizationEngine()

    def dashboard(self) -> DashboardResponse:
        summary = dashboard_summary(
            [incident.model_dump() for incident in self._incidents.list_ranked()],
            [crew.model_dump() for crew in self._crews.list()],
            [assignment.model_dump() for assignment in self._assignments.list_active()],
            scenario_id=self._active_scenario_id(),
            policy=self._optimization_engine.policy,
        )
        return DashboardResponse.model_validate(summary)

    def recommend(self, incident_id: str | None = None) -> Recommendation:
        incidents = self._incidents.list_ranked()
        if incident_id is not None:
            incidents = [incident for incident in incidents if incident.incident_id == incident_id]
        if not incidents:
            raise EntityNotFoundError("Incident", incident_id)

        return self._optimization_engine.recommend(
            OptimizationRequest(
                scenario_id=self._active_scenario_id(),
                incident=incidents[0],
                crews=self._crews.list(),
                assignments=self._assignments.list_active(),
            )
        )
