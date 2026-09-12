from __future__ import annotations

import csv
import hashlib
import io
import json
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .domain.models import Incident
from .optimization.deterministic_engine import DeterministicOptimizationEngine
from .optimization.policy import DEFAULT_RECOMMENDATION_POLICY
from .scenario_generator import (
    ASSIGNMENT_HEADERS,
    CREW_HEADERS,
    HISTORICAL_REPAIR_HEADERS,
    TOPOLOGY_HEADERS,
    WEATHER_HEADERS,
    GeneratedScenario,
    generate_scenario,
    validate_generated_scenario,
)


POC019_DATASET_ID = "poc-019-cf-sample-v2"
POC019_COMPLETE_DATASET_ID = "poc-019-cf-full-v2"
POC019_SAMPLE_DATASET_VERSION = "sample-v2"
POC019_COMPLETE_DATASET_VERSION = "full-v2"
POC019_SEED = 20260912
POC019_COMPLETE_INCIDENT_COUNT = 2000
POC019_COMPLETE_CREW_COUNT = 500
POC019_GENERATED_AT = "2026-09-12T12:00:00-04:00"
DEFAULT_CANDIDATE_WEIGHTS = {"level_1": 120, "level_2": 80, "level_3": 40}
DEFAULT_SCORE_BANDS = (
    {"band_id": "evaluation_band_1", "minimum": 0, "maximum": 99},
    {"band_id": "evaluation_band_2", "minimum": 100, "maximum": 199},
    {"band_id": "evaluation_band_3", "minimum": 200, "maximum": 299},
    {"band_id": "evaluation_band_4", "minimum": 300, "maximum": None},
)

INCIDENT_HEADERS = [
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
]
FACILITY_HEADERS = [
    "facility_id",
    "facility_name",
    "facility_type",
    "region",
    "municipality",
    "feeder",
    "priority_level",
]
CASE_HEADERS = [
    "case_id",
    "category",
    "left_incident_id",
    "right_incident_id",
    "variable_under_test",
    "expected_baseline_relation",
    "expected_candidate_relation",
    "review_status",
    "sme_question",
]

LEVEL_BY_PRIORITY = {"critical": 1, "high": 2, "medium": 3}
SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


@dataclass(frozen=True)
class FacilityResolution:
    level: int | None
    matched_facility_ids: tuple[str, ...]
    warning: str | None = None


@dataclass
class EvaluationPackage:
    dataset_id: str
    dataset_version: str
    seed: int
    incidents: list[dict[str, Any]]
    facilities: list[dict[str, Any]]
    cases: list[dict[str, str]]
    scoring_profiles: dict[str, Any]
    score_bands: list[dict[str, Any]]
    override_examples: list[dict[str, Any]]
    expected_results: dict[str, Any]
    review_status: str
    generation_scope: str
    complete_scenario_generated: bool
    application_scenario: GeneratedScenario | None = None

    def summary(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "seed": self.seed,
            "incidents": len(self.incidents),
            "facilities": len(self.facilities),
            "controlled_pairs": len(self.cases),
            "score_bands": len(self.score_bands),
            "override_examples": len(self.override_examples),
            "review_status": self.review_status,
            "complete_scenario_generated": self.complete_scenario_generated,
        }


def _incident(
    incident_id: str,
    feeder: str,
    *,
    customers_out: int = 1,
    critical_facility: bool = False,
    severity: str = "low",
    hazard: str = "none",
    age_minutes: int = 0,
) -> dict[str, Any]:
    return {
        "incident_id": incident_id,
        "region": "Central-Nassau",
        "municipality": "Hicksville",
        "feeder": feeder,
        "severity": severity,
        "status": "pending",
        "customers_out": customers_out,
        "critical_facility": critical_facility,
        "hazard": hazard,
        "required_skill": "general",
        "age_minutes": age_minutes,
        "latitude": 40.7684,
        "longitude": -73.5251,
        "etr": "2026-09-12T14:00:00-04:00",
    }


def _facility(
    facility_id: str,
    feeder: str,
    priority_level: str,
    *,
    facility_type: str = "healthcare",
    facility_name: str | None = None,
) -> dict[str, str]:
    return {
        "facility_id": facility_id,
        "facility_name": facility_name or f"Synthetic {facility_id}",
        "facility_type": facility_type,
        "region": "Central-Nassau",
        "municipality": "Hicksville",
        "feeder": feeder,
        "priority_level": priority_level,
    }


