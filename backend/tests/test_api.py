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
        assert [row["version"] for row in applied_migrations(connection)] == [1, 2, 3, 4, 5, 6]


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
        "response_scope",
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
    assert payload["response_scope"] == "Complete crew calculation: 8 crews evaluated"


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


def test_chat_exposes_deterministic_pseg_reference_query() -> None:
    activation = client.put(
        "/api/scenarios/active",
        json={"scenario_id": "long-island-copilot-demo"},
    )
    assert activation.status_code == 200

    response = client.post(
        "/api/chat",
        json={"message": "How many customers are served in Arverne?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "reference_customers_served"
    assert payload["execution_mode"] == "local_query"
    assert payload["source"] == "approved-static-reference"
    assert "**4,607 customers served**" in payload["answer"]
    assert payload["evidence"][0]["source_type"] == "pseg_reference"
    assert payload["provider"] is None
    assert payload["model"] is None


def test_chat_critical_facility_levels_preserve_the_public_response_contract() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "Break down critical facilities by level."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "critical_facility_levels"
    assert payload["execution_mode"] == "local_query"
    assert payload["scenario_id"] == "base"
    assert payload["provider"] is None
    assert "| Level 1 | 3 | +120 |" in payload["answer"]
    assert "| Level 2 | 0 | +80 |" in payload["answer"]
    assert "| Level 3 | 0 | +40 |" in payload["answer"]
    assert "| Unknown/withheld | 0 | Withheld |" in payload["answer"]
    assert {item["source_type"] for item in payload["evidence"]} == {
        "incident",
        "critical_facility",
    }


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


def test_unassigning_active_assignment_updates_incident_and_crew_state() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()
    client.post(
        "/api/recommendation-actions",
        json={"incident_id": "INC-1001", "action": "accepted", "recommendation": recommendation},
    )
    assignment = next(item for item in client.get("/api/assignments").json() if item["incident_id"] == "INC-1001")

    response = client.post(
        "/api/assignment-actions",
        json={
            "assignment_id": assignment["assignment_id"],
            "action": "unassigned",
            "reason_category": "field_condition_changed",
        },
    )

    assert response.status_code == 200
    mutation = response.json()
    assert mutation["action"] == "unassigned"
    assert mutation["assignment_id"] == assignment["assignment_id"]
    assert mutation["resulting_incident_status"] == "unassigned"
    history = client.get("/api/assignment-actions/history")
    assert history.status_code == 200
    assert history.json() == [mutation]
    assert not any(item["assignment_id"] == assignment["assignment_id"] for item in client.get("/api/assignments").json())

    incident = client.get("/api/incidents/INC-1001").json()
    assert incident["status"] == "unassigned"
    assert incident["assigned_crews"] == []

    crew = next(item for item in client.get("/api/crews").json() if item["crew_id"] == assignment["crew_id"])
    assert crew["status"] == "available"
    assert crew["assigned_incidents"] == []


def test_unassign_requires_reason_and_rejects_stale_assignment() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()
    client.post(
        "/api/recommendation-actions",
        json={"incident_id": "INC-1001", "action": "accepted", "recommendation": recommendation},
    )
    assignment = next(item for item in client.get("/api/assignments").json())

    missing_reason = client.post(
        "/api/assignment-actions",
        json={"assignment_id": assignment["assignment_id"], "action": "unassigned", "reason_category": "other", "note": " "},
    )
    assert missing_reason.status_code == 400
    assert missing_reason.json()["error"]["code"] == "assignment_reason_required"

    first = client.post(
        "/api/assignment-actions",
        json={"assignment_id": assignment["assignment_id"], "action": "unassigned", "reason_category": "assignment_entered_in_error"},
    )
    assert first.status_code == 200
    stale = client.post(
        "/api/assignment-actions",
        json={"assignment_id": assignment["assignment_id"], "action": "unassigned", "reason_category": "assignment_entered_in_error"},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "assignment_conflict"


def test_reassign_retires_old_assignment_and_activates_available_crew() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()
    client.post(
        "/api/recommendation-actions",
        json={"incident_id": "INC-1001", "action": "accepted", "recommendation": recommendation},
    )
    current = next(item for item in client.get("/api/assignments").json() if item["incident_id"] == "INC-1001")
    replacement = next(
        item for item in client.get("/api/crews").json()
        if item["crew_id"] != current["crew_id"] and item["status"] == "available"
    )

    response = client.post(
        "/api/assignment-actions",
        json={
            "assignment_id": current["assignment_id"],
            "action": "reassigned",
            "selected_crew_id": replacement["crew_id"],
            "reason_category": "crew_unavailable",
        },
    )

    assert response.status_code == 200
    mutation = response.json()
    assert mutation["action"] == "reassigned"
    assert mutation["new_crew_id"] == replacement["crew_id"]
    assert mutation["resulting_incident_status"] == "assigned"
    assert client.get("/api/assignment-actions/history").json() == [mutation]
    active = client.get("/api/assignments").json()
    assert not any(item["assignment_id"] == current["assignment_id"] for item in active)
    assert any(item["assignment_id"] == mutation["new_assignment_id"] and item["crew_id"] == replacement["crew_id"] for item in active)

    incident = client.get("/api/incidents/INC-1001").json()
    assert incident["status"] == "assigned"
    assert [item["crew_id"] for item in incident["assigned_crews"]] == [replacement["crew_id"]]
    old_crew = next(item for item in client.get("/api/crews").json() if item["crew_id"] == current["crew_id"])
    assert old_crew["status"] == "available"
    assert old_crew["assigned_incidents"] == []
    new_crew = next(item for item in client.get("/api/crews").json() if item["crew_id"] == replacement["crew_id"])
    assert new_crew["status"] == "assigned"
    assert new_crew["assigned_incidents"][0]["incident_id"] == "INC-1001"


def test_assignment_history_is_scenario_scoped_and_survives_new_database_connection() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()
    client.post(
        "/api/recommendation-actions",
        json={"incident_id": "INC-1001", "action": "accepted", "recommendation": recommendation},
    )
    assignment = next(item for item in client.get("/api/assignments").json() if item["incident_id"] == "INC-1001")
    mutation = client.post(
        "/api/assignment-actions",
        json={"assignment_id": assignment["assignment_id"], "action": "unassigned",
              "reason_category": "other", "note": "Field report verified"},
    ).json()

    # Each read opens a fresh SQLite connection; repeat after a new app lifespan.
    with TestClient(app) as restarted_client:
        assert restarted_client.get("/api/assignment-actions/history").json() == [mutation]
        assert restarted_client.get("/api/audit/events").json()[0]["action"] == "accepted"
        switched = restarted_client.put(
            "/api/scenarios/active", json={"scenario_id": "long-island-copilot-demo"}
        )
        assert switched.status_code == 200
        assert restarted_client.get("/api/assignment-actions/history").json() == []
        assert restarted_client.put(
            "/api/scenarios/active", json={"scenario_id": "base"}
        ).status_code == 200
        assert restarted_client.get("/api/assignment-actions/history").json() == [mutation]

    assert mutation["note"] == "Field report verified"
    assert mutation["actor"] == "demo-dispatcher"
    assert mutation["scenario_id"] == "base"
    assert mutation["created_at"]


def test_unassign_history_snapshots_assigned_when_another_crew_remains() -> None:
    clear_decisions()
    recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()
    client.post(
        "/api/recommendation-actions",
        json={"incident_id": "INC-1001", "action": "accepted", "recommendation": recommendation},
    )
    original = next(item for item in client.get("/api/assignments").json() if item["incident_id"] == "INC-1001")
    other_crew = next(
        crew for crew in client.get("/api/crews").json()
        if crew["status"] == "available" and crew["crew_id"] != original["crew_id"]
    )
    with decision_store._connect() as connection:
        connection.execute(
            """
            INSERT INTO demo_assignments (
              assignment_id, scenario_id, incident_id, crew_id, status,
              assigned_at, notes, decision_event_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("ASG-SECOND", "base", "INC-1001", other_crew["crew_id"], "active",
             "2026-09-25T12:00:00+00:00", "Second crew", "test-second"),
        )

    mutation = client.post(
        "/api/assignment-actions",
        json={"assignment_id": original["assignment_id"], "action": "unassigned",
              "reason_category": "field_condition_changed"},
    ).json()

    assert mutation["resulting_incident_status"] == "assigned"
    assert client.get("/api/incidents/INC-1001").json()["status"] == "assigned"
    assert client.get("/api/assignment-actions/history?limit=0").json() == [mutation]
    assert client.get("/api/assignment-actions/history?offset=1").json() == []


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
