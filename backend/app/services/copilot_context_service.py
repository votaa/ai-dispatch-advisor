from __future__ import annotations

import json
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from ..api_models import CopilotEvidence
from ..domain.models import Incident
from ..geography import TravelEstimateService
from .context_service import OperationalContextService
from .crew_service import CrewService
from .incident_service import IncidentService
from .recommendation_service import RecommendationService


@dataclass(frozen=True)
class GroundedCopilotContext:
    user_prompt: str
    evidence: list[CopilotEvidence]


class CopilotContextBuilder:
    def __init__(
        self,
        *,
        active_scenario_id: Callable[[], str],
        incidents: IncidentService,
        crews: CrewService,
        recommendations: RecommendationService,
        context: OperationalContextService,
        travel_estimates: TravelEstimateService,
        max_records: int,
    ) -> None:
        self._active_scenario_id = active_scenario_id
        self._incidents = incidents
        self._crews = crews
        self._recommendations = recommendations
        self._context = context
        self._travel_estimates = travel_estimates
        self._max_records = max_records

    def build(
        self,
        question: str,
        selected_incident: Incident | None,
    ) -> GroundedCopilotContext:
        remaining = self._max_records
        evidence: list[CopilotEvidence] = []
        payload: dict[str, Any] = {
            "scenario_id": self._active_scenario_id(),
            "synthetic_data": True,
            "question": question,
            "selected_incident": None,
            "ranked_incidents": [],
            "recommendation": None,
            "crews": [],
            "critical_facilities": [],
            "weather": [],
        }

        if selected_incident is not None and remaining:
            payload["selected_incident"] = selected_incident.model_dump(mode="json")
            evidence.append(
                CopilotEvidence(
                    source_type="incident",
                    record_id=selected_incident.incident_id,
                    label=selected_incident.municipality,
                )
            )
            remaining -= 1

        ranked = self._incidents.list_ranked()[: min(5, remaining)]
        payload["ranked_incidents"] = [row.model_dump(mode="json") for row in ranked]
        for incident in ranked:
            evidence.append(
                CopilotEvidence(
                    source_type="incident",
                    record_id=incident.incident_id,
                    label=f"Ranked incident: {incident.municipality}",
                )
            )
        remaining -= len(ranked)

        if selected_incident is not None and remaining:
            recommendation = self._recommendations.recommend(selected_incident.incident_id)
            payload["recommendation"] = recommendation.model_dump(mode="json")
            evidence.append(
                CopilotEvidence(
                    source_type="recommendation",
                    record_id=recommendation.recommendation_id,
                    label=recommendation.recommended_action,
                )
            )
            remaining -= 1

        crews = self._crews.list()
        if selected_incident is not None:
            crews = self._travel_estimates.crews_for_incident(crews, selected_incident)
        crews = crews[: min(6, remaining)]
        payload["crews"] = [crew.model_dump(mode="json") for crew in crews]
        remaining -= len(crews)

        facilities = self._context.critical_facilities()[: min(8, remaining)]
        payload["critical_facilities"] = facilities
        for facility in facilities:
            evidence.append(
                CopilotEvidence(
                    source_type="critical_facility",
                    record_id=str(facility.get("facility_id")),
                    label=str(facility.get("facility_name")),
                )
            )
        remaining -= len(facilities)

        weather = self._context.weather()[: min(4, remaining)]
        payload["weather"] = weather

        return GroundedCopilotContext(
            user_prompt=json.dumps(payload, sort_keys=True, separators=(",", ":")),
            evidence=evidence,
        )
