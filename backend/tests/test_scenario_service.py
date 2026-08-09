from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import data_loader
from app.main import app
from app.scenario_service import ScenarioService, ScenarioServiceError


client = TestClient(app)


def test_scenario_endpoints_list_and_identify_active_scenario() -> None:
    response = client.get("/api/scenarios")

    assert response.status_code == 200
    scenarios = response.json()
    assert {scenario["scenario_id"] for scenario in scenarios} == {
        "base",
        "storm",
        "crew-shortage",
        "critical-facility",
    }
    assert all(scenario["validation_status"] == "valid" for scenario in scenarios)
    assert sum(scenario["is_active"] for scenario in scenarios) == 1

    active_response = client.get("/api/scenarios/active")
    assert active_response.status_code == 200
    assert active_response.json()["scenario_id"] == data_loader.get_active_scenario()
    assert active_response.json()["is_active"] is True


def test_service_reports_missing_required_csv(tmp_path: Path) -> None:
    source = data_loader.DATA_ROOT / "base"
    scenario_directory = tmp_path / "base"
    shutil.copytree(source, scenario_directory)
    (scenario_directory / "Weather.csv").unlink()

    service = ScenarioService(tmp_path, "base")

    try:
        service.active_scenario()
    except ScenarioServiceError as exc:
        assert exc.status_code == 422
        assert exc.code == "scenario_validation_failed"
        assert exc.scenario_id == "base"
        assert exc.details == [{"location": "Weather.csv", "message": "Required CSV file is missing"}]
    else:
        raise AssertionError("Expected missing CSV validation to fail")


def test_service_reports_invalid_manifest(tmp_path: Path) -> None:
    scenario_directory = tmp_path / "broken"
    scenario_directory.mkdir()
    (scenario_directory / "scenario.json").write_text(
        json.dumps({"scenario_id": "broken", "name": "Broken"}),
        encoding="utf-8",
    )

    service = ScenarioService(tmp_path, "broken")

    try:
        service.active_scenario()
    except ScenarioServiceError as exc:
        assert exc.status_code == 422
        assert exc.code == "scenario_manifest_invalid"
        assert exc.scenario_id == "broken"
        assert any(detail["location"] == "schema_version" for detail in exc.details)
    else:
        raise AssertionError("Expected invalid manifest validation to fail")


def test_service_reports_invalid_csv_headers(tmp_path: Path) -> None:
    scenario_directory = tmp_path / "base"
    shutil.copytree(data_loader.DATA_ROOT / "base", scenario_directory)
    weather_path = scenario_directory / "Weather.csv"
    weather_path.write_text(
        weather_path.read_text(encoding="utf-8").replace("weather_id,region", "weather_id,service_area", 1),
        encoding="utf-8",
    )

    service = ScenarioService(tmp_path, "base")

    try:
        service.active_scenario()
    except ScenarioServiceError as exc:
        assert exc.code == "scenario_validation_failed"
        assert any(
            detail["location"] == "Weather.csv" and "headers" in detail["message"]
            for detail in exc.details
        )
    else:
        raise AssertionError("Expected invalid CSV headers to fail")


@pytest.mark.parametrize(
    ("filename", "id_field"),
    [
        ("PendingIncidents.csv", "incident_id"),
        ("Crews.csv", "crew_id"),
    ],
)
def test_service_reports_duplicate_domain_identifiers(
    tmp_path: Path,
    filename: str,
    id_field: str,
) -> None:
    scenario_directory = tmp_path / "base"
    shutil.copytree(data_loader.DATA_ROOT / "base", scenario_directory)
    csv_path = scenario_directory / filename
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    csv_path.write_text("\n".join([*lines, lines[1]]) + "\n", encoding="utf-8")

    service = ScenarioService(tmp_path, "base")

    with pytest.raises(ScenarioServiceError) as error:
        service.active_scenario()

    assert error.value.code == "scenario_validation_failed"
    assert any(
        detail["location"] == filename and detail["message"] == f"Duplicate {id_field} values found"
        for detail in error.value.details
    )


