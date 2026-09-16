from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app import data_loader
from app.copilot_provider import CopilotGenerationRequest, CopilotGenerationResult
from app.services import PsegLongIslandReferenceService, build_services
from app.services.reference_service import CSV_HEADERS, DEFAULT_REFERENCE_ROOT


SCENARIO_ROOT = Path(__file__).resolve().parents[2] / "data" / "scenarios"


class RecordingProvider:
    def __init__(self) -> None:
        self.requests: list[CopilotGenerationRequest] = []

    def generate(self, request: CopilotGenerationRequest) -> CopilotGenerationResult:
        self.requests.append(request)
        return CopilotGenerationResult(
            answer="Provider should not answer deterministic reference queries.",
            provider="fake",
            model="fake-v1",
        )


def _long_island_services(monkeypatch, **kwargs):
    monkeypatch.setattr(data_loader, "DATA_ROOT", SCENARIO_ROOT)
    data_loader.set_active_scenario("long-island-copilot-demo")
    return build_services(**kwargs)


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


def test_customers_served_queries_cover_all_levels_alias_and_selected_incident(
    monkeypatch,
) -> None:
    provider = RecordingProvider()
    services = _long_island_services(monkeypatch, copilot_provider=provider)
    arverne = next(
        incident
        for incident in services.incidents.list_visible()
        if incident.municipality == "Arverne"
    )

    county = services.copilot.respond(
        "How many customers are served in Nassau County?"
    )
    township = services.copilot.respond(
        "How many customers are served in the Town of Hempstead?"
    )
    village = services.copilot.respond("How many customers are served in Arverne?")
    alias = services.copilot.respond(
        "How many customers are served at Hewlett Service Center?"
    )
    selected = services.copilot.respond(
        "How many customers are served for this incident?",
        incident_id=arverne.incident_id,
    )

    for response in (county, township, village, alias, selected):
        assert response.intent == "reference_customers_served"
        assert response.execution_mode == "local_query"
        assert response.source == "approved-static-reference"
        assert response.provider is None
        assert response.model is None
        assert response.evidence
        assert all(
            item.source_type == "pseg_reference" for item in response.evidence
        )
        assert "SME-approved static customers-served value" in response.answer

    assert "**479,704 customers served**" in county.answer
    assert "**263,498 customers served**" in township.answer
    assert "**4,607 customers served**" in village.answer
    assert "Queens → Rockaway Peninsula → Arverne" in village.answer
    assert "NASSAU → HEMPSTEAD → HEWLETT" in alias.answer
    assert "**4,607 customers served**" in selected.answer
    assert provider.requests == []


def test_hierarchy_and_ambiguous_name_queries_show_source_paths(monkeypatch) -> None:
    services = _long_island_services(monkeypatch)

    rockaway = services.copilot.respond(
        "Show the PSEG Long Island hierarchy for Rockaway Peninsula."
    )
    hempstead = services.copilot.respond(
        "Show the PSEG Long Island hierarchy for Hempstead Village."
    )
    ambiguous = services.copilot.respond(
        "Which townships or villages match Calverton?"
    )

    assert rockaway.intent == "reference_hierarchy"
    assert "ROCKAWAY PENINSULA → ROCKAWAY PENINSULA" in rockaway.answer
    assert "Queens → Township Rockaway Peninsula" in rockaway.answer
    assert "(showing 9 of 9)" in rockaway.answer
    assert hempstead.intent == "reference_hierarchy"
    assert "NASSAU → HEMPSTEAD → HEMPSTEAD VILLAGE" in hempstead.answer
    assert "Nassau → Hempstead → Hempstead" in hempstead.answer
    assert ambiguous.intent == "reference_hierarchy"
    assert "2 reference paths match" in ambiguous.answer
    assert "Suffolk → Brookhaven → Calverton" in ambiguous.answer
    assert "Suffolk → Riverhead → Calverton" in ambiguous.answer
    assert ambiguous.warning == "Ambiguous area name; no customer counts were combined."


def test_aligned_percentage_uses_complete_synthetic_area_numerator(monkeypatch) -> None:
    provider = RecordingProvider()
    services = _long_island_services(monkeypatch, copilot_provider=provider)
    matching_incidents = [
        incident
        for incident in services.incidents.list_visible()
        if incident.municipality == "Melville"
    ]

    response = services.copilot.respond(
        "What percent of customers in Melville are affected?"
    )

    assert response.intent == "reference_outage_percentage"
    assert response.source == "synthetic-demo-data + approved-static-reference"
    assert (
        "**420 synthetic customers out ÷ 8,513 static customers served = 4.93%**"
        in response.answer
    )
    assert "snapshot 2026-08-24T21:13:51Z" in response.answer
    assert "source timestamp 2026-09-15T23:41:56Z" in response.answer
    assert "not a live PSEG Long Island outage percentage" in response.answer
    assert response.warning is None
    assert {item.source_type for item in response.evidence} == {
        "pseg_reference",
        "dashboard",
        "incident",
    }
    assert {
        item.record_id
        for item in response.evidence
        if item.source_type == "incident"
    } == {incident.incident_id for incident in matching_incidents}
    assert provider.requests == []


