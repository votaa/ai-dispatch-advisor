from app import data_loader
from app.optimization.contracts import OptimizationRequest
from app.optimization.deterministic_engine import DeterministicOptimizationEngine
from app.services import build_services


def test_crew_feasibility_reports_each_blocking_exclusion_reason() -> None:
    data_loader.set_active_scenario("base")
    services = build_services()
    incident = services.incidents.get("INC-1001").model_copy(update={"required_skill": "line"})
    crew = next(crew for crew in services.crews.list() if crew.crew_id == "CR-01").model_copy(
        update={
            "status": "assigned",
            "capability": "vegetation",
            "shift_remaining_hours": 0.25,
            "travel_minutes_to_selected_incident": 30,
        }
    )
    request = OptimizationRequest(
        scenario_id="base",
        incident=incident,
        crews=[crew],
        assignments=[],
    )

    result = DeterministicOptimizationEngine().evaluate_crew_feasibility(request)[0]

    assert result.feasible is False
    assert [reason.constraint_id for reason in result.exclusions] == [
        "crew_available",
        "crew_capability_required",
        "shift_sufficiency",
    ]
    assert result.exclusions[1].details == {
        "required_skill": "line",
        "capability": "vegetation",
    }
    assert result.exclusions[2].details["travel_minutes"] == 30


def test_phase_5_3_filters_infeasible_crews_before_scoring() -> None:
    data_loader.set_active_scenario("base")
    services = build_services()
    incident = services.incidents.get("INC-1001")
    request = OptimizationRequest(
        scenario_id="base",
        incident=incident,
        crews=services.crews.list(),
        assignments=services.assignments.list_active(),
    )

    feasibility = DeterministicOptimizationEngine().evaluate_crew_feasibility(request)
    recommendation = DeterministicOptimizationEngine().recommend(request)
    feasible_ids = {item.crew_id for item in feasibility if item.feasible}
    returned_ids = {
        candidate.crew_id
        for candidate in [recommendation.recommended_crew, *recommendation.alternatives]
        if candidate is not None
    }

    assert returned_ids <= feasible_ids