@pytest.mark.parametrize(
    ("field_name", "existing_value", "unknown_value"),
    [
        ("incident_id", "INC-1002", "INC-UNKNOWN"),
        ("crew_id", "CR-02", "CR-UNKNOWN"),
    ],
)
def test_service_reports_unknown_assignment_reference(
    tmp_path: Path,
    field_name: str,
    existing_value: str,
    unknown_value: str,
) -> None:
    scenario_directory = tmp_path / "base"
    shutil.copytree(data_loader.DATA_ROOT / "base", scenario_directory)
    assignment_path = scenario_directory / "Assignments.csv"
    assignment_path.write_text(
        assignment_path.read_text(encoding="utf-8").replace(existing_value, unknown_value, 1),
        encoding="utf-8",
    )

    service = ScenarioService(tmp_path, "base")

    try:
        service.active_scenario()
    except ScenarioServiceError as exc:
        assert exc.code == "scenario_validation_failed"
        assert {
            "location": f"Assignments.csv:2.{field_name}",
            "message": f"Unknown {field_name} '{unknown_value}'",
        } in exc.details
    else:
        raise AssertionError("Expected unknown assignment reference to fail")


@pytest.mark.parametrize(
    ("old_row", "new_row", "expected_message"),
    [
        (
            "CR-02,Central Veg Beta,Central,assigned",
            "CR-02,Central Veg Beta,Central,available",
            "Crew 'CR-02' has an active assignment but status is 'available'; expected 'assigned'",
        ),
        (
            "CR-03,South General Gamma,South,available",
            "CR-03,South General Gamma,South,assigned",
            "Crew 'CR-03' is assigned but has no active assignment",
        ),
    ],
)
def test_service_reports_crew_assignment_status_mismatch(
    tmp_path: Path,
    old_row: str,
    new_row: str,
    expected_message: str,
) -> None:
    scenario_directory = tmp_path / "base"
    shutil.copytree(data_loader.DATA_ROOT / "base", scenario_directory)
    crew_path = scenario_directory / "Crews.csv"
    crew_path.write_text(
        crew_path.read_text(encoding="utf-8").replace(old_row, new_row, 1),
        encoding="utf-8",
    )

    service = ScenarioService(tmp_path, "base")

    with pytest.raises(ScenarioServiceError) as error:
        service.active_scenario()

    assert error.value.code == "scenario_validation_failed"
    assert any(detail["message"] == expected_message for detail in error.value.details)


def test_active_endpoint_returns_structured_not_found_error(monkeypatch) -> None:
    monkeypatch.setattr(data_loader, "_active_scenario_id", "does-not-exist")

    response = client.get("/api/scenarios/active")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "scenario_not_found",
            "message": "Scenario 'does-not-exist' was not found.",
            "scenario_id": "does-not-exist",
            "details": [
                {
                    "location": str(data_loader.DATA_ROOT / "does-not-exist"),
                    "message": "Directory not found",
                }
            ],
        }
    }


def test_active_endpoint_returns_structured_validation_error(tmp_path: Path, monkeypatch) -> None:
    scenario_directory = tmp_path / "base"
    shutil.copytree(data_loader.DATA_ROOT / "base", scenario_directory)
    (scenario_directory / "Crews.csv").unlink()
    monkeypatch.setattr(data_loader, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(data_loader, "_active_scenario_id", "base")

    response = client.get("/api/scenarios/active")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "scenario_validation_failed",
            "message": "Scenario 'base' failed validation.",
            "scenario_id": "base",
            "details": [{"location": "Crews.csv", "message": "Required CSV file is missing"}],
        }
    }


