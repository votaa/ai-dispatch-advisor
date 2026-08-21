from datetime import date
from pathlib import Path

from app import data_loader
from app.scenario_generator import generate_copilot_demo_scenario, write_scenario
from app.services import build_services


def _copilot_services(tmp_path: Path, monkeypatch):
    scenario = generate_copilot_demo_scenario(start_date=date(2026, 8, 21))
    write_scenario(scenario, tmp_path)
    monkeypatch.setattr(data_loader, "DATA_ROOT", tmp_path)
    data_loader.set_active_scenario(scenario.scenario_id)
    return build_services()


def test_deterministic_acceptance_questions_use_local_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    arverne = next(
        incident
        for incident in services.incidents.list_ranked()
        if incident.municipality == "Arverne"
    )
    expected_recommendation = services.recommendations.recommend(arverne.incident_id)
    assert expected_recommendation.recommended_crew is not None

    cases = [
        ("What incident should be handled next, and why?", "priority_focus"),
        ("Which crew should handle this incident?", "recommended_crew"),
        ("Why was this crew recommended?", "recommendation_rationale"),
        ("Why was another crew not selected?", "crew_exclusion"),
        ("What hazards require attention?", "hazards"),
        ("Which critical facilities are affected?", "critical_facilities"),
        (
            "What county and township and village is this incident in?",
            "incident_geography",
        ),
        ("Which incidents are in Queens?", "incidents_by_geography"),
        (
            "Which available feasible crew is closest to this incident?",
            "closest_feasible_crew",
        ),
        ("How far away is that crew, and what is the travel time?", "crew_travel"),
        ("What information is missing or uncertain?", "data_limitations"),
    ]

    responses = {
        intent: services.copilot.respond(question, arverne.incident_id)
        for question, intent in cases
    }

    for intent, response in responses.items():
        assert response.intent == intent
        assert response.execution_mode == "local_query"
        assert response.scenario_id == "long-island-copilot-demo"
        assert response.generated_at
        assert response.data_snapshot_at
        assert response.evidence, intent
        assert response.provider is None
        assert response.model is None

    assert arverne.incident_id in responses["priority_focus"].answer
    assert expected_recommendation.recommended_crew.crew_id in responses[
        "recommended_crew"
    ].answer
    assert "proximity does not override blocking constraints" in responses[
        "crew_exclusion"
    ].answer
    assert "Arverne Emergency Services Center" in responses[
        "critical_facilities"
    ].answer
    assert "County Queens, Township Rockaway Peninsula, Village Arverne" in responses[
        "incident_geography"
    ].answer
    assert "road miles" in responses["crew_travel"].answer
    assert "not live routing" in responses["crew_travel"].answer

    synthesis = services.copilot.respond(
        "Summarize the most important operational concerns.",
        arverne.incident_id,
    )
    assert synthesis.execution_mode == "rule_based_fallback"
    assert "AI provider unavailable" in (synthesis.warning or "")


def test_geography_and_external_fact_gaps_are_not_inferred(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    arverne = next(
        incident
        for incident in services.incidents.list_ranked()
        if incident.municipality == "Arverne"
    )

    percentage = services.copilot.respond(
        "What percent of customers in Melville are affected?",
        arverne.incident_id,
    )

    assert percentage.intent == "data_limitations"
    assert "customers-served denominator" in percentage.answer
    assert "model memory" in percentage.answer

    base_root = Path(__file__).resolve().parents[2] / "data" / "scenarios"
    monkeypatch.setattr(data_loader, "DATA_ROOT", base_root)
    data_loader.set_active_scenario("base")
    base_services = build_services()
    geography = base_services.copilot.respond(
        "What county and township and village is this incident in?",
        "INC-1001",
    )

    assert geography.intent == "incident_geography"
    assert "cannot be verified" in geography.answer
    assert geography.warning == "No geographic hierarchy was inferred from model knowledge."
