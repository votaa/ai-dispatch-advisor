import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Crew, Incident } from "../types";
import {
  ContextualNavigationPanel,
  resolveNavigationDestinations
} from "./ContextualNavigation";

const incident: Incident = {
  incident_id: "INC-1",
  region: "Central-Nassau",
  municipality: "Hicksville",
  feeder: "FDR-1",
  severity: "high",
  status: "new",
  customers_out: 25,
  critical_facility: true,
  critical_facility_level: 2,
  matched_critical_facility_ids: ["CF-1"],
  hazard: "wire",
  required_skill: "line",
  age_minutes: 3,
  latitude: 40.77,
  longitude: -73.52,
  etr: "Unknown",
  assigned_crews: [{ crew_id: "CR-1", crew_name: "Line crew 1", assignment_id: "A-1", assigned_at: "2026-09-19T10:00:00Z" }],
  current_decision: null
};

const crew: Crew = {
  crew_id: "CR-1",
  crew_name: "Line crew 1",
  current_location: "Hicksville",
  home_region: "Central-Nassau",
  status: "assigned",
  capability: "line",
  shift_remaining_hours: 5,
  storm_ready: true,
  travel_minutes_to_selected_incident: 10,
  assigned_incidents: [{ incident_id: "INC-1", assignment_id: "A-1", assigned_at: "2026-09-19T10:00:00Z", municipality: "Hicksville", severity: "high" }],
  map_location: null
};

const context = { incidents: [incident], crews: [crew] };

afterEach(cleanup);

describe("contextual navigation", () => {
  it("resolves detail, related-record, and map destinations from the same authoritative entity", () => {
    const destinations = resolveNavigationDestinations({ kind: "incident", id: "INC-1" }, context);

    expect(destinations.map((destination) => destination.kind)).toEqual([
      "full_detail",
      "related_records",
      "show_on_map"
    ]);
    expect(destinations[1].command).toEqual({
      type: "filter_crews",
      filter: { kind: "crew_ids", ids: ["CR-1"], label: "Assigned to INC-1" }
    });
  });

  it("omits current or invalid destinations and keeps map valid for an unmapped crew", () => {
    const currentCrewDestinations = resolveNavigationDestinations(
      { kind: "crew", id: "CR-1" },
      { ...context, currentView: "crews", currentEntity: { kind: "crew", id: "CR-1" } }
    );

    expect(currentCrewDestinations.map((destination) => destination.kind)).toEqual([
      "related_records",
      "show_on_map"
    ]);
    expect(resolveNavigationDestinations({ kind: "crew", id: "missing" }, context)).toEqual([]);
  });

  it("uses exact structured filters for municipality, feeder, and critical-facility references", () => {
    expect(resolveNavigationDestinations({ kind: "municipality", name: "Hicksville" }, context)[0].command)
      .toEqual({ type: "filter_incidents", filter: { kind: "municipality", value: "Hicksville", label: "Municipality: Hicksville" } });
    expect(resolveNavigationDestinations({ kind: "feeder", id: "FDR-1" }, context)[0].command)
      .toEqual({ type: "filter_incidents", filter: { kind: "feeder", value: "FDR-1", label: "Feeder: FDR-1" } });
    expect(resolveNavigationDestinations({ kind: "critical_facility", id: "CF-1" }, context)[0].command)
      .toEqual({ type: "filter_incidents", filter: { kind: "critical_facility", value: "CF-1", label: "Critical facility: CF-1" } });
  });

  it("renders the resolved actions and dispatches the selected standard destination", () => {
    const onNavigate = vi.fn();
    render(
      <ContextualNavigationPanel
        context={context}
        onNavigate={onNavigate}
        reference={{ kind: "incident", id: "INC-1" }}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Show on map" }));
    expect(onNavigate).toHaveBeenCalledWith(
      { type: "show_on_map", entityKind: "incident", entityId: "INC-1" },
      expect.any(HTMLElement)
    );
  });
});
