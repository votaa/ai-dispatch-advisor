from __future__ import annotations

import csv
import json
import re
from collections import Counter
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


SUPPORTED_EVENT_TYPES = Literal["blue_sky", "storm", "crew_shortage", "critical_facility"]


class ScenarioFiles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incidents: Literal["PendingIncidents.csv"]
    crews: Literal["Crews.csv"]
    assignments: Literal["Assignments.csv"]
    historical_repairs: Literal["HistoricalRepairs.csv"]
    weather: Literal["Weather.csv"]
    critical_facilities: Literal["CriticalFacilities.csv"]
    topology: Literal["Topology.csv"]


class ScenarioManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    scenario_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str
    description: str
    event_type: SUPPORTED_EVENT_TYPES
    expected_conditions: list[str] = Field(min_length=1)
    files: ScenarioFiles

    @field_validator("name", "description")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("expected_conditions")
    @classmethod
    def validate_expected_conditions(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("entries must not be blank")
        return normalized


class ScenarioDescriptor(ScenarioManifest):
    validation_status: Literal["valid"] = "valid"
    is_active: bool


class ScenarioServiceError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        scenario_id: str | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.scenario_id = scenario_id
        self.details = details or []

    def response_content(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "scenario_id": self.scenario_id,
                "details": self.details,
            }
        }


CSV_SCHEMAS: dict[str, tuple[list[str], str]] = {
    "PendingIncidents.csv": (
        [
            "incident_id",
            "region",
            "municipality",
            "feeder",
            "severity",
            "status",
            "customers_out",
            "critical_facility",
            "hazard",
            "required_skill",
            "age_minutes",
            "latitude",
            "longitude",
            "etr",
        ],
        "incident_id",
    ),
    "Crews.csv": (
        [
            "crew_id",
            "crew_name",
            "home_region",
            "status",
            "capability",
            "current_location",
            "shift_remaining_hours",
            "storm_ready",
            "travel_minutes_to_selected_incident",
        ],
        "crew_id",
    ),
    "Assignments.csv": (
        ["assignment_id", "incident_id", "crew_id", "status", "assigned_at", "notes"],
        "assignment_id",
    ),
    "HistoricalRepairs.csv": (
        ["repair_id", "incident_type", "region", "average_duration_minutes", "crew_type", "notes"],
        "repair_id",
    ),
    "Weather.csv": (
        ["weather_id", "region", "condition", "wind_mph", "precipitation_inches", "lightning_risk", "updated_at"],
        "weather_id",
    ),
    "CriticalFacilities.csv": (
        ["facility_id", "facility_name", "facility_type", "region", "municipality", "feeder", "priority_level"],
        "facility_id",
    ),
    "Topology.csv": (
        ["asset_id", "asset_type", "feeder", "parent_asset_id", "region", "normal_status"],
        "asset_id",
    ),
}

REQUIRED_NON_EMPTY_CSVS = {"PendingIncidents.csv", "Crews.csv"}


