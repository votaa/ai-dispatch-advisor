import pytest

from app.domain.models import Assignment, Crew, Incident, Recommendation
from app.services import (
    DecisionConflictError,
    DecisionReasonRequiredError,
    EntityNotFoundError,
    build_services,
)


def test_services_return_typed_domain_models() -> None:
    services = build_services()

    assert all(isinstance(row, Assignment) for row in services.assignments.list_active())
    assert all(isinstance(row, Incident) for row in services.incidents.list_ranked())
    assert all(isinstance(row, Crew) for row in services.crews.list())
    recommendation = services.recommendations.recommend()
    assert isinstance(recommendation, Recommendation)
    assert recommendation.explanation is not None
    assert recommendation.explanation.algorithm_version == "deterministic-scoring-v2"
    assert recommendation.explanation.policy_version == "incident-priority-v1"
    assert recommendation.explanation.confidence_rationale.score == recommendation.recommended_crew.suitability_score
    assert recommendation.explanation.constraints
    assert services.recommendations.dashboard().scenario == "base"
    assert services.context.weather()
    assert services.context.critical_facilities()
    assert services.context.topology()


def test_decision_service_updates_incident_crew_and_audit_state() -> None:
    services = build_services()
    recommendation = services.recommendations.recommend("INC-1001")
    crew_id = recommendation.recommended_crew.crew_id

    decision = services.decisions.record(
        incident_id="INC-1001",
        action="accepted",
        recommendation=recommendation,
    )

    incident = services.incidents.get("INC-1001")
    crew = next(row for row in services.crews.list() if row.crew_id == crew_id)
    assert decision.scenario_id == "base"
    assert incident.status == "assigned"
    assert incident.current_decision is not None
    assert incident.current_decision.event_id == decision.event_id
    assert any(row.crew_id == crew_id for row in incident.assigned_crews)
    assert crew.status == "assigned"
    assert any(row.incident_id == "INC-1001" for row in crew.assigned_incidents)
    assert services.decisions.recent()[0].event_id == decision.event_id


def test_decision_service_enforces_required_reason() -> None:
    services = build_services()
    recommendation = services.recommendations.recommend("INC-1001")

    with pytest.raises(DecisionReasonRequiredError, match="Deferred reason is required"):
        services.decisions.record(
            incident_id="INC-1001",
            action="deferred",
            recommendation=recommendation,
            reason="   ",
        )


def test_decision_service_rejects_mismatched_recommendation_incident() -> None:
    services = build_services()
    recommendation = services.recommendations.recommend("INC-1001")

    with pytest.raises(
        DecisionConflictError,
        match="Recommendation incident does not match the decision incident",
    ):
        services.decisions.record(
            incident_id="INC-1002",
            action="accepted",
            recommendation=recommendation,
        )


def test_incident_and_recommendation_services_report_missing_incidents() -> None:
    services = build_services()

    with pytest.raises(EntityNotFoundError, match="Incident not found"):
        services.incidents.get("INC-MISSING")
    with pytest.raises(EntityNotFoundError, match="Incident not found"):
        services.recommendations.recommend("INC-MISSING")


def test_scenario_and_copilot_services_use_current_runtime_state() -> None:
    services = build_services()

    activated = services.scenarios.activate("storm")
    response = services.copilot.respond("How many crews are available?")

    assert activated.scenario_id == "storm"
    assert services.scenarios.active().scenario_id == "storm"
    assert services.recommendations.dashboard().scenario == "storm"
    assert response.intent == "crew_status"
    assert response.source == "synthetic-demo-data"
