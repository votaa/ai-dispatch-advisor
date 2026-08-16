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

function selectOption(select: HTMLSelectElement, value: string) {
  return Array.from(select.options).find((option) => option.value === value);
}

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

  it("filters and sorts Crew Board cards while showing crew IDs", async () => {
    apiMocks.crews.mockResolvedValue([
      {
        crew_id: "CR-01",
        crew_name: "North Line Alpha",
        home_region: "North",
        status: "available",
        capability: "line",
        current_location: "Millbrook",
        shift_remaining_hours: 8,
        storm_ready: true,
        travel_minutes_to_selected_incident: 12,
        assigned_incidents: []
      },
      {
        crew_id: "SC-06",
        crew_name: "South Vegetation",
        home_region: "South",
        status: "assigned",
        capability: "vegetation",
        current_location: "Fairview",
        shift_remaining_hours: 4,
        storm_ready: false,
        travel_minutes_to_selected_incident: 22,
        assigned_incidents: [{ assignment_id: "a-1", incident_id: "INC-1001", assigned_at: "2026-08-10T00:00:00Z", municipality: "Millbrook", severity: "critical" }]
      }
    ]);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Crew Board" }));
    expect(await screen.findByText("(CR-01)")).toBeTruthy();
    expect(screen.getByText("Showing 1–2 of 2 matching crews (2 total)")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Crew Board status"), { target: { value: "available" } });
    expect(await screen.findByText("Showing 1–1 of 1 matching crews (2 total)")).toBeTruthy();
    expect(screen.getByText("North Line Alpha")).toBeTruthy();
    expect(screen.queryByText("South Vegetation")).toBeNull();
    const capabilityFilter = screen.getByLabelText("Crew Board capability") as HTMLSelectElement;
    expect(selectOption(capabilityFilter, "vegetation")?.disabled).toBe(true);
    expect(selectOption(capabilityFilter, "line")?.textContent).toBe("line (1)");
    const regionFilter = screen.getByLabelText("Crew Board region") as HTMLSelectElement;
    expect(selectOption(regionFilter, "South")?.disabled).toBe(true);
    expect(selectOption(regionFilter, "North")?.textContent).toBe("North (1)");
    expect(screen.getByRole("button", { name: /Crew Board sort ascending/ })).toBeTruthy();
  });

  it("cascades severity and region counts consistently across incident views", async () => {
    const facetedIncidents = [
      { ...baseIncident, incident_id: "INC-NC", region: "North", severity: "critical", critical_facility: true },
      { ...baseIncident, incident_id: "INC-SC", region: "South", severity: "critical", critical_facility: true },
      { ...baseIncident, incident_id: "INC-NH", region: "North", severity: "high", critical_facility: true },
      { ...baseIncident, incident_id: "INC-EM", region: "East", severity: "medium", critical_facility: true }
    ];
    apiMocks.incidents.mockResolvedValue(facetedIncidents);
    apiMocks.dashboard.mockResolvedValue({
      ...dashboard("base"),
      active_incidents: facetedIncidents.length,
      top_incidents: facetedIncidents
    });
    render(<App />);

    const verifyFacets = async (label: string) => {
      const regionFilter = await screen.findByLabelText(`${label} region`) as HTMLSelectElement;
      fireEvent.change(regionFilter, { target: { value: "North" } });
      const severityFilter = screen.getByLabelText(`${label} severity`) as HTMLSelectElement;
      expect(selectOption(severityFilter, "critical")?.textContent).toBe("Critical (1)");
      expect(selectOption(severityFilter, "high")?.textContent).toBe("High (1)");
      expect(selectOption(severityFilter, "medium")?.disabled).toBe(true);

      fireEvent.change(severityFilter, { target: { value: "critical" } });
      expect(selectOption(regionFilter, "North")?.textContent).toBe("North (1)");
      expect(selectOption(regionFilter, "South")?.textContent).toBe("South (1)");
      expect(selectOption(regionFilter, "East")?.disabled).toBe(true);
    };

    await verifyFacets("Priority dispatch queue");
    fireEvent.click(screen.getByRole("button", { name: "Dispatch" }));
    await verifyFacets("Dispatch incident queue");
    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    await verifyFacets("Active incidents");
    fireEvent.click(screen.getByRole("button", { name: "Storm Mode" }));
    await verifyFacets("Storm exceptions");
  });

  it("provides current-page, focus, skip-link, and labeled-input semantics", async () => {
    render(<App />);

    expect(screen.getByRole("link", { name: "Skip to main content" }).getAttribute("href")).toBe("#main-content");
    expect(screen.getByRole("button", { name: "Dashboard" }).getAttribute("aria-current")).toBe("page");
    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "Incidents" })).toBe(document.activeElement));
    expect(screen.getByRole("button", { name: "Incidents" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("button", { name: "INC-1001" }).getAttribute("aria-pressed")).toBe("true");

    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));
    expect(screen.getByLabelText("Copilot question")).toBeTruthy();
  });

  it("compares the recommended crew with ranked alternatives and tradeoffs", async () => {
    const recommendedCrew = {
      crew_id: "CR-01",
      crew_name: "North Line Alpha",
      home_region: "North",
      status: "available",
      capability: "line",
      current_location: "Millbrook",
      shift_remaining_hours: 8,
      storm_ready: true,
      travel_minutes_to_selected_incident: 10,
      estimated_travel_minutes: 10,
      suitability_score: 92,
      capability_match: true,
      assigned_incidents: []
    };
    apiMocks.optimize.mockResolvedValue({
      ...recommendation,
      recommended_crew: recommendedCrew,
      alternatives: [{
        ...recommendedCrew,
        crew_id: "CR-02",
        crew_name: "East Line Beta",
        shift_remaining_hours: 6,
        storm_ready: false,
        travel_minutes_to_selected_incident: 20,
        estimated_travel_minutes: 20,
        suitability_score: 77
      }]
    });
    render(<App />);

    const comparison = await screen.findByRole("region", { name: "Recommendation comparison" });
    expect(comparison.textContent).toContain("Recommended");
    expect(comparison.textContent).toContain("Alternative 1");
    expect(comparison.textContent).toContain("10 minutes slower travel");
    expect(comparison.textContent).toContain("15 points lower suitability");
  });

  it("assigns a selected ranked alternative as a reasoned modified decision", async () => {
    const recommendedCrew = {
      crew_id: "CR-01",
      crew_name: "North Line Alpha",
      home_region: "North",
      status: "available",
      capability: "line",
      current_location: "Millbrook",
      shift_remaining_hours: 8,
      storm_ready: true,
      travel_minutes_to_selected_incident: 10,
      estimated_travel_minutes: 10,
      suitability_score: 92,
      capability_match: true,
      assigned_incidents: []
    };
    const alternativeCrew = {
      ...recommendedCrew,
      crew_id: "CR-02",
      crew_name: "East Line Beta",
      estimated_travel_minutes: 20,
      suitability_score: 77
    };
    const rankedRecommendation = {
      ...recommendation,
      recommended_crew: recommendedCrew,
      alternatives: [alternativeCrew]
    };
    apiMocks.optimize.mockResolvedValue(rankedRecommendation);
    apiMocks.recordRecommendationAction.mockResolvedValue({
      ...recordedDecision,
      event_id: "event-modified-alternative",
      crew_id: "CR-02",
      action: "modified",
      reason: "Crew is already staged near the switching location",
      note: "Crew is already staged near the switching location",
      recommendation: rankedRecommendation
    });
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Select this crew" }));
    expect(screen.getByText("Alternative crew selection reason")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Accept" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Assign selected crew" }));
    const validationError = screen.getByRole("alert");
    expect(validationError.textContent).toBe("Modified reason is required.");
    const reasonField = screen.getByLabelText("Alternative crew selection reason");
    expect(reasonField.getAttribute("aria-invalid")).toBe("true");
    expect(reasonField.getAttribute("aria-required")).toBe("true");

    fireEvent.change(screen.getByLabelText("Alternative crew selection reason"), {
      target: { value: "Crew is already staged near the switching location" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Assign selected crew" }));

    await waitFor(() => expect(apiMocks.recordRecommendationAction).toHaveBeenCalledWith(
      "modified",
      rankedRecommendation,
      "Crew is already staged near the switching location",
      "CR-02"
    ));
    expect(await screen.findByText("AI recommended North Line Alpha; dispatcher selected East Line Beta.")).toBeTruthy();
  });

  it("supports keyboard-focused Defer and Override reason workflows", async () => {
    const recommendedCrew = {
      crew_id: "CR-01",
      crew_name: "North Line Alpha",
      home_region: "North",
      status: "available",
      capability: "line",
      current_location: "Millbrook",
      shift_remaining_hours: 8,
      storm_ready: true,
      travel_minutes_to_selected_incident: 10,
      assigned_incidents: []
    };
    const actionableRecommendation = { ...recommendation, recommended_crew: recommendedCrew };
    apiMocks.optimize.mockResolvedValue(actionableRecommendation);
    apiMocks.recordRecommendationAction.mockImplementation(async (action: string, currentRecommendation: typeof actionableRecommendation, note?: string) => ({
      ...recordedDecision,
      event_id: `event-${action}`,
      action,
      reason: note ?? null,
      note: note ?? null,
      recommendation: currentRecommendation
    }));
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Defer" }));
    const deferReason = screen.getByLabelText("Deferred reason");
    expect(deferReason).toBe(document.activeElement);
    expect(deferReason.getAttribute("aria-required")).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: "Record Action" }));
    expect(screen.getByRole("alert").textContent).toBe("Deferred reason is required.");
    fireEvent.change(deferReason, { target: { value: "Awaiting field safety confirmation" } });
    fireEvent.click(screen.getByRole("button", { name: "Record Action" }));
    await waitFor(() => expect(apiMocks.recordRecommendationAction).toHaveBeenCalledWith(
      "deferred",
      actionableRecommendation,
      "Awaiting field safety confirmation",
      undefined
    ));

    await waitFor(() => expect((screen.getByRole("button", { name: "Override" }) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: "Override" }));
    const overrideReason = screen.getByLabelText("Overridden reason");
    expect(overrideReason).toBe(document.activeElement);
    fireEvent.change(overrideReason, { target: { value: "Supervisor-directed switching plan" } });
    fireEvent.click(screen.getByRole("button", { name: "Record Action" }));
    await waitFor(() => expect(apiMocks.recordRecommendationAction).toHaveBeenCalledWith(
      "overridden",
      actionableRecommendation,
      "Supervisor-directed switching plan",
      undefined
    ));
  });

  it("opens incident and crew details with assignment cross-navigation", async () => {
    const assignedCrew = {
      crew_id: "CR-01",
      crew_name: "North Line Alpha",
      home_region: "North",
      status: "assigned",
      capability: "line",
      current_location: "Millbrook",
      shift_remaining_hours: 8,
      storm_ready: true,
      travel_minutes_to_selected_incident: 10,
      assigned_incidents: [{ assignment_id: "a-1", incident_id: "INC-1001", assigned_at: "2026-08-10T00:00:00Z", municipality: "Millbrook", severity: "critical" }]
    };
    apiMocks.crews.mockResolvedValue([assignedCrew]);
    apiMocks.incidents.mockResolvedValue([{ ...baseIncident, assigned_crews: [{ crew_id: "CR-01", crew_name: "North Line Alpha", assignment_id: "a-1", assigned_at: "2026-08-10T00:00:00Z" }] }]);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    expect(await screen.findByLabelText("Incident details INC-1001")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /North Line Alpha/ }));
    expect(await screen.findByLabelText("Crew details CR-01")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /INC-1001/ }));
    expect(await screen.findByLabelText("Incident details INC-1001")).toBeTruthy();
  });

  it("filters, sorts, and paginates large incident queues", async () => {
    const manyIncidents = Array.from({ length: 55 }, (_, index) => ({
      ...baseIncident,
      incident_id: `INC-${String(1001 + index)}`,
      municipality: `Municipality ${index + 1}`,
      customers_out: 55 - index,
      severity: index % 2 === 0 ? "critical" : "medium"
    }));
    apiMocks.incidents.mockResolvedValue(manyIncidents);
    apiMocks.dashboard.mockResolvedValue({ ...dashboard("base"), top_incidents: manyIncidents.slice(0, 5) });
    apiMocks.auditEvents.mockResolvedValue([]);
    render(<App />);

    await screen.findByLabelText("Active synthetic scenario");
    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));

    expect(await screen.findByText("Showing 1–50 of 55 matching incidents (55 total)")).toBeTruthy();
    expect(screen.getAllByRole("columnheader")).toHaveLength(8);
    expect((screen.getByRole("button", { name: "Next Active incidents page" }) as HTMLButtonElement).disabled).toBe(false);
    const customersHeader = screen.getByRole("button", { name: /Active incidents Sort by Customers ascending/ });
    fireEvent.click(customersHeader);
    expect(customersHeader.closest("th")?.getAttribute("aria-sort")).toBe("ascending");
    fireEvent.click(customersHeader);
    expect(customersHeader.closest("th")?.getAttribute("aria-sort")).toBe("descending");
    const etrHeader = screen.getByRole("button", { name: /Active incidents Sort by ETR ascending/ });
    fireEvent.click(etrHeader);
    expect(etrHeader.closest("th")?.getAttribute("aria-sort")).toBe("ascending");
    fireEvent.click(screen.getByRole("button", { name: "Next Active incidents page" }));
    expect(screen.getByText("Page 2 of 2")).toBeTruthy();

    const search = screen.getByLabelText("Active incidents search");
    fireEvent.change(search, { target: { value: "Municipality 55" } });
    expect(await screen.findByText("Showing 1–1 of 1 matching incidents (55 total)")).toBeTruthy();
    expect(screen.getByText("INC-1055")).toBeTruthy();
    fireEvent.change(search, { target: { value: "does-not-exist" } });
    expect(await screen.findByText("No incidents match the current filters.")).toBeTruthy();
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

  it("keeps recommendation state loading while a slow scenario refresh is in progress", async () => {
    let resolveIncidents: (value: Array<typeof baseIncident>) => void = () => undefined;
    apiMocks.auditEvents.mockResolvedValue([]);
    render(<App />);

    const selector = await screen.findByLabelText("Active synthetic scenario") as HTMLSelectElement;
    await waitFor(() => expect(selector.value).toBe("base"));
    apiMocks.incidents.mockReturnValue(new Promise((resolve) => {
      resolveIncidents = resolve;
    }));
    fireEvent.change(selector, { target: { value: "storm" } });

    expect((await screen.findByRole("status")).textContent).toContain("Loading scenario data...");
    expect(screen.getByText(/Large scenarios may take longer to rank/)).toBeTruthy();
    expect(screen.queryByText("No recommendation is available because there are no active incidents.")).toBeNull();
    expect(selector.disabled).toBe(true);

    resolveIncidents([baseIncident]);
    await waitFor(() => expect(selector.value).toBe("storm"));
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
