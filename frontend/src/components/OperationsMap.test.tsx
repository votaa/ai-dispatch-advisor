import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
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
    const onOpenIncident = vi.fn(); const onOpenCrew = vi.fn();
    render(<OperationsMap incidents={[incident]} crews={[crew]} onOpenIncident={onOpenIncident} onOpenCrew={onOpenCrew} />);
    expect(screen.getByRole("status").textContent).toContain("1 incidents mapped · 1 crews mapped");
    fireEvent.click(screen.getByRole("button", { name: /! · INC-1/ }));
    fireEvent.click(screen.getByRole("button", { name: "Open incident" }));
    expect(onOpenIncident).toHaveBeenCalledWith("INC-1");
    fireEvent.click(screen.getByRole("button", { name: /C · Line crew 1/ }));
    fireEvent.click(screen.getByRole("button", { name: "Open crew board" }));
    expect(onOpenCrew).toHaveBeenCalledWith("C1");
    fireEvent.click(screen.getByRole("checkbox", { name: "Incidents" }));
    expect(screen.getByRole("status").textContent).toContain("0 incidents mapped · 1 crews mapped");
    expect(screen.queryByRole("button", { name: /! · INC-1/ })).toBeNull();
  });

  it("keeps unmapped records accessible and searches the complete inventory across pages", () => {
    const many = Array.from({length: 25}, (_, i) => ({...incident, incident_id: `INC-${i}`}));
    render(<OperationsMap incidents={many} crews={[{...crew, map_location: null}]} onOpenIncident={vi.fn()} onOpenCrew={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /! · INC-24/ })).toBeNull();
    fireEvent.change(screen.getByRole("searchbox"), {target: {value: "INC-24"}});
    expect(screen.getByRole("button", { name: /! · INC-24/ })).toBeTruthy();
    fireEvent.change(screen.getByRole("searchbox"), {target: {value: ""}});
    fireEvent.click(screen.getByRole("checkbox", { name: "Unmapped only" }));
    fireEvent.click(screen.getByRole("button", { name: /C · Line crew 1/ }));
    expect(screen.getByText("Location unavailable — this record is not plotted.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open crew board" })).toBeTruthy();
  });
  it("reports basemap failure and offers retry while keeping records available", () => {
    const tileLayer = vi.spyOn(L, "tileLayer");
    const redraw = vi.spyOn(L.TileLayer.prototype, "redraw");
    render(<OperationsMap incidents={[incident]} crews={[]} onOpenIncident={vi.fn()} onOpenCrew={vi.fn()} />);
    act(() => { tileLayer.mock.results[0].value.fire("tileerror"); });
    expect(screen.getByText(/Some basemap tiles could not load/)).toBeTruthy();
    expect(screen.getByRole("button", {name: /! · INC-1/})).toBeTruthy();
    fireEvent.click(screen.getByRole("button", {name: "Retry basemap"}));
    expect(redraw).toHaveBeenCalled();
  });

  it("selects a visible crew marker using the keyboard", () => {
    render(<OperationsMap incidents={[]} crews={[crew]} onOpenIncident={vi.fn()} onOpenCrew={vi.fn()} />);
    fireEvent.keyDown(screen.getByRole("button", {name: "Crew Line crew 1 · Hicksville"}), {key: "Enter"});
    expect(screen.getByRole("button", {name: "Open crew board"})).toBeTruthy();
  });

});
