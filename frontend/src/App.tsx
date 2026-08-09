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
import { useEffect, useMemo, useState } from "react";
import type { ElementType } from "react";
import { api } from "./api";
import type {
  Assignment,
  Crew,
  DashboardSummary,
  Incident,
  Recommendation,
  RecommendationAction,
  RecommendationActionType,
  ScenarioDescriptor
} from "./types";

type ViewKey = "dashboard" | "dispatch" | "incidents" | "crews" | "storm" | "scenario" | "copilot";
type ChatTurn = { question: string; answer: string };

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

function App() {
  const [view, setView] = useState<ViewKey>("dashboard");
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [crews, setCrews] = useState<Crew[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [recommendationActions, setRecommendationActions] = useState<RecommendationAction[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | undefined>();
  const [chatMessage, setChatMessage] = useState("What should I focus on first?");
  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<RecommendationActionType | null>(null);
  const [actionMessage, setActionMessage] = useState("");
  const [scenarios, setScenarios] = useState<ScenarioDescriptor[]>([]);
  const [activeScenario, setActiveScenario] = useState<ScenarioDescriptor | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [scenarioMessage, setScenarioMessage] = useState("");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    Promise.all([refreshOperationalState(), api.scenarios(), api.activeScenario()])
      .then(([{ incidentData }, scenarioData, activeScenarioData]) => {
        setSelectedIncidentId(incidentData[0]?.incident_id);
        setScenarios(scenarioData);
        setActiveScenario(activeScenarioData);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!selectedIncidentId) {
      setRecommendation(null);
      return;
    }
    api.optimize(selectedIncidentId)
      .then((nextRecommendation) => {
        if (!cancelled) setRecommendation(nextRecommendation);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedIncidentId]);

  const selectedIncident = useMemo(
    () => incidents.find((incident) => incident.incident_id === selectedIncidentId) ?? incidents[0],
    [incidents, selectedIncidentId]
  );

  const criticalIncidents = incidents.filter((incident) => incident.critical_facility);

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
      setChatTurns((turns) => [{ question, answer: response.answer }, ...turns]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Copilot request failed";
      setChatTurns((turns) => [{ question, answer: `Unable to reach Copilot: ${message}` }, ...turns]);
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
      setRecommendation(null);
      setActionMessage("");
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

  async function recordRecommendationAction(action: RecommendationActionType, note?: string) {
    if (!recommendation) return;

    setActionLoading(action);
    setActionMessage("");
    try {
      const event = await api.recordRecommendationAction(action, recommendation, note?.trim() || undefined);
      await refreshOperationalState();
      if (selectedIncidentId) {
        const nextRecommendation = await api.optimize(selectedIncidentId);
        setRecommendation(nextRecommendation);
      }
      setRecommendationActions((actions) => [event, ...actions.filter((item) => item.event_id !== event.event_id)]);
      setActionMessage(`Recommendation ${formatAction(action)}.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Recommendation action failed";
      setActionMessage(message);
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div className="app-shell">
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

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">Developer Bootstrap MVP</p>
            <h1>{navItems.find((item) => item.key === view)?.label}</h1>
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

        {error ? <div className="error-banner">Backend unavailable: {error}</div> : null}
        {scenarioMessage ? (
          <div className={scenarioMessage.endsWith("activated.") ? "success-banner" : "error-banner"}>
            {scenarioMessage}
          </div>
        ) : null}

        {view === "dashboard" && dashboard && (
          <section className="view-grid">
            <Metric label="Customers Out" value={dashboard.customers_out.toLocaleString()} />
            <Metric label="Active Incidents" value={dashboard.active_incidents} />
            <Metric label="Available Crews" value={dashboard.available_crews} />
            <Metric label="Crews Assigned" value={dashboard.assigned_crews} />
            <Metric label="Critical Facility Events" value={dashboard.critical_facility_incidents} />

            <section className="panel wide">
              <PanelTitle icon={AlertTriangle} title="Priority Dispatch Queue" />
              <IncidentTable incidents={dashboard.top_incidents} selectedIncidentId={selectedIncidentId} onSelect={setSelectedIncidentId} />
            </section>

            <RecommendationPanel
              actionLoading={actionLoading}
              actionMessage={actionMessage}
              onRecordAction={recordRecommendationAction}
              recentActions={recommendationActions}
              recommendation={recommendation}
            />
          </section>
        )}

        {view === "dispatch" && (
          <section className="split-layout">
            <section className="panel">
              <PanelTitle icon={RadioTower} title="Incident Queue" />
              <IncidentTable incidents={incidents} selectedIncidentId={selectedIncidentId} onSelect={setSelectedIncidentId} />
            </section>
            <RecommendationPanel
              actionLoading={actionLoading}
              actionMessage={actionMessage}
              onRecordAction={recordRecommendationAction}
              recentActions={recommendationActions}
              recommendation={recommendation}
              selectedIncident={selectedIncident}
            />
          </section>
        )}

        {view === "incidents" && (
          <section className="panel">
            <PanelTitle icon={ClipboardList} title="Active Incidents" />
            <IncidentTable incidents={incidents} selectedIncidentId={selectedIncidentId} onSelect={setSelectedIncidentId} />
          </section>
        )}

        {view === "crews" && (
          <section className="panel">
            <PanelTitle icon={Users} title="Crew Board" />
            <div className="crew-grid">
              {crews.map((crew) => (
                <article className="crew-card" key={crew.crew_id}>
                  <div>
                    <strong>{crew.crew_name}</strong>
                    <span>{crew.capability}</span>
                  </div>
                  <span className={`crew-status ${crew.status}`}>{crew.status}</span>
                  <p>{crew.current_location}</p>
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
                  <small>{crew.shift_remaining_hours} shift hours remaining</small>
                </article>
              ))}
            </div>
          </section>
        )}

        {view === "storm" && dashboard && (
          <section className="view-grid">
            <Metric label="High Priority Incidents" value={dashboard.high_priority_incidents} />
            <Metric label="Critical Facilities" value={criticalIncidents.length} />
            <Metric label="Crews Assigned" value={dashboard.assigned_crews} />
            <Metric label="Customers Out" value={dashboard.customers_out.toLocaleString()} />
            <section className="panel wide">
              <PanelTitle icon={CloudLightning} title="Storm Exceptions" />
              <IncidentTable incidents={criticalIncidents.length ? criticalIncidents : incidents.slice(0, 4)} selectedIncidentId={selectedIncidentId} onSelect={setSelectedIncidentId} />
            </section>
          </section>
        )}

        {view === "scenario" && (
          <section className="split-layout">
            <section className="panel">
              <PanelTitle icon={Map} title="Active Demo Scenario" />
              {activeScenario ? (
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
                <p>Loading scenario metadata...</p>
              )}
            </section>
            <RecommendationPanel
              actionLoading={actionLoading}
              actionMessage={actionMessage}
              onRecordAction={recordRecommendationAction}
              recentActions={recommendationActions}
              recommendation={recommendation}
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
            <textarea value={chatMessage} onChange={(event) => setChatMessage(event.target.value)} />
            <button className="primary-action" disabled={chatLoading} onClick={askCopilot} type="button">
              {chatLoading ? "Asking..." : "Ask Copilot"}
            </button>
            <div className="chat-history">
              {chatTurns.length === 0 ? (
                <div className="copilot-answer">Ask one of the sample questions to query the synthetic dispatch data.</div>
              ) : (
                chatTurns.map((turn, index) => (
                  <article className="chat-turn" key={`${turn.question}-${index}`}>
                    <strong>{turn.question}</strong>
                    <p>{turn.answer}</p>
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

function IncidentTable({
  incidents,
  selectedIncidentId,
  onSelect
}: {
  incidents: Incident[];
  selectedIncidentId?: string;
  onSelect: (incidentId: string) => void;
}) {
  return (
    <div className="table-shell">
      <table>
        <thead>
          <tr>
            <th>Incident</th>
            <th>Region</th>
            <th>Customers</th>
            <th>Severity</th>
            <th>Hazard</th>
            <th>Assigned Crews</th>
            <th>Decision</th>
            <th>ETR</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((incident) => (
            <tr
              className={selectedIncidentId === incident.incident_id ? "selected-row" : ""}
              key={incident.incident_id}
              onClick={() => onSelect(incident.incident_id)}
            >
              <td>
                <strong>{incident.incident_id}</strong>
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
    </div>
  );
}

function RecommendationPanel({
  actionLoading,
  actionMessage,
  onRecordAction,
  recentActions,
  recommendation,
  selectedIncident
}: {
  actionLoading: RecommendationActionType | null;
  actionMessage: string;
  onRecordAction: (action: RecommendationActionType, note?: string) => Promise<void>;
  recentActions: RecommendationAction[];
  recommendation: Recommendation | null;
  selectedIncident?: Incident;
}) {
  const [draftAction, setDraftAction] = useState<RecommendationActionType | null>(null);
  const [draftNote, setDraftNote] = useState("");
  const [draftError, setDraftError] = useState("");
  const incidentActions = recentActions.filter((action) => action.incident_id === recommendation?.incident_id).slice(0, 4);
  const currentDecision = selectedIncident?.current_decision ?? incidentActions[0] ?? null;

  function startDraft(action: RecommendationActionType) {
    setDraftAction(action);
    setDraftNote("");
    setDraftError("");
  }

  async function submitDraftAction() {
    if (!draftAction) return;
    const note = draftNote.trim();
    if ((draftAction === "deferred" || draftAction === "overridden") && !note) {
      setDraftError(`${formatAction(draftAction)} reason is required.`);
      return;
    }

    setDraftError("");
    await onRecordAction(draftAction, note);
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
      {recommendation ? (
        <>
          <div className="recommendation-hero">
            <span>{recommendation.recommended_action}</span>
            <strong>{recommendation.recommended_crew?.crew_name ?? "Supervisor review"}</strong>
            <small>Confidence: {recommendation.confidence}</small>
          </div>
          <div className="decision-status">
            <span>Current decision</span>
            <strong>{currentDecision ? formatAction(currentDecision.action) : "Pending dispatcher action"}</strong>
            {currentDecision?.reason ? <small>{currentDecision.reason}</small> : null}
          </div>
          {selectedIncident?.assigned_crews.length ? (
            <div className="decision-status assigned-state">
              <span>Assigned crew{selectedIncident.assigned_crews.length > 1 ? "s" : ""}</span>
              <strong>{selectedIncident.assigned_crews.map((crew) => crew.crew_name).join(", ")}</strong>
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
          <div className="action-row">
            <button disabled={actionLoading !== null} onClick={() => onRecordAction("accepted")} type="button">
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
                {draftAction === "modified" ? "Modification note" : `${formatAction(draftAction)} reason`}
              </label>
              <textarea
                id="recommendation-action-note"
                onChange={(event) => setDraftNote(event.target.value)}
                placeholder={
                  draftAction === "modified"
                    ? "Add a short note for the modified recommendation."
                    : draftAction === "deferred"
                      ? "Explain why this recommendation is being deferred."
                    : "Explain why this recommendation is being overridden."
                }
                value={draftNote}
              />
              {draftError ? <p className="action-error">{draftError}</p> : null}
              <div className="note-action-row">
                <button disabled={actionLoading !== null} onClick={submitDraftAction} type="button">
                  {actionLoading === draftAction ? "Recording..." : "Record Action"}
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
          {actionMessage ? <p className="action-message">{actionMessage}</p> : null}
          <RecentActions actions={incidentActions.length ? incidentActions : recentActions.slice(0, 4)} />
        </>
      ) : (
        <p>Loading recommendation...</p>
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
          {actions.map((action) => (
            <article className="action-event" key={action.event_id}>
              <div>
                <strong>{action.action}</strong>
                <span>{action.incident_id} / {action.recommendation.recommended_crew?.crew_name ?? "Supervisor review"}</span>
              </div>
              <time>{new Date(action.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>
              {action.note ? <p>{action.note}</p> : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default App;
