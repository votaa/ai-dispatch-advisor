from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Literal

from .geography import GeographyRecord, GeographyRegistry, _normalized_name


LOGGER = logging.getLogger(__name__)
PROXY_VILLAGES = {
    "pseg-li-78b452f119b7098c48bb": "Hewlett",
    "pseg-li-32180e1a9c9aeac831db": "Hicksville",
    "pseg-li-19dde346bc11e762bd90": "Brentwood",
    "pseg-li-808d36974b333bb1ab63": "Riverhead",
}

# Reviewed synthetic-scenario labels only. These are map proxies, not staging coordinates.
STAGING_MAP_PROXIES = (
    ("RDA1 MUA Staging", "Queens-Nassau", "pseg-li-78b452f119b7098c48bb"),
    ("Hewlett Vegetation Staging Area", "Queens-Nassau", "pseg-li-78b452f119b7098c48bb"),
    ("RDA4 MUA Staging", "Central-Nassau", "pseg-li-32180e1a9c9aeac831db"),
    ("RDA7 MUA Staging", "Central-Nassau", "pseg-li-32180e1a9c9aeac831db"),
    ("Hicksville Vegetation Staging Area", "Central-Nassau", "pseg-li-32180e1a9c9aeac831db"),
    ("RDA10 MUA Staging", "Western Suffolk", "pseg-li-19dde346bc11e762bd90"),
    ("RDA13 MUA Staging", "Western Suffolk", "pseg-li-19dde346bc11e762bd90"),
    ("Brentwood Vegetation Staging Area", "Western Suffolk", "pseg-li-19dde346bc11e762bd90"),
    ("RDA16 MUA Staging", "Eastern Suffolk", "pseg-li-808d36974b333bb1ab63"),
    ("RDA19 MUA Staging", "Eastern Suffolk", "pseg-li-808d36974b333bb1ab63"),
    ("Riverhead Vegetation Staging Area", "Eastern Suffolk", "pseg-li-808d36974b333bb1ab63"),
)


@dataclass(frozen=True)
class CrewMapResolution:
    place: GeographyRecord
    basis: Literal["source_place", "operating_hq_proxy"]


def _valid_coordinates(place: GeographyRecord) -> bool:
    return (
        math.isfinite(place.latitude)
        and math.isfinite(place.longitude)
        and abs(place.latitude) <= 90
        and abs(place.longitude) <= 180
        and (place.latitude, place.longitude) != (0, 0)
    )


class CrewMapLocationResolver:
    """Resolve only approved staging labels to a division HQ village-center proxy."""

    def __init__(self, geography: GeographyRegistry) -> None:
        self.geography = geography
        self._staging: dict[str, tuple[str, GeographyRecord | None]] = {}
        by_id = {record.reference_id: record for record in geography.records}
        for label, division, reference_id in STAGING_MAP_PROXIES:
            key = _normalized_name(label)
            if not key or key in self._staging:
                raise ValueError(f"Duplicate or blank crew staging map label: {label}")
            target = by_id.get(reference_id)
            if (
                target is None
                or target.village != PROXY_VILLAGES.get(reference_id)
                or not _valid_coordinates(target)
            ):
                LOGGER.warning("Crew map proxy unavailable for %s: invalid or missing reference %s", label, reference_id)
                target = None
            self._staging[key] = (division, target)

    def resolve(self, current_location: str, home_region: str) -> CrewMapResolution | None:
        direct = self.geography.resolve(current_location)
        if direct is not None and _valid_coordinates(direct):
            return CrewMapResolution(direct, "source_place")
        staging = self._staging.get(_normalized_name(current_location))
        if staging is None or staging[0] != home_region or staging[1] is None:
            return None
        return CrewMapResolution(staging[1], "operating_hq_proxy")
