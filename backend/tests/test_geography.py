import csv
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from app import data_loader
from app.crew_map_location import CrewMapLocationResolver, STAGING_MAP_PROXIES
from app.geography import GeographyRegistry, TravelEstimateService
from app.scenario_generator import (
    generate_copilot_demo_scenario,
    load_municipalities,
    write_scenario,
)
from app.services import build_services


def test_registry_normalizes_owner_approved_geography_hierarchy() -> None:
    registry = GeographyRegistry.from_csv()

    arverne = registry.require("Arverne")
    assert (arverne.county, arverne.township, arverne.village) == (
        "Queens",
        "Rockaway Peninsula",
        "Arverne",
    )
    melville = registry.require("Melville")
    assert (melville.county, melville.township, melville.village) == (
        "Suffolk",
        "Huntington",
        "Melville",
    )
    assert registry.require("Rockaway Beach").village == "Rockaway Park"
    assert registry.resolve("Briarcliff") is None


def test_registry_covers_every_generator_municipality_with_stable_reference() -> None:
    registry = GeographyRegistry.from_csv()
    municipalities = load_municipalities()
    generator_names = {
        row["municipality"]
        for rows in municipalities.values()
        for row in rows
    }

    assert len(generator_names) == 48
    assert len(registry.records) == 49
    assert all(registry.resolve(name) is not None for name in generator_names)
    assert len({record.reference_id for record in registry.records}) == 49

    reference_path = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "reference"
        / "pseg-long-island"
        / "customers-served.csv"
    )
    with reference_path.open(newline="", encoding="utf-8") as handle:
        reference_by_id = {
            row["reference_id"]: row for row in csv.DictReader(handle)
        }
    for record in registry.records:
        reference = reference_by_id[record.reference_id]
        assert (
            record.source_county,
            record.source_township,
            record.source_village,
        ) == (
            reference["source_county"],
            reference["source_township"],
            reference["source_village"],
        )
        assert (record.county, record.township, record.village) == (
            reference["county"],
            reference["township"],
            reference["village"],
        )

    assert registry.require("Floral Park").township == "Hempstead"
    assert registry.require("Commack").township == "Huntington"
    assert registry.require("Calverton").township == "Riverhead"
    assert registry.require("Westhampton Beach").township == "Southampton"


def test_travel_estimates_are_deterministic_and_incident_specific() -> None:
    service = TravelEstimateService(GeographyRegistry.from_csv())
    arverne = service.registry.require("Arverne")
    montauk = service.registry.require("Montauk")

    local = service.estimate(
        origin_name="Cedarhurst",
        destination_name="Arverne",
        destination_latitude=arverne.latitude,
        destination_longitude=arverne.longitude,
    )
    east_end = service.estimate(
        origin_name="Cedarhurst",
        destination_name="Montauk",
        destination_latitude=montauk.latitude,
        destination_longitude=montauk.longitude,
    )

    assert local is not None
    assert east_end is not None
    assert local == service.estimate(
        origin_name="Cedarhurst",
        destination_name="Arverne",
        destination_latitude=arverne.latitude,
        destination_longitude=arverne.longitude,
    )
    assert 5 <= local.estimated_travel_minutes < 45
    assert east_end.estimated_travel_minutes > local.estimated_travel_minutes
    assert service.estimate(
        origin_name="Unknown Yard",
        destination_name="Arverne",
        destination_latitude=arverne.latitude,
        destination_longitude=arverne.longitude,
    ) is None


def test_recommendation_uses_derived_travel_for_requested_incident(
    tmp_path: Path,
    monkeypatch,
) -> None:
    scenario = generate_copilot_demo_scenario(start_date=date(2026, 8, 21))
    write_scenario(scenario, tmp_path)
    monkeypatch.setattr(data_loader, "DATA_ROOT", tmp_path)
    data_loader.set_active_scenario(scenario.scenario_id)
    services = build_services()
    assert services.incidents.list_ranked()[0].municipality == "Arverne"
    incident = next(
        row for row in services.incidents.list_ranked() if row.municipality == "Arverne"
    )

    recommendation = services.recommendations.recommend(incident.incident_id)
    default_recommendation = services.recommendations.recommend()

    assert recommendation.recommended_crew is not None
    assert default_recommendation.incident_id == incident.incident_id
    assert default_recommendation.recommended_crew is not None
    assert default_recommendation.recommended_crew.crew_id == (
        recommendation.recommended_crew.crew_id
    )
    selected = recommendation.recommended_crew
    source_crew = next(
        row for row in services.crews.list() if row.crew_id == selected.crew_id
    )
    expected = services.travel_estimates.estimate_for(source_crew, incident)
    assert expected is not None
    assert selected.estimated_travel_minutes == expected.estimated_travel_minutes

    ineligible_estimates = [
        services.travel_estimates.estimate_for(crew, incident)
        for crew in services.crews.list()
        if crew.status == "available" and crew.capability != "line"
    ]
    ineligible_travel = min(
        estimate.estimated_travel_minutes
        for estimate in ineligible_estimates
        if estimate is not None
    )
    assert ineligible_travel < selected.estimated_travel_minutes


