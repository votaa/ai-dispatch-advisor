from __future__ import annotations

import copy
import json
import math
import random
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from .scenario_generator import (
    DEFAULT_LOOKUP_PATH,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_START_DAY_LOCATION_RATE,
    LOCAL_TIMEZONE,
    REGIONS,
    GeneratedScenario,
    _apply_capacity_location,
    _base_incident,
    _facility_keys,
    _lse_boundary_incidents,
    _set_linked_criticality,
    _suffix_region,
    generate_scenario,
    load_capacity_geographies,
    load_municipalities,
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

    def summary(self) -> dict[str, Any]:
        crew_counts = Counter(row["status"] for row in self.scenario.crews)
        return {
            "snapshot": self.index,
            "scenario_id": self.scenario.scenario_id,
            "timestamp": self.timestamp.isoformat(),
            "pending": len(self.scenario.incidents),
            "new": len(self.new_incident_ids),
            "cleared": len(self.cleared_incident_ids),
            "assigned": sum(row["status"] != "unassigned" for row in self.scenario.incidents),
            "available": crew_counts["available"],
            "off_shift": crew_counts["off_shift"],
        }


@dataclass
class GeneratedTimeline:
    config: TimelineConfig
    snapshots: list[TimelineSnapshot]

    def summary(self) -> dict[str, Any]:
        return {
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
            },
            "snapshots": [snapshot.summary() for snapshot in self.snapshots],
        }


def _validate_config(config: TimelineConfig) -> None:
    if config.scenario_id == "base":
        raise ValueError("The protected base scenario cannot be generated or replaced")
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
    elapsed = (timestamp - start).total_seconds() / 3600
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
    elapsed = max(0, (timestamp - state["started_at"]).total_seconds() / 60)
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
            elapsed = (timestamp - state["started_at"]).total_seconds() / 60
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
            incident["etr"] = max(latest_end, timestamp + timedelta(minutes=15)).isoformat()
        else:
            incident["status"] = "unassigned"
            estimated_minutes = max(
                60,
                min(720, 90 + int(incident["customers_out"]) // 5),
            )
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
    )


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
    )
    _validate_config(config)
    base = generate_scenario(
        scenario_id=f"{scenario_id}_01",
        start_date=start_date,
        end_date=end_date,
        incident_count=incident_count,
        crew_count=crew_count,
        assignment_rate=assignment_rate,
        dual_tree_incidents=dual_tree_incidents,
        critical_facilities_per_region=critical_facilities_per_region,
        seed=seed,
        start_day_location_rate=start_day_location_rate,
        lookup_path=lookup_path,
    )
    if snapshots == 1:
        arrival_counts = []
        clearance_counts = [0]
    else:
        arrival_total = round(incident_count * config.resolved_new_incident_share)
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
    start = config.first_timestamp
    assignment_states: dict[str, dict[str, Any]] = {}
    for assignment_id, assignment in assignments.items():
        try:
            assigned_at = datetime.fromisoformat(str(assignment["assigned_at"]))
        except ValueError:
            assigned_at = start
        if config.start_time != time(8, 0):
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
        timestamp = start + timedelta(hours=snapshot_index * hours_apart)
        arrivals: list[str] = []
        cleared: list[str] = []
        if snapshot_index:
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

            for _ in range(arrival_counts[snapshot_index - 1]):
                arrival_id = _next_identifier("ESD", timestamp, incident_counters)
                sequence = int(arrival_id.rsplit("-", 1)[1])
                incident = _base_incident(timestamp.date(), sequence, municipalities, rng)
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
            _update_snapshot_state(timestamp, start, incidents, crews, assignments, assignment_states, offsets)
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
            )
        _update_snapshot_state(timestamp, start, incidents, crews, assignments, assignment_states, offsets)
        scenario = _snapshot_scenario(
            f"{scenario_id}_{snapshot_index + 1:02d}",
            incidents,
            crews,
            assignments,
            base,
            _weather_for_snapshot(base.weather, timestamp, config.effective_arrival_decay, snapshot_index),
        )
        validate_timeline_snapshot(scenario)
        results.append(
            TimelineSnapshot(
                index=snapshot_index + 1,
                timestamp=timestamp,
                scenario=scenario,
                new_incident_ids=tuple(arrivals),
                cleared_incident_ids=tuple(cleared),
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
    for index, snapshot in enumerate(snapshots):
        expected_id = f"{timeline.config.scenario_id}_{index + 1:02d}"
        if snapshot.scenario.scenario_id != expected_id:
            raise ValueError("Timeline scenario IDs are not zero-padded and chronological")
        current_ids = {row["incident_id"] for row in snapshot.scenario.incidents}
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
