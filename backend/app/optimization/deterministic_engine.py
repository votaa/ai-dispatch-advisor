from __future__ import annotations

from ..domain.models import Incident, Recommendation
from ..recommendations import recommend_assignment
from .contracts import (
    IncidentScore,
    IncidentScoreContribution,
    OptimizationRequest,
    RankedIncident,
)
from .policy import DEFAULT_RECOMMENDATION_POLICY, RecommendationPolicy


class DeterministicOptimizationEngine:
    """Adapter around the characterized POC algorithm and its explicit policy."""

    def __init__(self, policy: RecommendationPolicy = DEFAULT_RECOMMENDATION_POLICY) -> None:
        self._policy = policy

    @property
    def policy(self) -> RecommendationPolicy:
        return self._policy

    def rank_incidents(self, incidents: list[Incident]) -> list[Incident]:
        return [result.incident for result in self.evaluate_incidents(incidents)]

    def evaluate_incidents(self, incidents: list[Incident]) -> list[RankedIncident]:
        ranked = [
            RankedIncident(incident=incident, score=self._score_incident(incident))
            for incident in incidents
        ]
        for rule in reversed(self._policy.incident_tie_breakers):
            if rule.direction == "source_order":
                continue
            ranked.sort(
                key=lambda result, field=rule.field: self._incident_tie_value(
                    result.incident,
                    field,
                ),
                reverse=rule.direction == "descending",
            )
        ranked.sort(key=lambda result: result.score.total_score, reverse=True)
        return ranked

    def _score_incident(self, incident: Incident) -> IncidentScore:
        scoring = self._policy.incident_scoring
        severity = incident.severity.lower()
        hazard_present = incident.hazard.lower() != "none"
        contributions = [
            IncidentScoreContribution(
                factor_id="customers_out",
                raw_value=incident.customers_out,
                configured_value=scoring.customers_out_divisor,
                contribution=incident.customers_out // scoring.customers_out_divisor,
                calculation="integer_division",
            ),
            IncidentScoreContribution(
                factor_id="critical_facility",
                raw_value=incident.critical_facility,
                configured_value=scoring.critical_facility_bonus,
                contribution=scoring.critical_facility_bonus if incident.critical_facility else 0,
                calculation="conditional_bonus",
            ),
            IncidentScoreContribution(
                factor_id="hazard",
                raw_value=incident.hazard,
                configured_value=scoring.hazard_bonus,
                contribution=scoring.hazard_bonus if hazard_present else 0,
                calculation="conditional_bonus",
            ),
            IncidentScoreContribution(
                factor_id="incident_age",
                raw_value=incident.age_minutes,
                configured_value=scoring.age_minutes_divisor,
                contribution=incident.age_minutes // scoring.age_minutes_divisor,
                calculation="integer_division",
            ),
            IncidentScoreContribution(
                factor_id="severity",
                raw_value=severity,
                configured_value=scoring.severity_weights.for_severity(severity),
                contribution=scoring.severity_weights.for_severity(severity),
                calculation="configured_weight",
            ),
        ]
        return IncidentScore(
            incident_id=incident.incident_id,
            total_score=sum(factor.contribution for factor in contributions),
            contributions=contributions,
            algorithm_version=self._policy.algorithm_version,
            policy_version=self._policy.policy_version,
        )

    def _incident_tie_value(self, incident: Incident, field: str) -> int | str:
        if field == "severity":
            return self._policy.incident_scoring.severity_weights.for_severity(
                incident.severity.lower()
            )
        if field == "age_minutes":
            return incident.age_minutes
        if field == "customers_out":
            return incident.customers_out
        if field == "incident_id":
            return incident.incident_id
        raise ValueError(f"Unsupported incident tie-break field: {field}")

    def recommend(self, request: OptimizationRequest) -> Recommendation:
        recommendation = recommend_assignment(
            request.incident.model_dump(),
            [crew.model_dump() for crew in request.crews],
            [assignment.model_dump() for assignment in request.assignments],
            policy=self._policy,
        )
        return Recommendation.model_validate(recommendation)
