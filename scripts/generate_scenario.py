#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.scenario_generator import (  # noqa: E402
    ASSIGNMENT_HEADERS,
    CRITICAL_FACILITY_HEADERS,
    CREW_HEADERS,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_START_DAY_LOCATION_RATE,
    HISTORICAL_REPAIR_HEADERS,
    INCIDENT_HEADERS,
    TOPOLOGY_HEADERS,
    WEATHER_HEADERS,
    generate_scenario,
    write_scenario,
)


def _csv_preview(headers: list[str], rows: list[dict], limit: int) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows[:limit])
    return buffer.getvalue().rstrip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate protected synthetic AI Dispatch Advisor scenario data.")
    parser.add_argument("--scenario-id", required=True, help="Lowercase scenario directory name")
    parser.add_argument("--start-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument("--incidents", type=int, default=2000)
    parser.add_argument("--crews", type=int, default=500)
    parser.add_argument("--assignment-rate", type=float, default=0.05)
    parser.add_argument("--dual-tree-incidents", type=int, default=5)
    parser.add_argument(
        "--critical-facilities-per-region",
        type=int,
        help="Fixed facility count for each region; omit to use 4 percent of each region's incident count",
    )
    parser.add_argument("--seed", type=int, default=20260810)
    parser.add_argument(
        "--start-day-location-rate",
        type=float,
        default=DEFAULT_START_DAY_LOCATION_RATE,
        help="Share of crews located at their mapped home facility; other crews use a prior-job municipality",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--preview-rows", type=int, default=5)
    parser.add_argument("--write", action="store_true", help="Write a new scenario folder; otherwise run as a dry-run preview")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    scenario = generate_scenario(
        scenario_id=args.scenario_id,
        start_date=args.start_date,
        end_date=args.end_date,
        incident_count=args.incidents,
        crew_count=args.crews,
        assignment_rate=args.assignment_rate,
        dual_tree_incidents=args.dual_tree_incidents,
        critical_facilities_per_region=args.critical_facilities_per_region,
        seed=args.seed,
        start_day_location_rate=args.start_day_location_rate,
    )
    print(json.dumps(scenario.summary(), indent=2))
    print("\nCrews.csv preview")
    print(_csv_preview(CREW_HEADERS, scenario.crews, args.preview_rows))
    print("\nPendingIncidents.csv preview")
    print(_csv_preview(INCIDENT_HEADERS, scenario.incidents, args.preview_rows))
    print("\nAssignments.csv preview")
    print(_csv_preview(ASSIGNMENT_HEADERS, scenario.assignments, args.preview_rows))
    print("\nWeather.csv preview")
    print(_csv_preview(WEATHER_HEADERS, scenario.weather, args.preview_rows))
    print("\nCriticalFacilities.csv preview")
    print(_csv_preview(CRITICAL_FACILITY_HEADERS, scenario.critical_facilities, args.preview_rows))
    print("\nTopology.csv preview")
    print(_csv_preview(TOPOLOGY_HEADERS, scenario.topology, args.preview_rows))
    print("\nHistoricalRepairs.csv preview")
    print(_csv_preview(HISTORICAL_REPAIR_HEADERS, scenario.historical_repairs, args.preview_rows))
    if args.write:
        print(f"\nCreated {write_scenario(scenario, args.output_root)}")
    else:
        print("\nDry run only; no files were written. Add --write after reviewing the preview.")


if __name__ == "__main__":
    main()
