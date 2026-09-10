from __future__ import annotations

from typing import Any

from .optimization.policy import DEFAULT_RECOMMENDATION_POLICY, RecommendationPolicy


def recommend_assignment(
    incident: dict[str, Any],
    crews: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    policy: RecommendationPolicy = DEFAULT_RECOMMENDATION_POLICY,
    feasible_crew_ids: set[str] | None = None,
) -> dict[str, Any]:
    scoring = policy.crew_scoring
    active_crews = {row.get("crew_id") for row in assignments if row.get("status") == "active"}
    required_skill = str(incident.get("required_skill") or "").lower()

    candidates = []
    for crew in crews:
        if feasible_crew_ids is not None and crew.get("crew_id") not in feasible_crew_ids:
            continue
        if crew.get("crew_id") in active_crews or crew.get("status") != "available":
            continue
        capability = str(crew.get("capability") or "").lower()
        capability_match = required_skill == "general" or capability == required_skill
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
    ranked_incidents: list[dict[str, Any]],
    crews: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    scenario_id: str = "base",
) -> dict[str, Any]:
    active_assigned_crews = {row.get("crew_id") for row in assignments if row.get("status") == "active"}
    return {
        "active_incidents": len(ranked_incidents),
        "customers_out": sum(int(row.get("customers_out") or 0) for row in ranked_incidents),
        "available_crews": sum(
            1 for row in crews if row.get("status") == "available" and row.get("crew_id") not in active_assigned_crews
        ),
        "assigned_crews": len(active_assigned_crews),
        "critical_facility_incidents": sum(
            1 for row in ranked_incidents if row.get("critical_facility")
        ),
        "high_priority_incidents": sum(
            1
            for row in ranked_incidents
            if str(row.get("severity")).lower() in {"critical", "high"}
        ),
        # The dashboard supports a bounded client-side display limit up to 50.
        # Keep the API payload bounded while allowing the UI to choose 5/10/25/50.
        "top_incidents": ranked_incidents[:50],
        "scenario": scenario_id,
        "data_freshness": "Synthetic demo data loaded at backend startup",
    }
