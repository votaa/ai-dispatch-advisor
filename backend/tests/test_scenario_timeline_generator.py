from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest

from app.scenario_generator import generate_scenario
from app.scenario_service import ScenarioService
from app.scenario_timeline_generator import (
    ARRIVAL_PROFILES,
    INCIDENT_PHASES,
    RECOVERY_PROFILES,
    generate_timeline,
    write_timeline,
)


def _timeline(**overrides):
    settings = {
        "scenario_id": "timeline-test",
        "start_date": date(2026, 8, 10),
        "incident_count": 120,
        "crew_count": 100,
        "assignment_rate": 0.10,
        "dual_tree_incidents": 2,
        "critical_facilities_per_region": 2,
        "seed": 7,
    }
    settings.update(overrides)
    return generate_timeline(**settings)


def _rows_by_id(rows, field):
    return {row[field]: row for row in rows}


def test_default_timeline_has_five_twelve_hour_snapshots_and_approved_targets() -> None:
    timeline = _timeline()

    assert [row.scenario.scenario_id for row in timeline.snapshots] == [
        "timeline-test_01",
        "timeline-test_02",
        "timeline-test_03",
        "timeline-test_04",
        "timeline-test_05",
    ]
    assert [
        row.timestamp - timeline.snapshots[index - 1].timestamp
        for index, row in enumerate(timeline.snapshots)
        if index
    ] == [timedelta(hours=12)] * 4
    assert sum(len(row.cleared_incident_ids) for row in timeline.snapshots) == round(120 * 0.92)
    assert sum(len(row.new_incident_ids) for row in timeline.snapshots) == round(120 * 0.18)
    arrival_counts = [len(row.new_incident_ids) for row in timeline.snapshots[1:]]
    assert all(left >= right for left, right in zip(arrival_counts, arrival_counts[1:]))


@pytest.mark.parametrize("snapshots", [1, 10])
def test_snapshot_count_boundaries_and_zero_padding(snapshots: int) -> None:
    timeline = _timeline(
        snapshots=snapshots,
        incident_count=40,
        crew_count=80,
        assignment_rate=0.05,
        dual_tree_incidents=1,
    )

    assert len(timeline.snapshots) == snapshots
    assert [row.scenario.scenario_id for row in timeline.snapshots] == sorted(
        row.scenario.scenario_id for row in timeline.snapshots
    )
    assert timeline.snapshots[-1].scenario.scenario_id.endswith(f"_{snapshots:02d}")
    if snapshots == 1:
        assert not timeline.snapshots[0].new_incident_ids
        assert not timeline.snapshots[0].cleared_incident_ids
        assert len(timeline.snapshots[0].scenario.incidents) == 40


def test_every_written_snapshot_passes_application_validation(tmp_path: Path) -> None:
    timeline = _timeline(incident_count=80, crew_count=80, assignment_rate=0.10, dual_tree_incidents=1)
    paths = write_timeline(timeline, tmp_path)

    assert [path.name for path in paths] == [f"timeline-test_{index:02d}" for index in range(1, 6)]
    for path in paths:
        descriptor = ScenarioService(tmp_path, path.name).active_scenario()
        assert descriptor.validation_status == "valid"
        manifest = json.loads((path / "scenario.json").read_text(encoding="utf-8"))
        assert manifest["scenario_id"] == path.name
        assert "snapshot at 2026-" in manifest["description"]


def test_identical_seeds_produce_identical_timeline_data() -> None:
    first = _timeline(seed=19)
    second = _timeline(seed=19)

    assert first.summary() == second.summary()
    assert [snapshot.scenario for snapshot in first.snapshots] == [
        snapshot.scenario for snapshot in second.snapshots
    ]


def test_queue_conservation_stable_survivors_and_no_resurrection() -> None:
    timeline = _timeline()
    cleared_seen: set[str] = set()

    for previous, current in zip(timeline.snapshots, timeline.snapshots[1:]):
        previous_incidents = _rows_by_id(previous.scenario.incidents, "incident_id")
        current_incidents = _rows_by_id(current.scenario.incidents, "incident_id")
        assert len(current_incidents) == (
            len(previous_incidents)
            + len(current.new_incident_ids)
            - len(current.cleared_incident_ids)
        )
        assert not cleared_seen.intersection(current_incidents)
        stable_fields = (
            "region",
            "municipality",
            "feeder",
            "severity",
            "customers_out",
            "critical_facility",
            "hazard",
            "required_skill",
            "latitude",
            "longitude",
        )
        for incident_id in previous_incidents.keys() & current_incidents.keys():
            assert tuple(previous_incidents[incident_id][field] for field in stable_fields) == tuple(
                current_incidents[incident_id][field] for field in stable_fields
            )

        previous_assignments = _rows_by_id(previous.scenario.assignments, "assignment_id")
        current_assignments = _rows_by_id(current.scenario.assignments, "assignment_id")
        for assignment_id in previous_assignments.keys() & current_assignments.keys():
            assert previous_assignments[assignment_id] == current_assignments[assignment_id]
        cleared_seen.update(current.cleared_incident_ids)


