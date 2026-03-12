#!/usr/bin/env python3
import json
import math
import os
from collections import defaultdict

import mapbox_vector_tile
import mercantile
import psycopg
from flask import Flask, Response
from psycopg.rows import dict_row
from shapely.geometry import LineString, MultiLineString, box, mapping, shape


DATABASE_URL = os.environ["DATABASE_URL"]
PORT = int(os.environ.get("PORT", "8090"))
EARTH_METERS_PER_DEG_LAT = 111320.0

app = Flask(__name__)


def tile_width_degrees_from_z(z: int) -> float:
    return 360.0 / (2 ** (z + 1))


def build_shapes_query(z: int, x: int, y: int, simplification_threshold: float, where_clause: str) -> str:
    return f"""
    SELECT
        ST_AsMVT(q, 'data', 4096, 'geom')
    FROM (
        SELECT
            onestop_feed_id,
            shape_id,
            color,
            routes,
            route_type,
            route_label,
            text_color,
            chateau,
            stop_to_stop_generated,
            ST_AsMVTGeom(
                ST_Transform(ST_Simplify(linestring, {simplification_threshold}), 3857),
                ST_TileEnvelope({z}, {x}, {y}),
                4096,
                64,
                true
            ) AS geom
        FROM gtfs.shapes
        WHERE
            (linestring && ST_Transform(ST_TileEnvelope({z}, {x}, {y}), 4326))
            AND allowed_spatial_query = true
            AND ({where_clause})
    ) q
    """


def tile_bounds(z: int, x: int, y: int) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    bounds = mercantile.bounds(x, y, z)
    return (
        bounds.west,
        bounds.south,
        bounds.east,
        bounds.north,
    ), (
        bounds.west,
        bounds.south,
        bounds.east,
        bounds.north,
    )


def expanded_tile_bounds(z: int, x: int, y: int, factor: float = 0.35) -> tuple[float, float, float, float]:
    west, south, east, north = tile_bounds(z, x, y)[0]
    pad_x = (east - west) * factor
    pad_y = (north - south) * factor
    return west - pad_x, south - pad_y, east + pad_x, north + pad_y


def meters_per_degree_lon(lat: float) -> float:
    return max(EARTH_METERS_PER_DEG_LAT * math.cos(math.radians(lat)), 1.0)


def snapped_coord(point: tuple[float, float], precision: int = 5) -> tuple[float, float]:
    return (round(point[0], precision), round(point[1], precision))


def canonical_segment(
    start: tuple[float, float], end: tuple[float, float]
) -> tuple[tuple[tuple[float, float], tuple[float, float]], tuple[float, float], tuple[float, float]]:
    start_key = snapped_coord(start)
    end_key = snapped_coord(end)
    if start_key <= end_key:
        return (start_key, end_key), start, end
    return (end_key, start_key), end, start


def segment_normal(
    start: tuple[float, float], end: tuple[float, float]
) -> tuple[float, float] | None:
    lat = (start[1] + end[1]) / 2.0
    dx_m = (end[0] - start[0]) * meters_per_degree_lon(lat)
    dy_m = (end[1] - start[1]) * EARTH_METERS_PER_DEG_LAT
    length = math.hypot(dx_m, dy_m)
    if length < 0.01:
        return None
    return (-dy_m / length, dx_m / length)


def apply_meter_offset(
    point: tuple[float, float], offset_x_m: float, offset_y_m: float
) -> tuple[float, float]:
    lon, lat = point
    return (
        lon + offset_x_m / meters_per_degree_lon(lat),
        lat + offset_y_m / EARTH_METERS_PER_DEG_LAT,
    )


def shape_sort_key(route_type: int | None, route_count: int, stop_to_stop_generated: bool) -> int:
    type_rank = {
        2: 400,
        1: 350,
        0: 340,
        5: 330,
        12: 320,
        3: 200,
        11: 190,
        200: 185,
    }
    rank = type_rank.get(route_type or -1, 100) + min(route_count, 80)
    if stop_to_stop_generated:
        rank -= 20
    return rank


def route_order_tuple(route: dict[str, object]) -> tuple[object, ...]:
    return (
        -int(route.get("sort_key", 0)),
        str(route.get("route_label", "")),
        str(route.get("color", "")),
        str(route.get("shape_id", "")),
    )


def segment_spacing(route_items: list[dict[str, object]], z: int) -> float:
    highest_rank = max(int(item.get("sort_key", 0)) for item in route_items)
    base = 6.0
    if highest_rank >= 320:
        base = 8.0
    elif highest_rank >= 200:
        base = 7.0

    zoom_scale = {
        8: 0.35,
        9: 0.55,
        10: 0.7,
        11: 0.85,
        12: 1.0,
        13: 1.15,
        14: 1.25,
        15: 1.35,
    }
    return base * zoom_scale.get(z, 1.45 if z >= 16 else 0.25)


