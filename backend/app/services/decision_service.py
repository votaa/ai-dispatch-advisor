from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..domain.models import Recommendation, RecommendationAction, RecommendationDecision
from .crew_service import CrewService
from .errors import (
    DecisionConflictError,
    DecisionCrewSelectionError,
    DecisionReasonRequiredError,
)
from .incident_service import IncidentService


class DecisionService:
    def __init__(
        self,
        *,
        active_scenario_id: Callable[[], str],
        crews: CrewService,
        incidents: IncidentService,
        record_decision: Callable[..., dict[str, Any]],
        recent_decisions: Callable[[str, int], list[dict[str, Any]]],
    ) -> None:
        self._active_scenario_id = active_scenario_id
        self._crews = crews
        self._incidents = incidents
        self._record_decision = record_decision
        self._recent_decisions = recent_decisions

    def record(
        self,
        *,
        incident_id: str,
        action: RecommendationAction,
        recommendation: Recommendation,
        selected_crew_id: str | None = None,
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

        recommended_crew_id = (
            recommendation.recommended_crew.crew_id
            if recommendation.recommended_crew is not None
            else None
        )
        chosen_crew_id = selected_crew_id or recommended_crew_id
        creates_assignment = action == "accepted" or (
            action == "modified"
            and chosen_crew_id is not None
            and chosen_crew_id != recommended_crew_id
        )

        if action == "accepted" and not chosen_crew_id:
            raise DecisionCrewSelectionError("none", "No crew is available for this assignment action")
        if action == "accepted" and chosen_crew_id != recommended_crew_id:
            raise DecisionCrewSelectionError(
                chosen_crew_id or "none",
                "Accept can only assign the recommended crew; use Modify for a ranked alternative",
            )

        if chosen_crew_id and chosen_crew_id != recommended_crew_id:
            alternative_ids = {candidate.crew_id for candidate in recommendation.alternatives}
            if chosen_crew_id not in alternative_ids:
                raise DecisionCrewSelectionError(
                    chosen_crew_id,
                    "Selected crew is not a ranked feasible alternative for this recommendation",
                )
            if action != "modified":
                raise DecisionCrewSelectionError(
                    chosen_crew_id,
                    "A ranked alternative must be recorded as a modified assignment",
                )
            if not normalized_reason:
                raise DecisionReasonRequiredError("modified")

        if creates_assignment and chosen_crew_id:
            live_crew = next(
                (crew for crew in self._crews.list() if crew.crew_id == chosen_crew_id),
                None,
            )
            if live_crew is None:
                raise DecisionCrewSelectionError(chosen_crew_id, "Selected crew no longer exists")
            if live_crew.status != "available" or live_crew.assigned_incidents:
                raise DecisionCrewSelectionError(
                    chosen_crew_id,
                    "Selected crew is no longer available; refresh the recommendation",
                )

        event = self._record_decision(
            scenario_id=self._active_scenario_id(),
            incident_id=incident_id,
            action=action,
            create_assignment=creates_assignment,
            reason=normalized_reason,
            recommendation=recommendation.model_dump(),
            selected_crew_id=chosen_crew_id,
        )
        return RecommendationDecision.model_validate(event)

    def recent(self, limit: int = 25) -> list[RecommendationDecision]:
        bounded_limit = max(1, min(limit, 100))
        return [
            RecommendationDecision.model_validate(event)
            for event in self._recent_decisions(self._active_scenario_id(), bounded_limit)
        ]
