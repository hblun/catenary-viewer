# Harebell Pipeline

This is the real ingestion/render path in this repo:

1. Maple ingests a GTFS zip into Postgres
2. Globeflower reads Postgres + OSM and writes a support graph
3. Harebell reads the graph + Postgres route metadata and exports vector tiles
4. Harebell serves those tiles over HTTP

## Local GTFS ingest

Maple now supports direct local ingest without Transitland:

```bash
export DATABASE_URL=postgres://catenary:catenary@localhost:5432/catenary

./target/release/maple --no-elastic local-ingest \
  --input-zip /path/to/feed.zip \
  --feed-id local-scotland \
  --chateau-id scotland
```

## OSM input

Globeflower expects a region-specific rail OSM PBF in the directory passed via `--osm-dir`.

For the Scotland preset, the expected filename is:

```text
railonly-scotland-latest.osm.pbf
```

If you only have a broader Great Britain extract, that is acceptable too. Place it in the OSM directory with the expected Scotland filename so the compose stack can find it.

## Docker

Use:

```bash
docker compose -f docker-compose.harebell-pipeline.yml up --build
```

Key environment variables:

- `GTFS_HOST_DIR`: host directory containing the GTFS zip
- `GTFS_FILE`: GTFS zip filename
- `GTFS_FEED_ID`: feed identifier to store in Postgres
- `GTFS_CHATEAU_ID`: chateau identifier to associate with the feed
- `OSM_HOST_DIR`: host directory containing the OSM PBF
- `GLOBEFLOWER_REGION`: region preset, for example `scotland`

## Outputs

- Harebell tiles are served on port `8080`
- The bundled viewer is served on port `8081`
