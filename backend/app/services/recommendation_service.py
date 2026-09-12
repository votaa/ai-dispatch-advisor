from __future__ import annotations

from collections.abc import Callable

from ..api_models import DashboardResponse
from ..domain.models import Recommendation
from ..geography import TravelEstimateService
from ..optimization.contracts import OptimizationEngine, OptimizationRequest
from ..optimization.deterministic_engine import DeterministicOptimizationEngine
from ..recommendations import dashboard_summary
from .assignment_service import AssignmentService
from .crew_service import CrewService
from .errors import EntityNotFoundError, IncidentRankingWithheldError
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
        travel_estimates: TravelEstimateService | None = None,
    ) -> None:
        self._active_scenario_id = active_scenario_id
        self._incidents = incidents
        self._crews = crews
        self._assignments = assignments
        self._optimization_engine = optimization_engine or DeterministicOptimizationEngine()
        self._travel_estimates = travel_estimates

    def dashboard(self) -> DashboardResponse:
        visible_incidents = self._incidents.list_visible()
        summary = dashboard_summary(
            [incident.model_dump() for incident in self._incidents.list_ranked()],
            [crew.model_dump() for crew in self._crews.list()],
            [assignment.model_dump() for assignment in self._assignments.list_active()],
            scenario_id=self._active_scenario_id(),
            all_incidents=[incident.model_dump() for incident in visible_incidents],
        )
        return DashboardResponse.model_validate(summary)

    def recommend(self, incident_id: str | None = None) -> Recommendation:
        if incident_id is not None:
            incident = self._incidents.get(incident_id)
            if incident.ranking_status == "withheld":
                raise IncidentRankingWithheldError(
                    incident.incident_id,
                    incident.ranking_warning or "Critical-facility data requires review.",
                    incident.matched_critical_facility_ids,
                )
        else:
            incidents = self._incidents.list_ranked()
            if not incidents:
                raise EntityNotFoundError("Incident", incident_id)
            incident = incidents[0]
        crews = self._crews.list()
        if self._travel_estimates is not None:
            crews = self._travel_estimates.crews_for_incident(crews, incident)

        return self._optimization_engine.recommend(
            OptimizationRequest(
                scenario_id=self._active_scenario_id(),
                incident=incident,
                crews=crews,
                assignments=self._assignments.list_active(),
            )
        )
