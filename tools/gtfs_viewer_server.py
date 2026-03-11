#!/usr/bin/env python3
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from threading import Lock

import mercantile
import mapbox_vector_tile
from flask import Flask, Response, abort, jsonify, send_from_directory
from shapely.geometry import shape, mapping, box
from shapely.strtree import STRtree


SITE_DIR = Path("/app/site")
DATA_DIR = SITE_DIR / "data"
STATIC_DIR = SITE_DIR / "static"
SPRITE_SOURCES = {
    "mbicons": "https://moreicons.catenarymaps.org/sprite",
    "orm": "https://maps.catenarymaps.org/orm_sprite_symbols/symbols",
    "ormsdf": "https://maps.catenarymaps.org/orm_sdf_sprite_symbols/symbols",
}

app = Flask(__name__, static_folder=None)
STATE_LOCK = Lock()
STATE = {
    "metadata": {
        "archive": "",
        "route_count": 0,
        "stop_count": 0,
        "bbox": None,
        "error": "GTFS data is still being prepared.",
        "renderer": "harebell-lite-v3",
    },
    "routes": [],
    "stops": [],
    "metadata_mtime_ns": None,
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_features(name: str):
    payload = load_json(DATA_DIR / f"{name}.geojson")
    features = []
    for feature in payload.get("features", []):
        geom = feature.get("geometry")
        if not geom:
            continue
        geometry = shape(geom)
        if geometry.is_empty:
            continue
        features.append(
            {
                "geometry": geometry,
                "properties": feature.get("properties", {}),
                "id": feature.get("properties", {}).get("route_id")
                or feature.get("properties", {}).get("stop_id", ""),
            }
        )
    return features


def build_index(features):
    geometries = [feature["geometry"] for feature in features]
    if not geometries:
        return None
    return STRtree(geometries)


def query_index(index, features, bbox_shape):
    if index is None:
        return features

    matches = index.query(bbox_shape)
    if len(matches) == 0:
        return []

    if not hasattr(matches[0], "geom_type"):
        return [features[index] for index in matches]

    geometry_ids = {id(geometry) for geometry in matches}
    return [feature for feature in features if id(feature["geometry"]) in geometry_ids]


def load_state():
    metadata_path = DATA_DIR / "metadata.json"
    if not metadata_path.exists():
        return {
            "metadata": dict(STATE["metadata"]),
            "routes": [],
            "stops": [],
            "route_index": None,
            "stop_index": None,
        }

    metadata = load_json(metadata_path)
    return {
        "metadata": metadata,
        "routes": [],
        "stops": [],
        "route_index": None,
        "stop_index": None,
    }

    
def refresh_state_if_needed():
    metadata_path = DATA_DIR / "metadata.json"
    if not metadata_path.exists():
        return

    metadata_mtime_ns = metadata_path.stat().st_mtime_ns
    with STATE_LOCK:
        if STATE["metadata_mtime_ns"] == metadata_mtime_ns:
            return

        next_state = load_state()
        metadata = next_state["metadata"]
        if not metadata.get("error"):
            next_state["routes"] = load_features("routes")
            next_state["stops"] = load_features("stops")
            next_state["route_index"] = build_index(next_state["routes"])
            next_state["stop_index"] = build_index(next_state["stops"])

        next_state["metadata_mtime_ns"] = metadata_mtime_ns
        STATE.update(next_state)


def current_state():
    refresh_state_if_needed()
    with STATE_LOCK:
        return {
            "metadata": STATE["metadata"],
            "routes": STATE["routes"],
            "stops": STATE["stops"],
            "route_index": STATE.get("route_index"),
            "stop_index": STATE.get("stop_index"),
        }


def tile_bbox(z: int, x: int, y: int):
    bounds = mercantile.bounds(x, y, z)
    return box(bounds.west, bounds.south, bounds.east, bounds.north), (
        bounds.west,
        bounds.south,
        bounds.east,
        bounds.north,
    )


def route_tile_features(z: int, x: int, y: int):
    state = current_state()
    bbox_shape, quantize_bounds = tile_bbox(z, x, y)
    items = []
    for feature in query_index(state["route_index"], state["routes"], bbox_shape):
        if not feature["geometry"].intersects(bbox_shape):
            continue
        clipped = feature["geometry"].intersection(bbox_shape)
        if clipped.is_empty:
            continue
        items.append(
            {
                "geometry": mapping(clipped),
                "properties": feature["properties"],
                "id": feature["properties"].get("route_id", ""),
            }
        )
    return items, quantize_bounds


def stop_tile_features(z: int, x: int, y: int):
    state = current_state()
    bbox_shape, quantize_bounds = tile_bbox(z, x, y)
    items = []
    for feature in query_index(state["stop_index"], state["stops"], bbox_shape):
        if not feature["geometry"].intersects(bbox_shape):
            continue
        items.append(
            {
                "geometry": mapping(feature["geometry"]),
                "properties": feature["properties"],
                "id": feature["properties"].get("stop_id", ""),
            }
        )
    return items, quantize_bounds


def encode_tile(layer_name: str, features, quantize_bounds):
    if not features:
        return b""
    return mapbox_vector_tile.encode(
        [{"name": layer_name, "features": features}],
        default_options={
            "quantize_bounds": quantize_bounds,
            "extents": 4096,
            "y_coord_down": False,
        },
    )


@app.get("/")
def index():
    return send_from_directory(SITE_DIR, "index.html")


@app.get("/static/<path:subpath>")
def static_files(subpath: str):
    return send_from_directory(STATIC_DIR, subpath)


@app.get("/sprite-proxy/<sprite_id>.<ext>")
def sprite_proxy(sprite_id: str, ext: str):
    sprite_name = sprite_id.removesuffix("@2x")
    scale_suffix = "@2x" if sprite_id.endswith("@2x") else ""
    base_url = SPRITE_SOURCES.get(sprite_name)
    if not base_url or ext not in {"json", "png"}:
        abort(404)

    try:
        with urllib.request.urlopen(f"{base_url}{scale_suffix}.{ext}", timeout=20) as response:
            payload = response.read()
            content_type = response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        return Response(status=exc.code)
    except Exception:
        return Response(status=502)

    if ext == "json":
        content_type = "application/json"
    elif ext == "png":
        content_type = "image/png"

    return Response(
        payload,
        mimetype=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/data/metadata.json")
def metadata():
    response = jsonify(current_state()["metadata"])
    response.headers["Cache-Control"] = "public, max-age=60"
    return response


@app.get("/tiles/routes/<int:z>/<int:x>/<int:y>.pbf")
def route_tiles(z: int, x: int, y: int):
    features, quantize_bounds = route_tile_features(z, x, y)
    payload = encode_tile("routes", features, quantize_bounds)
    return Response(
        payload,
        mimetype="application/x-protobuf",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/tiles/stops/<int:z>/<int:x>/<int:y>.pbf")
def stop_tiles(z: int, x: int, y: int):
    features, quantize_bounds = stop_tile_features(z, x, y)
    payload = encode_tile("stops", features, quantize_bounds)
    return Response(
        payload,
        mimetype="application/x-protobuf",
        headers={"Cache-Control": "public, max-age=300"},
    )


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8081"))
    app.run(host=host, port=port, threaded=True)
