from __future__ import annotations

from typing import Literal, Protocol, Union

from pydantic import Field, model_validator

from ..domain.models import Assignment, Crew, DomainModel, Incident, Recommendation
from .policy import RecommendationPolicy


IncidentFactorId = Literal[
    "customers_out",
    "critical_facility",
    "hazard",
    "incident_age",
    "severity",
]
CrewConstraintId = Literal[
    "crew_available",
    "crew_unassigned",
    "crew_capability_required",
    "shift_sufficiency",
]
ScoreCalculation = Literal["integer_division", "conditional_bonus", "configured_weight"]


class IncidentScoreContribution(DomainModel):
    factor_id: IncidentFactorId
    raw_value: Union[bool, int, str]
    configured_value: int
    contribution: int
    calculation: ScoreCalculation


class IncidentScore(DomainModel):
    incident_id: str
    total_score: int
    contributions: list[IncidentScoreContribution]
    algorithm_version: str
    policy_version: str


class RankedIncident(DomainModel):
    incident: Incident
    score: IncidentScore


class CrewExclusionReason(DomainModel):
    """A typed, internal explanation for excluding one crew candidate."""

    constraint_id: CrewConstraintId
    message: str
    details: dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class CrewFeasibility(DomainModel):
    """Feasibility result retained at the optimization boundary for explainability."""

    crew_id: str
    feasible: bool
    exclusions: list[CrewExclusionReason] = Field(default_factory=list)


class OptimizationRequest(DomainModel):
    """Typed snapshot supplied to a recommendation engine for one incident."""

    scenario_id: str
    incident: Incident
    crews: list[Crew]
    assignments: list[Assignment]

    @model_validator(mode="after")
    def validate_scenario_context(self) -> "OptimizationRequest":
        mismatched = [
            assignment.assignment_id
            for assignment in self.assignments
            if assignment.scenario_id != self.scenario_id
        ]
        if mismatched:
            raise ValueError(
                "assignments must belong to the optimization request scenario: "
                + ", ".join(mismatched)
            )
        return self


class OptimizationEngine(Protocol):
    """Behavior required from deterministic and future optimization engines."""

    @property
    def policy(self) -> RecommendationPolicy: ...

    def rank_incidents(self, incidents: list[Incident]) -> list[Incident]: ...

    def evaluate_incidents(self, incidents: list[Incident]) -> list[RankedIncident]: ...

    def evaluate_crew_feasibility(
        self, request: OptimizationRequest
    ) -> list[CrewFeasibility]: ...

    def recommend(self, request: OptimizationRequest) -> Recommendation: ...
