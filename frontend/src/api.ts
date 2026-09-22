import type {
  Assignment,
  AssignmentMutation,
  AssignmentReasonCategory,
  Crew,
  CopilotResponse,
  DashboardSummary,
  Incident,
  Recommendation,
  RecommendationAction,
  RecommendationActionType,
  ScenarioDescriptor
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type ErrorPayload = {
  detail?: string;
  error?: {
    message?: string;
    details?: Array<{ location?: string; message?: string }>;
  };
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ErrorPayload | null;
    const message = payload?.error?.message ?? payload?.detail ?? `Request failed: ${response.status}`;
    const issue = payload?.error?.details?.[0];
    const issueText = issue?.message
      ? `${issue.location ? `${issue.location}: ` : ""}${issue.message}`
      : "";
    throw new Error(issueText ? `${message} ${issueText}` : message);
  }
  return response.json() as Promise<T>;
}

async function getJson<T>(path: string): Promise<T> {
  return requestJson<T>(path);
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  return requestJson<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
}

async function putJson<T>(path: string, body: unknown): Promise<T> {
  return requestJson<T>(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
}

export const api = {
  scenarios: () => getJson<ScenarioDescriptor[]>("/api/scenarios"),
  activeScenario: () => getJson<ScenarioDescriptor>("/api/scenarios/active"),
  activateScenario: (scenarioId: string) =>
    putJson<ScenarioDescriptor>("/api/scenarios/active", { scenario_id: scenarioId }),
  dashboard: () => getJson<DashboardSummary>("/api/dashboard"),
  incidents: () => getJson<Incident[]>("/api/incidents"),
  crews: () => getJson<Crew[]>("/api/crews"),
  assignments: () => getJson<Assignment[]>("/api/assignments"),
  unassignAssignment: (assignmentId: string, reasonCategory: AssignmentReasonCategory, note?: string) =>
    postJson<AssignmentMutation>("/api/assignment-actions", {
      assignment_id: assignmentId,
      action: "unassigned",
      reason_category: reasonCategory,
      note
    }),
  reassignAssignment: (assignmentId: string, selectedCrewId: string, reasonCategory: AssignmentReasonCategory, note?: string) =>
    postJson<AssignmentMutation>("/api/assignment-actions", {
      assignment_id: assignmentId,
      action: "reassigned",
      selected_crew_id: selectedCrewId,
      reason_category: reasonCategory,
      note
    }),
  optimize: (incidentId?: string) => postJson<Recommendation>("/api/optimize", { incident_id: incidentId }),
  auditEvents: () => getJson<RecommendationAction[]>("/api/audit/events"),
  recordRecommendationAction: (
    action: RecommendationActionType,
    recommendation: Recommendation,
    note?: string,
    selectedCrewId?: string
  ) =>
    postJson<RecommendationAction>("/api/recommendation-actions", {
      incident_id: recommendation.incident_id,
      action,
      recommendation,
      selected_crew_id: selectedCrewId,
      reason: note
    }),
  chat: (message: string, incidentId?: string, crewId?: string) =>
    postJson<CopilotResponse>("/api/chat", {
      message,
      incident_id: incidentId,
      crew_id: crewId
    })
};
