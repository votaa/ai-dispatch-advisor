from __future__ import annotations

from ..api_models import ChatResponse
from .incident_service import IncidentService
from .recommendation_service import RecommendationService


class CopilotService:
    def __init__(
        self,
        *,
        incidents: IncidentService,
        recommendations: RecommendationService,
    ) -> None:
        self._incidents = incidents
        self._recommendations = recommendations

    def respond(self, message: str, incident_id: str | None = None) -> ChatResponse:
        normalized_message = message.lower()
        summary = self._recommendations.dashboard()
        incident = self._incidents.find(incident_id) if incident_id else None

        if any(term in normalized_message for term in ["critical", "hospital", "facility", "water", "emergency"]):
            answer = (
                f"There are {summary.critical_facility_incidents} incidents affecting critical facilities. "
                "The highest-priority critical events in this demo are Millbrook Regional Hospital, "
                "Briarcliff Emergency Operations Center, and Riverton Water Treatment."
            )
            intent = "critical_facilities"
        elif any(term in normalized_message for term in ["crew", "crews", "available", "resource", "resources"]):
            answer = (
                f"{summary.available_crews} crews are available and {summary.assigned_crews} are assigned. "
                "Crew recommendations consider availability, capability, and estimated travel time."
            )
            intent = "crew_status"
        elif any(term in normalized_message for term in ["recommend", "why", "assign", "assignment", "dispatch"]):
            recommendation = self._recommendations.recommend(incident_id)
            crew_name = (
                recommendation.recommended_crew.crew_name
                if recommendation.recommended_crew
                else "an available crew"
            )
            answer = (
                f"The current recommendation is to {recommendation.recommended_action.lower()} "
                f"{crew_name}. Confidence is {recommendation.confidence} because the explanation factors include "
                f"{', '.join(recommendation.factors[:3])}."
            )
            intent = "recommendation"
        elif any(term in normalized_message for term in ["first", "focus", "priority", "prioritize", "next"]):
            top_incident = summary.top_incidents[0]
            answer = (
                f"Focus first on {top_incident.incident_id} in {top_incident.municipality}. "
                f"It affects {top_incident.customers_out} customers, is marked {top_incident.severity}, "
                f"and has the hazard '{top_incident.hazard}'."
            )
            intent = "priority_focus"
        elif any(term in normalized_message for term in ["storm", "weather", "wind", "rain"]):
            answer = (
                "Storm mode should focus on critical facilities, downed-wire hazards, and crew capacity by region. "
                f"This scenario has {summary.high_priority_incidents} high-priority incidents and "
                f"{summary.customers_out} customers out."
            )
            intent = "storm_summary"
        elif any(term in normalized_message for term in ["selected", "incident", "outage", "status"]) and incident:
            answer = (
                f"Selected incident {incident.incident_id} is in {incident.municipality} on feeder "
                f"{incident.feeder}. It affects {incident.customers_out} customers, has status "
                f"{incident.status}, and current ETR is {incident.etr}."
            )
            intent = "selected_incident"
        else:
            answer = (
                f"The demo scenario has {summary.active_incidents} active incidents affecting "
                f"{summary.customers_out} customers. Try asking about crews, critical facilities, "
                "the top priority, storm status, or why a recommendation was made."
            )
            intent = "scenario_summary"

        return ChatResponse(
            answer=answer,
            intent=intent,
            source="synthetic-demo-data",
            safety_note="This copilot response is advisory and does not execute dispatch actions.",
        )
