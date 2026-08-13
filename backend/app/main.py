from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import data_loader
from .api_models import (
    ChatRequest,
    ChatResponse,
    DashboardResponse,
    HealthResponse,
    OptimizeRequest,
    RecommendationActionRequest,
    ScenarioActivationRequest,
)
from .decision_store import (
    accepted_assignments,
    latest_decisions_by_incident,
    recent_decisions,
    record_decision,
)
from .domain.models import Assignment, Crew, Incident, Recommendation, RecommendationDecision
from .recommendations import dashboard_summary, ranked_incidents, recommend_assignment
from .scenario_service import ScenarioDescriptor, ScenarioService, ScenarioServiceError


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


@app.exception_handler(ScenarioServiceError)
async def scenario_service_error_handler(
    _request: Request,
    exc: ScenarioServiceError,
) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.response_content())


def _scenario_service() -> ScenarioService:
    return ScenarioService(
        data_root=data_loader.DATA_ROOT,
        active_scenario_id=data_loader.get_active_scenario(),
    )


def _active_assignments() -> list[dict]:
    seen = set()
    rows: list[dict] = []
    scenario_id = data_loader.get_active_scenario()
    for assignment in [*data_loader.assignments(), *accepted_assignments(scenario_id)]:
        if assignment.get("status") != "active":
            continue
        key = (assignment.get("incident_id"), assignment.get("crew_id"))
        if key in seen:
            continue
        seen.add(key)
        rows.append({**assignment, "scenario_id": assignment.get("scenario_id") or scenario_id})
    return rows


def _crew_name_map() -> dict[str, str]:
    return {str(row.get("crew_id")): str(row.get("crew_name")) for row in data_loader.crews()}


def _incidents_with_state() -> list[dict]:
    assignments = _active_assignments()
    latest_decisions = latest_decisions_by_incident(data_loader.get_active_scenario())
    crew_names = _crew_name_map()
    assignments_by_incident: dict[str, list[dict]] = {}
    for assignment in assignments:
        assignments_by_incident.setdefault(str(assignment.get("incident_id")), []).append(assignment)

    rows = []
    for incident in data_loader.incidents():
        incident_id = str(incident.get("incident_id"))
        incident_assignments = assignments_by_incident.get(incident_id, [])
        assigned_crews = [
            {
                "crew_id": assignment.get("crew_id"),
                "crew_name": crew_names.get(str(assignment.get("crew_id")), str(assignment.get("crew_id"))),
                "assignment_id": assignment.get("assignment_id"),
                "assigned_at": assignment.get("assigned_at"),
            }
            for assignment in incident_assignments
        ]
        latest_decision = latest_decisions.get(incident_id)
        rows.append(
            {
                **incident,
                "status": "assigned" if assigned_crews else incident.get("status"),
                "assigned_crews": assigned_crews,
                "current_decision": latest_decision,
            }
        )
    return rows


def _crews_with_state() -> list[dict]:
    assignments = _active_assignments()
    incident_map = {str(row.get("incident_id")): row for row in data_loader.incidents()}
    active_by_crew: dict[str, list[dict]] = {}
    for assignment in assignments:
        active_by_crew.setdefault(str(assignment.get("crew_id")), []).append(assignment)

    rows = []
    for crew in data_loader.crews():
        crew_id = str(crew.get("crew_id"))
        crew_assignments = active_by_crew.get(crew_id, [])
        assigned_incidents = [
            {
                "incident_id": assignment.get("incident_id"),
                "assignment_id": assignment.get("assignment_id"),
                "assigned_at": assignment.get("assigned_at"),
                "municipality": incident_map.get(str(assignment.get("incident_id")), {}).get("municipality"),
                "severity": incident_map.get(str(assignment.get("incident_id")), {}).get("severity"),
            }
            for assignment in crew_assignments
        ]
        rows.append(
            {
                **crew,
                "status": "assigned" if assigned_incidents else crew.get("status"),
                "assigned_incidents": assigned_incidents,
            }
        )
    return rows


@app.get("/health")
def health() -> HealthResponse:
    return {"status": "ok", "service": "ai-dispatch-advisor-api"}


@app.get("/api/scenarios")
def scenarios() -> list[ScenarioDescriptor]:
    return _scenario_service().list_scenarios()


@app.get("/api/scenarios/active")
def active_scenario() -> ScenarioDescriptor:
    return _scenario_service().active_scenario()


@app.put("/api/scenarios/active")
def activate_scenario(request: ScenarioActivationRequest) -> ScenarioDescriptor:
    candidate = _scenario_service().scenario(request.scenario_id)
    data_loader.set_active_scenario(candidate.scenario_id)
    return _scenario_service().active_scenario()


@app.get("/api/dashboard")
def dashboard() -> DashboardResponse:
    return dashboard_summary(
        _incidents_with_state(),
        _crews_with_state(),
        _active_assignments(),
        scenario_id=data_loader.get_active_scenario(),
    )


@app.get("/api/incidents")
def incidents() -> list[Incident]:
    return ranked_incidents(_incidents_with_state())


@app.get("/api/incidents/{incident_id}")
def incident_detail(incident_id: str) -> Incident:
    for incident in _incidents_with_state():
        if incident.get("incident_id") == incident_id:
            return incident
    raise HTTPException(status_code=404, detail="Incident not found")


@app.get("/api/crews")
def crews() -> list[Crew]:
    return _crews_with_state()


@app.get("/api/assignments")
def assignments() -> list[Assignment]:
    return _active_assignments()


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
def optimize(request: OptimizeRequest) -> Recommendation:
    incident_rows = ranked_incidents(_incidents_with_state())
    if request.incident_id:
        incident_rows = [row for row in incident_rows if row.get("incident_id") == request.incident_id]
    if not incident_rows:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = incident_rows[0]
    return recommend_assignment(incident, _crews_with_state(), _active_assignments())


@app.post("/api/recommendation-actions")
def recommendation_action(request: RecommendationActionRequest) -> RecommendationDecision:
    incident = next(
        (row for row in data_loader.incidents() if row.get("incident_id") == request.incident_id),
        None,
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    reason_source = request.reason if request.reason is not None else request.note
    reason = reason_source.strip() if reason_source else None
    if request.action in {"deferred", "overridden"} and not reason:
        raise HTTPException(status_code=400, detail=f"{request.action.title()} reason is required")

    return record_decision(
        scenario_id=data_loader.get_active_scenario(),
        incident_id=request.incident_id,
        action=request.action,
        reason=reason,
        recommendation=request.recommendation.model_dump(),
    )


@app.get("/api/audit/events")
def audit_events(limit: int = 25) -> list[RecommendationDecision]:
    return recent_decisions(
        data_loader.get_active_scenario(),
        limit=max(1, min(limit, 100)),
    )


@app.post("/api/chat")
def chat(request: ChatRequest) -> ChatResponse:
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
