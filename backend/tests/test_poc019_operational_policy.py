import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.domain.models import Incident
from app.optimization.critical_facility import resolve_critical_facility_impact
from app.optimization.contracts import OptimizationRequest
from app.optimization.deterministic_engine import DeterministicOptimizationEngine
from app.optimization.policy import (
    DEFAULT_RECOMMENDATION_POLICY,
    POC019_OPERATIONAL_RECOMMENDATION_POLICY,
    RecommendationPolicy,
    configured_recommendation_policy,
    recommendation_policy_for_version,
)
from app.services.assignment_service import AssignmentService
from app.services.container import build_services
from app.services.crew_service import CrewService
from app.services.errors import IncidentRankingWithheldError
from app.services.incident_service import IncidentService
from app.services.recommendation_service import RecommendationService


REPO_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_ROOT = REPO_ROOT / "data" / "evaluation-previews" / "poc-019-cf-full-v2"


def _csv_rows(name: str) -> list[dict[str, str]]:
    with (EVALUATION_ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _operational_incidents() -> tuple[list[Incident], list[dict[str, str]]]:
    facilities = _csv_rows("CriticalFacilities.csv")
    incidents = []
    for row in _csv_rows("PendingIncidents.csv"):
        incident = Incident.model_validate(row)
        impact = resolve_critical_facility_impact(incident, facilities)
        incidents.append(
            incident.model_copy(
                update={
                    "critical_facility_level": impact.level,
                    "matched_critical_facility_ids": impact.matched_facility_ids,
                    "ranking_status": impact.ranking_status,
                    "ranking_warning": impact.warning_message,
                }
            )
        )
    return incidents, facilities


def test_operational_policy_versions_and_weights_are_explicit() -> None:
    policy = POC019_OPERATIONAL_RECOMMENDATION_POLICY

    assert policy.algorithm_version == "deterministic-scoring-v3"
    assert policy.policy_version == "incident-priority-cf-level-v1"
    assert policy.incident_scoring.critical_facility_weights.model_dump() == {
        "level_1": 120,
        "level_2": 80,
        "level_3": 40,
    }
    assert [band.model_dump() for band in policy.score_bands] == [
        {"band_id": "operational_band_1", "minimum": 0, "maximum": 99},
        {"band_id": "operational_band_2", "minimum": 100, "maximum": 199},
        {"band_id": "operational_band_3", "minimum": 200, "maximum": 299},
        {"band_id": "operational_band_4", "minimum": 300, "maximum": None},
    ]


def test_policy_selector_defaults_to_operational_policy_and_supports_rollback(
    monkeypatch,
) -> None:
    monkeypatch.delenv("AIDA_INCIDENT_POLICY_VERSION", raising=False)
    assert configured_recommendation_policy() is POC019_OPERATIONAL_RECOMMENDATION_POLICY

    monkeypatch.setenv("AIDA_INCIDENT_POLICY_VERSION", "incident-priority-v1")
    assert configured_recommendation_policy() is DEFAULT_RECOMMENDATION_POLICY

    assert (
        recommendation_policy_for_version("incident-priority-cf-level-v1")
        is POC019_OPERATIONAL_RECOMMENDATION_POLICY
    )

    with pytest.raises(ValueError, match="Unsupported AIDA incident policy"):
        recommendation_policy_for_version("unreviewed-policy")


def test_service_container_honors_explicit_operational_policy(monkeypatch) -> None:
    monkeypatch.setenv(
        "AIDA_INCIDENT_POLICY_VERSION",
        "incident-priority-cf-level-v1",
    )

    services = build_services()

    critical_incident = next(
        incident
        for incident in services.incidents.list_visible()
        if incident.critical_facility
    )
    assert critical_incident.critical_facility_level in {1, 2, 3}


@pytest.mark.parametrize(
    "bands",
    [
        [],
        [{"band_id": "bad", "minimum": 1, "maximum": None}],
        [
            {"band_id": "first", "minimum": 0, "maximum": 99},
            {"band_id": "gap", "minimum": 101, "maximum": None},
        ],
        [
            {"band_id": "open", "minimum": 0, "maximum": None},
            {"band_id": "after", "minimum": 100, "maximum": None},
        ],
    ],
)
def test_policy_rejects_invalid_score_bands(bands) -> None:
    payload = POC019_OPERATIONAL_RECOMMENDATION_POLICY.model_dump()
    payload["score_bands"] = bands

    with pytest.raises(ValidationError, match="score band"):
        RecommendationPolicy.model_validate(payload)


def test_resolver_applies_highest_level_once_and_retains_evidence() -> None:
    incidents, facilities = _operational_incidents()
    incident = next(row for row in incidents if row.incident_id == "P019-MULTI-L1-L3")
    impact = resolve_critical_facility_impact(incident, facilities)

    assert impact.level == 1
    assert impact.ranking_status == "ranked"
    assert impact.matched_facility_ids == ["FAC-MULTI-L1", "FAC-MULTI-L3A"]

    result = DeterministicOptimizationEngine(
        POC019_OPERATIONAL_RECOMMENDATION_POLICY
    ).evaluate_incidents([incident])[0]
    facility_factor = next(
        factor for factor in result.score.contributions if factor.factor_id == "critical_facility"
    )
    assert facility_factor.contribution == 120


def test_resolver_withholds_mixed_unknown_data_and_missing_linkage() -> None:
    incidents, _facilities = _operational_incidents()
    incident = next(row for row in incidents if row.incident_id == "P019-L1")
    known = {
        "facility_id": "FAC-KNOWN",
        "region": incident.region,
        "feeder": incident.feeder,
        "priority_level": "critical",
    }
    unknown = {
        "facility_id": "FAC-UNKNOWN-MIXED",
        "region": incident.region,
        "feeder": incident.feeder,
        "priority_level": "",
    }

    mixed = resolve_critical_facility_impact(incident, [known, unknown])
    missing = resolve_critical_facility_impact(incident, [])

    assert mixed.ranking_status == "withheld"
    assert mixed.warning_code == "unknown_critical_facility_level"
    assert missing.ranking_status == "withheld"
    assert missing.warning_code == "critical_facility_missing_link"


def test_recommendation_explanation_identifies_resolved_level_and_facilities() -> None:
    incidents, _facilities = _operational_incidents()
    incident = next(row for row in incidents if row.incident_id == "P019-MULTI-L1-L3")
    engine = DeterministicOptimizationEngine(POC019_OPERATIONAL_RECOMMENDATION_POLICY)

    recommendation = engine.recommend(
        OptimizationRequest(
            scenario_id="poc-019-cf-full-v2",
            incident=incident,
            crews=[],
            assignments=[],
        )
    )

    factor = next(
        row
        for row in recommendation.explanation.factors
        if row.factor_id == "critical_facility"
    )
    assert factor.contribution == 120
    assert factor.evidence == (
        "Resolved Level 1 from facility IDs: FAC-MULTI-L1, FAC-MULTI-L3A"
    )


def test_unknown_facility_is_visible_but_withheld_from_ranking() -> None:
    rows = _csv_rows("PendingIncidents.csv")
    unknown_row = next(row for row in rows if row["incident_id"] == "P019-UNKNOWN")
    facilities = _csv_rows("CriticalFacilities.csv")
    assignments = AssignmentService(
        active_scenario_id=lambda: "poc-019-cf-full-v2",
        baseline_assignments=lambda: [],
        accepted_assignments=lambda _scenario_id: [],
    )
    service = IncidentService(
        active_scenario_id=lambda: "poc-019-cf-full-v2",
        incident_rows=lambda: [unknown_row],
        crew_rows=lambda: [],
        critical_facility_rows=lambda: facilities,
        latest_decisions=lambda _scenario_id: {},
        assignments=assignments,
        optimization_engine=DeterministicOptimizationEngine(
            POC019_OPERATIONAL_RECOMMENDATION_POLICY
        ),
    )

    assert service.list_ranked() == []
    visible = service.list_visible()
    assert len(visible) == 1
    assert visible[0].ranking_status == "withheld"
    assert visible[0].ranking_warning.startswith("Critical-facility level is unknown")
    assert service.get("P019-UNKNOWN").incident_id == "P019-UNKNOWN"

    crews = CrewService(
        crew_rows=lambda: [],
        incident_rows=lambda: [unknown_row],
        assignments=assignments,
    )
    recommendation_service = RecommendationService(
        active_scenario_id=lambda: "poc-019-cf-full-v2",
        incidents=service,
        crews=crews,
        assignments=assignments,
        optimization_engine=DeterministicOptimizationEngine(
            POC019_OPERATIONAL_RECOMMENDATION_POLICY
        ),
    )
    with pytest.raises(IncidentRankingWithheldError) as exc_info:
        recommendation_service.recommend("P019-UNKNOWN")
    assert exc_info.value.matched_facility_ids == ["FAC-UNKNOWN"]


def test_withheld_optimization_uses_typed_api_conflict(monkeypatch) -> None:
    from app import main

    rows = _csv_rows("PendingIncidents.csv")
    unknown_row = next(row for row in rows if row["incident_id"] == "P019-UNKNOWN")
    assignments = AssignmentService(
        active_scenario_id=lambda: "poc-019-cf-full-v2",
        baseline_assignments=lambda: [],
        accepted_assignments=lambda _scenario_id: [],
    )
    incident_service = IncidentService(
        active_scenario_id=lambda: "poc-019-cf-full-v2",
        incident_rows=lambda: [unknown_row],
        crew_rows=lambda: [],
        critical_facility_rows=lambda: _csv_rows("CriticalFacilities.csv"),
        latest_decisions=lambda _scenario_id: {},
        assignments=assignments,
        optimization_engine=DeterministicOptimizationEngine(
            POC019_OPERATIONAL_RECOMMENDATION_POLICY
        ),
    )
    crews = CrewService(
        crew_rows=lambda: [],
        incident_rows=lambda: [unknown_row],
        assignments=assignments,
    )
    recommendation_service = RecommendationService(
        active_scenario_id=lambda: "poc-019-cf-full-v2",
        incidents=incident_service,
        crews=crews,
        assignments=assignments,
        optimization_engine=DeterministicOptimizationEngine(
            POC019_OPERATIONAL_RECOMMENDATION_POLICY
        ),
    )
    monkeypatch.setattr(
        main,
        "services",
        SimpleNamespace(recommendations=recommendation_service),
    )

    response = TestClient(main.app).post(
        "/api/optimize",
        json={"incident_id": "P019-UNKNOWN"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "incident_ranking_withheld"
    assert response.json()["error"]["entity_id"] == "P019-UNKNOWN"
    assert response.json()["error"]["details"][0]["matched_facility_ids"] == [
        "FAC-UNKNOWN"
    ]


def test_operational_engine_matches_all_approved_poc019_pairs_and_scores() -> None:
    incidents, _facilities = _operational_incidents()
    incidents_by_id = {incident.incident_id: incident for incident in incidents}
    engine = DeterministicOptimizationEngine(POC019_OPERATIONAL_RECOMMENDATION_POLICY)
    evaluations = {
        result.incident.incident_id: result.score
        for result in engine.evaluate_incidents(incidents)
    }
    expected = json.loads((EVALUATION_ROOT / "ExpectedResults.json").read_text())

    assert [
        incident.incident_id for incident in engine.rank_incidents(incidents)
    ] == expected["candidate"]["ranked_incident_ids"]

    for case in _csv_rows("EvaluationCases.csv"):
        left_id = case["left_incident_id"]
        right_id = case["right_incident_id"]
        expected_relation = case["expected_candidate_relation"]
        if expected_relation == "review":
            assert left_id not in evaluations
            assert incidents_by_id[left_id].ranking_status == "withheld"
            continue

        ranked_ids = [
            incident.incident_id
            for incident in engine.rank_incidents(
                [incidents_by_id[left_id], incidents_by_id[right_id]]
            )
        ]
        assert ranked_ids == [left_id, right_id], case["case_id"]

    controlled_ids = {
        incident_id
        for case in _csv_rows("EvaluationCases.csv")
        for incident_id in (case["left_incident_id"], case["right_incident_id"])
    }
    for incident_id in controlled_ids & evaluations.keys():
        assert evaluations[incident_id].total_score == expected["candidate"]["incidents"][
            incident_id
        ]["total_score"]
