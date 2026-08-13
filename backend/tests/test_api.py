from fastapi.testclient import TestClient

from app.decision_store import clear_decisions
from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_exposes_explicit_core_response_contracts() -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert paths["/api/incidents"]["get"]["responses"]["200"]["content"]["application/json"]["schema"][
        "items"
    ]["$ref"].endswith("/Incident")
    assert paths["/api/crews"]["get"]["responses"]["200"]["content"]["application/json"]["schema"][
        "items"
    ]["$ref"].endswith("/Crew")
    assert paths["/api/assignments"]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["items"]["$ref"].endswith("/Assignment")
    assert paths["/api/dashboard"]["get"]["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DashboardResponse")
    assert paths["/api/optimize"]["post"]["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/Recommendation-Output")
    assert paths["/api/recommendation-actions"]["post"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/RecommendationDecision")


def test_core_requests_reject_undeclared_fields() -> None:
    response = client.post("/api/optimize", json={"unexpected": "value"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"


def test_core_response_contracts_validate_for_every_discovered_scenario() -> None:
    scenario_ids = [scenario["scenario_id"] for scenario in client.get("/api/scenarios").json()]

    for scenario_id in scenario_ids:
        activation = client.put("/api/scenarios/active", json={"scenario_id": scenario_id})
        assert activation.status_code == 200

        for path in ["/api/dashboard", "/api/incidents", "/api/crews", "/api/assignments"]:
            response = client.get(path)
            assert response.status_code == 200, f"{scenario_id}: {path}: {response.text}"

        recommendation = client.post("/api/optimize", json={})
        assert recommendation.status_code == 200, f"{scenario_id}: /api/optimize: {recommendation.text}"


def test_incidents() -> None:
    response = client.get("/api/incidents")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_optimize() -> None:
    response = client.post("/api/optimize", json={})
    assert response.status_code == 200
    assert "recommended_action" in response.json()


def test_recommendation_action_records_audit_event() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={}).json()

    response = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": recommendation["incident_id"],
            "action": "accepted",
            "recommendation": recommendation,
        },
    )

    assert response.status_code == 200
    event = response.json()
    assert event["incident_id"] == recommendation["incident_id"]
    assert event["recommendation_id"] == recommendation["recommendation_id"]
    assert event["action"] == "accepted"
    assert event["recommendation"]["recommended_action"] == recommendation["recommended_action"]

    history = client.get("/api/audit/events")
    assert history.status_code == 200
    assert history.json()[0]["event_id"] == event["event_id"]


def test_accepting_recommendation_updates_assignment_state() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()
    crew_id = recommendation["recommended_crew"]["crew_id"]

    response = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": recommendation["incident_id"],
            "action": "accepted",
            "recommendation": recommendation,
        },
    )

    assert response.status_code == 200

    assignments = client.get("/api/assignments").json()
    assert any(
        assignment["incident_id"] == "INC-1001" and assignment["crew_id"] == crew_id
        for assignment in assignments
    )

    incident = client.get("/api/incidents/INC-1001").json()
    assert incident["status"] == "assigned"
    assert any(crew["crew_id"] == crew_id for crew in incident["assigned_crews"])

    crews = client.get("/api/crews").json()
    assigned_crew = next(crew for crew in crews if crew["crew_id"] == crew_id)
    assert assigned_crew["status"] == "assigned"
    assert assigned_crew["assigned_incidents"][0]["incident_id"] == "INC-1001"


def test_defer_requires_reason() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={}).json()

    response = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": recommendation["incident_id"],
            "action": "deferred",
            "recommendation": recommendation,
            "reason": "   ",
        },
    )

    assert response.status_code == 400


def test_override_requires_reason() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={}).json()

    response = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": recommendation["incident_id"],
            "action": "overridden",
            "recommendation": recommendation,
            "note": "   ",
        },
    )

    assert response.status_code == 400
