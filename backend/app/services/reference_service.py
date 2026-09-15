from __future__ import annotations

import csv
import hashlib
import json
import re
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from json import JSONDecodeError
from pathlib import Path

from pydantic import ValidationError

from ..domain.reference import (
    PsegReferenceLookupResult,
    PsegReferenceManifest,
    PsegReferenceProvenance,
    PsegReferenceRow,
    PsegReferenceSnapshot,
    ReferenceLookupQuery,
    ReferenceValidationIssue,
    ReferenceValidationResult,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REFERENCE_ROOT = REPO_ROOT / "data" / "reference" / "pseg-long-island"
CSV_FILE_NAME = "customers-served.csv"
MANIFEST_FILE_NAME = "manifest.json"
CSV_HEADERS = [
    "reference_id",
    "source_county",
    "source_township",
    "source_village",
    "county",
    "township",
    "village",
    "customers_served",
]
DEFAULT_STALE_AFTER_DAYS = 90


def _normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


class PsegLongIslandReferenceService:
    """Validated, read-only access to the approved POC-012 static reference."""

    def __init__(
        self,
        reference_root: Path = DEFAULT_REFERENCE_ROOT,
        *,
        aliases: Mapping[str, tuple[str, str, str]] | None = None,
        clock: Callable[[], datetime] | None = None,
        stale_after_days: int = DEFAULT_STALE_AFTER_DAYS,
    ) -> None:
        if stale_after_days < 1:
            raise ValueError("stale_after_days must be at least one day")
        self.reference_root = reference_root
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.stale_after_days = stale_after_days
        self.aliases: dict[str, tuple[str, str, str]] = {}
        for alias, path in (aliases or {}).items():
            normalized_alias = _normalized_name(alias)
            if not normalized_alias:
                raise ValueError("reference aliases must not be blank")
            if len(path) != 3 or any(not value.strip() for value in path):
                raise ValueError("reference aliases must target a complete non-blank path")
            existing = self.aliases.get(normalized_alias)
            if existing is not None and existing != path:
                raise ValueError(f"reference alias is ambiguous: {alias}")
            self.aliases[normalized_alias] = path

    def status(self) -> ReferenceValidationResult:
        return self.snapshot().validation

    def snapshot(self) -> PsegReferenceSnapshot:
        manifest_path = self.reference_root / MANIFEST_FILE_NAME
        csv_path = self.reference_root / CSV_FILE_NAME
        missing = [
            path.name for path in (manifest_path, csv_path) if not path.is_file()
        ]
        if missing:
            return self._unavailable_snapshot(missing)

        try:
            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = PsegReferenceManifest.model_validate(manifest_payload)
            csv_bytes = csv_path.read_bytes()
            checksum = hashlib.sha256(csv_bytes).hexdigest()
            if checksum != manifest.artifact.sha256:
                return self._invalid_snapshot(
                    "artifact.sha256",
                    "CSV checksum does not match the approved manifest",
                    manifest=manifest,
                )
            rows = self._read_rows(csv_path)
            issues = self._validate_rows(rows, manifest)
            if issues:
                return PsegReferenceSnapshot(
                    validation=self._validation_result(
                        "invalid", manifest=manifest, issues=issues
                    ),
                    provenance=self._provenance(manifest),
                )
            status = self._freshness_status(manifest)
            return PsegReferenceSnapshot(
                validation=self._validation_result(status, manifest=manifest),
                rows=rows,
                provenance=self._provenance(manifest),
            )
        except ValidationError as exc:
            issues = [
                ReferenceValidationIssue(
                    location=".".join(str(part) for part in issue["loc"]),
                    message=issue["msg"],
                    type=issue["type"],
                )
                for issue in exc.errors()
            ]
            return PsegReferenceSnapshot(
                validation=ReferenceValidationResult(
                    reference_status="invalid",
                    issues=issues,
                    stale_after_days=self.stale_after_days,
                )
            )
        except (OSError, UnicodeError, JSONDecodeError, csv.Error, ValueError) as exc:
            return self._invalid_snapshot(
                "reference",
                f"Reference files could not be read: {exc}",
            )

    def by_county(self, county: str) -> PsegReferenceLookupResult:
        return self._lookup(
            ReferenceLookupQuery(kind="county", county=county),
            lambda row: _normalized_name(row.county) == _normalized_name(county),
            scope=lambda row: (row.county,),
        )

    def by_township(
        self, township: str, *, county: str | None = None
    ) -> PsegReferenceLookupResult:
        return self._lookup(
            ReferenceLookupQuery(kind="township", county=county, township=township),
            lambda row: (
                _normalized_name(row.township) == _normalized_name(township)
                and (
                    county is None
                    or _normalized_name(row.county) == _normalized_name(county)
                )
            ),
            scope=lambda row: (row.county, row.township),
        )

    def by_village(
        self,
        village: str,
        *,
        county: str | None = None,
        township: str | None = None,
    ) -> PsegReferenceLookupResult:
        return self._lookup(
            ReferenceLookupQuery(
                kind="village",
                county=county,
                township=township,
                village=village,
            ),
            lambda row: (
                _normalized_name(row.village) == _normalized_name(village)
                and (
                    county is None
                    or _normalized_name(row.county) == _normalized_name(county)
                )
                and (
                    township is None
                    or _normalized_name(row.township) == _normalized_name(township)
                )
            ),
            scope=lambda row: (row.county, row.township, row.village),
        )

    def by_path(
        self, county: str, township: str, village: str
    ) -> PsegReferenceLookupResult:
        return self._lookup(
            ReferenceLookupQuery(
                kind="path", county=county, township=township, village=village
            ),
            lambda row: (
                _normalized_name(row.county) == _normalized_name(county)
                and _normalized_name(row.township) == _normalized_name(township)
                and _normalized_name(row.village) == _normalized_name(village)
            ),
            scope=lambda row: (row.county, row.township, row.village),
        )

    def by_alias(self, alias: str) -> PsegReferenceLookupResult:
        query = ReferenceLookupQuery(kind="alias", alias=alias)
        path = self.aliases.get(_normalized_name(alias))
        if path is None:
            return self._not_found(query)
        return self._lookup(
            query,
            lambda row: (
                _normalized_name(row.county) == _normalized_name(path[0])
                and _normalized_name(row.township) == _normalized_name(path[1])
                and _normalized_name(row.village) == _normalized_name(path[2])
            ),
            scope=lambda row: (row.county, row.township, row.village),
        )

    def _lookup(
        self,
        query: ReferenceLookupQuery,
        predicate: Callable[[PsegReferenceRow], bool],
        *,
        scope: Callable[[PsegReferenceRow], tuple[str, ...]],
    ) -> PsegReferenceLookupResult:
        snapshot = self.snapshot()
        if snapshot.validation.reference_status in {"unavailable", "invalid"}:
            return PsegReferenceLookupResult(
                reference_status=snapshot.validation.reference_status,
                match_status="not_evaluated",
                query=query,
                provenance=snapshot.provenance,
                issues=snapshot.validation.issues,
            )
        matches = [row for row in snapshot.rows if predicate(row)]
        if not matches:
            return PsegReferenceLookupResult(
                reference_status=snapshot.validation.reference_status,
                match_status="not_found",
                query=query,
                provenance=snapshot.provenance,
            )
        scopes = {scope(row) for row in matches}
        match_status = "ambiguous" if len(scopes) > 1 else "found"
        return PsegReferenceLookupResult(
            reference_status=snapshot.validation.reference_status,
            match_status=match_status,
            query=query,
            matches=matches,
            total_customers_served=(
                sum(row.customers_served for row in matches)
                if match_status == "found"
                else None
            ),
            provenance=snapshot.provenance,
        )

    def _not_found(self, query: ReferenceLookupQuery) -> PsegReferenceLookupResult:
        snapshot = self.snapshot()
        if snapshot.validation.reference_status in {"unavailable", "invalid"}:
            match_status = "not_evaluated"
        else:
            match_status = "not_found"
        return PsegReferenceLookupResult(
            reference_status=snapshot.validation.reference_status,
            match_status=match_status,
            query=query,
            provenance=snapshot.provenance,
            issues=snapshot.validation.issues,
        )

    def _read_rows(self, csv_path: Path) -> list[PsegReferenceRow]:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != CSV_HEADERS:
                raise ValueError(f"CSV headers must be {CSV_HEADERS}")
            return [PsegReferenceRow.model_validate(row) for row in reader]

    def _validate_rows(
        self,
        rows: list[PsegReferenceRow],
        manifest: PsegReferenceManifest,
    ) -> list[ReferenceValidationIssue]:
        issues: list[ReferenceValidationIssue] = []
        if not rows:
            issues.append(
                ReferenceValidationIssue(
                    location=CSV_FILE_NAME, message="Reference CSV contains no rows"
                )
            )
            return issues

        reference_ids = [row.reference_id for row in rows]
        if len(reference_ids) != len(set(reference_ids)):
            issues.append(
                ReferenceValidationIssue(
                    location="reference_id", message="Composite IDs must be unique"
                )
            )
        source_paths = [
            (row.source_county, row.source_township, row.source_village)
            for row in rows
        ]
        if len(source_paths) != len(set(source_paths)):
            issues.append(
                ReferenceValidationIssue(
                    location="source_path", message="Source hierarchy paths must be unique"
                )
            )
        if source_paths != sorted(source_paths):
            issues.append(
                ReferenceValidationIssue(
                    location=CSV_FILE_NAME,
                    message="Rows must use deterministic source hierarchy order",
                )
            )

        actual_counts = {
            "county": len({row.source_county for row in rows}),
            "township": len(
                {(row.source_county, row.source_township) for row in rows}
            ),
            "leaf": len(rows),
        }
        expected_counts = manifest.counts.model_dump()
        for level, actual in actual_counts.items():
            if actual != expected_counts[level]:
                issues.append(
                    ReferenceValidationIssue(
                        location=f"counts.{level}",
                        message=(
                            f"Manifest count {expected_counts[level]} does not match "
                            f"CSV count {actual}"
                        ),
                    )
                )
        total = sum(row.customers_served for row in rows)
        if total != manifest.total_customers_served:
            issues.append(
                ReferenceValidationIssue(
                    location="total_customers_served",
                    message=(
                        f"Manifest total {manifest.total_customers_served} does not match "
                        f"CSV total {total}"
                    ),
                )
            )
        issues.extend(self._normalization_issues(rows))
        return issues

    @staticmethod
    def _normalization_issues(
        rows: list[PsegReferenceRow],
    ) -> list[ReferenceValidationIssue]:
        issues: list[ReferenceValidationIssue] = []
        for index, row in enumerate(rows, start=2):
            if row.source_county == "ROCKAWAY PENINSULA":
                expected = ("Queens", "Rockaway Peninsula", row.source_village.title())
            else:
                village = (
                    "Hempstead"
                    if (
                        row.source_county == "NASSAU"
                        and row.source_township == "HEMPSTEAD"
                        and row.source_village == "HEMPSTEAD VILLAGE"
                    )
                    else row.source_village.title()
                )
                expected = (
                    row.source_county.title(),
                    row.source_township.title(),
                    village,
                )
            actual = (row.county, row.township, row.village)
            if actual != expected:
                issues.append(
                    ReferenceValidationIssue(
                        location=f"{CSV_FILE_NAME}:{index}",
                        message=(
                            "Normalized hierarchy does not match poc-012-v1: "
                            f"expected {expected!r}, received {actual!r}"
                        ),
                    )
                )
        return issues

    def _freshness_status(self, manifest: PsegReferenceManifest) -> str:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("reference clock must return a timezone-aware datetime")
        age = now - manifest.source.updated_at
        return "stale" if age > timedelta(days=self.stale_after_days) else "current"

    def _validation_result(
        self,
        status: str,
        *,
        manifest: PsegReferenceManifest,
        issues: list[ReferenceValidationIssue] | None = None,
    ) -> ReferenceValidationResult:
        now = self.clock()
        age_days = max(
            0.0,
            (now - manifest.source.updated_at).total_seconds() / 86400,
        )
        return ReferenceValidationResult(
            reference_status=status,
            issues=issues or [],
            source_updated_at=manifest.source.updated_at,
            extracted_at=manifest.extracted_at,
            age_days=round(age_days, 3),
            stale_after_days=self.stale_after_days,
        )

    def _unavailable_snapshot(self, missing: list[str]) -> PsegReferenceSnapshot:
        return PsegReferenceSnapshot(
            validation=ReferenceValidationResult(
                reference_status="unavailable",
                stale_after_days=self.stale_after_days,
                issues=[
                    ReferenceValidationIssue(
                        location=str(self.reference_root),
                        message=f"Missing reference files: {', '.join(missing)}",
                    )
                ],
            )
        )

    def _invalid_snapshot(
        self,
        location: str,
        message: str,
        *,
        manifest: PsegReferenceManifest | None = None,
    ) -> PsegReferenceSnapshot:
        issue = ReferenceValidationIssue(location=location, message=message)
        if manifest is None:
            validation = ReferenceValidationResult(
                reference_status="invalid",
                issues=[issue],
                stale_after_days=self.stale_after_days,
            )
            provenance = None
        else:
            validation = self._validation_result(
                "invalid", manifest=manifest, issues=[issue]
            )
            provenance = self._provenance(manifest)
        return PsegReferenceSnapshot(
            validation=validation,
            provenance=provenance,
        )

    @staticmethod
    def _provenance(manifest: PsegReferenceManifest) -> PsegReferenceProvenance:
        return PsegReferenceProvenance(
            dataset_id=manifest.dataset_id,
            schema_version=manifest.schema_version,
            source_organization=manifest.source.organization,
            source_product=manifest.source.product,
            report_url=manifest.source.report_url,
            source_updated_at=manifest.source.updated_at,
            extracted_at=manifest.extracted_at,
            extractor_repository=manifest.extractor.repository,
            extractor_commit=manifest.extractor.commit,
            normalization_rule_version=manifest.normalization_rule_version,
            reviewed_by_role=manifest.review.reviewed_by_role,
            reviewed_at=manifest.review.reviewed_at,
        )
