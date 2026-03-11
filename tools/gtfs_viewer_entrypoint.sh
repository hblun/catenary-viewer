#!/bin/sh
set -eu

mkdir -p /app/site/data
ERROR_FILE=/tmp/gtfs-prep-error.log

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
  if ! python /app/gtfs_to_geojson.py 2>"$ERROR_FILE"; then
    cat > /app/site/data/routes.geojson <<'EOF'
{"type":"FeatureCollection","features":[]}
EOF
    cat > /app/site/data/stops.geojson <<'EOF'
{"type":"FeatureCollection","features":[]}
EOF
    python - <<'PY'
import json
from pathlib import Path

error_file = Path("/tmp/gtfs-prep-error.log")
error_text = "Failed to prepare GTFS data."
if error_file.exists():
    raw = error_file.read_text(encoding="utf-8", errors="replace").strip()
    if raw:
        error_text = raw.splitlines()[-1][:400]

payload = {
    "archive": "",
    "route_count": 0,
    "stop_count": 0,
    "bbox": None,
    "error": error_text,
    "renderer": "harebell-lite-v3",
}
Path("/app/site/data/metadata.json").write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
PY
  fi
) &
PREP_PID=$!

python /app/gtfs_viewer_server.py &
SERVER_PID=$!

wait "$PREP_PID"
wait "$SERVER_PID"