def offset_linestring(
    coords: list[tuple[float, float]],
    feature_key: str,
    segment_offsets: dict[tuple[tuple[tuple[float, float], tuple[float, float]], str], float],
) -> list[tuple[float, float]]:
    if len(coords) < 2:
        return coords

    segment_vectors: list[tuple[float, float] | None] = []
    segment_shifts: list[float] = []

    for start, end in zip(coords, coords[1:]):
        segment_key, canonical_start, canonical_end = canonical_segment(start, end)
        shift = segment_offsets.get((segment_key, feature_key), 0.0)
        normal = segment_normal(canonical_start, canonical_end)
        segment_vectors.append(normal)
        segment_shifts.append(shift)

    offset_coords: list[tuple[float, float]] = []
    for index, point in enumerate(coords):
        offset_x = 0.0
        offset_y = 0.0
        contributors = 0

        if index > 0:
            shift = segment_shifts[index - 1]
            normal = segment_vectors[index - 1]
            if normal and abs(shift) > 0.001:
                offset_x += normal[0] * shift
                offset_y += normal[1] * shift
                contributors += 1

        if index < len(coords) - 1:
            shift = segment_shifts[index]
            normal = segment_vectors[index]
            if normal and abs(shift) > 0.001:
                offset_x += normal[0] * shift
                offset_y += normal[1] * shift
                contributors += 1

        if contributors == 0:
            offset_coords.append(point)
        else:
            offset_coords.append(
                apply_meter_offset(point, offset_x / contributors, offset_y / contributors)
            )

    return offset_coords


def encode_tile(layer_name: str, features: list[dict], quantize_bounds: tuple[float, float, float, float]) -> bytes:
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


def parse_routes(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def fetch_raw_shapes(z: int, x: int, y: int, where_clause: str) -> list[dict]:
    min_lon, min_lat, max_lon, max_lat = expanded_tile_bounds(z, x, y)
    query = f"""
    SELECT
        onestop_feed_id,
        shape_id,
        color,
        routes,
        route_type,
        route_label,
        text_color,
        chateau,
        stop_to_stop_generated,
        ST_AsGeoJSON(linestring) AS geometry
    FROM gtfs.shapes
    WHERE
        linestring && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
        AND allowed_spatial_query = true
        AND ({where_clause})
    """

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (min_lon, min_lat, max_lon, max_lat))
            return list(cur.fetchall())


def aggregate_bus_tile(z: int, x: int, y: int) -> bytes:
    raw_rows = fetch_raw_shapes(
        z,
        x,
        y,
        "route_type IN (3,11,200) AND routes != '{}' AND chateau != 'flixbus~europe' AND chateau != 'flixbus~america'",
    )
    if not raw_rows:
        return b""

    tile_bbox, quantize_bounds = tile_bounds(z, x, y)
    clip_box = box(*tile_bbox)
    tile_width = tile_width_degrees_from_z(z)
    simplification = tile_width * {6: 0.005, 7: 0.004, 8: 0.004}.get(z, 0.003)

    features_by_key: dict[str, dict] = {}
    segment_memberships: dict[
        tuple[tuple[float, float], tuple[float, float]], dict[str, dict[str, object]]
    ] = defaultdict(dict)

    for row in raw_rows:
        geometry_json = row.get("geometry")
        if not geometry_json:
            continue
        geometry = shape(json.loads(geometry_json))
        if geometry.is_empty:
            continue

        linestrings: list[list[tuple[float, float]]] = []
        if geometry.geom_type == "LineString":
            coords = [(float(lon), float(lat)) for lon, lat in geometry.coords]
            if len(coords) >= 2:
                linestrings.append(coords)
        elif geometry.geom_type == "MultiLineString":
            for line in geometry.geoms:
                coords = [(float(lon), float(lat)) for lon, lat in line.coords]
                if len(coords) >= 2:
                    linestrings.append(coords)

        if not linestrings:
            continue

        shape_id = str(row.get("shape_id") or "")
        route_label = str(row.get("route_label") or shape_id)
        routes = parse_routes(row.get("routes"))
        route_count = len(routes) if routes else 1
        stop_to_stop_generated = bool(row.get("stop_to_stop_generated"))
        route_type = int(row.get("route_type") or 0)
        feature_key = shape_id or f"{route_label}:{row.get('onestop_feed_id', '')}"
        color = str(row.get("color") or "e21b23").lstrip("#")
        text_color = str(row.get("text_color") or "ffffff").lstrip("#")

        props = {
            "onestop_feed_id": row.get("onestop_feed_id") or "",
            "shape_id": shape_id,
            "color": color,
            "routes": routes,
            "route_type": route_type,
            "route_label": route_label,
            "text_color": text_color,
            "chateau": row.get("chateau") or "",
            "stop_to_stop_generated": stop_to_stop_generated,
            "sort_key": shape_sort_key(route_type, route_count, stop_to_stop_generated),
            "_feature_key": feature_key,
        }
        features_by_key[feature_key] = {"properties": props, "linestrings": linestrings}

        for coords in linestrings:
            for start, end in zip(coords, coords[1:]):
                segment_key, _, _ = canonical_segment(start, end)
                segment_memberships[segment_key][feature_key] = props

    segment_offsets: dict[
        tuple[tuple[tuple[float, float], tuple[float, float]], str], float
    ] = {}
    for segment_key, feature_map in segment_memberships.items():
        feature_items = sorted(feature_map.values(), key=route_order_tuple)
        if len(feature_items) < 2:
            continue

        groups: list[dict[str, object]] = []
        for item in feature_items:
            if groups and groups[-1]["color"] == item["color"]:
                groups[-1]["feature_keys"].append(item["_feature_key"])
            else:
                groups.append({"color": item["color"], "feature_keys": [item["_feature_key"]]})

        if len(groups) < 2:
            continue

        spacing = segment_spacing(feature_items, z)
        for group_index, group in enumerate(groups):
            shift = (group_index - (len(groups) - 1) / 2.0) * spacing
            for feature_key in group["feature_keys"]:
                segment_offsets[(segment_key, feature_key)] = shift

    encoded_features: list[dict] = []
    for feature_key, item in features_by_key.items():
        adjusted_lines = [
            offset_linestring(linestring, feature_key, segment_offsets)
            for linestring in item["linestrings"]
        ]

        clipped_parts = []
        for coords in adjusted_lines:
            simplified = LineString(coords).simplify(simplification, preserve_topology=False)
            if simplified.is_empty:
                continue
            clipped = simplified.intersection(clip_box)
            if clipped.is_empty:
                continue
            if clipped.geom_type == "LineString":
                clipped_parts.append(clipped)
            elif clipped.geom_type == "MultiLineString":
                clipped_parts.extend(list(clipped.geoms))
            elif clipped.geom_type == "GeometryCollection":
                clipped_parts.extend([geom for geom in clipped.geoms if geom.geom_type == "LineString"])

        if not clipped_parts:
            continue

        geometry = clipped_parts[0] if len(clipped_parts) == 1 else MultiLineString(clipped_parts)
        properties = dict(item["properties"])
        properties.pop("sort_key", None)
        properties.pop("_feature_key", None)
        encoded_features.append(
            {
                "geometry": mapping(geometry),
                "properties": properties,
                "id": feature_key,
            }
        )

    return encode_tile("data", encoded_features, quantize_bounds)


