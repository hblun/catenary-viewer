# Catenary Viewer-Only Stack

A reduced, viewer-first transit map stack focused on UK/Scotland data. Renders routes and stops cleanly with support for click, hover, multi-select, and filter interactions.

## Architecture

```
GTFS → Maple → PostGIS → Harebell → MVT Tiles → Viewer (MapLibre)
                                    ↓
                            Birch (Search API)
```

## Quick Start (Ubuntu Server)

```bash
# 1. Install dependencies
sudo apt install -y protobuf-compiler pkg-config libssl-dev build-essential cmake git
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 2. Clone and build
git clone https://github.com/CatenaryTransit/catenary-backend.git
cd catenary-backend
cargo build --release --bin maple harebell birch

# 3. Start PostgreSQL
docker run -d --name catenary_postgres \
  -e POSTGRES_USER=catenary -e POSTGRES_PASSWORD=catenary -e POSTGRES_DB=catenary \
  -p 5432:5432 postgis/postgis:16-3.4

# 4. Ingest GTFS
export DATABASE_URL="postgres://catenary:catenary@localhost:5432/catenary"
./target/release/maple --gtfs /path/to/scotland-gtfs.zip

# 5. Start tile server
./target/release/harebell serve --port 8080

# 6. View at http://localhost:8081
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

## Services

| Service | Purpose | Command |
|---------|---------|---------|
| **Maple** | GTFS ingestion | `./target/release/maple --gtfs <file>` |
| **Harebell** | Tile server | `./target/release/harebell serve --port 8080` |
| **Birch** | Search API | `./target/release/birch` |
| **Viewer** | Web UI | `python3 -m http.server 8081` |

## Features

- [x] Pan/zoom vector map with routes and stops
- [x] Hover tooltip on routes
- [x] Click to select route
- [x] Shift+click for multi-select
- [x] Filter by mode (Rail, Metro/Tram, Bus, Other)
- [x] Filter by operator
- [x] URL state for shareable links
- [x] Pin routes to persist through filter changes

## Configuration

### Environment Variables

| Variable | Default |
|----------|---------|
| `DATABASE_URL` | `postgres://catenary:catenary@localhost:5432/catenary` |
| `RUST_LOG` | `info` |

### Ports

| Service | Port |
|---------|------|
| PostgreSQL | 5432 |
| Harebell | 8080 |
| Birch | 3000 |
| Viewer | 8081 |

## Documentation

- [Deployment Guide](docs/DEPLOYMENT.md) - Full setup instructions
- [Intent and Scope](docs/00-intent-and-scope.md)
- [Architecture](docs/03-architecture.md)
- [Tile Schema](docs/05-tile-schema.md)
- [Viewer Interactions](docs/06-viewer-interactions.md)

## What's Removed

- Routing/trip planning (Edelweiss)
- Realtime vehicle tracking (Aspen, Alpenrose, Spruce)
- Graph generation (Gentian, Linnaea)
- OSM preprocessing (Avens)
