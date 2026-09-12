from app import data_loader
from app.optimization.contracts import OptimizationRequest
from app.optimization.deterministic_engine import DeterministicOptimizationEngine
from app.services import build_services


def manifested_scenario_ids() -> list[str]:
    return sorted(
        path.name
        for path in data_loader.DATA_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def test_every_manifested_scenario_produces_a_valid_explained_recommendation() -> None:
    assert manifested_scenario_ids()

    for scenario_id in manifested_scenario_ids():
        data_loader.set_active_scenario(scenario_id)
        services = build_services()
        incidents = services.incidents.list_ranked()
        recommendation = services.recommendations.recommend()

        assert incidents, scenario_id
        assert recommendation.incident_id == incidents[0].incident_id
        assert recommendation.explanation is not None
        assert recommendation.explanation.algorithm_version == "deterministic-scoring-v3"
        assert recommendation.explanation.policy_version == "incident-priority-cf-level-v1"
        assert recommendation.explanation.confidence_rationale.reason
        assert all(
            candidate.crew_id
            for candidate in recommendation.alternatives
        )


def test_missing_travel_estimate_is_explicitly_warned_and_can_be_infeasible() -> None:
    data_loader.set_active_scenario("base")
    services = build_services()
    incident = services.incidents.get("INC-1001").model_copy(update={"required_skill": "general"})
    crew = next(crew for crew in services.crews.list() if crew.crew_id == "CR-01").model_copy(
        update={"travel_minutes_to_selected_incident": 999}
    )
    request = OptimizationRequest(
        scenario_id="base",
        incident=incident,
        crews=[crew],
        assignments=[],
    )

    recommendation = DeterministicOptimizationEngine().recommend(request)

    assert recommendation.recommended_crew is None
    assert recommendation.explanation is not None
    assert recommendation.explanation.data_quality_warnings == [
        "One or more crew travel estimates are unavailable and were treated as the configured missing-data value."
    ]
    assert any(
        constraint.status == "not_satisfied"
        for constraint in recommendation.explanation.constraints
    )
