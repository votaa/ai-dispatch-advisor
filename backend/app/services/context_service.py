from __future__ import annotations

from collections.abc import Callable
from typing import Any


class OperationalContextService:
    def __init__(
        self,
        *,
        weather_rows: Callable[[], list[dict[str, Any]]],
        critical_facility_rows: Callable[[], list[dict[str, Any]]],
        topology_rows: Callable[[], list[dict[str, Any]]],
    ) -> None:
        self._weather_rows = weather_rows
        self._critical_facility_rows = critical_facility_rows
        self._topology_rows = topology_rows

    def weather(self) -> list[dict[str, Any]]:
        return self._weather_rows()

    def critical_facilities(self) -> list[dict[str, Any]]:
        return self._critical_facility_rows()

    def topology(self) -> list[dict[str, Any]]:
        return self._topology_rows()
