from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.optimization.deterministic_engine import DeterministicOptimizationEngine
from app.optimization.policy import DEFAULT_RECOMMENDATION_POLICY, RecommendationPolicy
from app.services import build_services


def _incident(template, **changes):
    return template.model_copy(update=changes)


def test_phase_5_2_policy_has_explicit_versions_and_domain_tie_breakers() -> None:
    policy = DEFAULT_RECOMMENDATION_POLICY

    assert policy.algorithm_version == "deterministic-scoring-v2"
    assert policy.policy_version == "incident-priority-v1"
    assert [(rule.field, rule.direction) for rule in policy.incident_tie_breakers] == [
        ("severity", "descending"),
        ("age_minutes", "descending"),
        ("customers_out", "descending"),
        ("incident_id", "ascending"),
    ]


def test_incident_score_exposes_each_configured_factor_contribution() -> None:
    incident = build_services().incidents.get("INC-1001")

    result = DeterministicOptimizationEngine().evaluate_incidents([incident])[0]
    contributions = {factor.factor_id: factor for factor in result.score.contributions}

    assert result.score.incident_id == "INC-1001"
    assert result.score.algorithm_version == "deterministic-scoring-v2"
    assert result.score.policy_version == "incident-priority-v1"
    assert contributions["customers_out"].raw_value == 2840
    assert contributions["customers_out"].configured_value == 20
    assert contributions["customers_out"].contribution == 142
    assert contributions["critical_facility"].contribution == 80
    assert contributions["hazard"].contribution == 60
    assert contributions["incident_age"].contribution == 7
    assert contributions["severity"].raw_value == "critical"
    assert contributions["severity"].contribution == 120
    assert result.score.total_score == 409
    assert result.score.total_score == sum(
        contribution.contribution for contribution in result.score.contributions
    )
    assert set(contributions) == {
        factor.factor_id
        for factor in DEFAULT_RECOMMENDATION_POLICY.factors
        if factor.scope == "incident" and factor.status == "implemented"
    }


def test_configured_incident_weights_change_contributions_and_ranking() -> None:
    template = build_services().incidents.get("INC-1001")
    critical_incident = _incident(
        template,
        incident_id="INC-CRITICAL",
        customers_out=1,
        critical_facility=True,
        hazard="none",
        severity="low",
        age_minutes=0,
    )
    customer_incident = _incident(
        template,
        incident_id="INC-CUSTOMERS",
        customers_out=10_000,
        critical_facility=False,
        hazard="none",
        severity="low",
        age_minutes=0,
    )
    payload = deepcopy(DEFAULT_RECOMMENDATION_POLICY.model_dump())
    payload["policy_version"] = "incident-priority-critical-facility-test"
    payload["incident_scoring"]["critical_facility_bonus"] = 10_000
    engine = DeterministicOptimizationEngine(RecommendationPolicy.model_validate(payload))

    ranked = engine.evaluate_incidents([critical_incident, customer_incident])

    assert ranked[0].incident.incident_id == "INC-CRITICAL"
    critical_factors = {
        factor.factor_id: factor for factor in ranked[0].score.contributions
    }
    assert critical_factors["critical_facility"].configured_value == 10_000
    assert critical_factors["critical_facility"].contribution == 10_000


def test_equal_scores_use_severity_before_source_order() -> None:
    template = build_services().incidents.get("INC-1001")
    lower_severity = _incident(
        template,
        incident_id="INC-LOW",
        customers_out=0,
        critical_facility=True,
        hazard="none",
        severity="low",
        age_minutes=0,
    )
    higher_severity = _incident(
        template,
        incident_id="INC-HIGH",
        customers_out=200,
        critical_facility=False,
        hazard="none",
        severity="high",
        age_minutes=0,
    )

    ranked = DeterministicOptimizationEngine().evaluate_incidents(
        [lower_severity, higher_severity]
    )

    assert [result.score.total_score for result in ranked] == [90, 90]
    assert ranked[0].incident.incident_id == "INC-HIGH"


def test_equal_score_and_severity_use_age_then_customers_then_incident_id() -> None:
    template = build_services().incidents.get("INC-1001")
    younger = _incident(
        template,
        incident_id="INC-YOUNGER",
        customers_out=0,
        critical_facility=False,
        hazard="none",
        severity="low",
        age_minutes=10,
    )
    older = _incident(
        template,
        incident_id="INC-OLDER",
        customers_out=0,
        critical_facility=False,
        hazard="none",
        severity="low",
        age_minutes=19,
    )
    same_a = _incident(
        template,
        incident_id="INC-A",
        customers_out=0,
        critical_facility=False,
        hazard="none",
        severity="low",
        age_minutes=10,
    )
    same_b = _incident(
        template,
        incident_id="INC-B",
        customers_out=0,
        critical_facility=False,
        hazard="none",
        severity="low",
        age_minutes=10,
    )
    fewer_customers = _incident(
        template,
        incident_id="INC-CUSTOMERS-A",
        customers_out=0,
        critical_facility=False,
        hazard="none",
        severity="low",
        age_minutes=10,
    )
    more_customers = _incident(
        template,
        incident_id="INC-CUSTOMERS-Z",
        customers_out=19,
        critical_facility=False,
        hazard="none",
        severity="low",
        age_minutes=10,
    )

    age_ranked = DeterministicOptimizationEngine().rank_incidents([younger, older])
    customer_ranked = DeterministicOptimizationEngine().rank_incidents(
        [fewer_customers, more_customers]
    )
    id_ranked = DeterministicOptimizationEngine().rank_incidents([same_b, same_a])

    assert age_ranked[0].incident_id == "INC-OLDER"
    assert customer_ranked[0].incident_id == "INC-CUSTOMERS-Z"
    assert [incident.incident_id for incident in id_ranked] == ["INC-A", "INC-B"]


def test_ranked_incident_service_preserves_the_public_incident_shape() -> None:
    incident_payload = build_services().incidents.list_ranked()[0].model_dump()

    assert "score" not in incident_payload
    assert "contributions" not in incident_payload
    assert "algorithm_version" not in incident_payload
    assert "policy_version" not in incident_payload


@pytest.mark.parametrize(
    ("tie_breakers", "message"),
    [
        (
            [{"field": "unknown", "direction": "ascending", "description": "invalid"}],
            "unsupported incident tie-break fields",
        ),
        (
            [
                {"field": "incident_id", "direction": "ascending", "description": "first"},
                {"field": "incident_id", "direction": "descending", "description": "duplicate"},
            ],
            "must be unique",
        ),
        (
            [{"field": "source_order", "direction": "ascending", "description": "invalid"}],
            "must be used together",
        ),
    ],
)
def test_policy_rejects_invalid_incident_tie_breakers(tie_breakers, message) -> None:
    payload = DEFAULT_RECOMMENDATION_POLICY.model_dump()
    payload["incident_tie_breakers"] = tie_breakers

    with pytest.raises(ValidationError, match=message):
        RecommendationPolicy.model_validate(payload)
