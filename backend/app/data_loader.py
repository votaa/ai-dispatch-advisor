from __future__ import annotations

import csv
import os
from functools import lru_cache
from pathlib import Path
from threading import RLock
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIO = os.getenv("AIDA_DEMO_SCENARIO", "base")
DATA_ROOT = Path(os.getenv("AIDA_DATA_ROOT", REPO_ROOT / "data" / "scenarios"))
_active_scenario_id = DEFAULT_SCENARIO
_active_scenario_lock = RLock()


def get_active_scenario() -> str:
    with _active_scenario_lock:
        return _active_scenario_id


def set_active_scenario(scenario_id: str) -> None:
    global _active_scenario_id
    with _active_scenario_lock:
        _active_scenario_id = scenario_id
        _load_csv.cache_clear()


def _scenario_dir(scenario_id: str) -> Path:
    return DATA_ROOT / scenario_id


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


def _coerce_field(name: str, value: str) -> Any:
    if name.endswith("_id") or name == "feeder":
        return value or None
    return _coerce(value)


@lru_cache(maxsize=32)
def _load_csv(scenario_id: str, name: str) -> list[dict[str, Any]]:
    path = _scenario_dir(scenario_id) / name
    if not path.exists():
        raise FileNotFoundError(f"Demo data file not found: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [{key: _coerce_field(key, value) for key, value in row.items()} for row in reader]


def load_csv(name: str) -> list[dict[str, Any]]:
    return _load_csv(get_active_scenario(), name)


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
    _load_csv.cache_clear()
