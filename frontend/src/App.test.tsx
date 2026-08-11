import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  scenarios: vi.fn(),
  activeScenario: vi.fn(),
  activateScenario: vi.fn(),
  dashboard: vi.fn(),
  incidents: vi.fn(),
  crews: vi.fn(),
  assignments: vi.fn(),
  optimize: vi.fn(),
  auditEvents: vi.fn(),
  recordRecommendationAction: vi.fn(),
  chat: vi.fn()
}));

vi.mock("./api", () => ({ api: apiMocks }));

import App from "./App";

const baseScenario = {
  schema_version: "1.0",
  scenario_id: "base",
  name: "Base Operations",
  description: "Standard operations",
  event_type: "blue_sky",
  expected_conditions: ["Normal staffing"],
  files: {
    incidents: "PendingIncidents.csv",
    crews: "Crews.csv",
    assignments: "Assignments.csv",
    historical_repairs: "HistoricalRepairs.csv",
    weather: "Weather.csv",
    critical_facilities: "CriticalFacilities.csv",
    topology: "Topology.csv"
  },
  validation_status: "valid",
  is_active: true
};

const stormScenario = {
  ...baseScenario,
  scenario_id: "storm",
  name: "Major Storm",
  description: "Major storm operations",
  event_type: "storm",
  expected_conditions: ["High outage volume"],
  is_active: false
};

const baseIncident = {
  incident_id: "INC-1001",
  municipality: "Millbrook",
  feeder: "FDR-1",
  severity: "critical",
  status: "new",
  customers_out: 100,
  critical_facility: true,
  hazard: "downed wire",
  required_skill: "line",
  age_minutes: 20,
  etr: "Unknown",
  assigned_crews: [],
  current_decision: null
};

const recommendation = {
  recommendation_id: "REC-INC-1001-CR-01",
  incident_id: "INC-1001",
  recommended_action: "Assign crew",
  recommended_crew: null,
  confidence: "medium",
  expected_impact: "Restore affected customers",
  factors: ["Crew is available"],
  constraints: ["Dispatcher approval required"],
  alternatives: []
};

const recordedDecision = {
  event_id: "event-1",
  scenario_id: "base",
  recommendation_id: recommendation.recommendation_id,
  incident_id: "INC-1001",
  crew_id: null,
  action: "deferred",
  reason: "Awaiting field report",
  note: "Awaiting field report",
  recommendation,
  created_at: "2026-08-09T12:00:00Z",
  actor: "demo-dispatcher"
};

function dashboard(scenario: string) {
  return {
    active_incidents: 1,
    customers_out: 100,
    available_crews: 0,
    assigned_crews: 0,
    critical_facility_incidents: 1,
    high_priority_incidents: 1,
    top_incidents: [baseIncident],
    scenario,
    data_freshness: "Synthetic demo data"
  };
}

function emptyDashboard(scenario: string) {
  return {
    ...dashboard(scenario),
    active_incidents: 0,
    customers_out: 0,
    critical_facility_incidents: 0,
    high_priority_incidents: 0,
    top_incidents: []
  };
}

