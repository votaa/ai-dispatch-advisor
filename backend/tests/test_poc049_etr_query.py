from datetime import date, datetime, timedelta, timezone

from app import data_loader
from app.domain.models import Incident, ScenarioTemporal
from app.scenario_generator import generate_copilot_demo_scenario, write_scenario
from app.scenario_service import ScenarioDescriptor
from app.services import build_services
from app.services.etr_query_service import analyze_etrs, is_etr_count_question


NOW = datetime(2026, 9, 29, 20, 0, 44, tzinfo=timezone(timedelta(hours=-4)))


def snapshot(index=1, count=1, *, cutoff=None, timeline=False):
    temporal = ScenarioTemporal.model_validate({
        "kind": "timeline_snapshot" if timeline else "single_snapshot",
        "as_of_at": cutoff or NOW - timedelta(hours=2),
        "etr_distribution": [{"range": "null", "percent": 100}],
        **({"timeline_id": "poc049", "snapshot_index": index, "snapshot_count": count} if timeline else {}),
    })
    return ScenarioDescriptor.model_construct(scenario_id=f"step-{index}", temporal=temporal)


def incident(identifier, etr=None, status=None, withheld=False):
    return Incident.model_construct(
        incident_id=identifier,
        etr=etr,
        etr_status=status,
        ranking_status="withheld" if withheld else "ranked",
    )


def at(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def test_minute_boundaries_reasons_and_complete_inventory():
    rows = [
        incident("expired", at(-11)),
        incident("due-now-edge", at(-10)),
        incident("due-now", at(-1)),
        incident("this-minute", at(0)),
        incident("soon", at(60), withheld=True),
        incident("future", at(61)),
        incident("assessing", status="assessing_conditions"),
        incident("missing"),
        incident("invalid", "Unknown"),
    ]
    selected = snapshot()
    result = analyze_etrs(rows, selected, [selected], NOW, "current")
    assert result.status == "answered"
    assert result.counts.model_dump() == {
        "expired": 1, "due_now": 3, "due_soon": 1, "valid_future": 1, "unavailable": 3
    }
    assert result.evaluated_incident_count == 9
    assert result.past_due_total == 3
    assert result.past_due_within_due_now == 2
    assert result.unavailable_assessing_conditions == 1
    assert result.unavailable_missing_or_invalid == 2
    assert any(item.incident_id == "soon" for item in result.examples)
    assert {item.unavailable_reason for item in result.examples if item.category == "unavailable"} == {
        "assessing_conditions", "missing_or_invalid"
    }
    assert result.evaluation_at == NOW


def test_future_stale_legacy_and_explicit_preview_gates():
    first = snapshot(1, 3, cutoff=NOW - timedelta(hours=12), timeline=True)
    second = snapshot(2, 3, cutoff=NOW - timedelta(hours=1), timeline=True)
    third = snapshot(3, 3, cutoff=NOW + timedelta(hours=11), timeline=True)
    siblings = [first, second, third]
    row = incident("one", at(20))
    stale = analyze_etrs([row], first, siblings, NOW, "current")
    assert stale.status == "blocked" and stale.temporal_status == "stale"
    assert stale.suggested_scenario_id == second.scenario_id
    assert stale.counts is None
    historical = analyze_etrs([row], first, siblings, NOW, "scenario_preview")
    assert historical.status == "answered" and historical.evaluation_at == first.temporal.as_of_at
    assert analyze_etrs([row], second, siblings, NOW, "current").status == "answered"
    future = analyze_etrs([row], third, siblings, NOW, "current")
    assert future.status == "blocked" and future.temporal_status == "future"
    preview = analyze_etrs([row], third, siblings, NOW, "scenario_preview")
    assert preview.status == "answered" and preview.evaluation_at == third.temporal.as_of_at
    assert preview.counts.expired == 1
    future_single = snapshot(cutoff=NOW + timedelta(hours=1))
    assert analyze_etrs([row], future_single, [future_single], NOW, "current").status == "blocked"
    incomplete = analyze_etrs([row], first, siblings[:2], NOW, "scenario_preview")
    assert incomplete.status == "blocked" and incomplete.temporal_status == "unavailable"
    legacy = ScenarioDescriptor.model_construct(scenario_id="legacy", temporal=None)
    assert analyze_etrs([row], legacy, [legacy], NOW, "current").temporal_status == "legacy"


def test_etr_question_routes_before_provider_and_uses_typed_evidence(tmp_path, monkeypatch):
    generated = generate_copilot_demo_scenario(start_date=date(2026, 8, 21))
    write_scenario(generated, tmp_path)
    monkeypatch.setattr(data_loader, "DATA_ROOT", tmp_path)
    data_loader.set_active_scenario(generated.scenario_id)
    services = build_services(copilot_clock=lambda: NOW)
    selected = snapshot()
    monkeypatch.setattr(services.scenarios, "active", lambda: selected)
    monkeypatch.setattr(services.scenarios, "list", lambda: [selected])
    template = services.incidents.list_visible()[0]
    rows = [template.model_copy(update={"incident_id": f"I-{index}", "etr": at(index * 10)}) for index in range(8)]
    monkeypatch.setattr(services.incidents, "list_visible", lambda: rows)
    monkeypatch.setattr(services.incidents, "list_ranked", lambda: [])
    assert is_etr_count_question("How many incidents have expired or coming due soon ETRs?")
    response = services.copilot.respond("How many incidents have expired or coming due soon ETRs?")
    assert response.intent == "etr_time_counts"
    assert response.execution_mode == "local_query"
    assert response.etr_analysis.evaluated_incident_count == 8
    assert response.etr_analysis.counts.due_soon == 6
    assert response.etr_analysis.counts.due_now == 1
    assert response.etr_analysis.counts.valid_future == 1
    assert response.etr_analysis.evaluation_at == NOW
    assert response.request_time.received_at == NOW.astimezone(timezone.utc)
    assert response.data_snapshot_at is None  # ETR answers use their typed cutoff instead of weather freshness.
    assert response.evidence
