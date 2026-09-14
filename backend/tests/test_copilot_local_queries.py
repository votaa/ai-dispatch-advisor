from datetime import date
from pathlib import Path

import pytest

from app import data_loader
from app.copilot_provider import CopilotGenerationRequest, CopilotGenerationResult
from app.domain.models import Incident
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


def _poc025_inventory(services, monkeypatch) -> list[Incident]:
    template = services.incidents.list_visible()[0]
    incidents = [
        template.model_copy(
            update={
                "incident_id": "INC-POC025-L1-MULTI",
                "municipality": "Level One Village",
                "feeder": "FDR-POC025-L1",
                "critical_facility": True,
                "critical_facility_level": 1,
                "matched_critical_facility_ids": ["FAC-L1", "FAC-L3-A"],
            }
        ),
        template.model_copy(
            update={
                "incident_id": "INC-POC025-L2",
                "municipality": "Level Two Village",
                "feeder": "FDR-POC025-L2",
                "critical_facility": True,
                "critical_facility_level": 2,
                "matched_critical_facility_ids": ["FAC-L2"],
            }
        ),
        template.model_copy(
            update={
                "incident_id": "INC-POC025-L3",
                "municipality": "Level Three Village",
                "feeder": "FDR-POC025-L3",
                "critical_facility": True,
                "critical_facility_level": 3,
                "matched_critical_facility_ids": ["FAC-L3-B"],
            }
        ),
        template.model_copy(
            update={
                "incident_id": "INC-POC025-UNKNOWN",
                "municipality": "Unknown Village",
                "feeder": "FDR-POC025-U",
                "critical_facility": True,
                "critical_facility_level": None,
                "matched_critical_facility_ids": ["FAC-U"],
                "ranking_status": "withheld",
                "ranking_warning": (
                    "Critical-facility level is unknown for matched facility IDs: FAC-U"
                ),
            }
        ),
        template.model_copy(
            update={
                "incident_id": "INC-POC025-MISSING",
                "municipality": "Missing Link Village",
                "feeder": "FDR-POC025-MISSING",
                "critical_facility": True,
                "critical_facility_level": None,
                "matched_critical_facility_ids": [],
                "ranking_status": "withheld",
                "ranking_warning": (
                    "Critical-facility incident has no matching facility for its region and feeder."
                ),
            }
        ),
        template.model_copy(
            update={
                "incident_id": "INC-POC025-NO-CF",
                "municipality": "No Facility Village",
                "feeder": "FDR-POC025-NONE",
                "critical_facility": False,
                "critical_facility_level": None,
                "matched_critical_facility_ids": [],
            }
        ),
    ]
    facilities = [
        {
            "facility_id": "FAC-L1",
            "facility_name": "Level One Facility",
            "facility_type": "hospital",
            "priority_level": "critical",
        },
        {
            "facility_id": "FAC-L2",
            "facility_name": "Level Two Facility",
            "facility_type": "emergency services",
            "priority_level": "high",
        },
        {
            "facility_id": "FAC-L3-A",
            "facility_name": "Level Three Facility A",
            "facility_type": "healthcare",
            "priority_level": "medium",
        },
        {
            "facility_id": "FAC-L3-B",
            "facility_name": "Private Health Device (LSE)",
            "facility_type": "healthcare",
            "priority_level": "medium",
        },
        {
            "facility_id": "FAC-U",
            "facility_name": "Unknown Level Facility",
            "facility_type": "other",
            "priority_level": "unsupported",
        },
    ]
    rankable = incidents[:3] + [incidents[5]]
    visible = rankable + sorted(incidents[3:5], key=lambda incident: incident.incident_id)
    monkeypatch.setattr(services.incidents, "list_ranked", lambda: rankable)
    monkeypatch.setattr(services.incidents, "list_visible", lambda: visible)
    monkeypatch.setattr(services.context, "critical_facilities", lambda: facilities)
    return incidents


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
        assert response.request_time is not None
        assert response.request_time.timezone == "UTC"
        assert response.request_time.source == "backend_server_clock"
        assert response.request_time.clock_skew == "not_measured"
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
    assert "### Highest-priority rankable hazard incidents (showing" in responses[
        "hazards"
    ].answer
    assert (
        "### Highest-priority rankable critical-facility incidents (showing"
        in responses["critical_facilities"].answer
    )
    assert (
        "### Highest-priority rankable incidents matching Queens (showing"
        in responses["incidents_by_geography"].answer
    )
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
        f"{critical_count} rankable incident(s) are marked with critical-facility impact."
    )
    assert (
        "Matched incident-to-facility records in incident priority and facility source order"
        in critical_response.answer
    )
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


