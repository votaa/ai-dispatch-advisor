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


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "data" / "scenario-previews"
DEFAULT_LOOKUP_PATH = REPO_ROOT / "data" / "generator-lookups" / "LongIslandMunicipalities.csv"
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
COPILOT_DEMO_SCENARIO_ID = "long-island-copilot-demo"
COPILOT_DEMO_INCIDENT_COUNT = 24
COPILOT_DEMO_CREW_COUNT = 32
COPILOT_DEMO_ASSIGNMENT_RATE = 0.25
COPILOT_DEMO_DUAL_TREE_INCIDENTS = 1
COPILOT_DEMO_CRITICAL_FACILITIES_PER_REGION = 2
COPILOT_DEMO_SEED = 20260821

INCIDENT_HEADERS = [
    "incident_id",
    "region",
    "municipality",
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
    FacilityProfile("Private Health Device (LSE)", "healthcare", 3, "medium"),
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


def _generate_critical_facilities(
    incidents: list[dict[str, Any]],
    municipalities: dict[str, list[dict[str, Any]]],
    rng: random.Random,
    facilities_per_region: int | None,
) -> list[dict[str, Any]]:
    feeders = _feeders_by_region(incidents)
    incident_counts = Counter(row["region"] for row in incidents)
    rows: list[dict[str, Any]] = []
    for region in REGIONS:
        facility_count = facilities_per_region or max(
            1,
            round(incident_counts[region] * DEFAULT_CRITICAL_FACILITY_RATE),
        )
        localities = list(municipalities[region])
        rng.shuffle(localities)
        for index in range(1, facility_count + 1):
            profile = FACILITY_CATALOG[(index - 1) % len(FACILITY_CATALOG)]
            locality = localities[(index - 1) % len(localities)]
            region_feeders = feeders[region]
            feeder = region_feeders[(index - 1) % len(region_feeders)]
            rows.append(
                {
                    "facility_id": f"FAC-{REGION_CODES[region]}-{index:02d}",
                    "facility_name": f"{locality['municipality']} {profile.name_suffix}",
                    "facility_type": profile.facility_type,
                    "region": region,
                    "municipality": locality["municipality"],
                    "feeder": feeder,
                    "priority_level": profile.priority_level,
                }
            )
    return rows


def _facility_keys(facilities: Iterable[dict[str, Any]]) -> set[tuple[str, str]]:
    return {(str(row["region"]), str(row["feeder"])) for row in facilities}


def _set_linked_criticality(
    incident: dict[str, Any],
    facility_keys: set[tuple[str, str]],
    rng: random.Random,
) -> None:
    eligible = (str(incident["region"]), str(incident["feeder"])) in facility_keys
    incident["critical_facility"] = (
        "true"
        if eligible
        and incident["severity"] in {"high", "critical"}
        and rng.random() < DEFAULT_CRITICAL_IMPACT_RATE
        else "false"
    )


def _apply_linked_criticality(
    incidents: Iterable[dict[str, Any]],
    facilities: Iterable[dict[str, Any]],
    rng: random.Random,
) -> None:
    keys = _facility_keys(facilities)
    for incident in incidents:
        _set_linked_criticality(incident, keys, rng)


def validate_critical_facility_linkage(
    incidents: Iterable[dict[str, Any]],
    facilities: Iterable[dict[str, Any]],
) -> None:
    facility_rows = list(facilities)
    facility_keys = _facility_keys(facility_rows)
    for incident in incidents:
        value = str(incident["critical_facility"]).strip().lower()
        if value not in {"true", "false"}:
            raise ValueError(
                f"Incident {incident['incident_id']} has invalid critical_facility value "
                f"'{incident['critical_facility']}'"
            )
        key = (str(incident["region"]), str(incident["feeder"]))
        if value == "true" and key not in facility_keys:
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
    crews, crew_types = _generate_crews(crew_count, municipalities, rng, start_day_location_rate)
    incidents = [
        _base_incident(incident_date, sequence, municipalities, rng)
        for incident_date, sequence in _incident_dates(start_date, end_date, incident_count)
    ]

    assigned_incident_count = round(incident_count * assignment_rate)
    if dual_tree_incidents > assigned_incident_count:
        raise ValueError("dual_tree_incidents cannot exceed assigned incident count")
    required_crews = assigned_incident_count + dual_tree_incidents
    if required_crews > crew_count:
        raise ValueError("Not enough crews for unique active assignments")

    selected_incidents = rng.sample(incidents, assigned_incident_count)
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
        seed=seed,
        start_day_location_rate=0,
        critical_facilities_per_region=(
            COPILOT_DEMO_CRITICAL_FACILITIES_PER_REGION
        ),
        lookup_path=geography_path,
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
    for incident in scenario.incidents:
        incident["critical_facility"] = "false"
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


def _write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_scenario(scenario: GeneratedScenario, output_root: Path = DEFAULT_OUTPUT_ROOT) -> Path:
    if scenario.scenario_id == "base":
        raise ValueError("The protected base scenario cannot be generated or replaced")
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
