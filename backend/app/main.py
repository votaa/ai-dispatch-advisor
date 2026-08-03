from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import data_loader
from .recommendation_actions import record_action, recent_actions
from .recommendations import dashboard_summary, ranked_incidents, recommend_assignment


app = FastAPI(
    title="AI Dispatch Advisor API",
    description="Developer Bootstrap MVP API for synthetic utility outage dispatch data.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OptimizeRequest(BaseModel):
    incident_id: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    incident_id: Optional[str] = None


class RecommendationActionRequest(BaseModel):
    incident_id: str
    action: Literal["accepted", "modified", "deferred", "overridden"]
    recommendation: dict[str, Any]
    note: Optional[str] = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-dispatch-advisor-api"}


@app.get("/api/dashboard")
def dashboard() -> dict:
    return dashboard_summary(data_loader.incidents(), data_loader.crews(), data_loader.assignments())


@app.get("/api/incidents")
def incidents() -> list[dict]:
    return ranked_incidents(data_loader.incidents())


@app.get("/api/incidents/{incident_id}")
def incident_detail(incident_id: str) -> dict:
    for incident in data_loader.incidents():
        if incident.get("incident_id") == incident_id:
            return incident
    raise HTTPException(status_code=404, detail="Incident not found")


@app.get("/api/crews")
def crews() -> list[dict]:
    return data_loader.crews()


@app.get("/api/assignments")
def assignments() -> list[dict]:
    return data_loader.assignments()


@app.get("/api/weather")
def weather() -> list[dict]:
    return data_loader.weather()


@app.get("/api/critical-facilities")
def critical_facilities() -> list[dict]:
    return data_loader.critical_facilities()


@app.get("/api/topology")
def topology() -> list[dict]:
    return data_loader.topology()


@app.post("/api/optimize")
def optimize(request: OptimizeRequest) -> dict:
    incident_rows = ranked_incidents(data_loader.incidents())
    if request.incident_id:
        incident_rows = [row for row in incident_rows if row.get("incident_id") == request.incident_id]
    if not incident_rows:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = incident_rows[0]
    return recommend_assignment(incident, data_loader.crews(), data_loader.assignments())


@app.post("/api/recommendation-actions")
def recommendation_action(request: RecommendationActionRequest) -> dict:
    incident = next(
        (row for row in data_loader.incidents() if row.get("incident_id") == request.incident_id),
        None,
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    note = request.note.strip() if request.note else None
    if request.action == "overridden" and not note:
        raise HTTPException(status_code=400, detail="Override reason is required")

    return record_action(
        incident_id=request.incident_id,
        action=request.action,
        note=note,
        recommendation=request.recommendation,
    )


@app.get("/api/audit/events")
def audit_events(limit: int = 25) -> list[dict]:
    return recent_actions(limit=max(1, min(limit, 100)))


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    message = request.message.lower()
    summary = dashboard()
    incident = None
    if request.incident_id:
        incident = next(
            (row for row in data_loader.incidents() if row.get("incident_id") == request.incident_id),
            None,
        )

    if any(term in message for term in ["critical", "hospital", "facility", "water", "emergency"]):
        answer = (
            f"There are {summary['critical_facility_incidents']} incidents affecting critical facilities. "
            "The highest-priority critical events in this demo are Millbrook Regional Hospital, "
            "Briarcliff Emergency Operations Center, and Riverton Water Treatment."
        )
        intent = "critical_facilities"
    elif any(term in message for term in ["crew", "crews", "available", "resource", "resources"]):
        answer = (
            f"{summary['available_crews']} crews are available and {summary['assigned_crews']} are assigned. "
            "Crew recommendations consider availability, capability, and estimated travel time."
        )
        intent = "crew_status"
    elif any(term in message for term in ["recommend", "why", "assign", "assignment", "dispatch"]):
        recommendation = optimize(OptimizeRequest(incident_id=request.incident_id))
        crew = recommendation.get("recommended_crew") or {}
        answer = (
            f"The current recommendation is to {recommendation['recommended_action'].lower()} "
            f"{crew.get('crew_name', 'an available crew')}. "
            f"Confidence is {recommendation['confidence']} because the explanation factors include "
            f"{', '.join(recommendation['factors'][:3])}."
        )
        intent = "recommendation"
    elif any(term in message for term in ["first", "focus", "priority", "prioritize", "next"]):
        top_incident = summary["top_incidents"][0]
        answer = (
            f"Focus first on {top_incident['incident_id']} in {top_incident['municipality']}. "
            f"It affects {top_incident['customers_out']} customers, is marked {top_incident['severity']}, "
            f"and has the hazard '{top_incident['hazard']}'."
        )
        intent = "priority_focus"
    elif any(term in message for term in ["storm", "weather", "wind", "rain"]):
        answer = (
            "Storm mode should focus on critical facilities, downed-wire hazards, and crew capacity by region. "
            f"This scenario has {summary['high_priority_incidents']} high-priority incidents and "
            f"{summary['customers_out']} customers out."
        )
        intent = "storm_summary"
    elif any(term in message for term in ["selected", "incident", "outage", "status"]) and incident:
        answer = (
            f"Selected incident {incident['incident_id']} is in {incident['municipality']} on feeder "
            f"{incident['feeder']}. It affects {incident['customers_out']} customers, has status "
            f"{incident['status']}, and current ETR is {incident['etr']}."
        )
        intent = "selected_incident"
    else:
        answer = (
            f"The demo scenario has {summary['active_incidents']} active incidents affecting "
            f"{summary['customers_out']} customers. Try asking about crews, critical facilities, "
            "the top priority, storm status, or why a recommendation was made."
        )
        intent = "scenario_summary"

    return {
        "answer": answer,
        "intent": intent,
        "source": "synthetic-demo-data",
        "safety_note": "This copilot response is advisory and does not execute dispatch actions.",
    }
