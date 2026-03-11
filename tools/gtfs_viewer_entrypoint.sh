#!/bin/sh
set -eu

mkdir -p /app/site/data

if ! python /app/gtfs_to_geojson.py; then
  cat > /app/site/data/routes.geojson <<'EOF'
{"type":"FeatureCollection","features":[]}
EOF
  cat > /app/site/data/stops.geojson <<'EOF'
{"type":"FeatureCollection","features":[]}
EOF
  cat > /app/site/data/metadata.json <<'EOF'
{"archive":"","route_count":0,"stop_count":0,"bbox":null,"error":"Failed to prepare GTFS data. Check container logs and GTFS mount configuration."}
EOF
fi

exec python /app/gtfs_viewer_server.py
