import {
  ArrowLeft,
  AlertTriangle,
  BarChart3,
  Bot,
  Check,
  ClipboardList,
  CloudLightning,
  Map,
  Pause,
  Pencil,
  RadioTower,
  ShieldAlert,
  Users
} from "lucide-react";
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ElementType, ReactNode } from "react";
import { api } from "./api";
import { CopilotMarkdown } from "./CopilotMarkdown";
import { AutocompleteSearch, buildAutocompleteSuggestions } from "./components/AutocompleteSearch";
import type { AutocompleteField } from "./components/AutocompleteSearch";
import { ExpandableWorkspace } from "./components/ExpandableWorkspace";
import {
  ContextualNavigationPanel,
  EntityNavigationActions
} from "./components/ContextualNavigation";
import type {
  CrewNavigationFilter,
  IncidentNavigationFilter,
  NavigationResolverContext,
  OperationalNavigationCommand
} from "./components/ContextualNavigation";
import {
  ResizableSidebar,
  SIDEBAR_DEFAULT_WIDTH,
  SIDEBAR_MAX_WIDTH,
  SIDEBAR_MIN_WIDTH
} from "./components/ResizableSidebar";
import { SideSheet } from "./components/SideSheet";
import { ShowOnMapButton } from "./components/ShowOnMapButton";
import type { MapEntityKind } from "./components/ShowOnMapButton";
import type { MapNavigationTarget } from "./components/OperationsMap";
import { useFittedPageSize } from "./hooks/useFittedPageSize";
import type { CrewWorkspaceState, IncidentWorkspaceState, MapWorkspaceState } from "./navigationState";
import type {
  Assignment,
  CopilotResponse,
  Crew,
  DashboardSummary,
  Incident,
  Recommendation,
  RecommendationAction,
  RecommendationActionType,
  ScenarioDescriptor
} from "./types";

const OperationsMap = lazy(() => import("./components/OperationsMap"));

type ViewKey = "map" | "dashboard" | "dispatch" | "incidents" | "crews" | "storm" | "scenario" | "copilot";
type ChatTurn = {
  question: string;
  answer: string;
  error?: boolean;
  metadata?: Omit<CopilotResponse, "answer">;
};
type IncidentSortKey = "id" | "region" | "customers" | "severity" | "criticalFacility" | "hazard" | "assigned" | "decision" | "etr";
type SortDirection = "asc" | "desc";
type CrewSortKey = "name" | "status" | "capability" | "shift" | "assigned" | "travel";
type ExpandableWorkspaceKey = "dashboard" | "dispatch" | "incidents" | "crews" | "storm";
type NavigationFocusOrigin = { id: string; occurrence: number };
type ReturnNavigationContext = {
  scenarioId: string;
  sourceView: ViewKey;
  selectedIncidentId?: string;
  selectedCrewId?: string;
  expandedWorkspace: ExpandableWorkspaceKey | null;
  recommendationsOpen: boolean;
  incidentDetailOpen: boolean;
  dashboardDisplayPercentage: number;
  focusOrigin: NavigationFocusOrigin | null;
  incidentState?: IncidentWorkspaceState;
  crewState?: CrewWorkspaceState;
  mapState?: MapWorkspaceState;
};

const incidentSortOptions: Array<[IncidentSortKey, string]> = [
  ["id", "Incident"],
  ["region", "Region"],
  ["customers", "Customers"],
  ["severity", "Severity"],
  ["criticalFacility", "Critical Facility"],
  ["hazard", "Hazard"],
  ["assigned", "Assigned Crews"],
  ["decision", "Decision"],
  ["etr", "ETR"]
];

const incidentAutocompleteFields: AutocompleteField<Incident>[] = [
  { group: "Incident ID", values: (incident) => incident.incident_id },
  { group: "Feeder", values: (incident) => incident.feeder },
  { group: "Municipality", values: (incident) => incident.municipality },
  { group: "Hazard", values: (incident) => incident.hazard }
];

const crewAutocompleteFields: AutocompleteField<Crew>[] = [
  { group: "Crew ID", values: (crew) => crew.crew_id },
  { group: "Crew Name", values: (crew) => crew.crew_name },
  { group: "Location", values: (crew) => crew.current_location },
  { group: "Capability", values: (crew) => crew.capability },
  { group: "Region", values: (crew) => crew.home_region },
  { group: "Assigned Incident", values: (crew) => crew.assigned_incidents.map((assignment) => assignment.incident_id) }
];

const navItems: Array<{ key: ViewKey; label: string; icon: ElementType }> = [
  { key: "dashboard", label: "Dashboard", icon: BarChart3 },
  { key: "dispatch", label: "Dispatch", icon: RadioTower },
  { key: "incidents", label: "Incidents", icon: ClipboardList },
  { key: "crews", label: "Crew Board", icon: Users },
  { key: "map", label: "Operations Map", icon: Map },
  { key: "storm", label: "Storm Mode", icon: CloudLightning },
  { key: "scenario", label: "Scenario", icon: Map },
  { key: "copilot", label: "AI Copilot", icon: Bot }
];

const SIDEBAR_STORAGE_KEY = "aida.ui.sidebar-width.v1";
const DASHBOARD_DISPLAY_PERCENTAGES = [25, 50, 75, 100] as const;
const COPILOT_PROMPTS = [
  "What should I focus on first?",
  "How many customers are out across all active incidents?",
  "How many customers are served in Nassau County?",
  "What percentage of customers in Melville are affected?",
  "How many crews are available in the active scenario?",
  "Show available line crews in Eastern Suffolk.",
  "Break down critical facilities by level.",
  "Why was this crew recommended?",
  "Summarize storm status"
] as const;

function initialSidebarWidth() {
  try {
    const storedWidth = Number.parseInt(window.localStorage.getItem(SIDEBAR_STORAGE_KEY) ?? "", 10);
    if (Number.isFinite(storedWidth)) {
      return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, storedWidth));
    }
  } catch {
    // Storage can be unavailable in privacy-restricted browser contexts.
  }
  return SIDEBAR_DEFAULT_WIDTH;
}

function severityClass(severity: string) {
  return `severity severity-${severity.toLowerCase()}`;
}

function countBy<T>(items: T[], valueFor: (item: T) => string) {
  return items.reduce<Record<string, number>>((counts, item) => {
    const value = valueFor(item);
    counts[value] = (counts[value] ?? 0) + 1;
    return counts;
  }, {});
}

function facetCountsFor<T>(items: T[], valueFor: (item: T) => string): Record<string, number> {
  return { ...countBy(items, valueFor), all: items.length };
}

