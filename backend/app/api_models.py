from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field, field_validator

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
    crew_id: Optional[str] = None


class RecommendationActionRequest(DomainModel):
    incident_id: str
    action: RecommendationAction
    recommendation: Recommendation
    selected_crew_id: Optional[str] = None
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


class CopilotEvidence(DomainModel):
    source_type: Literal[
        "dashboard",
        "incident",
        "crew",
        "recommendation",
        "critical_facility",
        "geography",
        "travel_estimate",
    ]
    record_id: str
    label: str


class CopilotRequestTime(DomainModel):
    received_at: datetime
    timezone: Literal["UTC"] = "UTC"
    source: Literal["backend_server_clock"] = "backend_server_clock"
    clock_skew: Literal["not_measured"] = "not_measured"

    @field_validator("received_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("must include a timezone offset")
        return value


class ChatResponse(DomainModel):
    answer: str
    intent: str
    source: str
    safety_note: str
    execution_mode: Literal["local_query", "llm_grounded", "rule_based_fallback"]
    scenario_id: str
    generated_at: str
    request_time: Optional[CopilotRequestTime] = None
    data_snapshot_at: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    warning: Optional[str] = None
    evidence: list[CopilotEvidence] = Field(default_factory=list)
