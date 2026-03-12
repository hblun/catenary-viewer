#!/usr/bin/env python3
import os

import psycopg
from flask import Flask, Response


DATABASE_URL = os.environ["DATABASE_URL"]
PORT = int(os.environ.get("PORT", "8090"))

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

    tile_width_degrees = tile_width_degrees_from_z(z)
    simp_amount = {6: 0.005, 7: 0.004, 8: 0.004}.get(z, 0.003)
    query = build_shapes_query(
        z,
        x,
        y,
        tile_width_degrees * simp_amount,
        "route_type IN (3,11,200) AND routes != '{}' AND chateau != 'flixbus~europe' AND chateau != 'flixbus~america'",
    )
    return fetch_mvt(query, 1000)


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
