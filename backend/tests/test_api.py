from datetime import datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app import decision_store
from app.database_migrations import applied_migrations
from app.decision_store import clear_decisions
from app.main import app, services


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    UUID(response.headers["X-Correlation-ID"])


def test_valid_client_correlation_id_is_echoed() -> None:
    response = client.get("/health", headers={"X-Correlation-ID": "phase-4.4-smoke"})

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "phase-4.4-smoke"


def test_invalid_client_correlation_id_is_replaced() -> None:
    response = client.get("/health", headers={"X-Correlation-ID": "invalid correlation id"})

    assert response.status_code == 200
    generated_id = response.headers["X-Correlation-ID"]
    UUID(generated_id)
    assert generated_id != "invalid correlation id"


def test_application_startup_applies_database_migrations() -> None:
    with TestClient(app) as startup_client:
        assert startup_client.get("/health").status_code == 200

    with decision_store._connect() as connection:
        assert [row["version"] for row in applied_migrations(connection)] == [1, 2, 3]


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
    assert paths["/api/chat"]["post"]["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/ChatResponse")
    assert paths["/api/recommendation-actions"]["post"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/RecommendationDecision")
    assert "selected_crew_id" in schema["components"]["schemas"]["RecommendationActionRequest"]["properties"]
    assert paths["/api/optimize"]["post"]["responses"]["404"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/ErrorResponse")
    assert "X-Correlation-ID" in paths["/api/optimize"]["post"]["responses"]["404"]["headers"]
    assert paths["/api/optimize"]["post"]["responses"]["422"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/ErrorResponse")
    assert {"ApiError", "ErrorDetail", "ErrorResponse"}.issubset(schema["components"]["schemas"])
    assert {
        "RecommendationExplanation",
        "ConfidenceRationale",
        "ExplanationFactor",
        "ExplanationConstraint",
        "ExcludedCandidate",
    }.issubset(schema["components"]["schemas"])
    assert {
        "answer",
        "intent",
        "source",
        "safety_note",
        "execution_mode",
        "scenario_id",
        "generated_at",
        "request_time",
        "evidence",
    }.issubset(schema["components"]["schemas"]["ChatResponse"]["properties"])


def test_core_requests_reject_undeclared_fields() -> None:
    response = client.post(
        "/api/optimize",
        json={"unexpected": "value"},
        headers={"X-Correlation-ID": "validation-test"},
    )

    assert response.status_code == 422
    assert response.headers["X-Correlation-ID"] == "validation-test"
    assert response.json() == {
        "error": {
            "code": "request_validation_failed",
            "message": "Request validation failed.",
            "correlation_id": "validation-test",
            "details": [
                {
                    "location": "body.unexpected",
                    "message": "Extra inputs are not permitted",
                    "type": "extra_forbidden",
                }
            ],
        }
    }


def test_missing_incident_uses_domain_error_contract() -> None:
    response = client.get(
        "/api/incidents/INC-DOES-NOT-EXIST",
        headers={"X-Correlation-ID": "missing-incident-test"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "entity_not_found",
            "message": "Incident not found",
            "correlation_id": "missing-incident-test",
            "details": [],
            "entity": "Incident",
            "entity_id": "INC-DOES-NOT-EXIST",
        }
    }


def test_framework_not_found_uses_shared_error_contract() -> None:
    response = client.get("/api/not-a-route")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "resource_not_found"
    assert error["message"] == "Not Found"
    assert error["correlation_id"] == response.headers["X-Correlation-ID"]


def test_framework_error_preserves_protocol_headers() -> None:
    response = client.post("/health")

    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_unexpected_errors_return_safe_correlated_response(monkeypatch) -> None:
    def fail_dashboard():
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setattr(services.recommendations, "dashboard", fail_dashboard)
    with TestClient(app, raise_server_exceptions=False) as failure_client:
        response = failure_client.get(
            "/api/dashboard",
            headers={"X-Correlation-ID": "unexpected-error-test"},
        )

    assert response.status_code == 500
    assert response.headers["X-Correlation-ID"] == "unexpected-error-test"
    assert response.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "An unexpected server error occurred.",
            "correlation_id": "unexpected-error-test",
            "details": [],
        }
    }
    assert "sensitive internal detail" not in response.text


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


def test_chat_preserves_existing_fields_and_adds_local_evidence_metadata() -> None:
    response = client.post("/api/chat", json={"message": "How many crews are available?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"]
    assert payload["intent"] == "crew_status"
    assert payload["source"] == "synthetic-demo-data"
    assert payload["safety_note"]
    assert payload["execution_mode"] == "local_query"
    assert payload["scenario_id"] == "base"
    assert payload["generated_at"]
    request_time = payload["request_time"]
    parsed_request_time = datetime.fromisoformat(request_time["received_at"].replace("Z", "+00:00"))
    assert parsed_request_time.utcoffset() is not None
    assert request_time == {
        "received_at": request_time["received_at"],
        "timezone": "UTC",
        "source": "backend_server_clock",
        "clock_skew": "not_measured",
    }
    assert payload["evidence"][0]["source_type"] == "dashboard"


def test_chat_customer_outage_aggregate_matches_complete_dashboard_totals() -> None:
    dashboard = client.get("/api/dashboard").json()

    response = client.post(
        "/api/chat",
        json={
            "message": "How many customers are out across all active incidents?",
            "incident_id": "INC-1001",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "all_incident_customer_aggregate"
    assert payload["execution_mode"] == "local_query"
    assert payload["provider"] is None
    assert (
        f"{dashboard['active_incidents']} active incidents report "
        f"**{dashboard['customers_out']:,} customers out**"
    ) in payload["answer"]
    assert payload["evidence"][0]["source_type"] == "dashboard"


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


def test_modified_alternative_creates_assignment_and_preserves_recommendation_evidence() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()
    assert recommendation["alternatives"]
    recommended_crew_id = recommendation["recommended_crew"]["crew_id"]
    selected_crew_id = recommendation["alternatives"][0]["crew_id"]

    response = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": recommendation["incident_id"],
            "action": "modified",
            "selected_crew_id": selected_crew_id,
            "reason": "Closer to the switching location reported by operations",
            "recommendation": recommendation,
        },
    )

    assert response.status_code == 200
    event = response.json()
    assert event["action"] == "modified"
    assert event["crew_id"] == selected_crew_id
    assert event["recommendation"]["recommended_crew"]["crew_id"] == recommended_crew_id
    assert event["recommendation"]["alternatives"][0]["crew_id"] == selected_crew_id

    assignments = client.get("/api/assignments").json()
    assert any(
        assignment["incident_id"] == "INC-1001" and assignment["crew_id"] == selected_crew_id
        for assignment in assignments
    )
    incident = client.get("/api/incidents/INC-1001").json()
    assert any(crew["crew_id"] == selected_crew_id for crew in incident["assigned_crews"])


def test_modified_alternative_requires_reason() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()
    selected_crew_id = recommendation["alternatives"][0]["crew_id"]

    response = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": recommendation["incident_id"],
            "action": "modified",
            "selected_crew_id": selected_crew_id,
            "reason": "   ",
            "recommendation": recommendation,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "decision_reason_required"


def test_note_only_modification_does_not_create_an_assignment() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()

    response = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": recommendation["incident_id"],
            "action": "modified",
            "reason": "Review the work package before dispatch",
            "recommendation": recommendation,
        },
    )

    assert response.status_code == 200
    assert not any(
        assignment["incident_id"] == "INC-1001"
        for assignment in client.get("/api/assignments").json()
    )


