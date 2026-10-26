#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import date, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.scenario_generator import (  # noqa: E402
    ASSIGNMENT_HEADERS,
    CRITICAL_FACILITY_HEADERS,
    CREW_HEADERS,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_ETR_MIX,
    DEFAULT_START_DAY_LOCATION_RATE,
    HISTORICAL_REPAIR_HEADERS,
    INCIDENT_HEADERS,
    TEMPORAL_INCIDENT_HEADERS,
    TOPOLOGY_HEADERS,
    WEATHER_HEADERS,
    COPILOT_DEMO_SCENARIO_ID,
    COPILOT_DEMO_SEED,
    generate_copilot_demo_scenario,
    generate_scenario,
    write_scenario,
)
from app.geography import GeographyRegistry, TravelEstimateService  # noqa: E402


def _csv_preview(headers: list[str], rows: list[dict], limit: int) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows[:limit])
    return buffer.getvalue().rstrip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate protected synthetic AI Dispatch Advisor scenario data.")
    parser.add_argument("--scenario-id", required=True, help="Lowercase scenario directory name")
    parser.add_argument(
        "--preset",
        choices=("standard", "copilot-demo"),
        default="standard",
        help="Use the standard configurable generator or the bounded POC-002 Copilot fixture",
    )
    parser.add_argument("--start-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument(
        "--as-of-at",
        type=datetime.fromisoformat,
        help="Aware RFC 3339 cutoff for a temporal single snapshot, such as 2026-09-29T18:00:00-04:00",
    )
    parser.add_argument(
        "--etr-mix",
        help=f"Initial ETR percentages, such as 8h=25,24h=25,48h=25,null=25 (default with --as-of-at: {DEFAULT_ETR_MIX})",
    )
    parser.add_argument("--incidents", type=int, default=2000)
    parser.add_argument("--crews", type=int, default=500)
    parser.add_argument("--assignment-rate", type=float, default=0.05)
    parser.add_argument("--dual-tree-incidents", type=int, default=5)
    parser.add_argument(
        "--critical-facilities-per-region",
        type=int,
        help="Fixed facility count for each region; omit to use 4 percent of each region's incident count",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Deterministic seed; defaults to the selected preset's stable seed",
    )
    parser.add_argument(
        "--start-day-location-rate",
        type=float,
        default=DEFAULT_START_DAY_LOCATION_RATE,
        help="Share of crews located at their mapped home facility; other crews use a prior-job municipality",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--geography-coverage-target",
        type=int,
        help=(
            "Minimum distinct approved leaf geographies; generation expands beyond "
            "this target when more customer capacity is required"
        ),
    )
    parser.add_argument(
        "--customers-out-target",
        type=int,
        help="Exact scenario-wide synthetic customers-out total to preserve during allocation",
    )
    parser.add_argument("--preview-rows", type=int, default=5)
    parser.add_argument("--write", action="store_true", help="Write a new scenario folder; otherwise run as a dry-run preview")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.preset == "copilot-demo":
        if args.as_of_at is not None or args.etr_mix is not None:
            raise SystemExit("Temporal options are supported by the standard preset only")
        if args.scenario_id != COPILOT_DEMO_SCENARIO_ID:
            raise SystemExit(
                "The copilot-demo preset requires --scenario-id "
                f"{COPILOT_DEMO_SCENARIO_ID}"
            )
        scenario = generate_copilot_demo_scenario(
            scenario_id=args.scenario_id,
            start_date=args.start_date,
            seed=args.seed if args.seed is not None else COPILOT_DEMO_SEED,
        )
    else:
        scenario = generate_scenario(
            scenario_id=args.scenario_id,
            start_date=args.start_date,
            end_date=args.end_date,
            incident_count=args.incidents,
            crew_count=args.crews,
            assignment_rate=args.assignment_rate,
            dual_tree_incidents=args.dual_tree_incidents,
            critical_facilities_per_region=args.critical_facilities_per_region,
            seed=args.seed if args.seed is not None else 20260810,
            start_day_location_rate=args.start_day_location_rate,
            geography_coverage_target=args.geography_coverage_target,
            customer_out_target=args.customers_out_target,
            as_of_at=args.as_of_at,
            etr_mix=args.etr_mix,
        )
    print(f"Preset: {args.preset}")
    print(json.dumps(scenario.summary(), indent=2))
    print("\nCrews.csv preview")
    print(_csv_preview(CREW_HEADERS, scenario.crews, args.preview_rows))
    print("\nPendingIncidents.csv preview")
    print(_csv_preview(TEMPORAL_INCIDENT_HEADERS if scenario.temporal else INCIDENT_HEADERS, scenario.incidents, args.preview_rows))
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
    if args.preset == "copilot-demo":
        registry = GeographyRegistry.from_csv()
        travel_estimates = TravelEstimateService(registry)
        geography_rows = []
        for incident in scenario.incidents[: args.preview_rows]:
            location = registry.require(incident["municipality"])
            geography_rows.append(
                {
                    "incident_id": incident["incident_id"],
                    "county": location.county,
                    "township": location.township,
                    "village": location.village,
                }
            )
        print("\nGeography registry preview")
        print(
            _csv_preview(
                ["incident_id", "county", "township", "village"],
                geography_rows,
                args.preview_rows,
            )
        )
        anchor = next(
            incident
            for incident in scenario.incidents
            if incident["municipality"] == "Arverne"
        )
        travel_rows = []
        for crew in scenario.crews[: args.preview_rows]:
            estimate = travel_estimates.estimate(
                origin_name=crew["current_location"],
                destination_name=anchor["municipality"],
                destination_latitude=anchor["latitude"],
                destination_longitude=anchor["longitude"],
            )
            travel_rows.append(
                {
                    "crew_id": crew["crew_id"],
                    "origin": estimate.origin if estimate else "unavailable",
                    "destination": estimate.destination if estimate else "unavailable",
                    "road_miles": estimate.estimated_road_miles if estimate else "",
                    "travel_minutes": estimate.estimated_travel_minutes if estimate else "",
                }
            )
        print("\nTravel estimate preview for Arverne incident")
        print(
            _csv_preview(
                ["crew_id", "origin", "destination", "road_miles", "travel_minutes"],
                travel_rows,
                args.preview_rows,
            )
        )
    if args.write:
        print(f"\nCreated {write_scenario(scenario, args.output_root)}")
    else:
        print("\nDry run only; no files were written. Add --write after reviewing the preview.")


if __name__ == "__main__":
    main()
