from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services import PsegLongIslandReferenceService, build_services
from app.services.reference_service import CSV_HEADERS, DEFAULT_REFERENCE_ROOT


def _copy_reference(tmp_path: Path) -> Path:
    target = tmp_path / "pseg-long-island"
    shutil.copytree(DEFAULT_REFERENCE_ROOT, target)
    return target


def _read_manifest(reference_root: Path) -> dict:
    return json.loads((reference_root / "manifest.json").read_text(encoding="utf-8"))


def _write_manifest(reference_root: Path, manifest: dict) -> None:
    (reference_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_rows(reference_root: Path) -> list[dict[str, str]]:
    with (reference_root / "customers-served.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        return list(csv.DictReader(handle))


def _write_rows(reference_root: Path, rows: list[dict[str, str]]) -> None:
    csv_path = reference_root / "customers-served.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest = _read_manifest(reference_root)
    manifest["artifact"]["sha256"] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    _write_manifest(reference_root, manifest)


def test_loads_approved_reference_and_supports_hierarchy_lookups() -> None:
    service = PsegLongIslandReferenceService(
        clock=lambda: datetime(2026, 9, 16, tzinfo=timezone.utc)
    )

    snapshot = service.snapshot()
    nassau = service.by_county("nassau")
    hempstead = service.by_township("Hempstead", county="Nassau")
    arverne = service.by_path("Queens", "Rockaway Peninsula", "Arverne")

    assert snapshot.validation.reference_status == "current"
    assert len(snapshot.rows) == 347
    assert snapshot.provenance is not None
    assert snapshot.provenance.normalization_rule_version == "poc-012-v1"
    assert nassau.match_status == "found"
    assert nassau.total_customers_served == 479704
    assert hempstead.match_status == "found"
    assert hempstead.total_customers_served == 263498
    assert arverne.match_status == "found"
    assert arverne.total_customers_served == 4607
    assert arverne.matches[0].source_county == "ROCKAWAY PENINSULA"
    assert arverne.matches[0].county == "Queens"


def test_ambiguous_village_returns_every_path_without_combining_totals() -> None:
    service = PsegLongIslandReferenceService(
        clock=lambda: datetime(2026, 9, 16, tzinfo=timezone.utc)
    )

    result = service.by_village("Calverton")

    assert result.reference_status == "current"
    assert result.match_status == "ambiguous"
    assert result.total_customers_served is None
    assert {
        (row.county, row.township, row.village) for row in result.matches
    } == {
        ("Suffolk", "Brookhaven", "Calverton"),
        ("Suffolk", "Riverhead", "Calverton"),
    }


def test_configured_alias_resolves_to_complete_path() -> None:
    service = PsegLongIslandReferenceService(
        aliases={
            "Rockaway Beach": ("Queens", "Rockaway Peninsula", "Rockaway Park")
        },
        clock=lambda: datetime(2026, 9, 16, tzinfo=timezone.utc),
    )

    result = service.by_alias("rockaway-beach")

    assert result.match_status == "found"
    assert len(result.matches) == 1
    assert result.matches[0].village == "Rockaway Park"


def test_configured_aliases_cannot_normalize_to_different_paths() -> None:
    with pytest.raises(ValueError, match="reference alias is ambiguous"):
        PsegLongIslandReferenceService(
            aliases={
                "Shared-Alias": ("Nassau", "Hempstead", "Baldwin"),
                "Shared Alias": ("Suffolk", "Islip", "Bay Shore"),
            }
        )


def test_stale_reference_remains_queryable_with_explicit_state() -> None:
    service = PsegLongIslandReferenceService(
        clock=lambda: datetime(2026, 12, 16, tzinfo=timezone.utc)
    )

    result = service.by_village(
        "Hempstead", county="Nassau", township="Hempstead"
    )

    assert result.reference_status == "stale"
    assert result.match_status == "found"
    assert result.total_customers_served == 17319
    assert result.matches[0].source_village == "HEMPSTEAD VILLAGE"


def test_missing_reference_is_unavailable_without_raising(tmp_path: Path) -> None:
    service = PsegLongIslandReferenceService(tmp_path / "missing")

    status = service.status()
    lookup = service.by_county("Nassau")

    assert status.reference_status == "unavailable"
    assert lookup.reference_status == "unavailable"
    assert lookup.match_status == "not_evaluated"
    assert lookup.matches == []


def test_unavailable_reference_does_not_break_existing_services(tmp_path: Path) -> None:
    reference = PsegLongIslandReferenceService(tmp_path / "missing")

    services = build_services(pseg_reference=reference)

    assert services.pseg_reference.status().reference_status == "unavailable"
    assert services.incidents.list_ranked()
    assert services.recommendations.recommend().incident_id
    assert services.copilot.respond("How many crews are available?").intent == "crew_status"


def test_checksum_failure_is_invalid_without_exposing_rows(tmp_path: Path) -> None:
    reference_root = _copy_reference(tmp_path)
    manifest = _read_manifest(reference_root)
    manifest["artifact"]["sha256"] = "0" * 64
    _write_manifest(reference_root, manifest)

    snapshot = PsegLongIslandReferenceService(reference_root).snapshot()

    assert snapshot.validation.reference_status == "invalid"
    assert snapshot.rows == []
    assert snapshot.validation.issues[0].location == "artifact.sha256"


def test_schema_count_and_aggregate_failures_are_invalid(tmp_path: Path) -> None:
    schema_root = _copy_reference(tmp_path / "schema")
    schema_manifest = _read_manifest(schema_root)
    schema_manifest["schema_version"] = "2.0"
    _write_manifest(schema_root, schema_manifest)
    assert (
        PsegLongIslandReferenceService(schema_root).status().reference_status
        == "invalid"
    )

    count_root = _copy_reference(tmp_path / "count")
    count_manifest = _read_manifest(count_root)
    count_manifest["counts"]["leaf"] += 1
    _write_manifest(count_root, count_manifest)
    count_status = PsegLongIslandReferenceService(count_root).status()
    assert count_status.reference_status == "invalid"
    assert any(issue.location == "counts.leaf" for issue in count_status.issues)

    aggregate_root = _copy_reference(tmp_path / "aggregate")
    aggregate_manifest = _read_manifest(aggregate_root)
    aggregate_manifest["total_customers_served"] += 1
    _write_manifest(aggregate_root, aggregate_manifest)
    aggregate_status = PsegLongIslandReferenceService(aggregate_root).status()
    assert aggregate_status.reference_status == "invalid"
    assert any(
        issue.location == "total_customers_served"
        for issue in aggregate_status.issues
    )


def test_timestamp_and_csv_header_failures_are_invalid(tmp_path: Path) -> None:
    timestamp_root = _copy_reference(tmp_path / "timestamp")
    timestamp_manifest = _read_manifest(timestamp_root)
    timestamp_manifest["source"]["updated_at"] = "2026-09-15T23:41:56"
    _write_manifest(timestamp_root, timestamp_manifest)
    timestamp_status = PsegLongIslandReferenceService(timestamp_root).status()
    assert timestamp_status.reference_status == "invalid"
    assert any(
        issue.location == "source.updated_at" for issue in timestamp_status.issues
    )

    header_root = _copy_reference(tmp_path / "header")
    csv_path = header_root / "customers-served.csv"
    csv_text = csv_path.read_text(encoding="utf-8").replace(
        "reference_id,", "unexpected_id,", 1
    )
    csv_path.write_text(csv_text, encoding="utf-8")
    header_manifest = _read_manifest(header_root)
    header_manifest["artifact"]["sha256"] = hashlib.sha256(
        csv_path.read_bytes()
    ).hexdigest()
    _write_manifest(header_root, header_manifest)
    header_status = PsegLongIslandReferenceService(header_root).status()
    assert header_status.reference_status == "invalid"
    assert any("headers" in issue.message.casefold() for issue in header_status.issues)


def test_duplicate_id_and_normalization_failures_are_invalid(tmp_path: Path) -> None:
    duplicate_root = _copy_reference(tmp_path / "duplicate")
    duplicate_rows = _read_rows(duplicate_root)
    duplicate_rows[1]["reference_id"] = duplicate_rows[0]["reference_id"]
    _write_rows(duplicate_root, duplicate_rows)
    duplicate_status = PsegLongIslandReferenceService(duplicate_root).status()
    assert duplicate_status.reference_status == "invalid"
    assert any(
        issue.location == "reference_id" for issue in duplicate_status.issues
    )

    normalization_root = _copy_reference(tmp_path / "normalization")
    normalization_rows = _read_rows(normalization_root)
    arverne = next(
        row for row in normalization_rows if row["source_village"] == "ARVERNE"
    )
    arverne["county"] = "Rockaway"
    _write_rows(normalization_root, normalization_rows)
    normalization_status = PsegLongIslandReferenceService(
        normalization_root
    ).status()
    assert normalization_status.reference_status == "invalid"
    assert any(
        "normalization" in issue.message.casefold()
        or "normalized hierarchy" in issue.message.casefold()
        for issue in normalization_status.issues
    )


def test_scenario_switch_does_not_change_reference_values() -> None:
    services = build_services()
    before = services.pseg_reference.by_path(
        "Queens", "Rockaway Peninsula", "Arverne"
    )

    services.scenarios.activate("storm")
    after = services.pseg_reference.by_path(
        "Queens", "Rockaway Peninsula", "Arverne"
    )

    assert before.matches == after.matches
    assert before.total_customers_served == after.total_customers_served == 4607
