from __future__ import annotations

from typing import Optional

from pydantic import Field

from .domain.models import (
    DomainModel,
    Incident,
    Recommendation,
    RecommendationAction,
)


class HealthResponse(DomainModel):
    status: str
    service: str


class OptimizeRequest(DomainModel):
    incident_id: Optional[str] = None


class ChatRequest(DomainModel):
    message: str = Field(min_length=1)
    incident_id: Optional[str] = None


class RecommendationActionRequest(DomainModel):
    incident_id: str
    action: RecommendationAction
    recommendation: Recommendation
    reason: Optional[str] = None
    note: Optional[str] = None


class ScenarioActivationRequest(DomainModel):
    scenario_id: str


class DashboardResponse(DomainModel):
    active_incidents: int
    customers_out: int
    available_crews: int
    assigned_crews: int
    critical_facility_incidents: int
    high_priority_incidents: int
    top_incidents: list[Incident]
    scenario: str
    data_freshness: str


class ChatResponse(DomainModel):
    answer: str
    intent: str
    source: str
    safety_note: str
