# Catenary Transit Rendering Stack

This repo now contains two runnable paths:

1. A lightweight GTFS viewer for fast inspection of a raw feed
2. The actual Maple -> Globeflower -> Harebell ingestion and tile pipeline used to get much closer to Catenary route rendering parity

## Architecture

```text
GTFS zip -> Maple local-ingest -> PostGIS
OSM PBF  -> Globeflower       -> graph bin
PostGIS + graph bin -> Harebell export -> vector tiles -> Harebell serve / Viewer
```

## Harebell Pipeline In Repo

Yes. The real ingestion/rendering pieces are in this repo:

- Maple: [`backend/src/maple/main.rs`](/Users/home/Devwork/catenary/backend/src/maple/main.rs)
- Globeflower: [`backend/src/globeflower/main.rs`](/Users/home/Devwork/catenary/backend/src/globeflower/main.rs)
- Harebell: [`backend/src/harebell/main.rs`](/Users/home/Devwork/catenary/backend/src/harebell/main.rs)

The missing operational piece was a direct local GTFS ingest path. That now exists as:

```bash
maple --no-elastic local-ingest \
  --input-zip /path/to/feed.zip \
  --feed-id local-scotland \
  --chateau-id scotland
```

## Harebell Parity Pipeline In Docker

This is the path to use if you want Harebell-rendered tiles rather than the lightweight raw-shapes viewer.

Required inputs:
- A GTFS zip
- A rail OSM PBF for the target region

Scotland example:

```bash
GTFS_HOST_DIR=/home/youruser/gtfs \
GTFS_FILE=filtered_scotland_gtfs.zip \
GTFS_FEED_ID=filtered-scotland \
GTFS_CHATEAU_ID=scotland \
OSM_HOST_DIR=/home/youruser/osm \
GLOBEFLOWER_REGION=scotland \
docker compose -f docker-compose.harebell-pipeline.yml up --build
```

Expected OSM file path in `${OSM_HOST_DIR}` for the Scotland region:

```text
railonly-scotland-latest.osm.pbf
```

The file does not have to come from a Scotland-only Geofabrik extract. A Great Britain extract renamed to `railonly-scotland-latest.osm.pbf` is also valid if that is the OSM coverage you have available.

Ports:
- `8080`: Harebell tile server
- `8081`: simple viewer proxied to Harebell tiles

The compose file for this stack is:
- [`docker-compose.harebell-pipeline.yml`](/Users/home/Devwork/catenary/docker-compose.harebell-pipeline.yml)

## Fastest Path: View Your Own GTFS In Docker

If your immediate goal is just "drop in a GTFS zip and see it on the map", use the lightweight viewer path instead of the old Maple/Harebell stack.

1. Put a GTFS zip in [`gtfs/`](/Users/home/Devwork/catenary/gtfs)
2. Run:

```bash
docker compose -f docker-compose.gtfs-viewer.yml up --build
```

3. Open [http://localhost:8081](http://localhost:8081)

Notes:
- If there are multiple zip files in `gtfs/`, set `GTFS_FILE`:

```bash
GTFS_FILE=my-feed.zip docker compose -f docker-compose.gtfs-viewer.yml up --build
```

- If the GTFS zip already lives elsewhere on the server, mount that directory directly:

```bash
GTFS_HOST_DIR=/home/youruser/gtfs \
GTFS_FILE=filtered_scotland_gtfs.zip \
docker compose -f docker-compose.gtfs-viewer.yml up --build
```

- This path uses the existing Catenary basemap styling and overlays routes/stops extracted from your GTFS.
- It does not depend on the unfinished Maple/Harebell viewer-only refactor.

## Lightweight GTFS Viewer

If you only want to inspect a feed quickly and do not need the full Harebell render path yet:

```bash
docker compose -f docker-compose.gtfs-viewer.yml up --build
```

That path uses the Catenary basemap but not the real Globeflower/Harebell graph pipeline.

## Services

| Service | Purpose | Command |
|---------|---------|---------|
| **Maple** | GTFS ingestion | `./target/release/maple --no-elastic local-ingest --input-zip <file> --feed-id <id> --chateau-id <chateau>` |
| **Globeflower** | Support graph builder | `./target/release/globeflower --region scotland --osm-dir <dir> --output-dir <dir>` |
| **Harebell** | Tile exporter/server | `./target/release/harebell export ...` / `./target/release/harebell serve --port 8080` |
| **Birch** | Search API | `./target/release/birch` |
| **Viewer** | Web UI | `docker compose -f docker-compose.harebell-pipeline.yml up viewer` |

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

## Notes

- `docker-compose.yml` in the repo root is not the full Harebell pipeline.
- The new direct-local GTFS ingest path bypasses Transitland/DMFR, which is what makes local Scotland feeds practical here.
- Globeflower now includes a `scotland` region preset.
