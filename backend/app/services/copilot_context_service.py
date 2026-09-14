from __future__ import annotations

import json
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from ..api_models import CopilotEvidence, CopilotRequestTime
from ..domain.models import Crew, Incident
from ..geography import TravelEstimateService
from .context_service import OperationalContextService
from .crew_service import CrewService
from .incident_service import IncidentService
from .recommendation_service import RecommendationService


@dataclass(frozen=True)
class GroundedCopilotContext:
    user_prompt: str
    evidence: list[CopilotEvidence]
    response_scope: str


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
        selected_crew: Crew | None = None,
        request_time: CopilotRequestTime | None = None,
    ) -> GroundedCopilotContext:
        remaining = self._max_records
        evidence: list[CopilotEvidence] = []
        payload: dict[str, Any] = {
            "scenario_id": self._active_scenario_id(),
            "synthetic_data": True,
            "question": question,
            "request_time": request_time.model_dump(mode="json") if request_time else None,
            "selected_incident": None,
            "selected_crew": None,
            "ranked_incidents": [],
            "recommendation": None,
            "crews": [],
            "critical_facilities": [],
            "weather": [],
            "context_scope": {},
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

        if selected_crew is not None and remaining:
            payload["selected_crew"] = selected_crew.model_dump(mode="json")
            evidence.append(
                CopilotEvidence(
                    source_type="crew",
                    record_id=selected_crew.crew_id,
                    label=selected_crew.crew_name,
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

        selected_incident_count = 1 if payload["selected_incident"] else 0
        selected_crew_count = 1 if payload["selected_crew"] else 0
        recommendation_count = 1 if payload["recommendation"] else 0
        records_supplied = (
            selected_incident_count
            + selected_crew_count
            + len(ranked)
            + recommendation_count
            + len(crews)
            + len(facilities)
            + len(weather)
        )
        payload["context_scope"] = {
            "kind": "bounded_grounded_context",
            "complete_population": False,
            "record_limit": self._max_records,
            "records_supplied": records_supplied,
            "selected_incidents": selected_incident_count,
            "selected_crews": selected_crew_count,
            "ranked_incidents": len(ranked),
            "recommendations": recommendation_count,
            "crews": len(crews),
            "critical_facilities": len(facilities),
            "weather_records": len(weather),
        }

        scope_parts = []
        if selected_incident_count:
            scope_parts.append("1 selected incident")
        if selected_crew_count:
            scope_parts.append("1 selected crew")
        scope_parts.append(f"{len(ranked)} ranked incidents")
        if recommendation_count:
            scope_parts.append("1 recommendation")
        scope_parts.extend(
            [
                f"{len(crews)} crews",
                f"{len(facilities)} critical-facility records",
                f"{len(weather)} weather records",
            ]
        )
        response_scope = (
            "Bounded grounded context: "
            + " + ".join(scope_parts)
            + f" ({records_supplied} of {self._max_records} record limit used)"
        )

        return GroundedCopilotContext(
            user_prompt=json.dumps(payload, sort_keys=True, separators=(",", ":")),
            evidence=evidence,
            response_scope=response_scope,
        )
