from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


RecommendationAction = Literal["accepted", "modified", "deferred", "overridden"]
ScenarioEventType = Literal["blue_sky", "storm", "crew_shortage", "critical_facility"]
ScenarioFreshnessSource = Literal["scenario_generation", "file_upload", "repository_publish", "scenario_update"]


class DomainModel(BaseModel):
    """Strict base model for internal domain and public contract validation."""

    model_config = ConfigDict(extra="forbid")


class AssignedCrew(DomainModel):
    crew_id: str
    crew_name: str
    assignment_id: str
    assigned_at: str


class AssignedIncident(DomainModel):
    incident_id: str
    assignment_id: str
    assigned_at: str
    municipality: Optional[str] = None
    severity: Optional[str] = None


class CrewMapLocation(DomainModel):
    latitude: float
    longitude: float
    village: str
    reference_id: str
    precision: Literal["village_center"] = "village_center"


class Crew(DomainModel):
    crew_id: str
    crew_name: str
    home_region: str
    status: str
    capability: str
    current_location: str
    shift_remaining_hours: Union[int, float]
    storm_ready: bool
    travel_minutes_to_selected_incident: int
    assigned_incidents: list[AssignedIncident] = Field(default_factory=list)
    map_location: Optional[CrewMapLocation] = None


class CrewCandidate(Crew):
    suitability_score: int
    capability_match: bool
    estimated_travel_minutes: int


class ConfidenceRationale(DomainModel):
    score: Optional[int] = None
    threshold: Optional[int] = None
    reason: str


class ExplanationFactor(DomainModel):
    factor_id: str
    description: str
    contribution: Optional[int] = None
    evidence: Optional[str] = None


class ExplanationConstraint(DomainModel):
    constraint_id: str
    status: Literal["satisfied", "not_satisfied"]
    description: str


class ExcludedCandidate(DomainModel):
    crew_id: str
    reasons: list[str]


class RecommendationExplanation(DomainModel):
    """Versioned public explanation evidence for a recommendation."""

    confidence_rationale: ConfidenceRationale
    factors: list[ExplanationFactor] = Field(default_factory=list)
    constraints: list[ExplanationConstraint] = Field(default_factory=list)
    excluded_candidates: list[ExcludedCandidate] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    data_quality_warnings: list[str] = Field(default_factory=list)
    algorithm_version: str
    policy_version: str


class Recommendation(DomainModel):
    recommendation_id: str
    incident_id: str
    recommended_action: str
    recommended_crew: Optional[CrewCandidate]
    confidence: str
    expected_impact: str
    factors: list[str]
    constraints: list[str]
    alternatives: list[CrewCandidate]
    explanation: Optional[RecommendationExplanation] = None


class RecommendationDecision(DomainModel):
    event_id: str
    scenario_id: str
    recommendation_id: str
    incident_id: str
    crew_id: Optional[str] = None
    action: RecommendationAction
    reason: Optional[str] = None
    note: Optional[str] = None
    recommendation: Recommendation
    created_at: str
    actor: str


class Incident(DomainModel):
    incident_id: str
    region: str
    municipality: str
    geography_reference_id: Optional[str] = None
    feeder: str
    severity: str
    status: str
    customers_out: int
    critical_facility: bool
    hazard: str
    required_skill: str
    age_minutes: int
    latitude: float
    longitude: float
    etr: str
    assigned_crews: list[AssignedCrew] = Field(default_factory=list)
    current_decision: Optional[RecommendationDecision] = None
    critical_facility_level: Optional[Literal[1, 2, 3]] = None
    matched_critical_facility_ids: list[str] = Field(default_factory=list)
    ranking_status: Literal["ranked", "withheld"] = "ranked"
    ranking_warning: Optional[str] = None


class Assignment(DomainModel):
    assignment_id: str
    scenario_id: str
    incident_id: str
    crew_id: str
    status: str
    assigned_at: str
    notes: str


class AssignmentMutation(DomainModel):
    mutation_id: str
    scenario_id: str
    assignment_id: str
    incident_id: str
    crew_id: str
    action: Literal["unassigned", "reassigned"]
    reason: str
    reason_category: Literal[
        "field_condition_changed",
        "crew_unavailable",
        "assignment_entered_in_error",
        "incident_priority_changed",
        "supervisor_direction",
        "other",
    ]
    note: Optional[str] = None
    actor: str
    created_at: str
    new_assignment_id: Optional[str] = None
    new_crew_id: Optional[str] = None


class AuditEvent(DomainModel):
    """Target generic audit contract; recommendation decisions are its first persisted subtype."""

    event_id: str
    event_type: str
    actor_type: str
    actor_id: str
    entity_type: str
    entity_id: str
    timestamp: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None


class ScenarioFreshness(DomainModel):
    updated_at: datetime
    source: ScenarioFreshnessSource
    provenance: str = Field(min_length=1)

    @field_validator("updated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("must include a timezone offset")
        return value

    @field_validator("provenance")
    @classmethod
    def normalize_provenance(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class ScenarioMetadata(DomainModel):
    schema_version: Literal["1.0"]
    scenario_id: str
    name: str
    description: str
    event_type: ScenarioEventType
    expected_conditions: list[str]
    freshness: Optional[ScenarioFreshness] = None