def test_daily_incident_and_assignment_sequences_are_unique_across_midnight() -> None:
    timeline = _timeline(
        start_time=time(20, 0),
        snapshots=4,
        hours_apart=12,
        recovery_profile="severe",
        arrival_profile="persistent",
    )
    incident_ids = {
        row["incident_id"]
        for snapshot in timeline.snapshots
        for row in snapshot.scenario.incidents
    }
    assignment_ids = {
        row["assignment_id"]
        for snapshot in timeline.snapshots
        for row in snapshot.scenario.assignments
    }
    by_incident_day = defaultdict(set)
    for incident_id in incident_ids:
        _, day, sequence = incident_id.split("-")
        assert sequence not in by_incident_day[day]
        by_incident_day[day].add(sequence)
    by_assignment_day = defaultdict(set)
    for assignment_id in assignment_ids:
        _, day, sequence = assignment_id.split("-")
        assert sequence not in by_assignment_day[day]
        by_assignment_day[day].add(sequence)
    assert len(by_incident_day) >= 2


@pytest.mark.parametrize("profile,target", RECOVERY_PROFILES.items())
def test_predefined_recovery_profiles(profile: str, target: float) -> None:
    timeline = _timeline(recovery_profile=profile, arrival_profile="low")
    assert sum(len(row.cleared_incident_ids) for row in timeline.snapshots) == round(120 * target)


@pytest.mark.parametrize("profile,target", ARRIVAL_PROFILES.items())
def test_predefined_arrival_profiles(profile: str, target: float) -> None:
    timeline = _timeline(recovery_profile="severe", arrival_profile=profile)
    assert sum(len(row.new_incident_ids) for row in timeline.snapshots) == round(120 * target)


def test_custom_profiles_accept_direct_percentages() -> None:
    timeline = _timeline(
        recovery_profile="custom",
        recovery_target=0.63,
        arrival_profile="custom",
        new_incident_share=0.22,
    )
    assert sum(len(row.cleared_incident_ids) for row in timeline.snapshots) == round(120 * 0.63)
    assert sum(len(row.new_incident_ids) for row in timeline.snapshots) == round(120 * 0.22)


def test_incident_lifecycle_and_active_assignment_compatibility() -> None:
    timeline = _timeline(
        snapshots=5,
        hours_apart=1,
        assignment_rate=0.20,
        recovery_profile="severe",
        arrival_profile="low",
        seed=11,
    )
    observed_phases = {
        row["status"]
        for snapshot in timeline.snapshots
        for row in snapshot.scenario.incidents
        if row["status"] != "unassigned"
    }
    assert observed_phases == set(INCIDENT_PHASES)
    for snapshot in timeline.snapshots:
        incidents = _rows_by_id(snapshot.scenario.incidents, "incident_id")
        assert all(row["status"] == "active" for row in snapshot.scenario.assignments)
        assert all(
            incidents[row["incident_id"]]["status"] in INCIDENT_PHASES
            for row in snapshot.scenario.assignments
        )
        assert "active" not in {row["status"] for row in snapshot.scenario.incidents}


def test_crew_rotations_release_locations_and_reassignment_rules() -> None:
    timeline = _timeline(seed=19)
    assert any(row["status"] == "off_shift" for row in timeline.snapshots[0].scenario.crews)
    assert any(row["status"] == "available" for row in timeline.snapshots[0].scenario.crews)

    first = timeline.snapshots[0]
    second = timeline.snapshots[1]
    first_assignments = _rows_by_id(first.scenario.assignments, "assignment_id")
    first_incidents = _rows_by_id(first.scenario.incidents, "incident_id")
    second_assignments = _rows_by_id(second.scenario.assignments, "assignment_id")
    second_crews = _rows_by_id(second.scenario.crews, "crew_id")
    released = [row for key, row in first_assignments.items() if key not in second_assignments]
    assert released
    assert any(
        second_crews[row["crew_id"]]["current_location"]
        == first_incidents[row["incident_id"]]["municipality"]
        for row in released
    )

    for snapshot in timeline.snapshots:
        crew_counts = Counter(row["crew_id"] for row in snapshot.scenario.assignments)
        assert all(count == 1 for count in crew_counts.values())
        assert {row["status"] for row in snapshot.scenario.crews} <= {
            "available",
            "assigned",
            "off_shift",
        }
        assert all(float(row["shift_remaining_hours"]) <= 16 for row in snapshot.scenario.crews)


