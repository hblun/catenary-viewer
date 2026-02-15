# Render Contract: Data to Tiles

This document defines the contract between the database (Maple ingestion) and the tile server (Harebell).

## Current Architecture

```
GTFS Feed → Maple → PostGIS → Harebell → MVT Tiles → Viewer
```

## Existing Tables (Read by Harebell)

### gtfs.routes

| Column | Type | Description | Needed for Tiles? |
|--------|------|-------------|------------------|
| route_id | text | Unique route identifier | ✅ Yes |
| short_name | text | Short name (e.g., "1", "X1") | ✅ Yes |
| long_name | text | Full route name | ✅ Yes |
| route_type | int2 | GTFS route type (0=Tram, 1=Subway, etc.) | ✅ Yes (for mode filter) |
| color | text | Hex color (e.g., "FF0000") | ✅ Yes |
| text_color | text | Text color for contrast | ✅ Yes |
| chateau | text | Operator/agency identifier | ✅ Yes (for operator filter) |
| agency_id | text | Legacy agency ID | ⚡ Maybe |

### gtfs.shapes

| Column | Type | Description | Needed for Tiles? |
|--------|------|-------------|------------------|
| shape_id | text | Shape identifier | ✅ Yes |
| linestring | geometry | Route geometry (LineString) | ✅ Yes |
| color | text | Override route color | ✅ Yes |
| route_label | text | Label for the route | ✅ Yes |
| text_color | text | Text color | ✅ Yes |
| routes | array | List of route_ids using this shape | ✅ Yes |
| route_type | int2 | Route type | ✅ Yes |
| chateau | text | Operator identifier | ✅ Yes |

### gtfs.stops

| Column | Type | Description | Needed for Tiles? |
|--------|------|-------------|------------------|
| gtfs_id | text | Stop identifier | ✅ Yes |
| name | text | Stop name | ✅ Yes |
| code | text | Stop code | ✅ Yes |
| point | geometry | Stop location (Point) | ✅ Yes |
| chateau | text | Operator identifier | ⚡ Maybe |
| routes | array | Routes serving this stop | ⚡ Maybe |

### gtfs.agencies

| Column | Type | Description | Needed for Tiles? |
|--------|------|-------------|------------------|
| agency_id | text | Agency identifier | ✅ Yes |
| agency_name | text | Agency/operator name | ✅ Yes (for display) |
| chateau | text | Maps to routes.chateau | ✅ Yes |

## Proposed Render Views

Create dedicated views for tile generation to simplify Harebell and make stripping safer.

### routes_render

```sql
CREATE VIEW routes_render AS
SELECT 
    r.route_id,
    r.short_name,
    r.long_name,
    r.route_type,
    COALESCE(r.color, s.color, '000000') AS color,
    COALESCE(r.text_color, s.text_color, 'FFFFFF') AS text_color,
    r.chateau AS operator_id,
    a.agency_name AS operator_name,
    s.shape_id,
    s.linestring AS geometry
FROM gtfs.routes r
LEFT JOIN gtfs.shapes s ON s.routes && ARRAY[r.route_id]
LEFT JOIN gtfs.agencies a ON a.chateau = r.chateau AND a.agency_id = r.agency_id
WHERE s.linestring IS NOT NULL;
```

### stops_render

```sql
CREATE VIEW stops_render AS
SELECT 
    s.gtfs_id AS stop_id,
    s.name AS stop_name,
    s.code AS stop_code,
    s.point AS geometry,
    s.chateau AS operator_id,
    a.agency_name AS operator_name
FROM gtfs.stops s
LEFT JOIN gtfs.agencies a ON a.chateau = s.chateau
WHERE s.point IS NOT NULL;
```

## Tile Layer Properties

### routes_base

Properties included in each feature:
```json
{
  "route_id": "string",
  "route_short_name": "string", 
  "route_long_name": "string",
  "operator_id": "string",
  "operator_name": "string",
  "mode": "string",  // derived from route_type
  "color": "string",
  "text_color": "string",
  "sort_key": "number"  // for line ordering
}
```

### stations/stops

Properties:
```json
{
  "stop_id": "string",
  "stop_name": "string",
  "stop_code": "string"
}
```

## Mode Mapping (GTFS route_type)

| route_type | mode |
|------------|------|
| 0 | tram |
| 1 | subway |
| 2 | rail |
| 3 | bus |
| 4 | ferry |
| 5 | cable_car |
| 6 | aerial_lift |
| 7 | funicular |
| 11 | trolleybus |
| 12 | monorail |

## Indexes Required

```sql
-- Spatial index on shapes
CREATE INDEX idx_shapes_geom ON gtfs.shapes USING GIST (linestring);

-- Spatial index on stops  
CREATE INDEX idx_stops_geom ON gtfs.stops USING GIST (point);

-- Index on routes for filtering
CREATE INDEX idx_routes_chateau ON gtfs.routes (chateau);
CREATE INDEX idx_routes_type ON gtfs.routes (route_type);

-- Index on agencies
CREATE INDEX idx_agencies_chateau ON gtfs.agencies (chateau);
```

## Future: Hitbox Layer

For reliable click detection on thin lines:

```sql
CREATE VIEW routes_hitbox AS
SELECT 
    route_id,
    ST_Buffer(linestring, 0.001) AS geometry  -- Buffer for click target
FROM routes_render;
```
