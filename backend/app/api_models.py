from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field, field_validator

from .domain.models import (
    AssignmentMutation,
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
    etr_mode: Literal["current", "scenario_preview"] = "current"


class RecommendationActionRequest(DomainModel):
    incident_id: str
    action: RecommendationAction
    recommendation: Recommendation
    selected_crew_id: Optional[str] = None
    reason: Optional[str] = None
    note: Optional[str] = None


class AssignmentActionRequest(DomainModel):
    assignment_id: str
    action: Literal["unassigned", "reassigned"]
    selected_crew_id: Optional[str] = None
    reason_category: Literal[
        "field_condition_changed",
        "crew_unavailable",
        "assignment_entered_in_error",
        "incident_priority_changed",
        "supervisor_direction",
        "other",
    ]
    note: Optional[str] = None



class AssignmentActionResponse(AssignmentMutation):
    pass


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
        "pseg_reference",
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


class ETRCategoryCounts(DomainModel):
    expired: int
    due_now: int
    due_soon: int
    valid_future: int
    unavailable: int


class ETRExample(DomainModel):
    incident_id: str
    category: Literal["expired", "due_now", "due_soon", "valid_future", "unavailable"]
    etr: Optional[str] = None
    unavailable_reason: Optional[Literal["assessing_conditions", "missing_or_invalid"]] = None


class ETRAnalysis(DomainModel):
    mode: Literal["current", "scenario_preview"]
    status: Literal["answered", "blocked"]
    temporal_status: Literal["eligible", "future", "stale", "legacy", "unavailable"]
    evaluation_at: datetime
    scenario_as_of_at: Optional[datetime] = None
    due_now_grace_minutes: int = 10
    due_soon_window_minutes: int = 60
    evaluated_incident_count: Optional[int] = None
    counts: Optional[ETRCategoryCounts] = None
    unavailable_assessing_conditions: Optional[int] = None
    unavailable_missing_or_invalid: Optional[int] = None
    past_due_total: Optional[int] = None
    past_due_within_due_now: Optional[int] = None
    examples: list[ETRExample] = Field(default_factory=list)
    suggested_scenario_id: Optional[str] = None


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
    response_scope: Optional[str] = None
    evidence: list[CopilotEvidence] = Field(default_factory=list)
    etr_analysis: Optional[ETRAnalysis] = None
