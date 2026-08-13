from __future__ import annotations

from typing import Protocol

from pydantic import model_validator

from ..domain.models import Assignment, Crew, DomainModel, Incident, Recommendation
from .policy import RecommendationPolicy


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

    def recommend(self, request: OptimizationRequest) -> Recommendation: ...
