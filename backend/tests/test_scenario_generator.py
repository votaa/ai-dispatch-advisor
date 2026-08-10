from __future__ import annotations

import csv
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from app.scenario_generator import (
    MUA_CONTRACTOR_LOCATIONS,
    SERVICE_LOCATIONS,
    VEGETATION_LOCATIONS,
    REGIONS,
    generate_scenario,
    load_municipalities,
    write_scenario,
)
from app.scenario_service import ScenarioService


def test_default_generator_obeys_approved_dispatch_rules() -> None:
    scenario = generate_scenario(scenario_id="preview-20260810", start_date=date(2026, 8, 10))

    assert len(scenario.crews) == 500
    assert len(scenario.incidents) == 2000
    assert len({row["incident_id"] for row in scenario.incidents}) == 2000
    assert scenario.incidents[0]["incident_id"] == "ESD-20260810-0001"
    assert scenario.incidents[-1]["incident_id"] == "ESD-20260810-2000"
    assert len({row["incident_id"] for row in scenario.assignments}) == 100
    assert len(scenario.assignments) == 105
    assert len({row["crew_id"] for row in scenario.assignments}) == 105
    assert all(row["assignment_id"].startswith("ASG-20260810-") for row in scenario.assignments)
    assert len(scenario.weather) == 4
    incident_counts = Counter(row["region"] for row in scenario.incidents)
    expected_facility_counts = {
        region: max(1, round(count * 0.04))
        for region, count in incident_counts.items()
    }
    assert len(scenario.critical_facilities) == sum(expected_facility_counts.values()) == 80
    assert Counter(row["region"] for row in scenario.critical_facilities) == expected_facility_counts
    assert len(scenario.historical_repairs) == 40
    assert {row["region"] for row in scenario.weather} == set(REGIONS)
    assert {row["region"] for row in scenario.critical_facilities} == set(REGIONS)
    assert {row["region"] for row in scenario.historical_repairs} == set(REGIONS)

    distribution = Counter(scenario.crew_types.values())
    assert distribution == {
        "lkp": 60,
        "ww": 40,
        "troubleshooter": 110,
        "low_voltage": 70,
        "line": 70,
        "mua": 60,
        "cntr": 55,
        "tree": 25,
        "cg": 10,
    }
    for crew in scenario.crews:
        location = crew["current_location"]
        assert not location.endswith(" Staging Area") or location in VEGETATION_LOCATIONS.values()

    incidents = {row["incident_id"]: row for row in scenario.incidents}
    crews = {row["crew_id"]: row for row in scenario.crews}
    topology_assets = {row["asset_id"]: row for row in scenario.topology}
    topology_feeders = {(row["region"], row["feeder"]) for row in scenario.topology}
    assert {(row["region"], row["feeder"]) for row in scenario.incidents}.issubset(topology_feeders)
    assert {(row["region"], row["feeder"]) for row in scenario.critical_facilities}.issubset(topology_feeders)
    assert all(not row["parent_asset_id"] or row["parent_asset_id"] in topology_assets for row in scenario.topology)
    dual_counts = Counter(row["incident_id"] for row in scenario.assignments)
    assert sum(count == 2 for count in dual_counts.values()) == 5

    expected_regions = {
        "1": "Queens-Nassau",
        "2": "Central-Nassau",
        "3": "Western Suffolk",
        "4": "Eastern Suffolk",
    }
    for assignment in scenario.assignments:
        crew = crews[assignment["crew_id"]]
        incident = incidents[assignment["incident_id"]]
        suffix = crew["crew_id"].rsplit("-", 1)[-1]
        if suffix[0] in expected_regions:
            assert crew["home_region"] == expected_regions[suffix[0]]
            assert incident["region"] == expected_regions[suffix[0]]
        crew_type = scenario.crew_types[crew["crew_id"]]
        if crew_type == "low_voltage":
            assert incident["customers_out"] == 1
            assert incident["required_skill"] == "low_voltage"
        if crew_type == "line":
            assert incident["customers_out"] >= 40
            assert incident["severity"] in {"high", "critical"}
            assert incident["required_skill"] == "line"


def test_start_day_locations_use_approved_facilities() -> None:
    scenario = generate_scenario(
        scenario_id="start-day-locations",
        start_date=date(2026, 8, 10),
        incident_count=40,
        crew_count=80,
        assignment_rate=0,
        dual_tree_incidents=0,
        start_day_location_rate=1,
    )

    for crew in scenario.crews:
        crew_type = scenario.crew_types[crew["crew_id"]]
        if crew_type == "tree":
            assert crew["current_location"] == VEGETATION_LOCATIONS[crew["home_region"]]
        elif crew_type in {"mua", "cntr"}:
            assert crew["current_location"] in MUA_CONTRACTOR_LOCATIONS[crew["home_region"]]
        else:
            assert crew["current_location"] == SERVICE_LOCATIONS[crew["home_region"]]


def test_prior_job_locations_are_plain_municipality_names() -> None:
    scenario = generate_scenario(
        scenario_id="prior-job-locations",
        start_date=date(2026, 8, 10),
        incident_count=40,
        crew_count=80,
        assignment_rate=0,
        dual_tree_incidents=0,
        start_day_location_rate=0,
    )
    municipalities = load_municipalities()
    names_by_region = {
        region: {row["municipality"] for row in rows}
        for region, rows in municipalities.items()
    }
    assert all(
        crew["current_location"] in names_by_region[crew["home_region"]]
        for crew in scenario.crews
    )


def test_written_preview_is_a_valid_application_scenario(tmp_path: Path) -> None:
    scenario = generate_scenario(
        scenario_id="generated-test",
        start_date=date(2026, 8, 10),
        incident_count=80,
        crew_count=80,
        assignment_rate=0.1,
        dual_tree_incidents=1,
        critical_facilities_per_region=3,
        seed=7,
    )
    target = write_scenario(scenario, tmp_path)

    descriptor = ScenarioService(tmp_path, "generated-test").active_scenario()
    assert descriptor.validation_status == "valid"
    with (target / "PendingIncidents.csv").open(newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 80
    with (target / "Weather.csv").open(newline="", encoding="utf-8") as handle:
        assert {row["region"] for row in csv.DictReader(handle)} == set(REGIONS)
    with (target / "CriticalFacilities.csv").open(newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 12
    with (target / "HistoricalRepairs.csv").open(newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 40
    with (target / "Topology.csv").open(newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == len(scenario.topology)


def test_generator_refuses_to_replace_base_or_existing_output(tmp_path: Path) -> None:
    base = generate_scenario(
        scenario_id="base",
        start_date=date(2026, 8, 10),
        incident_count=20,
        crew_count=20,
        assignment_rate=0,
        dual_tree_incidents=0,
    )
    with pytest.raises(ValueError, match="protected base"):
        write_scenario(base, tmp_path)

    scenario = generate_scenario(
        scenario_id="existing",
        start_date=date(2026, 8, 10),
        incident_count=20,
        crew_count=20,
        assignment_rate=0,
        dual_tree_incidents=0,
    )
    write_scenario(scenario, tmp_path)
    with pytest.raises(FileExistsError):
        write_scenario(scenario, tmp_path)
