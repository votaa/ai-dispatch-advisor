import type { CrewNavigationFilter, IncidentNavigationFilter } from "./components/ContextualNavigation";

// Return snapshots contain view-local UI state only. Scenario records remain authoritative
// in App and are deliberately never copied into navigation history.

export type IncidentSortState = {
  key: "id" | "region" | "customers" | "severity" | "criticalFacility" | "hazard" | "assigned" | "decision" | "etr";
  direction: "asc" | "desc";
};

export type CrewSortState = {
  key: "name" | "status" | "capability" | "shift" | "assigned" | "travel";
  direction: "asc" | "desc";
};

export type IncidentWorkspaceState = {
  query: string;
  severity: string;
  region: string;
  criticalFacility: string;
  relatedFilter: IncidentNavigationFilter | null;
  sort: IncidentSortState | null;
  page: number;
};

export type CrewWorkspaceState = {
  query: string;
  status: string;
  capability: string;
  region: string;
  stormReady: string;
  relatedFilter: CrewNavigationFilter | null;
  sort: CrewSortState;
  page: number;
};

export type MapViewportState = {
  center: [number, number];
  zoom: number;
};

export type MapWorkspaceState = {
  showIncidents: boolean;
  showCrews: boolean;
  query: string;
  region: string;
  unmappedOnly: boolean;
  selected: string | null;
  page: number;
  viewport: MapViewportState | null;
};
