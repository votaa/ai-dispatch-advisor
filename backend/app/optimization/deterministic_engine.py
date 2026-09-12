from __future__ import annotations

from ..domain.models import (
    ConfidenceRationale,
    ExcludedCandidate,
    ExplanationConstraint,
    ExplanationFactor,
    Incident,
    Recommendation,
    RecommendationExplanation,
)
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
            if self._incident_is_rankable(incident)
        ]
        if self._policy.incident_scoring.critical_facility_weights is not None:
            for rule in reversed(self._policy.incident_tie_breakers):
                ranked.sort(
                    key=lambda result, field=rule.field: self._operational_rank_value(
                        result,
                        field,
                    ),
                    reverse=rule.direction == "descending",
                )
            return ranked
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

    def _incident_is_rankable(self, incident: Incident) -> bool:
        if self._policy.incident_scoring.critical_facility_weights is None:
            return True
        return (
            incident.ranking_status != "withheld"
            and (not incident.critical_facility or incident.critical_facility_level is not None)
        )

    def _score_incident(self, incident: Incident) -> IncidentScore:
        scoring = self._policy.incident_scoring
        severity = incident.severity.lower()
        hazard_present = incident.hazard.lower() != "none"
        facility_weights = scoring.critical_facility_weights
        if facility_weights is None:
            facility_raw_value = incident.critical_facility
            facility_configured_value = scoring.critical_facility_bonus
            facility_contribution = (
                scoring.critical_facility_bonus if incident.critical_facility else 0
            )
            facility_calculation = "conditional_bonus"
        else:
            facility_raw_value = (
                f"level_{incident.critical_facility_level}"
                if incident.critical_facility_level is not None
                else "none"
            )
            facility_configured_value = facility_weights.for_level(
                incident.critical_facility_level
            )
            facility_contribution = facility_configured_value
            facility_calculation = "configured_weight"

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
                raw_value=facility_raw_value,
                configured_value=facility_configured_value,
                contribution=facility_contribution,
                calculation=facility_calculation,
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

    def _operational_rank_value(
        self,
        result: RankedIncident,
        field: str,
    ) -> int | str:
        incident = result.incident
        if field == "score_band":
            return self._score_band_rank(result.score.total_score)
        if field == "hazard_presence":
            return int(incident.hazard.strip().lower() != "none")
        if field == "total_score":
            return result.score.total_score
        if field == "critical_facility_level":
            return (
                4 - incident.critical_facility_level
                if incident.critical_facility_level is not None
                else 0
            )
        return self._incident_tie_value(incident, field)

    def _score_band_rank(self, score: int) -> int:
        for index, band in enumerate(self._policy.score_bands):
            if score >= band.minimum and (band.maximum is None or score <= band.maximum):
                return index
        raise ValueError(f"Score {score} does not belong to a configured operational band")

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
        recommendation["explanation"] = self._build_explanation(
            request,
            feasibility,
            recommendation,
        ).model_dump()
        return Recommendation.model_validate(recommendation)

    def _build_explanation(
        self,
        request: OptimizationRequest,
        feasibility: list[CrewFeasibility],
        recommendation: dict,
    ) -> RecommendationExplanation:
        incident_score = self.evaluate_incidents([request.incident])[0].score
        selected = recommendation.get("recommended_crew")
        selected_score = selected.get("suitability_score") if selected else None
        threshold = self._policy.crew_scoring.high_confidence_threshold
        if selected is None:
            confidence_reason = (
                "No crew satisfied all active blocking constraints; supervisor review is required."
            )
        elif recommendation["confidence"] == "high":
            confidence_reason = (
                "Selected crew satisfies all active blocking constraints and exceeds the high-confidence threshold."
            )
        else:
            confidence_reason = (
                "Selected crew satisfies all active blocking constraints but remains below the high-confidence threshold."
            )

        factors = [
            ExplanationFactor(
                factor_id=contribution.factor_id,
                description=f"Incident {contribution.factor_id.replace('_', ' ')} contribution.",
                contribution=contribution.contribution,
                evidence=(
                    "Resolved Level "
                    f"{request.incident.critical_facility_level} from facility IDs: "
                    + ", ".join(request.incident.matched_critical_facility_ids)
                    if contribution.factor_id == "critical_facility"
                    and request.incident.critical_facility_level is not None
                    else f"Raw value: {contribution.raw_value}"
                ),
            )
            for contribution in incident_score.contributions
        ]
        if selected is not None:
            factors.extend(
                [
                    ExplanationFactor(
                        factor_id="crew_suitability",
                        description="Selected crew suitability score.",
                        contribution=selected.get("suitability_score"),
                        evidence=f"Estimated travel: {selected.get('estimated_travel_minutes')} minutes",
                    ),
                    ExplanationFactor(
                        factor_id="capability_match",
                        description="Required skill capability match.",
                        contribution=(
                            self._policy.crew_scoring.capability_match_bonus
                            if selected.get("capability_match")
                            else 0
                        ),
                        evidence=str(selected.get("capability")),
                    ),
                    ExplanationFactor(
                        factor_id="storm_readiness",
                        description="Storm readiness bonus.",
                        contribution=(
                            self._policy.crew_scoring.storm_ready_bonus
                            if selected.get("storm_ready")
                            else 0
                        ),
                        evidence=str(selected.get("storm_ready")),
                    ),
                ]
            )
        enabled_constraints = [
            constraint
            for constraint in self._policy.constraints
            if constraint.scope == "crew" and constraint.blocking and constraint.status == "implemented"
        ]
        selected_feasibility = next(
            (result for result in feasibility if selected and result.crew_id == selected.get("crew_id")),
            None,
        )
        rejected_constraint_ids = {
            reason.constraint_id
            for reason in (selected_feasibility.exclusions if selected_feasibility else [])
        }
        constraints = [
            ExplanationConstraint(
                constraint_id=constraint.constraint_id,
                status=(
                    "satisfied"
                    if selected is not None and constraint.constraint_id not in rejected_constraint_ids
                    else "not_satisfied"
                ),
                description=constraint.description,
            )
            for constraint in enabled_constraints
        ]
        excluded_candidates = [
            ExcludedCandidate(
                crew_id=result.crew_id,
                reasons=[reason.message for reason in result.exclusions],
            )
            for result in feasibility
            if not result.feasible
        ]
        data_quality_warnings = []
        if any(
            crew.travel_minutes_to_selected_incident == self._policy.crew_scoring.missing_travel_minutes
            for crew in request.crews
        ):
            data_quality_warnings.append(
                "One or more crew travel estimates are unavailable and were treated as the configured missing-data value."
            )
        return RecommendationExplanation(
            confidence_rationale=ConfidenceRationale(
                score=selected_score,
                threshold=threshold,
                reason=confidence_reason,
            ),
            factors=factors,
            constraints=constraints,
            excluded_candidates=excluded_candidates,
            assumptions=[
                "Shift sufficiency currently covers estimated travel time only; repair duration is not modeled.",
                "Recommendation remains advisory and requires dispatcher approval.",
            ],
            data_quality_warnings=data_quality_warnings,
            algorithm_version=self._policy.algorithm_version,
            policy_version=self._policy.policy_version,
        )
