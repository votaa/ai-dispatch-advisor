from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..domain.models import Assignment


class AssignmentService:
    def __init__(
        self,
        *,
        active_scenario_id: Callable[[], str],
        baseline_assignments: Callable[[], list[dict[str, Any]]],
        accepted_assignments: Callable[[str], list[dict[str, Any]]],
    ) -> None:
        self._active_scenario_id = active_scenario_id
        self._baseline_assignments = baseline_assignments
        self._accepted_assignments = accepted_assignments

    def list_active(self) -> list[Assignment]:
        scenario_id = self._active_scenario_id()
        seen: set[tuple[str, str]] = set()
        assignments: list[Assignment] = []

        for row in [*self._baseline_assignments(), *self._accepted_assignments(scenario_id)]:
            if row.get("status") != "active":
                continue
            key = (str(row.get("incident_id")), str(row.get("crew_id")))
            if key in seen:
                continue
            seen.add(key)
            assignments.append(
                Assignment.model_validate(
                    {**row, "scenario_id": row.get("scenario_id") or scenario_id}
                )
            )

        return assignments
