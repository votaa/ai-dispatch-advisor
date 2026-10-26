#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.scenario_generator import (  # noqa: E402
    ASSIGNMENT_HEADERS,
    CREW_HEADERS,
    DEFAULT_ETR_MIX,
    DEFAULT_OUTPUT_ROOT,
    INCIDENT_HEADERS,
    LOCAL_TIMEZONE,
    TIMELINE_INCIDENT_HEADERS,
    parse_etr_mix,
)
from app.scenario_timeline_generator import (  # noqa: E402
    generate_timeline,
    parse_assessing_conversion,
    parse_assessing_conversion_overrides,
    write_timeline,
)


def _time(value: str) -> time:
    parsed = time.fromisoformat(value)
    if parsed.second or parsed.microsecond:
        raise argparse.ArgumentTypeError("start time must use HH:MM")
    return parsed


def _share(value: str | float) -> float:
    number = float(value)
    if number > 1:
        number /= 100
    if not 0 <= number <= 1:
        raise argparse.ArgumentTypeError("percentage must be between 0 and 100")
    return number


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be a positive whole number")
    return number


def _nonnegative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("value must be zero or a positive whole number")
    return number


def _snapshot_count(value: str) -> int:
    number = int(value)
    if not 1 <= number <= 10:
        raise argparse.ArgumentTypeError("snapshots must be between 1 and 10")
    return number


def _etr_mix(value: str) -> str:
    parse_etr_mix(value)
    return value


def _conversion(value: str) -> str:
    parse_assessing_conversion(value)
    return value


def _decay(value: str) -> float:
    number = float(value)
    if not 0 < number <= 1:
        raise argparse.ArgumentTypeError("decay must be greater than 0 and at most 1")
    return number


def _choice(*choices: str) -> Callable[[str], str]:
    def convert(value: str) -> str:
        if value not in choices:
            raise argparse.ArgumentTypeError(f"choose one of: {', '.join(choices)}")
        return value

    return convert


def _csv_preview(headers: list[str], rows: list[dict[str, Any]], limit: int) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows[:limit])
    return buffer.getvalue().rstrip()


def _prompt(
    label: str,
    default: Any,
    converter: Callable[[str], Any] = str,
    *,
    input_fn: Callable[[str], str] = input,
) -> Any:
    while True:
        shown = default.isoformat() if hasattr(default, "isoformat") else str(default)
        raw = input_fn(f"{label} [{shown}]: ").strip()
        if not raw:
            return default
        try:
            return converter(raw)
        except (TypeError, ValueError, argparse.ArgumentTypeError) as exc:
            print(f"Invalid value: {exc}", file=sys.stderr)


def _prompt_optional_int(
    label: str,
    value: int | None,
    *,
    input_fn: Callable[[str], str] = input,
) -> int | None:
    default = str(value) if value is not None else "automatic"
    while True:
        raw = input_fn(f"{label} [{default}]: ").strip()
        if not raw or raw.lower() in {"automatic", "auto", "none"}:
            return value
        try:
            return _positive_int(raw)
        except (ValueError, argparse.ArgumentTypeError) as exc:
            print(f"Invalid value: {exc}", file=sys.stderr)


