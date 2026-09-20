import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
  freshness: {
    updated_at: "2026-08-09T10:41:03-04:00",
    source: "repository_publish",
    provenance: "Git commit 001559d"
  },
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
  freshness: {
    updated_at: "2026-08-09T09:24:27-04:00",
    source: "repository_publish",
    provenance: "Git commit a306ec1"
  },
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

async function openRecommendations() {
  const trigger = await screen.findByRole("button", { name: "Open recommendations" });
  fireEvent.click(trigger);
  return screen.findByRole("complementary", { name: "Dispatch recommendations" });
}

describe("application states and scenario switching", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
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
    vi.unstubAllGlobals();
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

  it("keeps data-quality incidents visible while withholding automatic selection", async () => {
    const withheldIncident = {
      ...baseIncident,
      critical_facility_level: null,
      matched_critical_facility_ids: ["FAC-UNKNOWN"],
      ranking_status: "withheld",
      ranking_warning: "Critical-facility level is unknown for matched facility IDs: FAC-UNKNOWN"
    };
    apiMocks.auditEvents.mockResolvedValue([]);
    apiMocks.incidents.mockResolvedValue([withheldIncident]);
    apiMocks.dashboard.mockResolvedValue({
      ...dashboard("base"),
      active_incidents: 1,
      top_incidents: []
    });

    render(<App />);

    expect(await screen.findByText("Ranking data requires review")).toBeTruthy();
    expect(screen.getByText(/1 incident is visible but withheld/)).toBeTruthy();
    expect(apiMocks.optimize).not.toHaveBeenCalled();
  });

  it("shows authoritative scenario freshness in UTC and updates it when scenarios switch", async () => {
    apiMocks.auditEvents.mockResolvedValue([]);
    apiMocks.dashboard.mockResolvedValueOnce(dashboard("base")).mockResolvedValueOnce(dashboard("storm"));
    render(<App />);

    expect(await screen.findByText("Scenario Last Updated 08/09/2026 14:41 UTC")).toBeTruthy();
    const selector = screen.getByLabelText("Active synthetic scenario") as HTMLSelectElement;
    fireEvent.change(selector, { target: { value: "storm" } });

    expect(await screen.findByText("Scenario Last Updated 08/09/2026 13:24 UTC")).toBeTruthy();
  });

  it("shows an explicit unavailable state when freshness metadata is absent", async () => {
    apiMocks.activeScenario.mockResolvedValue({ ...baseScenario, freshness: null });
    render(<App />);

    expect(await screen.findByText("Scenario Last Updated Unavailable")).toBeTruthy();
  });

  it("shows useful empty states instead of blank tables and panels", async () => {
    apiMocks.dashboard.mockResolvedValue(emptyDashboard("base"));
    apiMocks.incidents.mockResolvedValue([]);
    apiMocks.crews.mockResolvedValue([]);
    apiMocks.assignments.mockResolvedValue([]);
    apiMocks.auditEvents.mockResolvedValue([]);
    render(<App />);

    expect(await screen.findByText("No priority incidents are active in this scenario.")).toBeTruthy();
    await openRecommendations();
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
    expect(container.querySelector(".dashboard-workspace .recommendation-panel")).toBeNull();
    await openRecommendations();
    expect(screen.getByRole("complementary", { name: "Dispatch recommendations" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Close Recommendations" }));

    fireEvent.click(screen.getByRole("button", { name: "Dispatch" }));
    expect(screen.getByRole("region", { name: "Dispatch incident queue" })).toBeTruthy();
    expect(container.querySelector(".queue-workspace .recommendation-panel")).toBeNull();
    await openRecommendations();
    for (const action of ["Accept", "Modify", "Defer", "Override"]) {
      expect(screen.getByRole("button", { name: action })).toBeTruthy();
    }

    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    expect(screen.getByRole("region", { name: "Active incidents" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Storm Mode" }));
    const stormTable = screen.getByRole("region", { name: "Storm exceptions" });
    expect(stormTable.closest(".panel")?.classList.contains("full-width")).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "Scenario" }));
    expect(container.querySelector(".split-layout .recommendation-panel")).toBeTruthy();
  });

  it("offers the shared expandable workspace on every qualifying operational view", async () => {
    apiMocks.crews.mockResolvedValue([{
      crew_id: "CR-01",
      crew_name: "North Line Crew",
      capability: "line",
      status: "available",
      home_region: "North",
      current_location: "Millbrook",
      shift_remaining_hours: 8,
      storm_ready: true,
      travel_minutes_to_selected_incident: 12,
      assigned_incidents: []
    }]);
    render(<App />);

    const expectedControls: Array<[string, string]> = [
      ["Dashboard", "Expand Top 1 Priority Incidents workspace"],
      ["Dispatch", "Expand Incident Queue workspace"],
      ["Incidents", "Expand Active Incidents workspace"],
      ["Crew Board", "Expand Crew Board workspace"],
      ["Storm Mode", "Expand Storm Exceptions workspace"]
    ];

    await screen.findByRole("button", { name: expectedControls[0][1] });
    for (const [viewName, controlName] of expectedControls) {
      if (viewName !== "Dashboard") fireEvent.click(screen.getByRole("button", { name: viewName }));
      const expand = screen.getByRole("button", { name: controlName });
      fireEvent.click(expand);
      expect(screen.getByRole("button", { name: controlName.replace("Expand", "Restore") })).toBeTruthy();
      fireEvent.click(screen.getByRole("button", { name: controlName.replace("Expand", "Restore") }));
    }

    fireEvent.click(screen.getByRole("button", { name: "Scenario" }));
    expect(screen.queryByRole("button", { name: /^Expand .* workspace$/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));
    expect(screen.queryByRole("button", { name: /^Expand .* workspace$/ })).toBeNull();
  });

  it("restores an expanded workspace when navigation changes", async () => {
    render(<App />);

    const expand = await screen.findByRole("button", { name: "Expand Top 1 Priority Incidents workspace" });
    fireEvent.click(expand);
    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.click(screen.getByRole("button", { name: "Dispatch" }));

    expect(screen.getByRole("button", { name: "Expand Incident Queue workspace" })).toBeTruthy();
    expect(document.body.style.overflow).toBe("");
  });

  it("keeps the recommendation sheet synchronized and restores focus when dismissed", async () => {
    const secondIncident = {
      ...baseIncident,
      incident_id: "INC-2002",
      municipality: "Southport",
      feeder: "FDR-2",
      severity: "high"
    };
    apiMocks.incidents.mockResolvedValue([baseIncident, secondIncident]);
    apiMocks.dashboard.mockResolvedValue({ ...dashboard("base"), active_incidents: 8, top_incidents: [baseIncident, secondIncident] });
    apiMocks.optimize.mockImplementation(async (incidentId: string) => ({
      ...recommendation,
      incident_id: incidentId,
      recommendation_id: `REC-${incidentId}`
    }));
    render(<App />);

    const trigger = await screen.findByRole("button", { name: "Open recommendations" });
    fireEvent.click(trigger);
    expect(await screen.findByText("INC-1001 · Millbrook")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "INC-2002" }));
    expect(await screen.findByText("INC-2002 · Southport")).toBeTruthy();
    await waitFor(() => expect(apiMocks.optimize).toHaveBeenLastCalledWith("INC-2002"));

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("complementary", { name: "Dispatch recommendations" })).toBeNull();
    await waitFor(() => expect(trigger).toBe(document.activeElement));
  });

  it("provides compact queue sorting and labeled reflow fields", async () => {
    const secondIncident = {
      ...baseIncident,
      incident_id: "INC-2002",
      municipality: "Southport",
      customers_out: 250
    };
    apiMocks.incidents.mockResolvedValue([baseIncident, secondIncident]);
    apiMocks.dashboard.mockResolvedValue({ ...dashboard("base"), active_incidents: 8, top_incidents: [baseIncident, secondIncident] });
    const { container } = render(<App />);

    const compactSort = await screen.findByLabelText("Priority dispatch queue compact sort") as HTMLSelectElement;
    fireEvent.change(compactSort, { target: { value: "customers" } });
    expect(compactSort.value).toBe("customers");
    expect(screen.getByRole("button", { name: /Priority dispatch queue compact sort ascending/ })).toBeTruthy();

    const compactLabels = Array.from(container.querySelectorAll(".compact-cell-label")).map((label) => label.textContent);
    expect(compactLabels).toEqual([
      "Incident", "Region", "Customers", "Severity", "Critical Facility", "Hazard", "Assigned Crews", "Decision", "ETR",
      "Incident", "Region", "Customers", "Severity", "Critical Facility", "Hazard", "Assigned Crews", "Decision", "ETR"
    ]);
  });

  it("preserves backend priority order in the dashboard queue", async () => {
    const lowerPriorityIncident = {
      ...baseIncident,
      incident_id: "INC-2002",
      municipality: "Southport",
      severity: "low",
      customers_out: 1
    };
    const rankedIncidents = [lowerPriorityIncident, baseIncident];
    apiMocks.incidents.mockResolvedValue(rankedIncidents);
    apiMocks.dashboard.mockResolvedValue({
      ...dashboard("base"),
      active_incidents: 8,
      top_incidents: rankedIncidents
    });
    render(<App />);

    const queue = await screen.findByRole("table");
    const queueText = queue.textContent ?? "";
    expect(queueText.indexOf("Southport")).toBeGreaterThanOrEqual(0);
    expect(queueText.indexOf("Southport")).toBeLessThan(queueText.indexOf("Millbrook"));
  });

  it("shows a bounded dashboard priority limit and updates the label", async () => {
    const dashboardIncidents = Array.from({ length: 25 }, (_, index) => ({
      ...baseIncident,
      incident_id: `INC-${String(index + 1).padStart(4, "0")}`
    }));
    apiMocks.dashboard.mockResolvedValue({
      ...dashboard("base"),
      active_incidents: 25,
      top_incidents: dashboardIncidents
    });
    apiMocks.incidents.mockResolvedValue(dashboardIncidents);
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Top 7 Priority Incidents" })).toBeTruthy();
    const limit = screen.getByLabelText("Dashboard incidents shown") as HTMLSelectElement;
    expect(selectOption(limit, "100")?.disabled).toBe(false);
    expect(screen.getByRole("combobox", { name: "Search Top 7 Incidents Shown" })).toBeTruthy();

    fireEvent.change(limit, { target: { value: "100" } });
    expect(await screen.findByRole("heading", { name: "Top 25 Priority Incidents" })).toBeTruthy();
    expect(screen.getByText("Showing 25 of 25 active incidents")).toBeTruthy();
  });

  it("provides scoped grouped autocomplete suggestions on all five search surfaces", async () => {
    const autocompleteIncidents = Array.from({ length: 8 }, (_, index) => ({
      ...baseIncident,
      incident_id: `INC-ES-${index + 1}`,
      feeder: index < 2 ? "FDR-ES-13" : "FDR-ES-03",
      municipality: index % 2 === 0 ? "East Meadow" : "East Hampton",
      region: index < 2 ? "Central-Nassau" : "Eastern-Suffolk"
    }));
    const autocompleteCrews = [
      {
        crew_id: "CR-01",
        crew_name: "East Line Alpha",
        home_region: "Central-Nassau",
        status: "available",
        capability: "line",
        current_location: "Riverhead",
        shift_remaining_hours: 8,
        storm_ready: true,
        travel_minutes_to_selected_incident: 12,
        assigned_incidents: []
      },
      {
        crew_id: "CR-02",
        crew_name: "West Tree Beta",
        home_region: "Eastern-Suffolk",
        status: "available",
        capability: "vegetation",
        current_location: "East Meadow",
        shift_remaining_hours: 6,
        storm_ready: true,
        travel_minutes_to_selected_incident: 18,
        assigned_incidents: []
      }
    ];
    apiMocks.dashboard.mockResolvedValue({
      ...dashboard("base"),
      active_incidents: 8,
      top_incidents: autocompleteIncidents
    });
    apiMocks.incidents.mockResolvedValue(autocompleteIncidents);
    apiMocks.crews.mockResolvedValue(autocompleteCrews);
    render(<App />);

    const dashboardSearch = await screen.findByRole("combobox", { name: "Search Top 2 Incidents Shown" });
    fireEvent.change(dashboardSearch, { target: { value: "FDR-ES" } });
    expect(await screen.findByRole("option", { name: "FDR-ES-13, Feeder, 2 matches" })).toBeTruthy();
    expect(screen.queryByRole("option", { name: /FDR-ES-03/ })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Dispatch" }));
    const dispatchSearch = screen.getByRole("combobox", { name: "Dispatch incident queue search" });
    fireEvent.change(dispatchSearch, { target: { value: "FDR-ES" } });
    expect(await screen.findByRole("option", { name: "FDR-ES-03, Feeder, 6 matches" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    const activeRegion = screen.getByLabelText("Active incidents region");
    fireEvent.change(activeRegion, { target: { value: "Central-Nassau" } });
    const activeSearch = screen.getByRole("combobox", { name: "Active incidents search" });
    fireEvent.change(activeSearch, { target: { value: "FDR-ES" } });
    expect(await screen.findByRole("option", { name: "FDR-ES-13, Feeder, 2 matches" })).toBeTruthy();
    expect(screen.queryByRole("option", { name: /FDR-ES-03/ })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Storm Mode" }));
    const stormSearch = screen.getByRole("combobox", { name: "Storm exceptions search" });
    fireEvent.change(stormSearch, { target: { value: "East" } });
    expect(await screen.findByRole("group", { name: "Municipality" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "East Meadow, Municipality, 4 matches" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Crew Board" }));
    const crewSearch = screen.getByRole("combobox", { name: "Crew Board search" });
    fireEvent.change(crewSearch, { target: { value: "East" } });
    expect(await screen.findByRole("group", { name: "Crew Name" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Location" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "East Line Alpha, Crew Name, 1 match" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "East Meadow, Location, 1 match" })).toBeTruthy();
  });

  it("gives the Customers Out metric room for comma-formatted totals", async () => {
    apiMocks.dashboard.mockResolvedValue({ ...dashboard("base"), customers_out: 1_000_000 });
    render(<App />);

    const customersLabel = await screen.findByText("Customers Out");
    expect(customersLabel.closest(".metric")?.classList.contains("metric-customers-out")).toBe(true);
    expect(screen.getByText("1,000,000")).toBeTruthy();
  });

  it("shows all incidents and disables the dashboard limit for small scenarios", async () => {
    apiMocks.dashboard.mockResolvedValue(emptyDashboard("base"));
    apiMocks.incidents.mockResolvedValue([]);
    render(<App />);

    expect(await screen.findByRole("heading", { name: "All 0 Priority Incidents" })).toBeTruthy();
    expect(screen.getByLabelText("Dashboard incidents shown")).toHaveProperty("disabled", true);
    expect(screen.getByText("Showing 0 of 0 active incidents")).toBeTruthy();
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

  it("resets Crew Board pagination inputs when the scenario changes with the same crew count", async () => {
    const scenarioCrews = [
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
        crew_id: "CR-02",
        crew_name: "South Line Beta",
        home_region: "South",
        status: "assigned",
        capability: "line",
        current_location: "Fairview",
        shift_remaining_hours: 5,
        storm_ready: true,
        travel_minutes_to_selected_incident: 18,
        assigned_incidents: []
      }
    ];
    apiMocks.auditEvents.mockResolvedValue([]);
    apiMocks.crews.mockResolvedValue(scenarioCrews);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Crew Board" }));
    expect(await screen.findByText("Showing 1–2 of 2 matching crews (2 total)")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Crew Board status"), { target: { value: "available" } });
    expect(await screen.findByText("Showing 1–1 of 1 matching crews (2 total)")).toBeTruthy();
    const crewSearch = screen.getByRole("combobox", { name: "Crew Board search" });
    fireEvent.change(crewSearch, { target: { value: "CR" } });
    expect(await screen.findByRole("listbox")).toBeTruthy();

    const selector = screen.getByLabelText("Active synthetic scenario") as HTMLSelectElement;
    fireEvent.change(selector, { target: { value: "storm" } });

    await waitFor(() => expect(selector.value).toBe("storm"));
    expect((screen.getByLabelText("Crew Board status") as HTMLSelectElement).value).toBe("all");
    expect((screen.getByRole("combobox", { name: "Crew Board search" }) as HTMLInputElement).value).toBe("");
    expect(screen.queryByRole("listbox")).toBeNull();
    expect(screen.getByText("Showing 1–2 of 2 matching crews (2 total)")).toBeTruthy();
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
      active_incidents: 16,
      top_incidents: facetedIncidents
    });
    render(<App />);

    const verifyFacets = async (label: string) => {
      const regionFilter = await screen.findByLabelText(`${label} region`) as HTMLSelectElement;
      const criticalFacilityFilter = screen.getByLabelText(`${label} critical facility`) as HTMLSelectElement;
      expect(selectOption(criticalFacilityFilter, "yes")?.textContent).toBe("Critical facility (4)");
      expect(selectOption(criticalFacilityFilter, "no")?.textContent).toMatch(/^No critical facility \(/);
      fireEvent.change(regionFilter, { target: { value: "North" } });
      const severityFilter = screen.getByLabelText(`${label} severity`) as HTMLSelectElement;
      expect(selectOption(severityFilter, "critical")?.textContent).toBe("Critical (1)");
      expect(selectOption(severityFilter, "high")?.textContent).toBe("High (1)");
      expect(selectOption(severityFilter, "medium")?.disabled).toBe(true);

      fireEvent.change(severityFilter, { target: { value: "critical" } });
      expect(selectOption(regionFilter, "North")?.textContent).toBe("North (1)");
      expect(selectOption(regionFilter, "South")?.textContent).toBe("South (1)");
      expect(selectOption(regionFilter, "East")?.disabled).toBe(true);
      expect(selectOption(criticalFacilityFilter, "yes")?.textContent).toBe("Critical facility (1)");
      expect(selectOption(criticalFacilityFilter, "no")?.disabled).toBe(true);
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
    expect((await screen.findByRole("button", { name: "INC-1001" })).getAttribute("aria-pressed")).toBe("true");

    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));
    expect(screen.getByLabelText("Copilot question")).toBeTruthy();
  });

  it("restores and persists the bounded desktop navigation width", async () => {
    window.localStorage.setItem("aida.ui.sidebar-width.v1", "310");
    render(<App />);

    const separator = screen.getByRole("separator", { name: "Resize primary navigation" });
    expect(separator.getAttribute("aria-valuenow")).toBe("310");
    fireEvent.keyDown(separator, { key: "ArrowRight" });

    await waitFor(() => expect(window.localStorage.getItem("aida.ui.sidebar-width.v1")).toBe("320"));
    expect(separator.getAttribute("aria-valuenow")).toBe("320");
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

    await openRecommendations();
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

    await openRecommendations();
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

    await openRecommendations();
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
    await screen.findByRole("region", { name: "Active incidents" });
    expect(screen.queryByRole("complementary", { name: "Incident details INC-1001" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "INC-1001" }));
    expect(await screen.findByLabelText("Incident details INC-1001")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "North Line Alpha (CR-01)" }));
    const crewDetails = await screen.findByLabelText("Crew details CR-01");
    fireEvent.click(within(crewDetails).getByRole("button", { name: "INC-1001 · Millbrook" }));
    expect(await screen.findByLabelText("Incident details INC-1001")).toBeTruthy();
  });

  it("opens incident details in place from Dashboard and Dispatch rows", async () => {
    render(<App />);

    const dashboardTable = await screen.findByRole("region", { name: "Priority dispatch queue" });
    const dashboardRow = within(dashboardTable).getByRole("row", { name: "Open incident details for INC-1001" });
    expect(dashboardRow.tabIndex).toBe(0);
    fireEvent.click(dashboardRow);

    expect(await screen.findByRole("complementary", { name: "Incident details INC-1001" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Dashboard" }).getAttribute("aria-current")).toBe("page");
    fireEvent.click(screen.getByRole("button", { name: "Close Incident details" }));

    fireEvent.click(screen.getByRole("button", { name: "Dispatch" }));
    const dispatchTable = screen.getByRole("region", { name: "Dispatch incident queue" });
    const dispatchRow = within(dispatchTable).getByRole("row", { name: "Open incident details for INC-1001" });
    dispatchRow.focus();
    fireEvent.keyDown(dispatchRow, { key: "Enter" });

    expect(await screen.findByRole("complementary", { name: "Incident details INC-1001" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Dispatch" }).getAttribute("aria-current")).toBe("page");
    fireEvent.click(screen.getByRole("button", { name: "Close Incident details" }));
    await waitFor(() => expect(dispatchRow).toBe(document.activeElement));

    fireEvent.keyDown(dispatchRow, { key: " " });
    expect(await screen.findByRole("complementary", { name: "Incident details INC-1001" })).toBeTruthy();
  });

  it("updates and dismisses incident details without clearing selection", async () => {
    const secondIncident = {
      ...baseIncident,
      incident_id: "INC-2002",
      municipality: "Southport",
      feeder: "FDR-2"
    };
    apiMocks.incidents.mockResolvedValue([baseIncident, secondIncident]);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    const firstTrigger = await screen.findByRole("button", { name: "INC-1001" });
    fireEvent.click(firstTrigger);
    expect(await screen.findByText("INC-1001 · Millbrook")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "INC-2002" }));
    expect(await screen.findByText("INC-2002 · Southport")).toBeTruthy();
    const secondTrigger = screen.getByRole("button", { name: "INC-2002" });
    fireEvent.click(screen.getByRole("button", { name: "Close Incident details" }));

    expect(screen.queryByRole("complementary", { name: "Incident details INC-2002" })).toBeNull();
    await waitFor(() => expect(secondTrigger).toBe(document.activeElement));
    expect(secondTrigger.getAttribute("aria-pressed")).toBe("true");
  });

  it("closes incident details when the active scenario changes", async () => {
    apiMocks.auditEvents.mockResolvedValue([]);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    fireEvent.click(await screen.findByRole("button", { name: "INC-1001" }));
    expect(await screen.findByRole("complementary", { name: "Incident details INC-1001" })).toBeTruthy();

    const selector = screen.getByLabelText("Active synthetic scenario") as HTMLSelectElement;
    fireEvent.change(selector, { target: { value: "storm" } });

    await waitFor(() => expect(apiMocks.activateScenario).toHaveBeenCalledWith("storm"));
    expect(screen.queryByRole("complementary", { name: "Incident details INC-1001" })).toBeNull();
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
    expect(screen.getAllByRole("columnheader")).toHaveLength(9);
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

    const search = screen.getByRole("combobox", { name: "Active incidents search" });
    fireEvent.change(search, { target: { value: "Municipality 55" } });
    fireEvent.click(await screen.findByRole("option", { name: "Municipality 55, Municipality, 1 match" }));
    expect((search as HTMLInputElement).value).toBe("Municipality 55");
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

    await openRecommendations();
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
    const copilotContext = screen.getByRole("status", { name: "Copilot context" });
    expect(copilotContext.textContent).toContain("Selected incident: INC-1001 · Millbrook");
    expect(copilotContext.textContent).toContain("Selected crew: None");
    expect(
      screen.getByText(/For an exact complete-scenario calculation, name both the measure and population/)
    ).toBeTruthy();
    expect(
      screen.getByText(/Open-ended summaries use grounded AI over a bounded context disclosed with each response/)
    ).toBeTruthy();
    expect(
      screen.getByRole("button", {
        name: "How many customers are out across all active incidents?"
      })
    ).toBeTruthy();
    expect(
      screen.getByRole("button", {
        name: "How many crews are available in the active scenario?"
      })
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Break down critical facilities by level." })
    ).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Ask Copilot" }));
    expect(screen.getByRole("button", { name: "Asking..." })).toBeTruthy();
    rejectChat(new Error("Copilot service unavailable"));

    expect(await screen.findByText(/Unable to reach Copilot: Copilot service unavailable/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Ask Copilot" })).toBeTruthy();
  });

  it("renders Copilot as a persistent full-width workspace without an expand control", async () => {
    render(<App />);

    await screen.findByLabelText("Active synthetic scenario");
    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));

    const heading = screen.getByRole("heading", { level: 2, name: "AI Copilot" });
    const workspace = heading.closest("section");
    expect(workspace?.classList.contains("copilot")).toBe(true);
    expect(workspace?.parentElement?.id).toBe("main-content");
    expect(screen.getByRole("status", { name: "Copilot context" })).toBeTruthy();
    expect(screen.getByLabelText("Copilot question")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /^(Expand|Restore) AI Copilot workspace$/ })).toBeNull();
  });

  it("clears only the Copilot composer and disables Clear for blank input", async () => {
    apiMocks.chat.mockResolvedValue({
      answer: "Five crews are available.",
      intent: "crew_availability",
      source: "synthetic-demo-data",
      safety_note: "Advisory only.",
      execution_mode: "local_query",
      scenario_id: "base",
      generated_at: "2026-08-21T12:00:00Z",
      request_time: {
        received_at: "2026-08-21T12:00:00Z",
        timezone: "UTC",
        source: "backend_server_clock",
        clock_skew: "not_measured"
      },
      data_snapshot_at: "2026-08-21T11:45:00Z",
      provider: null,
      model: null,
      warning: null,
      evidence: []
    });
    render(<App />);

    await screen.findByLabelText("Active synthetic scenario");
    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));
    const composer = screen.getByLabelText("Copilot question") as HTMLTextAreaElement;
    const clear = screen.getByRole("button", { name: "Clear" }) as HTMLButtonElement;
    const ask = screen.getByRole("button", { name: "Ask Copilot" });

    expect(composer.value).toBe("What should I focus on first?");
    expect(clear.disabled).toBe(false);
    expect(clear.nextElementSibling).toBe(ask);
    clear.focus();
    expect(clear).toBe(document.activeElement);
    fireEvent.click(clear);
    expect(composer.value).toBe("");
    expect(clear.disabled).toBe(true);

    fireEvent.change(composer, { target: { value: "   " } });
    expect(clear.disabled).toBe(true);
    fireEvent.change(composer, { target: { value: "How many crews are available?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask Copilot" }));
    expect(await screen.findByText("Five crews are available.")).toBeTruthy();

    fireEvent.change(composer, { target: { value: "Start a new question" } });
    fireEvent.click(clear);
    expect(composer.value).toBe("");
    expect(screen.getByText("Five crews are available.")).toBeTruthy();
    expect(screen.getAllByText("How many crews are available?")).toHaveLength(1);
  });

  it("shows Copilot execution mode, snapshot, and evidence metadata", async () => {
    apiMocks.chat.mockResolvedValue({
      answer: "INC-1001 is the local top priority.",
      intent: "priority_focus",
      source: "synthetic-demo-data",
      safety_note: "Advisory only.",
      execution_mode: "local_query",
      scenario_id: "base",
      generated_at: "2026-08-21T12:00:00Z",
      request_time: {
        received_at: "2026-08-21T12:00:00Z",
        timezone: "UTC",
        source: "backend_server_clock",
        clock_skew: "not_measured"
      },
      data_snapshot_at: "2026-08-21T11:45:00Z",
      provider: null,
      model: null,
      warning: null,
      response_scope: "Local scenario records for the stated query scope",
      evidence: [
        { source_type: "incident", record_id: "INC-1001", label: "Millbrook" }
      ]
    });
    render(<App />);

    await screen.findByLabelText("Active synthetic scenario");
    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));
    fireEvent.click(screen.getByRole("button", { name: "Ask Copilot" }));

    expect(await screen.findByText("INC-1001 is the local top priority.")).toBeTruthy();
    const requestTime = screen.getByText("Request Received 08/21/2026 12:00 UTC");
    expect(requestTime.tagName).toBe("TIME");
    expect(requestTime.getAttribute("datetime")).toBe("2026-08-21T12:00:00Z");
    expect(screen.getByText("Local scenario query")).toBeTruthy();
    expect(screen.getByText("Scenario: base")).toBeTruthy();
    expect(screen.getByText("Snapshot: 2026-08-21T11:45:00Z")).toBeTruthy();
    const scope = screen.getByLabelText("Response scope");
    expect(scope.textContent).toBe(
      "Response scope: Local scenario records for the stated query scope"
    );
    expect(screen.getByText("Evidence (1)")).toBeTruthy();
  });

  it("clears response-scope metadata when the active scenario changes", async () => {
    apiMocks.auditEvents.mockResolvedValue([]);
    apiMocks.chat.mockResolvedValue({
      answer: "Five crews are available.",
      intent: "crew_status",
      source: "synthetic-demo-data",
      safety_note: "Advisory only.",
      execution_mode: "local_query",
      scenario_id: "base",
      generated_at: "2026-08-21T12:00:00Z",
      request_time: null,
      data_snapshot_at: null,
      provider: null,
      model: null,
      warning: null,
      response_scope: "Complete crew calculation: 5 crews evaluated",
      evidence: []
    });
    render(<App />);

    const scenarioSelector = await screen.findByLabelText("Active synthetic scenario");
    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));
    fireEvent.click(screen.getByRole("button", { name: "Ask Copilot" }));
    expect(await screen.findByLabelText("Response scope")).toBeTruthy();

    fireEvent.change(scenarioSelector, { target: { value: "storm" } });

    await waitFor(() => expect(screen.queryByLabelText("Response scope")).toBeNull());
    expect(
      screen.getByText(/For an exact complete-scenario calculation, name both the measure and population/)
    ).toBeTruthy();
  });

  it("renders deterministic all-incident customer aggregates", async () => {
    const question = "How many customers are out across all active incidents?";
    apiMocks.chat.mockResolvedValue({
      answer: [
        "## Customer outage aggregate",
        "",
        "24 active incidents report **24,427 customers out** in scenario `long-island-copilot-demo`.",
        "",
        "Ranking-withheld incidents contribute 0 record(s) to this complete visible-incident calculation; 0 appear in the displayed subset.",
        "",
        "### Highest-priority rankable incidents (showing 10 of 24)",
        "",
        "| ESD ID | Village | Customers out | Status |",
        "| --- | --- | ---: | --- |",
        "| ESD-20260821-0002 | Arverne | 5,000 | unassigned |"
      ].join("\n"),
      intent: "all_incident_customer_aggregate",
      source: "synthetic-demo-data",
      safety_note: "Advisory only.",
      execution_mode: "local_query",
      scenario_id: "long-island-copilot-demo",
      generated_at: "2026-09-13T13:29:00Z",
      request_time: {
        received_at: "2026-09-13T13:29:00Z",
        timezone: "UTC",
        source: "backend_server_clock",
        clock_skew: "not_measured"
      },
      data_snapshot_at: "2026-08-21T07:00:00-04:00",
      provider: null,
      model: null,
      warning: null,
      evidence: [
        {
          source_type: "dashboard",
          record_id: "long-island-copilot-demo",
          label: "Complete customer-outage aggregate: 24 active incidents"
        }
      ]
    });
    render(<App />);

    await screen.findByLabelText("Active synthetic scenario");
    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));
    fireEvent.change(screen.getByLabelText("Copilot question"), {
      target: { value: question }
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask Copilot" }));

    expect(
      await screen.findByRole("heading", { name: "Customer outage aggregate" })
    ).toBeTruthy();
    expect(
      screen.getByText((_, element) =>
        element?.tagName === "P"
        && element.textContent?.includes("24 active incidents report 24,427 customers out") === true
      )
    ).toBeTruthy();
    expect(screen.getByText("24,427 customers out")).toBeTruthy();
    expect(
      screen.getByRole("heading", {
        name: "Highest-priority rankable incidents (showing 10 of 24)"
      })
    ).toBeTruthy();
    expect(screen.getByRole("table")).toBeTruthy();
    expect(screen.getByText("Local scenario query")).toBeTruthy();
    expect(apiMocks.chat).toHaveBeenCalledWith(question, "INC-1001", undefined);
  });

  it("renders mixed-source PSEG reference calculations and evidence", async () => {
    const question = "What percent of customers in Melville are affected?";
    apiMocks.chat.mockResolvedValue({
      answer: [
        "## Mixed-source outage percentage",
        "",
        "**420 synthetic customers out ÷ 8,513 static customers served = 4.93%** for Suffolk → Huntington → Melville.",
        "",
        "- **Numerator:** Complete active-scenario aggregate from `long-island-copilot-demo`; snapshot 2026-08-24T21:13:51Z.",
        "- **Denominator:** SME-approved static PSEG Long Island reference; source timestamp 2026-09-15T23:41:56Z.",
        "",
        "This deliberately mixes synthetic outage data with a static reference denominator. It is not a live PSEG Long Island outage percentage."
      ].join("\n"),
      intent: "reference_outage_percentage",
      source: "synthetic-demo-data + approved-static-reference",
      safety_note: "Advisory only.",
      execution_mode: "local_query",
      scenario_id: "long-island-copilot-demo",
      generated_at: "2026-09-15T23:55:00Z",
      request_time: {
        received_at: "2026-09-15T23:55:00Z",
        timezone: "UTC",
        source: "backend_server_clock",
        clock_skew: "not_measured"
      },
      data_snapshot_at: "2026-08-24T21:13:51Z",
      provider: null,
      model: null,
      warning: null,
      response_scope: "Complete aligned area calculation for Suffolk → Huntington → Melville",
      evidence: [
        {
          source_type: "pseg_reference",
          record_id: "pseg-li-5b9a7b6b1be35e55c535",
          label: "Approved static reference: Melville; 8,513 customers served"
        },
        {
          source_type: "incident",
          record_id: "ESD-20260821-0004",
          label: "Synthetic numerator record: Melville, 420 customers out"
        }
      ]
    });
    render(<App />);

    await screen.findByLabelText("Active synthetic scenario");
    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));
    fireEvent.change(screen.getByLabelText("Copilot question"), {
      target: { value: question }
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask Copilot" }));

    expect(
      await screen.findByRole("heading", { name: "Mixed-source outage percentage" })
    ).toBeTruthy();
    expect(
      screen.getByText((_, element) =>
        element?.tagName === "STRONG"
        && element.textContent?.includes("4.93%") === true
      )
    ).toBeTruthy();
    expect(
      screen.getByText(/It is not a live PSEG Long Island outage percentage/)
    ).toBeTruthy();
    expect(screen.getByText("Evidence (2)")).toBeTruthy();
    expect(screen.getByText("Local scenario query")).toBeTruthy();
    expect(apiMocks.chat).toHaveBeenCalledWith(question, "INC-1001", undefined);
  });

  it("renders POC-025 tables with explicit population and subset headings", async () => {
    const question = "Break down critical facilities by level.";
    apiMocks.chat.mockResolvedValue({
      answer: [
        "## Critical-facility levels",
        "",
        "### Complete visible affected-incident counts (all 15 critical-facility incidents)",
        "",
        "| Applied level | Affected incidents | Score contribution |",
        "| --- | ---: | ---: |",
        "| Level 1 | 5 | +120 |",
        "| Level 2 | 3 | +80 |",
        "| Level 3 | 7 | +40 |",
        "| Unknown/withheld | 0 | Withheld |",
        "",
        "### Complete matched facility-record counts (all 11 matched records)",
        "",
        "| Source facility level | Facility records |",
        "| --- | ---: |",
        "| Level 1 | 5 |",
        "| Level 2 | 3 |",
        "| Level 3 | 3 |",
        "| Unknown | 0 |",
        "",
        "### Priority-ordered visible critical-facility incidents (rankable first; withheld by incident ID; showing 10 of 15)",
        "",
        "| ESD ID | Village | Applied level |",
        "| --- | --- | --- |",
        "| ESD-20260810-0661 | Riverhead | Level 1 |"
      ].join("\n"),
      intent: "critical_facility_levels",
      source: "synthetic-demo-data",
      safety_note: "Advisory only.",
      execution_mode: "local_query",
      scenario_id: "august-storm-preview-v2",
      generated_at: "2026-09-14T13:29:00Z",
      request_time: {
        received_at: "2026-09-14T13:29:00Z",
        timezone: "UTC",
        source: "backend_server_clock",
        clock_skew: "not_measured"
      },
      data_snapshot_at: null,
      provider: null,
      model: null,
      warning: null,
      evidence: []
    });
    render(<App />);

    await screen.findByLabelText("Active synthetic scenario");
    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));
    fireEvent.click(screen.getByRole("button", { name: question }));
    fireEvent.click(screen.getByRole("button", { name: "Ask Copilot" }));

    expect(
      await screen.findByRole("heading", {
        name: "Complete visible affected-incident counts (all 15 critical-facility incidents)"
      })
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", {
        name: "Complete matched facility-record counts (all 11 matched records)"
      })
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", {
        name: "Priority-ordered visible critical-facility incidents (rankable first; withheld by incident ID; showing 10 of 15)"
      })
    ).toBeTruthy();
    expect(screen.getAllByRole("table")).toHaveLength(3);
    for (const tableRegion of screen.getAllByRole("region", { name: "Copilot response table" })) {
      expect(tableRegion.classList.contains("copilot-table-scroll")).toBe(true);
      expect(tableRegion.parentElement?.classList.contains("copilot-markdown")).toBe(true);
    }
    expect(apiMocks.chat).toHaveBeenCalledWith(question, "INC-1001", undefined);
  });

  it("renders safe, semantic Markdown in Copilot responses", async () => {
    apiMocks.chat.mockResolvedValue({
      answer: [
        "# Operational impact",
        "",
        "A concise **grounded** summary with `scenario data`.",
        "",
        "## Key impacts",
        "",
        "- **Safety:** Downed wire controls are required.",
        "",
        "| Incident | Customers |",
        "| --- | ---: |",
        "| INC-1001 | 500 |",
        "",
        "[Source](https://example.com/evidence) [Run script](javascript:alert('unsafe'))<br><script>window.injected = true</script>"
      ].join("\n"),
      intent: "grounded_synthesis",
      source: "synthetic-demo-data",
      safety_note: "Advisory only.",
      execution_mode: "llm_grounded",
      scenario_id: "base",
      generated_at: "2026-08-21T12:00:00Z",
      data_snapshot_at: null,
      provider: "ollama",
      model: "gpt-oss:120b",
      warning: null,
      response_scope: (
        "Bounded grounded context: 1 selected incident + 5 ranked incidents + 6 crews + " +
        "8 critical-facility records + 4 weather records (24 of 30 record limit used)"
      ),
      evidence: []
    });
    render(<App />);

    await screen.findByLabelText("Active synthetic scenario");
    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));
    fireEvent.click(screen.getByRole("button", { name: "Ask Copilot" }));

    expect(await screen.findByRole("heading", { level: 3, name: "Operational impact" })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 4, name: "Key impacts" })).toBeTruthy();
    expect(screen.getByText("grounded").tagName).toBe("STRONG");
    expect(screen.getByText("scenario data").tagName).toBe("CODE");
    expect(screen.getByRole("listitem")).toBeTruthy();
    expect(screen.getByRole("table")).toBeTruthy();
    expect(screen.getByRole("region", { name: "Copilot response table" })).toBeTruthy();
    const sourceLink = screen.getByRole("link", { name: "Source" });
    expect(sourceLink.getAttribute("href")).toBe("https://example.com/evidence");
    expect(sourceLink.getAttribute("rel")).toBe("noopener noreferrer");
    expect(screen.queryByRole("link", { name: "Run script" })).toBeNull();
    expect(screen.getByText("Run script")).toBeTruthy();
    expect(document.querySelector("script")).toBeNull();
    expect(screen.queryByText("<br>")).toBeNull();
    expect(screen.getByLabelText("Response scope").textContent).toContain(
      "Bounded grounded context"
    );
  });

  it("shows an explicit rule-based fallback warning", async () => {
    apiMocks.chat.mockResolvedValue({
      answer: "Rule-based storm summary.",
      intent: "scenario_summary",
      source: "synthetic-demo-data",
      safety_note: "Advisory only.",
      execution_mode: "rule_based_fallback",
      scenario_id: "base",
      generated_at: "2026-08-21T12:00:00Z",
      data_snapshot_at: null,
      provider: null,
      model: null,
      warning: "AI provider unavailable; using the rule-based scenario summary.",
      response_scope: (
        "Rule-based scenario summary: complete dashboard totals plus 8 rankable incidents evaluated"
      ),
      evidence: []
    });
    render(<App />);

    await screen.findByLabelText("Active synthetic scenario");
    fireEvent.click(screen.getByRole("button", { name: "AI Copilot" }));
    fireEvent.click(screen.getByRole("button", { name: "Ask Copilot" }));

    expect(await screen.findByText("Rule-based fallback")).toBeTruthy();
    expect(
      screen.getByText("AI provider unavailable; using the rule-based scenario summary.")
    ).toBeTruthy();
    expect(screen.getByLabelText("Response scope").textContent).toContain(
      "complete dashboard totals"
    );
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
  it("opens map incidents in the existing detail view and clears map filters on scenario change", async () => {
    vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
    apiMocks.auditEvents.mockResolvedValue([]);
    apiMocks.incidents.mockResolvedValue([{...baseIncident, region: "North"}]);
    render(<App />);
    await screen.findByRole("button", {name: "Open recommendations"});
    fireEvent.click(screen.getByRole("button", {name: "Operations Map"}));
    fireEvent.click(await screen.findByRole("button", {name: /! · INC-1001/}));
    fireEvent.click(screen.getByRole("button", {name: "Open incident details"}));
    expect(await screen.findByRole("complementary", {name: "Incident details INC-1001"})).toBeTruthy();
    fireEvent.click(screen.getByRole("button", {name: "Operations Map"}));
    fireEvent.change(await screen.findByRole("combobox", {name: "Search records"}), {target: {value: "no match"}});
    expect(screen.getByText("No records match these filters.")).toBeTruthy();
    apiMocks.activateScenario.mockResolvedValue({...stormScenario, is_active: true});
    fireEvent.change(screen.getByLabelText("Active synthetic scenario"), {target: {value: "storm"}});
    await screen.findByText("Major Storm activated.");
    expect((screen.getByRole("combobox", {name: "Search records"}) as HTMLInputElement).value).toBe("");
    expect(screen.getByRole("button", {name: /! · INC-1001/})).toBeTruthy();
    expect(apiMocks.recordRecommendationAction).not.toHaveBeenCalled();
  });

  it("shows incidents on the map from every operational incident view", async () => {
    vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
    apiMocks.incidents.mockResolvedValue([{ ...baseIncident, region: "North", latitude: 40.77, longitude: -73.52 }]);
    render(<App />);

    for (const viewName of ["Dashboard", "Dispatch", "Incidents", "Storm Mode"]) {
      if (viewName !== "Dashboard") fireEvent.click(screen.getByRole("button", { name: viewName }));
      const showOnMap = await screen.findByRole("button", { name: "Show incident INC-1001 on map" });
      expect(showOnMap.getAttribute("title")).toBe("Show on map");
      expect(showOnMap.textContent).toBe("");
      expect(showOnMap.querySelector("svg")).toBeTruthy();
      expect(showOnMap.closest(".incident-map-link")?.querySelector(".incident-select-button")?.textContent).toBe("INC-1001");
      fireEvent.click(showOnMap);
      expect(await screen.findByText("Showing incident INC-1001 on the map.")).toBeTruthy();
      expect(screen.getByRole("button", { name: "Open incident details" })).toBeTruthy();
      expect(screen.queryByRole("complementary", { name: "Incident details INC-1001" })).toBeNull();
    }
  });

  it("keeps municipality and feeder actions grouped across incident views and populated states", async () => {
    const assignedCrew = {
      crew_id: "CR-048",
      crew_name: "Eastern Suffolk Contractor Crew With A Long Name",
      assignment_id: "assignment-048",
      assigned_at: "2026-09-20T12:00:00Z"
    };
    const populatedIncident = {
      ...baseIncident,
      incident_id: "INC-048-A",
      municipality: "Westhampton Beach-Southampton",
      feeder: "FDR-EASTERN-SUFFOLK-048",
      assigned_crews: [assignedCrew],
      current_decision: recordedDecision
    };
    const sparseIncident = {
      ...baseIncident,
      incident_id: "INC-048-B",
      municipality: "East Farmingdale",
      feeder: "FDR-048",
      assigned_crews: [],
      current_decision: null
    };
    const incidents = [populatedIncident, sparseIncident];
    apiMocks.incidents.mockResolvedValue(incidents);
    apiMocks.dashboard.mockResolvedValue({
      ...dashboard("base"),
      active_incidents: 8,
      top_incidents: incidents
    });
    render(<App />);

    for (const viewName of ["Dashboard", "Dispatch", "Incidents", "Storm Mode"]) {
      if (viewName !== "Dashboard") fireEvent.click(screen.getByRole("button", { name: viewName }));

      for (const incident of incidents) {
        const group = await screen.findByRole("group", {
          name: `Municipality and feeder for ${incident.incident_id}`
        });
        expect(group.classList.contains("incident-related-location")).toBe(true);
        expect(within(group).getByRole("button", { name: incident.municipality })).toBeTruthy();
        expect(within(group).getByRole("button", { name: incident.feeder })).toBeTruthy();
        expect(group.querySelectorAll("svg")).toHaveLength(1);
      }
    }
  });

  it("returns to an entity-navigation source with filters, page, selection, and focus restored", async () => {
    vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
    const manyIncidents = Array.from({ length: 55 }, (_, index) => ({
      ...baseIncident,
      incident_id: `INC-${String(1001 + index)}`,
      municipality: `Municipality ${index + 1}`,
      region: index % 2 === 0 ? "North" : "South",
      customers_out: 55 - index,
      latitude: 40.7 + index / 1000,
      longitude: -73.5
    }));
    apiMocks.incidents.mockResolvedValue(manyIncidents);
    apiMocks.dashboard.mockResolvedValue({ ...dashboard("base"), active_incidents: 55, top_incidents: manyIncidents.slice(0, 5) });
    apiMocks.auditEvents.mockResolvedValue([]);
    render(<App />);

    await screen.findByLabelText("Active synthetic scenario");
    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    fireEvent.click(await screen.findByRole("button", { name: "Next Active incidents page" }));
    expect(screen.getByText("Page 2 of 2")).toBeTruthy();

    const mapAction = screen.getAllByRole("button", { name: /Show incident .* on map/ })[0];
    const accessibleName = mapAction.getAttribute("aria-label")!;
    fireEvent.click(mapAction);

    expect(await screen.findByRole("button", { name: "Return to Incidents" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Return to Incidents" }));

    expect(await screen.findByText("Page 2 of 2")).toBeTruthy();
    const restoredAction = screen.getByRole("button", { name: accessibleName });
    await waitFor(() => expect(document.activeElement).toBe(restoredAction));
  });

  it("restores a non-default Dashboard selection and its open detail context", async () => {
    vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
    const secondIncident = {
      ...baseIncident,
      incident_id: "INC-1002",
      municipality: "Riverhead",
      region: "East",
      latitude: 40.92,
      longitude: -72.66
    };
    apiMocks.auditEvents.mockResolvedValue([]);
    apiMocks.incidents.mockResolvedValue([{ ...baseIncident, region: "North", latitude: 40.77, longitude: -73.52 }, secondIncident]);
    apiMocks.dashboard.mockResolvedValue({
      ...dashboard("base"),
      active_incidents: 2,
      customers_out: 200,
      top_incidents: [{ ...baseIncident, region: "North", latitude: 40.77, longitude: -73.52 }, secondIncident]
    });
    render(<App />);

    fireEvent.change(await screen.findByRole("combobox", { name: "Dashboard incidents shown" }), { target: { value: "100" } });
    fireEvent.click(await screen.findByRole("row", { name: "Open incident details for INC-1002" }));
    expect(await screen.findByRole("complementary", { name: "Incident details INC-1002" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Show incident INC-1002 on map" }));
    fireEvent.click(await screen.findByRole("button", { name: "Return to Dashboard" }));

    expect(await screen.findByRole("complementary", { name: "Incident details INC-1002" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "INC-1002" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("discards the return snapshot when the active scenario changes", async () => {
    vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
    apiMocks.auditEvents.mockResolvedValue([]);
    apiMocks.incidents.mockResolvedValue([{ ...baseIncident, region: "North", latitude: 40.77, longitude: -73.52 }]);
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Show incident INC-1001 on map" }));
    expect(await screen.findByRole("button", { name: "Return to Dashboard" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Active synthetic scenario"), { target: { value: "storm" } });

    await screen.findByText("Major Storm activated.");
    expect(screen.queryByRole("button", { name: "Return to Dashboard" })).toBeNull();
  });

  it("shows mapped and unmapped crews on the map from Crew Board", async () => {
    vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
    const mappedCrew = {
      crew_id: "CR-01",
      crew_name: "North Line Alpha",
      home_region: "North",
      status: "available",
      capability: "line",
      current_location: "Millbrook",
      shift_remaining_hours: 8,
      storm_ready: true,
      travel_minutes_to_selected_incident: 10,
      assigned_incidents: [],
      map_location: { latitude: 40.77, longitude: -73.52, village: "Millbrook", reference_id: "village-1", precision: "village_center" }
    };
    apiMocks.crews.mockResolvedValue([mappedCrew, { ...mappedCrew, crew_id: "CR-02", crew_name: "Unmapped Crew", map_location: null }]);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Crew Board" }));
    const mappedAction = await screen.findByRole("button", { name: "Show crew CR-01 on map" });
    expect(mappedAction.closest(".crew-card-primary")).toBeTruthy();
    expect(mappedAction.getAttribute("title")).toBe("Show on map");
    expect(mappedAction.textContent).toBe("");
    expect(mappedAction.querySelector("svg")).toBeTruthy();
    fireEvent.click(mappedAction);
    expect(await screen.findByText("Showing crew CR-01 on the map.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open crew details" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Crew Board" }));
    fireEvent.click(await screen.findByRole("button", { name: "Show crew CR-02 on map" }));
    expect(await screen.findByText("Crew CR-02 is selected, but no map location is available.")).toBeTruthy();
    expect(screen.getByText("Location unavailable — this record is not plotted.")).toBeTruthy();
  });

  it("uses contextual destinations for exact related-record filters", async () => {
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
      assigned_incidents: [{ incident_id: "INC-1001", assignment_id: "a-1", assigned_at: "2026-09-19T10:00:00Z", municipality: "Millbrook", severity: "critical" }],
      map_location: null
    };
    const assignedSummary = { crew_id: "CR-01", crew_name: "North Line Alpha", assignment_id: "a-1", assigned_at: "2026-09-19T10:00:00Z" };
    apiMocks.crews.mockResolvedValue([assignedCrew]);
    apiMocks.incidents.mockResolvedValue([
      { ...baseIncident, region: "North", assigned_crews: [assignedSummary], matched_critical_facility_ids: ["CF-1"] },
      { ...baseIncident, incident_id: "INC-1002", region: "North", feeder: "FDR-2", assigned_crews: [] },
      { ...baseIncident, incident_id: "INC-1003", region: "North", municipality: "Millbrook Heights", feeder: "FDR-1A", assigned_crews: [] }
    ]);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    fireEvent.click(await screen.findByRole("button", { name: "INC-1001" }));
    const incidentDetails = await screen.findByRole("complementary", { name: "Incident details INC-1001" });
    fireEvent.click(within(incidentDetails).getByRole("button", { name: "Millbrook" }));

    expect(await screen.findByText("Related records · Municipality: Millbrook")).toBeTruthy();
    expect(screen.getByText(/of 2 matching incidents \(3 total\)/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Clear related filter" }));

    fireEvent.click(screen.getByRole("button", { name: "INC-1001" }));
    const reopenedDetails = await screen.findByRole("complementary", { name: "Incident details INC-1001" });
    fireEvent.click(within(reopenedDetails).getByRole("button", { name: "View assigned crew (1)" }));

    expect(await screen.findByText("Related records · Assigned to INC-1001")).toBeTruthy();
    expect(screen.getByRole("button", { name: /North Line Alpha/ })).toBeTruthy();
  });

  it("restores state for same-view related-record navigation", async () => {
    apiMocks.auditEvents.mockResolvedValue([]);
    apiMocks.incidents.mockResolvedValue([
      { ...baseIncident, region: "North" },
      { ...baseIncident, incident_id: "INC-1002", region: "North", feeder: "FDR-2" }
    ]);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
    const search = await screen.findByRole("combobox", { name: "Active incidents search" });
    fireEvent.change(search, { target: { value: "INC-1001" } });
    const municipalityAction = screen.getByRole("button", { name: "Millbrook" });
    fireEvent.click(municipalityAction);

    expect(await screen.findByText("Related records · Municipality: Millbrook")).toBeTruthy();
    expect((search as HTMLInputElement).value).toBe("");
    fireEvent.click(screen.getByRole("button", { name: "Return to Incidents" }));

    await waitFor(() => expect((screen.getByRole("combobox", { name: "Active incidents search" }) as HTMLInputElement).value).toBe("INC-1001"));
    expect(screen.queryByText("Related records · Municipality: Millbrook")).toBeNull();
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole("button", { name: "Millbrook" })));
  });

});
