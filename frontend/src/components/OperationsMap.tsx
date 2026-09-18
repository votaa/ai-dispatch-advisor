import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet.markercluster";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import type { Crew, Incident } from "../types";
import { AutocompleteSearch, buildAutocompleteSuggestions } from "./AutocompleteSearch";
import type { AutocompleteField } from "./AutocompleteSearch";
import "./OperationsMap.css";

// Initial framing only: panning remains unrestricted, including surrounding NYC.
const LONG_ISLAND_BOUNDS: L.LatLngBoundsExpression = [[40.48, -74.12], [41.19, -71.80]];
const PAGE_SIZE = 20;
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

function markerIcon(kind: MapRecord["kind"]) {
  return L.divIcon({
    className: `operations-marker operations-marker-${kind}`,
    html: kind === "incident" ? "!" : "C", iconSize: [28, 28], iconAnchor: [14, 14]
  });
}

function MapCanvas({ records, selected, onSelect, homeRequest }: {
  records: MapRecord[]; selected: string | null; onSelect: (key: string) => void; homeRequest: number;
}) {
  const element = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const clusters = useRef<L.MarkerClusterGroup | null>(null);
  const markers = useRef(new Map<string, L.Marker>());
  const tiles = useRef<L.TileLayer | null>(null);
  const [tileError, setTileError] = useState(false);

  useEffect(() => {
    if (!element.current) return;
    const instance = L.map(element.current, { maxZoom: 18, minZoom: 5, zoomSnap: 0.25 });
    instance.fitBounds(LONG_ISLAND_BOUNDS, { padding: [24, 24] });
    const tileLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(instance);
    tileLayer.on("tileerror", () => setTileError(true));
    const group = L.markerClusterGroup({
      maxClusterRadius: 42, showCoverageOnHover: false, animate: false,
      spiderfyOnMaxZoom: true,
      iconCreateFunction: (cluster) => L.divIcon({
        html: `<span aria-label="${cluster.getChildCount()} grouped records">${cluster.getChildCount()}</span>`, className: "operations-cluster",
        iconSize: [38, 38]
      })
    }).addTo(instance);
    L.control.scale({ imperial: true, metric: false }).addTo(instance);
    map.current = instance; clusters.current = group; tiles.current = tileLayer;
    const observer = new ResizeObserver(() => instance.invalidateSize({ pan: false }));
    observer.observe(element.current);
    return () => {
      observer.disconnect(); instance.remove();
      map.current = null; clusters.current = null; tiles.current = null; markers.current.clear();
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
        icon: markerIcon(record.kind), title: label, alt: label, keyboard: true
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
  }, [records, onSelect]);

  useEffect(() => {
    if (!selected) return;
    const marker = markers.current.get(selected);
    if (marker) clusters.current?.zoomToShowLayer(marker, () => marker.openTooltip());
  }, [selected, records]);

  useEffect(() => {
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

export default function OperationsMap({ incidents, crews, onOpenIncident, onOpenCrew }: {
  incidents: Incident[]; crews: Crew[]; onOpenIncident: (id: string) => void; onOpenCrew: (id: string) => void;
}) {
  const [showIncidents, setShowIncidents] = useState(true);
  const [showCrews, setShowCrews] = useState(true);
  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("all");
  const [unmappedOnly, setUnmappedOnly] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [homeRequest, setHomeRequest] = useState(0);
  const all = useMemo(() => mapRecords(incidents, crews), [incidents, crews]);
  const regions = useMemo(() => Array.from(new Set(all.map((r) => r.region))).sort(), [all]);
  const suggestionRecords = useMemo(() => all.filter((record) =>
    (record.kind === "incident" ? showIncidents : showCrews) &&
    (region === "all" || record.region === region)
  ), [all, region, showIncidents, showCrews]);
  const autocompleteSuggestions = useMemo(
    () => buildAutocompleteSuggestions(suggestionRecords, mapAutocompleteFields, query),
    [query, suggestionRecords]
  );
  const filtered = useMemo(() => {
    const search = query.toLowerCase().trim();
    return all.filter((r) => (r.kind === "incident" ? showIncidents : showCrews) &&
      (region === "all" || r.region === region) &&
      `${r.title} ${r.id} ${r.location} ${r.detail} ${r.status}`.toLowerCase().includes(search));
  }, [all, query, region, showIncidents, showCrews]);
  const unmappedCount = filtered.filter((r) => !r.coordinates).length;
  const mappedIncidents = filtered.filter((r) => r.kind === "incident" && r.coordinates).length;
  const mappedCrews = filtered.filter((r) => r.kind === "crew" && r.coordinates).length;
  const listed = unmappedOnly ? filtered.filter((r) => !r.coordinates) : filtered;
  const pageCount = Math.max(1, Math.ceil(listed.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount - 1);
  const selection = filtered.find((r) => r.key === selected);
  const select = useCallback((key: string) => setSelected(key), []);
  useEffect(() => { setPage(0); setSelected(null); }, [query, region, showIncidents, showCrews, unmappedOnly]);

  return <section className="operations-map panel" aria-label="Operations Map workspace">
    <div className="operations-map-intro">
      <div><h2>Long Island operations</h2><p>Active scenario incidents and crew locations</p></div>
      <button type="button" onClick={() => { setSelected(null); setHomeRequest((n) => n + 1); }}>Reset to Long Island</button>
    </div>
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
    </div>
    <p className="operations-map-summary" role="status">{mappedIncidents.toLocaleString()} incidents mapped · {mappedCrews.toLocaleString()} crews mapped · {unmappedCount.toLocaleString()} without a map location · {all.length.toLocaleString()} total scenario records</p>
    <div className="operations-map-layout">
      <div>
        <MapCanvas records={filtered} selected={selection?.key ?? null} onSelect={select} homeRequest={homeRequest} />
        <div className="operations-map-legend"><span><b className="operations-legend-incident">!</b> Incident</span><span><b className="operations-legend-crew">C</b> Crew</span><span><b className="operations-legend-cluster">#</b> Grouped records — click to expand</span></div>
        <p className="operations-map-note">Crew pins are approximate village centers, not live GPS. Incident pins use synthetic scenario coordinates. Multiple records can share a location.</p>
      </div>
      <aside className="operations-map-sidebar" aria-label="Map records and selection">
        {selection ? <div className="operations-map-detail">
          <div className="operations-map-detail-heading"><h3>{selection.title}</h3><button aria-label="Clear map selection" type="button" onClick={() => setSelected(null)}>×</button></div>
          <p>{selection.kind === "incident" ? "Incident" : "Crew"} · {selection.status.replace(/_/g, " ")}</p>
          <dl><dt>Location</dt><dd>{selection.location}</dd><dt>Region</dt><dd>{selection.region}</dd>
            {selection.incident && <><dt>Customers out</dt><dd>{selection.incident.customers_out.toLocaleString()}</dd><dt>Severity / hazard</dt><dd>{selection.detail}</dd><dt>Assigned crews</dt><dd>{selection.incident.assigned_crews.length}</dd></>}
            {selection.crew && <><dt>Capability</dt><dd>{selection.crew.capability}</dd><dt>Assigned incidents</dt><dd>{selection.crew.assigned_incidents.map((r) => r.incident_id).join(", ") || "None"}</dd></>}
          </dl>
          <p>{!selection.coordinates ? "Location unavailable — this record is not plotted." : selection.kind === "crew" ? `Approximate center: ${selection.crew?.map_location?.village}` : "Synthetic incident location"}</p>
          <button type="button" onClick={() => selection.kind === "incident" ? onOpenIncident(selection.id) : onOpenCrew(selection.id)}>{selection.kind === "incident" ? "Open incident" : "Open crew board"}</button>
        </div> : <div className="operations-map-help"><h3>Explore the scenario</h3><p>Select a marker or record for details. Open its incident or crew screen to continue the existing workflow.</p></div>}
        <div className="operations-map-list-heading"><h3>Records ({listed.length.toLocaleString()})</h3><label><input type="checkbox" checked={unmappedOnly} onChange={(e) => setUnmappedOnly(e.target.checked)} /> Unmapped only</label></div>
        <ul className="operations-map-records" aria-label="Map record list">{listed.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE).map((r) => <li key={r.key}><button type="button" aria-pressed={selection?.key === r.key} onClick={() => select(r.key)}><strong>{r.kind === "incident" ? "!" : "C"} · {r.title}</strong><span>{r.location} · {r.status.replace(/_/g, " ")}{!r.coordinates ? " · Unmapped" : ""}</span></button></li>)}</ul>
        {listed.length === 0 && <p>No records match these filters.</p>}
        <div className="operations-map-pagination"><button type="button" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Previous</button><span>{currentPage + 1} / {pageCount}</span><button type="button" disabled={currentPage + 1 >= pageCount} onClick={() => setPage(currentPage + 1)}>Next</button></div>
      </aside>
    </div>
  </section>;
}
