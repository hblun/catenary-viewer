# Local GTFS Viewer

This is the simplest working path in this repo for viewing your own GTFS in Docker.

## What It Does

- Reads a GTFS zip from `./gtfs`
- Extracts route shapes and stops into GeoJSON
- Serves a MapLibre viewer on port `8081`
- Reuses the existing Catenary basemap styling from `frontend/static/light-style.json`

## What It Does Not Do

- It does not use Maple
- It does not use Harebell line-ordering or tile generation
- It does not depend on Transitland or Postgres

This is intentionally separate from the unfinished viewer-only backend work.

## Usage

1. Copy your GTFS zip into `gtfs/`

Example:

```bash
cp /path/to/your-feed.zip gtfs/
```

2. Start the viewer:

```bash
docker compose -f docker-compose.gtfs-viewer.yml up --build
```

3. Open:

```text
http://localhost:8081
```

## Server Path Example

If the GTFS file already exists at:

```text
/home/youruser/gtfs/filtered_scotland_gtfs.zip
```

run:

```bash
GTFS_HOST_DIR=/home/youruser/gtfs \
GTFS_FILE=filtered_scotland_gtfs.zip \
docker compose -f docker-compose.gtfs-viewer.yml up --build
```

## Multiple GTFS Archives

If `gtfs/` contains more than one zip file, select one explicitly:

```bash
GTFS_FILE=your-feed.zip docker compose -f docker-compose.gtfs-viewer.yml up --build
```

## Outputs

The prep container writes:

- `/data/routes.geojson`
- `/data/stops.geojson`
- `/data/metadata.json`

These are mounted into the viewer container and served directly.

## Troubleshooting

### "No GTFS zip found"

Put a `.zip` file inside `gtfs/`.

### "routes.txt is missing or empty"

The archive is not a valid GTFS schedule zip, or it is nested in an unexpected way.

### Map opens but nothing is visible

The feed may have:

- no `shapes.txt`
- invalid route geometry
- only stop data without route shapes

The current lightweight path requires `shapes.txt` for route rendering.