def test_accept_rejects_a_ranked_alternative_selection() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()
    selected_crew_id = recommendation["alternatives"][0]["crew_id"]

    response = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": recommendation["incident_id"],
            "action": "accepted",
            "selected_crew_id": selected_crew_id,
            "recommendation": recommendation,
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "decision_crew_selection_invalid"
    assert "use Modify" in response.json()["error"]["message"]


def test_decision_rejects_unranked_or_stale_alternative_selection() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()
    selected_crew_id = recommendation["alternatives"][0]["crew_id"]

    unranked = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": recommendation["incident_id"],
            "action": "modified",
            "selected_crew_id": "CR-NOT-RANKED",
            "reason": "Dispatcher requested a different crew",
            "recommendation": recommendation,
        },
    )
    assert unranked.status_code == 409
    assert unranked.json()["error"]["code"] == "decision_crew_selection_invalid"

    first_assignment = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": recommendation["incident_id"],
            "action": "modified",
            "selected_crew_id": selected_crew_id,
            "reason": "Operational preference",
            "recommendation": recommendation,
        },
    )
    assert first_assignment.status_code == 200

    stale = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": recommendation["incident_id"],
            "action": "modified",
            "selected_crew_id": selected_crew_id,
            "reason": "Retry stale choice",
            "recommendation": recommendation,
        },
    )
    assert stale.status_code == 409
    assert "no longer available" in stale.json()["error"]["message"]


def test_decision_rejects_recommendation_for_a_different_incident() -> None:
    recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()

    response = client.post(
        "/api/recommendation-actions",
        headers={"X-Correlation-ID": "decision-conflict-test"},
        json={
            "incident_id": "INC-1002",
            "action": "accepted",
            "recommendation": recommendation,
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "decision_incident_mismatch",
            "message": "Recommendation incident does not match the decision incident",
            "correlation_id": "decision-conflict-test",
            "details": [
                {
                    "location": "body.recommendation.incident_id",
                    "message": "The recommendation must belong to the decision incident.",
                    "type": "value_error.decision_conflict",
                    "expected": "INC-1002",
                    "actual": "INC-1001",
                }
            ],
            "entity": "Incident",
            "entity_id": "INC-1002",
        }
    }


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
    assert response.json()["error"]["code"] == "decision_reason_required"
    assert response.json()["error"]["details"][0]["action"] == "deferred"


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
    assert response.json()["error"]["code"] == "decision_reason_required"
    assert response.json()["error"]["details"][0]["action"] == "overridden"
