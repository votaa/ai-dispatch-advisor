from __future__ import annotations

import copy
import json
import math
import random
import re
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from .scenario_generator import (
    DEFAULT_LOOKUP_PATH,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_START_DAY_LOCATION_RATE,
    DEFAULT_ETR_MIX,
    LOCAL_TIMEZONE,
    REGIONS,
    GeneratedScenario,
    _apply_capacity_location,
    _base_incident,
    _facility_keys,
    _lse_boundary_incidents,
    _mix_labels,
    _set_linked_criticality,
    _suffix_region,
    generate_scenario,
    load_capacity_geographies,
    load_municipalities,
    parse_etr_mix,
    validate_critical_facility_linkage,
    validate_lse_coverage,
    validate_population_capacity,
    write_scenario,
)
from .scenario_service import ScenarioService


RECOVERY_PROFILES = {"fast": 0.92, "balanced": 0.75, "severe": 0.55}
ARRIVAL_PROFILES = {"low": 0.08, "moderate": 0.18, "persistent": 0.35}
INCIDENT_PHASES = ("assigned", "en_route", "onsite", "energized")


@dataclass(frozen=True)
class TimelineConfig:
    scenario_id: str
    start_date: date
    end_date: date | None = None
    start_time: time = time(8, 0)
    snapshots: int = 5
    hours_apart: int = 12
    incident_count: int = 2000
    crew_count: int = 500
    assignment_rate: float = 0.05
    dual_tree_incidents: int = 5
    critical_facilities_per_region: int | None = None
    seed: int = 20260810
    start_day_location_rate: float = DEFAULT_START_DAY_LOCATION_RATE
    recovery_profile: str = "fast"
    recovery_target: float | None = None
    arrival_profile: str = "moderate"
    new_incident_share: float | None = None
    arrival_decay: float = 0.60
    repair_duration_variation: float = 0.25
    lookup_path: Path = DEFAULT_LOOKUP_PATH
    etr_mix: str | None = None
    assessing_conversion: str | None = None
    assessing_conversion_overrides: str | None = None

    @property
    def resolved_recovery_target(self) -> float:
        if self.recovery_profile == "custom":
            assert self.recovery_target is not None
            return self.recovery_target
        return RECOVERY_PROFILES[self.recovery_profile]

    @property
    def resolved_new_incident_share(self) -> float:
        if self.arrival_profile == "custom":
            assert self.new_incident_share is not None
            return self.new_incident_share
        return ARRIVAL_PROFILES[self.arrival_profile]

    @property
    def first_timestamp(self) -> datetime:
        return datetime.combine(self.start_date, self.start_time, LOCAL_TIMEZONE)

    @property
    def effective_arrival_decay(self) -> float:
        return self.arrival_decay ** (self.hours_apart / 12)