def test_critical_facility_level_breakdown_uses_resolved_visible_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    _poc025_inventory(services, monkeypatch)

    response = services.copilot.respond(
        "What is the breakdown of critical facilities by level?"
    )

    assert response.intent == "critical_facility_levels"
    assert response.execution_mode == "local_query"
    assert response.provider is None
    assert "| Level 1 | 1 | +120 |" in response.answer
    assert "| Level 2 | 1 | +80 |" in response.answer
    assert "| Level 3 | 1 | +40 |" in response.answer
    assert "| Unknown/withheld | 2 | Withheld |" in response.answer
    assert "| Level 1 | 1 |" in response.answer
    assert "| Level 2 | 1 |" in response.answer
    assert "| Level 3 | 2 |" in response.answer
    assert "| Unknown | 1 |" in response.answer
    assert response.answer.count("| INC-POC025-L1-MULTI |") == 1
    assert "INC-POC025-NO-CF" not in response.answer
    assert (
        "### Complete visible affected-incident counts "
        "(all 5 critical-facility incidents)"
    ) in response.answer
    assert (
        "### Complete matched facility-record counts (all 5 matched records)"
    ) in response.answer
    assert (
        "### Priority-ordered visible critical-facility incidents "
        "(rankable first; withheld by incident ID; showing 5 of 5)"
    ) in response.answer
    assert (
        "Unknown/withheld incidents contribute 2 record(s) to the complete "
        "affected-incident calculation; 2 appear in the displayed subset."
    ) in response.answer
    assert response.warning == (
        "2 critical-facility incident(s) are withheld from ranking because their "
        "facility level is unresolved."
    )
    assert len(response.evidence) == 10


