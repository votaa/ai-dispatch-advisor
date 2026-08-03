from __future__ import annotations

import csv
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIO = os.getenv("AIDA_DEMO_SCENARIO", "base")
DATA_ROOT = Path(os.getenv("AIDA_DATA_ROOT", REPO_ROOT / "data" / "scenarios"))


def _scenario_dir() -> Path:
    return DATA_ROOT / DEFAULT_SCENARIO


def _coerce(value: str) -> Any:
    if value == "":
        return None
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


@lru_cache(maxsize=32)
def load_csv(name: str) -> list[dict[str, Any]]:
    path = _scenario_dir() / name
    if not path.exists():
        raise FileNotFoundError(f"Demo data file not found: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [{key: _coerce(value) for key, value in row.items()} for row in reader]


def incidents() -> list[dict[str, Any]]:
    return load_csv("PendingIncidents.csv")


def crews() -> list[dict[str, Any]]:
    return load_csv("Crews.csv")


def assignments() -> list[dict[str, Any]]:
    return load_csv("Assignments.csv")


def weather() -> list[dict[str, Any]]:
    return load_csv("Weather.csv")


def critical_facilities() -> list[dict[str, Any]]:
    return load_csv("CriticalFacilities.csv")


def topology() -> list[dict[str, Any]]:
    return load_csv("Topology.csv")


def historical_repairs() -> list[dict[str, Any]]:
    return load_csv("HistoricalRepairs.csv")


def clear_cache() -> None:
    load_csv.cache_clear()

