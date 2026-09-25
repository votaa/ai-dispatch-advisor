import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import L from "leaflet";
import "leaflet.markercluster";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import type { Crew, Incident } from "../types";
import { AutocompleteSearch, buildAutocompleteSuggestions } from "./AutocompleteSearch";
import type { AutocompleteField } from "./AutocompleteSearch";
import { ContextualNavigationPanel, EntityNavigationActions } from "./ContextualNavigation";
import type { NavigationResolverContext, OperationalNavigationCommand } from "./ContextualNavigation";
import type { MapViewportState, MapWorkspaceState } from "../navigationState";
import "./OperationsMap.css";

// Initial framing only: panning remains unrestricted, including surrounding NYC.
const LONG_ISLAND_BOUNDS: L.LatLngBoundsExpression = [[40.48, -74.12], [41.19, -71.80]];
const PAGE_SIZE = 20;
type IncidentFacetKey = "severity" | "hazard" | "criticalFacilityLevel" | "rankingStatus" | "customerImpact" | "assignmentState" | "incidentAge";
type CrewFacetKey = "status" | "capability" | "readiness" | "shift" | "assignment";
type MapEncoding = NonNullable<MapWorkspaceState["encoding"]>;
type MapFilterTab = NonNullable<MapWorkspaceState["filterPanelTab"]>;

const CUSTOMER_IMPACT_RANGES = [
  { value: "0-99", label: "0–99 customers", matches: (incident: Incident) => incident.customers_out < 100 },
  { value: "100-999", label: "100–999 customers", matches: (incident: Incident) => incident.customers_out >= 100 && incident.customers_out < 1_000 },
  { value: "1000+", label: "1,000+ customers", matches: (incident: Incident) => incident.customers_out >= 1_000 }
];
const INCIDENT_AGE_RANGES = [
  { value: "0-59", label: "Under 1 hour", matches: (incident: Incident) => incident.age_minutes < 60 },
  { value: "60-239", label: "1–3 hours", matches: (incident: Incident) => incident.age_minutes >= 60 && incident.age_minutes < 240 },
  { value: "240+", label: "4+ hours", matches: (incident: Incident) => incident.age_minutes >= 240 }
];
const CREW_SHIFT_RANGES = [
  { value: "0-3", label: "0–3 hours", matches: (crew: Crew) => crew.shift_remaining_hours < 4 },
  { value: "4-7", label: "4–7 hours", matches: (crew: Crew) => crew.shift_remaining_hours >= 4 && crew.shift_remaining_hours < 8 },
  { value: "8+", label: "8+ hours", matches: (crew: Crew) => crew.shift_remaining_hours >= 8 }
];
export type MapRecord = {
  key: string;
  kind: "incident" | "crew";
  id: string;
  title: string;
  location: string;
  region: string;
  status: string;
  detail: string;
  coordinates: [number, number] | null;
  incident?: Incident;
  crew?: Crew;
};

export type MapNavigationTarget = {
  entityKind: MapRecord["kind"];
  entityId: string;
  requestId: number;
};

export function incidentFacetValue(incident: Incident, facet: IncidentFacetKey): string {
  if (facet === "severity") return incident.severity.toLowerCase();
  if (facet === "hazard") return incident.hazard || "unknown";
  if (facet === "criticalFacilityLevel") return incident.critical_facility_level ? `level-${incident.critical_facility_level}` : "unknown";
  if (facet === "rankingStatus") return incident.ranking_status === "withheld" ? "withheld" : "ranked";
  if (facet === "customerImpact") return CUSTOMER_IMPACT_RANGES.find((range) => range.matches(incident))?.value ?? "unknown";
  if (facet === "assignmentState") return incident.assigned_crews.length ? "assigned" : "unassigned";
  return INCIDENT_AGE_RANGES.find((range) => range.matches(incident))?.value ?? "unknown";
}

function crewFacetValue(crew: Crew, facet: CrewFacetKey): string {
  if (facet === "status") return crew.status || "unknown";
  if (facet === "capability") return crew.capability || "unknown";
  if (facet === "readiness") return crew.storm_ready ? "ready" : "not-ready";
  if (facet === "assignment") return crew.assigned_incidents.length ? "assigned" : "unassigned";
  return CREW_SHIFT_RANGES.find((range) => range.matches(crew))?.value ?? "unknown";
}

export function encodingLabel(encoding: MapEncoding): string {
  return ({ severity: "Severity color", customers: "Customer impact size", age: "Incident age size", criticalFacility: "Critical-facility color", ranking: "Ranking status color" })[encoding];
}

function formatFacetValue(value: string): string {
  if (value === "unknown") return "Unknown";
  if (value === "ranked") return "Ranked";
  if (value === "withheld") return "Withheld";
  if (value.startsWith("level-")) return `Level ${value.slice(6)}`;
  return value.replace(/\b\w/g, (character) => character.toUpperCase()).replace(/-/g, " ");
}

function facetOptions(incidents: Incident[], facet: IncidentFacetKey, selected: string): Array<{ value: string; label: string; count: number }> {
  const values = Array.from(new Set(incidents.map((incident) => incidentFacetValue(incident, facet))));
  const ordered = facet === "severity" ? ["critical", "high", "medium", "low"] : values.sort((left, right) => left.localeCompare(right));
  if (selected !== "all" && !ordered.includes(selected)) ordered.push(selected);
  const rangeLabels = new Map([...CUSTOMER_IMPACT_RANGES, ...INCIDENT_AGE_RANGES].map((range) => [range.value, range.label]));
  return ordered.map((value) => ({ value, label: rangeLabels.get(value) ?? formatFacetValue(value), count: incidents.filter((incident) => incidentFacetValue(incident, facet) === value).length }));
}

function crewFacetOptions(crews: Crew[], facet: CrewFacetKey, selected: string): Array<{ value: string; label: string; count: number }> {
  const values = Array.from(new Set(crews.map((crew) => crewFacetValue(crew, facet))));
  const ordered = facet === "readiness" ? ["ready", "not-ready"] : values.sort((left, right) => left.localeCompare(right));
  if (selected !== "all" && !ordered.includes(selected)) ordered.push(selected);
  const rangeLabels = new Map(CREW_SHIFT_RANGES.map((range) => [range.value, range.label]));
  const labels: Record<string, string> = { ready: "Storm-ready", "not-ready": "Not storm-ready", assigned: "Assigned", unassigned: "Unassigned" };
  return ordered.map((value) => ({ value, label: rangeLabels.get(value) ?? labels[value] ?? formatFacetValue(value), count: crews.filter((crew) => crewFacetValue(crew, facet) === value).length }));
}

