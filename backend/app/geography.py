from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .domain.models import Crew, Incident


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GEOGRAPHY_PATH = (
    REPO_ROOT / "data" / "generator-lookups" / "LongIslandGeography.csv"
)
GEOGRAPHY_HEADERS = [
    "region",
    "municipality",
    "locality_type",
    "latitude",
    "longitude",
    "reference_id",
    "source_county",
    "source_township",
    "source_village",
    "county",
    "township",
    "village",
    "aliases",
    "reference_source",
]
GEOGRAPHY_REFERENCE_VERSION = "poc-032-v1-2026-09-15"


def _normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


@dataclass(frozen=True)
class GeographyRecord:
    region: str
    municipality: str
    locality_type: str
    latitude: float
    longitude: float
    reference_id: str
    source_county: str
    source_township: str
    source_village: str
    county: str
    township: str
    village: str
    aliases: tuple[str, ...]
    reference_source: str

    @property
    def hierarchy(self) -> str:
        return f"{self.county} -> {self.township} -> {self.village}"


class GeographyRegistry:
    """Exact, local authority for the POC County/Township/Village hierarchy."""

    def __init__(
        self,
        records: Iterable[GeographyRecord],
        *,
        version: str = GEOGRAPHY_REFERENCE_VERSION,
    ) -> None:
        self.version = version
        self.records = tuple(records)
        if not self.records:
            raise ValueError("Geography registry must contain at least one record")

        self._by_name: dict[str, GeographyRecord] = {}
        reference_ids: set[str] = set()
        for record in self.records:
            if not record.reference_id:
                raise ValueError("Geography reference IDs must not be blank")
            if record.reference_id in reference_ids:
                raise ValueError(
                    f"Geography reference ID is duplicated: {record.reference_id}"
                )
            reference_ids.add(record.reference_id)
            if not all(
                (
                    record.source_county,
                    record.source_township,
                    record.source_village,
                    record.county,
                    record.township,
                    record.village,
                )
            ):
                raise ValueError(
                    f"Geography hierarchy fields must not be blank: {record.municipality}"
                )
            names = (record.municipality, record.village, *record.aliases)
            for name in names:
                key = _normalized_name(name)
                if not key:
                    continue
                existing = self._by_name.get(key)
                if existing is not None and existing != record:
                    raise ValueError(f"Geography alias is ambiguous: {name}")
                self._by_name[key] = record

    @classmethod
    def from_csv(cls, path: Path = DEFAULT_GEOGRAPHY_PATH) -> "GeographyRegistry":
        records: list[GeographyRecord] = []
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != GEOGRAPHY_HEADERS:
                raise ValueError(
                    f"Geography registry headers must be {GEOGRAPHY_HEADERS}"
                )
            for row in reader:
                aliases = tuple(
                    alias.strip()
                    for alias in row["aliases"].split("|")
                    if alias.strip()
                )
                records.append(
                    GeographyRecord(
                        region=row["region"].strip(),
                        municipality=row["municipality"].strip(),
                        locality_type=row["locality_type"].strip(),
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                        reference_id=row["reference_id"].strip(),
                        source_county=row["source_county"].strip(),
                        source_township=row["source_township"].strip(),
                        source_village=row["source_village"].strip(),
                        county=row["county"].strip(),
                        township=row["township"].strip(),
                        village=row["village"].strip(),
                        aliases=aliases,
                        reference_source=row["reference_source"].strip(),
                    )
                )
        return cls(records)

    def resolve(self, name: str) -> GeographyRecord | None:
        return self._by_name.get(_normalized_name(name))

    def require(self, name: str) -> GeographyRecord:
        record = self.resolve(name)
        if record is None:
            raise ValueError(f"Location is not in the geography registry: {name}")
        return record

    def hierarchy_for_incident(self, incident: Incident) -> GeographyRecord | None:
        return self.resolve(incident.municipality)


@dataclass(frozen=True)
class TravelEstimate:
    origin: str
    destination: str
    straight_line_miles: float
    estimated_road_miles: float
    estimated_travel_minutes: int
    calculation: str
    geography_version: str


class TravelEstimateService:
    """Deterministic POC travel estimates with no network or model dependency."""

    ROAD_DISTANCE_FACTOR = 1.22
    LOCAL_SPEED_MPH = 27.0
    REGIONAL_SPEED_MPH = 34.0
    DISPATCH_OVERHEAD_MINUTES = 5

    def __init__(self, registry: GeographyRegistry) -> None:
        self.registry = registry

    @staticmethod
    def _haversine_miles(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
    ) -> float:
        earth_radius_miles = 3958.7613
        origin_lat = math.radians(origin_latitude)
        destination_lat = math.radians(destination_latitude)
        latitude_delta = math.radians(destination_latitude - origin_latitude)
        longitude_delta = math.radians(destination_longitude - origin_longitude)
        a = (
            math.sin(latitude_delta / 2) ** 2
            + math.cos(origin_lat)
            * math.cos(destination_lat)
            * math.sin(longitude_delta / 2) ** 2
        )
        a = min(1.0, max(0.0, a))
        return earth_radius_miles * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def estimate(
        self,
        *,
        origin_name: str,
        destination_name: str,
        destination_latitude: float,
        destination_longitude: float,
    ) -> TravelEstimate | None:
        origin = self.registry.resolve(origin_name)
        destination = self.registry.resolve(destination_name)
        if origin is None or destination is None:
            return None

        straight_line_miles = self._haversine_miles(
            origin.latitude,
            origin.longitude,
            destination_latitude,
            destination_longitude,
        )
        estimated_road_miles = max(1.0, straight_line_miles * self.ROAD_DISTANCE_FACTOR)
        speed_mph = (
            self.LOCAL_SPEED_MPH
            if estimated_road_miles <= 15
            else self.REGIONAL_SPEED_MPH
        )
        travel_minutes = max(
            self.DISPATCH_OVERHEAD_MINUTES,
            math.ceil(
                estimated_road_miles / speed_mph * 60
                + self.DISPATCH_OVERHEAD_MINUTES
            ),
        )
        return TravelEstimate(
            origin=origin.village,
            destination=destination.village,
            straight_line_miles=round(straight_line_miles, 1),
            estimated_road_miles=round(estimated_road_miles, 1),
            estimated_travel_minutes=travel_minutes,
            calculation=(
                "haversine distance x 1.22 road factor, "
                f"{speed_mph:.0f} mph planning speed, plus 5 dispatch minutes"
            ),
            geography_version=self.registry.version,
        )

    def estimate_for(self, crew: Crew, incident: Incident) -> TravelEstimate | None:
        return self.estimate(
            origin_name=crew.current_location,
            destination_name=incident.municipality,
            destination_latitude=incident.latitude,
            destination_longitude=incident.longitude,
        )

    def crews_for_incident(self, crews: Iterable[Crew], incident: Incident) -> list[Crew]:
        derived: list[Crew] = []
        for crew in crews:
            estimate = self.estimate_for(crew, incident)
            if estimate is None:
                derived.append(crew)
                continue
            derived.append(
                crew.model_copy(
                    update={
                        "travel_minutes_to_selected_incident": (
                            estimate.estimated_travel_minutes
                        )
                    }
                )
            )
        return derived