def test_runtime_activation_switches_loaded_scenario_and_dashboard_metadata() -> None:
    response = client.put("/api/scenarios/active", json={"scenario_id": "storm"})

    assert response.status_code == 200
    assert response.json()["scenario_id"] == "storm"
    assert response.json()["is_active"] is True
    assert client.get("/api/scenarios/active").json()["scenario_id"] == "storm"

    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 10
    assert all(incident["incident_id"].startswith("STM-") for incident in incidents)

    dashboard = client.get("/api/dashboard").json()
    assert dashboard["scenario"] == "storm"
    assert dashboard["active_incidents"] == 10


def test_runtime_activation_loads_each_scenario_without_cached_data_leakage() -> None:
    expected_scenarios = [
        ("base", "INC-", 8),
        ("storm", "STM-", 10),
        ("crew-shortage", "CRS-", 7),
        ("critical-facility", "CFI-", 6),
        ("base", "INC-", 8),
    ]

    for scenario_id, incident_prefix, incident_count in expected_scenarios:
        response = client.put("/api/scenarios/active", json={"scenario_id": scenario_id})
        assert response.status_code == 200

        incidents = client.get("/api/incidents").json()
        dashboard = client.get("/api/dashboard").json()
        assert len(incidents) == incident_count
        assert all(incident["incident_id"].startswith(incident_prefix) for incident in incidents)
        assert dashboard["scenario"] == scenario_id
        assert dashboard["active_incidents"] == incident_count


@pytest.mark.parametrize(
    ("scenario_id", "incident_id", "crew_id", "recommended_action"),
    [
        ("base", "INC-1001", "CR-01", "Assign crew"),
        ("storm", "STM-2001", "SC-06", "Assign crew"),
        ("crew-shortage", "CRS-3001", None, "Defer and escalate"),
        ("critical-facility", "CFI-4001", "FC-01", "Assign crew"),
    ],
)
def test_scenario_has_expected_top_recommendation(
    scenario_id: str,
    incident_id: str,
    crew_id: str | None,
    recommended_action: str,
) -> None:
    assert client.put("/api/scenarios/active", json={"scenario_id": scenario_id}).status_code == 200

    recommendation = client.post("/api/optimize", json={}).json()

    assert recommendation["incident_id"] == incident_id
    assert recommendation["recommended_action"] == recommended_action
    assert (recommendation["recommended_crew"] or {}).get("crew_id") == crew_id


def test_invalid_runtime_activation_preserves_current_scenario() -> None:
    response = client.put("/api/scenarios/active", json={"scenario_id": "does-not-exist"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "scenario_not_found"
    assert client.get("/api/scenarios/active").json()["scenario_id"] == "base"
    assert all(
        incident["incident_id"].startswith("INC-")
        for incident in client.get("/api/incidents").json()
    )


def test_decisions_and_demo_assignments_are_isolated_between_scenarios() -> None:
    base_recommendation = client.post("/api/optimize", json={"incident_id": "INC-1001"}).json()
    base_event = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": "INC-1001",
            "action": "accepted",
            "recommendation": base_recommendation,
        },
    ).json()
    assert base_event["scenario_id"] == "base"
    assert len(client.get("/api/audit/events").json()) == 1

    client.put("/api/scenarios/active", json={"scenario_id": "storm"})
    assert client.get("/api/audit/events").json() == []
    storm_seed_assignments = client.get("/api/assignments").json()
    assert len(storm_seed_assignments) == 4
    assert all(assignment["scenario_id"] == "storm" for assignment in storm_seed_assignments)

    storm_recommendation = client.post("/api/optimize", json={"incident_id": "STM-2003"}).json()
    storm_event = client.post(
        "/api/recommendation-actions",
        json={
            "incident_id": "STM-2003",
            "action": "accepted",
            "recommendation": storm_recommendation,
        },
    ).json()
    assert storm_event["scenario_id"] == "storm"
    assert len(client.get("/api/audit/events").json()) == 1
    assert len(client.get("/api/assignments").json()) == 5

    client.put("/api/scenarios/active", json={"scenario_id": "base"})
    base_history = client.get("/api/audit/events").json()
    assert [event["event_id"] for event in base_history] == [base_event["event_id"]]
    assert len(client.get("/api/assignments").json()) == 3