def resolve_facility_level(
    incident: dict[str, Any], facilities: Iterable[dict[str, Any]]
) -> FacilityResolution:
    critical_facility = incident["critical_facility"]
    if isinstance(critical_facility, bool):
        has_critical_facility = critical_facility
    else:
        normalized = str(critical_facility).strip().lower()
        if normalized not in {"true", "false"}:
            raise ValueError("critical_facility must be a boolean or true/false text")
        has_critical_facility = normalized == "true"
    if not has_critical_facility:
        return FacilityResolution(level=None, matched_facility_ids=())

    matches = [
        facility
        for facility in facilities
        if facility["region"] == incident["region"] and facility["feeder"] == incident["feeder"]
    ]
    matched_ids = tuple(sorted(str(facility["facility_id"]) for facility in matches))
    if not matches:
        return FacilityResolution(
            level=None,
            matched_facility_ids=(),
            warning="critical_facility_missing_link",
        )

    levels = [
        LEVEL_BY_PRIORITY[str(facility["priority_level"]).strip().lower()]
        for facility in matches
        if str(facility["priority_level"]).strip().lower() in LEVEL_BY_PRIORITY
    ]
    unknown_ids = sorted(
        str(facility["facility_id"])
        for facility in matches
        if str(facility["priority_level"]).strip().lower() not in LEVEL_BY_PRIORITY
    )
    if unknown_ids:
        return FacilityResolution(
            level=None,
            matched_facility_ids=matched_ids,
            warning="unknown_critical_facility_level:" + ",".join(unknown_ids),
        )
    return FacilityResolution(level=min(levels), matched_facility_ids=matched_ids)


def candidate_score(
    incident: dict[str, Any],
    facilities: Iterable[dict[str, Any]],
    weights: dict[str, int],
) -> dict[str, Any]:
    resolution = resolve_facility_level(incident, facilities)
    if resolution.warning:
        return {
            "total_score": None,
            "facility_level": resolution.level,
            "matched_facility_ids": list(resolution.matched_facility_ids),
            "warning": resolution.warning,
            "contributions": None,
        }

    scoring = DEFAULT_RECOMMENDATION_POLICY.incident_scoring
    severity = str(incident["severity"]).lower()
    facility_contribution = (
        weights[f"level_{resolution.level}"] if resolution.level is not None else 0
    )
    contributions = {
        "customers_out": int(incident["customers_out"]) // scoring.customers_out_divisor,
        "critical_facility": facility_contribution,
        "hazard": scoring.hazard_bonus if str(incident["hazard"]).lower() != "none" else 0,
        "incident_age": int(incident["age_minutes"]) // scoring.age_minutes_divisor,
        "severity": scoring.severity_weights.for_severity(severity),
    }
    return {
        "total_score": sum(contributions.values()),
        "facility_level": resolution.level,
        "matched_facility_ids": list(resolution.matched_facility_ids),
        "warning": None,
        "contributions": contributions,
    }


def _relation(left: int | None, right: int | None) -> str:
    if left is None or right is None:
        return "review"
    if left > right:
        return ">"
    if left < right:
        return "<"
    return "="


