# Viewer Interactions Specification

This document defines the exact interaction behaviors for the viewer UI.

## Interaction Spec

### Hover

- **Trigger**: Mouse enters route line
- **Action**: Show tooltip with route info
- **Tooltip content**: `route_short_name` - `route_long_name`
- **Visual**: Cursor changes to pointer

### Click Select

- **Trigger**: Click on route line
- **Action**: Toggle selection state
- **If not selected**: Add route_id to selected set, highlight in routes_selected layer
- **If already selected**: Remove from selected set, remove highlight
- **Visual**: Selected routes render thicker/brighter

### Multi-Select (Shift+Click)

- **Trigger**: Shift+Click on route line
- **Action**: Add/remove from selected set without affecting others
- **Visual**: All selected routes highlighted

### Filter by Operator

- **Trigger**: Click operator chip
- **Action**: Toggle operator in filter set
- **Effect**: Update routes_base layer filter
- **Visual**: 
  - Active operators: solid background
  - Inactive operators: outlined

### Filter by Mode

- **Trigger**: Click mode toggle (Rail, Metro/Tram, Bus, Other)
- **Action**: Toggle mode in filter set
- **Effect**: Update routes_base layer filter

### Pin Selection

- **Trigger**: Click "Pin" button on selected route
- **Action**: Mark route as pinned
- **Effect**: Route stays selected even when filters change

### Clear/Reset

- **Trigger**: Click "Clear" or "Reset" button
- **Action**: Clear all selections and reset filters
- **Effect**: All routes visible, no selection

## URL State Encoding

State should be encoded in URL query parameters for shareability.

### Query Parameters

| Parameter | Type | Example |
|-----------|------|---------|
| routes | comma-separated | `?routes=1,2,3` |
| operator | string | `?operator=tfl` |
| mode | comma-separated | `?mode=rail,bus` |
| pinned | comma-separated | `?pinned=1,2` |

### Examples

```
# Single route selected
https://viewer.example.com/?routes=1

# Multiple routes selected
https://viewer.example.com/?routes=1,2,X1

# Filter by operator
https://viewer.example.com/?operator=scotrail

# Filter by mode
https://viewer.example.com/?mode=rail

# Combined filters
https://viewer.example.com/?mode=rail,bus&operator=scotrail

# Pinned selection (persists through filter changes)
https://viewer.example.com/?routes=1&pinned=1
```

### URL State Parser

```javascript
function parseURLState() {
    const params = new URLSearchParams(window.location.search);
    return {
        routes: params.get('routes')?.split(',') || [],
        operator: params.get('operator'),
        mode: params.get('mode')?.split(',') || [],
        pinned: params.get('pinned')?.split(',') || []
    };
}

function updateURLState(state) {
    const params = new URLSearchParams();
    if (state.routes.length) params.set('routes', state.routes.join(','));
    if (state.operator) params.set('operator', state.operator);
    if (state.mode.length) params.set('mode', state.mode.join(','));
    if (state.pinned.length) params.set('pinned', state.pinned.join(','));
    
    const newURL = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState(null, '', newURL);
}
```

## Sidebar Panel

### Route Details

When routes are selected, show sidebar with:

- Route short name (large)
- Route long name
- Operator name
- Mode icon
- Color indicator

### Implementation

```javascript
// On route click
map.on('click', 'transit-lines', (e) => {
    const props = e.features[0].properties;
    const routeId = props.route_id;
    
    if (e.originalEvent.shiftKey) {
        // Multi-select
        toggleRouteSelection(routeId);
    } else {
        // Single select
        setSelectedRoute(routeId);
    }
    
    updateSidebar();
    updateURLState();
});
```

## Filter Chips

### Operator Chips

- Fetch unique operators from tiles or API
- Render as toggle buttons
- Update filter on change

### Mode Toggles

- Fixed set: Rail, Metro/Tram, Bus, Other
- Render as toggle buttons  
- Update filter on change

### Filter Logic

```javascript
function buildRouteFilter(state) {
    const filters = [];
    
    // Mode filter
    if (state.mode.length > 0) {
        filters.push(['in', ['get', 'mode'], ['literal', state.mode]]);
    }
    
    // Operator filter
    if (state.operator) {
        filters.push(['==', ['get', 'operator_id'], state.operator]);
    }
    
    if (filters.length === 0) return null;
    return filters.length === 1 ? filters[0] : ['all', ...filters];
}
```
