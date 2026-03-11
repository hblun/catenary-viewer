#!/bin/sh
set -eu

mkdir -p /app/site/data

cat > /app/site/data/routes.geojson <<'EOF'
{"type":"FeatureCollection","features":[]}
EOF
cat > /app/site/data/stops.geojson <<'EOF'
{"type":"FeatureCollection","features":[]}
EOF
cat > /app/site/data/metadata.json <<'EOF'
{"archive":"","route_count":0,"stop_count":0,"bbox":null,"error":"GTFS data is still being prepared.","renderer":"harebell-lite-v3"}
EOF

(
  if ! python /app/gtfs_to_geojson.py; then
    cat > /app/site/data/routes.geojson <<'EOF'
{"type":"FeatureCollection","features":[]}
EOF
    cat > /app/site/data/stops.geojson <<'EOF'
{"type":"FeatureCollection","features":[]}
EOF
    cat > /app/site/data/metadata.json <<'EOF'
{"archive":"","route_count":0,"stop_count":0,"bbox":null,"error":"Failed to prepare GTFS data. Check container logs and GTFS mount configuration.","renderer":"harebell-lite-v3"}
EOF
  fi
) &

exec python /app/gtfs_viewer_server.py