def _rank_candidate_incidents(
    incidents: Iterable[dict[str, Any]],
    evaluations: dict[str, dict[str, Any]],
    bands: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    band_list = list(bands)
    band_rank = {str(band["band_id"]): index for index, band in enumerate(band_list)}
    ranked = [
        incident
        for incident in incidents
        if evaluations[incident["incident_id"]]["total_score"] is not None
    ]
    ranked.sort(key=lambda incident: str(incident["incident_id"]))
    ranked.sort(key=lambda incident: int(incident["customers_out"]), reverse=True)
    ranked.sort(key=lambda incident: int(incident["age_minutes"]), reverse=True)
    ranked.sort(
        key=lambda incident: (
            4 - evaluations[incident["incident_id"]]["facility_level"]
            if evaluations[incident["incident_id"]]["facility_level"] is not None
            else 0
        ),
        reverse=True,
    )
    ranked.sort(
        key=lambda incident: SEVERITY_ORDER[str(incident["severity"]).lower()],
        reverse=True,
    )
    ranked.sort(
        key=lambda incident: int(evaluations[incident["incident_id"]]["total_score"]),
        reverse=True,
    )
    ranked.sort(
        key=lambda incident: str(incident["hazard"]).strip().lower() != "none",
        reverse=True,
    )
    ranked.sort(
        key=lambda incident: band_rank[
            _band_for_score(
                int(evaluations[incident["incident_id"]]["total_score"]),
                band_list,
            )
        ],
        reverse=True,
    )
    return ranked


def _candidate_order_relation(
    left_id: str,
    right_id: str,
    incidents_by_id: dict[str, dict[str, Any]],
    evaluations: dict[str, dict[str, Any]],
    bands: Iterable[dict[str, Any]],
) -> str:
    if evaluations[left_id]["total_score"] is None or evaluations[right_id]["total_score"] is None:
        return "review"
    order = [
        incident["incident_id"]
        for incident in _rank_candidate_incidents(
            [incidents_by_id[left_id], incidents_by_id[right_id]],
            evaluations,
            bands,
        )
    ]
    return ">" if order == [left_id, right_id] else "<"


def _case(
    case_id: str,
    category: str,
    left: str,
    right: str,
    variable: str,
    baseline_relation: str,
    candidate_relation: str,
    question: str,
) -> dict[str, str]:
    return {
        "case_id": case_id,
        "category": category,
        "left_incident_id": left,
        "right_incident_id": right,
        "variable_under_test": variable,
        "expected_baseline_relation": baseline_relation,
        "expected_candidate_relation": candidate_relation,
        "review_status": "approved_sme",
        "sme_question": question,
    }


def _band_for_score(score: int, bands: Iterable[dict[str, Any]]) -> str:
    for band in bands:
        maximum = band["maximum"]
        if score >= band["minimum"] and (maximum is None or score <= maximum):
            return str(band["band_id"])
    raise ValueError(f"Score {score} is not covered by the evaluation bands")


def _validate_inputs(weights: dict[str, int], score_bands: list[dict[str, Any]]) -> None:
    if set(weights) != {"level_1", "level_2", "level_3"}:
        raise ValueError("Candidate weights must define level_1, level_2, and level_3")
    if any(not isinstance(weight, int) or weight < 0 for weight in weights.values()):
        raise ValueError("Candidate weights must be non-negative integers")
    if not (weights["level_1"] >= weights["level_2"] >= weights["level_3"]):
        raise ValueError("Candidate weights must be monotonic from Level 1 through Level 3")

    expected_minimum = 0
    for index, band in enumerate(score_bands):
        if band["minimum"] != expected_minimum:
            raise ValueError("Evaluation score bands must be contiguous and start at zero")
        maximum = band["maximum"]
        if maximum is None:
            if index != len(score_bands) - 1:
                raise ValueError("Only the final evaluation score band may be open-ended")
            continue
        if maximum < band["minimum"]:
            raise ValueError("Evaluation score band maximum must not be below its minimum")
        expected_minimum = maximum + 1


def build_sample_evaluation(
    *,
    dataset_id: str = POC019_DATASET_ID,
    seed: int = POC019_SEED,
    candidate_weights: dict[str, int] | None = None,
    score_bands: Iterable[dict[str, Any]] = DEFAULT_SCORE_BANDS,
) -> EvaluationPackage:
    weights = dict(candidate_weights or DEFAULT_CANDIDATE_WEIGHTS)
    bands = [dict(band) for band in score_bands]
    _validate_inputs(weights, bands)

    facilities = [
        _facility("FAC-L1", "FDR-CN-L1", "critical", facility_type="hospital"),
        _facility("FAC-L2", "FDR-CN-L2", "high", facility_type="nursing_home"),
        _facility(
            "FAC-L3-LSE",
            "FDR-CN-L3",
            "medium",
            facility_type="healthcare",
            facility_name="Synthetic Private Health Device LSE Group",
        ),
        _facility("FAC-UNKNOWN", "FDR-CN-UNKNOWN", "unknown"),
        _facility("FAC-MULTI-L1", "FDR-CN-MULTI-L1", "critical", facility_type="hospital"),
        _facility("FAC-MULTI-L3A", "FDR-CN-MULTI-L1", "medium"),
        _facility("FAC-MULTI-L2", "FDR-CN-MULTI-L2", "high", facility_type="nursing_home"),
        _facility("FAC-MULTI-L3B", "FDR-CN-MULTI-L2", "medium"),
        _facility("FAC-CF-AGE", "FDR-CN-CF-AGE", "high", facility_type="nursing_home"),
    ]
    incidents = [
        _incident("P019-L1", "FDR-CN-L1", critical_facility=True),
        _incident("P019-L1-NONE", "FDR-CN-L1-NONE"),
        _incident("P019-L2", "FDR-CN-L2", critical_facility=True),
        _incident("P019-L2-NONE", "FDR-CN-L2-NONE"),
        _incident("P019-L3", "FDR-CN-L3", critical_facility=True),
        _incident("P019-L3-NONE", "FDR-CN-L3-NONE"),
        _incident("P019-UNKNOWN", "FDR-CN-UNKNOWN", critical_facility=True),
        _incident("P019-UNKNOWN-NONE", "FDR-CN-UNKNOWN-NONE"),
        _incident("P019-LSE-L3-C001", "FDR-CN-L3", critical_facility=True),
        _incident("P019-LSE-L3-C019", "FDR-CN-L3", customers_out=19, critical_facility=True),
        _incident("P019-LSE-L3-C020", "FDR-CN-L3", customers_out=20, critical_facility=True),
        _incident("P019-LSE-L3-C100", "FDR-CN-L3", customers_out=100, critical_facility=True),
        _incident("P019-NOCF-C019", "FDR-CN-NOCF-C019", customers_out=19),
        _incident("P019-NOCF-C020", "FDR-CN-NOCF-C020", customers_out=20),
        _incident("P019-MULTI-L1-L3", "FDR-CN-MULTI-L1", critical_facility=True),
        _incident("P019-MULTI-L2-L3", "FDR-CN-MULTI-L2", critical_facility=True),
        _incident("P019-HAZ-MED", "FDR-CN-HAZ-MED", severity="medium", hazard="downed wire"),
        _incident("P019-NOHAZ-HIGH", "FDR-CN-NOHAZ-HIGH", severity="high"),
        _incident("P019-HAZ-LOW", "FDR-CN-HAZ-LOW", severity="low", hazard="downed wire"),
        _incident("P019-SEV-MED-C600", "FDR-CN-SEV-MED-C600", customers_out=600, severity="medium"),
        _incident("P019-SEV-MED-C800", "FDR-CN-SEV-MED-C800", customers_out=800, severity="medium"),
        _incident("P019-CF-BEFORE-AGE", "FDR-CN-CF-AGE", critical_facility=True),
        _incident("P019-OLDER-NOCF", "FDR-CN-OLDER", age_minutes=800),
    ]

    for threshold in [band["minimum"] for band in bands if band["minimum"] > 0]:
        for delta, suffix in ((-1, "BELOW"), (0, "AT"), (1, "ABOVE")):
            target_score = threshold + delta
            incidents.append(
                _incident(
                    f"P019-BAND-{threshold}-{suffix}",
                    f"FDR-CN-BAND-{threshold}-{suffix}",
                    customers_out=(target_score - 10) * 20,
                )
            )

    cases = [
        _case("CF-L1-NONE", "facility_level", "P019-L1", "P019-L1-NONE", "level_1", ">", ">", "Should Level 1 receive the proposed differentiated bonus?"),
        _case("CF-L2-NONE", "facility_level", "P019-L2", "P019-L2-NONE", "level_2", ">", ">", "Should Level 2 retain the current flat-bonus magnitude?"),
        _case("CF-L3-NONE", "facility_level", "P019-L3", "P019-L3-NONE", "level_3", ">", ">", "Should Level 3 receive a smaller but positive bonus?"),
        _case("CF-UNKNOWN-NONE", "unknown_facility", "P019-UNKNOWN", "P019-UNKNOWN-NONE", "unknown_priority_level", ">", "review", "Should an unknown facility level be withheld from candidate ranking?"),
        _case("CF-L1-L2", "facility_level", "P019-L1", "P019-L2", "level_1_vs_level_2", "=", ">", "Is the proposed Level 1 over Level 2 ordering operationally appropriate?"),
        _case("CF-L2-L3", "facility_level", "P019-L2", "P019-L3", "level_2_vs_level_3", "=", ">", "Is the proposed Level 2 over Level 3 ordering operationally appropriate?"),
        _case("LSE-1-100", "lse_customer_count", "P019-LSE-L3-C100", "P019-LSE-L3-C001", "customers_out", ">", ">", "Should customer count remain independently additive for an LSE-linked incident?"),
        _case("NOCF-19-20", "customer_edge", "P019-NOCF-C020", "P019-NOCF-C019", "customers_out_20_boundary", ">", ">", "Is the one-point change at 20 customers acceptable without a CF?"),
        _case("LSE-L3-19-20", "lse_customer_edge", "P019-LSE-L3-C020", "P019-LSE-L3-C019", "customers_out_20_boundary_with_lse", ">", ">", "Is the same customer boundary appropriate when Level 3 LSE impact is present?"),
        _case("LSE-L3-C019-NOCF", "lse_customer_edge", "P019-LSE-L3-C019", "P019-NOCF-C019", "level_3_at_19_customers", ">", ">", "Is the Level 3 contribution appropriate at 19 customers?"),
        _case("LSE-L3-C020-NOCF", "lse_customer_edge", "P019-LSE-L3-C020", "P019-NOCF-C020", "level_3_at_20_customers", ">", ">", "Is the Level 3 contribution appropriate at 20 customers?"),
        _case("MULTI-L1-L2", "multiple_facilities", "P019-MULTI-L1-L3", "P019-MULTI-L2-L3", "highest_level_once", "=", ">", "Should only the highest facility level apply once on a feeder?"),
        _case("HAZ-MED-HIGH", "hazard_severity", "P019-HAZ-MED", "P019-NOHAZ-HIGH", "hazard_vs_severity", ">", ">", "Should medium severity with a hazard outrank high severity without one?"),
        _case("HAZ-LOW-HIGH", "hazard_precedence", "P019-HAZ-LOW", "P019-NOHAZ-HIGH", "same_band_hazard_precedence", "<", ">", "Within the same score band, should a hazardous incident rank ahead of a non-hazardous incident regardless of severity or numeric score?"),
        _case("SAME-HAZARD-GUARD", "hazard_guard", "P019-NOHAZ-HIGH", "P019-SEV-MED-C600", "same_hazard_score_precedence", ">", ">", "When both incidents are non-hazardous and in the same score band, should the higher score retain priority?"),
        _case("SEVERITY-TIE", "severity_precedence", "P019-NOHAZ-HIGH", "P019-SEV-MED-C800", "severity_tie_break_with_equal_hazard_status", "=", ">", "When scores and hazard status tie, should severity remain the next tie-break?"),
        _case("CF-BEFORE-AGE", "cf_before_age", "P019-CF-BEFORE-AGE", "P019-OLDER-NOCF", "level_2_vs_800_age_minutes", "=", ">", "When totals and severity tie, should known CF level precede incident age?"),
    ]

    baseline_engine = DeterministicOptimizationEngine()
    incident_models = [Incident.model_validate(incident) for incident in incidents]
    baseline_evaluations = {
        result.incident.incident_id: result.score
        for result in baseline_engine.evaluate_incidents(incident_models)
    }
    candidate_evaluations = {
        incident["incident_id"]: candidate_score(incident, facilities, weights)
        for incident in incidents
    }
    incidents_by_id = {incident["incident_id"]: incident for incident in incidents}

    actual_case_results = []
    for case in cases:
        left_id = case["left_incident_id"]
        right_id = case["right_incident_id"]
        baseline_relation = _relation(
            baseline_evaluations[left_id].total_score,
            baseline_evaluations[right_id].total_score,
        )
        candidate_score_relation = _relation(
            candidate_evaluations[left_id]["total_score"],
            candidate_evaluations[right_id]["total_score"],
        )
        candidate_relation = _candidate_order_relation(
            left_id,
            right_id,
            incidents_by_id,
            candidate_evaluations,
            bands,
        )
        actual_case_results.append(
            {
                "case_id": case["case_id"],
                "baseline_relation": baseline_relation,
                "candidate_score_relation": candidate_score_relation,
                "candidate_relation": candidate_relation,
                "baseline_expectation_met": baseline_relation == case["expected_baseline_relation"],
                "candidate_expectation_met": (
                    candidate_relation == case["expected_candidate_relation"]
                    if case["expected_candidate_relation"] != "review"
                    else None
                ),
            }
        )

    band_boundaries = []
    for threshold in [band["minimum"] for band in bands if band["minimum"] > 0]:
        for delta, suffix in ((-1, "BELOW"), (0, "AT"), (1, "ABOVE")):
            incident_id = f"P019-BAND-{threshold}-{suffix}"
            score = baseline_evaluations[incident_id].total_score
            band_boundaries.append(
                {
                    "incident_id": incident_id,
                    "threshold": threshold,
                    "position": suffix.lower(),
                    "score": score,
                    "band_id": _band_for_score(score, bands),
                }
            )

    expected_results = {
        "baseline": {
            "algorithm_version": DEFAULT_RECOMMENDATION_POLICY.algorithm_version,
            "policy_version": DEFAULT_RECOMMENDATION_POLICY.policy_version,
            "incidents": {
                incident_id: score.model_dump(mode="json")
                for incident_id, score in sorted(baseline_evaluations.items())
            },
        },
        "candidate": {
            "profile_id": "illustrative-level-differentiation-v1",
            "review_status": "approved_sme",
            "incidents": dict(sorted(candidate_evaluations.items())),
        },
        "case_results": actual_case_results,
        "band_boundaries": band_boundaries,
        "known_policy_question": {
            "case_id": "CF-BEFORE-AGE",
            "current_behavior": "age_precedes_critical_facility_level_when_total_and_severity_tie",
            "candidate_hypothesis": "critical_facility_level_precedes_age",
            "current_rank_order": [
                result.incident.incident_id
                for result in baseline_engine.evaluate_incidents(
                    [
                        Incident.model_validate(
                            next(
                                incident
                                for incident in incidents
                                if incident["incident_id"] == "P019-CF-BEFORE-AGE"
                            )
                        ),
                        Incident.model_validate(
                            next(
                                incident
                                for incident in incidents
                                if incident["incident_id"] == "P019-OLDER-NOCF"
                            )
                        ),
                    ]
                )
            ],
            "candidate_hypothesis_order": [
                incident["incident_id"]
                for incident in _rank_candidate_incidents(
                    [
                        incident
                        for incident in incidents
                        if incident["incident_id"]
                        in {"P019-CF-BEFORE-AGE", "P019-OLDER-NOCF"}
                    ],
                    candidate_evaluations,
                    bands,
                )
            ],
            "review_status": "approved_sme",
        },
    }
    scoring_profiles = {
        "baseline": {
            "algorithm_version": DEFAULT_RECOMMENDATION_POLICY.algorithm_version,
            "policy_version": DEFAULT_RECOMMENDATION_POLICY.policy_version,
            "critical_facility_weights": {"level_1": 80, "level_2": 80, "level_3": 80},
            "status": "implemented_poc_policy",
        },
        "candidate": {
            "profile_id": "illustrative-level-differentiation-v1",
            "critical_facility_weights": weights,
            "unknown_level_behavior": "withhold_from_candidate_ranking_and_warn",
            "multiple_facility_behavior": "apply_highest_level_once",
            "status": "sme_approved_for_complete_evaluation",
        },
    }
    override_examples = [
        {
            "example_id": "OVERRIDE-BACKUP-GENERATION",
            "action": "overridden",
            "reason": "Critical facility confirmed on backup generation; reassess immediate priority.",
            "expected_assignment_created": False,
            "expected_original_recommendation_preserved": True,
            "review_status": "approved_sme",
        },
        {
            "example_id": "OVERRIDE-FIELD-SAFETY",
            "action": "overridden",
            "reason": "Field report identifies an energized-wire safety condition not yet present in source data.",
            "expected_assignment_created": False,
            "expected_original_recommendation_preserved": True,
            "review_status": "approved_sme",
        },
        {
            "example_id": "MODIFIED-RANKED-ALTERNATIVE",
            "action": "modified",
            "reason": "Use a ranked alternative crew based on current switching coordination.",
            "expected_assignment_created": True,
            "expected_original_recommendation_preserved": True,
            "review_status": "approved_sme",
        },
        {
            "example_id": "OVERRIDE-MISSING-REASON",
            "action": "overridden",
            "reason": "",
            "expected_error": "decision_reason_required",
            "review_status": "contract_regression",
        },
        {
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
        },
    ]

    return EvaluationPackage(
        dataset_id=dataset_id,
        dataset_version=POC019_SAMPLE_DATASET_VERSION,
        seed=seed,
        incidents=incidents,
        facilities=facilities,
        cases=cases,
        scoring_profiles=scoring_profiles,
        score_bands=bands,
        override_examples=override_examples,
        expected_results=expected_results,
        review_status="approved_sme",
        generation_scope="approved_sample",
        complete_scenario_generated=False,
    )


def _build_scenario_topology(
    incidents: Iterable[dict[str, Any]], facilities: Iterable[dict[str, Any]]
) -> list[dict[str, str]]:
    feeder_keys = sorted(
        {
            (str(row["region"]), str(row["feeder"]))
            for row in [*incidents, *facilities]
        }
    )
    return [
        {
            "asset_id": f"POC019-FEEDER-{index:04d}",
            "asset_type": "feeder",
            "feeder": feeder,
            "parent_asset_id": "",
            "region": region,
            "normal_status": "energized",
        }
        for index, (region, feeder) in enumerate(feeder_keys, start=1)
    ]


def build_complete_evaluation(
    *,
    dataset_id: str = POC019_COMPLETE_DATASET_ID,
    seed: int = POC019_SEED,
    incident_count: int = POC019_COMPLETE_INCIDENT_COUNT,
    crew_count: int = POC019_COMPLETE_CREW_COUNT,
    candidate_weights: dict[str, int] | None = None,
    score_bands: Iterable[dict[str, Any]] = DEFAULT_SCORE_BANDS,
) -> EvaluationPackage:
    """Build the SME-approved evaluation as an isolated application scenario."""

    weights = dict(candidate_weights or DEFAULT_CANDIDATE_WEIGHTS)
    bands = [dict(band) for band in score_bands]
    _validate_inputs(weights, bands)
    controlled = build_sample_evaluation(
        dataset_id=POC019_DATASET_ID,
        seed=seed,
        candidate_weights=weights,
        score_bands=bands,
    )
    if incident_count < len(controlled.incidents):
        raise ValueError(
            "Complete incident count must include every approved controlled incident"
        )

    generated = generate_scenario(
        scenario_id=dataset_id,
        start_date=date(2026, 9, 12),
        incident_count=incident_count,
        crew_count=crew_count,
        assignment_rate=0,
        dual_tree_incidents=0,
        seed=seed,
        critical_facilities_per_region=max(1, round(incident_count * 0.01 / 4)),
    )
    incidents = [
        *controlled.incidents,
        *generated.incidents[len(controlled.incidents) :],
    ]
    facilities = [*controlled.facilities, *generated.critical_facilities]
    topology = _build_scenario_topology(incidents, facilities)
    application_scenario = GeneratedScenario(
        scenario_id=dataset_id,
        incidents=incidents,
        crews=generated.crews,
        assignments=[],
        historical_repairs=generated.historical_repairs,
        weather=generated.weather,
        critical_facilities=facilities,
        topology=topology,
        crew_types=generated.crew_types,
    )
    validate_generated_scenario(
        application_scenario,
        expected_assigned_incidents=0,
        expected_dual_tree_incidents=0,
    )

    baseline_engine = DeterministicOptimizationEngine()
    baseline_evaluations = {
        result.incident.incident_id: result.score
        for result in baseline_engine.evaluate_incidents(
            [Incident.model_validate(incident) for incident in incidents]
        )
    }
    candidate_evaluations = {
        incident["incident_id"]: candidate_score(incident, facilities, weights)
        for incident in incidents
    }
    incidents_by_id = {incident["incident_id"]: incident for incident in incidents}
    case_results = []
    for case in controlled.cases:
        left_id = case["left_incident_id"]
        right_id = case["right_incident_id"]
        baseline_relation = _relation(
            baseline_evaluations[left_id].total_score,
            baseline_evaluations[right_id].total_score,
        )
        candidate_score_relation = _relation(
            candidate_evaluations[left_id]["total_score"],
            candidate_evaluations[right_id]["total_score"],
        )
        candidate_relation = _candidate_order_relation(
            left_id,
            right_id,
            incidents_by_id,
            candidate_evaluations,
            bands,
        )
        case_results.append(
            {
                "case_id": case["case_id"],
                "baseline_relation": baseline_relation,
                "candidate_score_relation": candidate_score_relation,
                "candidate_relation": candidate_relation,
                "baseline_expectation_met": (
                    baseline_relation == case["expected_baseline_relation"]
                ),
                "candidate_expectation_met": (
                    candidate_relation == case["expected_candidate_relation"]
                    if case["expected_candidate_relation"] != "review"
                    else None
                ),
            }
        )

    ranked = _rank_candidate_incidents(incidents, candidate_evaluations, bands)
    expected_results = {
        "baseline": {
            "algorithm_version": DEFAULT_RECOMMENDATION_POLICY.algorithm_version,
            "policy_version": DEFAULT_RECOMMENDATION_POLICY.policy_version,
            "incidents": {
                incident_id: score.model_dump(mode="json")
                for incident_id, score in sorted(baseline_evaluations.items())
            },
        },
        "candidate": {
            "profile_id": "illustrative-level-differentiation-v1",
            "review_status": "approved_sme_for_evaluation",
            "ranking_policy": [
                "score_band",
                "hazard_presence_within_band",
                "numeric_score",
                "severity_when_hazard_status_matches",
                "critical_facility_level_before_age_on_equal_score_and_severity",
                "incident_age",
                "customers_out",
                "stable_incident_id",
            ],
            "ranked_incident_ids": [incident["incident_id"] for incident in ranked],
            "withheld_incident_ids": sorted(
                incident_id
                for incident_id, result in candidate_evaluations.items()
                if result["total_score"] is None
            ),
            "incidents": dict(sorted(candidate_evaluations.items())),
        },
        "case_results": case_results,
        "band_boundaries": controlled.expected_results["band_boundaries"],
        "approved_policy_evidence": controlled.expected_results["known_policy_question"],
    }

    return EvaluationPackage(
        dataset_id=dataset_id,
        dataset_version=POC019_COMPLETE_DATASET_VERSION,
        seed=seed,
        incidents=incidents,
        facilities=facilities,
        cases=controlled.cases,
        scoring_profiles=controlled.scoring_profiles,
        score_bands=bands,
        override_examples=controlled.override_examples,
        expected_results=expected_results,
        review_status="approved_sme_for_evaluation",
        generation_scope="complete_application_scenario",
        complete_scenario_generated=True,
        application_scenario=application_scenario,
    )


def _csv_text(headers: list[str], rows: Iterable[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_evaluation_files(package: EvaluationPackage) -> dict[str, str]:
    files = {
        "PendingIncidents.csv": _csv_text(INCIDENT_HEADERS, package.incidents),
        "CriticalFacilities.csv": _csv_text(FACILITY_HEADERS, package.facilities),
        "EvaluationCases.csv": _csv_text(CASE_HEADERS, package.cases),
        "ScoringProfiles.json": _json_text(package.scoring_profiles),
        "ScoreBands.json": _json_text(
            {
                "evaluation_only": True,
                "review_status": package.review_status,
                "bands": package.score_bands,
            }
        ),
        "OverrideExamples.json": _json_text(package.override_examples),
        "ExpectedResults.json": _json_text(package.expected_results),
    }
    if package.application_scenario is not None:
        scenario = package.application_scenario
        files.update(
            {
                "Crews.csv": _csv_text(CREW_HEADERS, scenario.crews),
                "Assignments.csv": _csv_text(ASSIGNMENT_HEADERS, scenario.assignments),
                "HistoricalRepairs.csv": _csv_text(
                    HISTORICAL_REPAIR_HEADERS, scenario.historical_repairs
                ),
                "Weather.csv": _csv_text(WEATHER_HEADERS, scenario.weather),
                "Topology.csv": _csv_text(TOPOLOGY_HEADERS, scenario.topology),
                "scenario.json": _json_text(
                    {
                        "schema_version": "1.0",
                        "scenario_id": scenario.scenario_id,
                        "name": "POC-019 Critical Facility Full Evaluation",
                        "description": (
                            "Isolated SME-approved evaluation scenario for critical-facility "
                            "scoring; the candidate policy is not operational."
                        ),
                        "event_type": "critical_facility",
                        "freshness": {
                            "updated_at": POC019_GENERATED_AT,
                            "source": "scenario_generation",
                            "provenance": "POC-019 deterministic evaluation generator",
                        },
                        "expected_conditions": [
                            "SME-approved controlled critical-facility comparisons",
                            "Representative deterministic Long Island incidents and crews",
                            "Candidate scoring remains evaluation-only",
                            "Unknown critical-facility levels remain data-quality exceptions",
                        ],
                        "files": {
                            "incidents": "PendingIncidents.csv",
                            "crews": "Crews.csv",
                            "assignments": "Assignments.csv",
                            "historical_repairs": "HistoricalRepairs.csv",
                            "weather": "Weather.csv",
                            "critical_facilities": "CriticalFacilities.csv",
                            "topology": "Topology.csv",
                        },
                    }
                ),
            }
        )
    hashes = {
        name: hashlib.sha256(content.encode("utf-8")).hexdigest()
        for name, content in sorted(files.items())
    }
    files["evaluation_manifest.json"] = _json_text(
        {
            **package.summary(),
            "artifact_sha256": hashes,
            "candidate_policy_is_operational": False,
            "existing_scenarios_modified": False,
            "generation_scope": package.generation_scope,
            "application_scenario_included": package.application_scenario is not None,
        }
    )
    return files


def write_evaluation(
    package: EvaluationPackage,
    output_root: Path,
) -> Path:
    output_root = output_root.resolve()
    target = output_root / package.dataset_id
    if target.exists():
        raise FileExistsError(f"Evaluation output already exists: {target}")
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{package.dataset_id}-", dir=output_root) as temporary:
        temporary_path = Path(temporary)
        for filename, content in render_evaluation_files(package).items():
            (temporary_path / filename).write_text(content, encoding="utf-8")
        temporary_path.rename(target)
    return target
