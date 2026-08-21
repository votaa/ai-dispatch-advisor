import {
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
import { useEffect, useMemo, useRef, useState } from "react";
import type { ElementType, ReactNode } from "react";
import { api } from "./api";
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

type ViewKey = "dashboard" | "dispatch" | "incidents" | "crews" | "storm" | "scenario" | "copilot";
type ChatTurn = {
  question: string;
  answer: string;
  error?: boolean;
  metadata?: Omit<CopilotResponse, "answer">;
};
type IncidentSortKey = "id" | "region" | "customers" | "severity" | "hazard" | "assigned" | "decision" | "etr";
type SortDirection = "asc" | "desc";
type CrewSortKey = "name" | "status" | "capability" | "shift" | "assigned" | "travel";

const navItems: Array<{ key: ViewKey; label: string; icon: ElementType }> = [
  { key: "dashboard", label: "Dashboard", icon: BarChart3 },
  { key: "dispatch", label: "Dispatch", icon: RadioTower },
  { key: "incidents", label: "Incidents", icon: ClipboardList },
  { key: "crews", label: "Crew Board", icon: Users },
  { key: "storm", label: "Storm Mode", icon: CloudLightning },
  { key: "scenario", label: "Scenario", icon: Map },
  { key: "copilot", label: "AI Copilot", icon: Bot }
];

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
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [crews, setCrews] = useState<Crew[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [recommendationActions, setRecommendationActions] = useState<RecommendationAction[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | undefined>();
  const [selectedCrewId, setSelectedCrewId] = useState<string | undefined>();
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

  useEffect(() => {
    loadApplication();
  }, []);

  useEffect(() => {
    pageHeadingRef.current?.focus();
  }, [view]);

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
  const selectedCrew = useMemo(
    () => crews.find((crew) => crew.crew_id === selectedCrewId),
    [crews, selectedCrewId]
  );

  const criticalIncidents = incidents.filter((incident) => incident.critical_facility);
  const operationalDataUnavailable = Boolean(error && !dashboard && incidents.length === 0 && crews.length === 0);

  async function loadApplication() {
    setInitialLoading(true);
    setError("");
    try {
      const [{ incidentData }, scenarioData, activeScenarioData] = await Promise.all([
        refreshOperationalState(),
        api.scenarios(),
        api.activeScenario()
      ]);
      setSelectedIncidentId(incidentData[0]?.incident_id);
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
      const response = await api.chat(question, selectedIncidentId);
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
      const activatedScenario = await api.activateScenario(scenarioId);
      setActiveScenario(activatedScenario);
      setScenarios((items) =>
        items.map((item) => ({ ...item, is_active: item.scenario_id === activatedScenario.scenario_id }))
      );
      setSelectedIncidentId(undefined);
      setSelectedCrewId(undefined);
      setRecommendation(null);
      setRecommendationError("");
      setActionMessage("");
      setActionFailed(false);
      setChatTurns([]);

      const { incidentData } = await refreshOperationalState();
      setSelectedIncidentId(incidentData[0]?.incident_id);
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

  function openCrewDetails(crewId: string) {
    setSelectedCrewId(crewId);
    setView("crews");
  }

  function openIncidentDetails(incidentId: string) {
    setSelectedIncidentId(incidentId);
    setView("incidents");
  }

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
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <aside className="sidebar">
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
                onClick={() => setView(item.key)}
                type="button"
              >
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

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
        </header>

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
              <Metric label="Customers Out" value={dashboard.customers_out.toLocaleString()} />
              <Metric label="Active Incidents" value={dashboard.active_incidents} />
              <Metric label="Available Crews" value={dashboard.available_crews} />
              <Metric label="Crews Assigned" value={dashboard.assigned_crews} />
              <Metric label="Critical Facility Events" value={dashboard.critical_facility_incidents} />
            </div>

            <div className="dashboard-workspace">
              <section className="panel">
                <PanelTitle icon={AlertTriangle} title="Priority Dispatch Queue" />
                <IncidentTable
                  emptyMessage="No priority incidents are active in this scenario."
                  incidents={dashboard.top_incidents}
                  selectedIncidentId={selectedIncidentId}
                  tableLabel="Priority dispatch queue"
                  onSelect={setSelectedIncidentId}
                />
              </section>

              <RecommendationPanel
                actionLoading={actionLoading}
                actionFailed={actionFailed}
                actionMessage={actionMessage}
                onOpenCrew={openCrewDetails}
                onRecordAction={recordRecommendationAction}
                recentActions={recommendationActions}
                recommendation={recommendation}
                recommendationError={recommendationError}
                recommendationLoading={recommendationLoading || scenarioLoading || initialLoading}
                onRetryRecommendation={() => setRecommendationRequestVersion((version) => version + 1)}
              />
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
          <section className="split-layout">
            <section className="panel">
              <PanelTitle icon={RadioTower} title="Incident Queue" />
              <IncidentTable
                emptyMessage="No active incidents are available for dispatch."
                incidents={incidents}
                selectedIncidentId={selectedIncidentId}
                tableLabel="Dispatch incident queue"
                onSelect={setSelectedIncidentId}
              />
            </section>
            <RecommendationPanel
              actionLoading={actionLoading}
              actionFailed={actionFailed}
              actionMessage={actionMessage}
              onOpenCrew={openCrewDetails}
              onRecordAction={recordRecommendationAction}
              recentActions={recommendationActions}
              recommendation={recommendation}
              recommendationError={recommendationError}
              recommendationLoading={recommendationLoading || scenarioLoading || initialLoading}
              onRetryRecommendation={() => setRecommendationRequestVersion((version) => version + 1)}
              selectedIncident={selectedIncident}
            />
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
          <section className="panel">
            <PanelTitle icon={ClipboardList} title="Active Incidents" />
            <IncidentTable
              emptyMessage="No active incidents are available in this scenario."
              incidents={incidents}
              selectedIncidentId={selectedIncidentId}
              tableLabel="Active incidents"
              onSelect={setSelectedIncidentId}
            />
            {selectedIncident ? <IncidentDetail incident={selectedIncident} onOpenCrew={openCrewDetails} /> : null}
          </section>
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
          <section className="panel">
            <PanelTitle icon={Users} title="Crew Board" />
            {crews.length === 0 ? (
              <EmptyState message="No crews are available in this scenario." />
            ) : (
              <CrewBoard
                crews={crews}
                onCloseDetails={() => setSelectedCrewId(undefined)}
                onOpenIncident={openIncidentDetails}
                onSelectCrew={setSelectedCrewId}
                selectedCrew={selectedCrew}
                selectedCrewId={selectedCrewId}
              />
            )}
          </section>
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
          <section className="view-grid">
            <Metric label="High Priority Incidents" value={dashboard.high_priority_incidents} />
            <Metric label="Critical Facilities" value={criticalIncidents.length} />
            <Metric label="Crews Assigned" value={dashboard.assigned_crews} />
            <Metric label="Customers Out" value={dashboard.customers_out.toLocaleString()} />
            <section className="panel full-width">
              <PanelTitle icon={CloudLightning} title="Storm Exceptions" />
              <IncidentTable
                emptyMessage="No storm exceptions are active in this scenario."
                incidents={criticalIncidents.length ? criticalIncidents : incidents.slice(0, 4)}
                selectedIncidentId={selectedIncidentId}
                tableLabel="Storm exceptions"
                onSelect={setSelectedIncidentId}
              />
            </section>
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
              onOpenCrew={openCrewDetails}
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
            <div className="prompt-row">
              {[
                "What should I focus on first?",
                "How many crews are available?",
                "What critical facilities are affected?",
                "Why was this crew recommended?",
                "Summarize storm status"
              ].map((prompt) => (
                <button key={prompt} onClick={() => usePrompt(prompt)} type="button">
                  {prompt}
                </button>
              ))}
            </div>
            <label className="sr-only" htmlFor="copilot-question">Copilot question</label>
            <textarea id="copilot-question" value={chatMessage} onChange={(event) => setChatMessage(event.target.value)} />
            <button className="primary-action" disabled={chatLoading} onClick={askCopilot} type="button">
              {chatLoading ? "Asking..." : "Ask Copilot"}
            </button>
            <div aria-live="polite" className="chat-history">
              {chatTurns.length === 0 ? (
                <div className="copilot-answer">Ask one of the sample questions to query the synthetic dispatch data.</div>
              ) : (
                chatTurns.map((turn, index) => (
                  <article className="chat-turn" key={`${turn.question}-${index}`} role={turn.error ? "alert" : undefined}>
                    <strong>{turn.question}</strong>
                    <p>{turn.answer}</p>
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
      </main>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <section className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </section>
  );
}

function PanelTitle({ icon: Icon, title }: { icon: ElementType; title: string }) {
  return (
    <div className="panel-title">
      <Icon size={18} />
      <h2>{title}</h2>
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

function IncidentDetail({ incident, onOpenCrew }: { incident: Incident; onOpenCrew: (crewId: string) => void }) {
  return (
    <aside aria-label={`Incident details ${incident.incident_id}`} className="detail-panel incident-detail">
      <div className="detail-heading">
        <div>
          <span>Selected incident</span>
          <h3>{incident.incident_id} · {incident.municipality}</h3>
        </div>
        <span className={severityClass(incident.severity)}>{incident.severity}</span>
      </div>
      <dl className="detail-grid">
        <div><dt>Region</dt><dd>{incident.region}</dd></div>
        <div><dt>Feeder</dt><dd>{incident.feeder}</dd></div>
        <div><dt>Customers out</dt><dd>{incident.customers_out.toLocaleString()}</dd></div>
        <div><dt>Status</dt><dd>{formatCrewStatus(incident.status)}</dd></div>
        <div><dt>Hazard</dt><dd>{incident.hazard}</dd></div>
        <div><dt>Critical facility</dt><dd>{incident.critical_facility ? "Yes" : "No"}</dd></div>
        <div><dt>Incident age</dt><dd>{incident.age_minutes} min</dd></div>
        <div><dt>ETR</dt><dd>{incident.etr}</dd></div>
      </dl>
      <div className="detail-section">
        <h4>Assigned crews</h4>
        {incident.assigned_crews.length ? (
          <div className="detail-link-list">
            {incident.assigned_crews.map((crew) => (
              <button key={crew.assignment_id} onClick={() => onOpenCrew(crew.crew_id)} type="button">
                {crew.crew_name} <span>({crew.crew_id})</span>
              </button>
            ))}
          </div>
        ) : <p>No crews assigned.</p>}
      </div>
      <div className="detail-section">
        <h4>Current decision</h4>
        <p>{incident.current_decision ? formatAction(incident.current_decision.action) : "No decision recorded."}</p>
        {incident.current_decision?.reason ? <small>{incident.current_decision.reason}</small> : null}
      </div>
    </aside>
  );
}

function CrewDetail({ crew, onClose, onOpenIncident }: { crew: Crew; onClose: () => void; onOpenIncident: (incidentId: string) => void }) {
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
              <button key={assignment.assignment_id} onClick={() => onOpenIncident(assignment.incident_id)} type="button">
                {assignment.incident_id}{assignment.municipality ? ` · ${assignment.municipality}` : ""}
              </button>
            ))}
          </div>
        ) : <p>No active incident assignments.</p>}
      </div>
    </aside>
  );
}

function CrewBoard({
  crews,
  onCloseDetails,
  onOpenIncident,
  onSelectCrew,
  selectedCrew,
  selectedCrewId
}: {
  crews: Crew[];
  onCloseDetails: () => void;
  onOpenIncident: (incidentId: string) => void;
  onSelectCrew: (crewId: string) => void;
  selectedCrew?: Crew;
  selectedCrewId?: string;
}) {
  const pageSize = 24;
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [capability, setCapability] = useState("all");
  const [region, setRegion] = useState("all");
  const [stormReady, setStormReady] = useState("all");
  const [sort, setSort] = useState<{ key: CrewSortKey; direction: SortDirection }>({ key: "name", direction: "asc" });
  const [page, setPage] = useState(0);

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
  const { filteredCrews, facetCounts } = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
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
        (excludedFacet === "status" || status === "all" || crew.status === status) &&
        (excludedFacet === "capability" || capability === "all" || crew.capability === capability) &&
        (excludedFacet === "region" || region === "all" || crew.home_region === region) &&
        (excludedFacet === "stormReady" || stormReady === "all" || (stormReady === "ready" ? crew.storm_ready : !crew.storm_ready))
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
      facetCounts: {
        status: facetCountsFor(statusEligible, (crew) => crew.status),
        capability: facetCountsFor(capabilityEligible, (crew) => crew.capability),
        region: facetCountsFor(regionEligible, (crew) => crew.home_region),
        stormReady: facetCountsFor(stormReadyEligible, (crew) => crew.storm_ready ? "ready" : "not-ready")
      }
    };
  }, [capability, crews, query, region, sort, status, stormReady]);
  const pageCount = Math.max(1, Math.ceil(filteredCrews.length / pageSize));
  const visibleCrews = filteredCrews.slice(page * pageSize, (page + 1) * pageSize);

  useEffect(() => {
    setPage(0);
  }, [capability, query, region, sort, status, stormReady, crews.length]);

  const toggleSortDirection = () => {
    setSort((current) => ({ ...current, direction: current.direction === "asc" ? "desc" : "asc" }));
  };

  return (
    <div className="crew-board">
      <div className="crew-board-controls" aria-label="Crew Board filters" role="group">
        <label>
          Search
          <input aria-label="Crew Board search" onChange={(event) => setQuery(event.target.value)} placeholder="Crew, capability, region, or incident" type="search" value={query} />
        </label>
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
        <span>Showing {visibleCrews.length ? page * pageSize + 1 : 0}–{Math.min((page + 1) * pageSize, filteredCrews.length)} of {filteredCrews.length} matching crews ({crews.length} total)</span>
        {pageCount > 1 ? (
          <div aria-label="Crew Board pagination" className="incident-pagination" role="navigation">
            <button aria-label="Previous Crew Board page" disabled={page === 0} onClick={() => setPage((current) => Math.max(0, current - 1))} type="button">Previous</button>
            <span>Page {page + 1} of {pageCount}</span>
            <button aria-label="Next Crew Board page" disabled={page >= pageCount - 1} onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))} type="button">Next</button>
          </div>
        ) : null}
      </div>
      {visibleCrews.length === 0 ? <EmptyState message="No crews match the current filters." /> : (
        <div className="crew-grid">
          {visibleCrews.map((crew) => (
            <article className={`crew-card ${selectedCrewId === crew.crew_id ? "selected-card" : ""}`} key={crew.crew_id}>
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
              {crew.assigned_incidents.length ? (
                <div className="assignment-list">
                  {crew.assigned_incidents.map((assignment) => (
                    <span key={assignment.assignment_id}>
                      Assigned to {assignment.incident_id}
                      {assignment.municipality ? ` in ${assignment.municipality}` : ""}
                    </span>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      )}
      {selectedCrew ? <CrewDetail crew={selectedCrew} onClose={onCloseDetails} onOpenIncident={onOpenIncident} /> : null}
    </div>
  );
}

function IncidentTable({
  emptyMessage,
  incidents,
  selectedIncidentId,
  tableLabel,
  onSelect
}: {
  emptyMessage: string;
  incidents: Incident[];
  selectedIncidentId?: string;
  tableLabel: string;
  onSelect: (incidentId: string) => void;
}) {
  const pageSize = 50;
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");
  const [region, setRegion] = useState("all");
  const [sort, setSort] = useState<{ key: IncidentSortKey; direction: SortDirection } | null>(null);
  const [page, setPage] = useState(0);

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
  const { filteredIncidents, facetCounts } = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const matches = (incident: Incident, excludedFacet?: "severity" | "region") => {
      const searchable = [incident.incident_id, incident.municipality, incident.feeder, incident.hazard]
        .join(" ")
        .toLowerCase();
      return (
        (!normalizedQuery || searchable.includes(normalizedQuery)) &&
        (excludedFacet === "severity" || severity === "all" || incident.severity.toLowerCase() === severity) &&
        (excludedFacet === "region" || region === "all" || incident.region === region)
      );
    };
    const matching = incidents.filter((incident) => matches(incident));
    const severityEligible = incidents.filter((incident) => matches(incident, "severity"));
    const regionEligible = incidents.filter((incident) => matches(incident, "region"));
    const severityRank: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
    const sorted = matching.sort((left, right) => {
      if (sort) {
        const direction = sort.direction === "asc" ? 1 : -1;
        let comparison = 0;
        if (sort.key === "customers") comparison = left.customers_out - right.customers_out;
        if (sort.key === "severity") comparison = (severityRank[left.severity.toLowerCase()] ?? 0) - (severityRank[right.severity.toLowerCase()] ?? 0);
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
      return (
        (severityRank[right.severity.toLowerCase()] ?? 0) - (severityRank[left.severity.toLowerCase()] ?? 0) ||
        right.customers_out - left.customers_out ||
        left.incident_id.localeCompare(right.incident_id)
      );
    });
    return {
      filteredIncidents: sorted,
      facetCounts: {
        severity: facetCountsFor(severityEligible, (incident) => incident.severity.toLowerCase()),
        region: facetCountsFor(regionEligible, (incident) => incident.region)
      }
    };
  }, [incidents, query, region, severity, sort]);
  const pageCount = Math.max(1, Math.ceil(filteredIncidents.length / pageSize));
  const visibleIncidents = filteredIncidents.slice(page * pageSize, (page + 1) * pageSize);

  useEffect(() => {
    setPage(0);
  }, [query, region, severity, sort, incidents.length]);

  const toggleSort = (key: IncidentSortKey) => {
    setSort((current) => current?.key === key
      ? { key, direction: current.direction === "asc" ? "desc" : "asc" }
      : { key, direction: "asc" });
  };

  const sortIndicator = (key: IncidentSortKey) => sort?.key === key ? (sort.direction === "asc" ? "↑" : "↓") : "↕";
  const sortLabel = (key: IncidentSortKey, label: string) => sort?.key === key
    ? `Sort by ${label} ${sort.direction === "asc" ? "descending next" : "ascending next"}`
    : `Sort by ${label} ascending`;

  if (incidents.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <div className="incident-table">
      <div className="incident-table-controls" aria-label={`${tableLabel} filters`} role="group">
        <label>
          Search
          <input
            aria-label={`${tableLabel} search`}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="ID, municipality, feeder, or hazard"
            type="search"
            value={query}
          />
        </label>
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
      </div>
      <div className="incident-table-summary" aria-live="polite">
        <span>Showing {visibleIncidents.length ? page * pageSize + 1 : 0}–{Math.min((page + 1) * pageSize, filteredIncidents.length)} of {filteredIncidents.length} matching incidents ({incidents.length} total)</span>
        {pageCount > 1 ? (
          <div aria-label={`${tableLabel} pagination`} className="incident-pagination" role="navigation">
            <button aria-label={`Previous ${tableLabel} page`} disabled={page === 0} onClick={() => setPage((current) => Math.max(0, current - 1))} type="button">Previous</button>
            <span>Page {page + 1} of {pageCount}</span>
            <button aria-label={`Next ${tableLabel} page`} disabled={page >= pageCount - 1} onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))} type="button">Next</button>
          </div>
        ) : null}
      </div>
      {visibleIncidents.length === 0 ? (
        <EmptyState message="No incidents match the current filters." />
      ) : (
        <ResponsiveTable label={tableLabel}>
          <table>
        <thead>
          <tr>
            {([
              ["id", "Incident"],
              ["region", "Region"],
              ["customers", "Customers"],
              ["severity", "Severity"],
              ["hazard", "Hazard"],
              ["assigned", "Assigned Crews"],
              ["decision", "Decision"],
              ["etr", "ETR"]
            ] as Array<[IncidentSortKey, string]>).map(([key, label]) => (
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
              aria-selected={selectedIncidentId === incident.incident_id}
              className={selectedIncidentId === incident.incident_id ? "selected-row" : ""}
              key={incident.incident_id}
              onClick={() => onSelect(incident.incident_id)}
            >
              <td>
                <button
                  aria-pressed={selectedIncidentId === incident.incident_id}
                  className="incident-select-button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelect(incident.incident_id);
                  }}
                  type="button"
                >
                  {incident.incident_id}
                </button>
                <span>{incident.municipality} / {incident.feeder}</span>
              </td>
              <td>{incident.region}</td>
              <td>{incident.customers_out.toLocaleString()}</td>
              <td><span className={severityClass(incident.severity)}>{incident.severity}</span></td>
              <td>{incident.hazard}</td>
              <td>
                {incident.assigned_crews.length ? (
                  incident.assigned_crews.map((crew) => (
                    <span className="assignment-chip" key={crew.assignment_id}>{crew.crew_name}</span>
                  ))
                ) : (
                  <span>Unassigned</span>
                )}
              </td>
              <td>
                {incident.current_decision ? (
                  <span className={`decision-badge decision-${incident.current_decision.action}`}>
                    {formatAction(incident.current_decision.action)}
                  </span>
                ) : (
                  <span>No decision</span>
                )}
              </td>
              <td>{incident.etr}</td>
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
  onOpenCrew,
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
  onOpenCrew: (crewId: string) => void;
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
            <button className="detail-link" onClick={() => onOpenCrew(recommendation.recommended_crew!.crew_id)} type="button">
              View recommended crew details
            </button>
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
                  <button key={crew.assignment_id} onClick={() => onOpenCrew(crew.crew_id)} type="button">
                    {crew.crew_name} ({crew.crew_id})
                  </button>
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
