from fastapi.testclient import TestClient

from app.recommendation_actions import clear_actions
from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_incidents() -> None:
    response = client.get("/api/incidents")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_optimize() -> None:
    response = client.post("/api/optimize", json={})
    assert response.status_code == 200
    assert "recommended_action" in response.json()


def test_recommendation_action_records_audit_event() -> None:
    clear_actions()
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
    assert event["action"] == "accepted"
    assert event["recommendation"]["recommended_action"] == recommendation["recommended_action"]

    history = client.get("/api/audit/events")
    assert history.status_code == 200
    assert history.json()[0]["event_id"] == event["event_id"]


def test_override_requires_reason() -> None:
    clear_actions()
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
