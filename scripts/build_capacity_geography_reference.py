#!/usr/bin/env python3
"""Build the static incident-coordinate reference from reviewed source exports.

The script is intentionally offline. Download the source files separately, review
them, and pass their paths here. Runtime scenario generation consumes only the
versioned CSV and never geocodes or guesses coordinates.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CUSTOMERS = REPO_ROOT / "data/reference/pseg-long-island/customers-served.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data/generator-lookups/LongIslandCapacityGeography.csv"
LONG_ISLAND_BOUNDS = (40.45, 41.35, -74.15, -71.75)
OUTPUT_HEADERS = [
    "reference_id",
    "county",
    "township",
    "village",
    "latitude",
    "longitude",
    "coordinate_source",
    "source_reference",
    "precision",
]


# These source labels do not match a current Census place or exact GNIS feature.
# Each replacement stays within the named locality and records the lower precision.
OVERRIDES: dict[tuple[str, str, str], tuple[float, float, str, str, str]] = {
    ("Nassau", "Hempstead", "Silver Point County Park"): (
        40.5880556, -73.7475, "USGS GNIS", "feature:2075812", "named_feature_point"
    ),
    ("Nassau", "Oyster Bay", "Centre Island Town Park"): (
        40.9128761, -73.5326234, "USGS GNIS", "feature:946330", "named_feature_point"
    ),
    ("Nassau", "Oyster Bay", "Oyster Bay Hamlet"): (
        40.868057, -73.531053, "US Census Bureau 2025 Gazetteer", "GEOID:3655992", "internal_point"
    ),
    ("Nassau", "Oyster Bay", "Tobay"): (
        40.6059352, -73.4451247, "USGS GNIS", "feature:967584", "named_feature_point"
    ),
    ("Suffolk", "Babylon", "Robert Moses Pk"): (
        40.6264151, -73.244326, "OpenStreetMap Nominatim", "relation:6442393", "representative_point"
    ),
    ("Suffolk", "Brookhaven", "Barrett Beach"): (
        40.6723214, -73.0409435, "OpenStreetMap Nominatim", "node:357546866", "named_feature_point"
    ),
    ("Suffolk", "Brookhaven", "Fire Island National Seashore"): (
        40.7084252, -72.9513976, "OpenStreetMap Nominatim", "relation:11132469", "representative_point"
    ),
    ("Suffolk", "Brookhaven", "Oakleyville"): (
        40.654186, -73.116602, "NPS community-order interpolation", "Oakleyville between Point o'Woods and Sailors Haven", "locality_estimate"
    ),
    ("Suffolk", "Brookhaven", "Ocean Ridge"): (
        40.6868048, -72.9991019, "OpenStreetMap Nominatim", "way:93628010", "representative_point"
    ),
    ("Suffolk", "Brookhaven", "Sailors Haven"): (
        40.656884, -73.104475, "National Park Service", "Sailors Haven Visitor Center", "named_feature_point"
    ),
    ("Suffolk", "Brookhaven", "Setauket-East Setauket"): (
        40.9306822, -73.1018326, "USGS GNIS", "feature:2390276", "historical_census_internal_point"
    ),
    ("Suffolk", "Brookhaven", "Watch Hill"): (
        40.6898212, -72.9892749, "OpenStreetMap Nominatim", "node:158872591", "named_feature_point"
    ),
    ("Suffolk", "East Hampton", "East Hampton Village"): (
        40.951543, -72.196094, "US Census Bureau 2025 Gazetteer", "GEOID:3622183", "internal_point"
    ),
    ("Suffolk", "East Hampton", "North West Harbor"): (
        41.013774, -72.220394, "US Census Bureau 2025 Gazetteer", "GEOID:3653852", "internal_point"
    ),
    ("Suffolk", "Islip", "Corneille Estates"): (
        40.6451, -73.1608, "NPS community-order interpolation", "Corneille Estates between Ocean Beach and Robbins Rest", "locality_estimate"
    ),
    ("Suffolk", "Islip", "Dunewood"): (
        40.6419256, -73.1801898, "OpenStreetMap Nominatim", "node:6737861694", "named_feature_point"
    ),
    ("Suffolk", "Islip", "Fairhaven"): (
        40.6392666, -73.1842821, "USGS GNIS", "feature:949800 (Fair Harbor)", "approved_alias_point"
    ),
    ("Suffolk", "Islip", "Us Coast Guard Sta"): (
        40.6253044, -73.2580351, "OpenStreetMap Nominatim", "relation:6442392", "representative_point"
    ),
    ("Suffolk", "Southampton", "Shinnecock Indian Res"): (
        40.8737616, -72.4309699, "USGS GNIS", "feature:979494 (Shinnecock Reservation)", "approved_alias_point"
    ),
    ("Suffolk", "Southampton", "Southampton Village"): (
        40.876617, -72.403089, "US Census Bureau 2025 Gazetteer", "GEOID:3668462", "internal_point"
    ),
    ("Suffolk", "Southampton", "Westhampton Dunes"): (
        40.77877, -72.706733, "US Census Bureau 2025 Gazetteer", "GEOID:3680186 (West Hampton Dunes)", "approved_alias_point"
    ),
}


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def census_key(name: str) -> str:
    key = normalized(name)
    for suffix in (" cdp", " village", " city", " town"):
        if key.endswith(suffix):
            return key[: -len(suffix)]
    return key


def in_bounds(latitude: float, longitude: float) -> bool:
    south, north, west, east = LONG_ISLAND_BOUNDS
    return south <= latitude <= north and west <= longitude <= east


def load_census(path: Path) -> dict[str, list[dict[str, str]]]:
    by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="|"):
            latitude = float(row["INTPTLAT"])
            longitude = float(row["INTPTLONG"])
            if row["USPS"] == "NY" and in_bounds(latitude, longitude):
                by_name[census_key(row["NAME"])].append(row)
    return dict(by_name)


def load_gnis(path: Path) -> dict[tuple[str, str], list[dict[str, str]]]:
    by_name: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="|"):
            if row["state_name"] != "New York" or not row["prim_lat_dec"]:
                continue
            latitude = float(row["prim_lat_dec"])
            longitude = float(row["prim_long_dec"])
            if in_bounds(latitude, longitude):
                by_name[(normalized(row["county_name"]), normalized(row["feature_name"]))].append(row)
    return dict(by_name)


def choose_gnis(rows: list[dict[str, str]]) -> dict[str, str] | None:
    populated = [row for row in rows if row["feature_class"] == "Populated Place"]
    if len(populated) == 1:
        return populated[0]
    return rows[0] if len(rows) == 1 else None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(customers_path: Path, census_path: Path, gnis_path: Path) -> list[dict[str, Any]]:
    census = load_census(census_path)
    gnis = load_gnis(gnis_path)
    output: list[dict[str, Any]] = []
    unresolved: list[str] = []
    with customers_path.open(encoding="utf-8", newline="") as handle:
        customers = list(csv.DictReader(handle))
    for row in customers:
        identity = (row["county"], row["township"], row["village"])
        if identity in OVERRIDES:
            latitude, longitude, source, source_reference, precision = OVERRIDES[identity]
        else:
            census_rows = census.get(normalized(row["village"]), [])
            if len(census_rows) == 1:
                match = census_rows[0]
                latitude = float(match["INTPTLAT"])
                longitude = float(match["INTPTLONG"])
                source = "US Census Bureau 2025 Gazetteer"
                source_reference = f"GEOID:{match['GEOID']}"
                precision = "internal_point"
            else:
                gnis_rows = gnis.get((normalized(row["county"]), normalized(row["village"])), [])
                match = choose_gnis(gnis_rows)
                if match is None:
                    unresolved.append(" / ".join(identity))
                    continue
                latitude = float(match["prim_lat_dec"])
                longitude = float(match["prim_long_dec"])
                source = "USGS GNIS Domestic Names 2026-08-28"
                source_reference = f"feature:{match['feature_id']}"
                precision = "named_feature_point"
        output.append(
            {
                "reference_id": row["reference_id"],
                "county": row["county"],
                "township": row["township"],
                "village": row["village"],
                "latitude": f"{latitude:.7f}".rstrip("0").rstrip("."),
                "longitude": f"{longitude:.7f}".rstrip("0").rstrip("."),
                "coordinate_source": source,
                "source_reference": source_reference,
                "precision": precision,
            }
        )
    if unresolved:
        raise ValueError("Unresolved capacity geographies: " + ", ".join(unresolved))
    if len(output) != len(customers):
        raise ValueError(f"Coordinate coverage mismatch: {len(output)} != {len(customers)}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--customers", type=Path, default=DEFAULT_CUSTOMERS)
    parser.add_argument("--census", type=Path, required=True)
    parser.add_argument("--gnis", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rows = build(args.customers, args.census, args.gnis)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_HEADERS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    source_counts = Counter(row["coordinate_source"] for row in rows)
    precision_counts = Counter(row["precision"] for row in rows)
    manifest = {
        "schema_version": "1.0",
        "dataset_id": "long-island-capacity-geography",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact": {"file_name": args.output.name, "sha256": sha256(args.output)},
        "counts": {"geographies": len(rows), "sources": dict(sorted(source_counts.items())), "precision": dict(sorted(precision_counts.items()))},
        "sources": [
            {"name": "U.S. Census Bureau 2025 Gazetteer Files", "url": "https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.2025.html"},
            {"name": "USGS GNIS Domestic Names", "url": "https://www.usgs.gov/us-board-on-geographic-names/download-gnis-data"},
            {"name": "OpenStreetMap Nominatim", "url": "https://nominatim.openstreetmap.org/"},
            {"name": "National Park Service Fire Island National Seashore", "url": "https://www.nps.gov/fiis/"},
        ],
        "limitations": [
            "Coordinates are representative planning points, not outage equipment, customer, or live GPS positions.",
            "Oakleyville and Corneille Estates use locality estimates interpolated from documented neighboring communities because no exact Census, GNIS, or OpenStreetMap named feature was available.",
        ],
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {args.output}")
    print(f"Wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()
