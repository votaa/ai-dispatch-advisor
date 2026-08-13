from __future__ import annotations

from ..domain.models import Incident, Recommendation
from ..recommendations import ranked_incidents, recommend_assignment
from .contracts import OptimizationRequest
from .policy import DEFAULT_RECOMMENDATION_POLICY, RecommendationPolicy


class DeterministicOptimizationEngine:
    """Adapter around the characterized POC algorithm and its explicit policy."""

    def __init__(self, policy: RecommendationPolicy = DEFAULT_RECOMMENDATION_POLICY) -> None:
        self._policy = policy

    @property
    def policy(self) -> RecommendationPolicy:
        return self._policy

    def rank_incidents(self, incidents: list[Incident]) -> list[Incident]:
        ranked = ranked_incidents(
            [incident.model_dump() for incident in incidents],
            policy=self._policy,
        )
        return [Incident.model_validate(incident) for incident in ranked]

    def recommend(self, request: OptimizationRequest) -> Recommendation:
        recommendation = recommend_assignment(
            request.incident.model_dump(),
            [crew.model_dump() for crew in request.crews],
            [assignment.model_dump() for assignment in request.assignments],
            policy=self._policy,
        )
        return Recommendation.model_validate(recommendation)
