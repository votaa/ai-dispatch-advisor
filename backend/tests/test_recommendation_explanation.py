from app import data_loader
from app.services import build_services


def test_explanation_contains_structured_score_and_excluded_candidates() -> None:
    data_loader.set_active_scenario("base")
    recommendation = build_services().recommendations.recommend("INC-1001")

    assert recommendation.explanation is not None
    assert {
        "customers_out",
        "critical_facility",
        "hazard",
        "incident_age",
        "severity",
    } <= {factor.factor_id for factor in recommendation.explanation.factors}
    assert recommendation.explanation.confidence_rationale.reason
    assert all(
        constraint.status == "satisfied"
        for constraint in recommendation.explanation.constraints
    )
    assert recommendation.explanation.excluded_candidates
    assert recommendation.explanation.assumptions


def test_no_feasible_crew_explanation_is_low_confidence_and_actionable() -> None:
    data_loader.set_active_scenario("crew-shortage")
    recommendation = build_services().recommendations.recommend()

    assert recommendation.recommended_crew is None
    assert recommendation.explanation is not None
    assert recommendation.explanation.confidence_rationale.score is None
    assert recommendation.explanation.confidence_rationale.threshold == 115
    assert "No crew satisfied" in recommendation.explanation.confidence_rationale.reason
    assert any(
        constraint.status == "not_satisfied"
        for constraint in recommendation.explanation.constraints
    )
