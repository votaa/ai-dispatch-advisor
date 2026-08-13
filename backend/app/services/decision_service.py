from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..domain.models import Recommendation, RecommendationAction, RecommendationDecision
from .errors import DecisionConflictError, DecisionReasonRequiredError
from .incident_service import IncidentService


class DecisionService:
    def __init__(
        self,
        *,
        active_scenario_id: Callable[[], str],
        incidents: IncidentService,
        record_decision: Callable[..., dict[str, Any]],
        recent_decisions: Callable[[str, int], list[dict[str, Any]]],
    ) -> None:
        self._active_scenario_id = active_scenario_id
        self._incidents = incidents
        self._record_decision = record_decision
        self._recent_decisions = recent_decisions

    def record(
        self,
        *,
        incident_id: str,
        action: RecommendationAction,
        recommendation: Recommendation,
        reason: str | None = None,
        note: str | None = None,
    ) -> RecommendationDecision:
        self._incidents.get(incident_id)
        if recommendation.incident_id != incident_id:
            raise DecisionConflictError(incident_id, recommendation.incident_id)

        reason_source = reason if reason is not None else note
        normalized_reason = reason_source.strip() if reason_source else None
        if action in {"deferred", "overridden"} and not normalized_reason:
            raise DecisionReasonRequiredError(action)

        event = self._record_decision(
            scenario_id=self._active_scenario_id(),
            incident_id=incident_id,
            action=action,
            reason=normalized_reason,
            recommendation=recommendation.model_dump(),
        )
        return RecommendationDecision.model_validate(event)

    def recent(self, limit: int = 25) -> list[RecommendationDecision]:
        bounded_limit = max(1, min(limit, 100))
        return [
            RecommendationDecision.model_validate(event)
            for event in self._recent_decisions(self._active_scenario_id(), bounded_limit)
        ]