const mapAutocompleteFields: AutocompleteField<MapRecord>[] = [
  { group: "Incident ID", values: (record) => record.incident?.incident_id ?? "" },
  { group: "Feeder", values: (record) => record.incident?.feeder ?? "" },
  { group: "Municipality", values: (record) => record.incident?.municipality ?? "" },
  { group: "Hazard", values: (record) => record.incident?.hazard ?? "" },
  { group: "Crew ID", values: (record) => record.crew?.crew_id ?? "" },
  { group: "Crew Name", values: (record) => record.crew?.crew_name ?? "" },
  { group: "Location", values: (record) => record.crew?.current_location ?? "" },
  { group: "Capability", values: (record) => record.crew?.capability ?? "" },
  { group: "Region", values: (record) => record.crew?.home_region ?? "" },
  { group: "Assigned Incident", values: (record) => record.crew?.assigned_incidents.map((assignment) => assignment.incident_id) ?? [] }
];

function coordinates(latitude: unknown, longitude: unknown): [number, number] | null {
  return typeof latitude === "number" && typeof longitude === "number" &&
    Number.isFinite(latitude) && Number.isFinite(longitude) &&
    Math.abs(latitude) <= 90 && Math.abs(longitude) <= 180 && !(latitude === 0 && longitude === 0)
    ? [latitude, longitude] : null;
}

export function mapRecords(incidents: Incident[], crews: Crew[]): MapRecord[] {
  return [
    ...incidents.map((incident): MapRecord => ({
      key: `incident:${incident.incident_id}`, kind: "incident", id: incident.incident_id,
      title: incident.incident_id, location: incident.municipality, region: incident.region,
      status: incident.status, detail: `${incident.severity} · ${incident.hazard}`,
      coordinates: coordinates(incident.latitude, incident.longitude), incident
    })),
    ...crews.map((crew): MapRecord => ({
      key: `crew:${crew.crew_id}`, kind: "crew", id: crew.crew_id,
      title: crew.crew_name, location: crew.current_location, region: crew.home_region,
      status: crew.status, detail: `${crew.capability} · ${crew.crew_id}`,
      coordinates: coordinates(crew.map_location?.latitude, crew.map_location?.longitude), crew
    }))
  ];
}

function markerIcon(record: MapRecord, encoding: MapEncoding, relationship: "selected" | "related" | null) {
  const incident = record.incident;
  const style = encoding === "customers" ? { size: incident ? Math.min(42, 24 + Math.log10(Math.max(1, incident.customers_out)) * 5) : 28 }
    : encoding === "age" ? { size: incident ? Math.min(42, 26 + Math.log10(Math.max(1, incident.age_minutes)) * 4) : 28 } : { size: 28 };
  const color = record.kind === "crew" ? "#176a96" : encoding === "criticalFacility"
    ? (incident?.critical_facility ? "#7b2cbf" : "#6b7c8f")
    : encoding === "ranking" ? (incident?.ranking_status === "withheld" ? "#6b7c8f" : "#176a96")
    : encoding === "severity" ? ({ critical: "#9d1c1c", high: "#bd3c2f", medium: "#c47b16", low: "#3d7f4f" }[incident?.severity.toLowerCase() ?? ""] ?? "#6b7c8f")
    : "#bd3c2f";
  return L.divIcon({
    className: `operations-marker operations-marker-${record.kind}${relationship ? ` operations-marker-${relationship}` : ""}`,
    html: `<span style="background:${color};width:${style.size}px;height:${style.size}px">${record.kind === "incident" ? "!" : "C"}</span>`, iconSize: [style.size, style.size], iconAnchor: [style.size / 2, style.size / 2]
  });
}