describe("application states and scenario switching", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.scenarios.mockResolvedValue([baseScenario, stormScenario]);
    apiMocks.activeScenario.mockResolvedValue(baseScenario);
    apiMocks.activateScenario.mockResolvedValue({ ...stormScenario, is_active: true });
    apiMocks.dashboard.mockResolvedValue(dashboard("base"));
    apiMocks.incidents.mockResolvedValue([baseIncident]);
    apiMocks.crews.mockResolvedValue([]);
    apiMocks.assignments.mockResolvedValue([]);
    apiMocks.optimize.mockResolvedValue(recommendation);
    apiMocks.auditEvents.mockResolvedValue([recordedDecision]);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows purposeful loading states across data-backed primary views", () => {
    apiMocks.dashboard.mockReturnValue(new Promise(() => undefined));
    render(<App />);

    expect(screen.getByText("Loading dashboard...")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Dispatch" }));
    expect(screen.getByText("Loading dispatch workspace...")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    expect(screen.getByText("Loading incidents...")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Crew Board" }));
    expect(screen.getByText("Loading crew board...")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Storm Mode" }));
    expect(screen.getByText("Loading storm mode...")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Scenario" }));
    expect(screen.getByText("Loading scenario metadata...")).toBeTruthy();
  });

  it("shows useful empty states instead of blank tables and panels", async () => {
    apiMocks.dashboard.mockResolvedValue(emptyDashboard("base"));
    apiMocks.incidents.mockResolvedValue([]);
    apiMocks.crews.mockResolvedValue([]);
    apiMocks.assignments.mockResolvedValue([]);
    apiMocks.auditEvents.mockResolvedValue([]);
    render(<App />);

    expect(await screen.findByText("No priority incidents are active in this scenario.")).toBeTruthy();
    expect(screen.getByText("No recommendation is available because there are no active incidents.")).toBeTruthy();
    expect(apiMocks.optimize).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Dispatch" }));
    expect(screen.getByText("No active incidents are available for dispatch.")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    expect(screen.getByText("No active incidents are available in this scenario.")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Crew Board" }));
    expect(screen.getByText("No crews are available in this scenario.")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Storm Mode" }));
    expect(screen.getByText("No storm exceptions are active in this scenario.")).toBeTruthy();
  });

  it("uses shared responsive table regions and complete recommendation action groups", async () => {
    apiMocks.auditEvents.mockResolvedValue([]);
    const { container } = render(<App />);

    expect(await screen.findByRole("region", { name: "Priority dispatch queue" })).toBeTruthy();
    expect(container.querySelector(".dashboard-workspace .recommendation-panel")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Dispatch" }));
    expect(screen.getByRole("region", { name: "Dispatch incident queue" })).toBeTruthy();
    expect(container.querySelector(".split-layout .recommendation-panel")).toBeTruthy();
    for (const action of ["Accept", "Modify", "Defer", "Override"]) {
      expect(screen.getByRole("button", { name: action })).toBeTruthy();
    }

    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    expect(screen.getByRole("region", { name: "Active incidents" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Storm Mode" }));
    const stormTable = screen.getByRole("region", { name: "Storm exceptions" });
    expect(stormTable.closest(".panel")?.classList.contains("full-width")).toBe(true);
  });

  it("shows a backend error with a working connection retry", async () => {
    apiMocks.dashboard.mockRejectedValueOnce(new Error("Network request failed"));
    render(<App />);

    expect((await screen.findByRole("alert")).textContent).toContain("Network request failed");
    apiMocks.dashboard.mockResolvedValue(dashboard("base"));

    fireEvent.click(screen.getAllByRole("button", { name: "Retry connection" })[0]);

    expect(await screen.findByText("Customers Out")).toBeTruthy();
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  });

  it("shows optimization failures separately and retries the recommendation", async () => {
    apiMocks.auditEvents.mockResolvedValue([]);
    apiMocks.optimize.mockRejectedValueOnce(new Error("Optimization service unavailable"));
    render(<App />);

    expect(await screen.findByText("Recommendation unavailable")).toBeTruthy();
    expect(screen.getByText("Optimization service unavailable")).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();

    apiMocks.optimize.mockResolvedValue(recommendation);
    fireEvent.click(screen.getByRole("button", { name: "Retry recommendation" }));

    expect(await screen.findByText("Supervisor review")).toBeTruthy();
    expect(apiMocks.optimize).toHaveBeenCalledTimes(2);
  });

  it("shows Copilot guidance, progress, and inline failure feedback", async () => {
    let rejectChat: (reason?: unknown) => void = () => undefined;
    apiMocks.chat.mockReturnValue(new Promise((_, reject) => {
      rejectChat = reject;
    }));
    render(<App />);

    await screen.findByLabelText("Active synthetic scenario");
    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));
    expect(screen.getByText("Ask one of the sample questions to query the synthetic dispatch data.")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Ask Copilot" }));
    expect(screen.getByRole("button", { name: "Asking..." })).toBeTruthy();
    rejectChat(new Error("Copilot service unavailable"));

    expect(await screen.findByText(/Unable to reach Copilot: Copilot service unavailable/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Ask Copilot" })).toBeTruthy();
  });

  it("keeps the current scenario selected when activation fails", async () => {
    apiMocks.auditEvents.mockResolvedValue([]);
    apiMocks.activateScenario.mockRejectedValue(new Error("Scenario validation failed"));
    render(<App />);

    const selector = await screen.findByLabelText("Active synthetic scenario") as HTMLSelectElement;
    await waitFor(() => expect(selector.value).toBe("base"));
    fireEvent.change(selector, { target: { value: "storm" } });

    expect(await screen.findByText("Scenario validation failed")).toBeTruthy();
    expect(selector.value).toBe("base");
  });

  it("requires confirmation when the active scenario has recorded decisions", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    render(<App />);

    const selector = await screen.findByLabelText("Active synthetic scenario") as HTMLSelectElement;
    await waitFor(() => expect(selector.value).toBe("base"));

    fireEvent.change(selector, { target: { value: "storm" } });

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("decisions will remain saved"));
    expect(apiMocks.activateScenario).not.toHaveBeenCalled();
    await waitFor(() => expect(selector.value).toBe("base"));

    apiMocks.dashboard.mockResolvedValue(dashboard("storm"));
    apiMocks.auditEvents.mockResolvedValue([]);
    fireEvent.change(selector, { target: { value: "storm" } });

    await waitFor(() => expect(apiMocks.activateScenario).toHaveBeenCalledWith("storm"));
    await waitFor(() => expect(selector.value).toBe("storm"));
    expect(await screen.findByText("Major Storm activated.")).toBeTruthy();
  });
});
