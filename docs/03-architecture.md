# Architecture: Thin Viewer Stack

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Viewer (Browser)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐│
│  │  MapLibre  │  │  Selection  │  │  URL State (Shareable)  ││
│  │     UI     │  │   State     │  │  ?routes=...&operator=.. ││
│  └─────────────┘  └─────────────┘  └─────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Harebell (Tile Server)                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  GET /tiles/{z}/{x}/{y}.pbf                                ││
│  │  Layers: routes_base, routes_hitbox, stops_base             ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PostGIS Database                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐│
│  │   routes    │  │   shapes    │  │        stops            ││
│  │  (tables)   │  │  (geometry) │  │       (points)          ││
│  └─────────────┘  └─────────────┘  └─────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Maple (GTFS Ingestion)                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Reads GTFS feeds → writes to PostGIS                       ││
│  │  Creates routes, stops, shapes tables                       ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Why This Architecture

### Decision: MVT-Based Viewer

**Benefits:**
1. **Client-side filtering**: All filterable properties are in tile properties
2. **Fast interaction**: No API calls for click/hover/filter
3. **Small payloads**: Only visible data loads
4. **Simple backend**: Just serves tiles

**Trade-offs:**
- Cannot search routes/stops by name (requires API)
- Cannot show detailed route info without API
- Tile size grows with property richness

### Decision: Keep Maple + Harebell

**Maple (Ingestion):**
- Already handles GTFS parsing
- Creates PostGIS geometry from shapes
- Manages routes/stops tables
- Proven with real feeds

**Harebell (Tiles):**
- Already generates MVT tiles
- Uses existing routes/shapes tables
- Can be simplified for viewer-only

## Components to Keep

| Component | Status | Reason |
|-----------|--------|--------|
| Maple | ✅ Keep | GTFS ingestion |
| Harebell | ✅ Keep | Tile generation |
| PostGIS | ✅ Keep | Geometry storage |
| Birch (API) | ⚡ Optional | Only for search/details |

## Components to Remove

| Component | Status | Reason |
|-----------|--------|--------|
| Edelweiss | ❌ Remove | Routing engine |
| Aspen | ❌ Remove | Realtime processing |
| Alpenrose | ❌ Remove | GTFS-rt ingestion |
| Spruce | ❌ Remove | WebSocket (vehicle locs) |
| Gentian | ❌ Remove | Graph generation |
| Linnaea | ❌ Remove | Visualization/debugging |
| Avens | ❌ Remove | OSM preprocessing |
| Sage | ❌ Remove | Rail stop queries |

## Data Flow

### Ingestion (Maple)

```
UK GTFS Feed → Unzip → Parse → routes table
                              → stops table  
                              → shapes table (with geometry)
                              → trips, calendar, etc.
```

### Tile Generation (Harebell)

```
PostGIS routes/shapes → Load geometries → Simplify → MVT tiles
                                              ↓
                                    routes_base layer
                                    routes_hitbox layer
                                    stops_base layer
```

### Viewer Interaction

```
User clicks map → get feature properties → check selected state
                → update selection → highlight in routes_selected layer
                
User toggles filter → map.setFilter() → routes_base layer updates
                                           (client-side!)
```

## Optional: Search API

For route/stop search, add minimal API endpoints:

```
GET /api/routes?q=...&operator=...&mode=...
GET /api/stops?q=...
GET /api/routes/:id
```

This can be:
1. A simple read-only endpoint from Harebell
2. A separate small service
3. Integrated into Birch (if keeping for other reasons)

## Environment

```bash
# Development
DATABASE_URL=postgres://catenary:catenary@localhost:5432/catenary

# Production (example)
DATABASE_URL=postgres://user:pass@postgres:5432/catenary
HATEBBELL_PORT=8080
```