def fetch_mvt(query: str, max_age: int) -> Response:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            row = cur.fetchone()

    payload = row[0] if row and row[0] is not None else b""
    return Response(
        payload,
        mimetype="application/x-protobuf",
        headers={"Cache-Control": f"public, max-age={max_age}"},
    )


@app.get("/health")
def health() -> Response:
    return Response("ok", mimetype="text/plain")


@app.get("/shapes_bus/<int:z>/<int:x>/<int:y>.pbf")
def shapes_bus(z: int, x: int, y: int) -> Response:
    if z < 4:
        return Response("Zoom level too low", status=400)

    payload = aggregate_bus_tile(z, x, y)
    return Response(
        payload,
        mimetype="application/x-protobuf",
        headers={"Cache-Control": "public, max-age=1000"},
    )


@app.get("/shapes_local_rail/<int:z>/<int:x>/<int:y>.pbf")
def shapes_local_rail(z: int, x: int, y: int) -> Response:
    if z < 4:
        return Response("Zoom level too low", status=400)

    tile_width_degrees = tile_width_degrees_from_z(z)
    query = build_shapes_query(
        z,
        x,
        y,
        tile_width_degrees * 0.001,
        "route_type IN (0,1,5,7,11,12)",
    )
    return fetch_mvt(query, 1000 if z <= 6 else 500)


@app.get("/shapes_intercity_rail/<int:z>/<int:x>/<int:y>.pbf")
def shapes_intercity_rail(z: int, x: int, y: int) -> Response:
    if z < 4:
        return Response("Zoom level too low", status=400)

    tile_width_degrees = tile_width_degrees_from_z(z)
    query = build_shapes_query(z, x, y, tile_width_degrees * 0.001, "route_type = 2")
    max_age = {4: 10000, 5: 5000, 6: 2000}.get(z, 1000)
    return fetch_mvt(query, max_age)


@app.get("/shapes_ferry/<int:z>/<int:x>/<int:y>.pbf")
def shapes_ferry(z: int, x: int, y: int) -> Response:
    if z < 4:
        return Response("Zoom level too low", status=400)

    tile_width_degrees = tile_width_degrees_from_z(z)
    query = build_shapes_query(z, x, y, tile_width_degrees * 0.004, "route_type = 4")
    max_age = {4: 36000, 5: 10000, 6: 2000}.get(z, 1000)
    return fetch_mvt(query, max_age)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
