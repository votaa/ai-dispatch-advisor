from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from ..domain.models import DomainModel


PolicyScope = Literal["incident", "crew", "recommendation"]
PolicyRuleStatus = Literal["implemented", "planned"]
SortDirection = Literal["ascending", "descending", "source_order"]


class PolicyModel(DomainModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SeverityWeights(PolicyModel):
    critical: int = Field(default=120, ge=0)
    high: int = Field(default=80, ge=0)
    medium: int = Field(default=40, ge=0)
    low: int = Field(default=10, ge=0)

    def for_severity(self, severity: str) -> int:
        return {
            "critical": self.critical,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
        }.get(severity, 0)


class IncidentScoringPolicy(PolicyModel):
    customers_out_divisor: int = Field(default=20, gt=0)
    critical_facility_bonus: int = Field(default=80, ge=0)
    hazard_bonus: int = Field(default=60, ge=0)
    age_minutes_divisor: int = Field(default=10, gt=0)
    severity_weights: SeverityWeights = Field(default_factory=SeverityWeights)


class CrewScoringPolicy(PolicyModel):
    base_score: int = 100
    travel_minute_penalty: int = Field(default=1, ge=0)
    capability_match_bonus: int = Field(default=40, ge=0)
    storm_ready_bonus: int = Field(default=10, ge=0)
    minimum_score: int = Field(default=0, ge=0)
    high_confidence_threshold: int = Field(default=115, ge=0)
    missing_travel_minutes: int = Field(default=999, gt=0)


class FactorDefinition(PolicyModel):
    factor_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    scope: PolicyScope
    description: str = Field(min_length=1)
    status: PolicyRuleStatus = "implemented"


class ConstraintDefinition(PolicyModel):
    constraint_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    scope: PolicyScope
    description: str = Field(min_length=1)
    blocking: bool
    status: PolicyRuleStatus = "implemented"


class AssumptionDefinition(PolicyModel):
    assumption_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    status: PolicyRuleStatus = "implemented"


class DataQualityDefinition(PolicyModel):
    condition_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    status: PolicyRuleStatus = "planned"


class TieBreakRule(PolicyModel):
    field: str = Field(min_length=1)
    direction: SortDirection
    description: str = Field(min_length=1)
    status: PolicyRuleStatus = "implemented"


class RecommendationPolicy(PolicyModel):
    """Versioned Phase 5 policy contract for deterministic recommendation behavior."""

    algorithm_version: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    policy_version: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    incident_scoring: IncidentScoringPolicy
    crew_scoring: CrewScoringPolicy
    factors: list[FactorDefinition]
    constraints: list[ConstraintDefinition]
    assumptions: list[AssumptionDefinition]
    data_quality_conditions: list[DataQualityDefinition]
    incident_tie_breakers: list[TieBreakRule]
    crew_tie_breakers: list[TieBreakRule]

    @field_validator(
        "factors",
        "constraints",
        "assumptions",
        "data_quality_conditions",
    )
    @classmethod
    def validate_unique_rule_ids(cls, rules):
        identifiers = [
            getattr(rule, "factor_id", None)
            or getattr(rule, "constraint_id", None)
            or getattr(rule, "assumption_id", None)
            or getattr(rule, "condition_id", None)
            for rule in rules
        ]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("policy rule identifiers must be unique within their category")
        return rules

    @field_validator("incident_tie_breakers")
    @classmethod
    def validate_incident_tie_breakers(cls, rules: list[TieBreakRule]) -> list[TieBreakRule]:
        allowed = {"severity", "age_minutes", "customers_out", "incident_id", "source_order"}
        fields = [rule.field for rule in rules]
        unsupported = sorted(set(fields) - allowed)
        if unsupported:
            raise ValueError(f"unsupported incident tie-break fields: {', '.join(unsupported)}")
        if len(fields) != len(set(fields)):
            raise ValueError("incident tie-break fields must be unique")
        for rule in rules:
            if (rule.field == "source_order") != (rule.direction == "source_order"):
                raise ValueError("source_order field and direction must be used together")
        return rules


POC_BASELINE_RECOMMENDATION_POLICY = RecommendationPolicy(
    algorithm_version="deterministic-scoring-v1",
    policy_version="poc-baseline-v1",
    incident_scoring=IncidentScoringPolicy(),
    crew_scoring=CrewScoringPolicy(),
    factors=[
        FactorDefinition(
            factor_id="customers_out",
            scope="incident",
            description="Increase priority as the number of affected customers increases.",
        ),
        FactorDefinition(
            factor_id="critical_facility",
            scope="incident",
            description="Increase priority when a critical facility is affected.",
        ),
        FactorDefinition(
            factor_id="hazard",
            scope="incident",
            description="Increase priority when the incident reports a hazard.",
        ),
        FactorDefinition(
            factor_id="incident_age",
            scope="incident",
            description="Increase priority as an incident remains unresolved.",
        ),
        FactorDefinition(
            factor_id="severity",
            scope="incident",
            description="Apply the configured weight for the incident severity.",
        ),
        FactorDefinition(
            factor_id="travel_time",
            scope="crew",
            description="Reduce crew suitability as estimated travel time increases.",
        ),
        FactorDefinition(
            factor_id="capability_match",
            scope="crew",
            description="Increase suitability when crew capability matches required work.",
        ),
        FactorDefinition(
            factor_id="storm_readiness",
            scope="crew",
            description="Increase suitability for a storm-ready crew.",
        ),
    ],
    constraints=[
        ConstraintDefinition(
            constraint_id="crew_available",
            scope="crew",
            description="Only crews with available status may be considered.",
            blocking=True,
        ),
        ConstraintDefinition(
            constraint_id="crew_unassigned",
            scope="crew",
            description="A crew with an active assignment may not be considered.",
            blocking=True,
        ),
        ConstraintDefinition(
            constraint_id="scenario_context",
            scope="recommendation",
            description="Optimization inputs must belong to the active scenario context.",
            blocking=True,
        ),
        ConstraintDefinition(
            constraint_id="crew_capability_required",
            scope="crew",
            description="A crew must satisfy required skill and certification policy.",
            blocking=True,
            status="planned",
        ),
        ConstraintDefinition(
            constraint_id="shift_sufficiency",
            scope="crew",
            description="Remaining shift time must cover travel and expected work duration.",
            blocking=True,
            status="planned",
        ),
        ConstraintDefinition(
            constraint_id="human_approval",
            scope="recommendation",
            description="A recommendation cannot dispatch a crew without dispatcher approval.",
            blocking=True,
        ),
    ],
    assumptions=[
        AssumptionDefinition(
            assumption_id="crew_status_current",
            description="Crew availability and assignment status are current.",
        ),
        AssumptionDefinition(
            assumption_id="travel_estimate_valid",
            description="The scenario travel estimate is valid for the selected incident.",
        ),
        AssumptionDefinition(
            assumption_id="incident_data_current",
            description="Incident impact, hazard, severity, and age are current.",
        ),
    ],
    data_quality_conditions=[
        DataQualityDefinition(
            condition_id="missing_or_stale_crew_status",
            description="Missing or stale crew state must reduce confidence.",
        ),
        DataQualityDefinition(
            condition_id="missing_or_stale_travel_time",
            description="Missing or stale travel estimates must reduce confidence.",
        ),
        DataQualityDefinition(
            condition_id="missing_or_stale_incident_context",
            description="Missing or stale incident context must reduce confidence.",
        ),
    ],
    incident_tie_breakers=[
        TieBreakRule(
            field="source_order",
            direction="source_order",
            description="Preserve current stable-sort behavior for the POC baseline.",
        )
    ],
    crew_tie_breakers=[
        TieBreakRule(
            field="source_order",
            direction="source_order",
            description="Preserve current stable-sort behavior for the POC baseline.",
        )
    ],
)


DEFAULT_RECOMMENDATION_POLICY = RecommendationPolicy.model_validate(
    {
        **POC_BASELINE_RECOMMENDATION_POLICY.model_dump(),
        "algorithm_version": "deterministic-scoring-v2",
        "policy_version": "incident-priority-v1",
        "constraints": [
            {
                **constraint,
                "status": (
                    "implemented"
                    if constraint["constraint_id"]
                    in {"crew_capability_required", "shift_sufficiency"}
                    else constraint["status"]
                ),
            }
            for constraint in POC_BASELINE_RECOMMENDATION_POLICY.model_dump()["constraints"]
        ],
        "incident_tie_breakers": [
            {
                "field": "severity",
                "direction": "descending",
                "description": "Prefer higher configured severity when total scores tie.",
            },
            {
                "field": "age_minutes",
                "direction": "descending",
                "description": "Prefer the older incident when score and severity tie.",
            },
            {
                "field": "customers_out",
                "direction": "descending",
                "description": "Prefer greater customer impact when earlier criteria tie.",
            },
            {
                "field": "incident_id",
                "direction": "ascending",
                "description": "Use the stable incident identifier as the final tie-breaker.",
            },
        ],
    }
)