function MapCanvas({ records, selected, relatedKeys, connectors, onSelect, homeRequest, restoredViewport, onViewportChange, encoding }: {
  records: MapRecord[];
  selected: string | null;
  relatedKeys: Set<string>;
  connectors: Array<[[number, number], [number, number]]>;
  onSelect: (key: string) => void;
  homeRequest: number;
  restoredViewport?: MapViewportState | null;
  onViewportChange?: (viewport: MapViewportState) => void;
  encoding: MapEncoding;
}) {
  const element = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const clusters = useRef<L.MarkerClusterGroup | null>(null);
  const markers = useRef(new Map<string, L.Marker>());
  const styledKeys = useRef(new Set<string>());
  const highlightedMarkers = useRef(new Set<L.Marker>());
  const tiles = useRef<L.TileLayer | null>(null);
  const relationshipLines = useRef<L.LayerGroup | null>(null);
  const skipInitialSelectionReveal = useRef(Boolean(restoredViewport && selected));
  const homeRequestMounted = useRef(false);
  const [tileError, setTileError] = useState(false);

  useEffect(() => {
    if (!element.current) return;
    const instance = L.map(element.current, { maxZoom: 18, minZoom: 5, zoomSnap: 0.25 });
    instance.fitBounds(LONG_ISLAND_BOUNDS, { padding: [24, 24] });
    const tileLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(instance);
    relationshipLines.current = L.layerGroup().addTo(instance);
    tileLayer.on("tileerror", () => setTileError(true));
    const group = L.markerClusterGroup({
      maxClusterRadius: 42, showCoverageOnHover: false, animate: false,
      spiderfyOnMaxZoom: true,
      iconCreateFunction: (cluster) => L.divIcon({
        html: `<span aria-label="${cluster.getChildCount()} grouped records">${cluster.getChildCount()}</span>`,
        className: `operations-cluster${cluster.getAllChildMarkers().some((marker) => highlightedMarkers.current.has(marker)) ? " operations-cluster-related" : ""}`,
        iconSize: [38, 38]
      })
    }).addTo(instance);
    L.control.scale({ imperial: true, metric: false }).addTo(instance);
    if (restoredViewport) instance.setView(restoredViewport.center, restoredViewport.zoom, { animate: false });
    const reportViewport = () => {
      const center = instance.getCenter();
      onViewportChange?.({ center: [center.lat, center.lng], zoom: instance.getZoom() });
    };
    instance.on("moveend", reportViewport);
    reportViewport();
    map.current = instance; clusters.current = group; tiles.current = tileLayer;
    const observer = new ResizeObserver(() => instance.invalidateSize({ pan: false }));
    observer.observe(element.current);
    return () => {
      observer.disconnect(); instance.off("moveend", reportViewport); instance.remove();
      map.current = null; clusters.current = null; tiles.current = null; relationshipLines.current = null; markers.current.clear(); styledKeys.current.clear(); highlightedMarkers.current.clear();
    };
  }, []);

  useEffect(() => {
    const group = clusters.current;
    if (!group) return;
    group.clearLayers(); markers.current.clear();
    const layers = records.flatMap((record) => {
      if (!record.coordinates) return [];
      const label = `${record.kind === "incident" ? "Incident" : "Crew"} ${record.title} · ${record.location}`;
      const tooltip = document.createElement("span");
      tooltip.textContent = label;
      const marker = L.marker(record.coordinates, {
        icon: markerIcon(record, encoding, null), title: label, alt: label, keyboard: true
      }).bindTooltip(tooltip).on("click", () => onSelect(record.key));
      marker.on("keydown", (event: L.LeafletKeyboardEvent) => {
        if (event.originalEvent.key === "Enter" || event.originalEvent.key === " ") {
          L.DomEvent.stop(event.originalEvent);
          onSelect(record.key);
        }
      });
      marker.on("add", () => marker.getElement()?.setAttribute("aria-label", label));
      markers.current.set(record.key, marker);
      return [marker];
    });
    group.addLayers(layers);
  }, [encoding, onSelect, records]);

  useEffect(() => {
    const next = new Set(relatedKeys);
    if (selected) next.add(selected);
    const byKey = new Map(records.map((record) => [record.key, record]));
    new Set([...styledKeys.current, ...next]).forEach((key) => {
      const record = byKey.get(key);
      if (record) markers.current.get(key)?.setIcon(markerIcon(record, encoding,
        key === selected ? "selected" : relatedKeys.has(key) ? "related" : null));
    });
    styledKeys.current = next;
    highlightedMarkers.current = new Set([...next].map((key) => markers.current.get(key)).filter((marker): marker is L.Marker => Boolean(marker)));
    clusters.current?.refreshClusters();
  }, [encoding, records, relatedKeys, selected]);

  useEffect(() => {
    const group = relationshipLines.current;
    if (!group) return;
    group.clearLayers();
    connectors.forEach(([from, to]) => {
      L.polyline([from, to], { color: "#51418b", weight: 3, opacity: 0.85, dashArray: "6 6", interactive: false }).addTo(group);
    });
  }, [connectors]);

  useEffect(() => {
    if (!selected) return;
    if (skipInitialSelectionReveal.current) {
      skipInitialSelectionReveal.current = false;
      return;
    }
    if (connectors.length > 0) {
      map.current?.fitBounds(L.latLngBounds(connectors.flatMap(([from, to]) => [from, to])), {
        padding: [36, 36], maxZoom: 12, animate: false
      });
      return;
    }
    const marker = markers.current.get(selected);
    if (marker) clusters.current?.zoomToShowLayer(marker, () => marker.openTooltip());
  }, [connectors, selected, records]);

  useEffect(() => {
    if (!homeRequestMounted.current) {
      homeRequestMounted.current = true;
      return;
    }
    map.current?.fitBounds(LONG_ISLAND_BOUNDS, { padding: [24, 24] });
  }, [homeRequest]);

  return <div className="operations-map-surface">
    {tileError && <div role="status" className="operations-map-warning">
      Some basemap tiles could not load. Locations and the record list remain available.
      <button type="button" onClick={() => { setTileError(false); tiles.current?.redraw(); }}>Retry basemap</button>
    </div>}
    <div ref={element} className="operations-map-canvas" aria-label="Long Island incident and crew map" />
  </div>;
}