def test_later_assignments_preserve_regional_capability_and_pairing_rules() -> None:
    timeline = _timeline(
        incident_count=300,
        crew_count=250,
        assignment_rate=0.50,
        dual_tree_incidents=5,
        recovery_profile="severe",
        arrival_profile="persistent",
        seed=1,
    )
    observed_tree_pair = False
    observed_wire_response = False
    for snapshot in timeline.snapshots[1:]:
        incidents = _rows_by_id(snapshot.scenario.incidents, "incident_id")
        crews = _rows_by_id(snapshot.scenario.crews, "crew_id")
        new_assignments = [
            row
            for row in snapshot.scenario.assignments
            if row["assigned_at"] == snapshot.timestamp.isoformat()
        ]
        assignments_by_incident = defaultdict(list)
        for assignment in new_assignments:
            incident = incidents[assignment["incident_id"]]
            crew = crews[assignment["crew_id"]]
            crew_type = snapshot.scenario.crew_types[crew["crew_id"]]
            assert crew["home_region"] == incident["region"]
            if crew_type == "low_voltage":
                assert int(incident["customers_out"]) == 1
                assert incident["required_skill"] == "low_voltage"
            if crew_type == "line":
                assert int(incident["customers_out"]) >= 40
                assert incident["required_skill"] in {"line", "underground"}
            if incident["hazard"] in {"downed wire", "burning wire", "arcing wire"}:
                assert crew_type in {"lkp", "ww"}
                observed_wire_response = True
            assignments_by_incident[incident["incident_id"]].append(crew_type)
        for incident_id, crew_types in assignments_by_incident.items():
            if incidents[incident_id]["hazard"] == "tree on primary":
                assert sorted(crew_types) in (["mua", "tree"], ["cntr", "tree"])
                observed_tree_pair = True
    assert observed_tree_pair
    assert observed_wire_response


def test_tree_crew_can_finish_before_paired_repair() -> None:
    timeline = _timeline(
        incident_count=200,
        crew_count=140,
        assignment_rate=0.10,
        dual_tree_incidents=5,
        recovery_profile="severe",
        seed=7,
    )
    first_counts = Counter(row["incident_id"] for row in timeline.snapshots[0].scenario.assignments)
    paired = {incident_id for incident_id, count in first_counts.items() if count == 2}
    later_counts = Counter(row["incident_id"] for row in timeline.snapshots[1].scenario.assignments)
    assert any(later_counts[incident_id] == 1 for incident_id in paired)


def test_supporting_reference_data_and_topology_remain_stable() -> None:
    timeline = _timeline()
    first = timeline.snapshots[0].scenario
    for snapshot in timeline.snapshots[1:]:
        assert snapshot.scenario.historical_repairs == first.historical_repairs
        assert snapshot.scenario.critical_facilities == first.critical_facilities
        assert snapshot.scenario.topology == first.topology
        topology_feeders = {(row["region"], row["feeder"]) for row in snapshot.scenario.topology}
        assert {
            (row["region"], row["feeder"]) for row in snapshot.scenario.incidents
        }.issubset(topology_feeders)
        facility_keys = {
            (row["region"], row["feeder"])
            for row in snapshot.scenario.critical_facilities
        }
        assert all(
            row["critical_facility"] == "false"
            or (row["region"], row["feeder"]) in facility_keys
            for row in snapshot.scenario.incidents
        )