def test_full_scale_scenario_percentage_uses_complete_zero_numerator(
    monkeypatch,
) -> None:
    provider = RecordingProvider()
    monkeypatch.setattr(data_loader, "DATA_ROOT", SCENARIO_ROOT)
    data_loader.set_active_scenario("august-storm-preview-v2")
    services = build_services(copilot_provider=provider)

    assert len(services.incidents.list_visible()) == 2000
    assert not any(
        incident.municipality == "Melville"
        for incident in services.incidents.list_visible()
    )

    response = services.copilot.respond(
        "What percentage of customers in Melville are affected?"
    )

    assert response.intent == "reference_outage_percentage"
    assert (
        "**0 synthetic customers out ÷ 8,513 static customers served = 0.00%**"
        in response.answer
    )
    assert "0 incident record(s)" in response.answer
    assert "2000 active incidents evaluated" in response.response_scope
    assert response.warning is None
    assert provider.requests == []


def test_percentage_refuses_partial_geographic_coverage(monkeypatch) -> None:
    monkeypatch.setattr(data_loader, "DATA_ROOT", SCENARIO_ROOT)
    data_loader.set_active_scenario("base")
    services = build_services()

    response = services.copilot.respond(
        "What percent of customers in Melville are affected?"
    )

    assert response.intent == "reference_outage_percentage"
    assert "No percentage was calculated" in response.answer
    assert "cannot be aligned" in response.answer
    assert response.warning == (
        "Mixed-source percentage blocked because geographic coverage is partial."
    )
    assert all(item.source_type == "pseg_reference" for item in response.evidence)


def test_stale_reference_is_visible_but_percentage_is_blocked(monkeypatch) -> None:
    reference = PsegLongIslandReferenceService(
        clock=lambda: datetime(2026, 12, 16, tzinfo=timezone.utc)
    )
    services = _long_island_services(monkeypatch, pseg_reference=reference)

    served = services.copilot.respond("How many customers are served in Arverne?")
    percentage = services.copilot.respond(
        "What percent of customers in Arverne are affected?"
    )

    assert "**4,607 customers served**" in served.answer
    assert served.warning is not None
    assert "older than 90 days" in served.warning
    assert "No percentage was calculated" in percentage.answer
    assert percentage.warning == (
        "Mixed-source percentage blocked because the reference denominator is stale."
    )


def test_missing_and_invalid_reference_never_fall_through_to_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    provider = RecordingProvider()
    missing = PsegLongIslandReferenceService(tmp_path / "missing")
    missing_services = _long_island_services(
        monkeypatch,
        copilot_provider=provider,
        pseg_reference=missing,
    )

    missing_response = missing_services.copilot.respond(
        "How many customers are served in Nassau County?"
    )

    invalid_root = _copy_reference(tmp_path / "invalid")
    invalid_manifest = _read_manifest(invalid_root)
    invalid_manifest["artifact"]["sha256"] = "0" * 64
    _write_manifest(invalid_root, invalid_manifest)
    invalid_services = _long_island_services(
        monkeypatch,
        copilot_provider=provider,
        pseg_reference=PsegLongIslandReferenceService(invalid_root),
    )
    invalid_response = invalid_services.copilot.respond(
        "How many customers are served in Nassau County?"
    )

    assert missing_response.intent == "reference_customers_served"
    assert "reference is unavailable" in missing_response.answer
    assert invalid_response.intent == "reference_customers_served"
    assert "invalid and was rejected" in invalid_response.answer
    assert provider.requests == []


def test_zero_denominator_blocks_percentage(tmp_path: Path, monkeypatch) -> None:
    reference_root = _copy_reference(tmp_path)
    csv_path = reference_root / "customers-served.csv"
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    melville = next(row for row in rows if row["source_village"] == "MELVILLE")
    original = int(melville["customers_served"])
    melville["customers_served"] = "0"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest = _read_manifest(reference_root)
    manifest["artifact"]["sha256"] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    manifest["total_customers_served"] -= original
    _write_manifest(reference_root, manifest)
    reference = PsegLongIslandReferenceService(
        reference_root,
        clock=lambda: datetime(2026, 9, 16, tzinfo=timezone.utc),
    )
    services = _long_island_services(monkeypatch, pseg_reference=reference)

    response = services.copilot.respond(
        "What percent of customers in Melville are affected?"
    )

    assert response.warning == (
        "Mixed-source percentage blocked because division by zero is not allowed."
    )
    assert "denominator is zero" in response.answer


def test_missing_scenario_timestamp_blocks_percentage(tmp_path: Path, monkeypatch) -> None:
    scenario_id = "long-island-copilot-demo"
    scenario_dir = tmp_path / scenario_id
    shutil.copytree(SCENARIO_ROOT / scenario_id, scenario_dir)
    manifest_path = scenario_dir / "scenario.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("freshness")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(data_loader, "DATA_ROOT", tmp_path)
    data_loader.set_active_scenario(scenario_id)
    services = build_services()

    response = services.copilot.respond(
        "What percent of customers in Melville are affected?"
    )

    assert response.warning == (
        "Mixed-source percentage blocked because numerator freshness is unavailable."
    )
    assert "no approved snapshot timestamp" in response.answer


def test_reference_queries_do_not_mutate_reference_or_dispatch_state(monkeypatch) -> None:
    services = _long_island_services(monkeypatch)
    csv_path = DEFAULT_REFERENCE_ROOT / "customers-served.csv"
    checksum_before = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    assignments_before = services.assignments.list_active()

    response = services.copilot.respond(
        "What percent of customers in Melville are affected?"
    )

    assert response.safety_note.endswith("does not execute dispatch actions.")
    assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == checksum_before
    assert services.assignments.list_active() == assignments_before
