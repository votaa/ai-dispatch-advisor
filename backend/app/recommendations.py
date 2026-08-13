from __future__ import annotations

from typing import Any

from .optimization.policy import DEFAULT_RECOMMENDATION_POLICY, RecommendationPolicy


def _score_incident(
    incident: dict[str, Any],
    policy: RecommendationPolicy = DEFAULT_RECOMMENDATION_POLICY,
) -> int:
    scoring = policy.incident_scoring
    customers = int(incident.get("customers_out") or 0)
    critical = scoring.critical_facility_bonus if incident.get("critical_facility") else 0
    hazard = scoring.hazard_bonus if str(incident.get("hazard", "")).lower() != "none" else 0
    age = int(incident.get("age_minutes") or 0) // scoring.age_minutes_divisor
    severity = scoring.severity_weights.for_severity(
        str(incident.get("severity", "")).lower()
    )
    return customers // scoring.customers_out_divisor + critical + hazard + age + severity


def ranked_incidents(
    incidents: list[dict[str, Any]],
    policy: RecommendationPolicy = DEFAULT_RECOMMENDATION_POLICY,
) -> list[dict[str, Any]]:
    return sorted(incidents, key=lambda incident: _score_incident(incident, policy), reverse=True)


def recommend_assignment(
    incident: dict[str, Any],
    crews: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    policy: RecommendationPolicy = DEFAULT_RECOMMENDATION_POLICY,
) -> dict[str, Any]:
    scoring = policy.crew_scoring
    active_crews = {row.get("crew_id") for row in assignments if row.get("status") == "active"}
    required_skill = str(incident.get("required_skill") or "").lower()

    candidates = []
    for crew in crews:
        if crew.get("crew_id") in active_crews or crew.get("status") != "available":
            continue
        capability = str(crew.get("capability") or "").lower()
        capability_match = required_skill in capability or required_skill == "general"
        travel_minutes = int(
            crew.get("travel_minutes_to_selected_incident") or scoring.missing_travel_minutes
        )
        score = scoring.base_score - travel_minutes * scoring.travel_minute_penalty
        if capability_match:
            score += scoring.capability_match_bonus
        if crew.get("storm_ready"):
            score += scoring.storm_ready_bonus
        candidates.append(
            {
                **crew,
                "suitability_score": max(score, scoring.minimum_score),
                "capability_match": capability_match,
                "estimated_travel_minutes": travel_minutes,
            }
        )

    candidates = sorted(candidates, key=lambda row: row["suitability_score"], reverse=True)
    selected = candidates[0] if candidates else None

    if not selected:
        return {
            "recommendation_id": f"REC-{incident.get('incident_id')}-REVIEW",
            "incident_id": incident.get("incident_id"),
            "recommended_action": "Defer and escalate",
            "recommended_crew": None,
            "confidence": "low",
            "expected_impact": "No available crew meets the current assignment constraints.",
            "factors": ["No available crew found", "Supervisor review recommended"],
            "constraints": ["Crew availability"],
            "alternatives": [],
        }

    confidence = (
        "high"
        if selected["suitability_score"] >= scoring.high_confidence_threshold
        else "medium"
    )
    return {
        "recommendation_id": f"REC-{incident.get('incident_id')}-{selected.get('crew_id')}",
        "incident_id": incident.get("incident_id"),
        "recommended_action": "Assign crew",
        "recommended_crew": selected,
        "confidence": confidence,
        "expected_impact": (
            f"Prioritizes {incident.get('customers_out')} affected customers "
            f"with {selected['estimated_travel_minutes']} minute estimated travel."
        ),
        "factors": [
            "Crew is available",
            "Crew capability matches required work",
            "Travel time is competitive",
            "Incident priority includes customer and safety impact",
        ],
        "constraints": [
            "Human dispatcher approval required",
            "Recommendation depends on current sample data freshness",
        ],
        "alternatives": candidates[1:4],
    }


def dashboard_summary(
    incidents: list[dict[str, Any]],
    crews: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    scenario_id: str = "base",
    policy: RecommendationPolicy = DEFAULT_RECOMMENDATION_POLICY,
) -> dict[str, Any]:
    ranked = ranked_incidents(incidents, policy=policy)
    active_assigned_crews = {row.get("crew_id") for row in assignments if row.get("status") == "active"}
    return {
        "active_incidents": len(incidents),
        "customers_out": sum(int(row.get("customers_out") or 0) for row in incidents),
        "available_crews": sum(
            1 for row in crews if row.get("status") == "available" and row.get("crew_id") not in active_assigned_crews
        ),
        "assigned_crews": len(active_assigned_crews),
        "critical_facility_incidents": sum(1 for row in incidents if row.get("critical_facility")),
        "high_priority_incidents": sum(
            1 for row in incidents if str(row.get("severity")).lower() in {"critical", "high"}
        ),
        "top_incidents": ranked[:5],
        "scenario": scenario_id,
        "data_freshness": "Synthetic demo data loaded at backend startup",
    }