export default function OperationsMap({
  incidents,
  crews,
  navigationTarget,
  navigationContext,
  onNavigate,
  onNavigationHandled,
  restoredState,
  onStateChange
}: {
  incidents: Incident[]; crews: Crew[];
  navigationTarget?: MapNavigationTarget | null;
  navigationContext?: NavigationResolverContext;
  onNavigate: (command: OperationalNavigationCommand, trigger?: HTMLElement) => void;
  onNavigationHandled?: (requestId: number) => void;
  restoredState?: MapWorkspaceState;
  onStateChange?: (state: MapWorkspaceState) => void;
}) {
  const [showIncidents, setShowIncidents] = useState(restoredState?.showIncidents ?? true);
  const [showCrews, setShowCrews] = useState(restoredState?.showCrews ?? true);
  const [query, setQuery] = useState(restoredState?.query ?? "");
  const [region, setRegion] = useState(restoredState?.region ?? "all");
  const [unmappedOnly, setUnmappedOnly] = useState(restoredState?.unmappedOnly ?? false);
  const [severity, setSeverity] = useState(restoredState?.severity ?? "all");
  const [hazard, setHazard] = useState(restoredState?.hazard ?? "all");
  const [criticalFacilityLevel, setCriticalFacilityLevel] = useState(restoredState?.criticalFacilityLevel ?? "all");
  const [rankingStatus, setRankingStatus] = useState(restoredState?.rankingStatus ?? "all");
  const [customerImpact, setCustomerImpact] = useState(restoredState?.customerImpact ?? "all");
  const [assignmentState, setAssignmentState] = useState(restoredState?.assignmentState ?? "all");
  const [incidentAge, setIncidentAge] = useState(restoredState?.incidentAge ?? "all");
  const [encoding, setEncoding] = useState<MapEncoding>(restoredState?.encoding ?? "severity");
  const [crewStatus, setCrewStatus] = useState(restoredState?.crewStatus ?? "all");
  const [crewCapability, setCrewCapability] = useState(restoredState?.crewCapability ?? "all");
  const [crewReadiness, setCrewReadiness] = useState(restoredState?.crewReadiness ?? "all");
  const [crewShift, setCrewShift] = useState(restoredState?.crewShift ?? "all");
  const [crewAssignment, setCrewAssignment] = useState(restoredState?.crewAssignment ?? "all");
  const [crewPreset, setCrewPreset] = useState(restoredState?.crewPreset ?? "all");
  const [showRelationships, setShowRelationships] = useState(restoredState?.showRelationships ?? false);
  const [selected, setSelected] = useState<string | null>(restoredState?.selected ?? null);
  const [page, setPage] = useState(restoredState?.page ?? 0);
  const [viewport, setViewport] = useState<MapViewportState | null>(restoredState?.viewport ?? null);
  const [homeRequest, setHomeRequest] = useState(0);
  const [navigationNotice, setNavigationNotice] = useState("");
  const [filterPanelOpen, setFilterPanelOpen] = useState(restoredState?.filterPanelOpen ?? false);
  const [filterPanelTab, setFilterPanelTab] = useState<MapFilterTab>(restoredState?.filterPanelTab ?? "incidents");
  const filterTriggerRef = useRef<HTMLButtonElement>(null);
  const filterPanelRef = useRef<HTMLElement>(null);
  const focusOpenedTab = useRef(false);
  const skipInitialFilterReset = useRef(Boolean(restoredState));
  const all = useMemo(() => mapRecords(incidents, crews), [incidents, crews]);
  const regions = useMemo(
    () => Array.from(new Set(all.map((record) => record.region).filter((region): region is string => Boolean(region)))).sort(),
    [all]
  );
  const incidentFacetSelections: Record<IncidentFacetKey, string> = { severity, hazard, criticalFacilityLevel, rankingStatus, customerImpact, assignmentState, incidentAge };
  const crewFacetSelections: Record<CrewFacetKey, string> = { status: crewStatus, capability: crewCapability, readiness: crewReadiness, shift: crewShift, assignment: crewAssignment };
  const matchesIncidentFacets = useCallback((incident: Incident, excluded?: IncidentFacetKey) =>
    (excluded === "severity" || severity === "all" || incidentFacetValue(incident, "severity") === severity) &&
    (excluded === "hazard" || hazard === "all" || incidentFacetValue(incident, "hazard") === hazard) &&
    (excluded === "criticalFacilityLevel" || criticalFacilityLevel === "all" || incidentFacetValue(incident, "criticalFacilityLevel") === criticalFacilityLevel) &&
    (excluded === "rankingStatus" || rankingStatus === "all" || incidentFacetValue(incident, "rankingStatus") === rankingStatus) &&
    (excluded === "customerImpact" || customerImpact === "all" || incidentFacetValue(incident, "customerImpact") === customerImpact) &&
    (excluded === "assignmentState" || assignmentState === "all" || incidentFacetValue(incident, "assignmentState") === assignmentState) &&
    (excluded === "incidentAge" || incidentAge === "all" || incidentFacetValue(incident, "incidentAge") === incidentAge),
  [assignmentState, criticalFacilityLevel, customerImpact, hazard, incidentAge, rankingStatus, severity]);
  const matchesCrewFacets = useCallback((crew: Crew, excluded?: CrewFacetKey) =>
    (excluded === "status" || crewStatus === "all" || crewFacetValue(crew, "status") === crewStatus) &&
    (excluded === "capability" || crewCapability === "all" || crewFacetValue(crew, "capability") === crewCapability) &&
    (excluded === "readiness" || crewReadiness === "all" || crewFacetValue(crew, "readiness") === crewReadiness) &&
    (excluded === "shift" || crewShift === "all" || crewFacetValue(crew, "shift") === crewShift) &&
    (excluded === "assignment" || crewAssignment === "all" || crewFacetValue(crew, "assignment") === crewAssignment) &&
    (crewPreset === "all" || (crewPreset === "available-line" && crew.status === "available" && crew.capability.toLowerCase() === "line")),
  [crewAssignment, crewCapability, crewPreset, crewReadiness, crewShift, crewStatus]);
  const suggestionRecords = useMemo(() => all.filter((record) =>
    (record.kind === "incident" ? showIncidents : showCrews) &&
    (region === "all" || record.region === region) &&
    (record.kind === "incident" ? Boolean(record.incident && matchesIncidentFacets(record.incident)) : Boolean(record.crew && matchesCrewFacets(record.crew)))
  ), [all, matchesCrewFacets, matchesIncidentFacets, region, showCrews, showIncidents]);
  const autocompleteSuggestions = useMemo(
    () => buildAutocompleteSuggestions(suggestionRecords, mapAutocompleteFields, query),
    [query, suggestionRecords]
  );
  const filtered = useMemo(() => {
    const search = query.toLowerCase().trim();
    return all.filter((r) => (r.kind === "incident" ? showIncidents : showCrews) &&
      (region === "all" || r.region === region) &&
      (r.kind === "incident" ? Boolean(r.incident && matchesIncidentFacets(r.incident)) : Boolean(r.crew && matchesCrewFacets(r.crew))) &&
      `${r.title} ${r.id} ${r.location} ${r.detail} ${r.status}`.toLowerCase().includes(search));
  }, [all, matchesCrewFacets, matchesIncidentFacets, query, region, showIncidents, showCrews]);
  const filteredIncidentInventory = useMemo(() => all.filter((record) => record.kind === "incident" &&
    (region === "all" || record.region === region) &&
    `${record.title} ${record.id} ${record.location} ${record.detail} ${record.status}`.toLowerCase().includes(query.toLowerCase().trim())
  ).map((record) => record.incident!).filter(Boolean), [all, query, region]);
  const facetOptionsByKey = useMemo(() => Object.fromEntries((Object.keys(incidentFacetSelections) as IncidentFacetKey[]).map((facet) => [facet,
    facetOptions(filteredIncidentInventory.filter((incident) => matchesIncidentFacets(incident, facet)), facet, incidentFacetSelections[facet])
  ])), [filteredIncidentInventory, incidentFacetSelections, matchesIncidentFacets]);
  const filteredCrewInventory = useMemo(() => all.filter((record) => record.kind === "crew" &&
    (region === "all" || record.region === region) &&
    `${record.title} ${record.id} ${record.location} ${record.detail} ${record.status}`.toLowerCase().includes(query.toLowerCase().trim())
  ).map((record) => record.crew!).filter(Boolean), [all, query, region]);
  const crewFacetOptionsByKey = useMemo(() => Object.fromEntries((Object.keys(crewFacetSelections) as CrewFacetKey[]).map((facet) => [facet,
    crewFacetOptions(filteredCrewInventory.filter((crew) => matchesCrewFacets(crew, facet)), facet, crewFacetSelections[facet])
  ])), [crewFacetSelections, filteredCrewInventory, matchesCrewFacets]);
  const unmappedCount = filtered.filter((r) => !r.coordinates).length;
  const mappedIncidents = filtered.filter((r) => r.kind === "incident" && r.coordinates).length;
  const mappedCrews = filtered.filter((r) => r.kind === "crew" && r.coordinates).length;
  // Summary populations come from the complete filtered inventory, before list paging,
  // the list-only unmapped switch, clustering, or viewport rendering.
  const summaryCriteria = (kind: MapRecord["kind"]) => [
    region !== "all" && `region: ${region}`,
    query.trim() && `map search: ${query.trim()}`,
    ...(kind === "incident" ? Object.entries(incidentFacetSelections) : Object.entries(crewFacetSelections))
      .filter(([, value]) => value !== "all").map(([key, value]) => `${key}: ${value}`),
    kind === "crew" && crewPreset !== "all" && `crew preset: ${crewPreset}`
  ].filter(Boolean).join(" · ") || "no applicable search or facet filters";
  const summaryRecords = (kind: MapRecord["kind"], location: "all" | "mapped" | "unmapped" = "all") =>
    filtered.filter((record) => record.kind === kind && (location === "all" || Boolean(record.coordinates) === (location === "mapped")));
  const summaryAction = (kind: MapRecord["kind"], location: "all" | "mapped" | "unmapped" | "scenario", label: string) => {
    const records = location === "scenario" ? all.filter((record) => record.kind === kind) : summaryRecords(kind, location);
    const criteria = location === "scenario" ? "entire active scenario; map filters excluded" : `${summaryCriteria(kind)}${location === "all" ? "" : ` · location: ${location}`}`;
    return <button
      type="button"
      data-navigation-origin={`map-summary-${kind}-${location}`}
      disabled={!records.length}
      title={`Open the complete ${kind} inventory matching ${criteria}. Map list paging and viewport do not limit this population.`}
      onClick={(event) => onNavigate(kind === "incident"
        ? { type: "filter_incidents", filter: { kind: "incident_ids", ids: records.map((record) => record.id), label, source: "map_summary", criteria } }
        : { type: "filter_crews", filter: { kind: "crew_ids", ids: records.map((record) => record.id), label, source: "map_summary", criteria } }, event.currentTarget)}
    >{label} ({records.length.toLocaleString()})</button>;
  };
  const listed = unmappedOnly ? filtered.filter((r) => !r.coordinates) : filtered;
  const pageCount = Math.max(1, Math.ceil(listed.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount - 1);
  const selection = filtered.find((r) => r.key === selected);
  const related = useMemo(() => {
    if (!selection) return [];
    const references = selection.incident
      ? selection.incident.assigned_crews.map((assignment) => ({ key: `crew:${assignment.crew_id}`, name: assignment.crew_name }))
      : selection.crew?.assigned_incidents.map((assignment) => ({ key: `incident:${assignment.incident_id}`, name: assignment.incident_id })) ?? [];
    const byKey = new Map(all.map((record) => [record.key, record]));
    const visibleKeys = new Set(filtered.map((record) => record.key));
    return Array.from(new Map(references.map((reference) => [reference.key, reference])).values()).map((reference) => ({
      ...reference, record: byKey.get(reference.key), visible: visibleKeys.has(reference.key)
    }));
  }, [all, filtered, selection]);
  const relatedKeys = useMemo(() => new Set(related.filter((item) => item.visible).map((item) => item.key)), [related]);
  const connectors = useMemo((): Array<[[number, number], [number, number]]> => {
    if (!showRelationships || !selection?.coordinates) return [];
    return related.flatMap(({ record, visible }) => visible && record?.coordinates &&
      (record.coordinates[0] !== selection.coordinates![0] || record.coordinates[1] !== selection.coordinates![1])
      ? [[selection.coordinates!, record.coordinates]] : []);
  }, [related, selection, showRelationships]);
  const mapNavigationContext: NavigationResolverContext = {
    ...(navigationContext ?? { incidents, crews }),
    currentView: "map",
    currentEntity: selection ? { kind: selection.kind, id: selection.id } : undefined
  };
  const select = useCallback((key: string) => {
    setNavigationNotice("");
    setSelected(key);
  }, []);
  const activeFilterCount = [
    query.trim() !== "", region !== "all", !showIncidents, !showCrews, unmappedOnly,
    severity !== "all", hazard !== "all", criticalFacilityLevel !== "all", rankingStatus !== "all",
    customerImpact !== "all", assignmentState !== "all", incidentAge !== "all",
    crewStatus !== "all", crewCapability !== "all", crewReadiness !== "all", crewShift !== "all",
    crewAssignment !== "all", crewPreset !== "all"
  ].filter(Boolean).length;
  const openFilterPanel = (tab: MapFilterTab) => {
    focusOpenedTab.current = true;
    setFilterPanelTab(tab);
    setFilterPanelOpen(true);
  };
  const closeFilterPanel = () => {
    setFilterPanelOpen(false);
    filterTriggerRef.current?.focus();
  };
  const clearMapFilters = () => {
    setQuery("");
    setRegion("all");
    setShowIncidents(true);
    setShowCrews(true);
    setUnmappedOnly(false);
    setSeverity("all");
    setHazard("all");
    setCriticalFacilityLevel("all");
    setRankingStatus("all");
    setCustomerImpact("all");
    setAssignmentState("all");
    setIncidentAge("all");
    setCrewStatus("all");
    setCrewCapability("all");
    setCrewReadiness("all");
    setCrewShift("all");
    setCrewAssignment("all");
    setCrewPreset("all");
  };
  useEffect(() => {
    if (!filterPanelOpen || !focusOpenedTab.current) return;
    filterPanelRef.current?.querySelector<HTMLButtonElement>(`[data-map-filter-tab="${filterPanelTab}"]`)?.focus();
    focusOpenedTab.current = false;
  }, [filterPanelOpen, filterPanelTab]);
  useEffect(() => {
    if (skipInitialFilterReset.current) {
      skipInitialFilterReset.current = false;
      return;
    }
    setPage(0);
    setSelected((current) => current && filtered.some((record) => record.key === current) ? current : null);
    setNavigationNotice("");
  }, [crewAssignment, crewCapability, crewPreset, crewReadiness, crewShift, crewStatus, filtered, query, region, showIncidents, showCrews, unmappedOnly]);

  useEffect(() => {
    onStateChange?.({
      filterPanelOpen,
      filterPanelTab,
      showIncidents,
      showCrews,
      query,
      region,
      unmappedOnly,
      severity,
      hazard,
      criticalFacilityLevel,
      rankingStatus,
      customerImpact,
      assignmentState,
      incidentAge,
      encoding,
      crewStatus,
      crewCapability,
      crewReadiness,
      crewShift,
      crewAssignment,
      crewPreset,
      showRelationships,
      selected: selection?.key ?? null,
      page: currentPage,
      viewport
    });
  }, [assignmentState, crewAssignment, crewCapability, crewPreset, crewReadiness, crewShift, crewStatus, criticalFacilityLevel, currentPage, customerImpact, encoding, filterPanelOpen, filterPanelTab, hazard, incidentAge, onStateChange, query, rankingStatus, region, selection?.key, severity, showCrews, showIncidents, showRelationships, unmappedOnly, viewport]);

  useEffect(() => {
    if (!navigationTarget) return;
    const targetKey = `${navigationTarget.entityKind}:${navigationTarget.entityId}`;
    const targetRecord = all.find((record) => record.key === targetKey);
    if (!targetRecord) {
      setSelected(null);
      setNavigationNotice(`${navigationTarget.entityKind === "incident" ? "Incident" : "Crew"} ${navigationTarget.entityId} is not available in the active scenario.`);
      onNavigationHandled?.(navigationTarget.requestId);
      return;
    }

    const targetLayerVisible = targetRecord.kind === "incident" ? showIncidents : showCrews;
    if (query || region !== "all" || unmappedOnly || severity !== "all" || hazard !== "all" || criticalFacilityLevel !== "all" || rankingStatus !== "all" || customerImpact !== "all" || assignmentState !== "all" || incidentAge !== "all" || crewStatus !== "all" || crewCapability !== "all" || crewReadiness !== "all" || crewShift !== "all" || crewAssignment !== "all" || crewPreset !== "all" || !targetLayerVisible) {
      setQuery("");
      setRegion("all");
      setUnmappedOnly(false);
      setSeverity("all");
      setHazard("all");
      setCriticalFacilityLevel("all");
      setRankingStatus("all");
      setCustomerImpact("all");
      setAssignmentState("all");
      setIncidentAge("all");
      setCrewStatus("all");
      setCrewCapability("all");
      setCrewReadiness("all");
      setCrewShift("all");
      setCrewAssignment("all");
      setCrewPreset("all");
      if (targetRecord.kind === "incident") setShowIncidents(true);
      if (targetRecord.kind === "crew") setShowCrews(true);
      return;
    }

    const targetIndex = filtered.findIndex((record) => record.key === targetKey);
    setPage(Math.floor(Math.max(0, targetIndex) / PAGE_SIZE));
    setSelected(targetRecord.key);
    setNavigationNotice(targetRecord.coordinates
      ? `Showing ${targetRecord.kind} ${targetRecord.id} on the map.`
      : `${targetRecord.kind === "incident" ? "Incident" : "Crew"} ${targetRecord.id} is selected, but no map location is available.`);
    onNavigationHandled?.(navigationTarget.requestId);
  }, [all, assignmentState, crewAssignment, crewCapability, crewPreset, crewReadiness, crewShift, crewStatus, criticalFacilityLevel, customerImpact, filtered, hazard, incidentAge, navigationTarget, onNavigationHandled, query, rankingStatus, region, severity, showCrews, showIncidents, unmappedOnly]);

  const facetControl = (label: string, facet: IncidentFacetKey, value: string, setValue: (value: string) => void) => (
    <label>{label}<select aria-label={`Map ${label.toLowerCase()}`} value={value} onChange={(event) => setValue(event.target.value)}><option value="all">All {label.toLowerCase()}</option>{(facetOptionsByKey[facet] ?? []).map((option) => <option key={option.value} disabled={option.count === 0 && value !== option.value} value={option.value}>{option.label} ({option.count})</option>)}</select></label>
  );
  const crewFacetControl = (label: string, facet: CrewFacetKey, value: string, setValue: (value: string) => void) => (
    <label>{label}<select aria-label={`Map ${label.toLowerCase()}`} value={value} onChange={(event) => setValue(event.target.value)}><option value="all">All {label.toLowerCase()}</option>{(crewFacetOptionsByKey[facet] ?? []).map((option) => <option key={option.value} disabled={option.count === 0 && value !== option.value} value={option.value}>{option.label} ({option.count})</option>)}</select></label>
  );
  const filterTabs: MapFilterTab[] = ["incidents", "crews", "results"];
  const handleTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, tab: MapFilterTab) => {
    const current = filterTabs.indexOf(tab);
    const next = event.key === "ArrowRight" ? (current + 1) % filterTabs.length
      : event.key === "ArrowLeft" ? (current - 1 + filterTabs.length) % filterTabs.length
      : event.key === "Home" ? 0 : event.key === "End" ? filterTabs.length - 1 : -1;
    if (next < 0) return;
    event.preventDefault();
    const nextTab = filterTabs[next];
    setFilterPanelTab(nextTab);
    filterPanelRef.current?.querySelector<HTMLButtonElement>(`[data-map-filter-tab="${nextTab}"]`)?.focus();
  };

  return <section className="operations-map panel" aria-label="Operations Map workspace">
    <div className="operations-map-intro">
      <div><h2>Long Island operations</h2><p>Active scenario incidents and crew locations</p></div>
      <button type="button" onClick={() => { setSelected(null); setNavigationNotice(""); setHomeRequest((n) => n + 1); }}>Reset to Long Island</button>
    </div>
    <div className="operations-map-filter-anchor">
      <div className="operations-map-controls" role="group" aria-label="Map filters">
        <div className="operations-map-search">
          <AutocompleteSearch
            accessibleLabel="Search records"
            label="Search records"
            onChange={setQuery}
            placeholder="Incident, crew, village…"
            suggestions={autocompleteSuggestions}
            value={query}
          />
        </div>
        <label>Operating region<select value={region} onChange={(e) => setRegion(e.target.value)}><option value="all">All regions</option>{regions.map((r) => <option key={r}>{r}</option>)}</select></label>
        <label className="operations-map-toggle"><input type="checkbox" checked={showIncidents} onChange={(e) => setShowIncidents(e.target.checked)} />Incidents</label>
        <label className="operations-map-toggle"><input type="checkbox" checked={showCrews} onChange={(e) => setShowCrews(e.target.checked)} />Crews</label>
        <button ref={filterTriggerRef} type="button" className="operations-map-filter-trigger" aria-expanded={filterPanelOpen} aria-controls="operations-map-filter-panel" onClick={() => filterPanelOpen ? closeFilterPanel() : openFilterPanel(filterPanelTab)}>Filters &amp; results · {activeFilterCount} active</button>
      </div>
      <div className="operations-map-summary"><span role="status">{mappedIncidents.toLocaleString()} incidents mapped · {mappedCrews.toLocaleString()} crews mapped · {unmappedCount.toLocaleString()} without a map location</span><button type="button" onClick={() => openFilterPanel("results")}>Open results</button></div>
      <section ref={filterPanelRef} id="operations-map-filter-panel" className="operations-map-filter-panel" aria-label="Map filters and results" hidden={!filterPanelOpen} onKeyDown={(event) => { if (event.key === "Escape") { event.stopPropagation(); closeFilterPanel(); } }}>
        <div className="operations-map-filter-heading"><h3>Map filters &amp; results</h3><button type="button" onClick={closeFilterPanel}>Close</button></div>
        <div className="operations-map-filter-tabs" role="tablist" aria-label="Map filter categories">
          {filterTabs.map((tab) => <button key={tab} type="button" role="tab" id={`operations-map-tab-${tab}`} data-map-filter-tab={tab} aria-controls={`operations-map-panel-${tab}`} aria-selected={filterPanelTab === tab} tabIndex={filterPanelTab === tab ? 0 : -1} onClick={() => setFilterPanelTab(tab)} onKeyDown={(event) => handleTabKeyDown(event, tab)}>{tab === "incidents" ? "Incidents" : tab === "crews" ? "Crews" : "Results"}</button>)}
        </div>
        <div role="tabpanel" id="operations-map-panel-incidents" aria-labelledby="operations-map-tab-incidents" hidden={filterPanelTab !== "incidents"} className="operations-map-filter-body"><div className="operations-map-filter-fields">
          {facetControl("Severity", "severity", severity, setSeverity)}
          {facetControl("Hazard", "hazard", hazard, setHazard)}
          {facetControl("Critical-facility level", "criticalFacilityLevel", criticalFacilityLevel, setCriticalFacilityLevel)}
          {facetControl("Ranking status", "rankingStatus", rankingStatus, setRankingStatus)}
          {facetControl("Customer impact", "customerImpact", customerImpact, setCustomerImpact)}
          {facetControl("Assignment state", "assignmentState", assignmentState, setAssignmentState)}
          {facetControl("Incident age", "incidentAge", incidentAge, setIncidentAge)}
          <label>Marker encoding<select aria-label="Map marker encoding" value={encoding} onChange={(event) => setEncoding(event.target.value as MapEncoding)}><option value="severity">Severity color</option><option value="customers">Customer impact size</option><option value="age">Incident age size</option><option value="criticalFacility">Critical-facility color</option><option value="ranking">Ranking status color</option></select></label>
        </div></div>
        <div role="tabpanel" id="operations-map-panel-crews" aria-labelledby="operations-map-tab-crews" hidden={filterPanelTab !== "crews"} className="operations-map-filter-body"><div className="operations-map-filter-fields">
          {crewFacetControl("Crew status", "status", crewStatus, setCrewStatus)}
          {crewFacetControl("Crew capability", "capability", crewCapability, setCrewCapability)}
          {crewFacetControl("Crew readiness", "readiness", crewReadiness, setCrewReadiness)}
          {crewFacetControl("Crew shift remaining", "shift", crewShift, setCrewShift)}
          {crewFacetControl("Crew assignment", "assignment", crewAssignment, setCrewAssignment)}
          <label>Crew preset<select aria-label="Map crew preset" value={crewPreset} onChange={(event) => setCrewPreset(event.target.value)}><option value="all">All crews</option><option value="available-line">Available line crews</option></select></label>
        </div></div>
        <section role="tabpanel" id="operations-map-panel-results" aria-labelledby="operations-map-tab-results" hidden={filterPanelTab !== "results"} className="operations-map-drillup operations-map-filter-body">
          <p>Open complete inventories. Counts use the active map search and facets across the scenario, including records outside the viewport and current list page. “Unmapped only” changes the list below, not these counts.</p>
          <div className="operations-map-drillup-actions">
            {summaryAction("incident", "all", "Matching incidents")}
            {summaryAction("crew", "all", "Matching crews")}
            {summaryAction("incident", "mapped", "Mapped incidents")}
            {summaryAction("crew", "mapped", "Mapped crews")}
            {summaryAction("incident", "unmapped", "Unmapped incidents")}
            {summaryAction("crew", "unmapped", "Unmapped crews")}
          </div>
          <div className="operations-map-drillup-actions" aria-label="Broader scenario inventories">
            {summaryAction("incident", "scenario", "All scenario incidents")}
            {summaryAction("crew", "scenario", "All scenario crews")}
          </div>
          <p>Scenario totals exclude map filters. Destination inventories keep their own operational ordering.</p>
        </section>
        <div className="operations-map-filter-footer"><span>Selections update the map immediately</span><button type="button" disabled={activeFilterCount === 0} onClick={clearMapFilters}>Clear map filters</button></div>
      </section>
    </div>
    {selection && <label className="operations-map-relationship-toggle"><input type="checkbox" checked={showRelationships} onChange={(event) => setShowRelationships(event.target.checked)} /> Show assignment relationship connectors <span>(straight lines, not routes)</span></label>}
    {navigationNotice ? <p className="operations-map-navigation-notice" role="status">{navigationNotice}</p> : null}
    <div className="operations-map-layout">
      <div>
        <MapCanvas
          records={filtered}
          selected={selection?.key ?? null}
          relatedKeys={relatedKeys}
          connectors={connectors}
          onSelect={select}
          homeRequest={homeRequest}
          restoredViewport={restoredState?.viewport}
          onViewportChange={setViewport}
          encoding={encoding}
        />
        <div className="operations-map-legend" aria-label="Map legend">
          <span><b className="operations-legend-incident">!</b> Incident</span>
          <span><b className="operations-legend-crew">C</b> Crew</span>
          <span><b className="operations-legend-cluster">#</b> Grouped records — click to expand</span>
          {selection && <span><b className="operations-legend-related">◎</b> Selected or assigned record</span>}
          {connectors.length > 0 && <span><b className="operations-legend-relationship">┄</b> Assignment relationship, not a route</span>}
          <span>Encoding: {encodingLabel(encoding)}</span>
          {encoding === "severity" && <span className="operations-map-encoding-key" aria-label="Severity colors">
            <i className="operations-swatch operations-swatch-critical" aria-label="Critical severity" />Critical
            <i className="operations-swatch operations-swatch-high" aria-label="High severity" />High
            <i className="operations-swatch operations-swatch-medium" aria-label="Medium severity" />Medium
            <i className="operations-swatch operations-swatch-low" aria-label="Low severity" />Low
          </span>}
          {encoding === "criticalFacility" && <span className="operations-map-encoding-key" aria-label="Critical-facility colors">
            <i className="operations-swatch operations-swatch-critical-facility" aria-label="Critical facility" />Critical facility
            <i className="operations-swatch operations-swatch-unknown" aria-label="No or unknown critical facility" />No/unknown
          </span>}
          {encoding === "ranking" && <span className="operations-map-encoding-key" aria-label="Ranking status colors">
            <i className="operations-swatch operations-swatch-ranked" aria-label="Ranked" />Ranked
            <i className="operations-swatch operations-swatch-withheld" aria-label="Withheld" />Withheld
          </span>}
        </div>
        <p className="operations-map-note">Crew pins are approximate village centers, not live GPS. Incident pins use synthetic scenario coordinates. Multiple records can share a location.</p>
      </div>
      <aside className="operations-map-sidebar" aria-label="Map records and selection">
        {selection ? <div className="operations-map-detail">
          <div className="operations-map-detail-heading"><h3>{selection.title}</h3><button aria-label="Clear map selection" type="button" onClick={() => setSelected(null)}>×</button></div>
          <p>{selection.kind === "incident" ? "Incident" : "Crew"} · {selection.status.replace(/_/g, " ")}</p>
          <dl><dt>Location</dt><dd>{selection.location}</dd><dt>Region</dt><dd>{selection.region}</dd>
            {selection.incident && <><dt>Customers out</dt><dd>{selection.incident.customers_out.toLocaleString()}</dd><dt>Severity / hazard</dt><dd>{selection.detail}</dd><dt>Assigned crews</dt><dd>{related.length}</dd></>}
            {selection.crew && <><dt>Capability</dt><dd>{selection.crew.capability}</dd><dt>Assigned incidents</dt><dd>{related.length}</dd></>}
          </dl>
          <p>{!selection.coordinates ? "Location unavailable — this record is not plotted." : selection.kind === "crew" ? `Approximate center: ${selection.crew?.map_location?.village}` : "Synthetic incident location"}</p>
          <section className="operations-map-relationships" aria-label="Assignment relationships">
            <h3>Assignment relationships ({related.length})</h3>
            {related.length === 0 ? <p>No current assignments for this record.</p> : <ul>{related.map((item) => <li key={item.key}>
              <strong>{item.name}</strong>
              <span>{!item.record ? "Record unavailable in this scenario" : !item.visible ? "Hidden by current map filters" : !item.record.coordinates ? "Visible in list · location unavailable" : "Visible on map"}</span>
              {item.visible && <button type="button" onClick={() => { setPage(Math.floor(filtered.findIndex((record) => record.key === item.key) / PAGE_SIZE)); select(item.key); }}>Select {item.name} on map</button>}
              {item.record && <EntityNavigationActions accessibleLabel={`${item.name} destinations`} context={mapNavigationContext} destinationKinds={["full_detail"]} labelOverrides={{ full_detail: `Open ${item.name} details` }} onNavigate={onNavigate} reference={{ kind: item.record.kind, id: item.record.id }} />}
            </li>)}</ul>}
            {related.some((item) => item.visible && item.record?.coordinates && selection.coordinates &&
              item.record.coordinates[0] === selection.coordinates[0] && item.record.coordinates[1] === selection.coordinates[1]) &&
              <p>Some assigned records share a map point; no line appears between overlapping locations.</p>}
          </section>
          <ContextualNavigationPanel context={mapNavigationContext} onNavigate={onNavigate} reference={{ kind: selection.kind, id: selection.id }} />
        </div> : <div className="operations-map-help"><h3>Explore the scenario</h3><p>Select a marker or record for details. Open its incident or crew screen to continue the existing workflow.</p></div>}
        <div className="operations-map-list-heading"><h3>Records ({listed.length.toLocaleString()})</h3><label><input type="checkbox" checked={unmappedOnly} onChange={(e) => setUnmappedOnly(e.target.checked)} /> Unmapped only</label></div>
        <ul className="operations-map-records" aria-label="Map record list">{listed.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE).map((r) => <li key={r.key}><button type="button" aria-pressed={selection?.key === r.key} data-related={relatedKeys.has(r.key)} onClick={() => select(r.key)}><strong>{r.kind === "incident" ? "!" : "C"} · {r.title}</strong><span>{r.location} · {r.status.replace(/_/g, " ")}{!r.coordinates ? " · Unmapped" : ""}{relatedKeys.has(r.key) ? " · Assigned relationship" : ""}</span></button></li>)}</ul>
        {listed.length === 0 && <p>No records match these filters.</p>}
        <div className="operations-map-pagination"><button type="button" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Previous</button><span>{currentPage + 1} / {pageCount}</span><button type="button" disabled={currentPage + 1 >= pageCount} onClick={() => setPage(currentPage + 1)}>Next</button></div>
      </aside>
    </div>
  </section>;
}
