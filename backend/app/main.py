from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import data_loader
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


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    message = request.message.lower()
    summary = dashboard()
    if "critical" in message:
        answer = (
            f"There are {summary['critical_facility_incidents']} incidents affecting critical facilities. "
            "Review the dispatch queue and storm mode panels for priority context."
        )
    elif "crew" in message:
        answer = (
            f"{summary['available_crews']} crews are available and {summary['assigned_crews']} are assigned. "
            "Crew recommendations consider availability, capability, and estimated travel time."
        )
    elif "recommend" in message or "why" in message:
        recommendation = optimize(OptimizeRequest(incident_id=request.incident_id))
        crew = recommendation.get("recommended_crew") or {}
        answer = (
            f"The current recommendation is to {recommendation['recommended_action'].lower()} "
            f"{crew.get('crew_name', 'an available crew')}. "
            f"Confidence is {recommendation['confidence']} because the explanation factors include "
            f"{', '.join(recommendation['factors'][:3])}."
        )
    else:
        answer = (
            f"The demo scenario has {summary['active_incidents']} active incidents affecting "
            f"{summary['customers_out']} customers. The highest priority items are shown in the dispatch queue."
        )

    return {
        "answer": answer,
        "source": "synthetic-demo-data",
        "safety_note": "This copilot response is advisory and does not execute dispatch actions.",
    }
