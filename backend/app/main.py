from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api_models import (
    ChatRequest,
    ChatResponse,
    DashboardResponse,
    HealthResponse,
    OptimizeRequest,
    RecommendationActionRequest,
    ScenarioActivationRequest,
)
from .domain.models import Assignment, Crew, Incident, Recommendation, RecommendationDecision
from .scenario_service import ScenarioDescriptor, ScenarioServiceError
from .services import (
    DecisionReasonRequiredError,
    EntityNotFoundError,
    build_services,
    initialize_application,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    initialize_application()
    yield


app = FastAPI(
    title="AI Dispatch Advisor API",
    description="Developer Bootstrap MVP API for synthetic utility outage dispatch data.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

services = build_services()


@app.exception_handler(ScenarioServiceError)
async def scenario_service_error_handler(
    _request: Request,
    exc: ScenarioServiceError,
) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.response_content())


@app.get("/health")
def health() -> HealthResponse:
    return {"status": "ok", "service": "ai-dispatch-advisor-api"}


@app.get("/api/scenarios")
def scenarios() -> list[ScenarioDescriptor]:
    return services.scenarios.list()


@app.get("/api/scenarios/active")
def active_scenario() -> ScenarioDescriptor:
    return services.scenarios.active()


@app.put("/api/scenarios/active")
def activate_scenario(request: ScenarioActivationRequest) -> ScenarioDescriptor:
    return services.scenarios.activate(request.scenario_id)


@app.get("/api/dashboard")
def dashboard() -> DashboardResponse:
    return services.recommendations.dashboard()


@app.get("/api/incidents")
def incidents() -> list[Incident]:
    return services.incidents.list_ranked()


@app.get("/api/incidents/{incident_id}")
def incident_detail(incident_id: str) -> Incident:
    try:
        return services.incidents.get(incident_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/crews")
def crews() -> list[Crew]:
    return services.crews.list()


@app.get("/api/assignments")
def assignments() -> list[Assignment]:
    return services.assignments.list_active()


@app.get("/api/weather")
def weather() -> list[dict]:
    return services.context.weather()


@app.get("/api/critical-facilities")
def critical_facilities() -> list[dict]:
    return services.context.critical_facilities()


@app.get("/api/topology")
def topology() -> list[dict]:
    return services.context.topology()


@app.post("/api/optimize")
def optimize(request: OptimizeRequest) -> Recommendation:
    try:
        return services.recommendations.recommend(request.incident_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/recommendation-actions")
def recommendation_action(request: RecommendationActionRequest) -> RecommendationDecision:
    try:
        return services.decisions.record(
            incident_id=request.incident_id,
            action=request.action,
            recommendation=request.recommendation,
            reason=request.reason,
            note=request.note,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DecisionReasonRequiredError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/audit/events")
def audit_events(limit: int = 25) -> list[RecommendationDecision]:
    return services.decisions.recent(limit)


@app.post("/api/chat")
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return services.copilot.respond(request.message, request.incident_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