def test_snapshot_ages_etrs_shift_hours_and_travel_are_recalculated() -> None:
    timeline = _timeline()
    first = timeline.snapshots[0]
    second = timeline.snapshots[1]
    first_incidents = _rows_by_id(first.scenario.incidents, "incident_id")
    second_incidents = _rows_by_id(second.scenario.incidents, "incident_id")
    surviving = first_incidents.keys() & second_incidents.keys()
    assert all(
        int(second_incidents[incident_id]["age_minutes"])
        == int(first_incidents[incident_id]["age_minutes"]) + 12 * 60
        for incident_id in surviving
    )
    assert all(
        datetime.fromisoformat(row["etr"]).tzinfo is not None
        and datetime.fromisoformat(row["etr"]) >= second.timestamp
        for row in second.scenario.incidents
    )
    first_crews = _rows_by_id(first.scenario.crews, "crew_id")
    second_crews = _rows_by_id(second.scenario.crews, "crew_id")
    assert any(
        first_crews[crew_id]["travel_minutes_to_selected_incident"]
        != second_crews[crew_id]["travel_minutes_to_selected_incident"]
        for crew_id in first_crews
    )
    assert all(0 <= float(row["shift_remaining_hours"]) <= 16 for row in second.scenario.crews)


def test_protected_batch_refuses_any_existing_target_without_partial_output(tmp_path: Path) -> None:
    timeline = _timeline(incident_count=40, crew_count=80, assignment_rate=0.05, dual_tree_incidents=1)
    existing = tmp_path / "timeline-test_03"
    existing.mkdir()

    with pytest.raises(FileExistsError, match="timeline-test_03"):
        write_timeline(timeline, tmp_path)

    assert [path.name for path in tmp_path.iterdir()] == ["timeline-test_03"]


def test_generation_is_dry_run_until_write_is_called(tmp_path: Path) -> None:
    _timeline(incident_count=40, crew_count=80, assignment_rate=0.05, dual_tree_incidents=1)
    assert not tmp_path.exists() or not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"snapshots": 0}, "snapshots"),
        ({"snapshots": 11}, "snapshots"),
        ({"hours_apart": 0}, "hours_apart"),
        ({"recovery_profile": "custom"}, "recovery_target"),
        ({"arrival_profile": "custom"}, "new_incident_share"),
    ],
)
def test_invalid_timeline_configuration(overrides, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _timeline(**overrides)


def test_infeasible_configuration_has_actionable_guidance() -> None:
    with pytest.raises(ValueError, match="add crews, extend the timeline, or lower"):
        _timeline(
            incident_count=500,
            crew_count=10,
            assignment_rate=0,
            dual_tree_incidents=0,
            snapshots=2,
            hours_apart=1,
        )


def test_timezone_aware_timestamps_cross_daylight_saving_boundary() -> None:
    timeline = _timeline(
        start_date=date(2026, 11, 1),
        start_time=time(0, 0),
        snapshots=3,
        hours_apart=12,
        recovery_profile="severe",
        arrival_profile="low",
    )
    timestamps = [row.timestamp for row in timeline.snapshots]
    assert all(timestamp.tzinfo is not None and timestamp.utcoffset() is not None for timestamp in timestamps)
    assert timestamps[0].utcoffset() != timestamps[1].utcoffset()
    for snapshot in timeline.snapshots:
        assert all(row["updated_at"] == snapshot.timestamp.isoformat() for row in snapshot.scenario.weather)


def test_original_single_snapshot_generator_contract_remains_unchanged() -> None:
    original = generate_scenario(
        scenario_id="single-regression",
        start_date=date(2026, 8, 10),
        incident_count=80,
        crew_count=80,
        assignment_rate=0.10,
        dual_tree_incidents=1,
        critical_facilities_per_region=2,
        seed=7,
    )
    assert len(original.incidents) == 80
    assert len({row["incident_id"] for row in original.assignments}) == 8
    assert len(original.assignments) == 9
    assert {row["status"] for row in original.assignments} == {"active"}
    assert {row["status"] for row in original.incidents} == {"unassigned", "assigned"}


def test_noninteractive_cli_requires_scenario_id_and_custom_targets() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "generate_scenario_timeline.py"
    spec = importlib.util.spec_from_file_location("timeline_cli", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parser = module.build_parser()

    with pytest.raises(ValueError, match="scenario-id"):
        module.resolve_arguments(parser.parse_args(["--no-prompt"]))
    with pytest.raises(ValueError, match="recovery-target"):
        module.resolve_arguments(
            parser.parse_args(
                ["--scenario-id", "cli-test", "--recovery-profile", "custom", "--no-prompt"]
            )
        )


def test_interactive_prompt_retries_invalid_values(capsys) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "generate_scenario_timeline.py"
    spec = importlib.util.spec_from_file_location("timeline_cli_prompts", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    responses = iter(["eleven", "10"])

    value = module._prompt(
        "Number of snapshots",
        5,
        module._snapshot_count,
        input_fn=lambda _: next(responses),
    )

    assert value == 10
    assert "Invalid value" in capsys.readouterr().err