@dataclass
class TimelineSnapshot:
    index: int
    timestamp: datetime
    scenario: GeneratedScenario
    new_incident_ids: tuple[str, ...] = ()
    cleared_incident_ids: tuple[str, ...] = ()
    converted_incident_ids: tuple[str, ...] = ()
    conversion_eligible_count: int = 0

    def summary(self) -> dict[str, Any]:
        crew_counts = Counter(row["status"] for row in self.scenario.crews)
        result = {
            "snapshot": self.index,
            "scenario_id": self.scenario.scenario_id,
            "timestamp": self.timestamp.isoformat(),
            "pending": len(self.scenario.incidents),
            "new": len(self.new_incident_ids),
            "cleared": len(self.cleared_incident_ids),
            "converted": len(self.converted_incident_ids),
            "assigned": sum(row["status"] != "unassigned" for row in self.scenario.incidents),
            "available": crew_counts["available"],
            "off_shift": crew_counts["off_shift"],
        }
        if self.scenario.temporal is not None:
            cutoff = self.timestamp.astimezone(timezone.utc).replace(second=0, microsecond=0)
            categories: Counter[str] = Counter()
            examples: dict[str, list[str]] = defaultdict(list)
            for incident in self.scenario.incidents:
                etr_text = incident.get("etr")
                if not etr_text:
                    category = "unavailable"
                else:
                    etr = datetime.fromisoformat(str(etr_text)).astimezone(timezone.utc)
                    etr = etr.replace(second=0, microsecond=0)
                    minutes = int((etr - cutoff).total_seconds() // 60)
                    category = (
                        "expired" if minutes < -10 else
                        "due_now" if minutes <= 0 else
                        "due_soon" if minutes <= 60 else
                        "valid_future"
                    )
                categories[category] += 1
                if len(examples[category]) < 2:
                    examples[category].append(str(incident["incident_id"]))
            cohort_ids = set(self.new_incident_ids) if self.index > 1 else {
                row["incident_id"] for row in self.scenario.incidents
            }
            cohort_created = [
                datetime.fromisoformat(str(row["created_at"])) for row in self.scenario.incidents
                if row["incident_id"] in cohort_ids
            ]
            result["temporal"] = {
                "as_of_at": self.scenario.temporal["as_of_at"],
                "arrival_created_at_range": {
                    "first": min(cohort_created).isoformat() if cohort_created else None,
                    "last": max(cohort_created).isoformat() if cohort_created else None,
                },
                "requested_etr_mix": self.scenario.temporal["etr_distribution"],
                "realized_arrival_etr_mix": self.scenario.etr_mix_counts,
                "conversion_eligible": self.conversion_eligible_count,
                "assessing_conditions": categories["unavailable"],
                "future_etr_count": categories["due_soon"] + categories["valid_future"],
                "etr_categories": {name: categories[name] for name in (
                    "expired", "due_now", "due_soon", "valid_future", "unavailable"
                )},
                "example_incident_ids": dict(examples),
            }
        return result


@dataclass
class GeneratedTimeline:
    config: TimelineConfig
    snapshots: list[TimelineSnapshot]

    def summary(self, evaluation_at: datetime | None = None) -> dict[str, Any]:
        rows = [snapshot.summary() for snapshot in self.snapshots]
        if evaluation_at is not None:
            if evaluation_at.tzinfo is None or evaluation_at.utcoffset() is None:
                raise ValueError("Timeline preview evaluation time must include an offset")
            evaluated = evaluation_at.astimezone(timezone.utc)
            latest_eligible = max((
                index for index, snapshot in enumerate(self.snapshots)
                if snapshot.timestamp.astimezone(timezone.utc) <= evaluated
            ), default=None)
            for index, row in enumerate(rows):
                row["clock_state"] = (
                    "future" if latest_eligible is None or index > latest_eligible else
                    "latest_eligible" if index == latest_eligible else "stale"
                )
        warnings: list[dict[str, Any]] = []
        if self.config.assessing_conversion:
            baseline = parse_assessing_conversion(self.config.assessing_conversion)
            overrides = parse_assessing_conversion_overrides(
                self.config.assessing_conversion_overrides, self.config.snapshots
            )
            for index in range(1, len(self.snapshots) - 1):
                snapshot = self.snapshots[index]
                if not snapshot.converted_incident_ids:
                    continue
                rule = overrides.get(index + 1, baseline)
                interval = int((
                    self.snapshots[index + 1].timestamp.astimezone(timezone.utc)
                    - snapshot.timestamp.astimezone(timezone.utc)
                ).total_seconds() // 3600)
                if rule.hours <= interval:
                    warnings.append({
                        "step": index + 1,
                        "horizon_hours": rule.hours,
                        "next_interval_hours": interval,
                        "state_at_next_cutoff": "due_now" if rule.hours == interval else "expired",
                    })
        result = {
            "configuration": {
                "scenario_id": self.config.scenario_id,
                "snapshots": self.config.snapshots,
                "hours_apart": self.config.hours_apart,
                "start_timestamp": self.config.first_timestamp.isoformat(),
                "recovery_profile": self.config.recovery_profile,
                "recovery_target": self.config.resolved_recovery_target,
                "arrival_profile": self.config.arrival_profile,
                "new_incident_share": self.config.resolved_new_incident_share,
                "effective_arrival_decay": self.config.effective_arrival_decay,
                "repair_duration_variation": self.config.repair_duration_variation,
                "seed": self.config.seed,
                "etr_mix": self.config.etr_mix,
                "assessing_conversion": self.config.assessing_conversion,
                "assessing_conversion_overrides": self.config.assessing_conversion_overrides,
            },
            "snapshots": rows,
            "conversion_horizon_warnings": warnings,
        }
        if evaluation_at is not None:
            result["evaluation_at"] = evaluation_at.isoformat()
        return result


@dataclass(frozen=True)
class AssessingConversionRule:
    percent: Decimal
    hours: int

    def as_manifest(self) -> dict[str, int | float]:
        return {"percent": float(self.percent), "hours": self.hours}


def parse_assessing_conversion(value: str) -> AssessingConversionRule:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)%@([1-9]\d*)h\s*", value, re.I)
    if match is None:
        raise ValueError("Conversion rule must look like 10%@24h")
    percent = Decimal(match.group(1))
    if percent > 100:
        raise ValueError("Conversion percentage must be between 0 and 100")
    return AssessingConversionRule(percent, int(match.group(2)))


def parse_assessing_conversion_overrides(
    value: str | None, snapshots: int
) -> dict[int, AssessingConversionRule]:
    if not value:
        return {}
    overrides: dict[int, AssessingConversionRule] = {}
    for piece in value.split(","):
        match = re.fullmatch(r"\s*(\d+)\s*=\s*(.+)\s*", piece)
        if match is None:
            raise ValueError("Conversion overrides must look like 2=10%@12h,4=20%@24h")
        step = int(match.group(1))
        if step < 2 or step > snapshots or step in overrides:
            raise ValueError("Conversion override steps must be unique and within 2..snapshots")
        overrides[step] = parse_assessing_conversion(match.group(2))
    return overrides


def _validate_config(config: TimelineConfig) -> None:
    if config.scenario_id == "base":
        raise ValueError("The protected base scenario cannot be generated or replaced")
    if config.end_date is not None and config.end_date < config.start_date:
        raise ValueError("end_date must be on or after start_date")
    if config.etr_mix is not None:
        parse_etr_mix(config.etr_mix)
    if config.assessing_conversion_overrides and not config.assessing_conversion:
        raise ValueError("Conversion overrides require a baseline conversion rule")
    if config.assessing_conversion:
        if config.snapshots == 1:
            raise ValueError("A one-snapshot timeline cannot convert Assessing Conditions")
        parse_assessing_conversion(config.assessing_conversion)
    parse_assessing_conversion_overrides(config.assessing_conversion_overrides, config.snapshots)
    if not 1 <= config.snapshots <= 10:
        raise ValueError("snapshots must be between 1 and 10")
    if config.hours_apart <= 0:
        raise ValueError("hours_apart must be a positive whole number")
    if config.dual_tree_incidents < 0:
        raise ValueError("dual_tree_incidents must be zero or positive")
    if config.recovery_profile not in {*RECOVERY_PROFILES, "custom"}:
        raise ValueError("Unknown recovery profile")
    if config.arrival_profile not in {*ARRIVAL_PROFILES, "custom"}:
        raise ValueError("Unknown arrival profile")
    if config.recovery_profile == "custom" and config.recovery_target is None:
        raise ValueError("recovery_target is required for the custom recovery profile")
    if config.arrival_profile == "custom" and config.new_incident_share is None:
        raise ValueError("new_incident_share is required for the custom arrival profile")
    if config.recovery_profile != "custom" and config.recovery_target is not None:
        raise ValueError("recovery_target can only be used with the custom recovery profile")
    if config.arrival_profile != "custom" and config.new_incident_share is not None:
        raise ValueError("new_incident_share can only be used with the custom arrival profile")
    if not 0 <= config.resolved_recovery_target <= 1:
        raise ValueError("recovery target must be between 0 and 100 percent")
    if not 0 <= config.resolved_new_incident_share <= 1:
        raise ValueError("new incident share must be between 0 and 100 percent")
    if not 0 < config.arrival_decay <= 1:
        raise ValueError("arrival_decay must be greater than 0 and at most 1")
    if not 0 <= config.repair_duration_variation <= 1:
        raise ValueError("repair_duration_variation must be between 0 and 100 percent")
    if config.snapshots > 1:
        requested = round(config.incident_count * config.resolved_recovery_target)
        on_shift_hours = config.crew_count * (config.snapshots - 1) * config.hours_apart * (16 / 24)
        estimated_capacity = math.floor(on_shift_hours / 1.25)
        if requested > estimated_capacity:
            raise ValueError(
                "Infeasible recovery target for the configured crews and timeline; "
                "add crews, extend the timeline, or lower the recovery target"
            )


def _nonincreasing_geometric_counts(total: int, intervals: int, decay: float) -> list[int]:
    if intervals <= 0:
        return []
    if total <= 0:
        return [0] * intervals
    weights = [decay**index for index in range(intervals)]
    denominator = sum(weights)
    exact = [total * weight / denominator for weight in weights]
    counts = [math.floor(value) for value in exact]
    remaining = total - sum(counts)
    candidates = sorted(range(intervals), key=lambda index: (exact[index] - counts[index], -index), reverse=True)
    while remaining:
        changed = False
        for index in candidates:
            proposed = counts[index] + 1
            if index and proposed > counts[index - 1]:
                continue
            counts[index] = proposed
            remaining -= 1
            changed = True
            if not remaining:
                break
        if not changed:
            counts[0] += remaining
            remaining = 0
    assert all(left >= right for left, right in zip(counts, counts[1:]))
    return counts


def _clearance_counts(total: int, snapshots: int) -> list[int]:
    if snapshots <= 1 or total <= 0:
        return [0] * snapshots
    cumulative = [0]
    for index in range(1, snapshots):
        progress = index / (snapshots - 1)
        smooth = progress * progress * (3 - 2 * progress)
        cumulative.append(round(total * smooth))
    return [cumulative[0], *[cumulative[index] - cumulative[index - 1] for index in range(1, snapshots)]]


def _rotation_position(offset: float, timestamp: datetime, start: datetime) -> float:
    elapsed = (timestamp.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds() / 3600
    return (offset + elapsed) % 24


def _crew_rotation(
    crew_id: str,
    timestamp: datetime,
    start: datetime,
    offsets: dict[str, float],
) -> tuple[bool, float]:
    position = _rotation_position(offsets[crew_id], timestamp, start)
    if position < 16:
        return True, max(0.25, 16 - position)
    return False, 0.0


def _repair_duration(
    incident: dict[str, Any],
    historical_repairs: list[dict[str, Any]],
    variation: float,
    rng: random.Random,
) -> int:
    matches = [
        int(row["average_duration_minutes"])
        for row in historical_repairs
        if row["region"] == incident["region"] and row["incident_type"] == incident["hazard"]
    ]
    if not matches:
        matches = [
            int(row["average_duration_minutes"])
            for row in historical_repairs
            if row["region"] == incident["region"]
        ]
    baseline = sum(matches) / len(matches)
    return max(30, round(baseline * rng.uniform(1 - variation, 1 + variation)))


def _phase_for_assignment(state: dict[str, Any], timestamp: datetime) -> str:
    elapsed = max(0, (
        timestamp.astimezone(timezone.utc) - state["started_at"].astimezone(timezone.utc)
    ).total_seconds() / 60)
    progress = elapsed / max(1, state["duration_minutes"])
    if progress < 0.20:
        return "assigned"
    if progress < 0.40:
        return "en_route"
    if progress < 0.80:
        return "onsite"
    return "energized"


def _crew_matches(crew: dict[str, Any], crew_type: str, incident: dict[str, Any]) -> bool:
    if crew["home_region"] != incident["region"]:
        return False
    suffix_region = _suffix_region(crew["crew_id"])
    if suffix_region and suffix_region != incident["region"]:
        return False
    hazard = incident["hazard"]
    skill = incident["required_skill"]
    if hazard in {"downed wire", "burning wire", "arcing wire"}:
        return crew_type in {"lkp", "ww"}
    if skill == "low_voltage":
        return crew_type == "low_voltage" and int(incident["customers_out"]) == 1
    if skill in {"line", "underground"}:
        return crew_type in {"line", "mua", "cntr"} and int(incident["customers_out"]) >= 40
    if skill == "vegetation":
        return crew_type == "tree"
    return crew_type in {"troubleshooter", "lkp", "ww", "cg"}


def _next_identifier(prefix: str, timestamp: datetime, counters: Counter[str]) -> str:
    day = timestamp.strftime("%Y%m%d")
    counters[day] += 1
    return f"{prefix}-{day}-{counters[day]:04d}"


def _initialize_counters(rows: list[dict[str, Any]], field: str) -> Counter[str]:
    counters: Counter[str] = Counter()
    for row in rows:
        parts = str(row[field]).split("-")
        if len(parts) >= 3 and parts[-1].isdigit():
            counters[parts[-2]] = max(counters[parts[-2]], int(parts[-1]))
    return counters


def _release_assignment(
    assignment_id: str,
    assignments: dict[str, dict[str, Any]],
    assignment_states: dict[str, dict[str, Any]],
    crews: dict[str, dict[str, Any]],
    incident: dict[str, Any],
) -> None:
    assignment = assignments.pop(assignment_id)
    assignment_states.pop(assignment_id, None)
    crew = crews[assignment["crew_id"]]
    crew["current_location"] = incident["municipality"]


def _finish_tree_work(
    timestamp: datetime,
    incidents: dict[str, dict[str, Any]],
    crews: dict[str, dict[str, Any]],
    assignments: dict[str, dict[str, Any]],
    assignment_states: dict[str, dict[str, Any]],
    crew_types: dict[str, str],
) -> None:
    by_incident: dict[str, list[str]] = defaultdict(list)
    for assignment_id, assignment in assignments.items():
        by_incident[assignment["incident_id"]].append(assignment_id)
    for incident_id, assignment_ids in by_incident.items():
        if len(assignment_ids) < 2:
            continue
        for assignment_id in list(assignment_ids):
            assignment = assignments[assignment_id]
            if crew_types[assignment["crew_id"]] != "tree":
                continue
            state = assignment_states[assignment_id]
            elapsed = (
                timestamp.astimezone(timezone.utc) - state["started_at"].astimezone(timezone.utc)
            ).total_seconds() / 60
            if elapsed >= state["duration_minutes"]:
                _release_assignment(assignment_id, assignments, assignment_states, crews, incidents[incident_id])


def _update_snapshot_state(
    timestamp: datetime,
    start: datetime,
    incidents: dict[str, dict[str, Any]],
    crews: dict[str, dict[str, Any]],
    assignments: dict[str, dict[str, Any]],
    assignment_states: dict[str, dict[str, Any]],
    offsets: dict[str, float],
    *,
    preserve_etr: bool = False,
) -> None:
    assignments_by_incident: dict[str, list[str]] = defaultdict(list)
    assigned_crews = {row["crew_id"] for row in assignments.values()}
    for assignment_id, assignment in assignments.items():
        assignments_by_incident[assignment["incident_id"]].append(assignment_id)
    for incident in incidents.values():
        incident["age_minutes"] = int(incident["age_minutes"]) + 0
        active_ids = assignments_by_incident.get(incident["incident_id"], [])
        if active_ids:
            phases = [
                _phase_for_assignment(assignment_states[assignment_id], timestamp)
                for assignment_id in active_ids
            ]
            incident["status"] = INCIDENT_PHASES[max(INCIDENT_PHASES.index(phase) for phase in phases)]
            latest_end = max(
                assignment_states[assignment_id]["started_at"]
                + timedelta(minutes=assignment_states[assignment_id]["duration_minutes"])
                for assignment_id in active_ids
            )
            if not preserve_etr:
                incident["etr"] = max(latest_end, timestamp + timedelta(minutes=15)).isoformat()
        else:
            incident["status"] = "unassigned"
            estimated_minutes = max(
                60,
                min(720, 90 + int(incident["customers_out"]) // 5),
            )
            if not preserve_etr:
                incident["etr"] = (timestamp + timedelta(minutes=estimated_minutes)).isoformat()
    for crew_id, crew in crews.items():
        on_shift, remaining = _crew_rotation(crew_id, timestamp, start, offsets)
        if crew_id in assigned_crews:
            crew["status"] = "assigned"
        else:
            crew["status"] = "available" if on_shift else "off_shift"
        crew["shift_remaining_hours"] = round(remaining, 2)
        travel_rng = random.Random(
            f"{crew_id}|{crew['current_location']}|{timestamp.isoformat()}"
        )
        crew["travel_minutes_to_selected_incident"] = travel_rng.randint(8, 75)


def _assign_pending_work(
    timestamp: datetime,
    start: datetime,
    config: TimelineConfig,
    rng: random.Random,
    incidents: dict[str, dict[str, Any]],
    crews: dict[str, dict[str, Any]],
    assignments: dict[str, dict[str, Any]],
    assignment_states: dict[str, dict[str, Any]],
    assignment_counters: Counter[str],
    crew_types: dict[str, str],
    historical_repairs: list[dict[str, Any]],
    offsets: dict[str, float],
    *,
    preserve_etr: bool = False,
) -> None:
    assigned_incidents = {row["incident_id"] for row in assignments.values()}
    desired = round(len(incidents) * config.assignment_rate)
    needed = max(0, desired - len(assigned_incidents))
    if not needed:
        return
    assigned_crew_ids = {row["crew_id"] for row in assignments.values()}
    free_crews = [crew for crew in crews.values() if crew["crew_id"] not in assigned_crew_ids]
    candidates = [incident for incident in incidents.values() if incident["incident_id"] not in assigned_incidents]
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    candidates.sort(key=lambda row: (severity_order.get(row["severity"], 4), row["incident_id"]))
    rng.shuffle(free_crews)
    for incident in candidates:
        if needed <= 0:
            break
        duration = _repair_duration(incident, historical_repairs, config.repair_duration_variation, rng)
        travel = rng.randint(8, 75)
        matches = []
        for crew in free_crews:
            on_shift, remaining = _crew_rotation(crew["crew_id"], timestamp, start, offsets)
            if not on_shift or duration + travel > remaining * 60:
                continue
            if _crew_matches(crew, crew_types[crew["crew_id"]], incident):
                matches.append(crew)
        if not matches:
            continue
        selected = [matches[0]]
        durations = [duration]
        notes = ["Timeline reassignment using regional capability and remaining-shift rules"]
        if incident["hazard"] == "tree on primary":
            repair_matches = []
            for repair_crew in free_crews:
                repair_type = crew_types[repair_crew["crew_id"]]
                on_shift, remaining = _crew_rotation(repair_crew["crew_id"], timestamp, start, offsets)
                if (
                    repair_crew["home_region"] == incident["region"]
                    and repair_type in {"mua", "cntr"}
                    and on_shift
                    and duration + travel <= remaining * 60
                ):
                    repair_matches.append(repair_crew)
            if not repair_matches:
                continue
            selected = [repair_matches[0], matches[0]]
            durations = [duration, max(30, round(duration * 0.60))]
            notes = [
                "Repair crew paired for primary restoration after tree clearance",
                "TREE crew paired to clear primary conductors before repair completion",
            ]
        for crew, crew_duration, note in zip(selected, durations, notes):
            assignment_id = _next_identifier("ASG", timestamp, assignment_counters)
            assignments[assignment_id] = {
                "assignment_id": assignment_id,
                "incident_id": incident["incident_id"],
                "crew_id": crew["crew_id"],
                "status": "active",
                "assigned_at": timestamp.isoformat(),
                "notes": note,
            }
            assignment_states[assignment_id] = {
                "started_at": timestamp,
                "duration_minutes": crew_duration,
            }
            crew["status"] = "assigned"
            crew["travel_minutes_to_selected_incident"] = travel
            free_crews.remove(crew)
        incident["status"] = "assigned"
        if not preserve_etr:
            incident["etr"] = (timestamp + timedelta(minutes=duration + travel)).isoformat()
        needed -= 1


def _weather_for_snapshot(
    base_weather: list[dict[str, Any]],
    timestamp: datetime,
    decay: float,
    index: int,
) -> list[dict[str, Any]]:
    factor = decay**index
    rows = copy.deepcopy(base_weather)
    for row in rows:
        row["updated_at"] = timestamp.isoformat()
        row["wind_mph"] = max(5, round(float(row["wind_mph"]) * max(0.35, factor)))
        row["precipitation_inches"] = round(float(row["precipitation_inches"]) * factor, 2)
        if factor < 0.35:
            row["condition"] = "overcast"
            row["lightning_risk"] = "low"
        elif factor < 0.65 and row["lightning_risk"] == "high":
            row["condition"] = "light rain"
            row["lightning_risk"] = "medium"
    return rows


def _snapshot_scenario(
    scenario_id: str,
    incidents: dict[str, dict[str, Any]],
    crews: dict[str, dict[str, Any]],
    assignments: dict[str, dict[str, Any]],
    base: GeneratedScenario,
    weather: list[dict[str, Any]],
    temporal: dict[str, Any] | None = None,
    etr_mix_counts: dict[str, int] | None = None,
) -> GeneratedScenario:
    return GeneratedScenario(
        scenario_id=scenario_id,
        incidents=copy.deepcopy(sorted(incidents.values(), key=lambda row: row["incident_id"])),
        crews=copy.deepcopy(sorted(crews.values(), key=lambda row: row["crew_id"])),
        assignments=copy.deepcopy(sorted(assignments.values(), key=lambda row: row["assignment_id"])),
        historical_repairs=copy.deepcopy(base.historical_repairs),
        weather=weather,
        critical_facilities=copy.deepcopy(base.critical_facilities),
        topology=copy.deepcopy(base.topology),
        crew_types=copy.deepcopy(base.crew_types),
        temporal=copy.deepcopy(temporal),
        etr_mix_counts=etr_mix_counts or {},
    )


def _temporal_cutoff(start: datetime, index: int, hours_apart: int) -> datetime:
    """Advance by elapsed hours, including across Eastern DST transitions."""
    return (start.astimezone(timezone.utc) + timedelta(hours=index * hours_apart)).astimezone(LOCAL_TIMEZONE)


def _arrival_window(
    previous: datetime,
    current: datetime,
    start_date: date,
    end_date: date,
) -> tuple[datetime, int] | None:
    """Return the first eligible UTC minute and number of eligible minutes."""
    first = max(
        previous.astimezone(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=1),
        datetime.combine(start_date, time.min, LOCAL_TIMEZONE).astimezone(timezone.utc),
    )
    last_exclusive = min(
        current.astimezone(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=1),
        datetime.combine(end_date + timedelta(days=1), time.min, LOCAL_TIMEZONE).astimezone(timezone.utc),
    )
    count = int((last_exclusive - first).total_seconds() // 60)
    return (first, count) if count > 0 else None


def generate_timeline(
    *,
    scenario_id: str,
    start_date: date,
    end_date: date | None = None,
    start_time: time = time(8, 0),
    snapshots: int = 5,
    hours_apart: int = 12,
    incident_count: int = 2000,
    crew_count: int = 500,
    assignment_rate: float = 0.05,
    dual_tree_incidents: int = 5,
    critical_facilities_per_region: int | None = None,
    seed: int = 20260810,
    start_day_location_rate: float = DEFAULT_START_DAY_LOCATION_RATE,
    recovery_profile: str = "fast",
    recovery_target: float | None = None,
    arrival_profile: str = "moderate",
    new_incident_share: float | None = None,
    arrival_decay: float = 0.60,
    repair_duration_variation: float = 0.25,
    lookup_path: Path = DEFAULT_LOOKUP_PATH,
    etr_mix: str | None = None,
    assessing_conversion: str | None = None,
    assessing_conversion_overrides: str | None = None,
) -> GeneratedTimeline:
    config = TimelineConfig(
        scenario_id=scenario_id,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        snapshots=snapshots,
        hours_apart=hours_apart,
        incident_count=incident_count,
        crew_count=crew_count,
        assignment_rate=assignment_rate,
        dual_tree_incidents=dual_tree_incidents,
        critical_facilities_per_region=critical_facilities_per_region,
        seed=seed,
        start_day_location_rate=start_day_location_rate,
        recovery_profile=recovery_profile,
        recovery_target=recovery_target,
        arrival_profile=arrival_profile,
        new_incident_share=new_incident_share,
        arrival_decay=arrival_decay,
        repair_duration_variation=repair_duration_variation,
        lookup_path=lookup_path,
        etr_mix=etr_mix,
        assessing_conversion=assessing_conversion,
        assessing_conversion_overrides=assessing_conversion_overrides,
    )
    _validate_config(config)
    temporal_mode = etr_mix is not None or assessing_conversion is not None
    effective_etr_mix = etr_mix or DEFAULT_ETR_MIX if temporal_mode else None
    conversion_rule = parse_assessing_conversion(assessing_conversion) if assessing_conversion else None
    conversion_overrides = parse_assessing_conversion_overrides(assessing_conversion_overrides, snapshots)
    start = config.first_timestamp
    base = generate_scenario(
        scenario_id=f"{scenario_id}_01",
        start_date=start_date,
        end_date=start_date if temporal_mode else end_date,
        incident_count=incident_count,
        crew_count=crew_count,
        assignment_rate=assignment_rate,
        dual_tree_incidents=dual_tree_incidents,
        critical_facilities_per_region=critical_facilities_per_region,
        seed=seed,
        start_day_location_rate=start_day_location_rate,
        lookup_path=lookup_path,
        as_of_at=start if temporal_mode else None,
        etr_mix=effective_etr_mix,
    )
    if snapshots == 1:
        arrival_counts = []
        clearance_counts = [0]
    else:
        arrival_total = round(incident_count * config.resolved_new_incident_share)
        if temporal_mode:
            eligible_steps = [
                index
                for index in range(1, snapshots)
                if _arrival_window(
                    _temporal_cutoff(start, index - 1, hours_apart),
                    _temporal_cutoff(start, index, hours_apart),
                    start_date,
                    end_date or start_date,
                ) is not None
            ]
            if arrival_total and not eligible_steps:
                raise ValueError("No timeline step intersects the requested arrival dates")
            eligible_counts = _nonincreasing_geometric_counts(
                arrival_total, len(eligible_steps), config.effective_arrival_decay
            ) if eligible_steps else []
            arrival_counts = [0] * (snapshots - 1)
            for index, count in zip(eligible_steps, eligible_counts):
                arrival_counts[index - 1] = count
        else:
            arrival_counts = _nonincreasing_geometric_counts(
                arrival_total,
                snapshots - 1,
                config.effective_arrival_decay,
            )
        clearance_counts = _clearance_counts(
            round(incident_count * config.resolved_recovery_target),
            snapshots,
        )

    rng = random.Random(seed + 1_000_003)
    criticality_rng = random.Random(seed + 3_000_003)
    municipalities = load_municipalities(lookup_path)
    incidents = {row["incident_id"]: copy.deepcopy(row) for row in base.incidents}
    crews = {row["crew_id"]: copy.deepcopy(row) for row in base.crews}
    assignments = {row["assignment_id"]: copy.deepcopy(row) for row in base.assignments}
    protected_lse_incident_ids = {
        str(row["incident_id"])
        for row in _lse_boundary_incidents(
            base.incidents,
            base.critical_facilities,
        )
    }
    initial_incident_ids = [
        incident_id
        for incident_id in incidents
        if incident_id not in protected_lse_incident_ids
    ]
    rng.shuffle(initial_incident_ids)
    initial_incident_ids.extend(sorted(protected_lse_incident_ids))
    clearance_cursor = 0
    incident_counters = _initialize_counters(base.incidents, "incident_id")
    assignment_counters = _initialize_counters(base.assignments, "assignment_id")
    offsets = {crew_id: rng.randrange(24) for crew_id in crews}
    arrival_time_rng = random.Random(f"{seed}:poc049:timeline:created")
    arrival_etr_rng = random.Random(f"{seed}:poc049:timeline:etr")
    mix = parse_etr_mix(effective_etr_mix) if temporal_mode else ()
    conversion_rng = random.Random(f"{seed}:poc049:timeline:conversion")
    conversion_remainder = Decimal(0)
    assignment_states: dict[str, dict[str, Any]] = {}
    for assignment_id, assignment in assignments.items():
        try:
            assigned_at = datetime.fromisoformat(str(assignment["assigned_at"]))
        except ValueError:
            assigned_at = start
        if config.start_time != time(8, 0) and not temporal_mode:
            assigned_at = start
            assignment["assigned_at"] = start.isoformat()
        assignment_states[assignment_id] = {
            "started_at": assigned_at,
            "duration_minutes": _repair_duration(
                incidents[assignment["incident_id"]],
                base.historical_repairs,
                repair_duration_variation,
                rng,
            ),
        }
        offsets[assignment["crew_id"]] = 0

    capacity_geographies = {
        row.reference_id: row for row in load_capacity_geographies()
    }
    facility_keys = _facility_keys(base.critical_facilities)
    results: list[TimelineSnapshot] = []
    previous_timestamp = start
    for snapshot_index in range(snapshots):
        timestamp = (
            _temporal_cutoff(start, snapshot_index, hours_apart)
            if temporal_mode else start + timedelta(hours=snapshot_index * hours_apart)
        )
        arrivals: list[str] = []
        cleared: list[str] = []
        converted: list[str] = []
        conversion_eligible_count = 0
        cohort_mix_counts: Counter[str] = Counter()
        if snapshot_index:
            if temporal_mode:
                for incident in incidents.values():
                    created = datetime.fromisoformat(str(incident["created_at"]))
                    incident["age_minutes"] = int(
                        (timestamp.astimezone(timezone.utc) - created.astimezone(timezone.utc)).total_seconds() // 60
                    )
            else:
                elapsed_minutes = int((timestamp - previous_timestamp).total_seconds() / 60)
                for incident in incidents.values():
                    incident["age_minutes"] = int(incident["age_minutes"]) + elapsed_minutes

            count_to_clear = clearance_counts[snapshot_index]
            ids_to_clear = initial_incident_ids[clearance_cursor : clearance_cursor + count_to_clear]
            clearance_cursor += count_to_clear
            for incident_id in ids_to_clear:
                incident = incidents.pop(incident_id)
                for assignment_id in [
                    key for key, row in assignments.items() if row["incident_id"] == incident_id
                ]:
                    _release_assignment(assignment_id, assignments, assignment_states, crews, incident)
                cleared.append(incident_id)

            eligible = sorted(
                incident_id for incident_id, incident in incidents.items()
                if incident.get("etr_status") == "assessing_conditions" and incident.get("etr") is None
            ) if temporal_mode else []
            conversion_eligible_count = len(eligible)
            rule = conversion_overrides.get(snapshot_index + 1, conversion_rule)
            if rule is not None:
                exact = Decimal(len(eligible)) * rule.percent / 100 + conversion_remainder
                count = min(len(eligible), int(exact))
                conversion_remainder = exact - count
                conversion_rng.shuffle(eligible)
                for incident_id in eligible[:count]:
                    incident = incidents[incident_id]
                    incident["etr"] = (
                        timestamp.astimezone(timezone.utc) + timedelta(hours=rule.hours)
                    ).astimezone(LOCAL_TIMEZONE).isoformat()
                    incident["etr_status"] = "estimated"
                    incident["etr_updated_at"] = timestamp.isoformat()
                    incident["etr_source"] = "timeline_assessment_conversion"
                    converted.append(incident_id)

            arrival_count = arrival_counts[snapshot_index - 1]
            window = _arrival_window(
                previous_timestamp, timestamp, start_date, end_date or start_date
            ) if temporal_mode and arrival_count else None
            allocations = _mix_labels(mix, arrival_count, arrival_etr_rng) if temporal_mode else []
            for arrival_index in range(arrival_count):
                created = (
                    (window[0] + timedelta(minutes=arrival_time_rng.randrange(window[1]))).astimezone(LOCAL_TIMEZONE)
                    if window is not None else timestamp
                )
                arrival_id = _next_identifier("ESD", created, incident_counters)
                sequence = int(arrival_id.rsplit("-", 1)[1])
                incident = _base_incident(created.date(), sequence, municipalities, rng)
                incident["incident_id"] = arrival_id
                active_totals: Counter[str] = Counter()
                anchors: dict[str, dict[str, Any]] = {}
                for active in incidents.values():
                    reference_id = str(active.get("geography_reference_id") or "")
                    if reference_id:
                        active_totals[reference_id] += int(active["customers_out"])
                        anchors.setdefault(reference_id, active)
                required = int(incident["customers_out"])
                candidates = [
                    geography
                    for reference_id, geography in capacity_geographies.items()
                    if reference_id in anchors
                    and geography.customers_served - active_totals[reference_id]
                    >= required
                ]
                if not candidates:
                    raise ValueError(
                        "Timeline arrival cannot fit remaining approved geography capacity: "
                        f"incident {arrival_id}, customers_out {required:,}"
                    )
                geography = min(
                    candidates,
                    key=lambda row: (
                        row.region != incident["region"],
                        row.customers_served - active_totals[row.reference_id],
                        row.reference_id,
                    ),
                )
                _apply_capacity_location(incident, geography)
                incident["feeder"] = anchors[geography.reference_id]["feeder"]
                _set_linked_criticality(incident, facility_keys, criticality_rng)
                if temporal_mode:
                    allocation = allocations[arrival_index]
                    cohort_mix_counts[allocation.label] += 1
                    incident["created_at"] = created.isoformat()
                    incident["created_at_source"] = "synthetic_generator"
                    incident["age_minutes"] = int(
                        (timestamp.astimezone(timezone.utc) - created.astimezone(timezone.utc)).total_seconds() // 60
                    )
                    if allocation.label == "null":
                        incident["etr"] = None
                        incident["etr_status"] = "assessing_conditions"
                    else:
                        duration = arrival_etr_rng.randint(
                            allocation.minimum_minutes, allocation.maximum_minutes
                        )
                        incident["etr"] = (
                            created.astimezone(timezone.utc) + timedelta(minutes=duration)
                        ).astimezone(LOCAL_TIMEZONE).isoformat()
                        incident["etr_status"] = "estimated"
                else:
                    incident["age_minutes"] = rng.randint(1, max(1, elapsed_minutes))
                    incident["etr"] = (timestamp + timedelta(minutes=_repair_duration(
                        incident, base.historical_repairs, repair_duration_variation, rng
                    ))).isoformat()
                incidents[arrival_id] = incident
                arrivals.append(arrival_id)

            _finish_tree_work(
                timestamp,
                incidents,
                crews,
                assignments,
                assignment_states,
                base.crew_types,
            )
            _update_snapshot_state(
                timestamp, start, incidents, crews, assignments, assignment_states, offsets,
                preserve_etr=temporal_mode,
            )
            _assign_pending_work(
                timestamp,
                start,
                config,
                rng,
                incidents,
                crews,
                assignments,
                assignment_states,
                assignment_counters,
                base.crew_types,
                base.historical_repairs,
                offsets,
                preserve_etr=temporal_mode,
            )
        _update_snapshot_state(
            timestamp, start, incidents, crews, assignments, assignment_states, offsets,
            preserve_etr=temporal_mode,
        )
        temporal = None
        if temporal_mode:
            temporal = {
                "kind": "timeline_snapshot",
                "as_of_at": timestamp.isoformat(),
                "time_zone": "America/New_York",
                "etr_distribution": base.temporal["etr_distribution"],
                "timeline_id": scenario_id,
                "snapshot_index": snapshot_index + 1,
                "snapshot_count": snapshots,
                "assessing_conversion": conversion_rule.as_manifest() if conversion_rule else None,
                "assessing_conversion_overrides": {
                    step: rule.as_manifest() for step, rule in conversion_overrides.items()
                },
            }
        scenario = _snapshot_scenario(
            f"{scenario_id}_{snapshot_index + 1:02d}",
            incidents,
            crews,
            assignments,
            base,
            _weather_for_snapshot(base.weather, timestamp, config.effective_arrival_decay, snapshot_index),
            temporal=temporal,
            etr_mix_counts=base.etr_mix_counts if snapshot_index == 0 else dict(cohort_mix_counts),
        )
        validate_timeline_snapshot(scenario)
        results.append(
            TimelineSnapshot(
                index=snapshot_index + 1,
                timestamp=timestamp,
                scenario=scenario,
                new_incident_ids=tuple(arrivals),
                cleared_incident_ids=tuple(cleared),
                converted_incident_ids=tuple(converted),
                conversion_eligible_count=conversion_eligible_count,
            )
        )
        previous_timestamp = timestamp

    timeline = GeneratedTimeline(config=config, snapshots=results)
    validate_timeline(timeline)
    return timeline


def validate_timeline_snapshot(scenario: GeneratedScenario) -> None:
    validate_population_capacity(scenario.incidents)
    incident_by_id = {row["incident_id"]: row for row in scenario.incidents}
    crew_by_id = {row["crew_id"]: row for row in scenario.crews}
    if len(incident_by_id) != len(scenario.incidents):
        raise ValueError("Timeline incident IDs are not unique")
    if len(crew_by_id) != len(scenario.crews):
        raise ValueError("Timeline crew IDs are not unique")
    if len({row["assignment_id"] for row in scenario.assignments}) != len(scenario.assignments):
        raise ValueError("Timeline assignment IDs are not unique")
    active_crews: Counter[str] = Counter()
    for assignment in scenario.assignments:
        if assignment["status"] != "active":
            raise ValueError("Timeline assignments must remain active while present")
        if assignment["incident_id"] not in incident_by_id or assignment["crew_id"] not in crew_by_id:
            raise ValueError("Timeline assignment contains an unknown foreign key")
        incident = incident_by_id[assignment["incident_id"]]
        crew = crew_by_id[assignment["crew_id"]]
        if incident["status"] not in INCIDENT_PHASES:
            raise ValueError("Active timeline assignments require a nonterminal incident phase")
        if crew["status"] != "assigned":
            raise ValueError("A crew with an active timeline assignment must be assigned")
        suffix_region = _suffix_region(crew["crew_id"])
        if suffix_region and (crew["home_region"] != suffix_region or incident["region"] != suffix_region):
            raise ValueError("A region-encoded crew is assigned outside its region")
        crew_type = scenario.crew_types[crew["crew_id"]]
        if crew_type == "low_voltage" and (
            int(incident["customers_out"]) != 1 or incident["required_skill"] != "low_voltage"
        ):
            raise ValueError("Low-voltage timeline work violates the single-customer rule")
        if crew_type == "line" and (
            int(incident["customers_out"]) < 40 or incident["required_skill"] not in {"line", "underground"}
        ):
            raise ValueError("Line-crew timeline work violates the 40-customer rule")
        active_crews[assignment["crew_id"]] += 1
    if any(count > 1 for count in active_crews.values()):
        raise ValueError("A crew has multiple active timeline assignments")
    active_crew_ids = set(active_crews)
    if any(row["status"] == "assigned" and row["crew_id"] not in active_crew_ids for row in scenario.crews):
        raise ValueError("An assigned timeline crew has no active assignment")
    if {row["region"] for row in scenario.weather} != set(REGIONS):
        raise ValueError("Timeline weather must cover all regions")
    validate_critical_facility_linkage(
        scenario.incidents,
        scenario.critical_facilities,
    )
    topology_feeders = {(row["region"], row["feeder"]) for row in scenario.topology}
    if not {(row["region"], row["feeder"]) for row in scenario.incidents}.issubset(topology_feeders):
        raise ValueError("Timeline topology does not cover every pending incident feeder")


def validate_timeline(timeline: GeneratedTimeline) -> None:
    snapshots = timeline.snapshots
    if len(snapshots) != timeline.config.snapshots:
        raise ValueError("Timeline snapshot count does not match configuration")
    validate_lse_coverage(
        snapshots[0].scenario.incidents,
        snapshots[0].scenario.critical_facilities,
    )
    cleared_seen: set[str] = set()
    first_temporal = snapshots[0].scenario.temporal
    for index, snapshot in enumerate(snapshots):
        expected_id = f"{timeline.config.scenario_id}_{index + 1:02d}"
        if snapshot.scenario.scenario_id != expected_id:
            raise ValueError("Timeline scenario IDs are not zero-padded and chronological")
        current_ids = {row["incident_id"] for row in snapshot.scenario.incidents}
        if (snapshot.scenario.temporal is None) != (first_temporal is None):
            raise ValueError("Timeline siblings mix temporal and legacy contracts")
        if snapshot.scenario.temporal is not None:
            metadata = snapshot.scenario.temporal
            if any(metadata.get(name) != first_temporal.get(name) for name in (
                "time_zone", "etr_distribution", "assessing_conversion", "assessing_conversion_overrides"
            )):
                raise ValueError("Timeline siblings have inconsistent temporal policy")
            if (
                metadata.get("timeline_id") != timeline.config.scenario_id
                or metadata.get("snapshot_index") != index + 1
                or metadata.get("snapshot_count") != len(snapshots)
                or datetime.fromisoformat(metadata["as_of_at"]).astimezone(timezone.utc)
                != snapshot.timestamp.astimezone(timezone.utc)
            ):
                raise ValueError("Timeline temporal identity or cutoff is inconsistent")
            cutoff = snapshot.timestamp.astimezone(timezone.utc)
            for incident in snapshot.scenario.incidents:
                created = datetime.fromisoformat(str(incident["created_at"])).astimezone(timezone.utc)
                if created > cutoff or int(incident["age_minutes"]) != int((cutoff - created).total_seconds() // 60):
                    raise ValueError("Timeline incident creation or snapshot age is invalid")
        if cleared_seen & current_ids:
            raise ValueError("An incident reappeared after clearance")
        if index:
            previous_ids = {row["incident_id"] for row in snapshots[index - 1].scenario.incidents}
            expected_count = (
                len(previous_ids)
                + len(snapshot.new_incident_ids)
                - len(snapshot.cleared_incident_ids)
            )
            if len(current_ids) != expected_count:
                raise ValueError("Timeline queue conservation failed")
            if not set(snapshot.new_incident_ids).issubset(current_ids):
                raise ValueError("Timeline arrival is missing from its snapshot")
            if snapshot.scenario.temporal is not None:
                before = {row["incident_id"]: row for row in snapshots[index - 1].scenario.incidents}
                after = {row["incident_id"]: row for row in snapshot.scenario.incidents}
                if not set(snapshot.converted_incident_ids).issubset(before.keys() & after.keys()):
                    raise ValueError("Only continuing incidents can receive an ETR conversion")
                for incident_id in before.keys() & after.keys():
                    prior, current = before[incident_id], after[incident_id]
                    if current["created_at"] != prior["created_at"]:
                        raise ValueError("Timeline incident creation time changed")
                    converted = incident_id in snapshot.converted_incident_ids
                    if prior["etr_status"] == "assessing_conditions":
                        if converted:
                            if (
                                current["etr_status"] != "estimated"
                                or current.get("etr_source") != "timeline_assessment_conversion"
                                or current.get("etr_updated_at") != snapshot.timestamp.isoformat()
                            ):
                                raise ValueError("Timeline ETR conversion provenance is invalid")
                        elif current["etr_status"] != "assessing_conditions" or current["etr"] is not None:
                            raise ValueError("Assessing Conditions changed without configured conversion")
                    elif converted:
                        raise ValueError("An already estimated ETR was converted again")
                previous_cutoff = snapshots[index - 1].timestamp.astimezone(timezone.utc)
                for incident_id in snapshot.new_incident_ids:
                    created = datetime.fromisoformat(str(after[incident_id]["created_at"])).astimezone(timezone.utc)
                    if not previous_cutoff < created <= snapshot.timestamp.astimezone(timezone.utc):
                        raise ValueError("Timeline arrival falls outside its step window")
        cleared_seen.update(snapshot.cleared_incident_ids)
    if len(snapshots) > 1:
        expected_arrivals = round(timeline.config.incident_count * timeline.config.resolved_new_incident_share)
        expected_clearances = round(timeline.config.incident_count * timeline.config.resolved_recovery_target)
        if sum(len(row.new_incident_ids) for row in snapshots) != expected_arrivals:
            raise ValueError("Timeline arrival target was not met")
        if sum(len(row.cleared_incident_ids) for row in snapshots) != expected_clearances:
            raise ValueError("Timeline recovery target was not met")


def _write_snapshot(snapshot: TimelineSnapshot, output_root: Path) -> Path:
    target = write_scenario(snapshot.scenario, output_root)
    manifest_path = target / "scenario.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["name"] = f"Generated Timeline Snapshot {snapshot.index}"
    manifest["description"] = (
        "Synthetic Long Island storm progression snapshot at "
        f"{snapshot.timestamp.isoformat()}; select sibling snapshots sequentially."
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target


def write_timeline(timeline: GeneratedTimeline, output_root: Path = DEFAULT_OUTPUT_ROOT) -> list[Path]:
    output_root = output_root.resolve()
    targets = [output_root / snapshot.scenario.scenario_id for snapshot in timeline.snapshots]
    existing = [target for target in targets if target.exists()]
    if existing:
        raise FileExistsError(f"Timeline output already exists: {existing[0]}")
    output_root.mkdir(parents=True, exist_ok=True)
    published: list[Path] = []
    with tempfile.TemporaryDirectory(prefix=f".{timeline.config.scenario_id}-timeline-", dir=output_root) as temporary:
        staging_root = Path(temporary)
        for snapshot in timeline.snapshots:
            _write_snapshot(snapshot, staging_root)
            descriptor = ScenarioService(staging_root, snapshot.scenario.scenario_id).active_scenario()
            if descriptor.validation_status != "valid":
                raise ValueError(f"Staged snapshot {snapshot.scenario.scenario_id} failed application validation")
        try:
            for snapshot in timeline.snapshots:
                staged = staging_root / snapshot.scenario.scenario_id
                target = output_root / snapshot.scenario.scenario_id
                staged.rename(target)
                published.append(target)
        except Exception:
            for target in reversed(published):
                if target.exists():
                    target.rename(staging_root / target.name)
            raise
    return published
