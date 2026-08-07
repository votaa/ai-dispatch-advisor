import type {
  Assignment,
  Crew,
  DashboardSummary,
  Incident,
  Recommendation,
  RecommendationAction,
  RecommendationActionType
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload && typeof payload.detail === "string" ? payload.detail : `Request failed: ${response.status}`;
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  dashboard: () => getJson<DashboardSummary>("/api/dashboard"),
  incidents: () => getJson<Incident[]>("/api/incidents"),
  crews: () => getJson<Crew[]>("/api/crews"),
  assignments: () => getJson<Assignment[]>("/api/assignments"),
  optimize: (incidentId?: string) => postJson<Recommendation>("/api/optimize", { incident_id: incidentId }),
  auditEvents: () => getJson<RecommendationAction[]>("/api/audit/events"),
  recordRecommendationAction: (
    action: RecommendationActionType,
    recommendation: Recommendation,
    note?: string
  ) =>
    postJson<RecommendationAction>("/api/recommendation-actions", {
      incident_id: recommendation.incident_id,
      action,
      recommendation,
      reason: note
    }),
  chat: (message: string, incidentId?: string) =>
    postJson<{ answer: string; source: string; safety_note: string }>("/api/chat", {
      message,
      incident_id: incidentId
    })
};
