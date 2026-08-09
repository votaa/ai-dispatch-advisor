import json
import shutil
from pathlib import Path

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
    assert active_response.json()["scenario_id"] == data_loader.DEFAULT_SCENARIO
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


def test_service_reports_unknown_assignment_reference(tmp_path: Path) -> None:
    scenario_directory = tmp_path / "base"
    shutil.copytree(data_loader.DATA_ROOT / "base", scenario_directory)
    assignment_path = scenario_directory / "Assignments.csv"
    assignment_path.write_text(
        assignment_path.read_text(encoding="utf-8").replace("INC-1002", "INC-UNKNOWN", 1),
        encoding="utf-8",
    )

    service = ScenarioService(tmp_path, "base")

    try:
        service.active_scenario()
    except ScenarioServiceError as exc:
        assert exc.code == "scenario_validation_failed"
        assert {
            "location": "Assignments.csv:2.incident_id",
            "message": "Unknown incident_id 'INC-UNKNOWN'",
        } in exc.details
    else:
        raise AssertionError("Expected unknown assignment reference to fail")


def test_active_endpoint_returns_structured_not_found_error(monkeypatch) -> None:
    monkeypatch.setattr(data_loader, "DEFAULT_SCENARIO", "does-not-exist")

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
    monkeypatch.setattr(data_loader, "DEFAULT_SCENARIO", "base")

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