function App() {
  const [view, setView] = useState<ViewKey>("dashboard");
  const [sidebarWidth, setSidebarWidth] = useState(initialSidebarWidth);
  const [recommendationsOpen, setRecommendationsOpen] = useState(false);
  const [incidentDetailOpen, setIncidentDetailOpen] = useState(false);
  const [expandedWorkspace, setExpandedWorkspace] = useState<ExpandableWorkspaceKey | null>(null);
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [dashboardDisplayPercentage, setDashboardDisplayPercentage] = useState<number>(25);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [crews, setCrews] = useState<Crew[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [recommendationActions, setRecommendationActions] = useState<RecommendationAction[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | undefined>();
  const [selectedCrewId, setSelectedCrewId] = useState<string | undefined>();
  const [mapNavigationTarget, setMapNavigationTarget] = useState<MapNavigationTarget | null>(null);
  const [incidentNavigationFilter, setIncidentNavigationFilter] = useState<{ requestId: number; filter: IncidentNavigationFilter } | null>(null);
  const [crewNavigationFilter, setCrewNavigationFilter] = useState<{ requestId: number; filter: CrewNavigationFilter } | null>(null);
  const [returnNavigation, setReturnNavigation] = useState<ReturnNavigationContext | null>(null);
  const [restoringNavigation, setRestoringNavigation] = useState<ReturnNavigationContext | null>(null);
  const [chatMessage, setChatMessage] = useState("What should I focus on first?");
  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<RecommendationActionType | null>(null);
  const [actionMessage, setActionMessage] = useState("");
  const [actionFailed, setActionFailed] = useState(false);
  const [scenarios, setScenarios] = useState<ScenarioDescriptor[]>([]);
  const [activeScenario, setActiveScenario] = useState<ScenarioDescriptor | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [scenarioMessage, setScenarioMessage] = useState("");
  const [error, setError] = useState<string>("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [recommendationError, setRecommendationError] = useState("");
  const [recommendationRequestVersion, setRecommendationRequestVersion] = useState(0);
  const pageHeadingRef = useRef<HTMLHeadingElement>(null);
  const recommendationTriggerRef = useRef<HTMLButtonElement>(null);
  const incidentDetailTriggerRef = useRef<HTMLElement>(null);
  const mapNavigationRequestRef = useRef(0);
  const inventoryNavigationRequestRef = useRef(0);
  const incidentWorkspaceStatesRef = useRef<Partial<Record<ViewKey, IncidentWorkspaceState>>>({});
  const crewWorkspaceStateRef = useRef<CrewWorkspaceState | undefined>(undefined);
  const mapWorkspaceStateRef = useRef<MapWorkspaceState | undefined>(undefined);

  useEffect(() => {
    loadApplication();
  }, []);

  useEffect(() => {
    pageHeadingRef.current?.focus();
  }, [view]);

  useEffect(() => {
    if (!restoringNavigation || view !== restoringNavigation.sourceView) return;
    let secondFrame: number | undefined;
    const firstFrame = window.requestAnimationFrame(() => {
      secondFrame = window.requestAnimationFrame(() => {
        const origin = restoringNavigation.focusOrigin;
        const candidates = origin
          ? Array.from(document.querySelectorAll<HTMLElement>("[data-navigation-origin]"))
              .filter((element) => element.dataset.navigationOrigin === origin.id)
          : [];
        (candidates[origin?.occurrence ?? -1] ?? candidates[0] ?? pageHeadingRef.current)?.focus();
        setRestoringNavigation(null);
      });
    });
    return () => {
      window.cancelAnimationFrame(firstFrame);
      if (secondFrame !== undefined) window.cancelAnimationFrame(secondFrame);
    };
  }, [restoringNavigation, view]);

  useEffect(() => {
    try {
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(sidebarWidth));
    } catch {
      // Resizing remains available when persistence is blocked.
    }
  }, [sidebarWidth]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedIncidentId) {
      setRecommendation(null);
      setRecommendationError("");
      setRecommendationLoading(false);
      return;
    }
    setRecommendation(null);
    setRecommendationError("");
    setRecommendationLoading(true);
    api.optimize(selectedIncidentId)
      .then((nextRecommendation) => {
        if (!cancelled) setRecommendation(nextRecommendation);
      })
      .catch((err: Error) => {
        if (!cancelled) setRecommendationError(err.message);
      })
      .finally(() => {
        if (!cancelled) setRecommendationLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedIncidentId, recommendationRequestVersion]);

  const selectedIncident = useMemo(
    () => incidents.find((incident) => incident.incident_id === selectedIncidentId) ?? incidents[0],
    [incidents, selectedIncidentId]
  );
  const incidentDetail = useMemo(
    () => incidents.find((incident) => incident.incident_id === selectedIncidentId),
    [incidents, selectedIncidentId]
  );
  const selectedCrew = useMemo(
    () => crews.find((crew) => crew.crew_id === selectedCrewId),
    [crews, selectedCrewId]
  );
  const selectedCrewContext = selectedCrew ?? selectedIncident?.assigned_crews[0];
  const navigationContext = useMemo<NavigationResolverContext>(
    () => ({ incidents, crews }),
    [crews, incidents]
  );

  const criticalIncidents = incidents.filter((incident) => incident.critical_facility);
  const withheldIncidents = incidents.filter((incident) => incident.ranking_status === "withheld");
  const rankableIncidents = incidents.filter((incident) => incident.ranking_status !== "withheld");
  const operationalDataUnavailable = Boolean(error && !dashboard && incidents.length === 0 && crews.length === 0);
  const dashboardIncidentLimit = dashboard
    ? dashboard.active_incidents === 0
      ? 0
      : Math.min(
          dashboard.active_incidents,
          Math.max(1, Math.ceil((dashboard.active_incidents * dashboardDisplayPercentage) / 100)),
          rankableIncidents.length || dashboard.top_incidents.length
        )
    : 0;
  const dashboardIncidentLabel = dashboard && dashboard.active_incidents === 0
    ? `All ${dashboard.active_incidents} Priority Incidents`
    : `Top ${dashboardIncidentLimit} Priority Incidents`;

  useEffect(() => {
    if (incidentDetailOpen && !incidentDetail) {
      setIncidentDetailOpen(false);
    }
  }, [incidentDetail, incidentDetailOpen]);

  async function loadApplication() {
    setInitialLoading(true);
    setError("");
    try {
      const [{ incidentData }, scenarioData, activeScenarioData] = await Promise.all([
        refreshOperationalState(),
        api.scenarios(),
        api.activeScenario()
      ]);
      setSelectedIncidentId(
        incidentData.find((incident) => incident.ranking_status !== "withheld")?.incident_id
      );
      setScenarios(scenarioData);
      setActiveScenario(activeScenarioData);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Application data could not be loaded";
      setError(message);
    } finally {
      setInitialLoading(false);
    }
  }

  async function refreshOperationalState() {
    const [dashboardData, incidentData, crewData, assignmentData, auditData] = await Promise.all([
      api.dashboard(),
      api.incidents(),
      api.crews(),
      api.assignments(),
      api.auditEvents()
    ]);
    setDashboard(dashboardData);
    setIncidents(incidentData);
    setCrews(crewData);
    setAssignments(assignmentData);
    setRecommendationActions(auditData);
    return { dashboardData, incidentData, crewData, assignmentData, auditData };
  }

  async function askCopilot() {
    const question = chatMessage.trim();
    if (!question) return;
    setChatLoading(true);
    try {
      const response = await api.chat(question, selectedIncidentId, selectedCrewContext?.crew_id);
      const { answer, ...metadata } = response;
      setChatTurns((turns) => [{ question, answer, metadata }, ...turns]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Copilot request failed";
      setChatTurns((turns) => [{ question, answer: `Unable to reach Copilot: ${message}`, error: true }, ...turns]);
    } finally {
      setChatLoading(false);
    }
  }

  async function activateScenario(scenarioId: string) {
    if (scenarioLoading || scenarioId === activeScenario?.scenario_id) return;

    if (recommendationActions.length > 0) {
      const targetScenario = scenarios.find((scenario) => scenario.scenario_id === scenarioId);
      const shouldSwitch = window.confirm(
        `The active scenario has recorded dispatch decisions. Switch to ${targetScenario?.name ?? scenarioId}?\n\n` +
          "Existing decisions will remain saved under the current scenario and will reappear when you switch back."
      );
      if (!shouldSwitch) return;
    }

    setScenarioLoading(true);
    setScenarioMessage("");
    setError("");
    try {
      setExpandedWorkspace(null);
      setRecommendationsOpen(false);
      setIncidentDetailOpen(false);
      const activatedScenario = await api.activateScenario(scenarioId);
      setActiveScenario(activatedScenario);
      setScenarios((items) =>
        items.map((item) => ({ ...item, is_active: item.scenario_id === activatedScenario.scenario_id }))
      );
      setSelectedIncidentId(undefined);
      setSelectedCrewId(undefined);
      setMapNavigationTarget(null);
      setIncidentNavigationFilter(null);
      setCrewNavigationFilter(null);
      setReturnNavigation(null);
      setRestoringNavigation(null);
      setRecommendation(null);
      setRecommendationError("");
      setActionMessage("");
      setActionFailed(false);
      setChatTurns([]);

      const { incidentData } = await refreshOperationalState();
      setSelectedIncidentId(
        incidentData.find((incident) => incident.ranking_status !== "withheld")?.incident_id
      );
      setScenarioMessage(`${activatedScenario.name} activated.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Scenario activation failed";
      setScenarioMessage(message);
    } finally {
      setScenarioLoading(false);
    }
  }

  function usePrompt(prompt: string) {
    setChatMessage(prompt);
  }

  function selectView(nextView: ViewKey, clearReturnNavigation = false) {
    if (clearReturnNavigation) {
      setReturnNavigation(null);
      setRestoringNavigation(null);
    }
    setExpandedWorkspace(null);
    if (nextView !== "dashboard" && nextView !== "dispatch") {
      setRecommendationsOpen(false);
    }
    if (nextView !== "incidents") {
      setIncidentDetailOpen(false);
    }
    setView(nextView);
  }

  function navigationFocusOrigin(trigger?: HTMLElement): NavigationFocusOrigin | null {
    const id = trigger?.dataset.navigationOrigin;
    if (!id || !trigger) return null;
    const matches = Array.from(document.querySelectorAll<HTMLElement>("[data-navigation-origin]"))
      .filter((element) => element.dataset.navigationOrigin === id);
    return { id, occurrence: Math.max(0, matches.indexOf(trigger)) };
  }

  function captureReturnNavigation(trigger?: HTMLElement) {
    if (!activeScenario) return;
    setReturnNavigation({
      scenarioId: activeScenario.scenario_id,
      sourceView: view,
      selectedIncidentId,
      selectedCrewId,
      expandedWorkspace,
      recommendationsOpen,
      incidentDetailOpen,
      dashboardDisplayPercentage,
      focusOrigin: navigationFocusOrigin(trigger),
      incidentState: incidentWorkspaceStatesRef.current[view],
      crewState: view === "crews" ? crewWorkspaceStateRef.current : undefined,
      mapState: view === "map" ? mapWorkspaceStateRef.current : undefined
    });
  }

  function returnToPreviousView() {
    if (!returnNavigation || returnNavigation.scenarioId !== activeScenario?.scenario_id) {
      setReturnNavigation(null);
      return;
    }
    const context = returnNavigation;
    setMapNavigationTarget(null);
    setIncidentNavigationFilter(null);
    setCrewNavigationFilter(null);
    selectView(context.sourceView);
    setSelectedIncidentId(context.selectedIncidentId);
    setSelectedCrewId(context.selectedCrewId);
    setExpandedWorkspace(context.expandedWorkspace);
    setRecommendationsOpen(context.recommendationsOpen);
    setIncidentDetailOpen(context.incidentDetailOpen);
    setDashboardDisplayPercentage(context.dashboardDisplayPercentage);
    setRestoringNavigation(context);
    setReturnNavigation(null);
  }

  function openCrewDetails(crewId: string) {
    setSelectedCrewId(crewId);
    selectView("crews");
  }

  function showIncidentDetails(incidentId: string, trigger?: HTMLElement) {
    incidentDetailTriggerRef.current = trigger ?? null;
    setSelectedIncidentId(incidentId);
    setIncidentDetailOpen(true);
  }

  function openIncidentDetails(incidentId: string, trigger?: HTMLElement) {
    showIncidentDetails(incidentId, trigger);
    selectView("incidents");
  }

  function showOnMap(entityKind: MapEntityKind, entityId: string) {
    mapNavigationRequestRef.current += 1;
    setMapNavigationTarget({ entityKind, entityId, requestId: mapNavigationRequestRef.current });
    selectView("map");
  }

  function navigateOperationally(command: OperationalNavigationCommand, trigger?: HTMLElement) {
    captureReturnNavigation(trigger);
    if (command.type === "open_incident") {
      openIncidentDetails(command.incidentId, trigger);
      return;
    }
    if (command.type === "open_crew") {
      openCrewDetails(command.crewId);
      return;
    }
    if (command.type === "show_on_map") {
      showOnMap(command.entityKind, command.entityId);
      return;
    }

    inventoryNavigationRequestRef.current += 1;
    if (command.type === "filter_incidents") {
      setIncidentDetailOpen(false);
      setIncidentNavigationFilter({
        requestId: inventoryNavigationRequestRef.current,
        filter: command.filter
      });
      selectView("incidents");
      return;
    }
    setCrewNavigationFilter({
      requestId: inventoryNavigationRequestRef.current,
      filter: command.filter
    });
    selectView("crews");
  }

  const handleMapNavigation = useCallback((requestId: number) => {
    setMapNavigationTarget((current) => current?.requestId === requestId ? null : current);
  }, []);

  async function recordRecommendationAction(action: RecommendationActionType, note?: string, selectedCrewId?: string) {
    if (!recommendation) return;

    setActionLoading(action);
    setActionMessage("");
    setActionFailed(false);
    try {
      const event = await api.recordRecommendationAction(action, recommendation, note?.trim() || undefined, selectedCrewId);
      await refreshOperationalState();
      if (selectedIncidentId) {
        const nextRecommendation = await api.optimize(selectedIncidentId);
        setRecommendation(nextRecommendation);
      }
      setRecommendationActions((actions) => [event, ...actions.filter((item) => item.event_id !== event.event_id)]);
      setActionMessage(`Recommendation ${formatAction(action)}.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Recommendation action failed";
      setActionFailed(true);
      setActionMessage(message);
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div className="app-shell" style={{ "--sidebar-width": `${sidebarWidth}px` } as CSSProperties}>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <ResizableSidebar onWidthChange={setSidebarWidth} width={sidebarWidth}>
        <div className="brand">
          <div className="brand-mark">AI</div>
          <div>
            <strong>Dispatch Advisor</strong>
            <span>Utility outage POC</span>
          </div>
        </div>
        <nav className="nav-list" aria-label="Primary navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                aria-current={view === item.key ? "page" : undefined}
                className={view === item.key ? "nav-item active" : "nav-item"}
                onClick={() => selectView(item.key, true)}
                type="button"
              >
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </ResizableSidebar>

      <main
        aria-busy={initialLoading || scenarioLoading}
        aria-labelledby="page-heading"
        className="main"
        id="main-content"
      >
        <header className="topbar">
          <div>
            <p className="eyebrow">Developer Bootstrap MVP</p>
            <h1 id="page-heading" ref={pageHeadingRef} tabIndex={-1}>{navItems.find((item) => item.key === view)?.label}</h1>
          </div>
          <div className="scenario-control">
            <div className="scenario-selector">
              <label htmlFor="active-scenario">
                <span className="pulse" />
                Synthetic scenario
              </label>
              <select
                aria-label="Active synthetic scenario"
                disabled={scenarioLoading || scenarios.length === 0}
                id="active-scenario"
                onChange={(event) => activateScenario(event.target.value)}
                value={activeScenario?.scenario_id ?? ""}
              >
                {!activeScenario ? <option value="">Loading scenarios...</option> : null}
                {scenarios.map((scenario) => (
                  <option key={scenario.scenario_id} value={scenario.scenario_id}>
                    {scenario.name}
                  </option>
                ))}
              </select>
            </div>
            <ScenarioFreshnessLabel scenario={activeScenario} />
          </div>
        </header>

        {returnNavigation && returnNavigation.scenarioId === activeScenario?.scenario_id ? (
          <nav aria-label="Return navigation" className="return-navigation">
            <button onClick={returnToPreviousView} type="button">
              <ArrowLeft aria-hidden="true" size={16} />
              Return to {navItems.find((item) => item.key === returnNavigation.sourceView)?.label}
            </button>
            <span>Restores your prior filters, result position, selection, and focus.</span>
          </nav>
        ) : null}

        {scenarioLoading ? (
          <div aria-live="polite" className="loading-banner" role="status">
            <strong>Loading scenario data...</strong>
            <span>
              {scenarios.find((scenario) => scenario.scenario_id === activeScenario?.scenario_id)?.name ?? "Selected scenario"} is being refreshed. Large scenarios may take longer to rank.
            </span>
          </div>
        ) : scenarioMessage ? (
          <div
            aria-live={scenarioMessage.endsWith("activated.") ? "polite" : "assertive"}
            className={scenarioMessage.endsWith("activated.") ? "success-banner" : "error-banner"}
            role={scenarioMessage.endsWith("activated.") ? "status" : "alert"}
          >
            {scenarioMessage}
          </div>
        ) : null}

        {error ? (
          <div className="error-banner system-banner" role="alert">
            <div>
              <strong>Backend unavailable</strong>
              <span>{error}</span>
            </div>
            <button disabled={initialLoading} onClick={loadApplication} type="button">
              {initialLoading ? "Retrying..." : "Retry connection"}
            </button>
          </div>
        ) : null}

        {withheldIncidents.length ? (
          <div className="ranking-warning-banner" role="alert">
            <strong>Ranking data requires review</strong>
            <span>
              {withheldIncidents.length} incident{withheldIncidents.length === 1 ? " is" : "s are"} visible but withheld from automated ranking because critical-facility data is incomplete or unknown.
            </span>
          </div>
        ) : null}

        {view === "dashboard" && (initialLoading ? (
          <ViewState title="Loading dashboard..." message="Retrieving outage, crew, and recommendation data." />
        ) : operationalDataUnavailable || !dashboard ? (
          <ViewState
            actionLabel="Retry connection"
            message="Dashboard data could not be loaded from the backend."
            onAction={loadApplication}
            title="Dashboard unavailable"
          />
        ) : (
          <section className="dashboard-view">
            <div className="metric-grid">
              <Metric className="metric-customers-out" label="Customers Out" value={dashboard.customers_out.toLocaleString()} />
              <Metric label="Active Incidents" value={dashboard.active_incidents} />
              <Metric label="Available Crews" value={dashboard.available_crews} />
              <Metric label="Crews Assigned" value={dashboard.assigned_crews} />
              <Metric label="Critical Facility Events" value={dashboard.critical_facility_incidents} />
            </div>

            <div className="dashboard-workspace">
              <ExpandableWorkspace
                action={(
                    <div className="dashboard-panel-actions">
                      <label>
                        Search Top {dashboardIncidentLimit} Incidents Shown
                        <select
                          aria-label="Dashboard incidents shown"
                          disabled={dashboard.active_incidents === 0}
                          onChange={(event) => setDashboardDisplayPercentage(Number(event.target.value))}
                          value={dashboardDisplayPercentage}
                        >
                          {DASHBOARD_DISPLAY_PERCENTAGES.map((percentage) => (
                            <option key={percentage} value={percentage}>
                              {percentage}%
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        aria-controls="recommendations-sheet"
                        aria-expanded={recommendationsOpen}
                        aria-label="Open recommendations"
                        className="panel-title-action"
                        onClick={() => setRecommendationsOpen(true)}
                        ref={recommendationTriggerRef}
                        type="button"
                      >
                        Recommendations
                      </button>
                    </div>
                )}
                expanded={expandedWorkspace === "dashboard"}
                icon={AlertTriangle}
                id="dashboard-priority-workspace"
                onExpand={() => setExpandedWorkspace("dashboard")}
                onRestore={() => setExpandedWorkspace(null)}
                title={dashboardIncidentLabel}
              >
                <p className="dashboard-incident-summary" aria-live="polite">
                  Showing {dashboardIncidentLimit} of {dashboard.active_incidents} active incidents
                </p>
                <IncidentTable
                  emptyMessage="No priority incidents are active in this scenario."
                  incidents={(incidents.length ? rankableIncidents : dashboard.top_incidents).slice(0, dashboardIncidentLimit)}
                  key={`dashboard-incidents-${activeScenario?.scenario_id ?? "loading"}`}
                  selectedIncidentId={selectedIncidentId}
                  searchLabel={`Search Top ${dashboardIncidentLimit} Incidents Shown`}
                  preserveOrder
                  layoutKey={expandedWorkspace === "dashboard" ? "expanded" : "embedded"}
                  navigationContext={navigationContext}
                  syncSelectionToFirst
                  tableLabel="Priority dispatch queue"
                  restoredState={restoringNavigation?.sourceView === "dashboard" ? restoringNavigation.incidentState : undefined}
                  onStateChange={(state) => { incidentWorkspaceStatesRef.current.dashboard = state; }}
                  onSelect={setSelectedIncidentId}
                  onActivate={showIncidentDetails}
                  onNavigate={navigateOperationally}
                />
              </ExpandableWorkspace>
            </div>
          </section>
        ))}

        {view === "dispatch" && (initialLoading ? (
          <ViewState title="Loading dispatch workspace..." message="Retrieving incidents and recommendations." />
        ) : operationalDataUnavailable ? (
          <ViewState
            actionLabel="Retry connection"
            message="Dispatch data could not be loaded from the backend."
            onAction={loadApplication}
            title="Dispatch unavailable"
          />
        ) : (
          <section className="queue-workspace">
            <ExpandableWorkspace
              action={(
                  <button
                    aria-controls="recommendations-sheet"
                    aria-expanded={recommendationsOpen}
                    aria-label="Open recommendations"
                    className="panel-title-action"
                    onClick={() => setRecommendationsOpen(true)}
                    ref={recommendationTriggerRef}
                    type="button"
                  >
                    Recommendations
                  </button>
              )}
              expanded={expandedWorkspace === "dispatch"}
              icon={RadioTower}
              id="dispatch-incident-workspace"
              onExpand={() => setExpandedWorkspace("dispatch")}
              onRestore={() => setExpandedWorkspace(null)}
              title="Incident Queue"
            >
              <IncidentTable
                emptyMessage="No active incidents are available for dispatch."
                incidents={incidents}
                layoutKey={expandedWorkspace === "dispatch" ? "expanded" : "embedded"}
                navigationContext={navigationContext}
                key={`dispatch-incidents-${activeScenario?.scenario_id ?? "loading"}`}
                selectedIncidentId={selectedIncidentId}
                syncSelectionToFirst
                tableLabel="Dispatch incident queue"
                restoredState={restoringNavigation?.sourceView === "dispatch" ? restoringNavigation.incidentState : undefined}
                onStateChange={(state) => { incidentWorkspaceStatesRef.current.dispatch = state; }}
                onSelect={setSelectedIncidentId}
                onActivate={showIncidentDetails}
                onNavigate={navigateOperationally}
              />
            </ExpandableWorkspace>
          </section>
        ))}

        {view === "incidents" && (initialLoading ? (
          <ViewState title="Loading incidents..." message="Retrieving the active incident queue." />
        ) : operationalDataUnavailable ? (
          <ViewState
            actionLabel="Retry connection"
            message="Incident data could not be loaded from the backend."
            onAction={loadApplication}
            title="Incidents unavailable"
          />
        ) : (
          <ExpandableWorkspace
            expanded={expandedWorkspace === "incidents"}
            icon={ClipboardList}
            id="active-incidents-workspace"
            onExpand={() => setExpandedWorkspace("incidents")}
            onRestore={() => setExpandedWorkspace(null)}
            title="Active Incidents"
          >
            <IncidentTable
              emptyMessage="No active incidents are available in this scenario."
              incidents={incidents}
              layoutKey={expandedWorkspace === "incidents" ? "expanded" : "embedded"}
              navigationContext={navigationContext}
              navigationFilterRequest={incidentNavigationFilter}
              key={`active-incidents-${activeScenario?.scenario_id ?? "loading"}`}
              selectedIncidentId={selectedIncidentId}
              tableLabel="Active incidents"
              restoredState={restoringNavigation?.sourceView === "incidents" ? restoringNavigation.incidentState : undefined}
              onStateChange={(state) => { incidentWorkspaceStatesRef.current.incidents = state; }}
              onSelect={openIncidentDetails}
              onNavigate={navigateOperationally}
            />
          </ExpandableWorkspace>
        ))}

        {view === "map" && (initialLoading || scenarioLoading ? (
          <ViewState title="Loading operations map..." message="Retrieving incident and crew locations." />
        ) : operationalDataUnavailable ? (
          <ViewState title="Operations map unavailable" message="Location data could not be loaded from the backend." actionLabel="Retry connection" onAction={loadApplication} />
        ) : (
          <Suspense fallback={<ViewState title="Loading map..." message="Preparing the geographic view." />}>
            <OperationsMap
              key={`operations-map-${activeScenario?.scenario_id ?? "loading"}`}
              incidents={incidents}
              crews={crews}
              navigationTarget={mapNavigationTarget}
              navigationContext={navigationContext}
              onNavigate={navigateOperationally}
              onNavigationHandled={handleMapNavigation}
              restoredState={restoringNavigation?.sourceView === "map" ? restoringNavigation.mapState : undefined}
              onStateChange={(state) => { mapWorkspaceStateRef.current = state; }}
            />
          </Suspense>
        ))}

        {view === "crews" && (initialLoading ? (
          <ViewState title="Loading crew board..." message="Retrieving crew availability and assignments." />
        ) : operationalDataUnavailable ? (
          <ViewState
            actionLabel="Retry connection"
            message="Crew data could not be loaded from the backend."
            onAction={loadApplication}
            title="Crew board unavailable"
          />
        ) : (
          <ExpandableWorkspace
            expanded={expandedWorkspace === "crews"}
            icon={Users}
            id="crew-board-workspace"
            onExpand={() => setExpandedWorkspace("crews")}
            onRestore={() => setExpandedWorkspace(null)}
            title="Crew Board"
          >
            {crews.length === 0 ? (
              <EmptyState message="No crews are available in this scenario." />
            ) : (
              <CrewBoard
                crews={crews}
                key={`crew-board-${activeScenario?.scenario_id ?? "loading"}`}
                layoutKey={expandedWorkspace === "crews" ? "expanded" : "embedded"}
                navigationContext={navigationContext}
                navigationFilterRequest={crewNavigationFilter}
                onCloseDetails={() => setSelectedCrewId(undefined)}
                onSelectCrew={setSelectedCrewId}
                onNavigate={navigateOperationally}
                selectedCrew={selectedCrew}
                selectedCrewId={selectedCrewId}
                restoredState={restoringNavigation?.sourceView === "crews" ? restoringNavigation.crewState : undefined}
                onStateChange={(state) => { crewWorkspaceStateRef.current = state; }}
              />
            )}
          </ExpandableWorkspace>
        ))}

        {view === "storm" && (initialLoading ? (
          <ViewState title="Loading storm mode..." message="Retrieving high-priority and critical-facility events." />
        ) : operationalDataUnavailable || !dashboard ? (
          <ViewState
            actionLabel="Retry connection"
            message="Storm-mode data could not be loaded from the backend."
            onAction={loadApplication}
            title="Storm mode unavailable"
          />
        ) : (
          <section className="view-grid storm-view">
            <Metric label="High Priority Incidents" value={dashboard.high_priority_incidents} />
            <Metric label="Critical Facilities" value={criticalIncidents.length} />
            <Metric label="Crews Assigned" value={dashboard.assigned_crews} />
            <Metric label="Customers Out" value={dashboard.customers_out.toLocaleString()} />
            <ExpandableWorkspace
              className="full-width"
              expanded={expandedWorkspace === "storm"}
              icon={CloudLightning}
              id="storm-exceptions-workspace"
              onExpand={() => setExpandedWorkspace("storm")}
              onRestore={() => setExpandedWorkspace(null)}
              title="Storm Exceptions"
            >
              <IncidentTable
                emptyMessage="No storm exceptions are active in this scenario."
                incidents={criticalIncidents.length ? criticalIncidents : incidents.slice(0, 4)}
                layoutKey={expandedWorkspace === "storm" ? "expanded" : "embedded"}
                navigationContext={navigationContext}
                key={`storm-incidents-${activeScenario?.scenario_id ?? "loading"}`}
                selectedIncidentId={selectedIncidentId}
                tableLabel="Storm exceptions"
                restoredState={restoringNavigation?.sourceView === "storm" ? restoringNavigation.incidentState : undefined}
                onStateChange={(state) => { incidentWorkspaceStatesRef.current.storm = state; }}
                onSelect={setSelectedIncidentId}
                onNavigate={navigateOperationally}
              />
            </ExpandableWorkspace>
          </section>
        ))}

        {view === "scenario" && (
          <section className="split-layout">
            <section className="panel">
              <PanelTitle icon={Map} title="Active Demo Scenario" />
              {initialLoading ? (
                <ViewState compact title="Loading scenario metadata..." message="Validating the active scenario manifest." />
              ) : activeScenario ? (
                <>
                  <div className="scenario-heading">
                    <div>
                      <span className="scenario-type">{formatScenarioType(activeScenario.event_type)}</span>
                      <h3>{activeScenario.name}</h3>
                    </div>
                    <span className="validation-badge">Validated</span>
                  </div>
                  <p>{activeScenario.description}</p>
                  <div className="scenario-freshness-detail">
                    <ScenarioFreshnessLabel scenario={activeScenario} />
                    <span>
                      <strong>Freshness source:</strong>{" "}
                      {activeScenario.freshness
                        ? `${formatScenarioFreshnessSource(activeScenario.freshness.source)} · ${activeScenario.freshness.provenance}`
                        : "Unavailable"}
                    </span>
                  </div>
                  <h3>Expected conditions</h3>
                  <ul className="condition-list">
                    {activeScenario.expected_conditions.map((condition) => (
                      <li key={condition}>{condition}</li>
                    ))}
                  </ul>
                  <p className="scenario-note">
                    Selection affects every user connected to this POC backend and resets when the backend restarts.
                  </p>
                </>
              ) : (
                <EmptyState message="Scenario metadata is unavailable. Retry the backend connection." />
              )}
            </section>
            <RecommendationPanel
              actionLoading={actionLoading}
              actionFailed={actionFailed}
              actionMessage={actionMessage}
              navigationContext={navigationContext}
              onNavigate={navigateOperationally}
              onRecordAction={recordRecommendationAction}
              recentActions={recommendationActions}
              recommendation={recommendation}
              recommendationError={recommendationError}
              recommendationLoading={recommendationLoading || scenarioLoading || initialLoading}
              onRetryRecommendation={() => setRecommendationRequestVersion((version) => version + 1)}
              selectedIncident={selectedIncident}
            />
          </section>
        )}

        {view === "copilot" && (
          <section className="panel copilot">
            <PanelTitle icon={Bot} title="AI Copilot" />
            <div aria-label="Copilot context" className="copilot-context" role="status">
              <span><strong>Selected incident:</strong> {selectedIncident ? `${selectedIncident.incident_id} · ${selectedIncident.municipality}` : "None"}</span>
              <span><strong>Selected crew:</strong> {selectedCrewContext ? `${selectedCrewContext.crew_id} · ${selectedCrewContext.crew_name}` : "None"}</span>
            </div>
            <div className="prompt-row">
              {COPILOT_PROMPTS.map((prompt) => (
                <button key={prompt} onClick={() => usePrompt(prompt)} type="button">
                  {prompt}
                </button>
              ))}
            </div>
            <label className="sr-only" htmlFor="copilot-question">Copilot question</label>
            <textarea id="copilot-question" value={chatMessage} onChange={(event) => setChatMessage(event.target.value)} />
            <div className="copilot-actions">
              <button
                className="secondary-action"
                disabled={!chatMessage.trim()}
                onClick={() => setChatMessage("")}
                type="button"
              >
                Clear
              </button>
              <button className="primary-action" disabled={chatLoading} onClick={askCopilot} type="button">
                {chatLoading ? "Asking..." : "Ask Copilot"}
              </button>
            </div>
            <div aria-live="polite" className="chat-history">
              {chatTurns.length === 0 ? (
                <div className="copilot-answer">
                  For an exact complete-scenario calculation, name both the measure and population—for example,
                  total customers out across all active incidents or available crews in the active scenario.
                  Open-ended summaries use grounded AI over a bounded context disclosed with each response.
                </div>
              ) : (
                chatTurns.map((turn, index) => (
                  <article className="chat-turn" key={`${turn.question}-${index}`} role={turn.error ? "alert" : undefined}>
                    <header className="copilot-response-header">
                      <strong className="copilot-question">{turn.question}</strong>
                      {turn.metadata?.request_time && (
                        <time dateTime={turn.metadata.request_time.received_at}>
                          Request Received {formatUtcDateTime(turn.metadata.request_time.received_at)}
                        </time>
                      )}
                    </header>
                    {turn.error ? <p>{turn.answer}</p> : <CopilotMarkdown>{turn.answer}</CopilotMarkdown>}
                    {turn.metadata && (
                      <div className="copilot-metadata">
                        <span className={`copilot-mode copilot-mode-${turn.metadata.execution_mode}`}>
                          {turn.metadata.execution_mode === "local_query"
                            ? "Local scenario query"
                            : turn.metadata.execution_mode === "llm_grounded"
                              ? `Grounded AI${turn.metadata.model ? ` · ${turn.metadata.model}` : ""}`
                              : "Rule-based fallback"}
                        </span>
                        <span>Scenario: {turn.metadata.scenario_id}</span>
                        {turn.metadata.data_snapshot_at && <span>Snapshot: {turn.metadata.data_snapshot_at}</span>}
                        {turn.metadata.response_scope ? (
                          <p aria-label="Response scope" className="copilot-scope">
                            <strong>Response scope:</strong> {turn.metadata.response_scope}
                          </p>
                        ) : null}
                        {turn.metadata.warning && <p className="copilot-warning">{turn.metadata.warning}</p>}
                        {turn.metadata.evidence.length > 0 && (
                          <details>
                            <summary>Evidence ({turn.metadata.evidence.length})</summary>
                            <ul>
                              {turn.metadata.evidence.map((item) => (
                                <li key={`${item.source_type}-${item.record_id}`}>
                                  {item.label} <code>{item.record_id}</code>
                                </li>
                              ))}
                            </ul>
                          </details>
                        )}
                      </div>
                    )}
                  </article>
                ))
              )}
            </div>
            <p className="safety-note">Copilot responses are advisory and cannot execute dispatch actions.</p>
          </section>
        )}
        <SideSheet
          ariaLabel="Dispatch recommendations"
          id="recommendations-sheet"
          onClose={() => setRecommendationsOpen(false)}
          open={recommendationsOpen && (view === "dashboard" || view === "dispatch")}
          returnFocusRef={recommendationTriggerRef}
          title="Recommendations"
        >
          <RecommendationPanel
            actionLoading={actionLoading}
            actionFailed={actionFailed}
            actionMessage={actionMessage}
            navigationContext={navigationContext}
            onNavigate={navigateOperationally}
            onRecordAction={recordRecommendationAction}
            recentActions={recommendationActions}
            recommendation={recommendation}
            recommendationError={recommendationError}
            recommendationLoading={recommendationLoading || scenarioLoading || initialLoading}
            onRetryRecommendation={() => setRecommendationRequestVersion((version) => version + 1)}
            selectedIncident={selectedIncident}
          />
        </SideSheet>
        <SideSheet
          ariaLabel={incidentDetail ? `Incident details ${incidentDetail.incident_id}` : "Incident details"}
          id="incident-detail-sheet"
          onClose={() => setIncidentDetailOpen(false)}
          open={incidentDetailOpen && (view === "dashboard" || view === "dispatch" || view === "incidents") && Boolean(incidentDetail)}
          returnFocusRef={incidentDetailTriggerRef}
          title="Incident details"
        >
          {incidentDetail ? (
            <IncidentDetail
              incident={incidentDetail}
              navigationContext={navigationContext}
              onNavigate={navigateOperationally}
            />
          ) : null}
        </SideSheet>
      </main>
    </div>
  );
}

function Metric({ className, label, value }: { className?: string; label: string; value: string | number }) {
  return (
    <section className={`metric${className ? ` ${className}` : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </section>
  );
}

function PanelTitle({ action, icon: Icon, title }: { action?: ReactNode; icon: ElementType; title: string }) {
  return (
    <div className="panel-title">
      <Icon size={18} />
      <h2>{title}</h2>
      {action}
    </div>
  );
}

function ViewState({
  actionLabel,
  compact = false,
  message,
  onAction,
  title
}: {
  actionLabel?: string;
  compact?: boolean;
  message: string;
  onAction?: () => void;
  title: string;
}) {
  return (
    <section aria-live="polite" className={compact ? "view-state compact" : "panel view-state"}>
      <strong>{title}</strong>
      <p>{message}</p>
      {actionLabel && onAction ? <button onClick={onAction} type="button">{actionLabel}</button> : null}
    </section>
  );
}

function EmptyState({ message }: { message: string }) {
  return <p className="empty-state">{message}</p>;
}

function formatAction(action: RecommendationActionType) {
  const labels: Record<RecommendationActionType, string> = {
    accepted: "Accepted",
    modified: "Modified",
    deferred: "Deferred",
    overridden: "Overridden"
  };
  return labels[action];
}

function formatScenarioType(eventType: ScenarioDescriptor["event_type"]) {
  return eventType.replace(/_/g, " ");
}

function ScenarioFreshnessLabel({ scenario }: { scenario: ScenarioDescriptor | null }) {
  const freshness = scenario?.freshness;
  const provenance = freshness
    ? `${formatScenarioFreshnessSource(freshness.source)}: ${freshness.provenance}`
    : "No authoritative scenario freshness metadata is available.";
  return (
    <span className="scenario-freshness" title={provenance}>
      {formatScenarioFreshness(freshness?.updated_at)}
    </span>
  );
}

function formatScenarioFreshness(updatedAt?: string) {
  if (!updatedAt) return "Scenario Last Updated Unavailable";
  const formatted = formatUtcDateTime(updatedAt);
  return formatted ? `Scenario Last Updated ${formatted}` : "Scenario Last Updated Unavailable";
}

function formatUtcDateTime(value: string) {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return null;
  const parts = new Intl.DateTimeFormat("en-US", {
    day: "2-digit",
    hour: "2-digit",
    hourCycle: "h23",
    minute: "2-digit",
    month: "2-digit",
    timeZone: "UTC",
    year: "numeric"
  }).formatToParts(timestamp);
  const partValue = (type: Intl.DateTimeFormatPartTypes) => parts.find((part) => part.type === type)?.value ?? "";
  return `${partValue("month")}/${partValue("day")}/${partValue("year")} ${partValue("hour")}:${partValue("minute")} UTC`;
}

function formatScenarioFreshnessSource(source: NonNullable<ScenarioDescriptor["freshness"]>["source"]) {
  const labels = {
    scenario_generation: "Scenario generation",
    file_upload: "File upload",
    repository_publish: "Repository publish",
    scenario_update: "Scenario update"
  } as const;
  return labels[source];
}

function formatConfidence(confidence: string) {
  return confidence ? `${confidence.charAt(0).toUpperCase()}${confidence.slice(1).toLowerCase()}` : confidence;
}

function formatCrewStatus(status: string) {
  return status ? `${status.charAt(0).toUpperCase()}${status.slice(1).toLowerCase()}` : status;
}

function recommendationTradeoff(recommended: Crew, option: Crew) {
  const tradeoffs: string[] = [];
  const recommendedTravel = recommended.estimated_travel_minutes ?? recommended.travel_minutes_to_selected_incident;
  const optionTravel = option.estimated_travel_minutes ?? option.travel_minutes_to_selected_incident;
  const travelDifference = optionTravel - recommendedTravel;
  if (travelDifference > 0) tradeoffs.push(`${travelDifference} minutes slower travel`);
  if (travelDifference < 0) tradeoffs.push(`${Math.abs(travelDifference)} minutes faster travel`);
  if (recommended.suitability_score !== undefined && option.suitability_score !== undefined) {
    const scoreDifference = recommended.suitability_score - option.suitability_score;
    if (scoreDifference > 0) tradeoffs.push(`${scoreDifference} points lower suitability`);
    if (scoreDifference < 0) tradeoffs.push(`${Math.abs(scoreDifference)} points higher suitability`);
  }
  if (option.shift_remaining_hours < recommended.shift_remaining_hours) {
    tradeoffs.push(`${recommended.shift_remaining_hours - option.shift_remaining_hours} fewer shift hours remaining`);
  }
  if (option.capability_match === false) tradeoffs.push("capability does not match the requested work");
  if (!option.storm_ready && recommended.storm_ready) tradeoffs.push("not storm-ready");
  return tradeoffs.length ? tradeoffs.join("; ") : "Operationally comparable; ranking uses the configured scoring policy.";
}

function RecommendationComparison({
  onSelectCrew,
  recommendation,
  selectedCrewId
}: {
  onSelectCrew: (crewId: string) => void;
  recommendation: Recommendation;
  selectedCrewId?: string;
}) {
  if (!recommendation.recommended_crew || recommendation.alternatives.length === 0) return null;
  const recommended = recommendation.recommended_crew;
  const options = [recommended, ...recommendation.alternatives];
  return (
    <section aria-label="Recommendation comparison" className="recommendation-comparison">
      <div className="comparison-heading">
        <h3>Compare crew options</h3>
        <span>Advisory ranking</span>
      </div>
      <div className="comparison-options">
        {options.map((option, index) => {
          const travelMinutes = option.estimated_travel_minutes ?? option.travel_minutes_to_selected_incident;
          return (
            <article className={`comparison-card ${index === 0 ? "recommended" : ""} ${selectedCrewId === option.crew_id ? "selected-option" : ""}`} key={option.crew_id}>
              <div className="comparison-card-heading">
                <span>{index === 0 ? "Recommended" : `Alternative ${index}`}</span>
                {option.suitability_score !== undefined ? <strong>{option.suitability_score} score</strong> : null}
              </div>
              <h4>{option.crew_name} <span className="crew-id">({option.crew_id})</span></h4>
              <dl>
                <div><dt>Travel</dt><dd>{travelMinutes} min</dd></div>
                <div><dt>Capability</dt><dd>{option.capability_match === false ? "No match" : "Match"}</dd></div>
                <div><dt>Shift</dt><dd>{option.shift_remaining_hours} hr</dd></div>
                <div><dt>Storm-ready</dt><dd>{option.storm_ready ? "Yes" : "No"}</dd></div>
              </dl>
              <p><strong>Tradeoff:</strong> {index === 0 ? "Highest-ranked feasible option under the active policy." : recommendationTradeoff(recommended, option)}</p>
              <button
                aria-pressed={selectedCrewId === option.crew_id}
                className="comparison-select"
                onClick={() => onSelectCrew(option.crew_id)}
                type="button"
              >
                {selectedCrewId === option.crew_id ? "Selected for assignment" : index === 0 ? "Use recommended crew" : "Select this crew"}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function IncidentDetail({
  incident,
  navigationContext,
  onNavigate
}: {
  incident: Incident;
  navigationContext: NavigationResolverContext;
  onNavigate: (command: OperationalNavigationCommand, trigger?: HTMLElement) => void;
}) {
  const detailNavigationContext: NavigationResolverContext = {
    ...navigationContext,
    currentView: "incidents",
    currentEntity: { kind: "incident", id: incident.incident_id }
  };
  return (
    <div className="detail-panel incident-detail">
      <div className="detail-heading">
        <div>
          <span>Selected incident</span>
          <h3>{incident.incident_id} · {incident.municipality}</h3>
        </div>
        <span className={severityClass(incident.severity)}>{incident.severity}</span>
      </div>
      <dl className="detail-grid">
        <div><dt>Region</dt><dd>{incident.region}</dd></div>
        <div><dt>Municipality</dt><dd><EntityNavigationActions
          accessibleLabel={`${incident.municipality} destinations`}
          context={detailNavigationContext}
          destinationKinds={["related_records"]}
          labelOverrides={{ related_records: incident.municipality }}
          onNavigate={onNavigate}
          reference={{ kind: "municipality", name: incident.municipality }}
        /></dd></div>
        <div><dt>Feeder</dt><dd><EntityNavigationActions
          accessibleLabel={`${incident.feeder} destinations`}
          context={detailNavigationContext}
          destinationKinds={["related_records"]}
          labelOverrides={{ related_records: incident.feeder }}
          onNavigate={onNavigate}
          reference={{ kind: "feeder", id: incident.feeder }}
        /></dd></div>
        <div><dt>Customers out</dt><dd>{incident.customers_out.toLocaleString()}</dd></div>
        <div><dt>Status</dt><dd>{formatCrewStatus(incident.status)}</dd></div>
        <div><dt>Hazard</dt><dd>{incident.hazard}</dd></div>
        <div><dt>Critical facility</dt><dd>{incident.critical_facility ? "Yes" : "No"}</dd></div>
        {incident.critical_facility_level ? <div><dt>CF level</dt><dd>Level {incident.critical_facility_level}</dd></div> : null}
        {incident.ranking_status === "withheld" ? <div><dt>Ranking</dt><dd>Withheld — {incident.ranking_warning}</dd></div> : null}
        <div><dt>Incident age</dt><dd>{incident.age_minutes} min</dd></div>
        <div><dt>ETR</dt><dd>{incident.etr}</dd></div>
      </dl>
      {incident.matched_critical_facility_ids?.length ? (
        <div className="detail-section">
          <h4>Critical-facility references</h4>
          <div className="detail-link-list">
            {incident.matched_critical_facility_ids.map((facilityId) => (
              <EntityNavigationActions
                accessibleLabel={`${facilityId} destinations`}
                context={detailNavigationContext}
                destinationKinds={["related_records"]}
                key={facilityId}
                labelOverrides={{ related_records: facilityId }}
                onNavigate={onNavigate}
                reference={{ kind: "critical_facility", id: facilityId }}
              />
            ))}
          </div>
        </div>
      ) : null}
      <div className="detail-section">
        <h4>Assigned crews</h4>
        {incident.assigned_crews.length ? (
          <div className="detail-link-list">
            {incident.assigned_crews.map((crew) => (
              <EntityNavigationActions
                accessibleLabel={`${crew.crew_name} destinations`}
                context={detailNavigationContext}
                destinationKinds={["full_detail"]}
                key={crew.assignment_id}
                labelOverrides={{ full_detail: `${crew.crew_name} (${crew.crew_id})` }}
                onNavigate={onNavigate}
                reference={{ kind: "crew", id: crew.crew_id }}
              />
            ))}
          </div>
        ) : <p>No crews assigned.</p>}
      </div>
      <div className="detail-section">
        <h4>Current decision</h4>
        <p>{incident.current_decision ? formatAction(incident.current_decision.action) : "No decision recorded."}</p>
        {incident.current_decision?.reason ? <small>{incident.current_decision.reason}</small> : null}
      </div>
      <ContextualNavigationPanel
        context={detailNavigationContext}
        onNavigate={onNavigate}
        reference={{ kind: "incident", id: incident.incident_id }}
      />
    </div>
  );
}

function CrewDetail({
  crew,
  navigationContext,
  onClose,
  onNavigate
}: {
  crew: Crew;
  navigationContext: NavigationResolverContext;
  onClose: () => void;
  onNavigate: (command: OperationalNavigationCommand, trigger?: HTMLElement) => void;
}) {
  const detailNavigationContext: NavigationResolverContext = {
    ...navigationContext,
    currentView: "crews",
    currentEntity: { kind: "crew", id: crew.crew_id }
  };
  return (
    <aside aria-label={`Crew details ${crew.crew_id}`} className="detail-panel crew-detail">
      <div className="detail-heading">
        <div>
          <span>Selected crew</span>
          <h3>{crew.crew_name} <span className="crew-id">({crew.crew_id})</span></h3>
        </div>
        <button className="detail-close" onClick={onClose} type="button">Close details</button>
      </div>
      <dl className="detail-grid">
        <div><dt>Status</dt><dd>{formatCrewStatus(crew.status)}</dd></div>
        <div><dt>Capability</dt><dd>{crew.capability}</dd></div>
        <div><dt>Home region</dt><dd>{crew.home_region}</dd></div>
        <div><dt>Current location</dt><dd>{crew.current_location}</dd></div>
        <div><dt>Shift remaining</dt><dd>{crew.shift_remaining_hours} hr</dd></div>
        <div><dt>Storm-ready</dt><dd>{crew.storm_ready ? "Yes" : "No"}</dd></div>
        <div><dt>Travel to selected incident</dt><dd>{crew.travel_minutes_to_selected_incident} min</dd></div>
        <div><dt>Assigned incidents</dt><dd>{crew.assigned_incidents.length}</dd></div>
      </dl>
      <div className="detail-section">
        <h4>Incident assignments</h4>
        {crew.assigned_incidents.length ? (
          <div className="detail-link-list">
            {crew.assigned_incidents.map((assignment) => (
              <EntityNavigationActions
                accessibleLabel={`${assignment.incident_id} destinations`}
                context={detailNavigationContext}
                destinationKinds={["full_detail"]}
                key={assignment.assignment_id}
                labelOverrides={{ full_detail: `${assignment.incident_id}${assignment.municipality ? ` · ${assignment.municipality}` : ""}` }}
                onNavigate={onNavigate}
                reference={{ kind: "incident", id: assignment.incident_id }}
              />
            ))}
          </div>
        ) : <p>No active incident assignments.</p>}
      </div>
      <ContextualNavigationPanel
        context={detailNavigationContext}
        onNavigate={onNavigate}
        reference={{ kind: "crew", id: crew.crew_id }}
      />
    </aside>
  );
}

function CrewBoard({
  crews,
  layoutKey,
  navigationContext,
  navigationFilterRequest,
  onCloseDetails,
  onNavigate,
  onSelectCrew,
  selectedCrew,
  selectedCrewId,
  restoredState,
  onStateChange
}: {
  crews: Crew[];
  layoutKey?: string;
  navigationContext: NavigationResolverContext;
  navigationFilterRequest?: { requestId: number; filter: CrewNavigationFilter } | null;
  onCloseDetails: () => void;
  onNavigate: (command: OperationalNavigationCommand, trigger?: HTMLElement) => void;
  onSelectCrew: (crewId: string) => void;
  selectedCrew?: Crew;
  selectedCrewId?: string;
  restoredState?: CrewWorkspaceState;
  onStateChange?: (state: CrewWorkspaceState) => void;
}) {
  const [query, setQuery] = useState(restoredState?.query ?? "");
  const [status, setStatus] = useState(restoredState?.status ?? "all");
  const [capability, setCapability] = useState(restoredState?.capability ?? "all");
  const [region, setRegion] = useState(restoredState?.region ?? "all");
  const [stormReady, setStormReady] = useState(restoredState?.stormReady ?? "all");
  const [relatedFilter, setRelatedFilter] = useState<CrewNavigationFilter | null>(restoredState?.relatedFilter ?? null);
  const [sort, setSort] = useState<{ key: CrewSortKey; direction: SortDirection }>(restoredState?.sort ?? { key: "name", direction: "asc" });
  const [page, setPage] = useState(restoredState?.page ?? 0);
  const previousPageSizeRef = useRef(24);
  const handledNavigationRequestRef = useRef<number | null>(null);
  const skipInitialFilterReset = useRef(Boolean(restoredState));
  const handledRestoredStateRef = useRef(restoredState);
  const boardNavigationContext: NavigationResolverContext = {
    ...navigationContext,
    currentView: "crews"
  };

  useEffect(() => {
    if (!navigationFilterRequest || handledNavigationRequestRef.current === navigationFilterRequest.requestId) return;
    handledNavigationRequestRef.current = navigationFilterRequest.requestId;
    setRelatedFilter(navigationFilterRequest.filter);
    setQuery("");
    setStatus("all");
    setCapability("all");
    setRegion("all");
    setStormReady("all");
    setPage(0);
  }, [navigationFilterRequest]);

  useEffect(() => {
    if (!restoredState || handledRestoredStateRef.current === restoredState) return;
    handledRestoredStateRef.current = restoredState;
    skipInitialFilterReset.current = true;
    setQuery(restoredState.query);
    setStatus(restoredState.status);
    setCapability(restoredState.capability);
    setRegion(restoredState.region);
    setStormReady(restoredState.stormReady);
    setRelatedFilter(restoredState.relatedFilter);
    setSort(restoredState.sort);
    setPage(restoredState.page);
  }, [restoredState]);

  const statuses = useMemo(
    () => Array.from(new Set([...crews.map((crew) => crew.status), ...(status !== "all" ? [status] : [])])).sort(),
    [crews, status]
  );
  const capabilities = useMemo(
    () => Array.from(new Set([...crews.map((crew) => crew.capability), ...(capability !== "all" ? [capability] : [])])).sort(),
    [capability, crews]
  );
  const regions = useMemo(
    () => Array.from(new Set([...crews.map((crew) => crew.home_region), ...(region !== "all" ? [region] : [])])).sort(),
    [crews, region]
  );
  const { filteredCrews, facetCounts, suggestionCrews } = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const matchesFacets = (crew: Crew, excludedFacet?: "status" | "capability" | "region" | "stormReady") => (
      (excludedFacet === "status" || status === "all" || crew.status === status) &&
      (excludedFacet === "capability" || capability === "all" || crew.capability === capability) &&
      (excludedFacet === "region" || region === "all" || crew.home_region === region) &&
      (excludedFacet === "stormReady" || stormReady === "all" || (stormReady === "ready" ? crew.storm_ready : !crew.storm_ready))
    );
    const matches = (crew: Crew, excludedFacet?: "status" | "capability" | "region" | "stormReady") => {
      const searchable = [
        crew.crew_id,
        crew.crew_name,
        crew.capability,
        crew.home_region,
        crew.current_location,
        ...crew.assigned_incidents.map((assignment) => assignment.incident_id)
      ].join(" ").toLowerCase();
      return (
        (!normalizedQuery || searchable.includes(normalizedQuery)) &&
        (!relatedFilter || relatedFilter.ids.includes(crew.crew_id)) &&
        matchesFacets(crew, excludedFacet)
      );
    };
    const matching = crews.filter((crew) => matches(crew));
    const statusEligible = crews.filter((crew) => matches(crew, "status"));
    const capabilityEligible = crews.filter((crew) => matches(crew, "capability"));
    const regionEligible = crews.filter((crew) => matches(crew, "region"));
    const stormReadyEligible = crews.filter((crew) => matches(crew, "stormReady"));
    const sorted = matching.sort((left, right) => {
      const direction = sort.direction === "asc" ? 1 : -1;
      let comparison = 0;
      if (sort.key === "name") comparison = left.crew_name.localeCompare(right.crew_name);
      if (sort.key === "status") comparison = left.status.localeCompare(right.status) || left.crew_name.localeCompare(right.crew_name);
      if (sort.key === "capability") comparison = left.capability.localeCompare(right.capability) || left.crew_name.localeCompare(right.crew_name);
      if (sort.key === "shift") comparison = left.shift_remaining_hours - right.shift_remaining_hours;
      if (sort.key === "assigned") comparison = left.assigned_incidents.length - right.assigned_incidents.length;
      if (sort.key === "travel") comparison = left.travel_minutes_to_selected_incident - right.travel_minutes_to_selected_incident;
      return comparison * direction || left.crew_id.localeCompare(right.crew_id);
    });
    return {
      filteredCrews: sorted,
      suggestionCrews: crews.filter((crew) => matchesFacets(crew)),
      facetCounts: {
        status: facetCountsFor(statusEligible, (crew) => crew.status),
        capability: facetCountsFor(capabilityEligible, (crew) => crew.capability),
        region: facetCountsFor(regionEligible, (crew) => crew.home_region),
        stormReady: facetCountsFor(stormReadyEligible, (crew) => crew.storm_ready ? "ready" : "not-ready")
      }
    };
  }, [capability, crews, query, region, relatedFilter, sort, status, stormReady]);
  const autocompleteSuggestions = useMemo(
    () => buildAutocompleteSuggestions(suggestionCrews, crewAutocompleteFields, query),
    [query, suggestionCrews]
  );
  const { containerRef, pageSize } = useFittedPageSize({
    bottomPadding: layoutKey === "expanded" ? 0 : 24,
    fallbackPageSize: 24,
    itemCount: filteredCrews.length,
    itemSelector: ".crew-card",
    layout: "grid",
    measurementKey: `${capability}|${layoutKey ?? "embedded"}|${page}|${query}|${region}|${relatedFilter?.label ?? "all-related"}|${sort.key}|${sort.direction}|${status}|${stormReady}`
  });
  const pageCount = Math.max(1, Math.ceil(filteredCrews.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const visibleCrews = filteredCrews.slice(currentPage * pageSize, (currentPage + 1) * pageSize);

  useEffect(() => {
    if (skipInitialFilterReset.current) {
      skipInitialFilterReset.current = false;
      return;
    }
    setPage(0);
  }, [capability, query, region, relatedFilter, sort, status, stormReady, crews.length]);

  useEffect(() => {
    setPage((current) => Math.min(current, pageCount - 1));
  }, [pageCount]);

  useEffect(() => {
    const previousPageSize = previousPageSizeRef.current;
    previousPageSizeRef.current = pageSize;
    if (previousPageSize === pageSize) return;
    setPage((current) => Math.floor((current * previousPageSize) / pageSize));
  }, [pageSize]);

  useEffect(() => {
    onStateChange?.({ query, status, capability, region, stormReady, relatedFilter, sort, page: currentPage });
  }, [capability, currentPage, onStateChange, query, region, relatedFilter, sort, status, stormReady]);

  const toggleSortDirection = () => {
    setSort((current) => ({ ...current, direction: current.direction === "asc" ? "desc" : "asc" }));
  };

  return (
    <div className="crew-board" ref={containerRef}>
      <div className="crew-board-controls" aria-label="Crew Board filters" role="group">
        <AutocompleteSearch
          accessibleLabel="Crew Board search"
          label="Search"
          onChange={(value) => {
            setQuery(value);
            setPage(0);
          }}
          placeholder="Crew, capability, region, or incident"
          suggestions={autocompleteSuggestions}
          value={query}
        />
        <label>
          Status
          <select aria-label="Crew Board status" onChange={(event) => setStatus(event.target.value)} value={status}>
            <option value="all">All statuses ({facetCounts.status.all})</option>
            {statuses.map((item) => <option disabled={(facetCounts.status[item] ?? 0) === 0 && status !== item} key={item} value={item}>{formatCrewStatus(item)} ({facetCounts.status[item] ?? 0})</option>)}
          </select>
        </label>
        <label>
          Capability
          <select aria-label="Crew Board capability" onChange={(event) => setCapability(event.target.value)} value={capability}>
            <option value="all">All capabilities ({facetCounts.capability.all})</option>
            {capabilities.map((item) => <option disabled={(facetCounts.capability[item] ?? 0) === 0 && capability !== item} key={item} value={item}>{item} ({facetCounts.capability[item] ?? 0})</option>)}
          </select>
        </label>
        <label>
          Region
          <select aria-label="Crew Board region" onChange={(event) => setRegion(event.target.value)} value={region}>
            <option value="all">All regions ({facetCounts.region.all})</option>
            {regions.map((item) => <option disabled={(facetCounts.region[item] ?? 0) === 0 && region !== item} key={item} value={item}>{item} ({facetCounts.region[item] ?? 0})</option>)}
          </select>
        </label>
        <label>
          Storm-ready
          <select aria-label="Crew Board storm readiness" onChange={(event) => setStormReady(event.target.value)} value={stormReady}>
            <option value="all">All crews ({facetCounts.stormReady.all})</option>
            <option disabled={(facetCounts.stormReady.ready ?? 0) === 0 && stormReady !== "ready"} value="ready">Storm-ready ({facetCounts.stormReady.ready ?? 0})</option>
            <option disabled={(facetCounts.stormReady["not-ready"] ?? 0) === 0 && stormReady !== "not-ready"} value="not-ready">Not storm-ready ({facetCounts.stormReady["not-ready"] ?? 0})</option>
          </select>
        </label>
        <label>
          Sort by
          <span className="crew-sort-control">
            <select aria-label="Crew Board sort" onChange={(event) => setSort({ key: event.target.value as CrewSortKey, direction: "asc" })} value={sort.key}>
              <option value="name">Crew name</option>
              <option value="status">Status</option>
              <option value="capability">Capability</option>
              <option value="shift">Shift hours remaining</option>
              <option value="assigned">Assigned incident count</option>
              <option value="travel">Travel time</option>
            </select>
            <button aria-label={`Crew Board sort ${sort.direction === "asc" ? "ascending" : "descending"}; click to reverse`} onClick={toggleSortDirection} type="button">{sort.direction === "asc" ? "↑" : "↓"}</button>
          </span>
        </label>
      </div>
      <div className="crew-board-summary" aria-live="polite">
        <span>Showing {visibleCrews.length ? currentPage * pageSize + 1 : 0}–{Math.min((currentPage + 1) * pageSize, filteredCrews.length)} of {filteredCrews.length} matching crews ({crews.length} total)</span>
        {pageCount > 1 ? (
          <div aria-label="Crew Board pagination" className="incident-pagination" role="navigation">
            <button aria-label="Previous Crew Board page" disabled={currentPage === 0} onClick={() => setPage((current) => Math.max(0, current - 1))} type="button">Previous</button>
            <span>Page {currentPage + 1} of {pageCount}</span>
            <button aria-label="Next Crew Board page" disabled={currentPage >= pageCount - 1} onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))} type="button">Next</button>
          </div>
        ) : null}
      </div>
      {relatedFilter ? (
        <div className="navigation-filter-banner" role="status">
          <span>Related records · {relatedFilter.label}</span>
          <button onClick={() => setRelatedFilter(null)} type="button">Clear related filter</button>
        </div>
      ) : null}
      {visibleCrews.length === 0 ? <EmptyState message="No crews match the current filters." /> : (
        <div className="crew-grid">
          {visibleCrews.map((crew) => (
            <article className={`crew-card ${selectedCrewId === crew.crew_id ? "selected-card" : ""}`} key={crew.crew_id}>
              <div className="crew-card-primary">
                <button
                  aria-pressed={selectedCrewId === crew.crew_id}
                  className="crew-card-select"
                  onClick={() => onSelectCrew(crew.crew_id)}
                  type="button"
                >
                  <span className="crew-card-name">
                    <strong>{crew.crew_name} <span className="crew-id">({crew.crew_id})</span></strong>
                    <span>{crew.capability}</span>
                  </span>
                  <span className={`crew-status ${crew.status}`}>{formatCrewStatus(crew.status)}</span>
                  <span className="crew-location">{crew.current_location}</span>
                  <small>{crew.shift_remaining_hours} shift hours remaining</small>
                </button>
                <ShowOnMapButton entityId={crew.crew_id} entityKind="crew" navigationContext={boardNavigationContext} onNavigate={onNavigate} />
              </div>
              {crew.assigned_incidents.length ? (
                <div className="assignment-list">
                  {crew.assigned_incidents.map((assignment) => (
                    <div className="assignment-navigation" key={assignment.assignment_id}>
                      <span>Assigned to</span>
                      <EntityNavigationActions
                        accessibleLabel={`${assignment.incident_id} destinations`}
                        context={boardNavigationContext}
                        destinationKinds={["full_detail"]}
                        labelOverrides={{ full_detail: `${assignment.incident_id}${assignment.municipality ? ` in ${assignment.municipality}` : ""}` }}
                        onNavigate={onNavigate}
                        reference={{ kind: "incident", id: assignment.incident_id }}
                      />
                    </div>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      )}
      {selectedCrew ? (
        <CrewDetail
          crew={selectedCrew}
          navigationContext={navigationContext}
          onClose={onCloseDetails}
          onNavigate={onNavigate}
        />
      ) : null}
    </div>
  );
}

function IncidentTable({
  emptyMessage,
  incidents,
  layoutKey,
  navigationContext,
  navigationFilterRequest,
  preserveOrder = false,
  searchLabel,
  selectedIncidentId,
  syncSelectionToFirst = false,
  tableLabel,
  onActivate,
  onSelect,
  onNavigate,
  restoredState,
  onStateChange
}: {
  emptyMessage: string;
  incidents: Incident[];
  layoutKey?: string;
  navigationContext: NavigationResolverContext;
  navigationFilterRequest?: { requestId: number; filter: IncidentNavigationFilter } | null;
  preserveOrder?: boolean;
  searchLabel?: string;
  selectedIncidentId?: string;
  syncSelectionToFirst?: boolean;
  tableLabel: string;
  onActivate?: (incidentId: string, trigger?: HTMLElement) => void;
  onSelect: (incidentId: string, trigger?: HTMLElement) => void;
  onNavigate: (command: OperationalNavigationCommand, trigger?: HTMLElement) => void;
  restoredState?: IncidentWorkspaceState;
  onStateChange?: (state: IncidentWorkspaceState) => void;
}) {
  const [query, setQuery] = useState(restoredState?.query ?? "");
  const [severity, setSeverity] = useState(restoredState?.severity ?? "all");
  const [region, setRegion] = useState(restoredState?.region ?? "all");
  const [criticalFacility, setCriticalFacility] = useState(restoredState?.criticalFacility ?? "all");
  const [relatedFilter, setRelatedFilter] = useState<IncidentNavigationFilter | null>(restoredState?.relatedFilter ?? null);
  const [sort, setSort] = useState<{ key: IncidentSortKey; direction: SortDirection } | null>(restoredState?.sort ?? null);
  const [page, setPage] = useState(restoredState?.page ?? 0);
  const previousPageSizeRef = useRef(50);
  const lastSyncedFirstIncidentRef = useRef<string | undefined>(undefined);
  const handledNavigationRequestRef = useRef<number | null>(null);
  const skipInitialFilterReset = useRef(Boolean(restoredState));
  const handledRestoredStateRef = useRef(restoredState);
  const suppressSelectionSyncRef = useRef(Boolean(restoredState));
  const tableNavigationContext: NavigationResolverContext = {
    ...navigationContext,
    currentView: "incidents"
  };

  useEffect(() => {
    if (!navigationFilterRequest || handledNavigationRequestRef.current === navigationFilterRequest.requestId) return;
    handledNavigationRequestRef.current = navigationFilterRequest.requestId;
    setRelatedFilter(navigationFilterRequest.filter);
    setQuery("");
    setSeverity("all");
    setRegion("all");
    setCriticalFacility("all");
    setPage(0);
  }, [navigationFilterRequest]);

  useEffect(() => {
    if (!restoredState || handledRestoredStateRef.current === restoredState) return;
    handledRestoredStateRef.current = restoredState;
    skipInitialFilterReset.current = true;
    suppressSelectionSyncRef.current = true;
    setQuery(restoredState.query);
    setSeverity(restoredState.severity);
    setRegion(restoredState.region);
    setCriticalFacility(restoredState.criticalFacility);
    setRelatedFilter(restoredState.relatedFilter);
    setSort(restoredState.sort);
    setPage(restoredState.page);
  }, [restoredState]);

  const regions = useMemo(
    () => Array.from(new Set([...incidents.map((incident) => incident.region), ...(region !== "all" ? [region] : [])])).sort(),
    [incidents, region]
  );
  const severities = useMemo(
    () => {
      const severityRank: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
      return Array.from(new Set([
        ...incidents.map((incident) => incident.severity.toLowerCase()),
        ...(severity !== "all" ? [severity] : [])
      ])).sort((left, right) => (severityRank[right] ?? 0) - (severityRank[left] ?? 0) || left.localeCompare(right));
    },
    [incidents, severity]
  );
  const { filteredIncidents, facetCounts, suggestionIncidents } = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const matchesFacets = (incident: Incident, excludedFacet?: "severity" | "region" | "criticalFacility") => (
      (excludedFacet === "severity" || severity === "all" || incident.severity.toLowerCase() === severity) &&
      (excludedFacet === "region" || region === "all" || incident.region === region) &&
      (excludedFacet === "criticalFacility" || criticalFacility === "all" || (criticalFacility === "yes" ? incident.critical_facility : !incident.critical_facility))
    );
    const matches = (incident: Incident, excludedFacet?: "severity" | "region" | "criticalFacility") => {
      const searchable = [incident.incident_id, incident.municipality, incident.feeder, incident.hazard]
        .join(" ")
        .toLowerCase();
      return (
        (!normalizedQuery || searchable.includes(normalizedQuery)) &&
        (!relatedFilter || (
          (relatedFilter.kind === "incident_ids" && relatedFilter.ids.includes(incident.incident_id)) ||
          (relatedFilter.kind === "municipality" && incident.municipality === relatedFilter.value) ||
          (relatedFilter.kind === "feeder" && incident.feeder === relatedFilter.value) ||
          (relatedFilter.kind === "critical_facility" && incident.matched_critical_facility_ids?.includes(relatedFilter.value))
        )) &&
        matchesFacets(incident, excludedFacet)
      );
    };
    const matching = incidents.filter((incident) => matches(incident));
    const severityEligible = incidents.filter((incident) => matches(incident, "severity"));
    const regionEligible = incidents.filter((incident) => matches(incident, "region"));
    const criticalFacilityEligible = incidents.filter((incident) => matches(incident, "criticalFacility"));
    const severityRank: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
    const sorted = matching.sort((left, right) => {
      const rankingComparison = Number(left.ranking_status === "withheld") - Number(right.ranking_status === "withheld");
      if (rankingComparison) return rankingComparison;
      if (sort) {
        const direction = sort.direction === "asc" ? 1 : -1;
        let comparison = 0;
        if (sort.key === "customers") comparison = left.customers_out - right.customers_out;
        if (sort.key === "severity") comparison = (severityRank[left.severity.toLowerCase()] ?? 0) - (severityRank[right.severity.toLowerCase()] ?? 0);
        if (sort.key === "criticalFacility") comparison = Number(left.critical_facility) - Number(right.critical_facility);
        if (sort.key === "region") comparison = left.region.localeCompare(right.region);
        if (sort.key === "id") comparison = left.incident_id.localeCompare(right.incident_id);
        if (sort.key === "hazard") comparison = left.hazard.localeCompare(right.hazard);
        if (sort.key === "assigned") {
          comparison = left.assigned_crews.length - right.assigned_crews.length ||
            (left.assigned_crews[0]?.crew_name ?? "").localeCompare(right.assigned_crews[0]?.crew_name ?? "");
        }
        if (sort.key === "decision") comparison = (left.current_decision?.action ?? "").localeCompare(right.current_decision?.action ?? "");
        if (sort.key === "etr") comparison = left.etr.localeCompare(right.etr, undefined, { numeric: true });
        return comparison * direction || left.incident_id.localeCompare(right.incident_id);
      }
      if (preserveOrder) return 0;
      return (
        (severityRank[right.severity.toLowerCase()] ?? 0) - (severityRank[left.severity.toLowerCase()] ?? 0) ||
        right.customers_out - left.customers_out ||
        left.incident_id.localeCompare(right.incident_id)
      );
    });
    return {
      filteredIncidents: sorted,
      suggestionIncidents: incidents.filter((incident) => matchesFacets(incident)),
      facetCounts: {
        severity: facetCountsFor(severityEligible, (incident) => incident.severity.toLowerCase()),
        region: facetCountsFor(regionEligible, (incident) => incident.region),
        criticalFacility: facetCountsFor(criticalFacilityEligible, (incident) => incident.critical_facility ? "yes" : "no")
      }
    };
  }, [criticalFacility, incidents, preserveOrder, query, region, relatedFilter, severity, sort]);
  const autocompleteSuggestions = useMemo(
    () => buildAutocompleteSuggestions(suggestionIncidents, incidentAutocompleteFields, query),
    [query, suggestionIncidents]
  );

  useEffect(() => {
    const firstVisibleIncident = filteredIncidents.find(
      (incident) => incident.ranking_status !== "withheld"
    );
    if (suppressSelectionSyncRef.current) {
      suppressSelectionSyncRef.current = false;
      lastSyncedFirstIncidentRef.current = firstVisibleIncident?.incident_id;
      return;
    }
    if (syncSelectionToFirst && firstVisibleIncident && lastSyncedFirstIncidentRef.current !== firstVisibleIncident.incident_id) {
      lastSyncedFirstIncidentRef.current = firstVisibleIncident.incident_id;
      onSelect(firstVisibleIncident.incident_id);
    }
  }, [filteredIncidents, onSelect, syncSelectionToFirst]);

  const { containerRef, pageSize } = useFittedPageSize({
    bottomPadding: layoutKey === "expanded" ? 0 : 24,
    fallbackPageSize: 50,
    itemCount: filteredIncidents.length,
    itemSelector: "tbody tr",
    layout: "rows",
    measurementKey: `${layoutKey ?? "embedded"}|${page}|${query}|${region}|${relatedFilter?.label ?? "all-related"}|${severity}|${sort?.key ?? "default"}|${sort?.direction ?? "default"}`
  });
  const pageCount = Math.max(1, Math.ceil(filteredIncidents.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const visibleIncidents = filteredIncidents.slice(currentPage * pageSize, (currentPage + 1) * pageSize);

  useEffect(() => {
    if (skipInitialFilterReset.current) {
      skipInitialFilterReset.current = false;
      return;
    }
    setPage(0);
  }, [criticalFacility, query, region, relatedFilter, severity, sort, incidents.length]);

  useEffect(() => {
    setPage((current) => Math.min(current, pageCount - 1));
  }, [pageCount]);

  useEffect(() => {
    const previousPageSize = previousPageSizeRef.current;
    previousPageSizeRef.current = pageSize;
    if (previousPageSize === pageSize) return;
    setPage((current) => Math.floor((current * previousPageSize) / pageSize));
  }, [pageSize]);

  useEffect(() => {
    onStateChange?.({ query, severity, region, criticalFacility, relatedFilter, sort, page: currentPage });
  }, [criticalFacility, currentPage, onStateChange, query, region, relatedFilter, severity, sort]);

  const toggleSort = (key: IncidentSortKey) => {
    setSort((current) => current?.key === key
      ? { key, direction: current.direction === "asc" ? "desc" : "asc" }
      : { key, direction: "asc" });
  };

  const sortIndicator = (key: IncidentSortKey) => sort?.key === key ? (sort.direction === "asc" ? "↑" : "↓") : "↕";
  const sortLabel = (key: IncidentSortKey, label: string) => sort?.key === key
    ? `Sort by ${label} ${sort.direction === "asc" ? "descending next" : "ascending next"}`
    : `Sort by ${label} ascending`;
  const activateIncident = onActivate ?? onSelect;

  if (incidents.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <div className="incident-table" ref={containerRef}>
      <div className="incident-table-controls" aria-label={`${tableLabel} filters`} role="group">
        <AutocompleteSearch
          accessibleLabel={searchLabel ?? `${tableLabel} search`}
          label={searchLabel ?? "Search"}
          onChange={(value) => {
            setQuery(value);
            setPage(0);
          }}
          placeholder="ID, municipality, feeder, or hazard"
          suggestions={autocompleteSuggestions}
          value={query}
        />
        <label>
          Severity
          <select aria-label={`${tableLabel} severity`} onChange={(event) => setSeverity(event.target.value)} value={severity}>
            <option value="all">All severities ({facetCounts.severity.all})</option>
            {severities.map((item) => <option disabled={(facetCounts.severity[item] ?? 0) === 0 && severity !== item} key={`severity-${item}`} value={item}>{formatCrewStatus(item)} ({facetCounts.severity[item] ?? 0})</option>)}
          </select>
        </label>
        <label>
          Region
          <select aria-label={`${tableLabel} region`} onChange={(event) => setRegion(event.target.value)} value={region}>
            <option value="all">All regions ({facetCounts.region.all})</option>
            {regions.map((item) => <option disabled={(facetCounts.region[item] ?? 0) === 0 && region !== item} key={`region-${item}`} value={item}>{item} ({facetCounts.region[item] ?? 0})</option>)}
          </select>
        </label>
        <label>
          Critical Facility
          <select aria-label={`${tableLabel} critical facility`} onChange={(event) => setCriticalFacility(event.target.value)} value={criticalFacility}>
            <option value="all">All facilities ({facetCounts.criticalFacility.all})</option>
            <option disabled={(facetCounts.criticalFacility.yes ?? 0) === 0 && criticalFacility !== "yes"} value="yes">Critical facility ({facetCounts.criticalFacility.yes ?? 0})</option>
            <option disabled={(facetCounts.criticalFacility.no ?? 0) === 0 && criticalFacility !== "no"} value="no">No critical facility ({facetCounts.criticalFacility.no ?? 0})</option>
          </select>
        </label>
      </div>
      <div aria-label={`${tableLabel} compact sorting`} className="compact-sort-controls" role="group">
        <label>
          Sort by
          <select
            aria-label={`${tableLabel} compact sort`}
            onChange={(event) => setSort(event.target.value === "default" ? null : { key: event.target.value as IncidentSortKey, direction: "asc" })}
            value={sort?.key ?? "default"}
          >
            <option value="default">Default priority</option>
            {incidentSortOptions.map(([key, label]) => <option key={`compact-${key}`} value={key}>{label}</option>)}
          </select>
        </label>
        <button
          aria-label={`${tableLabel} compact sort ${sort?.direction === "desc" ? "descending" : "ascending"}; click to reverse`}
          disabled={!sort}
          onClick={() => setSort((current) => current ? { ...current, direction: current.direction === "asc" ? "desc" : "asc" } : current)}
          type="button"
        >
          {sort?.direction === "desc" ? "↓" : "↑"}
        </button>
      </div>
      <div className="incident-table-summary" aria-live="polite">
        <span>Showing {visibleIncidents.length ? currentPage * pageSize + 1 : 0}–{Math.min((currentPage + 1) * pageSize, filteredIncidents.length)} of {filteredIncidents.length} matching incidents ({incidents.length} total)</span>
        {pageCount > 1 ? (
          <div aria-label={`${tableLabel} pagination`} className="incident-pagination" role="navigation">
            <button aria-label={`Previous ${tableLabel} page`} disabled={currentPage === 0} onClick={() => setPage((current) => Math.max(0, current - 1))} type="button">Previous</button>
            <span>Page {currentPage + 1} of {pageCount}</span>
            <button aria-label={`Next ${tableLabel} page`} disabled={currentPage >= pageCount - 1} onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))} type="button">Next</button>
          </div>
        ) : null}
      </div>
      {relatedFilter ? (
        <div className="navigation-filter-banner" role="status">
          <span>Related records · {relatedFilter.label}</span>
          <button onClick={() => setRelatedFilter(null)} type="button">Clear related filter</button>
        </div>
      ) : null}
      {visibleIncidents.length === 0 ? (
        <EmptyState message="No incidents match the current filters." />
      ) : (
        <ResponsiveTable label={tableLabel}>
          <table className="incident-data-table">
        <thead>
          <tr>
            {incidentSortOptions.map(([key, label]) => (
              <th aria-sort={sort?.key === key ? (sort.direction === "asc" ? "ascending" : "descending") : "none"} key={key}>
                <button aria-label={`${tableLabel} ${sortLabel(key, label)}`} className="table-sort-button" onClick={() => toggleSort(key)} type="button">
                  {label}<span aria-hidden="true">{sortIndicator(key)}</span>
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visibleIncidents.map((incident) => (
            <tr
              aria-label={`Open incident details for ${incident.incident_id}`}
              aria-selected={selectedIncidentId === incident.incident_id}
              className={selectedIncidentId === incident.incident_id ? "selected-row" : ""}
              key={incident.incident_id}
              onClick={(event) => activateIncident(
                incident.incident_id,
                event.currentTarget.querySelector<HTMLButtonElement>(".incident-select-button") ?? undefined
              )}
              onKeyDown={(event) => {
                if (event.target !== event.currentTarget || (event.key !== "Enter" && event.key !== " ")) return;
                event.preventDefault();
                activateIncident(incident.incident_id, event.currentTarget);
              }}
              tabIndex={0}
            >
              <td className="incident-identity-cell">
                <span className="compact-cell-label">Incident</span>
                <span className="incident-map-link">
                  <button
                    aria-pressed={selectedIncidentId === incident.incident_id}
                    className="incident-select-button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onSelect(incident.incident_id, event.currentTarget);
                    }}
                    type="button"
                  >
                    {incident.incident_id}
                  </button>
                  <ShowOnMapButton entityId={incident.incident_id} entityKind="incident" navigationContext={tableNavigationContext} onNavigate={onNavigate} />
                </span>
                <span
                  aria-label={`Municipality and feeder for ${incident.incident_id}`}
                  className="incident-location incident-related-location"
                  role="group"
                >
                  <EntityNavigationActions
                    accessibleLabel={`${incident.municipality} destinations`}
                    context={tableNavigationContext}
                    destinationKinds={["related_records"]}
                    labelOverrides={{ related_records: incident.municipality }}
                    onNavigate={onNavigate}
                    reference={{ kind: "municipality", name: incident.municipality }}
                  />
                  <span aria-hidden="true">/</span>
                  <EntityNavigationActions
                    accessibleLabel={`${incident.feeder} destinations`}
                    context={tableNavigationContext}
                    destinationKinds={["related_records"]}
                    labelOverrides={{ related_records: incident.feeder }}
                    onNavigate={onNavigate}
                    reference={{ kind: "feeder", id: incident.feeder }}
                    showIcon={false}
                  />
                </span>
              </td>
              <td><span className="compact-cell-label">Region</span>{incident.region}</td>
              <td><span className="compact-cell-label">Customers</span>{incident.customers_out.toLocaleString()}</td>
              <td><span className="compact-cell-label">Severity</span><span className={severityClass(incident.severity)}>{incident.severity}</span></td>
              <td>
                <span className="compact-cell-label">Critical Facility</span>
                <span className={incident.critical_facility ? "critical-facility-badge is-critical" : "critical-facility-badge"}>
                  {incident.critical_facility ? "Yes" : "No"}
                </span>
              </td>
              <td><span className="compact-cell-label">Hazard</span>{incident.hazard}</td>
              <td>
                <span className="compact-cell-label">Assigned Crews</span>
                {incident.assigned_crews.length ? (
                  incident.assigned_crews.map((crew) => (
                    <EntityNavigationActions
                      accessibleLabel={`${crew.crew_name} destinations`}
                      context={tableNavigationContext}
                      destinationKinds={["full_detail"]}
                      key={crew.assignment_id}
                      labelOverrides={{ full_detail: crew.crew_name }}
                      onNavigate={onNavigate}
                      reference={{ kind: "crew", id: crew.crew_id }}
                    />
                  ))
                ) : (
                  <span>Unassigned</span>
                )}
              </td>
              <td>
                <span className="compact-cell-label">Decision</span>
                {incident.current_decision ? (
                  <span className={`decision-badge decision-${incident.current_decision.action}`}>
                    {formatAction(incident.current_decision.action)}
                  </span>
                ) : (
                  <span>No decision</span>
                )}
              </td>
              <td><span className="compact-cell-label">ETR</span>{incident.etr}</td>
            </tr>
          ))}
        </tbody>
          </table>
        </ResponsiveTable>
      )}
    </div>
  );
}

function ResponsiveTable({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div aria-label={label} className="table-shell" role="region" tabIndex={0}>
      {children}
    </div>
  );
}

function RecommendationPanel({
  actionFailed,
  actionLoading,
  actionMessage,
  navigationContext,
  onNavigate,
  onRecordAction,
  onRetryRecommendation,
  recentActions,
  recommendation,
  recommendationError,
  recommendationLoading,
  selectedIncident
}: {
  actionFailed: boolean;
  actionLoading: RecommendationActionType | null;
  actionMessage: string;
  navigationContext: NavigationResolverContext;
  onNavigate: (command: OperationalNavigationCommand, trigger?: HTMLElement) => void;
  onRecordAction: (action: RecommendationActionType, note?: string, selectedCrewId?: string) => Promise<void>;
  onRetryRecommendation: () => void;
  recentActions: RecommendationAction[];
  recommendation: Recommendation | null;
  recommendationError: string;
  recommendationLoading: boolean;
  selectedIncident?: Incident;
}) {
  const [draftAction, setDraftAction] = useState<RecommendationActionType | null>(null);
  const [draftNote, setDraftNote] = useState("");
  const [draftError, setDraftError] = useState("");
  const [selectedActionCrewId, setSelectedActionCrewId] = useState<string | undefined>();
  const actionNoteRef = useRef<HTMLTextAreaElement>(null);
  const incidentActions = recentActions.filter((action) => action.incident_id === recommendation?.incident_id).slice(0, 4);
  const currentDecision = selectedIncident?.current_decision ?? incidentActions[0] ?? null;
  const recommendedCrewId = recommendation?.recommended_crew?.crew_id;
  const selectedActionCrew = recommendation
    ? [recommendation.recommended_crew, ...recommendation.alternatives].find(
        (crew) => crew?.crew_id === selectedActionCrewId
      )
    : undefined;
  const alternativeSelected = Boolean(
    selectedActionCrewId && recommendedCrewId && selectedActionCrewId !== recommendedCrewId
  );

  useEffect(() => {
    setSelectedActionCrewId(recommendation?.recommended_crew?.crew_id);
    setDraftAction(null);
    setDraftNote("");
    setDraftError("");
  }, [recommendation?.recommendation_id]);

  useEffect(() => {
    if (draftAction) actionNoteRef.current?.focus();
  }, [draftAction]);

  function startDraft(action: RecommendationActionType) {
    setDraftAction(action);
    setDraftNote("");
    setDraftError("");
  }

  function selectComparisonCrew(crewId: string) {
    setSelectedActionCrewId(crewId);
    setDraftNote("");
    setDraftError("");
    setDraftAction(crewId === recommendedCrewId ? null : "modified");
  }

  async function submitDraftAction() {
    if (!draftAction) return;
    const note = draftNote.trim();
    if ((draftAction === "deferred" || draftAction === "overridden" || (draftAction === "modified" && alternativeSelected)) && !note) {
      setDraftError(`${formatAction(draftAction)} reason is required.`);
      return;
    }

    setDraftError("");
    await onRecordAction(
      draftAction,
      note,
      draftAction === "modified" ? selectedActionCrewId : undefined
    );
    setDraftAction(null);
    setDraftNote("");
  }

  return (
    <section className="panel recommendation-panel">
      <PanelTitle icon={Bot} title="Recommendation" />
      {selectedIncident ? (
        <div className="selected-context">
          <span>Selected incident</span>
          <strong>{selectedIncident.incident_id} · {selectedIncident.municipality}</strong>
        </div>
      ) : null}
      {recommendationLoading ? (
        <ViewState compact title="Loading recommendation..." message="Evaluating the selected incident and available crews." />
      ) : recommendationError ? (
        <ViewState
          actionLabel="Retry recommendation"
          compact
          message={recommendationError}
          onAction={onRetryRecommendation}
          title="Recommendation unavailable"
        />
      ) : recommendation ? (
        <>
          <div className="recommendation-hero">
            <span>{recommendation.recommended_action}</span>
            <strong>{recommendation.recommended_crew ? <>{recommendation.recommended_crew.crew_name} <span className="crew-id">({recommendation.recommended_crew.crew_id})</span></> : "Supervisor review"}</strong>
            <small className="confidence-line">
              <span>Confidence: {formatConfidence(recommendation.confidence)}</span>
              {recommendation.explanation ? <span>{recommendation.explanation.confidence_rationale.reason}</span> : null}
            </small>
          </div>
          {recommendation.recommended_crew ? (
            <EntityNavigationActions
              accessibleLabel="Recommended crew destinations"
              context={navigationContext}
              destinationKinds={["full_detail"]}
              labelOverrides={{ full_detail: "View recommended crew details" }}
              onNavigate={onNavigate}
              reference={{ kind: "crew", id: recommendation.recommended_crew.crew_id }}
            />
          ) : null}
          <div className="decision-status">
            <span>Current decision</span>
            <strong>{currentDecision ? formatAction(currentDecision.action) : "Pending dispatcher action"}</strong>
            {currentDecision?.reason ? <small>{currentDecision.reason}</small> : null}
          </div>
          {selectedIncident?.assigned_crews.length ? (
            <div className="decision-status assigned-state">
              <span>Assigned crew{selectedIncident.assigned_crews.length > 1 ? "s" : ""}</span>
              <div className="detail-link-list compact">
                {selectedIncident.assigned_crews.map((crew) => (
                  <EntityNavigationActions
                    accessibleLabel={`${crew.crew_name} destinations`}
                    context={navigationContext}
                    destinationKinds={["full_detail"]}
                    key={crew.assignment_id}
                    labelOverrides={{ full_detail: `${crew.crew_name} (${crew.crew_id})` }}
                    onNavigate={onNavigate}
                    reference={{ kind: "crew", id: crew.crew_id }}
                  />
                ))}
              </div>
            </div>
          ) : null}
          <p>{recommendation.expected_impact}</p>
          <div className="explain-grid">
            <div>
              <h3>Factors</h3>
              <ul>
                {recommendation.factors.map((factor) => <li key={factor}>{factor}</li>)}
              </ul>
            </div>
            <div>
              <h3>Constraints</h3>
              <ul>
                {recommendation.constraints.map((constraint) => <li key={constraint}>{constraint}</li>)}
              </ul>
            </div>
          </div>
          {recommendation.explanation?.data_quality_warnings.length ? (
            <div className="decision-status">
              <span>Data quality</span>
              <small>{recommendation.explanation.data_quality_warnings.join(" ")}</small>
            </div>
          ) : null}
          {recommendation.explanation?.excluded_candidates.length ? (
            <div className="decision-status">
              <span>Excluded candidates</span>
              <small>{recommendation.explanation.excluded_candidates.length} crew candidate(s) failed blocking constraints.</small>
            </div>
          ) : null}
          {recommendation.recommended_crew ? (
            <div className={`pending-crew-choice ${alternativeSelected ? "alternative" : ""}`}>
              <span>Pending crew choice</span>
              <strong>
                {selectedActionCrew?.crew_name ?? recommendation.recommended_crew.crew_name}{" "}
                <span className="crew-id">({selectedActionCrewId ?? recommendation.recommended_crew.crew_id})</span>
              </strong>
              <small>
                {alternativeSelected
                  ? "A lower-ranked feasible crew is selected. Record a reason to create a modified assignment."
                  : "The top-ranked recommendation will be assigned if accepted."}
              </small>
            </div>
          ) : null}
          <RecommendationComparison
            onSelectCrew={selectComparisonCrew}
            recommendation={recommendation}
            selectedCrewId={selectedActionCrewId}
          />
          <div className="action-row">
            <button
              disabled={actionLoading !== null || alternativeSelected || !recommendedCrewId}
              onClick={() => onRecordAction("accepted", undefined, recommendedCrewId)}
              type="button"
            >
              <Check size={16} />
              Accept
            </button>
            <button disabled={actionLoading !== null} onClick={() => startDraft("modified")} type="button">
              <Pencil size={16} />
              Modify
            </button>
            <button disabled={actionLoading !== null} onClick={() => startDraft("deferred")} type="button">
              <Pause size={16} />
              Defer
            </button>
            <button disabled={actionLoading !== null} onClick={() => startDraft("overridden")} type="button">
              <ShieldAlert size={16} />
              Override
            </button>
          </div>
          {draftAction ? (
            <div className="action-note-form">
              <label htmlFor="recommendation-action-note">
                {draftAction === "modified" && alternativeSelected
                  ? "Alternative crew selection reason"
                  : draftAction === "modified"
                    ? "Modification note"
                    : `${formatAction(draftAction)} reason`}
              </label>
              <textarea
                aria-describedby={draftError ? "recommendation-action-error" : undefined}
                aria-invalid={Boolean(draftError)}
                aria-required={draftAction === "deferred" || draftAction === "overridden" || (draftAction === "modified" && alternativeSelected)}
                id="recommendation-action-note"
                onChange={(event) => setDraftNote(event.target.value)}
                ref={actionNoteRef}
                placeholder={
                  draftAction === "modified"
                    ? alternativeSelected
                      ? "Explain why this lower-ranked feasible crew should be assigned."
                      : "Add a short note for the modified recommendation."
                    : draftAction === "deferred"
                      ? "Explain why this recommendation is being deferred."
                    : "Explain why this recommendation is being overridden."
                }
                value={draftNote}
              />
              {draftError ? <p className="action-error" id="recommendation-action-error" role="alert">{draftError}</p> : null}
              <div className="note-action-row">
                <button disabled={actionLoading !== null} onClick={submitDraftAction} type="button">
                  {actionLoading === draftAction
                    ? "Recording..."
                    : draftAction === "modified" && alternativeSelected
                      ? "Assign selected crew"
                      : "Record Action"}
                </button>
                <button
                  disabled={actionLoading !== null}
                  onClick={() => {
                    setDraftAction(null);
                    setDraftNote("");
                    setDraftError("");
                  }}
                  type="button"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : null}
          {actionMessage ? (
            <p
              aria-live={actionFailed ? "assertive" : "polite"}
              className={actionFailed ? "action-message action-error" : "action-message"}
              role={actionFailed ? "alert" : "status"}
            >
              {actionMessage}
            </p>
          ) : null}
          <RecentActions actions={incidentActions.length ? incidentActions : recentActions.slice(0, 4)} />
        </>
      ) : (
        <EmptyState message="No recommendation is available because there are no active incidents." />
      )}
    </section>
  );
}

function RecentActions({ actions }: { actions: RecommendationAction[] }) {
  return (
    <section className="recent-actions">
      <h3>Recent Actions</h3>
      {actions.length === 0 ? (
        <p>No recommendation actions recorded yet.</p>
      ) : (
        <div className="action-history">
          {actions.map((action) => {
            const recommendedCrew = action.recommendation.recommended_crew;
            const selectedCrew = [recommendedCrew, ...action.recommendation.alternatives].find(
              (crew) => crew?.crew_id === action.crew_id
            );
            const alternativeAssigned = Boolean(
              selectedCrew && recommendedCrew && selectedCrew.crew_id !== recommendedCrew.crew_id
            );
            return (
              <article className="action-event" key={action.event_id}>
                <div>
                  <strong>{action.action}</strong>
                  <span>{action.incident_id} / {selectedCrew?.crew_name ?? recommendedCrew?.crew_name ?? "Supervisor review"}</span>
                </div>
                <time>{new Date(action.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>
                {alternativeAssigned ? <p>AI recommended {recommendedCrew!.crew_name}; dispatcher selected {selectedCrew!.crew_name}.</p> : null}
                {action.note ? <p>{action.note}</p> : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default App;
