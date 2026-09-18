# Operations Map (POC-035)

## Scope

A single read-only geographic view of the active synthetic scenario. The default bounding box is southwest `(40.48, -74.12)` to northeast `(41.19, -71.80)`, with padding. It covers Long Island, Nassau, Suffolk, and the Rockaway Peninsula, with surrounding NYC and coastal context. Users can pan freely and reset to this extent.

## Behavior

- Incident pins use the scenario latitude/longitude. Crew pins use the village center resolved by the backend's shared geography registry from `current_location`, including approved aliases. Crew home region remains the operating-region filter; it is not used to infer physical location.
- Round red `!` markers identify incidents; square blue `C` markers identify crews. Navy clusters count records, not customers, distinct locations, or incidents alone. Clicking clusters expands them; coincident points spread apart for selection.
- Search covers IDs, names, named locations, incident severity/hazard, crew capability, and status over the complete active inventory. Layer toggles and the operating-region filter affect the map and list together. The paginated record list contains 20 records per page and never caps the plotted inventory.
- Counts describe filtered records with valid map locations, plus filtered unmapped records and the full scenario population. They are independent of the current map viewport. The `Unmapped only` checkbox filters the record list only, allowing missing positions to be inspected without hiding mapped context.
- Selecting a marker or list item displays details. `Open incident` opens the existing incident detail workflow; `Open crew board` selects that crew in the existing Crew Board. No map control dispatches, reassigns, changes recommendations, or writes data.
- Scenario changes reset filters, selection, and extent. Map modules load only when the tab is opened. Map resizing follows the application container.
- Invalid or missing coordinates remain in the list as unmapped. Unknown staging-area names are not assigned guessed coordinates. Older crew API responses without `map_location` also remain unmapped.
- Tile failures show an explicit warning and retry control. The record list and locally rendered markers remain available. The map requires an internet connection for its basemap.

## Basemap

Uses [Leaflet 1.9.4](https://leafletjs.com/reference.html), [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster), and standard OpenStreetMap raster tiles with visible attribution. Normal browser caching is preserved; no bulk downloads or prefetch are performed. Follow the [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/) and review provider capacity before expanding beyond the POC.

## Data limitations and deferred work

The `base` scenario has fictional named crew locations outside the Long Island registry and therefore shows unmapped crews. `long-island-copilot-demo` resolves all 32 crew locations. `august-storm-preview-v3` resolves 445 of 500 crews; 55 staging-location records remain unmapped. Incident coordinates remain synthetic and are not claims of actual equipment or customer positions.

Explicit operations-center/staging-area coordinates, live GPS, road routing, electrical topology, outage-area polygons, weather overlays, and map-based dispatch actions are outside this scope.

## Validation

Validate authoritative center resolution and unknown-location handling; full-scale inventory; layer and search filtering across all pages; selection links; coincident points; scenario reset; invalid coordinates; tile failure/retry; keyboard access; desktop and narrow-screen layouts. No existing scenario fixtures are regenerated.