def test_crew_map_locations_use_authoritative_village_centers() -> None:
    data_loader.set_active_scenario("long-island-copilot-demo")
    services = build_services()
    crews = services.crews.list()
    assert crews
    for crew in crews:
        location = services.geography.require(crew.current_location)
        assert crew.map_location is not None
        assert crew.map_location.precision == "village_center"
        assert crew.map_location.latitude == location.latitude
        assert crew.map_location.longitude == location.longitude
        assert crew.map_location.village == location.village
        assert crew.map_location.reference_id == location.reference_id
        assert crew.map_location.resolution_basis == "source_place"


def test_crew_map_proxy_resolves_only_approved_label_and_division_pairs() -> None:
    registry = GeographyRegistry.from_csv()
    resolver = CrewMapLocationResolver(registry)
    for label, division, reference_id in STAGING_MAP_PROXIES:
        resolved = resolver.resolve(label, division)
        assert resolved is not None
        assert resolved.basis == "operating_hq_proxy"
        assert resolved.place.reference_id == reference_id
        assert resolver.resolve(label.lower().replace(" ", "--"), division) == resolved
        assert resolver.resolve(label, "Wrong division") is None

    assert resolver.resolve("RDA2 MUA Staging", "Queens-Nassau") is None
    assert resolver.resolve("Unknown Yard", "Queens-Nassau") is None
    assert resolver.resolve("RDA1 MUA Staging extra", "Queens-Nassau") is None
    direct = resolver.resolve("Hicksville", "Western Suffolk")
    assert direct is not None
    assert direct.basis == "source_place"


def test_crew_map_proxy_fails_closed_if_target_is_missing(caplog) -> None:
    registry = GeographyRegistry.from_csv()
    without_hewlett = GeographyRegistry(
        record for record in registry.records if record.village != "Hewlett"
    )
    resolver = CrewMapLocationResolver(without_hewlett)
    assert resolver.resolve("RDA1 MUA Staging", "Queens-Nassau") is None
    assert "invalid or missing reference" in caplog.text

    wrong_village = GeographyRegistry(
        replace(record, village="Wrong village") if record.village == "Hewlett" else record
        for record in registry.records
    )
    assert CrewMapLocationResolver(wrong_village).resolve(
        "RDA1 MUA Staging", "Queens-Nassau"
    ) is None


@pytest.mark.parametrize("scenario_id,expected_proxies", [
    ("august-storm-preview-v3", 55),
    ("september-storm-preview-v2", 168),
])
def test_full_scale_map_resolves_staging_proxies_without_changing_reported_locations(
    scenario_id: str, expected_proxies: int,
) -> None:
    data_loader.set_active_scenario(scenario_id)
    services = build_services()
    crews = services.crews.list()
    assert crews
    source_locations = {
        row["crew_id"]: row["current_location"] for row in data_loader.crews()
    }
    mapped = [crew for crew in crews if crew.map_location is not None]
    unmapped = [crew for crew in crews if crew.map_location is None]
    assert len(mapped) == len(crews)
    assert not unmapped
    proxies = [
        crew for crew in mapped
        if crew.map_location and crew.map_location.resolution_basis == "operating_hq_proxy"
    ]
    assert len(proxies) == expected_proxies
    assert all(crew.current_location == source_locations[crew.crew_id] for crew in crews)
    for crew in proxies:
        assert services.geography.resolve(crew.current_location) is None
    assert services.travel_estimates.estimate_for(proxies[0], services.incidents.list_ranked()[0]) is None
    # Assignment never substitutes an incident position for a crew village center.
    assert any(crew.assigned_incidents for crew in mapped)
