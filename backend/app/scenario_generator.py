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
        if reader.fieldnames != expected:
            raise ValueError(f"Municipality lookup headers must be {expected}")
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
    return {
        "incident_id": f"ESD-{incident_date:%Y%m%d}-{sequence:04d}",
        "region": region,
        "municipality": locality["municipality"],
        "feeder": f"FDR-{REGION_CODES[region]}-{rng.randint(1, 40):02d}",
        "severity": severity,
        "status": "unassigned",
        "customers_out": rng.randint(minimum, maximum),
        "critical_facility": "true" if severity in {"high", "critical"} and rng.random() < 0.08 else "false",
        "hazard": hazard,
        "required_skill": required_skill,
        "age_minutes": rng.randint(5, 180),
        "latitude": round(locality["latitude"] + rng.uniform(-0.012, 0.012), 5),
        "longitude": round(locality["longitude"] + rng.uniform(-0.012, 0.012), 5),
        "etr": _iso_at(incident_date, rng.randint(10, 22), rng.choice((0, 15, 30, 45))),
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
    facility_profiles = (
        ("Regional Medical Center", "hospital", "critical"),
        ("Water Treatment Facility", "water", "critical"),
        ("Emergency Services Center", "emergency_services", "critical"),
        ("Senior Care Center", "healthcare", "high"),
        ("Public Safety Communications Center", "communications", "critical"),
        ("Fire District Headquarters", "emergency_services", "high"),
        ("Police Precinct", "emergency_services", "high"),
        ("Emergency Shelter", "shelter", "high"),
        ("Wastewater Pump Station", "water", "high"),
        ("Transit Operations Center", "transportation", "high"),
    )
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
            name_suffix, facility_type, priority = facility_profiles[(index - 1) % len(facility_profiles)]
            locality = localities[(index - 1) % len(localities)]
            region_feeders = feeders[region]
            feeder = region_feeders[(index - 1) % len(region_feeders)]
            rows.append(
                {
                    "facility_id": f"FAC-{REGION_CODES[region]}-{index:02d}",
                    "facility_name": f"{locality['municipality']} {name_suffix}",
                    "facility_type": facility_type,
                    "region": region,
                    "municipality": locality["municipality"],
                    "feeder": feeder,
                    "priority_level": priority,
                }
            )
    return rows


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
