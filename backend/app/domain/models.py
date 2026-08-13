from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


RecommendationAction = Literal["accepted", "modified", "deferred", "overridden"]
ScenarioEventType = Literal["blue_sky", "storm", "crew_shortage", "critical_facility"]


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


class CrewCandidate(Crew):
    suitability_score: int
    capability_match: bool
    estimated_travel_minutes: int


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


class Assignment(DomainModel):
    assignment_id: str
    scenario_id: str
    incident_id: str
    crew_id: str
    status: str
    assigned_at: str
    notes: str


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


class ScenarioMetadata(DomainModel):
    schema_version: Literal["1.0"]
    scenario_id: str
    name: str
    description: str
    event_type: ScenarioEventType
    expected_conditions: list[str]
