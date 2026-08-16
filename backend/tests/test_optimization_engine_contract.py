from app import data_loader
from app.domain.models import Recommendation
from app.optimization.contracts import (
    IncidentScore,
    OptimizationRequest,
    RankedIncident,
    CrewFeasibility,
)
from app.optimization.deterministic_engine import DeterministicOptimizationEngine
from app.optimization.policy import DEFAULT_RECOMMENDATION_POLICY
from app.services import build_services


class FakeOptimizationEngine:
    """Minimal conforming adapter proving services do not depend on the implementation."""

    policy = DEFAULT_RECOMMENDATION_POLICY

    def rank_incidents(self, incidents):
        return list(reversed(incidents))

    def evaluate_incidents(self, incidents):
        return [
            RankedIncident(
                incident=incident,
                score=IncidentScore(
                    incident_id=incident.incident_id,
                    total_score=1,
                    contributions=[],
                    algorithm_version="fake-v1",
                    policy_version="fake-policy-v1",
                ),
            )
            for incident in incidents
        ]

    def evaluate_crew_feasibility(self, request):
        return [CrewFeasibility(crew_id=crew.crew_id, feasible=True) for crew in request.crews]

    def recommend(self, request: OptimizationRequest) -> Recommendation:
        return Recommendation(
            recommendation_id=f"FAKE-{request.incident.incident_id}",
            incident_id=request.incident.incident_id,
            recommended_action="Fake engine review",
            recommended_crew=None,
            confidence="low",
            expected_impact="Fake adapter contract result.",
            factors=["Fake engine"],
            constraints=[],
            alternatives=[],
        )


def _assert_engine_contract(engine) -> None:
    services = build_services()
    incidents = services.incidents.list_ranked()
    request = OptimizationRequest(
        scenario_id=data_loader.get_active_scenario(),
        incident=incidents[0],
        crews=services.crews.list(),
        assignments=services.assignments.list_active(),
    )

    assert engine.policy
    assert engine.rank_incidents(incidents)
    assert engine.evaluate_incidents(incidents)
    assert engine.evaluate_crew_feasibility(request)
    assert isinstance(engine.recommend(request), Recommendation)


def test_deterministic_and_fake_adapters_satisfy_the_same_contract() -> None:
    _assert_engine_contract(DeterministicOptimizationEngine())
    _assert_engine_contract(FakeOptimizationEngine())


def test_services_can_use_a_fake_engine_without_route_or_service_changes() -> None:
    data_loader.set_active_scenario("base")
    services = build_services(optimization_engine=FakeOptimizationEngine())

    assert services.incidents.list_ranked()[0].incident_id != "INC-1001"
    recommendation = services.recommendations.recommend()
    assert recommendation.recommended_action == "Fake engine review"
    assert recommendation.recommendation_id.startswith("FAKE-")
