# Stripping Log

This document tracks the removal of services from the Catenary backend to create a viewer-only stack.

## Status: In Progress

## Removed/To Remove from Backend

### Services Removed (Not compiled)

| Service | Path | Reason |
|---------|------|--------|
| Edelweiss | `src/edelweiss/` | Routing engine - not needed for viewing |
| Aspen | `src/aspen/` | Realtime processing |
| Alpenrose | `src/alpenrose/` | GTFS-rt ingestion |
| Spruce | `src/spruce/` | WebSocket for vehicle locations |
| Gentian | `src/gentian/` | Graph generation task server |
| Linnaea | `src/linnaea/` | Graph visualization |
| Avens | `src/avens/` | OSM preprocessing |
| Sage | `src/sage/` | Rail stop queries |
| Cholla | `src/cholla/` | Unclear purpose |
| Prairie | `src/prairie/` | Routing preprocessing |

### Dependencies to Remove

From `Cargo.toml`, these dependencies are only used by removed services:

- `travic_types` (if only for routing)
- Some Elasticsearch dependencies
- Some Redis dependencies  
- Some Actix-web components (if only for removed APIs)

### Keep (Viewer-Related)

| Service | Path | Reason |
|---------|------|--------|
| Maple | `src/maple/` | GTFS ingestion to PostGIS |
| Harebell | `src/harebell/` | MVT tile generation |
| Birch | `src/birch/` | Optional: search API only |

## Proposed Feature Flags

Add to `Cargo.toml`:

```toml
[features]
default = ["maple", "harebell"]
maple = []
harebell = []
birch = ["optional"]  # Only if search API needed
routing = ["edelweiss", "gentian", "avens"]
realtime = ["aspen", "alpenrose", "spruce"]
```

## Frontend Stripping

### To Disable/Remove

1. **Realtime vehicle locations**
   - Remove `process_realtime_data.ts`
   - Remove `fetch_realtime_vehicle_locations.ts`
   - Remove WebSocket connection in `spruce_websocket.ts`
   - Disable vehicle layer in map

2. **Departure boards**
   - Remove `NearbyDepartures.svelte`
   - Remove departures API calls

3. **Routing features**
   - Remove trip planning UI
   - Remove journey result display

### To Keep/Enhance

1. **Route selection**
   - Keep click handling in `mapClickHandler.ts`
   - Enhance with multi-select support

2. **Filtering**
   - Keep `filterState.ts`
   - Enhance with operator chips

3. **URL state**
   - Add query param encoding for shareable links

## Build Verification

After stripping:

```bash
# Should compile only viewer components
cargo build --features maple,harebell

# Should NOT compile removed services
```

## Migration Notes

1. **Database schema unchanged** - routes, stops, shapes tables remain
2. **Tile output format unchanged** - existing harebell_viewer.html works
3. **Breaking changes**: 
   - No realtime vehicle positions
   - No API for departure times
   - No routing/trip planning

## Date: 2026-02-14
