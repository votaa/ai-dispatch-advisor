from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from app.optimization.policy import DEFAULT_RECOMMENDATION_POLICY
from app.poc019_evaluation_dataset import (
    DEFAULT_CANDIDATE_WEIGHTS,
    build_complete_evaluation,
    build_sample_evaluation,
    render_evaluation_files,
    write_evaluation,
)
from app.scenario_service import ScenarioService


def _candidate(package, incident_id: str):
    return package.expected_results["candidate"]["incidents"][incident_id]


def _baseline(package, incident_id: str) -> int:
    return package.expected_results["baseline"]["incidents"][incident_id]["total_score"]


def test_sample_covers_required_evaluation_categories() -> None:
    package = build_sample_evaluation()

    assert {case["category"] for case in package.cases} >= {
        "facility_level",
        "unknown_facility",
        "lse_customer_count",
        "customer_edge",
        "lse_customer_edge",
        "multiple_facilities",
        "hazard_severity",
        "hazard_precedence",
        "hazard_guard",
        "severity_precedence",
        "cf_before_age",
    }
    assert package.summary()["complete_scenario_generated"] is False
    assert package.summary()["review_status"] == "approved_sme"
    assert package.scoring_profiles["candidate"]["status"] == "sme_approved_for_complete_evaluation"


def test_lse_level_3_includes_single_and_multiple_customer_counts() -> None:
    package = build_sample_evaluation()

    assert {
        incident["customers_out"]
        for incident in package.incidents
        if incident["incident_id"].startswith("P019-LSE-L3-")
    } == {1, 19, 20, 100}
    assert _candidate(package, "P019-LSE-L3-C019")["total_score"] == 50
    assert _candidate(package, "P019-LSE-L3-C020")["total_score"] == 51
    assert _baseline(package, "P019-LSE-L3-C019") == 90
    assert _baseline(package, "P019-LSE-L3-C020") == 91


def test_customer_boundary_is_isolated_with_and_without_lse_level_3() -> None:
    package = build_sample_evaluation()

    assert _candidate(package, "P019-NOCF-C019")["total_score"] == 10
    assert _candidate(package, "P019-NOCF-C020")["total_score"] == 11
    assert _candidate(package, "P019-LSE-L3-C019")["total_score"] == 50
    assert _candidate(package, "P019-LSE-L3-C020")["total_score"] == 51
    assert {
        case["case_id"] for case in package.cases if case["category"] == "lse_customer_edge"
    } == {"LSE-L3-19-20", "LSE-L3-C019-NOCF", "LSE-L3-C020-NOCF"}


def test_multiple_facilities_apply_only_the_highest_level_once() -> None:
    package = build_sample_evaluation()

    level_1 = _candidate(package, "P019-MULTI-L1-L3")
    level_2 = _candidate(package, "P019-MULTI-L2-L3")

    assert level_1["facility_level"] == 1
    assert level_1["contributions"]["critical_facility"] == 120
    assert level_1["total_score"] == 130
    assert len(level_1["matched_facility_ids"]) == 2
    assert level_2["facility_level"] == 2
    assert level_2["contributions"]["critical_facility"] == 80
    assert level_2["total_score"] == 90


def test_unknown_facility_level_is_not_silently_scored() -> None:
    package = build_sample_evaluation()
    unknown = _candidate(package, "P019-UNKNOWN")

    assert unknown["total_score"] is None
    assert unknown["contributions"] is None
    assert unknown["warning"] == "unknown_critical_facility_level:FAC-UNKNOWN"


def test_cf_before_age_case_exposes_current_policy_question() -> None:
    package = build_sample_evaluation()

    assert _candidate(package, "P019-CF-BEFORE-AGE")["total_score"] == 90
    assert _candidate(package, "P019-OLDER-NOCF")["total_score"] == 90
    question = package.expected_results["known_policy_question"]
    assert question == {
        "case_id": "CF-BEFORE-AGE",
        "current_behavior": "age_precedes_critical_facility_level_when_total_and_severity_tie",
        "candidate_hypothesis": "critical_facility_level_precedes_age",
        "current_rank_order": ["P019-OLDER-NOCF", "P019-CF-BEFORE-AGE"],
        "candidate_hypothesis_order": ["P019-CF-BEFORE-AGE", "P019-OLDER-NOCF"],
        "review_status": "approved_sme",
    }


def test_score_band_boundaries_cover_below_at_and_above() -> None:
    package = build_sample_evaluation()
    boundaries = package.expected_results["band_boundaries"]

    assert len(boundaries) == 9
    for threshold in (100, 200, 300):
        rows = [row for row in boundaries if row["threshold"] == threshold]
        assert {(row["position"], row["score"]) for row in rows} == {
            ("below", threshold - 1),
            ("at", threshold),
            ("above", threshold + 1),
        }


