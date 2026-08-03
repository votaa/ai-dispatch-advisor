import { AlertTriangle, BarChart3, Bot, ClipboardList, CloudLightning, Map, RadioTower, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ElementType } from "react";
import { api } from "./api";
import type { Assignment, Crew, DashboardSummary, Incident, Recommendation } from "./types";

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
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | undefined>();
  const [chatMessage, setChatMessage] = useState("What should I focus on first?");
  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    Promise.all([api.dashboard(), api.incidents(), api.crews(), api.assignments()])
      .then(([dashboardData, incidentData, crewData, assignmentData]) => {
        setDashboard(dashboardData);
        setIncidents(incidentData);
        setCrews(crewData);
        setAssignments(assignmentData);
        setSelectedIncidentId(incidentData[0]?.incident_id);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedIncidentId) return;
    api.optimize(selectedIncidentId).then(setRecommendation).catch((err: Error) => setError(err.message));
  }, [selectedIncidentId]);

  const selectedIncident = useMemo(
    () => incidents.find((incident) => incident.incident_id === selectedIncidentId) ?? incidents[0],
    [incidents, selectedIncidentId]
  );

  const criticalIncidents = incidents.filter((incident) => incident.critical_facility);

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

  function usePrompt(prompt: string) {
    setChatMessage(prompt);
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
          <div className="status-pill">
            <span className="pulse" />
            Synthetic scenario: base
          </div>
        </header>

        {error ? <div className="error-banner">Backend unavailable: {error}</div> : null}

        {view === "dashboard" && dashboard && (
          <section className="view-grid">
            <Metric label="Customers Out" value={dashboard.customers_out.toLocaleString()} />
            <Metric label="Active Incidents" value={dashboard.active_incidents} />
            <Metric label="Available Crews" value={dashboard.available_crews} />
            <Metric label="Critical Facility Events" value={dashboard.critical_facility_incidents} />

            <section className="panel wide">
              <PanelTitle icon={AlertTriangle} title="Priority Dispatch Queue" />
              <IncidentTable incidents={dashboard.top_incidents} selectedIncidentId={selectedIncidentId} onSelect={setSelectedIncidentId} />
            </section>

            <RecommendationPanel recommendation={recommendation} />
          </section>
        )}

        {view === "dispatch" && (
          <section className="split-layout">
            <section className="panel">
              <PanelTitle icon={RadioTower} title="Incident Queue" />
              <IncidentTable incidents={incidents} selectedIncidentId={selectedIncidentId} onSelect={setSelectedIncidentId} />
            </section>
            <RecommendationPanel recommendation={recommendation} selectedIncident={selectedIncident} />
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
              <PanelTitle icon={Map} title="Scenario Comparison" />
              <div className="scenario-row">
                <strong>Base Recommendation</strong>
                <span>{recommendation?.expected_impact ?? "Select an incident to calculate a recommendation."}</span>
              </div>
              <div className="scenario-row">
                <strong>Alternative</strong>
                <span>Hold nearest crew for critical facility response and assign next best available crew.</span>
              </div>
              <div className="scenario-row">
                <strong>Tradeoff</strong>
                <span>Improves critical facility readiness but may increase restoration time for lower-severity incidents.</span>
              </div>
            </section>
            <RecommendationPanel recommendation={recommendation} selectedIncident={selectedIncident} />
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
              <td>{incident.etr}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RecommendationPanel({
  recommendation,
  selectedIncident
}: {
  recommendation: Recommendation | null;
  selectedIncident?: Incident;
}) {
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
            <button type="button">Accept</button>
            <button type="button">Modify</button>
            <button type="button">Defer</button>
            <button type="button">Override</button>
          </div>
        </>
      ) : (
        <p>Loading recommendation...</p>
      )}
    </section>
  );
}

export default App;
