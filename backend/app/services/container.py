from __future__ import annotations

from dataclasses import dataclass

from .. import data_loader, decision_store
from ..optimization.deterministic_engine import DeterministicOptimizationEngine
from ..optimization.contracts import OptimizationEngine
from .assignment_service import AssignmentService
from .copilot_service import CopilotService
from .context_service import OperationalContextService
from .crew_service import CrewService
from .decision_service import DecisionService
from .incident_service import IncidentService
from .recommendation_service import RecommendationService
from .scenario_management_service import ScenarioManagementService


@dataclass(frozen=True)
class ApplicationServices:
    assignments: AssignmentService
    incidents: IncidentService
    crews: CrewService
    recommendations: RecommendationService
    decisions: DecisionService
    scenarios: ScenarioManagementService
    copilot: CopilotService
    context: OperationalContextService


def build_services(optimization_engine: OptimizationEngine | None = None) -> ApplicationServices:
    optimization_engine = optimization_engine or DeterministicOptimizationEngine()
    assignments = AssignmentService(
        active_scenario_id=data_loader.get_active_scenario,
        baseline_assignments=data_loader.assignments,
        accepted_assignments=decision_store.accepted_assignments,
    )
    incidents = IncidentService(
        active_scenario_id=data_loader.get_active_scenario,
        incident_rows=data_loader.incidents,
        crew_rows=data_loader.crews,
        latest_decisions=decision_store.latest_decisions_by_incident,
        assignments=assignments,
        optimization_engine=optimization_engine,
    )
    crews = CrewService(
        crew_rows=data_loader.crews,
        incident_rows=data_loader.incidents,
        assignments=assignments,
    )
    recommendations = RecommendationService(
        active_scenario_id=data_loader.get_active_scenario,
        incidents=incidents,
        crews=crews,
        assignments=assignments,
        optimization_engine=optimization_engine,
    )
    decisions = DecisionService(
        active_scenario_id=data_loader.get_active_scenario,
        incidents=incidents,
        record_decision=decision_store.record_decision,
        recent_decisions=decision_store.recent_decisions,
    )
    scenarios = ScenarioManagementService(
        data_root=lambda: data_loader.DATA_ROOT,
        active_scenario_id=data_loader.get_active_scenario,
        set_active_scenario=data_loader.set_active_scenario,
    )
    copilot = CopilotService(incidents=incidents, recommendations=recommendations)
    context = OperationalContextService(
        weather_rows=data_loader.weather,
        critical_facility_rows=data_loader.critical_facilities,
        topology_rows=data_loader.topology,
    )
    return ApplicationServices(
        assignments=assignments,
        incidents=incidents,
        crews=crews,
        recommendations=recommendations,
        decisions=decisions,
        scenarios=scenarios,
        copilot=copilot,
        context=context,
    )


def initialize_application() -> None:
    decision_store.init_store()
