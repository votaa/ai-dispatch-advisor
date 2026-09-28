from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..crew_map_location import CrewMapLocationResolver
from ..domain.models import Assignment, Crew
from ..geography import GeographyRegistry
from .assignment_service import AssignmentService


class CrewService:
    def __init__(
        self,
        *,
        crew_rows: Callable[[], list[dict[str, Any]]],
        incident_rows: Callable[[], list[dict[str, Any]]],
        assignments: AssignmentService,
        geography: GeographyRegistry | None = None,
    ) -> None:
        self._crew_rows = crew_rows
        self._incident_rows = incident_rows
        self._assignments = assignments
        self._map_locations = CrewMapLocationResolver(geography) if geography else None

    def list(self) -> list[Crew]:
        assignments = self._assignments.list_active()
        incident_map = {
            str(row.get("incident_id")): row for row in self._incident_rows()
        }
        active_by_crew: dict[str, list[Assignment]] = {}
        for assignment in assignments:
            active_by_crew.setdefault(assignment.crew_id, []).append(assignment)

        crews: list[Crew] = []
        for row in self._crew_rows():
            crew_id = str(row.get("crew_id"))
            crew_assignments = active_by_crew.get(crew_id, [])
            assigned_incidents = [
                {
                    "incident_id": assignment.incident_id,
                    "assignment_id": assignment.assignment_id,
                    "assigned_at": assignment.assigned_at,
                    "municipality": incident_map.get(assignment.incident_id, {}).get("municipality"),
                    "severity": incident_map.get(assignment.incident_id, {}).get("severity"),
                }
                for assignment in crew_assignments
            ]
            resolved = self._map_locations.resolve(
                str(row.get("current_location", "")), str(row.get("home_region", ""))
            ) if self._map_locations else None
            location = resolved.place if resolved else None
            map_location = {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "village": location.village,
                "reference_id": location.reference_id,
                "precision": "village_center",
                "resolution_basis": resolved.basis,
            } if location else None
            crews.append(
                Crew.model_validate(
                    {
                        **row,
                        "status": (
                            "assigned"
                            if assigned_incidents
                            else "available"
                            if row.get("status") == "assigned"
                            else row.get("status")
                        ),
                        "assigned_incidents": assigned_incidents,
                        "map_location": map_location,
                    }
                )
            )

        return crews
