from __future__ import annotations

import csv
import json
import random
import re
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .geography import DEFAULT_GEOGRAPHY_PATH, GeographyRegistry, TravelEstimateService
from .services.reference_service import (
    DEFAULT_REFERENCE_ROOT,
    PsegLongIslandReferenceService,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "data" / "scenario-previews"
DEFAULT_LOOKUP_PATH = REPO_ROOT / "data" / "generator-lookups" / "LongIslandMunicipalities.csv"
DEFAULT_GEOGRAPHY_COVERAGE_PER_INCIDENTS = 6
LOCAL_TIMEZONE = ZoneInfo("America/New_York")

REGIONS = (
    "Queens-Nassau",
    "Central-Nassau",
    "Western Suffolk",
    "Eastern Suffolk",
)
REGION_NUMBER_BANDS = {
    "Queens-Nassau": (1000, 1999),
    "Central-Nassau": (2000, 2999),
    "Western Suffolk": (3000, 3999),
    "Eastern Suffolk": (4000, 4999),
}
REGION_CODES = {
    "Queens-Nassau": "QN",
    "Central-Nassau": "CN",
    "Western Suffolk": "WS",
    "Eastern Suffolk": "ES",
}
SERVICE_LOCATIONS = {
    "Queens-Nassau": "Hewlett Service Center",
    "Central-Nassau": "Hicksville Operations Yard",
    "Western Suffolk": "Brentwood Operations Yard",
    "Eastern Suffolk": "Riverhead Operations Yard",
}
VEGETATION_LOCATIONS = {
    region: f"{municipality} Vegetation Staging Area"
    for region, municipality in {
        "Queens-Nassau": "Hewlett",
        "Central-Nassau": "Hicksville",
        "Western Suffolk": "Brentwood",
        "Eastern Suffolk": "Riverhead",
    }.items()
}
MUA_CONTRACTOR_LOCATIONS = {
    "Queens-Nassau": ("RDA1 MUA Staging",),
    "Central-Nassau": ("RDA4 MUA Staging", "RDA7 MUA Staging"),
    "Western Suffolk": ("RDA10 MUA Staging", "RDA13 MUA Staging"),
    "Eastern Suffolk": ("RDA16 MUA Staging", "RDA19 MUA Staging"),
}
DEFAULT_START_DAY_LOCATION_RATE = 0.35
DEFAULT_CRITICAL_FACILITY_RATE = 0.04
DEFAULT_CRITICAL_IMPACT_RATE = 0.08
LSE_FACILITY_SUFFIX = "Private Health Device (LSE)"
LSE_CUSTOMER_BOUNDARIES = (1, 19, 20)
COPILOT_DEMO_SCENARIO_ID = "long-island-copilot-demo"
COPILOT_DEMO_INCIDENT_COUNT = 24
COPILOT_DEMO_CREW_COUNT = 32
COPILOT_DEMO_ASSIGNMENT_RATE = 0.25
COPILOT_DEMO_DUAL_TREE_INCIDENTS = 1
COPILOT_DEMO_CRITICAL_FACILITIES_PER_REGION = 2
COPILOT_DEMO_SEED = 20260821
COPILOT_DEMO_MUNICIPALITIES = (
    "Arverne",
    "Edgemere",
    "Far Rockaway",
    "Rockaway Park",
    "Hewlett",
    "Cedarhurst",
    "Valley Stream",
    "Mineola",
    "Hicksville",
    "East Meadow",
    "Westbury",
    "Hempstead",
    "Massapequa",
    "Babylon",
    "Brentwood",
    "Melville",
    "Smithtown",
    "Bay Shore",
    "Riverhead",
    "Yaphank",
    "Westhampton Beach",
    "Southampton",
    "Montauk",
    "Greenport",
)

INCIDENT_HEADERS = [
    "incident_id",
    "region",
    "municipality",
    "geography_reference_id",
    "feeder",
    "severity",
    "status",
    "customers_out",
    "critical_facility",
    "hazard",
    "required_skill",
    "age_minutes",
    "latitude",
    "longitude",
    "etr",
]
CREW_HEADERS = [
    "crew_id",
    "crew_name",
    "home_region",
    "status",
    "capability",
    "current_location",
    "shift_remaining_hours",
    "storm_ready",
    "travel_minutes_to_selected_incident",
]
ASSIGNMENT_HEADERS = [
    "assignment_id",
    "incident_id",
    "crew_id",
    "status",
    "assigned_at",
    "notes",
]
HISTORICAL_REPAIR_HEADERS = [
    "repair_id",
    "incident_type",
    "region",
    "average_duration_minutes",
    "crew_type",
    "notes",
]
WEATHER_HEADERS = [
    "weather_id",
    "region",
    "condition",
    "wind_mph",
    "precipitation_inches",
    "lightning_risk",
    "updated_at",
]
CRITICAL_FACILITY_HEADERS = [
    "facility_id",
    "facility_name",
    "facility_type",
    "region",
    "municipality",
    "feeder",
    "priority_level",
]
TOPOLOGY_HEADERS = [
    "asset_id",
    "asset_type",
    "feeder",
    "parent_asset_id",
    "region",
    "normal_status",
]


@dataclass(frozen=True)
class CrewSpec:
    key: str
    label: str
    default_count: int
    prefix: str | None
    capability: str
    number_ranges: tuple[tuple[int, int], ...]
    region_encoded: bool


@dataclass(frozen=True)
class FacilityProfile:
    """Approved synthetic facility classification used by seeded generation."""

    name_suffix: str
    facility_type: str
    dps_level: int
    priority_level: str


@dataclass(frozen=True)
class CapacityGeography:
    reference_id: str
    region: str
    municipality: str
    county: str
    township: str
    village: str
    latitude: float
    longitude: float
    customers_served: int


FACILITY_CATALOG = (
    FacilityProfile("Regional Medical Center", "hospital", 1, "critical"),
    FacilityProfile("Emergency Services Center", "emergency_services", 1, "critical"),
    FacilityProfile("Emergency Shelter", "shelter", 1, "critical"),
    FacilityProfile("Fire District Headquarters", "emergency_services", 1, "critical"),
    FacilityProfile("Police Precinct", "emergency_services", 1, "critical"),
    FacilityProfile("Water Treatment Facility", "water", 1, "critical"),
    FacilityProfile("Water Pumping Station", "water", 1, "critical"),
    FacilityProfile("Wastewater Treatment Facility", "water", 1, "critical"),
    FacilityProfile("Wastewater Pump Station", "water", 1, "critical"),
    FacilityProfile("Transit Operations Center", "transportation", 1, "critical"),
    FacilityProfile("Public Safety Communications Center", "communications", 1, "critical"),
    FacilityProfile("Nursing Home", "healthcare", 2, "high"),
    FacilityProfile("Dialysis Center", "healthcare", 2, "high"),
    FacilityProfile("Correctional Facility", "public_services", 2, "high"),
    FacilityProfile("Broadcast Communications Facility", "communications", 2, "high"),
    FacilityProfile("Senior Care Center", "healthcare", 3, "medium"),
    FacilityProfile("Health Related Facility", "healthcare", 3, "medium"),
    FacilityProfile(LSE_FACILITY_SUFFIX, "healthcare", 3, "medium"),
)


CREW_SPECS = (
    CrewSpec("lkp", "Lookup Crew", 60, "LKP", "general", ((1000, 4999),), True),
    CrewSpec("ww", "Wire Watcher", 40, "WW", "general", ((1000, 4999),), True),
    CrewSpec("troubleshooter", "Troubleshooter", 110, None, "general", ((1000, 4999),), True),
    CrewSpec("low_voltage", "Low Voltage Crew", 70, None, "low_voltage", ((5000, 5999), (7000, 7999)), False),
    CrewSpec("line", "Line Crew", 70, None, "line", ((6000, 6999),), False),
    CrewSpec("mua", "Mutual Aid Crew", 60, "MUA", "line", ((1000, 4999),), True),
    CrewSpec("cntr", "Contractor Crew", 55, "CNTR", "line", ((1000, 4999),), True),
    CrewSpec("tree", "Tree Crew", 25, "TREE", "vegetation", ((1000, 4999),), True),
    CrewSpec("cg", "Crew Guide", 10, "CG", "general", ((1000, 4999),), True),
)


@dataclass
class GeneratedScenario:
    scenario_id: str
    incidents: list[dict[str, Any]]
    crews: list[dict[str, Any]]
    assignments: list[dict[str, Any]]
    historical_repairs: list[dict[str, Any]]
    weather: list[dict[str, Any]]
    critical_facilities: list[dict[str, Any]]
    topology: list[dict[str, Any]]
    crew_types: dict[str, str]

    def summary(self) -> dict[str, Any]:
        geography_ids = {
            str(row["geography_reference_id"])
            for row in self.incidents
            if row.get("geography_reference_id")
        }
        return {
            "scenario_id": self.scenario_id,
            "incidents": len(self.incidents),
            "crews": len(self.crews),
            "assigned_incidents": sum(row["status"] == "assigned" for row in self.incidents),
            "assignments": len(self.assignments),
            "historical_repairs": len(self.historical_repairs),
            "weather_observations": len(self.weather),
            "critical_facilities": len(self.critical_facilities),
            "topology_assets": len(self.topology),
            "crew_distribution": dict(sorted(Counter(self.crew_types.values()).items())),
            "regions": dict(sorted(Counter(row["region"] for row in self.incidents).items())),
            "customers_out": sum(int(row["customers_out"]) for row in self.incidents),
            "geography_coverage": len(geography_ids),
        }


def _date_range(start_date: date, end_date: date) -> list[date]:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    return [start_date + timedelta(days=offset) for offset in range((end_date - start_date).days + 1)]


def _allocate_counts(total: int) -> dict[str, int]:
    if total <= 0:
        raise ValueError("crew_count must be positive")
    baseline = sum(spec.default_count for spec in CREW_SPECS)
    exact = {spec.key: total * spec.default_count / baseline for spec in CREW_SPECS}
    counts = {key: int(value) for key, value in exact.items()}
    remaining = total - sum(counts.values())
    order = sorted(exact, key=lambda key: (exact[key] - counts[key], exact[key]), reverse=True)
    for key in order[:remaining]:
        counts[key] += 1
    return counts


def load_municipalities(path: Path = DEFAULT_LOOKUP_PATH) -> dict[str, list[dict[str, Any]]]:
    by_region: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        expected = ["region", "municipality", "locality_type", "latitude", "longitude"]
        if reader.fieldnames is None or reader.fieldnames[: len(expected)] != expected:
            raise ValueError(f"Municipality lookup headers must begin with {expected}")
        for row in reader:
            if row["region"] not in REGIONS:
                raise ValueError(f"Unknown municipality region: {row['region']}")
            by_region[row["region"]].append(
                {
                    **row,
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                }
            )
    missing = [region for region in REGIONS if not by_region[region]]
    if missing:
        raise ValueError(f"Municipality lookup has no entries for: {', '.join(missing)}")
    return dict(by_region)


def _capacity_region(
    *,
    reference_id: str,
    county: str,
    township: str,
    approved_by_id: dict[str, Any],
) -> str:
    approved = approved_by_id.get(reference_id)
    if approved is not None:
        return str(approved.region)
    if county == "Queens":
        return "Queens-Nassau"
    if county == "Nassau":
        return "Queens-Nassau" if township == "Hempstead" else "Central-Nassau"
    if township in {"Babylon", "Huntington", "Islip", "Smithtown"}:
        return "Western Suffolk"
    return "Eastern Suffolk"


def _synthetic_reference_coordinates(
    reference_id: str,
    region: str,
) -> tuple[float, float]:
    centers = {
        "Queens-Nassau": (40.6650, -73.7200),
        "Central-Nassau": (40.7500, -73.5600),
        "Western Suffolk": (40.7900, -73.2200),
        "Eastern Suffolk": (40.9100, -72.6100),
    }
    latitude, longitude = centers[region]
    value = int(reference_id.removeprefix("pseg-li-")[:12], 16)
    latitude += ((value % 2001) - 1000) / 100_000
    longitude += (((value // 2001) % 3001) - 1500) / 100_000
    return round(latitude, 5), round(longitude, 5)


def load_capacity_geographies(
    *,
    reference_root: Path = DEFAULT_REFERENCE_ROOT,
    geography_path: Path = DEFAULT_GEOGRAPHY_PATH,
) -> list[CapacityGeography]:
    snapshot = PsegLongIslandReferenceService(reference_root).snapshot()
    if snapshot.validation.reference_status != "current":
        issues = "; ".join(
            f"{issue.location}: {issue.message}"
            for issue in snapshot.validation.issues
        )
        detail = f" ({issues})" if issues else ""
        raise ValueError(
            "Population-constrained generation requires a current, approved "
            f"customers-served reference; status was {snapshot.validation.reference_status}{detail}"
        )

    approved_registry = GeographyRegistry.from_csv(geography_path)
    approved_by_id = {
        record.reference_id: record for record in approved_registry.records
    }
    village_counts = Counter(row.village.casefold() for row in snapshot.rows)
    result: list[CapacityGeography] = []
    for row in snapshot.rows:
        approved = approved_by_id.get(row.reference_id)
        region = _capacity_region(
            reference_id=row.reference_id,
            county=row.county,
            township=row.township,
            approved_by_id=approved_by_id,
        )
        if approved is not None:
            latitude, longitude = approved.latitude, approved.longitude
        else:
            latitude, longitude = _synthetic_reference_coordinates(
                row.reference_id,
                region,
            )
        municipality = (
            f"{row.village}-{row.township}"
            if village_counts[row.village.casefold()] > 1
            else row.village
        )
        result.append(
            CapacityGeography(
                reference_id=row.reference_id,
                region=region,
                municipality=municipality,
                county=row.county,
                township=row.township,
                village=row.village,
                latitude=latitude,
                longitude=longitude,
                customers_served=row.customers_served,
            )
        )
    return result


def _apply_capacity_location(
    incident: dict[str, Any],
    geography: CapacityGeography,
    *,
    feeder: str | None = None,
) -> None:
    incident.update(
        region=geography.region,
        municipality=geography.municipality,
        geography_reference_id=geography.reference_id,
        latitude=geography.latitude,
        longitude=geography.longitude,
        feeder=feeder or (
            f"FDR-{REGION_CODES[geography.region]}-"
            f"{(int(geography.reference_id[-4:], 16) + int(str(incident['incident_id'])[-4:])) % 98 + 1:02d}"
        ),
    )


def _select_capacity_geographies(
    geographies: list[CapacityGeography],
    *,
    incident_count: int,
    customers_out: int,
    coverage_target: int | None,
) -> list[CapacityGeography]:
    max_coverage = max(1, incident_count - len(LSE_CUSTOMER_BOUNDARIES) + 1)
    if coverage_target is None:
        requested = max(
            min(48, max_coverage),
            (incident_count + DEFAULT_GEOGRAPHY_COVERAGE_PER_INCIDENTS - 1)
            // DEFAULT_GEOGRAPHY_COVERAGE_PER_INCIDENTS,
        )
    else:
        if coverage_target <= 0:
            raise ValueError("geography_coverage_target must be positive")
        requested = coverage_target
    if requested > max_coverage:
        raise ValueError(
            "geography_coverage_target exceeds the number of distinct locations "
            "available after reserving the three co-located LSE boundary incidents"
        )
    if requested > len(geographies):
        raise ValueError(
            f"geography_coverage_target {requested} exceeds the approved "
            f"{len(geographies)}-leaf reference"
        )

    ordered = sorted(
        geographies,
        key=lambda row: (-row.customers_served, row.reference_id),
    )
    selected = ordered[:requested]
    index = requested
    while sum(row.customers_served for row in selected) < customers_out:
        if index >= len(ordered):
            total_capacity = sum(row.customers_served for row in geographies)
            raise ValueError(
                "Requested scenario-wide customers_out target cannot fit the "
                f"approved reference capacity: requested {customers_out:,}, "
                f"available {total_capacity:,}"
            )
        selected.append(ordered[index])
        index += 1
    return selected


def allocate_population_capacity(
    incidents: list[dict[str, Any]],
    geographies: list[CapacityGeography],
    *,
    coverage_target: int | None = None,
) -> None:
    customers_out = sum(int(row["customers_out"]) for row in incidents)
    selected = _select_capacity_geographies(
        geographies,
        incident_count=len(incidents),
        customers_out=customers_out,
        coverage_target=coverage_target,
    )
    remaining = {row.reference_id: row.customers_served for row in selected}
    used: set[str] = set()

    def place(rows: list[dict[str, Any]], *, region: str | None = None) -> None:
        required = sum(int(row["customers_out"]) for row in rows)
        candidates = [
            row for row in selected
            if (region is None or row.region == region)
            and remaining[row.reference_id] >= required
        ]
        if not candidates:
            scope = f" in {region}" if region else ""
            raise ValueError(
                "Population capacity allocation failed"
                f"{scope}: no approved geography has {required:,} remaining customers"
            )
        geography = min(
            candidates,
            key=lambda row: (
                row.reference_id in used,
                remaining[row.reference_id],
                row.reference_id,
            ),
        )
        remaining[geography.reference_id] -= required
        used.add(geography.reference_id)
        shared_feeder = (
            f"FDR-{REGION_CODES[geography.region]}-99" if len(rows) > 1 else None
        )
        for incident in rows:
            _apply_capacity_location(incident, geography, feeder=shared_feeder)

    lse_rows = incidents[-len(LSE_CUSTOMER_BOUNDARIES) :]
    place(lse_rows)
    lse_ids = {str(row["incident_id"]) for row in lse_rows}

    assigned = sorted(
        (
            row for row in incidents
            if row["status"] == "assigned" and str(row["incident_id"]) not in lse_ids
        ),
        key=lambda row: (-int(row["customers_out"]), str(row["incident_id"])),
    )
    for incident in assigned:
        place([incident], region=str(incident["region"]))

    unassigned = [
        row for row in incidents
        if row["status"] != "assigned" and str(row["incident_id"]) not in lse_ids
    ]
    unassigned.sort(key=lambda row: (int(row["customers_out"]), str(row["incident_id"])))
    unused_geographies = sorted(
        (row for row in selected if row.reference_id not in used),
        key=lambda row: (row.customers_served, row.reference_id),
    )
    remaining_incidents = list(unassigned)
    for geography in unused_geographies:
        match_index = next(
            (
                index for index, incident in enumerate(remaining_incidents)
                if int(incident["customers_out"]) <= remaining[geography.reference_id]
            ),
            None,
        )
        if match_index is None:
            continue
        incident = remaining_incidents.pop(match_index)
        remaining[geography.reference_id] -= int(incident["customers_out"])
        used.add(geography.reference_id)
        _apply_capacity_location(incident, geography)

    remaining_incidents.sort(
        key=lambda row: (-int(row["customers_out"]), str(row["incident_id"]))
    )
    for incident in remaining_incidents:
        place([incident])

    achieved = len(used)
    requested = coverage_target or min(
        len(selected),
        max(
            min(48, len(incidents) - len(LSE_CUSTOMER_BOUNDARIES) + 1),
            (len(incidents) + DEFAULT_GEOGRAPHY_COVERAGE_PER_INCIDENTS - 1)
            // DEFAULT_GEOGRAPHY_COVERAGE_PER_INCIDENTS,
        ),
    )
    if achieved < requested:
        raise ValueError(
            "Population capacity allocation could not meet geography coverage target: "
            f"requested {requested}, achieved {achieved}"
        )


def apply_customer_out_target(
    incidents: list[dict[str, Any]],
    target: int,
) -> None:
    if target <= 0:
        raise ValueError("customer_out_target must be positive")
    lse_ids = {
        str(row["incident_id"])
        for row in incidents[-len(LSE_CUSTOMER_BOUNDARIES) :]
    }
    lower_bounds: dict[str, int] = {}
    for incident in incidents:
        incident_id = str(incident["incident_id"])
        if incident_id in lse_ids:
            lower_bounds[incident_id] = int(incident["customers_out"])
        elif str(incident.get("required_skill")) == "low_voltage":
            lower_bounds[incident_id] = 1
        elif (
            incident.get("status") == "assigned"
            and str(incident.get("required_skill")) == "line"
        ):
            lower_bounds[incident_id] = 40
        else:
            lower_bounds[incident_id] = 1
    minimum_total = sum(lower_bounds.values())
    if target < minimum_total:
        raise ValueError(
            "customer_out_target is below required incident minimums: "
            f"requested {target:,}, minimum {minimum_total:,}"
        )

    adjustable = [
        row for row in incidents if str(row["incident_id"]) not in lse_ids
    ]
    available = target - minimum_total
    weights = {
        str(row["incident_id"]): max(
            0,
            int(row["customers_out"]) - lower_bounds[str(row["incident_id"])],
        )
        for row in adjustable
    }
    weight_total = sum(weights.values())
    exact: dict[str, float] = {}
    allocated = 0
    for row in adjustable:
        incident_id = str(row["incident_id"])
        share = (
            available * weights[incident_id] / weight_total
            if weight_total
            else available / max(1, len(adjustable))
        )
        exact[incident_id] = share
        addition = int(share)
        row["customers_out"] = lower_bounds[incident_id] + addition
        allocated += addition
    remainder = available - allocated
    for row in sorted(
        adjustable,
        key=lambda item: (
            -(exact[str(item["incident_id"])] % 1),
            str(item["incident_id"]),
        ),
    )[:remainder]:
        row["customers_out"] = int(row["customers_out"]) + 1


def _balanced_regions(count: int, rng: random.Random) -> list[str]:
    regions = list(REGIONS)
    result = [regions[index % len(regions)] for index in range(count)]
    rng.shuffle(result)
    return result


def _numbers_for_spec(spec: CrewSpec, count: int, rng: random.Random) -> list[tuple[int, str]]:
    if spec.region_encoded:
        regions = _balanced_regions(count, rng)
        used: set[int] = set()
        result: list[tuple[int, str]] = []
        for region in regions:
            low, high = REGION_NUMBER_BANDS[region]
            available = [number for number in range(low, high + 1) if number not in used]
            if not available:
                raise ValueError(f"Crew ID range exhausted for {spec.key} in {region}")
            number = rng.choice(available)
            used.add(number)
            result.append((number, region))
        return result

    available_numbers = [
        number
        for low, high in spec.number_ranges
        for number in range(low, high + 1)
    ]
    if count > len(available_numbers):
        raise ValueError(f"Crew ID range exhausted for {spec.key}")
    numbers = rng.sample(available_numbers, count)
    regions = _balanced_regions(count, rng)
    return list(zip(numbers, regions))


def _generate_crews(
    crew_count: int,
    municipalities: dict[str, list[dict[str, Any]]],
    rng: random.Random,
    start_day_location_rate: float,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    counts = _allocate_counts(crew_count)
    rows: list[dict[str, Any]] = []
    crew_types: dict[str, str] = {}
    for spec in CREW_SPECS:
        for number, region in _numbers_for_spec(spec, counts[spec.key], rng):
            crew_id = f"{spec.prefix}-{number}" if spec.prefix else str(number)
            if rng.random() < start_day_location_rate:
                if spec.key == "tree":
                    current_location = VEGETATION_LOCATIONS[region]
                elif spec.key in {"mua", "cntr"}:
                    current_location = rng.choice(MUA_CONTRACTOR_LOCATIONS[region])
                else:
                    current_location = SERVICE_LOCATIONS[region]
            else:
                current_location = rng.choice(municipalities[region])["municipality"]
            rows.append(
                {
                    "crew_id": crew_id,
                    "crew_name": f"{region} {spec.label} {number}",
                    "home_region": region,
                    "status": "available",
                    "capability": spec.capability,
                    "current_location": current_location,
                    "shift_remaining_hours": rng.randint(3, 12),
                    "storm_ready": "true" if rng.random() < 0.8 else "false",
                    "travel_minutes_to_selected_incident": rng.randint(8, 75),
                }
            )
            crew_types[crew_id] = spec.key
    rng.shuffle(rows)
    return rows, crew_types


def _incident_dates(start_date: date, end_date: date, incident_count: int) -> list[tuple[date, int]]:
    dates = _date_range(start_date, end_date)
    if incident_count > len(dates) * 9999:
        raise ValueError("incident_count exceeds ESD daily sequence capacity for the selected date range")
    counters: Counter[date] = Counter()
    result: list[tuple[date, int]] = []
    for index in range(incident_count):
        incident_date = dates[index % len(dates)]
        counters[incident_date] += 1
        result.append((incident_date, counters[incident_date]))
    return result


def _iso_at(incident_date: date, hour: int, minute: int = 0) -> str:
    return datetime.combine(incident_date, time(hour=hour, minute=minute), LOCAL_TIMEZONE).isoformat()


def _base_incident(
    incident_date: date,
    sequence: int,
    municipalities: dict[str, list[dict[str, Any]]],
    rng: random.Random,
) -> dict[str, Any]:
    region = rng.choice(REGIONS)
    locality = rng.choice(municipalities[region])
    templates = (
        ("none", "general", "low", 1, 180),
        ("partial outage", "general", "medium", 2, 450),
        ("downed wire", "general", "high", 1, 500),
        ("burning wire", "general", "high", 1, 350),
        ("tree limb", "vegetation", "medium", 5, 900),
        ("tree on primary", "vegetation", "high", 40, 1600),
        ("broken crossarm", "line", "high", 40, 1800),
        ("transformer fire", "line", "critical", 40, 2600),
        ("underground cable fault", "underground", "high", 20, 1200),
        ("damaged service drop", "low_voltage", "low", 1, 1),
    )
    hazard, required_skill, severity, minimum, maximum = rng.choice(templates)
    feeder = f"FDR-{REGION_CODES[region]}-{rng.randint(1, 40):02d}"
    customers_out = rng.randint(minimum, maximum)
    if severity in {"high", "critical"}:
        # Preserve the established seeded stream while linked generation ignores
        # the former independent critical-impact roll.
        rng.random()
    age_minutes = rng.randint(5, 180)
    latitude = round(locality["latitude"] + rng.uniform(-0.012, 0.012), 5)
    longitude = round(locality["longitude"] + rng.uniform(-0.012, 0.012), 5)
    etr = _iso_at(
        incident_date,
        rng.randint(10, 22),
        rng.choice((0, 15, 30, 45)),
    )
    return {
        "incident_id": f"ESD-{incident_date:%Y%m%d}-{sequence:04d}",
        "region": region,
        "municipality": locality["municipality"],
        "feeder": feeder,
        "severity": severity,
        "status": "unassigned",
        "customers_out": customers_out,
        # Linked generation finalizes this flag only after the stable facility
        # catalog exists. Keeping the base row false prevents orphan impacts.
        "critical_facility": "false",
        "hazard": hazard,
        "required_skill": required_skill,
        "age_minutes": age_minutes,
        "latitude": latitude,
        "longitude": longitude,
        "etr": etr,
    }


def _set_incident_location(
    incident: dict[str, Any],
    region: str,
    municipalities: dict[str, list[dict[str, Any]]],
    rng: random.Random,
) -> None:
    locality = rng.choice(municipalities[region])
    incident.update(
        {
            "region": region,
            "municipality": locality["municipality"],
            "latitude": round(locality["latitude"] + rng.uniform(-0.008, 0.008), 5),
            "longitude": round(locality["longitude"] + rng.uniform(-0.008, 0.008), 5),
            "feeder": f"FDR-{REGION_CODES[region]}-{rng.randint(1, 40):02d}",
        }
    )


def _configure_for_crew(
    incident: dict[str, Any],
    crew_type: str,
    region: str,
    municipalities: dict[str, list[dict[str, Any]]],
    rng: random.Random,
) -> str:
    _set_incident_location(incident, region, municipalities, rng)
    incident["status"] = "assigned"
    incident["critical_facility"] = "false"
    if crew_type == "low_voltage":
        incident.update(severity=rng.choice(("low", "medium")), customers_out=1, hazard="damaged service drop", required_skill="low_voltage")
        return "Internal low-voltage crew assigned to single-customer service repair"
    if crew_type == "line":
        incident.update(severity=rng.choice(("high", "critical")), customers_out=rng.randint(40, 2800), hazard=rng.choice(("feeder lockout", "broken crossarm", "transformer fire")), required_skill="line")
        return "Internal line crew assigned to high-voltage repair"
    if crew_type in {"mua", "cntr"}:
        incident.update(severity=rng.choice(("high", "critical")), customers_out=rng.randint(40, 3000), hazard=rng.choice(("feeder lockout", "broken crossarm", "transformer fire")), required_skill="line")
        return "Repair crew assigned to primary restoration"
    if crew_type == "tree":
        incident.update(severity=rng.choice(("medium", "high")), customers_out=rng.randint(5, 1400), hazard=rng.choice(("tree limb", "tree on primary")), required_skill="vegetation")
        return "Tree crew assigned to vegetation removal"
    if crew_type in {"lkp", "ww"}:
        incident.update(severity=rng.choice(("high", "critical")), customers_out=rng.randint(1, 600), hazard=rng.choice(("downed wire", "burning wire", "arcing wire")), required_skill="general")
        return "Damage-assessment first responder assigned to wire hazard"
    if crew_type == "cg":
        incident.update(severity=rng.choice(("medium", "high")), customers_out=rng.randint(10, 1200), hazard="blocked access", required_skill="general")
        return "Crew guide assigned to lead repair resources to the incident"
    incident.update(severity=rng.choice(("low", "medium", "high", "critical")), customers_out=rng.randint(1, 2200), hazard=rng.choice(("none", "partial outage", "downed wire", "equipment failure")), required_skill="general")
    return "ESD troubleshooter assigned as first responder"


def _suffix_region(crew_id: str) -> str | None:
    suffix = crew_id.rsplit("-", 1)[-1]
    if not suffix.isdigit() or len(suffix) != 4:
        return None
    first_digit = int(suffix[0])
    return REGIONS[first_digit - 1] if 1 <= first_digit <= 4 else None


def _generate_weather(observation_date: date, rng: random.Random) -> list[dict[str, Any]]:
    profiles = (
        ("thunderstorms", (25, 45), (0.30, 1.20), "high"),
        ("heavy rain", (15, 30), (0.35, 0.95), "medium"),
        ("light rain", (8, 20), (0.05, 0.30), "low"),
        ("wind gusts", (22, 42), (0.00, 0.15), "low"),
        ("overcast", (5, 18), (0.00, 0.08), "low"),
    )
    rows: list[dict[str, Any]] = []
    for region in REGIONS:
        condition, wind_range, precipitation_range, lightning_risk = rng.choice(profiles)
        rows.append(
            {
                "weather_id": f"WX-{REGION_CODES[region]}-01",
                "region": region,
                "condition": condition,
                "wind_mph": rng.randint(*wind_range),
                "precipitation_inches": round(rng.uniform(*precipitation_range), 2),
                "lightning_risk": lightning_risk,
                "updated_at": _iso_at(observation_date, 7),
            }
        )
    return rows


def _feeders_by_region(incidents: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        region: sorted({row["feeder"] for row in incidents if row["region"] == region})
        or [f"FDR-{REGION_CODES[region]}-01"]
        for region in REGIONS
    }


def _facility_link_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row["region"]),
        str(row["feeder"]),
        str(row["municipality"]),
    )


def _is_lse_facility(facility: dict[str, Any]) -> bool:
    return str(facility.get("facility_name", "")).endswith(LSE_FACILITY_SUFFIX)


def _configure_lse_boundary_incidents(
    incidents: list[dict[str, Any]],
) -> set[str]:
    if len(incidents) < len(LSE_CUSTOMER_BOUNDARIES):
        raise ValueError(
            "incident_count must be at least 3 to generate Level 3 LSE customer boundaries"
        )
    selected = incidents[-len(LSE_CUSTOMER_BOUNDARIES) :]
    anchor = selected[0]
    for incident, customers_out in zip(selected, LSE_CUSTOMER_BOUNDARIES):
        incident.update(
            region=anchor["region"],
            municipality=anchor["municipality"],
            feeder=anchor["feeder"],
            severity="low",
            customers_out=customers_out,
            critical_facility="false",
            hazard="none",
            required_skill="general",
            latitude=anchor["latitude"],
            longitude=anchor["longitude"],
        )
    return {str(incident["incident_id"]) for incident in selected}


def _lse_boundary_incidents(
    incidents: Iterable[dict[str, Any]],
    facilities: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    lse_keys = {
        _facility_link_key(facility)
        for facility in facilities
        if _is_lse_facility(facility)
    }
    return [
        incident
        for incident in incidents
        if _facility_link_key(incident) in lse_keys
        and str(incident.get("severity", "")).lower() == "low"
        and int(incident.get("customers_out", -1)) in LSE_CUSTOMER_BOUNDARIES
    ]


def _generate_critical_facilities(
    incidents: list[dict[str, Any]],
    municipalities: dict[str, list[dict[str, Any]]],
    rng: random.Random,
    facilities_per_region: int | None,
) -> list[dict[str, Any]]:
    incident_counts = Counter(row["region"] for row in incidents)
    boundary_candidates: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for incident in incidents:
        if (
            str(incident.get("severity", "")).lower() == "low"
            and int(incident.get("customers_out", -1)) in LSE_CUSTOMER_BOUNDARIES
        ):
            boundary_candidates.setdefault(_facility_link_key(incident), []).append(
                incident
            )
    boundary_key = next(
        (
            key
            for key, rows_for_key in boundary_candidates.items()
            if {int(row["customers_out"]) for row in rows_for_key}
            == set(LSE_CUSTOMER_BOUNDARIES)
        ),
        None,
    )
    if boundary_key is None:
        raise ValueError("Generated scenario is missing the configured Level 3 LSE boundaries")

    rows: list[dict[str, Any]] = []
    for region in REGIONS:
        facility_count = facilities_per_region or max(
            1,
            round(incident_counts[region] * DEFAULT_CRITICAL_FACILITY_RATE),
        )
        anchors_by_feeder: dict[str, dict[str, Any]] = {}
        for incident in incidents:
            if incident["region"] == region:
                anchors_by_feeder.setdefault(str(incident["feeder"]), incident)
        if boundary_key[0] == region:
            boundary_anchor = boundary_candidates[boundary_key][0]
            anchors_by_feeder[boundary_key[1]] = boundary_anchor
        else:
            boundary_anchor = None
        anchors = sorted(anchors_by_feeder.values(), key=lambda row: str(row["feeder"]))
        rng.shuffle(anchors)
        non_boundary_anchors = [
            anchor for anchor in anchors if _facility_link_key(anchor) != boundary_key
        ]
        fallback_localities = list(municipalities[region])
        rng.shuffle(fallback_localities)
        for index in range(1, facility_count + 1):
            is_guaranteed_lse = boundary_anchor is not None and index == facility_count
            if is_guaranteed_lse:
                anchor = boundary_anchor
                profile = FACILITY_CATALOG[-1]
            elif non_boundary_anchors:
                anchor = non_boundary_anchors[(index - 1) % len(non_boundary_anchors)]
                profile = FACILITY_CATALOG[(index - 1) % len(FACILITY_CATALOG)]
            elif boundary_anchor is not None:
                anchor = boundary_anchor
                profile = FACILITY_CATALOG[-1]
            elif anchors:
                anchor = anchors[(index - 1) % len(anchors)]
                profile = FACILITY_CATALOG[(index - 1) % len(FACILITY_CATALOG)]
            else:
                locality = fallback_localities[(index - 1) % len(fallback_localities)]
                anchor = {
                    "municipality": locality["municipality"],
                    "feeder": f"FDR-{REGION_CODES[region]}-01",
                }
                profile = FACILITY_CATALOG[(index - 1) % len(FACILITY_CATALOG)]
            rows.append(
                {
                    "facility_id": f"FAC-{REGION_CODES[region]}-{index:02d}",
                    "facility_name": f"{anchor['municipality']} {profile.name_suffix}",
                    "facility_type": profile.facility_type,
                    "region": region,
                    "municipality": anchor["municipality"],
                    "feeder": anchor["feeder"],
                    "priority_level": profile.priority_level,
                }
            )
    return rows


def _facility_keys(
    facilities: Iterable[dict[str, Any]],
) -> set[tuple[str, str, str]]:
    return {_facility_link_key(row) for row in facilities}


def _set_linked_criticality(
    incident: dict[str, Any],
    facility_keys: set[tuple[str, str, str]],
    rng: random.Random,
) -> None:
    eligible = _facility_link_key(incident) in facility_keys
    incident["critical_facility"] = (
        "true"
        if eligible
        and rng.random() < DEFAULT_CRITICAL_IMPACT_RATE
        else "false"
    )


def _apply_linked_criticality(
    incidents: Iterable[dict[str, Any]],
    facilities: Iterable[dict[str, Any]],
    rng: random.Random,
) -> None:
    incident_rows = list(incidents)
    facility_rows = list(facilities)
    keys = _facility_keys(facility_rows)
    for incident in incident_rows:
        _set_linked_criticality(incident, keys, rng)
    for incident in _lse_boundary_incidents(incident_rows, facility_rows):
        incident["critical_facility"] = "true"


def validate_critical_facility_linkage(
    incidents: Iterable[dict[str, Any]],
    facilities: Iterable[dict[str, Any]],
) -> None:
    facility_rows = list(facilities)
    facility_feeder_keys = {
        (str(row["region"]), str(row["feeder"])) for row in facility_rows
    }
    facility_keys = _facility_keys(facility_rows)
    for incident in incidents:
        value = str(incident["critical_facility"]).strip().lower()
        if value not in {"true", "false"}:
            raise ValueError(
                f"Incident {incident['incident_id']} has invalid critical_facility value "
                f"'{incident['critical_facility']}'"
            )
        key = (str(incident["region"]), str(incident["feeder"]))
        if value == "true" and key not in facility_feeder_keys:
            region_facilities = [
                f"{row['facility_id']}:{row['feeder']}"
                for row in facility_rows
                if str(row["region"]) == key[0]
            ]
            context = ", ".join(region_facilities) or "none"
            raise ValueError(
                f"Critical-facility incident {incident['incident_id']} in {key[0]} on {key[1]} "
                f"has no matching facility; available region facilities: {context}"
            )
        if value == "true" and _facility_link_key(incident) not in facility_keys:
            matched_localities = sorted(
                {
                    str(row.get("municipality", "unknown"))
                    for row in facility_rows
                    if str(row["region"]) == key[0]
                    and str(row["feeder"]) == key[1]
                }
            )
            raise ValueError(
                f"Critical-facility incident {incident['incident_id']} in municipality "
                f"{incident.get('municipality')} has no municipality-consistent facility on "
                f"{key[1]}; matched facility municipalities: "
                + ", ".join(matched_localities)
            )


def validate_lse_coverage(
    incidents: Iterable[dict[str, Any]],
    facilities: Iterable[dict[str, Any]],
) -> None:
    incident_rows = list(incidents)
    facility_rows = list(facilities)
    lse_facilities = [row for row in facility_rows if _is_lse_facility(row)]
    if not lse_facilities:
        raise ValueError("Generated scenario must include a Level 3 Private Health Device (LSE)")
    if any(
        str(row.get("facility_type")) != "healthcare"
        or str(row.get("priority_level")) != "medium"
        for row in lse_facilities
    ):
        raise ValueError("Generated LSE facilities must use healthcare Level 3 metadata")
    boundary_incidents = [
        row
        for row in _lse_boundary_incidents(incident_rows, lse_facilities)
        if str(row.get("critical_facility", "")).lower() == "true"
    ]
    observed = {int(row["customers_out"]) for row in boundary_incidents}
    missing = sorted(set(LSE_CUSTOMER_BOUNDARIES) - observed)
    if missing:
        raise ValueError(
            "Generated scenario is missing linked low-severity LSE customer boundaries: "
            + ", ".join(str(value) for value in missing)
        )


def _generate_topology(incidents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    feeders = _feeders_by_region(incidents)
    for region in REGIONS:
        for index, feeder in enumerate(feeders[region], start=1):
            code = REGION_CODES[region]
            substation_id = f"SUB-{code}-{index:03d}"
            switch_id = f"SW-{code}-{index:03d}"
            transformer_id = f"TR-{code}-{index:03d}"
            rows.extend(
                [
                    {
                        "asset_id": substation_id,
                        "asset_type": "substation",
                        "feeder": feeder,
                        "parent_asset_id": "",
                        "region": region,
                        "normal_status": "energized",
                    },
                    {
                        "asset_id": switch_id,
                        "asset_type": "switch",
                        "feeder": feeder,
                        "parent_asset_id": substation_id,
                        "region": region,
                        "normal_status": "closed",
                    },
                    {
                        "asset_id": transformer_id,
                        "asset_type": "transformer",
                        "feeder": feeder,
                        "parent_asset_id": switch_id,
                        "region": region,
                        "normal_status": "energized",
                    },
                ]
            )
    return rows


def _generate_historical_repairs(rng: random.Random) -> list[dict[str, Any]]:
    profiles = (
        ("downed wire", 118, "line", "Requires safety isolation before repair"),
        ("burning wire", 135, "line", "Requires isolation and damaged-conductor replacement"),
        ("tree on primary", 142, "vegetation", "Vegetation removal normally precedes line repair"),
        ("tree limb", 95, "vegetation", "Often resolved by a vegetation crew"),
        ("transformer fire", 210, "line", "May require equipment replacement"),
        ("feeder lockout", 165, "line", "Includes patrol isolation and restoration switching"),
        ("broken crossarm", 150, "line", "Requires pole-top hardware repair"),
        ("underground cable fault", 190, "underground", "Includes fault location and cable isolation"),
        ("damaged service drop", 75, "low_voltage", "Normally affects a single customer"),
        ("partial outage", 65, "general", "Troubleshooter diagnosis may precede repair"),
    )
    rows: list[dict[str, Any]] = []
    repair_number = 1
    for region in REGIONS:
        for incident_type, baseline_minutes, crew_type, notes in profiles:
            rows.append(
                {
                    "repair_id": f"REP-{repair_number:03d}",
                    "incident_type": incident_type,
                    "region": region,
                    "average_duration_minutes": max(30, baseline_minutes + rng.randint(-15, 20)),
                    "crew_type": crew_type,
                    "notes": notes,
                }
            )
            repair_number += 1
    return rows


def generate_scenario(
    *,
    scenario_id: str,
    start_date: date,
    end_date: date | None = None,
    incident_count: int = 2000,
    crew_count: int = 500,
    assignment_rate: float = 0.05,
    dual_tree_incidents: int = 5,
    seed: int = 20260810,
    start_day_location_rate: float = DEFAULT_START_DAY_LOCATION_RATE,
    critical_facilities_per_region: int | None = None,
    lookup_path: Path = DEFAULT_LOOKUP_PATH,
    allowed_municipalities: Iterable[str] | None = None,
    geography_coverage_target: int | None = None,
    customer_out_target: int | None = None,
    reference_root: Path = DEFAULT_REFERENCE_ROOT,
    geography_path: Path = DEFAULT_GEOGRAPHY_PATH,
    population_constrained: bool = True,
) -> GeneratedScenario:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", scenario_id):
        raise ValueError("scenario_id must use lowercase letters, numbers, hyphens, or underscores")
    if incident_count <= 0:
        raise ValueError("incident_count must be positive")
    if not 0 <= assignment_rate <= 1:
        raise ValueError("assignment_rate must be between 0 and 1")
    if not 0 <= start_day_location_rate <= 1:
        raise ValueError("start_day_location_rate must be between 0 and 1")
    if critical_facilities_per_region is not None and critical_facilities_per_region <= 0:
        raise ValueError("critical_facilities_per_region must be positive")
    end_date = end_date or start_date
    rng = random.Random(seed)
    municipalities = load_municipalities(lookup_path)
    if allowed_municipalities is not None:
        allowed_order = tuple(allowed_municipalities)
        if len(set(allowed_order)) != len(allowed_order):
            raise ValueError("Allowed municipalities must be unique")
        available = {
            str(row["municipality"]): row
            for rows in municipalities.values()
            for row in rows
        }
        missing = sorted(set(allowed_order) - set(available))
        if missing:
            raise ValueError(
                "Allowed municipalities are absent from the lookup: "
                + ", ".join(missing)
            )
        municipalities = {
            region: [
                available[name]
                for name in allowed_order
                if str(available[name]["region"]) == region
            ]
            for region in municipalities
        }
        empty_regions = [region for region, rows in municipalities.items() if not rows]
        if empty_regions:
            raise ValueError(
                "Allowed municipalities leave no entries for: "
                + ", ".join(empty_regions)
            )
    crews, crew_types = _generate_crews(crew_count, municipalities, rng, start_day_location_rate)
    incidents = [
        _base_incident(incident_date, sequence, municipalities, rng)
        for incident_date, sequence in _incident_dates(start_date, end_date, incident_count)
    ]
    lse_boundary_incident_ids = _configure_lse_boundary_incidents(incidents)

    assigned_incident_count = round(incident_count * assignment_rate)
    if assigned_incident_count > incident_count - len(lse_boundary_incident_ids):
        raise ValueError(
            "assignment_rate must leave at least three unassigned incidents for "
            "Level 3 LSE customer-boundary coverage"
        )
    if dual_tree_incidents > assigned_incident_count:
        raise ValueError("dual_tree_incidents cannot exceed assigned incident count")
    required_crews = assigned_incident_count + dual_tree_incidents
    if required_crews > crew_count:
        raise ValueError("Not enough crews for unique active assignments")

    selected_incidents = rng.sample(incidents, assigned_incident_count)
    selected_incident_ids = {
        str(incident["incident_id"]) for incident in selected_incidents
    }
    replacements = iter(
        incident
        for incident in incidents
        if str(incident["incident_id"]) not in selected_incident_ids
        and str(incident["incident_id"]) not in lse_boundary_incident_ids
    )
    selected_incidents = [
        next(replacements)
        if str(incident["incident_id"]) in lse_boundary_incident_ids
        else incident
        for incident in selected_incidents
    ]
    unused_crews = {row["crew_id"]: row for row in crews}
    pending_assignments: list[tuple[dict[str, Any], dict[str, Any], str]] = []

    paired_incidents = selected_incidents[:dual_tree_incidents]
    for incident in paired_incidents:
        pair_found = False
        for region in rng.sample(list(REGIONS), len(REGIONS)):
            repair = next((row for row in unused_crews.values() if row["home_region"] == region and crew_types[row["crew_id"]] in {"mua", "cntr"}), None)
            tree = next((row for row in unused_crews.values() if row["home_region"] == region and crew_types[row["crew_id"]] == "tree"), None)
            if repair and tree:
                _set_incident_location(incident, region, municipalities, rng)
                incident.update(status="assigned", severity="high", customers_out=rng.randint(40, 1800), critical_facility="false", hazard="tree on primary", required_skill="vegetation")
                pending_assignments.append((incident, repair, "Repair crew assigned for primary restoration after tree clearance"))
                pending_assignments.append((incident, tree, "Tree crew paired with repair crew to clear primary conductors"))
                repair["status"] = "assigned"
                tree["status"] = "assigned"
                unused_crews.pop(repair["crew_id"])
                unused_crews.pop(tree["crew_id"])
                pair_found = True
                break
        if not pair_found:
            raise ValueError("Unable to form requested repair plus TREE crew pair in a common region")

    remaining_crews = list(unused_crews.values())
    rng.shuffle(remaining_crews)
    for incident, crew in zip(selected_incidents[dual_tree_incidents:], remaining_crews):
        crew_type = crew_types[crew["crew_id"]]
        note = _configure_for_crew(incident, crew_type, crew["home_region"], municipalities, rng)
        crew["status"] = "assigned"
        pending_assignments.append((incident, crew, note))

    pending_assignments.sort(key=lambda item: (item[0]["incident_id"], item[1]["crew_id"]))
    assignment_sequences: Counter[str] = Counter()
    assignments: list[dict[str, Any]] = []
    for incident, crew, note in pending_assignments:
        date_text = incident["incident_id"].split("-")[1]
        assignment_sequences[date_text] += 1
        assignments.append(
            {
                "assignment_id": f"ASG-{date_text}-{assignment_sequences[date_text]:04d}",
                "incident_id": incident["incident_id"],
                "crew_id": crew["crew_id"],
                "status": "active",
                "assigned_at": _iso_at(datetime.strptime(date_text, "%Y%m%d").date(), 8, rng.randint(0, 59)),
                "notes": note,
            }
        )

    if customer_out_target is not None:
        apply_customer_out_target(incidents, customer_out_target)

    if population_constrained:
        allocate_population_capacity(
            incidents,
            load_capacity_geographies(
                reference_root=reference_root,
                geography_path=geography_path,
            ),
            coverage_target=geography_coverage_target,
        )

    weather = _generate_weather(start_date, rng)
    critical_facilities = _generate_critical_facilities(
        incidents,
        municipalities,
        rng,
        critical_facilities_per_region,
    )
    _apply_linked_criticality(
        incidents,
        critical_facilities,
        random.Random(seed + 2_000_003),
    )
    topology = _generate_topology(incidents)
    historical_repairs = _generate_historical_repairs(rng)
    result = GeneratedScenario(
        scenario_id=scenario_id,
        incidents=incidents,
        crews=crews,
        assignments=assignments,
        historical_repairs=historical_repairs,
        weather=weather,
        critical_facilities=critical_facilities,
        topology=topology,
        crew_types=crew_types,
    )
    validate_generated_scenario(result, assigned_incident_count, dual_tree_incidents)
    return result


def _apply_demo_location(
    incident: dict[str, Any],
    locality: dict[str, Any],
    *,
    feeder_number: int,
) -> None:
    region = locality["region"]
    incident.update(
        {
            "region": region,
            "municipality": locality["municipality"],
            "latitude": round(float(locality["latitude"]), 5),
            "longitude": round(float(locality["longitude"]), 5),
            "feeder": f"FDR-{REGION_CODES[region]}-{feeder_number:02d}",
        }
    )


def generate_copilot_demo_scenario(
    *,
    scenario_id: str = COPILOT_DEMO_SCENARIO_ID,
    start_date: date,
    seed: int = COPILOT_DEMO_SEED,
    geography_path: Path = DEFAULT_GEOGRAPHY_PATH,
) -> GeneratedScenario:
    """Build the bounded, deterministic POC-002 scenario without writing it."""

    scenario = generate_scenario(
        scenario_id=scenario_id,
        start_date=start_date,
        incident_count=COPILOT_DEMO_INCIDENT_COUNT,
        crew_count=COPILOT_DEMO_CREW_COUNT,
        assignment_rate=COPILOT_DEMO_ASSIGNMENT_RATE,
        dual_tree_incidents=COPILOT_DEMO_DUAL_TREE_INCIDENTS,
        population_constrained=False,
        seed=seed,
        start_day_location_rate=0,
        critical_facilities_per_region=(
            COPILOT_DEMO_CRITICAL_FACILITIES_PER_REGION
        ),
        lookup_path=geography_path,
        allowed_municipalities=COPILOT_DEMO_MUNICIPALITIES,
    )
    municipalities = load_municipalities(geography_path)
    registry = GeographyRegistry.from_csv(geography_path)
    travel_estimates = TravelEstimateService(registry)
    locality_by_name = {
        row["municipality"]: row
        for rows in municipalities.values()
        for row in rows
    }
    unassigned = [row for row in scenario.incidents if row["status"] == "unassigned"]
    profiles = (
        (
            "Arverne",
            {
                "severity": "critical",
                "customers_out": 5000,
                "critical_facility": "true",
                "hazard": "downed wire",
                "required_skill": "line",
                "age_minutes": 180,
            },
        ),
        (
            "Hicksville",
            {
                "severity": "high",
                "customers_out": 1250,
                "critical_facility": "false",
                "hazard": "transformer fire",
                "required_skill": "line",
                "age_minutes": 95,
            },
        ),
        (
            "Melville",
            {
                "severity": "medium",
                "customers_out": 420,
                "critical_facility": "false",
                "hazard": "tree limb",
                "required_skill": "vegetation",
                "age_minutes": 65,
            },
        ),
        (
            "Riverhead",
            {
                "severity": "low",
                "customers_out": 18,
                "critical_facility": "false",
                "hazard": "none",
                "required_skill": "general",
                "age_minutes": 20,
            },
        ),
    )
    for feeder_number, (locality_name, profile) in enumerate(profiles, start=1):
        incident = unassigned[feeder_number - 1]
        _apply_demo_location(
            incident,
            locality_by_name[locality_name],
            feeder_number=feeder_number,
        )
        incident.update(profile)

    east_meadow_incident = next(
        incident
        for incident in scenario.incidents
        if incident["incident_id"] == f"ESD-{start_date:%Y%m%d}-0011"
    )
    if east_meadow_incident["status"] != "unassigned":
        raise ValueError("Copilot demo East Meadow incident must remain unassigned")
    _apply_demo_location(
        east_meadow_incident,
        locality_by_name["East Meadow"],
        feeder_number=35,
    )
    east_meadow_incident.update(
        severity="critical",
        customers_out=2100,
        critical_facility="true",
        hazard="blocked access",
        required_skill="line",
        age_minutes=110,
    )

    anchor_incident = unassigned[0]
    available_general = next(
        crew
        for crew in scenario.crews
        if crew["status"] == "available" and crew["capability"] == "general"
    )
    available_line_crews = [
        crew
        for crew in scenario.crews
        if crew["status"] == "available" and crew["capability"] == "line"
    ]
    if len(available_line_crews) < 2:
        raise ValueError("Copilot demo requires at least two available line crews")
    available_general.update(
        current_location="Arverne",
        shift_remaining_hours=12,
        storm_ready="true",
    )
    for index, crew in enumerate(available_line_crews):
        crew.update(
            current_location="Cedarhurst" if index == 0 else "Hicksville",
            shift_remaining_hours=12,
            storm_ready="true" if index == 0 else "false",
        )

    for crew in scenario.crews:
        estimate = travel_estimates.estimate(
            origin_name=crew["current_location"],
            destination_name=anchor_incident["municipality"],
            destination_latitude=float(anchor_incident["latitude"]),
            destination_longitude=float(anchor_incident["longitude"]),
        )
        if estimate is None:
            raise ValueError(
                f"Copilot demo crew location is not registered: {crew['current_location']}"
            )
        crew["travel_minutes_to_selected_incident"] = (
            estimate.estimated_travel_minutes
        )

    rng = random.Random(seed + 1)
    scenario.critical_facilities = _generate_critical_facilities(
        scenario.incidents,
        municipalities,
        rng,
        COPILOT_DEMO_CRITICAL_FACILITIES_PER_REGION,
    )
    scenario.critical_facilities[0].update(
        facility_name="Arverne Emergency Services Center",
        facility_type="emergency_services",
        region=anchor_incident["region"],
        municipality=anchor_incident["municipality"],
        feeder=anchor_incident["feeder"],
        priority_level="critical",
    )
    east_meadow_facility = next(
        facility
        for facility in scenario.critical_facilities
        if facility["facility_id"] == "FAC-CN-01"
    )
    east_meadow_facility.update(
        facility_name="East Meadow Fire Department",
        facility_type="emergency_services",
        region=east_meadow_incident["region"],
        municipality=east_meadow_incident["municipality"],
        feeder=east_meadow_incident["feeder"],
        priority_level="critical",
    )
    _apply_linked_criticality(
        scenario.incidents,
        scenario.critical_facilities,
        random.Random(seed + 2_000_003),
    )
    lse_boundary_incident_ids = {
        str(incident["incident_id"])
        for incident in _lse_boundary_incidents(
            scenario.incidents,
            scenario.critical_facilities,
        )
    }
    for incident in scenario.incidents:
        incident["critical_facility"] = (
            "true"
            if str(incident["incident_id"]) in lse_boundary_incident_ids
            else "false"
        )
    anchor_incident["critical_facility"] = "true"
    east_meadow_incident["critical_facility"] = "true"
    scenario.topology = _generate_topology(scenario.incidents)
    validate_generated_scenario(
        scenario,
        round(COPILOT_DEMO_INCIDENT_COUNT * COPILOT_DEMO_ASSIGNMENT_RATE),
        COPILOT_DEMO_DUAL_TREE_INCIDENTS,
    )
    validate_copilot_demo_scenario(scenario, registry)
    return scenario


def validate_copilot_demo_scenario(
    scenario: GeneratedScenario,
    registry: GeographyRegistry | None = None,
) -> None:
    registry = registry or GeographyRegistry.from_csv()
    incident_locations = [
        registry.require(str(incident["municipality"]))
        for incident in scenario.incidents
    ]
    for crew in scenario.crews:
        registry.require(str(crew["current_location"]))

    counties = {record.county for record in incident_locations}
    if counties != {"Nassau", "Suffolk", "Queens"}:
        raise ValueError("Copilot demo incidents must cover Nassau, Suffolk, and Queens")
    if not any(record.township == "Rockaway Peninsula" for record in incident_locations):
        raise ValueError("Copilot demo must include the Rockaway Peninsula")
    if not any(incident["hazard"] == "none" for incident in scenario.incidents):
        raise ValueError("Copilot demo must include a no-hazard incident")
    if len({incident["hazard"] for incident in scenario.incidents}) < 4:
        raise ValueError("Copilot demo must include multiple hazard types")
    if not any(incident["critical_facility"] == "true" for incident in scenario.incidents):
        raise ValueError("Copilot demo must include a critical-facility incident")
    east_meadow = next(
        incident
        for incident in scenario.incidents
        if incident["incident_id"].endswith("-0011")
    )
    if not (
        east_meadow["municipality"] == "East Meadow"
        and east_meadow["feeder"] == "FDR-CN-35"
        and east_meadow["critical_facility"] == "true"
    ):
        raise ValueError("Copilot demo must include the linked East Meadow incident")
    if not any(
        facility["facility_name"] == "East Meadow Fire Department"
        and facility["facility_type"] == "emergency_services"
        and facility["region"] == east_meadow["region"]
        and facility["feeder"] == east_meadow["feeder"]
        and facility["priority_level"] == "critical"
        for facility in scenario.critical_facilities
    ):
        raise ValueError("Copilot demo must include the approved East Meadow facility")
    statuses = {crew["status"] for crew in scenario.crews}
    if not {"available", "assigned"}.issubset(statuses):
        raise ValueError("Copilot demo must include available and assigned crews")

    anchor = next(
        incident
        for incident in scenario.incidents
        if incident["municipality"] == "Arverne"
        and incident["required_skill"] == "line"
    )
    travel_estimates = TravelEstimateService(registry)
    closer_ineligible = min(
        (
            travel_estimates.estimate(
                origin_name=crew["current_location"],
                destination_name=anchor["municipality"],
                destination_latitude=float(anchor["latitude"]),
                destination_longitude=float(anchor["longitude"]),
            )
            for crew in scenario.crews
            if crew["status"] == "available" and crew["capability"] != "line"
        ),
        key=lambda estimate: estimate.estimated_travel_minutes if estimate else 9999,
    )
    feasible_line = min(
        (
            travel_estimates.estimate(
                origin_name=crew["current_location"],
                destination_name=anchor["municipality"],
                destination_latitude=float(anchor["latitude"]),
                destination_longitude=float(anchor["longitude"]),
            )
            for crew in scenario.crews
            if crew["status"] == "available" and crew["capability"] == "line"
        ),
        key=lambda estimate: estimate.estimated_travel_minutes if estimate else 9999,
    )
    if closer_ineligible is None or feasible_line is None:
        raise ValueError("Copilot demo crew travel contrast could not be calculated")
    if closer_ineligible.estimated_travel_minutes >= feasible_line.estimated_travel_minutes:
        raise ValueError(
            "Copilot demo must include a closer capability-ineligible crew"
        )


def validate_generated_scenario(
    scenario: GeneratedScenario,
    expected_assigned_incidents: int | None = None,
    expected_dual_tree_incidents: int | None = None,
) -> None:
    validate_geographic_reference_coverage(scenario.incidents)
    if any(row.get("geography_reference_id") for row in scenario.incidents):
        validate_population_capacity(scenario.incidents)
    incident_by_id = {row["incident_id"]: row for row in scenario.incidents}
    crew_by_id = {row["crew_id"]: row for row in scenario.crews}
    if len(incident_by_id) != len(scenario.incidents):
        raise ValueError("Generated incident IDs are not unique")
    if len(crew_by_id) != len(scenario.crews):
        raise ValueError("Generated crew IDs are not unique")
    if len({row["assignment_id"] for row in scenario.assignments}) != len(scenario.assignments):
        raise ValueError("Generated assignment IDs are not unique")
    assigned_crews: Counter[str] = Counter()
    assignments_by_incident: Counter[str] = Counter()
    for assignment in scenario.assignments:
        incident = incident_by_id.get(assignment["incident_id"])
        crew = crew_by_id.get(assignment["crew_id"])
        if not incident or not crew:
            raise ValueError("Generated assignment contains an unknown foreign key")
        assigned_crews[crew["crew_id"]] += 1
        assignments_by_incident[incident["incident_id"]] += 1
        if crew["status"] != "assigned" or incident["status"] != "assigned":
            raise ValueError("Active assignments must synchronize incident and crew status")
        suffix_region = _suffix_region(crew["crew_id"])
        if suffix_region and (crew["home_region"] != suffix_region or incident["region"] != suffix_region):
            raise ValueError(f"Crew {crew['crew_id']} is not aligned to its encoded region")
        crew_type = scenario.crew_types[crew["crew_id"]]
        if crew_type == "low_voltage" and (incident["customers_out"] != 1 or incident["required_skill"] != "low_voltage"):
            raise ValueError("Internal low-voltage crews must be assigned to one-customer low-voltage incidents")
        if crew_type == "line" and (incident["customers_out"] < 40 or incident["severity"] not in {"high", "critical"} or incident["required_skill"] != "line"):
            raise ValueError("Internal line crews must be assigned to qualifying high-voltage incidents")
    if any(count > 1 for count in assigned_crews.values()):
        raise ValueError("A crew has multiple active seed assignments")
    if expected_assigned_incidents is not None and len(assignments_by_incident) != expected_assigned_incidents:
        raise ValueError("Assigned incident count does not match the configured assignment rate")
    if expected_dual_tree_incidents is not None and sum(count == 2 for count in assignments_by_incident.values()) != expected_dual_tree_incidents:
        raise ValueError("Dual-crew incident count does not match configuration")
    if {row["region"] for row in scenario.weather} != set(REGIONS):
        raise ValueError("Weather observations must cover all configured regions")
    if {row["region"] for row in scenario.critical_facilities} != set(REGIONS):
        raise ValueError("Critical facilities must cover all configured regions")
    if len({row["facility_id"] for row in scenario.critical_facilities}) != len(
        scenario.critical_facilities
    ):
        raise ValueError("Generated critical-facility IDs are not unique")
    validate_critical_facility_linkage(
        scenario.incidents,
        scenario.critical_facilities,
    )
    validate_lse_coverage(
        scenario.incidents,
        scenario.critical_facilities,
    )
    if {row["region"] for row in scenario.historical_repairs} != set(REGIONS):
        raise ValueError("Historical repairs must cover all configured regions")
    topology_by_id = {row["asset_id"]: row for row in scenario.topology}
    if len(topology_by_id) != len(scenario.topology):
        raise ValueError("Generated topology asset IDs are not unique")
    topology_feeders = {(row["region"], row["feeder"]) for row in scenario.topology}
    required_feeders = {
        (row["region"], row["feeder"])
        for row in [*scenario.incidents, *scenario.critical_facilities]
    }
    if not required_feeders.issubset(topology_feeders):
        raise ValueError("Topology does not cover every incident and critical-facility feeder")
    for asset in scenario.topology:
        parent_id = asset["parent_asset_id"]
        if parent_id and parent_id not in topology_by_id:
            raise ValueError(f"Topology asset {asset['asset_id']} has an unknown parent")


def validate_geographic_reference_coverage(
    incidents: Iterable[dict[str, Any]],
    registry: GeographyRegistry | None = None,
    *,
    reference_root: Path = DEFAULT_REFERENCE_ROOT,
) -> None:
    registry = registry or GeographyRegistry.from_csv()
    incident_rows = list(incidents)
    has_reference_ids = any(
        row.get("geography_reference_id") for row in incident_rows
    )
    capacity_by_id = (
        {
            row.reference_id: row
            for row in load_capacity_geographies(reference_root=reference_root)
        }
        if has_reference_ids
        else {}
    )
    unresolved: set[str] = set()
    unknown_reference_ids: set[str] = set()
    municipality_mismatches: set[tuple[str, str]] = set()
    region_mismatches: set[tuple[str, str, str]] = set()
    for incident in incident_rows:
        municipality = str(incident["municipality"])
        reference_id = str(incident.get("geography_reference_id") or "").strip()
        if reference_id:
            location = capacity_by_id.get(reference_id)
            if location is None:
                unknown_reference_ids.add(reference_id)
                continue
            if municipality != location.municipality:
                municipality_mismatches.add(
                    (municipality, location.municipality)
                )
            incident_region = str(incident["region"])
            if location.region != incident_region:
                region_mismatches.add(
                    (municipality, incident_region, location.region)
                )
            continue
        location = registry.resolve(municipality)
        if location is None:
            unresolved.add(municipality)
            continue
        incident_region = str(incident["region"])
        if location.region != incident_region:
            region_mismatches.add(
                (municipality, incident_region, location.region)
            )
    if unresolved:
        raise ValueError(
            "Generated incidents lack approved geography mappings: "
            + ", ".join(sorted(unresolved))
        )
    if unknown_reference_ids:
        raise ValueError(
            "Generated incidents use unapproved geography reference IDs: "
            + ", ".join(sorted(unknown_reference_ids))
        )
    if municipality_mismatches:
        details = ", ".join(
            f"{actual} (expected {expected})"
            for actual, expected in sorted(municipality_mismatches)
        )
        raise ValueError(
            "Generated incident municipality does not match its approved geography "
            "reference ID: " + details
        )
    if region_mismatches:
        details = ", ".join(
            f"{municipality} ({incident_region} != {mapped_region})"
            for municipality, incident_region, mapped_region in sorted(region_mismatches)
        )
        raise ValueError(
            "Generated incident regions do not match approved geography mappings: "
            + details
        )


def validate_population_capacity(
    incidents: Iterable[dict[str, Any]],
    *,
    reference_root: Path = DEFAULT_REFERENCE_ROOT,
) -> None:
    geographies = load_capacity_geographies(reference_root=reference_root)
    capacity_by_id = {
        row.reference_id: row.customers_served for row in geographies
    }
    totals: Counter[str] = Counter()
    missing: list[str] = []
    for incident in incidents:
        if str(incident.get("status", "")).casefold() in {
            "cancelled",
            "closed",
            "resolved",
            "restored",
        }:
            continue
        reference_id = str(incident.get("geography_reference_id") or "").strip()
        if not reference_id:
            missing.append(str(incident.get("incident_id", "unknown")))
            continue
        totals[reference_id] += int(incident["customers_out"])
    if missing:
        raise ValueError(
            "Population-constrained incidents are missing geography_reference_id: "
            + ", ".join(missing[:10])
        )
    exceeded = [
        (reference_id, total, capacity_by_id.get(reference_id))
        for reference_id, total in totals.items()
        if capacity_by_id.get(reference_id) is None
        or total > int(capacity_by_id[reference_id])
    ]
    if exceeded:
        details = ", ".join(
            f"{reference_id} ({total:,} > {capacity if capacity is not None else 'unknown'})"
            for reference_id, total, capacity in exceeded[:10]
        )
        raise ValueError(
            "Active customers_out exceeds approved geography capacity: " + details
        )


def _write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_scenario(scenario: GeneratedScenario, output_root: Path = DEFAULT_OUTPUT_ROOT) -> Path:
    if scenario.scenario_id == "base":
        raise ValueError("The protected base scenario cannot be generated or replaced")
    validate_geographic_reference_coverage(scenario.incidents)
    if any(row.get("geography_reference_id") for row in scenario.incidents):
        validate_population_capacity(scenario.incidents)
    output_root = output_root.resolve()
    target = output_root / scenario.scenario_id
    if target.exists():
        raise FileExistsError(f"Output scenario already exists: {target}")
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{scenario.scenario_id}-", dir=output_root) as temporary:
        temporary_path = Path(temporary)
        _write_csv(temporary_path / "PendingIncidents.csv", INCIDENT_HEADERS, scenario.incidents)
        _write_csv(temporary_path / "Crews.csv", CREW_HEADERS, scenario.crews)
        _write_csv(temporary_path / "Assignments.csv", ASSIGNMENT_HEADERS, scenario.assignments)
        _write_csv(temporary_path / "HistoricalRepairs.csv", HISTORICAL_REPAIR_HEADERS, scenario.historical_repairs)
        _write_csv(temporary_path / "Weather.csv", WEATHER_HEADERS, scenario.weather)
        _write_csv(temporary_path / "CriticalFacilities.csv", CRITICAL_FACILITY_HEADERS, scenario.critical_facilities)
        _write_csv(temporary_path / "Topology.csv", TOPOLOGY_HEADERS, scenario.topology)
        manifest = {
            "schema_version": "1.0",
            "scenario_id": scenario.scenario_id,
            "name": f"Generated Scenario {scenario.scenario_id}",
            "description": "Synthetic Long Island outage dispatch scenario generated from approved seed rules.",
            "event_type": "storm",
            "freshness": {
                "updated_at": datetime.now(LOCAL_TIMEZONE).isoformat(),
                "source": "scenario_generation",
                "provenance": "AI Dispatch Advisor synthetic scenario generator",
            },
            "expected_conditions": [
                "Synthetic Long Island incidents",
                "Region-coded crews",
                "Human dispatcher approval required",
            ],
            "files": {
                "incidents": "PendingIncidents.csv",
                "crews": "Crews.csv",
                "assignments": "Assignments.csv",
                "historical_repairs": "HistoricalRepairs.csv",
                "weather": "Weather.csv",
                "critical_facilities": "CriticalFacilities.csv",
                "topology": "Topology.csv",
            },
        }
        (temporary_path / "scenario.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        temporary_path.rename(target)
    return target
