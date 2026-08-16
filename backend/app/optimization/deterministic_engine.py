from __future__ import annotations

from ..domain.models import Incident, Recommendation
from ..recommendations import recommend_assignment
from .contracts import (
    CrewExclusionReason,
    CrewFeasibility,
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

    def evaluate_crew_feasibility(self, request: OptimizationRequest) -> list[CrewFeasibility]:
        """Evaluate blocking crew constraints before suitability scoring."""
        active_crews = {
            assignment.crew_id
            for assignment in request.assignments
            if assignment.status.lower() == "active"
        }
        required_skill = request.incident.required_skill.strip().lower()
        scoring = self._policy.crew_scoring
        enabled_constraints = {
            constraint.constraint_id
            for constraint in self._policy.constraints
            if constraint.status == "implemented" and constraint.blocking
        }
        results: list[CrewFeasibility] = []
        for crew in request.crews:
            exclusions: list[CrewExclusionReason] = []
            if (
                "crew_available" in enabled_constraints
                and crew.status.strip().lower() != "available"
            ):
                exclusions.append(
                    CrewExclusionReason(
                        constraint_id="crew_available",
                        message="Crew status is not available.",
                        details={"status": crew.status},
                    )
                )
            if "crew_unassigned" in enabled_constraints and crew.crew_id in active_crews:
                exclusions.append(
                    CrewExclusionReason(
                        constraint_id="crew_unassigned",
                        message="Crew already has an active assignment.",
                        details={"crew_id": crew.crew_id},
                    )
                )
            capability = crew.capability.strip().lower()
            if (
                "crew_capability_required" in enabled_constraints
                and required_skill != "general"
                and capability != required_skill
            ):
                exclusions.append(
                    CrewExclusionReason(
                        constraint_id="crew_capability_required",
                        message="Crew capability does not satisfy the incident required skill.",
                        details={"required_skill": required_skill, "capability": capability},
                    )
                )
            travel_minutes = crew.travel_minutes_to_selected_incident
            available_minutes = float(crew.shift_remaining_hours) * 60
            if "shift_sufficiency" in enabled_constraints and travel_minutes > available_minutes:
                exclusions.append(
                    CrewExclusionReason(
                        constraint_id="shift_sufficiency",
                        message="Remaining shift does not cover estimated travel time.",
                        details={
                            "travel_minutes": travel_minutes,
                            "available_shift_minutes": available_minutes,
                        },
                    )
                )
            results.append(
                CrewFeasibility(
                    crew_id=crew.crew_id,
                    feasible=not exclusions,
                    exclusions=exclusions,
                )
            )
        return results

    def recommend(self, request: OptimizationRequest) -> Recommendation:
        feasibility = self.evaluate_crew_feasibility(request)
        feasible_crew_ids = {result.crew_id for result in feasibility if result.feasible}
        recommendation = recommend_assignment(
            request.incident.model_dump(),
            [crew.model_dump() for crew in request.crews],
            [assignment.model_dump() for assignment in request.assignments],
            policy=self._policy,
            feasible_crew_ids=feasible_crew_ids,
        )
        return Recommendation.model_validate(recommendation)
