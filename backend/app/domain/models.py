from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    resolution_basis: Literal["source_place", "operating_hq_proxy"] = "source_place"


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
    etr: Optional[str] = None
    etr_status: Optional[Literal["estimated", "assessing_conditions"]] = None
    created_at: Optional[str] = None
    created_at_source: Optional[Literal["synthetic_generator", "source_record"]] = None
    assigned_crews: list[AssignedCrew] = Field(default_factory=list)
    current_decision: Optional[RecommendationDecision] = None
    critical_facility_level: Optional[Literal[1, 2, 3]] = None
    matched_critical_facility_ids: list[str] = Field(default_factory=list)
    ranking_status: Literal["ranked", "withheld"] = "ranked"
    ranking_warning: Optional[str] = None

    @model_validator(mode="after")
    def validate_temporal_state(self) -> Incident:
        if self.created_at is not None:
            try:
                created = datetime.fromisoformat(self.created_at)
            except ValueError as exc:
                raise ValueError("created_at must be an RFC 3339 datetime") from exc
            if created.tzinfo is None or created.utcoffset() is None:
                raise ValueError("created_at must include a timezone offset")
            if self.created_at_source is None:
                raise ValueError("created_at_source is required with created_at")
        if self.etr_status == "assessing_conditions" and self.etr is not None:
            raise ValueError("Assessing Conditions must have a NULL ETR")
        if self.etr_status == "estimated":
            if not self.etr:
                raise ValueError("An estimated ETR must have a timestamp")
            try:
                estimated = datetime.fromisoformat(self.etr)
            except ValueError as exc:
                raise ValueError("An estimated ETR must be an RFC 3339 datetime") from exc
            if estimated.tzinfo is None or estimated.utcoffset() is None:
                raise ValueError("An estimated ETR must include a timezone offset")
        return self


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
    resulting_incident_status: Optional[Literal["assigned", "unassigned"]] = None


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


class ScenarioETRDistributionEntry(DomainModel):
    range: str
    percent: float = Field(ge=0, le=100)

    @field_validator("range")
    @classmethod
    def validate_range(cls, value: str) -> str:
        if not re.fullmatch(r"null|[1-9]\d*(?:-[1-9]\d*)?h", value):
            raise ValueError("ETR range must be null, fixed hours, or an hour band")
        if "-" in value:
            minimum, maximum = value[:-1].split("-")
            if int(maximum) < int(minimum):
                raise ValueError("ETR hour band must be ordered")
        return value


class ScenarioTemporal(DomainModel):
    kind: Literal["single_snapshot", "timeline_snapshot"]
    as_of_at: datetime
    time_zone: Literal["America/New_York"] = "America/New_York"
    etr_distribution: list[ScenarioETRDistributionEntry] = Field(min_length=1)
    timeline_id: Optional[str] = None
    snapshot_index: Optional[int] = Field(default=None, ge=1)
    snapshot_count: Optional[int] = Field(default=None, ge=1)

    @field_validator("as_of_at")
    @classmethod
    def require_aware_cutoff(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("must include a timezone offset")
        return value

    @model_validator(mode="after")
    def validate_timeline_identity(self) -> ScenarioTemporal:
        if abs(sum(entry.percent for entry in self.etr_distribution) - 100) > 0.000001:
            raise ValueError("ETR distribution percentages must total 100")
        labels = [entry.range for entry in self.etr_distribution]
        if len(labels) != len(set(labels)):
            raise ValueError("ETR distribution ranges must be unique")
        fields = (self.timeline_id, self.snapshot_index, self.snapshot_count)
        if self.kind == "single_snapshot" and any(value is not None for value in fields):
            raise ValueError("single snapshots cannot declare timeline identity")
        if self.kind == "timeline_snapshot" and any(value is None for value in fields):
            raise ValueError("timeline snapshots require timeline identity and index/count")
        if self.snapshot_index and self.snapshot_count and self.snapshot_index > self.snapshot_count:
            raise ValueError("snapshot_index cannot exceed snapshot_count")
        return self


class ScenarioMetadata(DomainModel):
    schema_version: Literal["1.0"]
    scenario_id: str
    name: str
    description: str
    event_type: ScenarioEventType
    expected_conditions: list[str]
    freshness: Optional[ScenarioFreshness] = None
    temporal: Optional[ScenarioTemporal] = None
