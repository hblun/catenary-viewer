# Tile Schema for Viewer Interaction

This document specifies the tile layers and properties needed to support the viewer interactions defined in 00-intent-and-scope.md.

## Current Tile Properties

### transit layer (routes)

```json
{
  "line_id": "string",
  "color": "#RRGGBB",
  "chateau_id": "string",
  "route_id": "string",
  "offset": "number"
}
```

### stations layer (stops)

```json
{
  "name": "string"
}
```

## Required Properties for Viewer

### For Routes (transit layer)

| Property | Type | Required | Purpose |
|----------|------|----------|---------|
| route_id | string | ✅ Yes | Unique identifier for selection |
| route_short_name | string | ✅ Yes | Display name (e.g., "1", "X1") |
| route_long_name | string | ✅ Yes | Full name |
| operator_id | string | ✅ Yes | Filter by operator (maps to chateau) |
| operator_name | string | ✅ Yes | Display operator name |
| mode | string | ✅ Yes | Filter by mode (rail, bus, tram, etc.) |
| color | string | ✅ Yes | Route color |
| text_color | string | ✅ Yes | Contrast text color |
| sort_key | number | ❌ Optional | Line ordering |

### For Stops (stations layer)

| Property | Type | Required | Purpose |
|----------|------|----------|---------|
| stop_id | string | ✅ Yes | Unique identifier |
| stop_name | string | ✅ Yes | Display name |
| stop_code | string | ❌ Optional | Short code |

## Proposed Layer Structure

### Layer: routes_base

Base rendering of all routes. Filterable by operator and mode.

### Layer: routes_hitbox

Transparent thicker line for reliable click detection on thin routes.

Implementation: Same geometry as routes_base but with:
- Higher `line-width` in style
- `line-opacity: 0` (invisible but clickable)

### Layer: routes_selected

Only selected route_ids. Higher z-index, brighter styling.

Implementation: Filtered copy of routes_base with:
- `['in', ['get', 'route_id'], ['literal', selected_ids]]`
- Thicker line-width
- Brighter colors

### Layer: routes_dimmed (optional)

When filters active, show non-matching routes at low opacity.

Implementation:
- `['!', ['in', ['get', 'route_id'], ['literal', filtered_ids]]]`
- `line-opacity: 0.2`

### Layer: stops_base

Stop points.

### Layer: stops_selected

Highlighted stops when their route is selected.

## Implementation Steps

### 1. Update Harebell loader.rs

Add route_type and short_name to the render graph:

```rust
// In loader.rs, load from routes table:
let routes_data = routes_dsl::routes
    .select((
        routes_dsl::chateau,
        routes_dsl::route_id,
        routes_dsl::short_name,
        routes_dsl::long_name,
        routes_dsl::route_type,
        routes_dsl::color,
        routes_dsl::text_color,
    ))
    .load::<(...)>(&mut conn)?;
```

### 2. Update graph.rs

Add new fields to LineOnEdge struct:

```rust
pub struct LineOnEdge {
    // Existing fields
    pub line_id: String,
    pub color: String,
    pub chateau_id: String,
    pub route_id: String,
    
    // New fields
    pub short_name: Option<String>,
    pub long_name: Option<String>,
    pub route_type: i16,
    pub text_color: Option<String>,
}
```

### 3. Update tile_gen.rs

Add new properties to features:

```rust
feature.add_tag_string("route_short_name", &line.short_name);
feature.add_tag_string("route_long_name", &line.long_name);
feature.add_tag_string("mode", &route_type_to_mode(line.route_type));
feature.add_tag_string("operator_id", &line.chateau_id);
feature.add_tag_string("operator_name", &line.operator_name);
feature.add_tag_string("text_color", &line.text_color);
```

### 4. Update Viewer

Update harebell_viewer.html to use new properties:

```javascript
map.addLayer({
    id: 'transit-lines',
    type: 'line',
    source: 'harebell',
    'source-layer': 'transit',
    filter: ['all', 
        ['==', ['get', 'mode'], 'bus'],  // or other filters
    ],
    paint: {
        'line-color': ['get', 'color'],
        // ...
    }
});
```

## Mode Mapping

```javascript
const ROUTE_TYPE_TO_MODE = {
    0: 'tram',
    1: 'subway',
    2: 'rail',
    3: 'bus',
    4: 'ferry',
    5: 'cable_car',
    6: 'aerial_lift',
    7: 'funicular',
    11: 'trolleybus',
    12: 'monorail'
};
```

## Filter UI Specification

### Operator Chips

- Fetch unique operator_id/operator_name from tiles or API
- Toggle button for each operator
- Multi-select supported

### Mode Toggles

Fixed set: Rail, Metro/Tram, Bus, Other

- Toggle buttons for each mode
- Filter transit layer by mode property
