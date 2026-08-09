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

describe("scenario switching", () => {
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
