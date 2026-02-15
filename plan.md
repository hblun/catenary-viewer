# Catenary Viewer-Only Stack Reduction

## Overview

This project reduces the Catenary transit stack to a viewer-first product: a fast map that renders routes and stops cleanly, supporting click, hover, multi-select, and filter interactions.

## Goals

- **Keep**: Shape generation → stored geometry → vector tiles → viewer UI
- **Remove**: Routing engines, realtime, disruption tooling, and non-viewer services
- **Outcome**: Easy to run locally, easy to deploy, clear data contract

## Success Criteria

- User can open map, click a line, filter by operator/mode, search routes/stops
- Shareable URL that preserves selections

---

## Work Items

### Phase 1: Definition & Documentation

- [x] 1.1 docs/00-intent-and-scope.md - Viewer behaviours, non-goals, tile properties
- [x] 1.2 Explore existing backend (Maple, Harebell) structure
- [x] 1.3 Explore existing frontend structure

### Phase 2: Baseline & Contract

- [x] 2.1 docs/01-baseline-run.md - Setup instructions, commands, env vars
- [x] 2.2 docs/02-render-contract.md - routes_render/stops_render tables
- [x] 2.3 docs/03-architecture.md - Thin architecture diagram

### Phase 3: Implementation

- [x] 3.1 Set up docker-compose for PostGIS
- [x] 3.2 Strip backend to Maple + Harebell only (documented in stripping-log)
- [x] 3.3 Configure tile layers for interaction (hitbox, selected, dimmed)
- [x] 3.4 Strip frontend to viewer-only (viewer.html created)
- [x] 3.5 Add URL state encoding for shareable filters/selections

### Phase 4: Documentation & Validation

- [x] 4.1 docs/04-stripping-log.md - What was removed and why
- [x] 4.2 README.md created
