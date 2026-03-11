#!/usr/bin/env python3
import json
import os
from pathlib import Path

import mercantile
import mapbox_vector_tile
from flask import Flask, Response, jsonify, send_from_directory
from shapely.geometry import shape, mapping, box


SITE_DIR = Path("/app/site")
DATA_DIR = SITE_DIR / "data"
STATIC_DIR = SITE_DIR / "static"

app = Flask(__name__, static_folder=None)


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
        features.append({"geometry": geometry, "properties": feature.get("properties", {})})
    return features


def load_state():
    metadata = load_json(DATA_DIR / "metadata.json")
    state = {
        "metadata": metadata,
        "routes": [],
        "stops": [],
    }

    if not metadata.get("error"):
        state["routes"] = load_features("routes")
        state["stops"] = load_features("stops")
    return state


STATE = load_state()


def tile_bbox(z: int, x: int, y: int):
    bounds = mercantile.bounds(x, y, z)
    return box(bounds.west, bounds.south, bounds.east, bounds.north), (
        bounds.west,
        bounds.south,
        bounds.east,
        bounds.north,
    )


def route_tile_features(z: int, x: int, y: int):
    bbox_shape, quantize_bounds = tile_bbox(z, x, y)
    items = []
    for feature in STATE["routes"]:
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
    bbox_shape, quantize_bounds = tile_bbox(z, x, y)
    items = []
    for feature in STATE["stops"]:
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


@app.get("/data/metadata.json")
def metadata():
    response = jsonify(STATE["metadata"])
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