def test_rendered_sample_is_deterministic_and_labels_scope() -> None:
    first = render_evaluation_files(build_sample_evaluation())
    second = render_evaluation_files(build_sample_evaluation())

    assert first == second
    assert '"generation_scope": "approved_sample"' in first["evaluation_manifest.json"]
    assert '"candidate_policy_is_operational": false' in first["evaluation_manifest.json"]


def test_all_automatic_pair_expectations_are_met() -> None:
    package = build_sample_evaluation()

    assert all(
        result["baseline_expectation_met"]
        for result in package.expected_results["case_results"]
    )
    assert all(
        result["candidate_expectation_met"] is not False
        for result in package.expected_results["case_results"]
    )


def test_override_examples_preserve_existing_action_semantics() -> None:
    package = build_sample_evaluation()
    examples = {row["example_id"]: row for row in package.override_examples}

    assert examples["OVERRIDE-BACKUP-GENERATION"]["expected_assignment_created"] is False
    assert examples["OVERRIDE-FIELD-SAFETY"]["expected_original_recommendation_preserved"] is True
    assert examples["MODIFIED-RANKED-ALTERNATIVE"]["action"] == "modified"
    assert examples["MODIFIED-RANKED-ALTERNATIVE"]["expected_assignment_created"] is True
    assert examples["OVERRIDE-MISSING-REASON"]["expected_error"] == "decision_reason_required"
    assert examples["OVERRIDE-ESCALATION"] == {
        "example_id": "OVERRIDE-ESCALATION",
        "action": "overridden",
        "reason": (
            "Escalation: supervisor directed this incident ahead of the recommended "
            "ordering due to operational conditions."
        ),
        "expected_assignment_created": False,
        "expected_original_recommendation_preserved": True,
        "expected_score_mutated": False,
        "expected_queue_reordered": False,
        "review_status": "approved_sme",
    }


def test_approved_same_band_hazard_and_guard_ordering() -> None:
    package = build_sample_evaluation()
    results = {row["case_id"]: row for row in package.expected_results["case_results"]}

    assert results["HAZ-LOW-HIGH"]["candidate_score_relation"] == "<"
    assert results["HAZ-LOW-HIGH"]["candidate_relation"] == ">"
    assert results["SAME-HAZARD-GUARD"]["candidate_score_relation"] == ">"
    assert results["SAME-HAZARD-GUARD"]["candidate_relation"] == ">"
    assert results["SEVERITY-TIE"]["candidate_score_relation"] == "="
    assert results["SEVERITY-TIE"]["candidate_relation"] == ">"


def test_complete_evaluation_is_deterministic_application_scenario(tmp_path: Path) -> None:
    package = build_complete_evaluation(incident_count=80, crew_count=40)
    first = render_evaluation_files(package)
    second = render_evaluation_files(
        build_complete_evaluation(incident_count=80, crew_count=40)
    )

    assert first == second
    assert package.summary()["complete_scenario_generated"] is True
    assert package.summary()["incidents"] == 80
    assert package.summary()["controlled_pairs"] == 17
    assert package.generation_scope == "complete_application_scenario"
    assert package.application_scenario is not None
    assert {
        "scenario.json",
        "Crews.csv",
        "Assignments.csv",
        "HistoricalRepairs.csv",
        "Weather.csv",
        "Topology.csv",
    }.issubset(first)
    target = write_evaluation(package, tmp_path)
    descriptor = ScenarioService(tmp_path, package.dataset_id).active_scenario()
    assert descriptor.validation_status == "valid"
    assert target.name == package.dataset_id


def test_write_evaluation_refuses_to_replace_existing_output(tmp_path: Path) -> None:
    package = build_sample_evaluation()
    target = write_evaluation(package, tmp_path)

    assert target.is_dir()
    assert (target / "evaluation_manifest.json").is_file()
    with pytest.raises(FileExistsError, match="already exists"):
        write_evaluation(package, tmp_path)


def test_invalid_candidate_weights_are_rejected_without_changing_policy() -> None:
    policy_before = deepcopy(DEFAULT_RECOMMENDATION_POLICY.model_dump())

    with pytest.raises(ValueError, match="monotonic"):
        build_sample_evaluation(
            candidate_weights={"level_1": 40, "level_2": 80, "level_3": 120}
        )

    assert DEFAULT_RECOMMENDATION_POLICY.model_dump() == policy_before
    assert DEFAULT_CANDIDATE_WEIGHTS == {"level_1": 120, "level_2": 80, "level_3": 40}