def _prompt_yes_no(label: str, default: bool, *, input_fn: Callable[[str], str] = input) -> bool:
    shown = "yes" if default else "no"
    while True:
        raw = input_fn(f"{label} [{shown}]: ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Invalid value: enter yes or no", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate protected, sequential synthetic AI Dispatch Advisor storm snapshots."
    )
    parser.add_argument("--scenario-id", help="Lowercase base name for zero-padded sibling folders")
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument(
        "--etr-mix",
        help=f"Initial ETR percentages (default: {DEFAULT_ETR_MIX})",
    )
    parser.add_argument("--assessing-conversion", help="Repeat conversion rule, such as 10%%@24h")
    parser.add_argument(
        "--assessing-conversion-overrides",
        help="Destination-step overrides, such as 2=10%%@12h,4=20%%@24h",
    )
    parser.add_argument("--start-time", type=_time)
    parser.add_argument("--snapshots", type=_snapshot_count)
    parser.add_argument("--hours-apart", type=_positive_int)
    parser.add_argument("--incidents", type=_positive_int)
    parser.add_argument("--crews", type=_positive_int)
    parser.add_argument("--assignment-rate", type=_share)
    parser.add_argument("--dual-tree-incidents", type=_nonnegative_int)
    parser.add_argument("--critical-facilities-per-region", type=_positive_int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--start-day-location-rate", type=_share)
    parser.add_argument("--recovery-profile", choices=("fast", "balanced", "severe", "custom"))
    parser.add_argument("--recovery-target", type=_share)
    parser.add_argument("--arrival-profile", choices=("low", "moderate", "persistent", "custom"))
    parser.add_argument("--new-incident-share", type=_share)
    parser.add_argument("--arrival-decay", type=_decay)
    parser.add_argument("--repair-duration-variation", type=_share)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--preview-rows", type=_nonnegative_int)
    parser.add_argument("--write", action="store_true", help="Publish the complete validated batch")
    parser.add_argument("--no-prompt", action="store_true", help="Use defaults for omitted settings")
    return parser


def resolve_arguments(
    args: argparse.Namespace,
    *,
    input_fn: Callable[[str], str] = input,
) -> dict[str, Any]:
    defaults = {
        "scenario_id": "august-storm-preview",
        "start_date": date.today(),
        "start_time": time(8, 0),
        "snapshots": 5,
        "hours_apart": 12,
        "incidents": 2000,
        "crews": 500,
        "assignment_rate": 0.05,
        "dual_tree_incidents": 5,
        "critical_facilities_per_region": None,
        "seed": 20260810,
        "start_day_location_rate": 0.35,
        "recovery_profile": "fast",
        "arrival_profile": "moderate",
        "arrival_decay": 0.60,
        "repair_duration_variation": 0.25,
        "output_root": DEFAULT_OUTPUT_ROOT,
        "preview_rows": 5,
    }
    if args.no_prompt and not args.scenario_id:
        raise ValueError("--scenario-id is required with --no-prompt")

    def resolved(name: str, label: str, converter: Callable[[str], Any] = str) -> Any:
        current = getattr(args, name)
        if current is not None:
            return current
        default = defaults[name]
        if args.no_prompt:
            return default
        return _prompt(label, default, converter, input_fn=input_fn)

    scenario_id = resolved("scenario_id", "Scenario ID")
    start_date = resolved("start_date", "Overall incident arrival start date", date.fromisoformat)
    start_time = resolved("start_time", "Snapshot 1 local time", _time)
    snapshots = resolved("snapshots", "Number of snapshots", _snapshot_count)
    hours_apart = resolved("hours_apart", "Hours between snapshots", _positive_int)
    first_cutoff = datetime.combine(start_date, start_time, LOCAL_TIMEZONE)
    default_end_date = (
        first_cutoff.astimezone(timezone.utc) + timedelta(hours=(snapshots - 1) * hours_apart)
    ).astimezone(LOCAL_TIMEZONE).date()
    if args.end_date is not None:
        end_date = args.end_date
    elif args.no_prompt:
        end_date = default_end_date
    else:
        end_date = _prompt("Overall incident arrival end date", default_end_date, date.fromisoformat, input_fn=input_fn)
    etr_mix = args.etr_mix if args.etr_mix is not None else (
        DEFAULT_ETR_MIX if args.no_prompt else _prompt("Initial ETR mix", DEFAULT_ETR_MIX, _etr_mix, input_fn=input_fn)
    )
    conversion = args.assessing_conversion
    overrides = args.assessing_conversion_overrides
    if conversion is None and not args.no_prompt and _prompt_yes_no(
        "Convert continuing Assessing Conditions incidents at each advance", False, input_fn=input_fn
    ):
        conversion = _prompt("Baseline conversion rule", "10%@24h", _conversion, input_fn=input_fn)
    if conversion and overrides is None and not args.no_prompt and _prompt_yes_no(
        "Set step-specific conversion overrides", False, input_fn=input_fn
    ):
        overrides = _prompt("Conversion overrides", "2=10%@12h", str, input_fn=input_fn)
    if overrides:
        parse_assessing_conversion_overrides(overrides, snapshots)
    incidents = resolved("incidents", "Initial incidents", _positive_int)
    crews = resolved("crews", "Crews", _positive_int)
    assignment_rate = resolved("assignment_rate", "Initial assignment percentage", _share)
    dual_tree = resolved("dual_tree_incidents", "Dual repair/TREE incidents", _nonnegative_int)
    if args.critical_facilities_per_region is not None or args.no_prompt:
        facilities = args.critical_facilities_per_region
    else:
        facilities = _prompt_optional_int(
            "Critical facilities per region", None, input_fn=input_fn
        )
    seed = resolved("seed", "Random seed", int)
    location_rate = resolved("start_day_location_rate", "Start-day facility percentage", _share)
    recovery_profile = resolved(
        "recovery_profile", "Recovery profile", _choice("fast", "balanced", "severe", "custom")
    )
    recovery_target = args.recovery_target
    if recovery_profile == "custom" and recovery_target is None:
        if args.no_prompt:
            raise ValueError("--recovery-target is required with --recovery-profile custom")
        recovery_target = _prompt("Final clearance percentage", 0.92, _share, input_fn=input_fn)
    arrival_profile = resolved(
        "arrival_profile", "Arrival profile", _choice("low", "moderate", "persistent", "custom")
    )
    new_incident_share = args.new_incident_share
    if arrival_profile == "custom" and new_incident_share is None:
        if args.no_prompt:
            raise ValueError("--new-incident-share is required with --arrival-profile custom")
        new_incident_share = _prompt("Total new-incident percentage", 0.18, _share, input_fn=input_fn)
    arrival_decay = resolved("arrival_decay", "Arrival decay per 12 hours", _decay)
    duration_variation = resolved(
        "repair_duration_variation", "Repair-duration variation percentage", _share
    )
    output_root = resolved("output_root", "Output root", Path)
    preview_rows = resolved("preview_rows", "Preview rows", _nonnegative_int)
    write = args.write if args.no_prompt or args.write else _prompt_yes_no(
        "Write the validated snapshot folders", False, input_fn=input_fn
    )
    return {
        "scenario_id": scenario_id,
        "start_date": start_date,
        "end_date": end_date,
        "etr_mix": etr_mix,
        "assessing_conversion": conversion,
        "assessing_conversion_overrides": overrides,
        "start_time": start_time,
        "snapshots": snapshots,
        "hours_apart": hours_apart,
        "incident_count": incidents,
        "crew_count": crews,
        "assignment_rate": assignment_rate,
        "dual_tree_incidents": dual_tree,
        "critical_facilities_per_region": facilities,
        "seed": seed,
        "start_day_location_rate": location_rate,
        "recovery_profile": recovery_profile,
        "recovery_target": recovery_target,
        "arrival_profile": arrival_profile,
        "new_incident_share": new_incident_share,
        "arrival_decay": arrival_decay,
        "repair_duration_variation": duration_variation,
        "output_root": output_root,
        "preview_rows": preview_rows,
        "write": write,
    }


def _print_preview(label: str, snapshot: Any, limit: int) -> None:
    print(f"\n{label}: {snapshot.scenario.scenario_id} at {snapshot.timestamp.isoformat()}")
    print("PendingIncidents.csv")
    headers = (
        TIMELINE_INCIDENT_HEADERS if snapshot.scenario.temporal else INCIDENT_HEADERS
    )
    print(_csv_preview(headers, snapshot.scenario.incidents, limit))
    print("\nCrews.csv")
    print(_csv_preview(CREW_HEADERS, snapshot.scenario.crews, limit))
    print("\nAssignments.csv")
    print(_csv_preview(ASSIGNMENT_HEADERS, snapshot.scenario.assignments, limit))


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        settings = resolve_arguments(args)
        output_root = settings.pop("output_root")
        preview_rows = settings.pop("preview_rows")
        should_write = settings.pop("write")
        timeline = generate_timeline(**settings)
        print(json.dumps(timeline.summary(evaluation_at=datetime.now(timezone.utc)), indent=2))
        _print_preview("First snapshot preview", timeline.snapshots[0], preview_rows)
        if len(timeline.snapshots) > 1:
            _print_preview("Final snapshot preview", timeline.snapshots[-1], preview_rows)
        if should_write:
            paths = write_timeline(timeline, output_root)
            print("\nCreated validated timeline folders:")
            for path in paths:
                print(path)
        else:
            print("\nDry run only; no files were written. Add --write after reviewing the preview.")
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
