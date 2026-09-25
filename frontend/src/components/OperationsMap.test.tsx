import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import L from "leaflet";
import OperationsMap, { mapRecords } from "./OperationsMap";
import type { Crew, Incident } from "../types";

const incident: Incident = {
  incident_id: "INC-1", municipality: "Hicksville", region: "Central-Nassau", feeder: "F1",
  severity: "critical", status: "new", customers_out: 25, critical_facility: false,
  hazard: "wire", required_skill: "line", age_minutes: 3, latitude: 40.77, longitude: -73.52,
  etr: "Unknown", assigned_crews: [], current_decision: null
};
const crew: Crew = {
  crew_id: "C1", crew_name: "Line crew 1", current_location: "Hicksville", home_region: "Central-Nassau",
  status: "available", capability: "line", shift_remaining_hours: 5, storm_ready: true,
  travel_minutes_to_selected_incident: 10, assigned_incidents: [],
  map_location: { latitude: 40.77, longitude: -73.52, village: "Hicksville", reference_id: "village-1", precision: "village_center" }
};
const assignment = { assignment_id: "a-1", incident_id: "INC-1", assigned_at: "2026-09-21T00:00:00Z", municipality: "Hicksville", severity: "critical" };
const assignedCrew = { ...crew, status: "assigned", assigned_incidents: [assignment], map_location: { ...crew.map_location!, latitude: 40.8 } };
const assignedIncident = { ...incident, assigned_crews: [{ crew_id: "C1", crew_name: "Line crew 1", assignment_id: "a-1", assigned_at: "2026-09-21T00:00:00Z" }] };

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1024);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(600);
  vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("Operations Map", () => {
  it("uses supplied crew centers and excludes missing or invalid coordinates without losing records", () => {
    const records = mapRecords([
      incident, { ...incident, incident_id: "invalid", latitude: NaN },
      { ...incident, incident_id: "zero", latitude: 0, longitude: 0 }
    ], [crew, { ...crew, crew_id: "unknown", map_location: null }]);
    expect(records).toHaveLength(5);
    expect(records.filter((r) => r.coordinates)).toHaveLength(2);
    expect(records[3].coordinates).toEqual([40.77, -73.52]);
    expect(records[4].coordinates).toBeNull();
  });

  it("links selected incidents and crews to existing workflows and filters layers", () => {
    const onNavigate = vi.fn();
    render(<OperationsMap incidents={[incident]} crews={[crew]} onNavigate={onNavigate} />);
    expect(screen.getByRole("status").textContent).toContain("1 incidents mapped · 1 crews mapped");
    fireEvent.click(screen.getByRole("button", { name: /! · INC-1/ }));
    fireEvent.click(screen.getByRole("button", { name: "Open incident details" }));
    expect(onNavigate).toHaveBeenLastCalledWith({ type: "open_incident", incidentId: "INC-1" }, expect.any(HTMLElement));
    fireEvent.click(screen.getByRole("button", { name: /C · Line crew 1/ }));
    fireEvent.click(screen.getByRole("button", { name: "Open crew details" }));
    expect(onNavigate).toHaveBeenLastCalledWith({ type: "open_crew", crewId: "C1" }, expect.any(HTMLElement));
    fireEvent.click(screen.getByRole("checkbox", { name: "Incidents" }));
    expect(screen.getByRole("status").textContent).toContain("0 incidents mapped · 1 crews mapped");
    expect(screen.queryByRole("button", { name: /! · INC-1/ })).toBeNull();
  });

  it("keeps unmapped records accessible and searches the complete inventory across pages", () => {
    const many = Array.from({length: 25}, (_, i) => ({...incident, incident_id: `INC-${i}`}));
    render(<OperationsMap incidents={many} crews={[{...crew, map_location: null}]} onNavigate={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /! · INC-24/ })).toBeNull();
    fireEvent.change(screen.getByRole("combobox", {name: "Search records"}), {target: {value: "INC-24"}});
    expect(screen.getByRole("button", { name: /! · INC-24/ })).toBeTruthy();
    fireEvent.change(screen.getByRole("combobox", {name: "Search records"}), {target: {value: ""}});
    fireEvent.click(screen.getByRole("checkbox", { name: "Unmapped only" }));
    fireEvent.click(screen.getByRole("button", { name: /C · Line crew 1/ }));
    expect(screen.getByText("Location unavailable — this record is not plotted.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open crew details" })).toBeTruthy();
  });

  it("opens complete filtered and scenario populations without using the list page or map viewport", () => {
    const onNavigate = vi.fn();
    const many = Array.from({ length: 25 }, (_, index) => ({
      ...incident, incident_id: `INC-${index}`, severity: index < 24 ? "critical" : "low",
      latitude: index === 24 ? NaN : incident.latitude
    }));
    render(<OperationsMap incidents={many} crews={[{ ...crew, map_location: null }]} onNavigate={onNavigate} />);

    fireEvent.change(screen.getByRole("combobox", { name: "Map severity" }), { target: { value: "low" } });
    fireEvent.click(screen.getByRole("button", { name: "Matching incidents (1)" }));
    expect(onNavigate).toHaveBeenLastCalledWith({
      type: "filter_incidents",
      filter: { kind: "incident_ids", ids: ["INC-24"], label: "Matching incidents", source: "map_summary", criteria: "severity: low" }
    }, expect.any(HTMLElement));

    fireEvent.click(screen.getByRole("button", { name: "Unmapped incidents (1)" }));
    expect(onNavigate.mock.lastCall?.[0].filter.ids).toEqual(["INC-24"]);
    fireEvent.click(screen.getByRole("checkbox", { name: "Unmapped only" }));
    fireEvent.click(screen.getByRole("button", { name: "All scenario incidents (25)" }));
    expect(onNavigate.mock.lastCall?.[0].filter.ids).toHaveLength(25);
    expect(onNavigate.mock.lastCall?.[0].filter.criteria).toContain("map filters excluded");

    fireEvent.click(screen.getByRole("button", { name: "Unmapped crews (1)" }));
    expect(onNavigate.mock.lastCall?.[0]).toEqual({
      type: "filter_crews",
      filter: { kind: "crew_ids", ids: ["C1"], label: "Unmapped crews", source: "map_summary", criteria: "no applicable search or facet filters · location: unmapped" }
    });
  });

  it("consumes a mapped cross-view target, selects it, and reveals its clustered marker", async () => {
    const onNavigationHandled = vi.fn();
    const zoomToShowLayer = vi.spyOn(L.MarkerClusterGroup.prototype, "zoomToShowLayer");
    render(
      <OperationsMap
        incidents={[incident]}
        crews={[crew]}
        navigationTarget={{ entityKind: "incident", entityId: "INC-1", requestId: 7 }}
        onNavigationHandled={onNavigationHandled}
        onNavigate={vi.fn()}
      />
    );

    expect(await screen.findByText("Showing incident INC-1 on the map.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open incident details" })).toBeTruthy();
    await waitFor(() => expect(zoomToShowLayer).toHaveBeenCalled());
    expect(onNavigationHandled).toHaveBeenCalledWith(7);
  });

  it("clears hiding filters and enables the targeted entity layer", async () => {
    const onNavigationHandled = vi.fn();
    const view = render(
      <OperationsMap incidents={[incident]} crews={[crew]} onNavigate={vi.fn()} />
    );
    fireEvent.click(screen.getByRole("checkbox", { name: "Incidents" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Search records" }), { target: { value: "no match" } });

    view.rerender(
      <OperationsMap
        incidents={[incident]}
        crews={[crew]}
        navigationTarget={{ entityKind: "incident", entityId: "INC-1", requestId: 9 }}
        onNavigationHandled={onNavigationHandled}
        onNavigate={vi.fn()}
      />
    );

    expect(await screen.findByText("Showing incident INC-1 on the map.")).toBeTruthy();
    expect((screen.getByRole("checkbox", { name: "Incidents" }) as HTMLInputElement).checked).toBe(true);
    expect((screen.getByRole("combobox", { name: "Search records" }) as HTMLInputElement).value).toBe("");
    expect(screen.getByRole("button", { name: "Open incident details" })).toBeTruthy();
    expect(onNavigationHandled).toHaveBeenCalledWith(9);
  });

  it("selects a targeted unmapped record and reports that no location is available", async () => {
    const onNavigationHandled = vi.fn();
    render(
      <OperationsMap
        incidents={[incident]}
        crews={[{ ...crew, map_location: null }]}
        navigationTarget={{ entityKind: "crew", entityId: "C1", requestId: 8 }}
        onNavigationHandled={onNavigationHandled}
        onNavigate={vi.fn()}
      />
    );

    expect(await screen.findByText("Crew C1 is selected, but no map location is available.")).toBeTruthy();
    expect(screen.getByText("Location unavailable — this record is not plotted.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open crew details" })).toBeTruthy();
    expect(onNavigationHandled).toHaveBeenCalledWith(8);
  });

  it("restores list position, selection, layer filters, and map extent from a return snapshot", async () => {
    const setView = vi.spyOn(L.Map.prototype, "setView");
    const many = Array.from({ length: 25 }, (_, index) => ({
      ...incident,
      incident_id: `INC-${index}`,
      latitude: 40.7 + index / 1000
    }));
    render(
      <OperationsMap
        incidents={many}
        crews={[crew]}
        onNavigate={vi.fn()}
        restoredState={{
          showIncidents: true,
          showCrews: false,
          query: "",
          region: "all",
          unmappedOnly: false,
          selected: "incident:INC-24",
          page: 1,
          viewport: { center: [40.81, -73.2], zoom: 10 }
        }}
      />
    );

    expect(await screen.findByText("2 / 2")).toBeTruthy();
    expect((screen.getByRole("checkbox", { name: "Crews" }) as HTMLInputElement).checked).toBe(false);
    expect(screen.getByRole("button", { name: "Open incident details" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /! · INC-24/ }).getAttribute("aria-pressed")).toBe("true");
    expect(setView).toHaveBeenCalledWith([40.81, -73.2], 10, expect.objectContaining({ animate: false }));
  });

  it("offers grouped typeahead suggestions with filter-scoped match counts", () => {
    const incidents = [
      incident,
      { ...incident, incident_id: "INC-2", municipality: "Hicksville" },
      { ...incident, incident_id: "INC-3", municipality: "Riverhead", region: "Eastern-Suffolk" }
    ];
    render(<OperationsMap incidents={incidents} crews={[crew]} onNavigate={vi.fn()} />);

    const search = screen.getByRole("combobox", { name: "Search records" });
    fireEvent.change(search, { target: { value: "Hick" } });
    expect(screen.getByRole("option", { name: "Hicksville, Municipality, 2 matches" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Hicksville, Location, 1 match" })).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Operating region"), { target: { value: "Eastern-Suffolk" } });
    fireEvent.change(search, { target: { value: "River" } });
    expect(screen.getByRole("option", { name: "Riverhead, Municipality, 1 match" })).toBeTruthy();
    expect(screen.queryByRole("group", { name: "Location" })).toBeNull();
  });

  it("cascades complete-inventory incident facet counts and preserves withheld unknowns", () => {
    const incidents = [
      { ...incident, incident_id: "INC-CRITICAL", severity: "critical", hazard: "wire", critical_facility: true, critical_facility_level: 1 as const, ranking_status: "ranked" as const, customers_out: 1_500, assigned_crews: [] },
      { ...incident, incident_id: "INC-WITHHELD", severity: "high", hazard: "tree", critical_facility: true, critical_facility_level: null, ranking_status: "withheld" as const, customers_out: 50, assigned_crews: [{ crew_id: "C1", crew_name: "Line crew 1", assignment_id: "a-1", assigned_at: "2026-09-21T00:00:00Z" }] },
      { ...incident, incident_id: "INC-MEDIUM", severity: "medium", hazard: "wire", critical_facility: false, critical_facility_level: null, customers_out: 250, assigned_crews: [] }
    ];
    render(<OperationsMap incidents={incidents} crews={[]} onNavigate={vi.fn()} />);

    expect(screen.getByRole("option", { name: "Critical (1)" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Unknown (2)" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Withheld (1)" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Map severity"), { target: { value: "critical" } });
    expect(screen.getByRole("status").textContent).toContain("1 incidents · 0 crews match facets");
    expect(screen.getByRole("button", { name: /! · INC-CRITICAL/ })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /! · INC-WITHHELD/ })).toBeNull();
  });

  it("synchronizes the selected marker encoding with the legend", () => {
    render(<OperationsMap incidents={[{ ...incident, customers_out: 2_000 }]} crews={[]} onNavigate={vi.fn()} />);
    const encoding = screen.getByLabelText("Map marker encoding");
    expect(screen.getByLabelText("Severity colors")).toBeTruthy();
    expect(screen.getByLabelText("Critical severity")).toBeTruthy();
    fireEvent.change(encoding, { target: { value: "customers" } });
    expect(screen.getByText("Encoding: Customer impact size")).toBeTruthy();
    fireEvent.change(encoding, { target: { value: "ranking" } });
    expect(screen.getByLabelText("Ranking status colors")).toBeTruthy();
    expect(screen.getByLabelText("Withheld")).toBeTruthy();
  });

  it("filters crews by readiness, shift, assignment, and the available-line preset", () => {
    const crews = [
      crew,
      { ...crew, crew_id: "C2", crew_name: "Tree crew 2", status: "assigned", capability: "tree", shift_remaining_hours: 2, storm_ready: false, assigned_incidents: [{ assignment_id: "a-2", incident_id: "INC-1", assigned_at: "2026-09-21T00:00:00Z", municipality: "Hicksville", severity: "critical" }] },
      { ...crew, crew_id: "C3", crew_name: "Line crew 3", shift_remaining_hours: 8 }
    ];
    render(<OperationsMap incidents={[]} crews={crews} onNavigate={vi.fn()} />);

    expect(screen.getByRole("option", { name: "Storm-ready (2)" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Map crew readiness"), { target: { value: "ready" } });
    fireEvent.change(screen.getByLabelText("Map crew assignment"), { target: { value: "unassigned" } });
    expect(screen.getByRole("button", { name: /C · Line crew 1/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /C · Line crew 3/ })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /C · Tree crew 2/ })).toBeNull();
    fireEvent.change(screen.getByLabelText("Map crew preset"), { target: { value: "available-line" } });
    expect(screen.getByRole("button", { name: /C · Line crew 1/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /C · Line crew 3/ })).toBeTruthy();
  });

  it("reports basemap failure and offers retry while keeping records available", () => {
    const tileLayer = vi.spyOn(L, "tileLayer");
    const redraw = vi.spyOn(L.TileLayer.prototype, "redraw");
    render(<OperationsMap incidents={[incident]} crews={[]} onNavigate={vi.fn()} />);
    act(() => { tileLayer.mock.results[0].value.fire("tileerror"); });
    expect(screen.getByText(/Some basemap tiles could not load/)).toBeTruthy();
    expect(screen.getByRole("button", {name: /! · INC-1/})).toBeTruthy();
    fireEvent.click(screen.getByRole("button", {name: "Retry basemap"}));
    expect(redraw).toHaveBeenCalled();
  });

  it("selects a visible crew marker using the keyboard", () => {
    render(<OperationsMap incidents={[]} crews={[crew]} onNavigate={vi.fn()} />);
    fireEvent.keyDown(screen.getByRole("button", {name: "Crew Line crew 1 · Hicksville"}), {key: "Enter"});
    expect(screen.getByRole("button", {name: "Open crew details"})).toBeTruthy();
  });

  it("shows assigned records, selects them across list pages, and draws opt-in assignment connectors", () => {
    const line = vi.spyOn(L, "polyline");
    const fitBounds = vi.spyOn(L.Map.prototype, "fitBounds");
    const incidents = [assignedIncident, ...Array.from({ length: 24 }, (_, index) => ({ ...incident, incident_id: `OTHER-${index}` }))];
    render(<OperationsMap incidents={incidents} crews={[assignedCrew]} onNavigate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /! · INC-1/ }));
    expect(screen.getByRole("region", { name: "Assignment relationships" }).textContent).toContain("Visible on map");
    expect(line).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("checkbox", { name: /Show assignment relationship connectors/ }));
    expect(line).toHaveBeenCalledTimes(1);
    expect(line).toHaveBeenCalledWith([[40.77, -73.52], [40.8, -73.52]], expect.objectContaining({ dashArray: "6 6", interactive: false }));
    const relationshipBounds = fitBounds.mock.lastCall?.[0] as L.LatLngBounds;
    expect(relationshipBounds.contains([40.77, -73.52])).toBe(true);
    expect(relationshipBounds.contains([40.8, -73.52])).toBe(true);
    expect(fitBounds.mock.lastCall?.[1]).toEqual(expect.objectContaining({ maxZoom: 12, animate: false }));
    fireEvent.click(screen.getByRole("button", { name: "Select Line crew 1 on map" }));
    expect(screen.getByText("2 / 2")).toBeTruthy();
    expect(screen.getByRole("button", { name: /C · Line crew 1/ }).getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: "Clear map selection" }));
    expect(screen.queryByRole("checkbox", { name: /Show assignment relationship connectors/ })).toBeNull();
    expect(screen.queryByRole("region", { name: "Assignment relationships" })).toBeNull();
  });

  it("discloses filtered and unmapped assigned records without drawing misleading lines", () => {
    const line = vi.spyOn(L, "polyline");
    render(<OperationsMap incidents={[assignedIncident]} crews={[{ ...assignedCrew, map_location: null }]} onNavigate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /! · INC-1/ }));
    expect(screen.getByRole("region", { name: "Assignment relationships" }).textContent).toContain("Visible in list · location unavailable");
    fireEvent.click(screen.getByRole("checkbox", { name: /Show assignment relationship connectors/ }));
    expect(line).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Map crew status"), { target: { value: "available" } });
    expect(screen.getByRole("region", { name: "Assignment relationships" }).textContent).toContain("Hidden by current map filters");
    expect(screen.queryByRole("button", { name: "Select Line crew 1 on map" })).toBeNull();
  });

  it("keeps overlapping assigned points in the relationship panel without a connector", () => {
    const line = vi.spyOn(L, "polyline");
    render(<OperationsMap incidents={[assignedIncident]} crews={[{ ...assignedCrew, map_location: crew.map_location }]} onNavigate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /! · INC-1/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Show assignment relationship connectors/ }));
    expect(screen.getByText(/Some assigned records share a map point/)).toBeTruthy();
    expect(line).not.toHaveBeenCalled();
  });

  it("uses a selected crew's assignments and reports missing scenario records", () => {
    const withMissing = { ...assignedCrew, assigned_incidents: [assignment, { ...assignment, assignment_id: "a-2", incident_id: "INC-MISSING" }] };
    render(<OperationsMap incidents={[assignedIncident]} crews={[withMissing]} onNavigate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /C · Line crew 1/ }));
    const relationships = screen.getByRole("region", { name: "Assignment relationships" });
    expect(relationships.textContent).toContain("Assignment relationships (2)");
    expect(relationships.textContent).toContain("Record unavailable in this scenario");
    expect(screen.getByRole("button", { name: "Select INC-1 on map" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Select INC-MISSING on map" })).toBeNull();
  });

});
