from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..domain.models import Assignment
from .errors import AssignmentConflictError, AssignmentCrewSelectionError, AssignmentReasonRequiredError


REASON_LABELS = {
    "field_condition_changed": "Field condition changed",
    "crew_unavailable": "Crew unavailable",
    "assignment_entered_in_error": "Assignment entered in error",
    "incident_priority_changed": "Incident priority changed",
    "supervisor_direction": "Supervisor direction",
    "other": "Other",
}


class AssignmentService:
    def __init__(
        self,
        *,
        active_scenario_id: Callable[[], str],
        baseline_assignments: Callable[[], list[dict[str, Any]]],
        accepted_assignments: Callable[[str], list[dict[str, Any]]],
        unassigned_assignment_ids: Callable[[str], set[str]] = lambda _scenario_id: set(),
        record_unassignment: Callable[..., dict[str, Any]] = lambda **_kwargs: {},
        crew_rows: Callable[[], list[dict[str, Any]]] = lambda: [],
        record_reassignment: Callable[..., dict[str, Any]] = lambda **_kwargs: {},
    ) -> None:
        self._active_scenario_id = active_scenario_id
        self._baseline_assignments = baseline_assignments
        self._accepted_assignments = accepted_assignments
        self._unassigned_assignment_ids = unassigned_assignment_ids
        self._record_unassignment = record_unassignment
        self._crew_rows = crew_rows
        self._record_reassignment = record_reassignment

    def list_active(self) -> list[Assignment]:
        scenario_id = self._active_scenario_id()
        hidden_assignment_ids = self._unassigned_assignment_ids(scenario_id)
        seen: set[tuple[str, str]] = set()
        assignments: list[Assignment] = []

        for row in [*self._baseline_assignments(), *self._accepted_assignments(scenario_id)]:
            if row.get("status") != "active" or str(row.get("assignment_id")) in hidden_assignment_ids:
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

    def unassign(
        self,
        *,
        assignment_id: str,
        reason_category: str,
        note: str | None,
        actor: str = "demo-dispatcher",
    ) -> dict[str, Any]:
        normalized_note = self._validate_reason(reason_category, note)

        assignment = next(
            (item for item in self.list_active() if item.assignment_id == assignment_id),
            None,
        )
        if assignment is None:
            raise AssignmentConflictError(assignment_id, "Assignment is no longer active; refresh the operational data")

        return self._record_unassignment(
            scenario_id=self._active_scenario_id(),
            assignment_id=assignment.assignment_id,
            incident_id=assignment.incident_id,
            crew_id=assignment.crew_id,
            reason_category=reason_category,
            note=normalized_note,
            actor=actor,
        )

    def reassign(
        self,
        *,
        assignment_id: str,
        selected_crew_id: str | None,
        reason_category: str,
        note: str | None,
        actor: str = "demo-dispatcher",
    ) -> dict[str, Any]:
        normalized_note = self._validate_reason(reason_category, note)
        if not selected_crew_id:
            raise AssignmentCrewSelectionError("none", "A replacement crew is required")

        assignment = next(
            (item for item in self.list_active() if item.assignment_id == assignment_id),
            None,
        )
        if assignment is None:
            raise AssignmentConflictError(assignment_id, "Assignment is no longer active; refresh the operational data")
        if selected_crew_id == assignment.crew_id:
            raise AssignmentCrewSelectionError(selected_crew_id, "Replacement crew must differ from the current crew")

        active_assignments = self.list_active()
        if any(item.crew_id == selected_crew_id for item in active_assignments):
            raise AssignmentCrewSelectionError(selected_crew_id, "Selected crew is already assigned; choose an available crew")
        selected_crew = next((row for row in self._crew_rows() if str(row.get("crew_id")) == selected_crew_id), None)
        if selected_crew is None:
            raise AssignmentCrewSelectionError(selected_crew_id, "Selected crew does not exist")
        if str(selected_crew.get("status")).lower() != "available":
            raise AssignmentCrewSelectionError(selected_crew_id, "Selected crew is not available")

        return self._record_reassignment(
            scenario_id=self._active_scenario_id(),
            assignment_id=assignment.assignment_id,
            incident_id=assignment.incident_id,
            crew_id=assignment.crew_id,
            selected_crew_id=selected_crew_id,
            reason_category=reason_category,
            note=normalized_note,
            actor=actor,
        )

    @staticmethod
    def _validate_reason(reason_category: str, note: str | None) -> str | None:
        normalized_note = note.strip() if note else ""
        if reason_category not in REASON_LABELS:
            raise AssignmentReasonRequiredError()
        if reason_category == "other" and not normalized_note:
            raise AssignmentReasonRequiredError()
        return normalized_note or None