class ScenarioService:
    def __init__(self, data_root: Path, active_scenario_id: str) -> None:
        self.data_root = data_root
        self.active_scenario_id = active_scenario_id

    def list_scenarios(self) -> list[ScenarioDescriptor]:
        if not self.data_root.is_dir():
            raise ScenarioServiceError(
                code="scenario_data_root_missing",
                message="Scenario data root does not exist or is not a directory.",
                status_code=500,
                details=[{"location": str(self.data_root), "message": "Directory not found"}],
            )

        scenario_directories = sorted(
            path for path in self.data_root.iterdir() if path.is_dir() and not path.name.startswith(".")
        )
        if not scenario_directories:
            raise ScenarioServiceError(
                code="scenarios_not_found",
                message="No scenario directories were found.",
                status_code=404,
                details=[{"location": str(self.data_root), "message": "No scenarios discovered"}],
            )

        return [self._descriptor_for(path.name) for path in scenario_directories]

    def active_scenario(self) -> ScenarioDescriptor:
        return self._descriptor_for(self.active_scenario_id)

    def _descriptor_for(self, scenario_id: str) -> ScenarioDescriptor:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", scenario_id):
            raise ScenarioServiceError(
                code="scenario_id_invalid",
                message="Scenario identifier is invalid.",
                status_code=400,
                scenario_id=scenario_id,
                details=[
                    {
                        "location": "scenario_id",
                        "message": "Use lowercase letters, numbers, hyphens, or underscores",
                    }
                ],
            )
        scenario_directory = self.data_root / scenario_id
        if not scenario_directory.is_dir():
            raise ScenarioServiceError(
                code="scenario_not_found",
                message=f"Scenario '{scenario_id}' was not found.",
                status_code=404,
                scenario_id=scenario_id,
                details=[{"location": str(scenario_directory), "message": "Directory not found"}],
            )

        manifest = self._load_manifest(scenario_directory)
        validation_issues = self._validate_scenario_data(scenario_directory, manifest)
        if validation_issues:
            raise ScenarioServiceError(
                code="scenario_validation_failed",
                message=f"Scenario '{scenario_id}' failed validation.",
                status_code=422,
                scenario_id=scenario_id,
                details=validation_issues,
            )

        return ScenarioDescriptor(
            **manifest.model_dump(),
            is_active=manifest.scenario_id == self.active_scenario_id,
        )

    def _load_manifest(self, scenario_directory: Path) -> ScenarioManifest:
        scenario_id = scenario_directory.name
        manifest_path = scenario_directory / "scenario.json"
        if not manifest_path.is_file():
            raise ScenarioServiceError(
                code="scenario_manifest_missing",
                message=f"Scenario '{scenario_id}' does not contain scenario.json.",
                status_code=422,
                scenario_id=scenario_id,
                details=[{"location": "scenario.json", "message": "Required manifest is missing"}],
            )

        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, JSONDecodeError) as exc:
            raise ScenarioServiceError(
                code="scenario_manifest_invalid",
                message=f"Scenario '{scenario_id}' contains an unreadable or invalid manifest.",
                status_code=422,
                scenario_id=scenario_id,
                details=[{"location": "scenario.json", "message": str(exc)}],
            ) from exc

        try:
            manifest = ScenarioManifest.model_validate(payload)
        except ValidationError as exc:
            details = [
                {
                    "location": ".".join(str(part) for part in issue["loc"]),
                    "message": issue["msg"],
                    "type": issue["type"],
                }
                for issue in exc.errors()
            ]
            raise ScenarioServiceError(
                code="scenario_manifest_invalid",
                message=f"Scenario '{scenario_id}' contains an invalid manifest.",
                status_code=422,
                scenario_id=scenario_id,
                details=details,
            ) from exc

        if manifest.scenario_id != scenario_id:
            raise ScenarioServiceError(
                code="scenario_manifest_invalid",
                message=f"Scenario '{scenario_id}' contains an invalid manifest.",
                status_code=422,
                scenario_id=scenario_id,
                details=[
                    {
                        "location": "scenario_id",
                        "message": f"Must match directory name '{scenario_id}'",
                    }
                ],
            )
        return manifest

    def _validate_scenario_data(
        self,
        scenario_directory: Path,
        manifest: ScenarioManifest,
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        rows_by_file: dict[str, list[dict[str, str]]] = {}

        for filename in manifest.files.model_dump().values():
            expected_headers, id_field = CSV_SCHEMAS[filename]
            file_path = scenario_directory / filename
            try:
                if file_path.resolve().parent != scenario_directory.resolve():
                    issues.append({"location": filename, "message": "File must remain inside the scenario directory"})
                    continue
            except OSError as exc:
                issues.append({"location": filename, "message": str(exc)})
                continue

            if not file_path.is_file():
                issues.append({"location": filename, "message": "Required CSV file is missing"})
                continue

            try:
                with file_path.open(newline="", encoding="utf-8") as handle:
                    reader = csv.DictReader(handle, strict=True)
                    if reader.fieldnames != expected_headers:
                        issues.append(
                            {
                                "location": filename,
                                "message": "CSV headers do not match the required schema",
                                "expected": expected_headers,
                                "actual": reader.fieldnames,
                            }
                        )
                        continue
                    rows = list(reader)
            except (OSError, UnicodeError, csv.Error) as exc:
                issues.append({"location": filename, "message": f"CSV could not be read: {exc}"})
                continue

            if not rows and filename in REQUIRED_NON_EMPTY_CSVS:
                issues.append({"location": filename, "message": "CSV must contain at least one data row"})
                continue
            if any(None in row or any(value is None for value in row.values()) for row in rows):
                issues.append({"location": filename, "message": "One or more rows do not match the CSV column count"})
                continue

            identifiers = [row[id_field].strip() for row in rows]
            if any(not identifier for identifier in identifiers):
                issues.append({"location": filename, "message": f"{id_field} must not be blank"})
            duplicates = sorted(identifier for identifier, count in Counter(identifiers).items() if count > 1)
            if duplicates:
                issues.append(
                    {
                        "location": filename,
                        "message": f"Duplicate {id_field} values found",
                        "values": duplicates,
                    }
                )
            rows_by_file[filename] = rows

        reference_files = {"Assignments.csv", "PendingIncidents.csv", "Crews.csv"}
        if reference_files.issubset(rows_by_file):
            assignments = rows_by_file["Assignments.csv"]
            incident_ids = {row["incident_id"] for row in rows_by_file["PendingIncidents.csv"]}
            crew_ids = {row["crew_id"] for row in rows_by_file["Crews.csv"]}
            for row_number, assignment in enumerate(assignments, start=2):
                if assignment["incident_id"] not in incident_ids:
                    issues.append(
                        {
                            "location": f"Assignments.csv:{row_number}.incident_id",
                            "message": f"Unknown incident_id '{assignment['incident_id']}'",
                        }
                    )
                if assignment["crew_id"] not in crew_ids:
                    issues.append(
                        {
                            "location": f"Assignments.csv:{row_number}.crew_id",
                            "message": f"Unknown crew_id '{assignment['crew_id']}'",
                        }
                    )
        return issues
