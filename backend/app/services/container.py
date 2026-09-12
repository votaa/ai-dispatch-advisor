from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from .. import data_loader, decision_store
from ..copilot_config import CopilotConfig
from ..copilot_provider import CopilotProvider, configured_provider
from ..geography import GeographyRegistry, TravelEstimateService
from ..optimization.deterministic_engine import DeterministicOptimizationEngine
from ..optimization.policy import configured_recommendation_policy
from ..optimization.contracts import OptimizationEngine
from .assignment_service import AssignmentService
from .copilot_service import CopilotService
from .context_service import OperationalContextService
from .copilot_context_service import CopilotContextBuilder
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
    geography: GeographyRegistry
    travel_estimates: TravelEstimateService


def build_services(
    optimization_engine: OptimizationEngine | None = None,
    *,
    copilot_config: CopilotConfig | None = None,
    copilot_provider: CopilotProvider | None = None,
    copilot_clock: Callable[[], datetime] | None = None,
) -> ApplicationServices:
    optimization_engine = optimization_engine or DeterministicOptimizationEngine(
        configured_recommendation_policy()
    )
    copilot_config = copilot_config or CopilotConfig.from_env()
    copilot_provider = copilot_provider or configured_provider(copilot_config)
    geography = GeographyRegistry.from_csv()
    travel_estimates = TravelEstimateService(geography)
    assignments = AssignmentService(
        active_scenario_id=data_loader.get_active_scenario,
        baseline_assignments=data_loader.assignments,
        accepted_assignments=decision_store.accepted_assignments,
    )
    incidents = IncidentService(
        active_scenario_id=data_loader.get_active_scenario,
        incident_rows=data_loader.incidents,
        crew_rows=data_loader.crews,
        critical_facility_rows=data_loader.critical_facilities,
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
        travel_estimates=travel_estimates,
    )
    decisions = DecisionService(
        active_scenario_id=data_loader.get_active_scenario,
        crews=crews,
        incidents=incidents,
        record_decision=decision_store.record_decision,
        recent_decisions=decision_store.recent_decisions,
    )
    scenarios = ScenarioManagementService(
        data_root=lambda: data_loader.DATA_ROOT,
        active_scenario_id=data_loader.get_active_scenario,
        set_active_scenario=data_loader.set_active_scenario,
    )
    context = OperationalContextService(
        weather_rows=data_loader.weather,
        critical_facility_rows=data_loader.critical_facilities,
        topology_rows=data_loader.topology,
    )
    copilot_context = CopilotContextBuilder(
        active_scenario_id=data_loader.get_active_scenario,
        incidents=incidents,
        crews=crews,
        recommendations=recommendations,
        context=context,
        travel_estimates=travel_estimates,
        max_records=copilot_config.max_context_records,
    )
    copilot = CopilotService(
        active_scenario_id=data_loader.get_active_scenario,
        incidents=incidents,
        crews=crews,
        recommendations=recommendations,
        context=context,
        geography=geography,
        travel_estimates=travel_estimates,
        config=copilot_config,
        context_builder=copilot_context,
        provider=copilot_provider,
        clock=copilot_clock,
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
        geography=geography,
        travel_estimates=travel_estimates,
    )


def initialize_application() -> None:
    decision_store.init_store()
