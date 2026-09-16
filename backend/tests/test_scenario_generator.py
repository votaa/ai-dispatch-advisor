from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from app.domain.models import Incident
from app.geography import GeographyRegistry
from app.optimization.critical_facility import resolve_critical_facility_impact
from app.optimization.deterministic_engine import DeterministicOptimizationEngine
from app.optimization.policy import POC019_OPERATIONAL_RECOMMENDATION_POLICY
from app.scenario_generator import (
    COPILOT_DEMO_CREW_COUNT,
    COPILOT_DEMO_INCIDENT_COUNT,
    FACILITY_CATALOG,
    LSE_CUSTOMER_BOUNDARIES,
    LSE_FACILITY_SUFFIX,
    MUA_CONTRACTOR_LOCATIONS,
    SERVICE_LOCATIONS,
    VEGETATION_LOCATIONS,
    REGIONS,
    generate_copilot_demo_scenario,
    generate_scenario,
    load_municipalities,
    write_scenario,
    validate_critical_facility_linkage,
    validate_geographic_reference_coverage,
    validate_lse_coverage,
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
    facility_keys = {
        (row["region"], row["feeder"], row["municipality"])
        for row in scenario.critical_facilities
    }
    assert all(
        row["critical_facility"] == "false"
        or (row["region"], row["feeder"], row["municipality"])
        in facility_keys
        for row in scenario.incidents
    )
    assert all(
        row["facility_name"].startswith(f"{row['municipality']} ")
        for row in scenario.critical_facilities
    )
    lse_facilities = [
        row
        for row in scenario.critical_facilities
        if row["facility_name"].endswith(LSE_FACILITY_SUFFIX)
    ]
    assert lse_facilities
    assert all(
        row["facility_type"] == "healthcare"
        and row["priority_level"] == "medium"
        for row in lse_facilities
    )
    lse_keys = {
        (row["region"], row["feeder"], row["municipality"])
        for row in lse_facilities
    }
    lse_boundary_incidents = [
        row
        for row in scenario.incidents
        if row["critical_facility"] == "true"
        and row["severity"] == "low"
        and (row["region"], row["feeder"], row["municipality"])
        in lse_keys
    ]
    assert {row["customers_out"] for row in lse_boundary_incidents} >= set(
        LSE_CUSTOMER_BOUNDARIES
    )
    assert all(row["status"] == "unassigned" for row in lse_boundary_incidents)
    validate_lse_coverage(scenario.incidents, scenario.critical_facilities)

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


def test_geographic_reference_coverage_rejects_unmapped_or_wrong_region() -> None:
    with pytest.raises(ValueError, match="Unknown Village"):
        validate_geographic_reference_coverage(
            [{"municipality": "Unknown Village", "region": "Central-Nassau"}]
        )

    with pytest.raises(ValueError, match="Melville.*Eastern Suffolk.*Western Suffolk"):
        validate_geographic_reference_coverage(
            [{"municipality": "Melville", "region": "Eastern Suffolk"}]
        )


def test_facility_catalog_uses_approved_level_priority_mapping() -> None:
    assert {profile.dps_level for profile in FACILITY_CATALOG} == {1, 2, 3}
    assert all(
        profile.priority_level == {1: "critical", 2: "high", 3: "medium"}[
            profile.dps_level
        ]
        for profile in FACILITY_CATALOG
    )


def test_linkage_validation_reports_orphan_context() -> None:
    incident = {
        "incident_id": "ESD-20260810-0001",
        "region": "Central-Nassau",
        "municipality": "East Meadow",
        "feeder": "FDR-CN-99",
        "critical_facility": "true",
    }
    facility = {
        "facility_id": "FAC-CN-01",
        "facility_name": "East Meadow Fire Department",
        "region": "Central-Nassau",
        "municipality": "East Meadow",
        "feeder": "FDR-CN-01",
    }

    with pytest.raises(ValueError) as error:
        validate_critical_facility_linkage([incident], [facility])

    message = str(error.value)
    assert "ESD-20260810-0001" in message
    assert "Central-Nassau" in message
    assert "FDR-CN-99" in message
    assert "FAC-CN-01:FDR-CN-01" in message


def test_linkage_validation_rejects_cross_municipality_matches() -> None:
    incident = {
        "incident_id": "ESD-20260810-0001",
        "region": "Central-Nassau",
        "municipality": "East Meadow",
        "feeder": "FDR-CN-01",
        "critical_facility": "true",
    }
    facility = {
        "facility_id": "FAC-CN-01",
        "facility_name": "Hicksville Fire Department",
        "region": "Central-Nassau",
        "municipality": "Hicksville",
        "feeder": "FDR-CN-01",
    }

    with pytest.raises(ValueError, match="municipality-consistent"):
        validate_critical_facility_linkage([incident], [facility])


def test_generator_preserves_unassigned_capacity_for_lse_boundary_cases() -> None:
    with pytest.raises(ValueError, match="leave at least three unassigned incidents"):
        generate_scenario(
            scenario_id="insufficient-lse-capacity",
            start_date=date(2026, 8, 10),
            incident_count=20,
            crew_count=20,
            assignment_rate=1,
            dual_tree_incidents=0,
        )


def test_lse_validation_rejects_missing_boundary_case() -> None:
    scenario = generate_scenario(
        scenario_id="missing-lse-boundary",
        start_date=date(2026, 8, 10),
        incident_count=20,
        crew_count=20,
        assignment_rate=0,
        dual_tree_incidents=0,
    )
    boundary = scenario.incidents[-1]
    assert boundary["customers_out"] == LSE_CUSTOMER_BOUNDARIES[-1]
    assert boundary["severity"] == "low"
    assert boundary["critical_facility"] == "true"
    boundary["customers_out"] = 21

    with pytest.raises(ValueError, match="boundaries: 20"):
        validate_lse_coverage(scenario.incidents, scenario.critical_facilities)


def test_lse_validation_rejects_incorrect_level_metadata() -> None:
    scenario = generate_scenario(
        scenario_id="invalid-lse-metadata",
        start_date=date(2026, 8, 10),
        incident_count=20,
        crew_count=20,
        assignment_rate=0,
        dual_tree_incidents=0,
    )
    lse_facility = next(
        row
        for row in scenario.critical_facilities
        if row["facility_name"].endswith(LSE_FACILITY_SUFFIX)
    )
    lse_facility["priority_level"] = "high"

    with pytest.raises(ValueError, match="healthcare Level 3 metadata"):
        validate_lse_coverage(scenario.incidents, scenario.critical_facilities)


def test_generated_lse_boundaries_resolve_level_3_and_customer_threshold() -> None:
    scenario = generate_scenario(
        scenario_id="lse-scoring-boundaries",
        start_date=date(2026, 8, 10),
        incident_count=20,
        crew_count=20,
        assignment_rate=0,
        dual_tree_incidents=0,
    )
    engine = DeterministicOptimizationEngine(POC019_OPERATIONAL_RECOMMENDATION_POLICY)

    for row, expected_customer_contribution in zip(
        scenario.incidents[-3:],
        (0, 0, 1),
    ):
        incident = Incident.model_validate(row)
        impact = resolve_critical_facility_impact(
            incident,
            scenario.critical_facilities,
        )
        assert impact.level == 3
        evaluated = engine.evaluate_incidents(
            [
                incident.model_copy(
                    update={
                        "critical_facility_level": impact.level,
                        "matched_critical_facility_ids": impact.matched_facility_ids,
                    }
                )
            ]
        )[0]
        contributions = {
            factor.factor_id: factor.contribution
            for factor in evaluated.score.contributions
        }
        assert contributions["critical_facility"] == 40
        assert contributions["customers_out"] == expected_customer_contribution


def test_identical_seeds_produce_identical_lse_linkage() -> None:
    settings = {
        "scenario_id": "deterministic-lse",
        "start_date": date(2026, 8, 10),
        "incident_count": 40,
        "crew_count": 40,
        "assignment_rate": 0.1,
        "dual_tree_incidents": 1,
        "seed": 26,
    }

    first = generate_scenario(**settings)
    second = generate_scenario(**settings)

    assert first.incidents == second.incidents
    assert first.critical_facilities == second.critical_facilities


def test_start_day_locations_use_approved_facilities() -> None:
    expected_mua_contractor_locations = {
        "Queens-Nassau": {"RDA1 MUA Staging"},
        "Central-Nassau": {"RDA4 MUA Staging", "RDA7 MUA Staging"},
        "Western Suffolk": {"RDA10 MUA Staging", "RDA13 MUA Staging"},
        "Eastern Suffolk": {"RDA16 MUA Staging", "RDA19 MUA Staging"},
    }
    assert {
        region: set(locations)
        for region, locations in MUA_CONTRACTOR_LOCATIONS.items()
    } == expected_mua_contractor_locations

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
            assert crew["current_location"] in expected_mua_contractor_locations[crew["home_region"]]
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
    manifest = json.loads((target / "scenario.json").read_text(encoding="utf-8"))
    assert manifest["freshness"]["source"] == "scenario_generation"
    assert manifest["freshness"]["provenance"] == "AI Dispatch Advisor synthetic scenario generator"
    assert descriptor.freshness is not None
    assert descriptor.freshness.updated_at.utcoffset() is not None
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


def test_publication_rejects_incomplete_geographic_coverage(tmp_path: Path) -> None:
    scenario = generate_scenario(
        scenario_id="unmapped-geography",
        start_date=date(2026, 8, 10),
        incident_count=20,
        crew_count=20,
        assignment_rate=0,
        dual_tree_incidents=0,
    )
    scenario.incidents[0]["municipality"] = "Unknown Village"

    with pytest.raises(ValueError, match="Unknown Village"):
        write_scenario(scenario, tmp_path)

    assert not (tmp_path / scenario.scenario_id).exists()


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


def test_copilot_demo_preset_is_bounded_and_geographically_complete() -> None:
    scenario = generate_copilot_demo_scenario(start_date=date(2026, 8, 21))
    registry = GeographyRegistry.from_csv()

    assert scenario.scenario_id == "long-island-copilot-demo"
    assert len(scenario.incidents) == COPILOT_DEMO_INCIDENT_COUNT
    assert len(scenario.crews) == COPILOT_DEMO_CREW_COUNT
    assert {registry.require(row["municipality"]).county for row in scenario.incidents} == {
        "Nassau",
        "Suffolk",
        "Queens",
    }
    assert all(registry.resolve(row["municipality"]) for row in scenario.incidents)
    assert all(registry.resolve(row["current_location"]) for row in scenario.crews)
    assert {row["status"] for row in scenario.crews} == {"available", "assigned"}
    assert any(row["hazard"] == "none" for row in scenario.incidents)
    assert len({row["hazard"] for row in scenario.incidents}) >= 4
    assert any(row["critical_facility"] == "true" for row in scenario.incidents)
    arverne = next(row for row in scenario.incidents if row["municipality"] == "Arverne")
    assert arverne["required_skill"] == "line"
    assert any(
        row["facility_name"] == "Arverne Emergency Services Center"
        and row["feeder"] == arverne["feeder"]
        for row in scenario.critical_facilities
    )
    east_meadow = next(
        row for row in scenario.incidents if row["incident_id"] == "ESD-20260821-0011"
    )
    assert east_meadow["municipality"] == "East Meadow"
    assert east_meadow["feeder"] == "FDR-CN-35"
    assert east_meadow["critical_facility"] == "true"
    assert sum(
        row["critical_facility"] == "true" for row in scenario.incidents
    ) == 2 + len(LSE_CUSTOMER_BOUNDARIES)
    validate_lse_coverage(scenario.incidents, scenario.critical_facilities)
    assert any(
        row["facility_name"] == "East Meadow Fire Department"
        and row["facility_type"] == "emergency_services"
        and row["region"] == east_meadow["region"]
        and row["feeder"] == east_meadow["feeder"]
        and row["priority_level"] == "critical"
        for row in scenario.critical_facilities
    )
