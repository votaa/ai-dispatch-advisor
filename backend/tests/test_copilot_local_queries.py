from datetime import date
from pathlib import Path

from app import data_loader
from app.copilot_provider import CopilotGenerationRequest, CopilotGenerationResult
from app.scenario_generator import generate_copilot_demo_scenario, write_scenario
from app.services import build_services


class RecordingProvider:
    def __init__(self) -> None:
        self.requests: list[CopilotGenerationRequest] = []

    def generate(self, request: CopilotGenerationRequest) -> CopilotGenerationResult:
        self.requests.append(request)
        return CopilotGenerationResult(
            answer="Grounded provider summary.",
            provider="fake",
            model="fake-v1",
        )


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

    critical_count = sum(
        incident.critical_facility for incident in services.incidents.list_ranked()
    )
    critical_response = services.copilot.respond(
        "How many incidents have critical facilities on them?"
    )
    assert critical_response.execution_mode == "local_query"
    assert critical_response.intent == "critical_facilities"
    assert critical_response.answer.startswith(
        f"{critical_count} incident(s) are marked with critical-facility impact:"
    )
    assert "Matched facility records:" in critical_response.answer
    assert {item.source_type for item in critical_response.evidence} == {
        "incident",
        "critical_facility",
    }

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


def test_severity_counts_use_complete_scenario_and_markdown_examples(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    incidents = services.incidents.list_ranked()
    expected = sum(incident.severity.casefold() == "low" for incident in incidents)

    response = services.copilot.respond("How many severity Low incidents?")

    assert response.intent == "incident_severity_counts"
    assert response.execution_mode == "local_query"
    assert response.provider is None
    assert response.answer.startswith(f"{expected} active incident(s) have **low** severity.")
    assert "### Examples" in response.answer
    assert len(response.evidence) == expected


def test_crew_queries_support_combined_filters_and_bound_visible_results(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    crews = services.crews.list()
    expected = [
        crew
        for crew in crews
        if crew.status.casefold() == "available"
        and not crew.storm_ready
        and crew.home_region == "Central-Nassau"
    ]

    response = services.copilot.respond(
        "How many available crews are not storm ready in Central-Nassau?"
    )

    assert response.intent == "crew_query"
    assert response.execution_mode == "local_query"
    assert response.answer.startswith(f"## Crew query\n\n{len(expected)} crew(s) match")
    assert "Results (showing" in response.answer
    assert len(response.evidence) == len(expected)


def test_crew_query_can_target_id_and_shift_hours(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    crew = services.crews.list()[0]
    response = services.copilot.respond(
        f"Show crew {crew.crew_id} with more than 1 hour shift remaining"
    )

    assert response.intent == "crew_query"
    assert response.answer.startswith("## Crew query\n\n1 crew(s) match")
    assert crew.crew_id in response.answer


def test_action_oriented_question_does_not_execute_a_dispatch_action(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    assignments_before = services.assignments.list_active()

    response = services.copilot.respond(
        "Assign the nearest available crew to the highest-priority incident now."
    )

    assert services.assignments.list_active() == assignments_before
    assert response.safety_note == (
        "This copilot response is advisory and does not execute dispatch actions."
    )


def test_deterministic_queries_bypass_provider_and_grounded_queries_receive_race_prompt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    provider = RecordingProvider()
    scenario = generate_copilot_demo_scenario(start_date=date(2026, 8, 21))
    write_scenario(scenario, tmp_path)
    monkeypatch.setattr(data_loader, "DATA_ROOT", tmp_path)
    data_loader.set_active_scenario(scenario.scenario_id)
    services = build_services(copilot_provider=provider)
    incident = services.incidents.list_ranked()[0]

    local_response = services.copilot.respond(
        "Which crew should handle this incident?", incident.incident_id
    )
    assert local_response.execution_mode == "local_query"
    assert provider.requests == []

    grounded_response = services.copilot.respond(
        "Summarize the operational concerns for this storm.", incident.incident_id
    )
    assert grounded_response.execution_mode == "llm_grounded"
    assert len(provider.requests) == 1
    assert "POC-specific RACE instructions" in provider.requests[0].system_prompt