@pytest.mark.parametrize(
    ("question", "expected_scope", "expected_heading"),
    [
        (
            "How many Level 1 critical facilities are affected?",
            "Level 1 — 1 affected incident(s)",
            "Highest-priority rankable Level 1 incidents (showing 1 of 1)",
        ),
        (
            "Which incidents affect Level Two facilities?",
            "Level 2 — 1 affected incident(s)",
            "Highest-priority rankable Level 2 incidents (showing 1 of 1)",
        ),
        (
            "Show L3 critical-facility incidents.",
            "Level 3 — 1 affected incident(s)",
            "Highest-priority rankable Level 3 incidents (showing 1 of 1)",
        ),
        (
            "Are any critical-facility levels unknown?",
            "Unknown/withheld — 2 affected incident(s)",
            (
                "Ranking-withheld unknown-level incidents in incident ID order "
                "(showing 2 of 2)"
            ),
        ),
    ],
)
def test_critical_facility_level_filters_have_explicit_subset_headings(
    tmp_path: Path,
    monkeypatch,
    question: str,
    expected_scope: str,
    expected_heading: str,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    _poc025_inventory(services, monkeypatch)

    response = services.copilot.respond(question)

    assert response.intent == "critical_facility_levels"
    assert f"The requested {expected_scope.split(' — ')[0]} scope contains" in response.answer
    assert f"**Requested scope:** {expected_scope}." in response.answer
    assert f"### {expected_heading}" in response.answer


def test_critical_facility_level_incident_detail_uses_highest_level_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    _poc025_inventory(services, monkeypatch)

    response = services.copilot.respond(
        "What level and scoring contribution apply to INC-POC025-L1-MULTI?"
    )

    assert response.intent == "critical_facility_levels"
    assert "**Applied level:** Level 1" in response.answer
    assert "**Critical-facility score contribution:** +120" in response.answer
    assert "only the highest resolved level once" in response.answer
    assert (
        "### Matched facility records in facility ID order (showing 2 of 2)"
    ) in response.answer
    assert "| FAC-L1 | Level One Facility | hospital | Level 1 |" in response.answer
    assert (
        "| FAC-L3-A | Level Three Facility A | healthcare | Level 3 |"
    ) in response.answer


def test_unknown_critical_facility_incident_stays_visible_and_withheld(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    incidents = _poc025_inventory(services, monkeypatch)
    unknown = next(row for row in incidents if row.incident_id == "INC-POC025-UNKNOWN")

    response = services.copilot.respond(
        "What critical-facility level applies to this incident?",
        incident_id=unknown.incident_id,
    )

    assert response.intent == "critical_facility_levels"
    assert "**Applied level:** Unknown/withheld" in response.answer
    assert "**Critical-facility score contribution:** Withheld" in response.answer
    assert "**Ranking status:** withheld" in response.answer
    assert unknown.ranking_warning in response.answer
    assert response.warning == unknown.ranking_warning


def test_critical_facility_level_queries_bypass_the_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    provider = RecordingProvider()
    scenario = generate_copilot_demo_scenario(start_date=date(2026, 8, 21))
    write_scenario(scenario, tmp_path)
    monkeypatch.setattr(data_loader, "DATA_ROOT", tmp_path)
    data_loader.set_active_scenario(scenario.scenario_id)
    services = build_services(copilot_provider=provider)

    response = services.copilot.respond("Break down critical facilities by level.")

    assert response.intent == "critical_facility_levels"
    assert response.execution_mode == "local_query"
    assert provider.requests == []


def test_poc026_published_scenario_supplies_all_resolved_facility_levels(
    monkeypatch,
) -> None:
    scenario_root = Path(__file__).resolve().parents[2] / "data" / "scenarios"
    monkeypatch.setattr(data_loader, "DATA_ROOT", scenario_root)
    data_loader.set_active_scenario("august-storm-preview-v2")
    services = build_services()

    response = services.copilot.respond("Break down critical facilities by level.")

    assert response.scenario_id == "august-storm-preview-v2"
    assert "| Level 1 | 5 | +120 |" in response.answer
    assert "| Level 2 | 3 | +80 |" in response.answer
    assert "| Level 3 | 7 | +40 |" in response.answer
    assert "| Unknown/withheld | 0 | Withheld |" in response.answer
    assert "### Complete matched facility-record counts (all 11 matched records)" in response.answer
    assert "| Level 1 | 5 |" in response.answer
    assert "| Level 2 | 3 |" in response.answer
    assert "| Level 3 | 3 |" in response.answer


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


def test_severity_counts_use_complete_rankable_scope_and_ordered_examples(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    incidents = services.incidents.list_ranked()
    expected = sum(incident.severity.casefold() == "low" for incident in incidents)
    expected_withheld = sum(
        incident.severity.casefold() == "low"
        for incident in services.incidents.list_withheld()
    )

    response = services.copilot.respond("How many severity Low incidents?")

    assert response.intent == "incident_severity_counts"
    assert response.execution_mode == "local_query"
    assert response.provider is None
    assert response.answer.startswith(
        f"{expected} rankable active incident(s) have **low** severity."
    )
    assert (
        f"{expected_withheld} ranking-withheld **low** incident(s) are excluded"
        in response.answer
    )
    assert (
        "### Highest-priority rankable low incidents "
        f"(showing {min(expected, 10)} of {expected})"
    ) in response.answer
    assert len(response.evidence) == expected


@pytest.mark.parametrize(
    "question",
    [
        "How many customers are out of service across all of the active incidents?",
        "What is the total customers out?",
        "How many customers are affected across all active incidents?",
        "Show the aggregate customers out.",
    ],
)
def test_customer_outage_aggregates_use_every_visible_incident(
    tmp_path: Path,
    monkeypatch,
    question: str,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    incidents = services.incidents.list_visible()
    assert len(incidents) == 24
    assert sum(incident.customers_out for incident in incidents) == 23_414

    response = services.copilot.respond(
        question,
        incident_id=incidents[0].incident_id,
    )

    assert response.intent == "all_incident_customer_aggregate"
    assert response.execution_mode == "local_query"
    assert response.provider is None
    assert response.answer.startswith(
        "## Customer outage aggregate\n\n"
        "24 active incidents report **23,414 customers out**"
    )
    assert "Highest-priority rankable incidents (showing 10 of 24)" in response.answer
    assert (
        "Ranking-withheld incidents contribute 0 record(s) to this complete "
        "visible-incident calculation; 0 appear in the displayed subset."
    ) in response.answer
    assert len(response.evidence) == 11
    assert response.evidence[0].source_type == "dashboard"


def test_customer_outage_aggregate_handles_an_empty_inventory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    monkeypatch.setattr(services.incidents, "list_ranked", lambda: [])
    monkeypatch.setattr(services.incidents, "list_visible", lambda: [])

    response = services.copilot.respond("What is the total customers out?")

    assert response.intent == "all_incident_customer_aggregate"
    assert "0 active incidents report **0 customers out**" in response.answer
    assert "Incident details" not in response.answer
    assert len(response.evidence) == 1


def test_empty_rankable_queries_do_not_render_a_result_subset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    monkeypatch.setattr(services.incidents, "list_ranked", lambda: [])
    monkeypatch.setattr(services.incidents, "list_visible", lambda: [])
    monkeypatch.setattr(services.crews, "list", lambda: [])

    severity = services.copilot.respond("How many severity Low incidents?")
    geography = services.copilot.respond("Which incidents are in Queens?")
    crews = services.copilot.respond("Show available crews")
    hazards = services.copilot.respond("What hazards require attention?")

    assert "no result subset is displayed" in severity.answer
    assert geography.answer == (
        "No incidents in the active scenario resolve to Queens. "
        "No result subset is displayed."
    )
    assert crews.answer == (
        "## Crew query\n\n0 crews match (available). No result subset is displayed."
    )
    assert "no result subset is displayed" in hazards.answer
    assert all("###" not in response.answer for response in (severity, geography, crews, hazards))


def test_customer_outage_aggregate_discloses_withheld_records_in_visible_subset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    incidents = _poc025_inventory(services, monkeypatch)

    response = services.copilot.respond("What is the total customers out?")

    assert response.intent == "all_incident_customer_aggregate"
    assert (
        "Ranking-withheld incidents contribute 2 record(s) to this complete "
        "visible-incident calculation; 2 appear in the displayed subset."
    ) in response.answer
    assert (
        "### Priority-ordered visible incidents (rankable first; withheld by incident ID; "
        f"showing {len(incidents)} of {len(incidents)})"
    ) in response.answer


def test_customer_outage_aggregate_updates_after_scenario_switch(
    monkeypatch,
) -> None:
    scenario_root = Path(__file__).resolve().parents[2] / "data" / "scenarios"
    monkeypatch.setattr(data_loader, "DATA_ROOT", scenario_root)
    data_loader.set_active_scenario("base")
    services = build_services()

    base_incidents = services.incidents.list_visible()
    base_response = services.copilot.respond("What is the total customers out?")
    data_loader.set_active_scenario("long-island-copilot-demo")
    demo_response = services.copilot.respond("What is the total customers out?")

    assert f"{len(base_incidents)} active incidents" in base_response.answer
    assert base_response.scenario_id == "base"
    assert "24 active incidents report **24,427 customers out**" in demo_response.answer
    assert demo_response.scenario_id == "long-island-copilot-demo"


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
    assert (
        "### Matching crews in scenario order "
        f"(showing {min(len(expected), 10)} of {len(expected)})"
    ) in response.answer
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
    assert "Matching crews in scenario order (showing 1 of 1)" in response.answer
    assert crew.crew_id in response.answer


def test_crew_query_can_target_selected_crew_context(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    crew = services.crews.list()[0]
    response = services.copilot.respond(
        "What is the status of this crew?",
        crew_id=crew.crew_id,
    )

    assert response.intent == "crew_query"
    assert response.answer.startswith("## Crew query\n\n1 crew(s) match")
    assert crew.crew_id in response.answer


def test_incident_assignment_queries_use_explicit_and_selected_incident_scope(
    monkeypatch,
) -> None:
    base_root = Path(__file__).resolve().parents[2] / "data" / "scenarios"
    monkeypatch.setattr(data_loader, "DATA_ROOT", base_root)
    data_loader.set_active_scenario("base")
    services = build_services()

    responses = [
        services.copilot.respond("Which crews are assigned to INC-1002?"),
        services.copilot.respond(
            "Summarize this incident and assigned crew(s) for this incident only.",
            incident_id="INC-1002",
            crew_id="CR-02",
        ),
    ]

    for response in responses:
        assert response.intent == "incident_assignments"
        assert response.execution_mode == "local_query"
        assert response.answer.startswith("## Currently assigned crews\n\n1 crew(s)")
        assert "Current assignments in scenario crew order (showing 1 of 1)" in response.answer
        assert "Central Veg Beta (CR-02)" in response.answer
        assert "South Veg India (CR-08)" not in response.answer
        assert {item.record_id for item in response.evidence} == {"INC-1002", "CR-02"}


def test_incident_assignment_query_supports_zero_and_multiple_crews(
    tmp_path: Path,
    monkeypatch,
) -> None:
    services = _copilot_services(tmp_path, monkeypatch)
    crews_by_incident: dict[str, list[str]] = {}
    for crew in services.crews.list():
        for assignment in crew.assigned_incidents:
            crews_by_incident.setdefault(assignment.incident_id, []).append(crew.crew_id)

    multiple_incident_id, expected_crew_ids = next(
        (incident_id, crew_ids)
        for incident_id, crew_ids in crews_by_incident.items()
        if len(crew_ids) > 1
    )
    multiple = services.copilot.respond(
        f"Which crews are assigned to {multiple_incident_id}?"
    )

    assert multiple.intent == "incident_assignments"
    assert multiple.answer.startswith(
        f"## Currently assigned crews\n\n{len(expected_crew_ids)} crew(s)"
    )
    assert all(crew_id in multiple.answer for crew_id in expected_crew_ids)

    unassigned = next(
        incident
        for incident in services.incidents.list_ranked()
        if incident.incident_id not in crews_by_incident
    )
    none = services.copilot.respond(
        "Which crews are assigned to this incident?",
        incident_id=unassigned.incident_id,
    )

    assert none.intent == "incident_assignments"
    assert f"0 crews are currently assigned to {unassigned.incident_id}" in none.answer
    assert {item.record_id for item in none.evidence} == {unassigned.incident_id}


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

    aggregate_response = services.copilot.respond(
        "How many customers are out across all active incidents?",
        incident.incident_id,
    )
    assert aggregate_response.intent == "all_incident_customer_aggregate"
    assert aggregate_response.execution_mode == "local_query"
    assert provider.requests == []

    grounded_response = services.copilot.respond(
        "Summarize the operational concerns for this storm.", incident.incident_id
    )
    assert grounded_response.execution_mode == "llm_grounded"
    assert len(provider.requests) == 1
    assert "POC-specific RACE instructions" in provider.requests[0].system_prompt
