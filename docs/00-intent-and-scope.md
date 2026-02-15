# Intent and Scope

## Product Vision

A viewer-first transit map product that renders routes and stops cleanly with support for click, hover, multi-select, and filter interactions. Focus on UK transit data.

## Non-Goals (Out of Scope)

The following are explicitly NOT part of this viewer product:

- **Routing/Trip Planning**: No journey planning, no origin-destination queries
- **Realtime Vehicle Tracking**: No live vehicle positions, no GTFS-rt ingestion
- **Disruption/Alert Handling**: No service alerts, no delay predictions
- ** Fare Calculation**: No fare lookup or ticketing integration
- **Stop Departure Boards**: No real-time departure information

## Viewer Behaviors (MVP)

### Map Interactions

- [x] Pan/zoom vector map with routes and stops
- [x] Hover tooltip on routes and stops
- [x] Click a route to select and highlight it
- [x] Click again to unselect
- [x] Multi-select routes (Shift+click to pin a set)
- [x] Filter by operator using chips/toggles
- [x] Filter by mode (Rail, Metro/Tram, Bus, Other) using chips/toggles
- [x] Clear selections and reset filters
- [x] Sidebar panel showing selected route(s) details
- [x] URL state preservation for shareable links

### Data Layers

Routes rendered as vector lines with:

- route_id
- route_short_name
- route_long_name
- operator_id / agency_id
- operator_name
- mode (derived from GTFS route_type)
- colour (post colour-correction)
- text_colour
- sort_key / z_order (for line ordering)

Stops rendered as points with:

- stop_id
- stop_name
- stop_code
- locality / admin fields (if available)

## Tile Schema

### Layer: routes_base

Regular route rendering with all properties needed for filtering.

### Layer: routes_hitbox

Transparent thicker line for reliable click detection.

### Layer: routes_selected

Only selected route_ids, thicker/brighter styling.

### Layer: routes_dimmed

Optional: inverse set at low opacity when filtering is active.

### Layer: stops_base

Station/stop points.

### Layer: stops_selected

Highlighted stops.

## API Contracts (Future)

Optional tiny API for:

- GET /routes?query=&operator=&mode=&limit=
- GET /stops?query=&limit=
- GET /route/{route_id}
- GET /stop/{stop_id}
