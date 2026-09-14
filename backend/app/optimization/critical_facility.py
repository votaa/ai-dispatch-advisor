from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..domain.models import Incident
from .contracts import CriticalFacilityImpact, CriticalFacilityLevel


LEVEL_BY_PRIORITY = {
    "critical": 1,
    "high": 2,
    "medium": 3,
}


def critical_facility_level_for_priority(
    priority_level: object,
) -> CriticalFacilityLevel | None:
    """Map one source facility priority through the shared operational-level contract."""

    return LEVEL_BY_PRIORITY.get(str(priority_level or "").strip().lower())


def resolve_critical_facility_impact(
    incident: Incident,
    facilities: Iterable[Mapping[str, Any]],
) -> CriticalFacilityImpact:
    """Resolve one incident's facility level without reading scenario-global state."""

    if not incident.critical_facility:
        return CriticalFacilityImpact()

    matches = [
        facility
        for facility in facilities
        if str(facility.get("region")) == incident.region
        and str(facility.get("feeder")) == incident.feeder
    ]
    matched_ids = sorted(str(facility.get("facility_id")) for facility in matches)
    if not matches:
        return CriticalFacilityImpact(
            ranking_status="withheld",
            warning_code="critical_facility_missing_link",
            warning_message=(
                "Critical-facility incident has no matching facility for its region and feeder."
            ),
        )

    unknown_ids = sorted(
        str(facility.get("facility_id"))
        for facility in matches
        if critical_facility_level_for_priority(facility.get("priority_level")) is None
    )
    if unknown_ids:
        joined_ids = ", ".join(unknown_ids)
        return CriticalFacilityImpact(
            ranking_status="withheld",
            matched_facility_ids=matched_ids,
            warning_code="unknown_critical_facility_level",
            warning_message=(
                "Critical-facility level is unknown for matched facility IDs: " + joined_ids
            ),
        )

    levels = [
        level
        for facility in matches
        if (level := critical_facility_level_for_priority(facility.get("priority_level")))
        is not None
    ]
    return CriticalFacilityImpact(
        level=min(levels),
        matched_facility_ids=matched_ids,
    )
