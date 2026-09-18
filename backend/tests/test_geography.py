import csv
from datetime import date
from pathlib import Path

from app import data_loader
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


def test_full_scale_map_keeps_unresolved_staging_locations_unmapped() -> None:
    data_loader.set_active_scenario("august-storm-preview-v3")
    services = build_services()
    crews = services.crews.list()
    assert len(crews) == 500
    mapped = [crew for crew in crews if crew.map_location is not None]
    unmapped = [crew for crew in crews if crew.map_location is None]
    assert mapped and unmapped
    for crew in unmapped:
        assert services.geography.resolve(crew.current_location) is None
    # Assignment never substitutes an incident position for a crew village center.
    assert any(crew.assigned_incidents for crew in mapped)
