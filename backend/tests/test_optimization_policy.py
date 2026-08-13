from copy import deepcopy

import pytest
from pydantic import ValidationError

from app import data_loader
from app.domain.models import Assignment
from app.optimization import OptimizationRequest
from app.optimization.deterministic_engine import DeterministicOptimizationEngine
from app.optimization.policy import DEFAULT_RECOMMENDATION_POLICY, RecommendationPolicy
from app.services import build_services


def test_default_policy_versions_and_rule_classification_are_stable() -> None:
    policy = DEFAULT_RECOMMENDATION_POLICY

    assert policy.algorithm_version == "deterministic-scoring-v1"
    assert policy.policy_version == "poc-baseline-v1"
    assert {factor.factor_id for factor in policy.factors} == {
        "customers_out",
        "critical_facility",
        "hazard",
        "incident_age",
        "severity",
        "travel_time",
        "capability_match",
        "storm_readiness",
    }
    assert {
        constraint.constraint_id
        for constraint in policy.constraints
        if constraint.status == "implemented" and constraint.blocking
    } == {"crew_available", "crew_unassigned", "scenario_context", "human_approval"}
    assert {
        constraint.constraint_id
        for constraint in policy.constraints
        if constraint.status == "planned"
    } == {"crew_capability_required", "shift_sufficiency"}


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("incident_scoring", "customers_out_divisor"), 0, "greater than 0"),
        (("crew_scoring", "travel_minute_penalty"), -1, "greater than or equal to 0"),
        (
            ("incident_scoring", "severity_weights"),
            {"critical": 120, "high": -1, "medium": 40, "low": 10},
            "greater than or equal to 0",
        ),
    ],
)
def test_policy_rejects_invalid_scoring_configuration(path, value, message) -> None:
    payload = DEFAULT_RECOMMENDATION_POLICY.model_dump()
    payload[path[0]][path[1]] = value

    with pytest.raises(ValidationError, match=message):
        RecommendationPolicy.model_validate(payload)


def test_policy_rejects_undeclared_fields() -> None:
    payload = DEFAULT_RECOMMENDATION_POLICY.model_dump()
    payload["unexpected"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RecommendationPolicy.model_validate(payload)


def test_default_policy_is_immutable() -> None:
    with pytest.raises(ValidationError, match="Instance is frozen"):
        DEFAULT_RECOMMENDATION_POLICY.policy_version = "changed"
    with pytest.raises(ValidationError, match="Instance is frozen"):
        DEFAULT_RECOMMENDATION_POLICY.incident_scoring.severity_weights.high = 999


def test_custom_policy_is_consumed_by_the_deterministic_engine() -> None:
    services = build_services()
    template = services.incidents.get("INC-1001")
    critical_incident = template.model_copy(
        update={
            "incident_id": "INC-CRITICAL",
            "customers_out": 1,
            "critical_facility": True,
            "hazard": "none",
            "severity": "low",
            "age_minutes": 0,
        }
    )
    customer_incident = template.model_copy(
        update={
            "incident_id": "INC-CUSTOMERS",
            "customers_out": 10_000,
            "critical_facility": False,
            "hazard": "none",
            "severity": "low",
            "age_minutes": 0,
        }
    )
    incidents = [critical_incident, customer_incident]
    payload = deepcopy(DEFAULT_RECOMMENDATION_POLICY.model_dump())
    payload["incident_scoring"]["critical_facility_bonus"] = 10_000
    engine = DeterministicOptimizationEngine(RecommendationPolicy.model_validate(payload))

    baseline_ranked = DeterministicOptimizationEngine().rank_incidents(incidents)
    custom_ranked = engine.rank_incidents(incidents)

    assert baseline_ranked[0].incident_id == "INC-CUSTOMERS"
    assert custom_ranked[0].incident_id == "INC-CRITICAL"


def test_optimization_request_rejects_cross_scenario_assignments() -> None:
    services = build_services()
    incident = services.incidents.get("INC-1001")
    assignment = Assignment.model_validate(
        {
            "assignment_id": "AS-MISMATCH",
            "scenario_id": "storm",
            "incident_id": "STM-2001",
            "crew_id": "SC-01",
            "status": "active",
            "assigned_at": "2026-08-01T12:00:00-04:00",
            "notes": "test",
        }
    )

    with pytest.raises(ValidationError, match="must belong to the optimization request scenario"):
        OptimizationRequest(
            scenario_id="base",
            incident=incident,
            crews=services.crews.list(),
            assignments=[assignment],
        )


@pytest.mark.parametrize(
    ("scenario_id", "incident_id", "action", "crew_id", "score", "alternatives"),
    [
        ("base", "INC-1001", "Assign crew", "CR-01", 132, [("CR-04", 128), ("CR-06", 119), ("CR-03", 65)]),
        ("storm", "STM-2001", "Assign crew", "SC-06", 129, [("SC-05", 86), ("SC-03", 83), ("SC-08", 81)]),
        ("crew-shortage", "CRS-3001", "Defer and escalate", None, None, []),
        ("critical-facility", "CFI-4001", "Assign crew", "FC-01", 138, [("FC-02", 130), ("FC-07", 121), ("FC-03", 92)]),
    ],
)
def test_poc_baseline_recommendations_are_characterized(
    scenario_id,
    incident_id,
    action,
    crew_id,
    score,
    alternatives,
) -> None:
    data_loader.set_active_scenario(scenario_id)
    services = build_services()

    ranked = services.incidents.list_ranked()
    recommendation = services.recommendations.recommend()

    assert ranked[0].incident_id == incident_id
    assert recommendation.recommended_action == action
    assert (
        recommendation.recommended_crew.crew_id if recommendation.recommended_crew else None
    ) == crew_id
    assert (
        recommendation.recommended_crew.suitability_score
        if recommendation.recommended_crew
        else None
    ) == score
    assert [(candidate.crew_id, candidate.suitability_score) for candidate in recommendation.alternatives] == alternatives
