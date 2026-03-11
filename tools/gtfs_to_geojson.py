#!/usr/bin/env python3
import csv
import io
import json
import os
import sys
import time
import zipfile
from collections import defaultdict
from contextlib import contextmanager


OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/output")
GTFS_DIR = os.environ.get("GTFS_DIR", "/gtfs")
GTFS_FILE = os.environ.get("GTFS_FILE", "")


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def list_gtfs_archives() -> list[str]:
    archives: list[str] = []
    for entry in sorted(os.listdir(GTFS_DIR)):
        if entry.lower().endswith(".zip"):
            archives.append(os.path.join(GTFS_DIR, entry))
    return archives


def pick_archive() -> str:
    if GTFS_FILE:
        candidate = GTFS_FILE
        if not os.path.isabs(candidate):
            candidate = os.path.join(GTFS_DIR, candidate)
        if not os.path.exists(candidate):
            fail(f"Configured GTFS_FILE does not exist: {candidate}")
        return candidate

    archives = list_gtfs_archives()
    if not archives:
        fail(f"No GTFS zip found in {GTFS_DIR}")
    if len(archives) > 1:
        print(
            f"GTFS_FILE not set. Using first archive: {os.path.basename(archives[0])}",
            file=sys.stderr,
        )
    return archives[0]


def resolve_member_name(zf: zipfile.ZipFile, name: str) -> str | None:
    members = {member.filename.lower(): member.filename for member in zf.infolist()}
    for member_name, original_name in members.items():
        if member_name.endswith(f"/{name}") or member_name == name:
            return original_name
    return None


@contextmanager
def iter_csv_from_zip(zf: zipfile.ZipFile, name: str):
    target = resolve_member_name(zf, name)
    if target is None:
        yield None
        return

    with zf.open(target) as raw_file:
        text = io.TextIOWrapper(raw_file, encoding="utf-8-sig", newline="")
        yield csv.DictReader(text)


def parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def clean_color(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    value = value.strip().lstrip("#")
    if len(value) in (3, 6):
        return f"#{value}"
    return fallback


def route_mode(route_type: str | None) -> str:
    if route_type in {"0", "1", "5", "6", "12"}:
        return "metro"
    if route_type == "2":
        return "rail"
    if route_type in {"3", "11"}:
        return "bus"
    return "other"


def bbox_from_points(points: list[tuple[float, float]]) -> list[float] | None:
    if not points:
        return None
    lons = [point[0] for point in points]
    lats = [point[1] for point in points]
    return [min(lons), min(lats), max(lons), max(lats)]


def combine_bboxes(bboxes: list[list[float] | None]) -> list[float] | None:
    valid = [bbox for bbox in bboxes if bbox is not None]
    if not valid:
        return None
    return [
        min(bbox[0] for bbox in valid),
        min(bbox[1] for bbox in valid),
        max(bbox[2] for bbox in valid),
        max(bbox[3] for bbox in valid),
    ]


def write_json(path: str, payload: object) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True)


def stable_hash(value: str) -> int:
    result = 2166136261
    for char in value:
        result ^= ord(char)
        result = (result * 16777619) & 0xFFFFFFFF
    return result


def color_from_palette(key: str, palette: list[str]) -> str:
    return palette[stable_hash(key) % len(palette)]


def mode_fallback_color(mode: str, route_id: str) -> str:
    palettes = {
        "rail": ["#003f7d", "#005a9c", "#0a6ebd", "#145d8f"],
        "metro": ["#b400a6", "#e4007c", "#008ecf", "#0b72b5"],
        "bus": ["#e21b23", "#cc2f2f", "#ff5a36", "#d9480f", "#b91c1c"],
        "other": ["#7c3aed", "#8b5cf6", "#0f766e", "#0ea5a4"],
    }
    return color_from_palette(route_id, palettes.get(mode, palettes["other"]))


def route_sort_key(route_type: str | None, trip_count: int) -> int:
    type_rank = {
        "2": 400,
        "1": 350,
        "0": 340,
        "5": 330,
        "12": 320,
        "3": 200,
        "11": 190,
    }
    return type_rank.get(route_type or "", 100) + min(trip_count, 80)


def main() -> None:
    ensure_output_dir()
    archive_path = pick_archive()
    archive_stat = os.stat(archive_path)
    metadata_path = os.path.join(OUTPUT_DIR, "metadata.json")

    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as handle:
                existing_metadata = json.load(handle)
            existing_source = existing_metadata.get("source", {})
            if (
                existing_source.get("archive") == os.path.basename(archive_path)
                and existing_source.get("size") == archive_stat.st_size
                and int(existing_source.get("mtime", 0)) == int(archive_stat.st_mtime)
            ):
                print(
                    f"GTFS source unchanged for {os.path.basename(archive_path)}; reusing generated data"
                )
                return
        except Exception:
            pass

    with zipfile.ZipFile(archive_path) as zf:
        with iter_csv_from_zip(zf, "routes.txt") as routes_reader:
            if routes_reader is None:
                fail("routes.txt is missing")
            routes_by_id: dict[str, dict[str, str]] = {}
            for row in routes_reader:
                route_id = row.get("route_id")
                if route_id:
                    routes_by_id[route_id] = row

        with iter_csv_from_zip(zf, "trips.txt") as trips_reader:
            trip_shape_by_route: dict[str, set[str]] = defaultdict(set)
            trip_count_by_route: dict[str, int] = defaultdict(int)
            if trips_reader is not None:
                for row in trips_reader:
                    route_id = row.get("route_id")
                    if not route_id:
                        continue
                    trip_count_by_route[route_id] += 1
                    shape_id = row.get("shape_id")
                    if shape_id:
                        trip_shape_by_route[route_id].add(shape_id)

        with iter_csv_from_zip(zf, "shapes.txt") as shapes_reader:
            shape_stop_order: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
            if shapes_reader is not None:
                for row in shapes_reader:
                    shape_id = row.get("shape_id")
                    lat = parse_float(row.get("shape_pt_lat"))
                    lon = parse_float(row.get("shape_pt_lon"))
                    sequence = row.get("shape_pt_sequence")
                    if not shape_id or lat is None or lon is None or sequence is None:
                        continue
                    try:
                        sequence_num = int(float(sequence))
                    except ValueError:
                        continue
                    shape_stop_order[shape_id].append((sequence_num, lon, lat))

        with iter_csv_from_zip(zf, "stops.txt") as stops_reader:
            if stops_reader is None:
                fail("stops.txt is missing")
            stop_features = []
            stop_points: list[tuple[float, float]] = []
            for row in stops_reader:
                stop_id = row.get("stop_id")
                stop_name = row.get("stop_name")
                lat = parse_float(row.get("stop_lat"))
                lon = parse_float(row.get("stop_lon"))
                if not stop_id or not stop_name or lat is None or lon is None:
                    continue

                stop_points.append((lon, lat))
                stop_features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "stop_id": stop_id,
                            "stop_name": stop_name,
                            "stop_code": row.get("stop_code") or "",
                            "location_type": row.get("location_type") or "0",
                            "route_ids": [],
                        },
                        "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    }
                )

    route_features = []
    route_bboxes: list[list[float] | None] = []

    for route_id, route in routes_by_id.items():
        shape_ids = sorted(trip_shape_by_route.get(route_id, set()))
        short_name = route.get("route_short_name") or route_id
        long_name = route.get("route_long_name") or ""
        color = clean_color(route.get("route_color"), "")
        text_color = clean_color(route.get("route_text_color"), "#ffffff")
        mode = route_mode(route.get("route_type"))
        if not color:
            color = mode_fallback_color(mode, route_id)

        linestrings = []
        line_points_for_bbox: list[tuple[float, float]] = []
        for shape_id in shape_ids:
            ordered = sorted(shape_stop_order.get(shape_id, []), key=lambda item: item[0])
            coords = [(lon, lat) for _, lon, lat in ordered]
            if len(coords) >= 2:
                linestrings.append(coords)
                line_points_for_bbox.extend(coords)

        geometry = None
        if len(linestrings) == 1:
            geometry = {"type": "LineString", "coordinates": linestrings[0]}
        elif len(linestrings) > 1:
            geometry = {"type": "MultiLineString", "coordinates": linestrings}

        if geometry is None:
            continue

        route_bbox = bbox_from_points(line_points_for_bbox)
        route_bboxes.append(route_bbox)

        route_features.append(
            {
                "type": "Feature",
                "properties": {
                    "route_id": route_id,
                    "route_short_name": short_name,
                    "route_long_name": long_name,
                    "operator_name": route.get("agency_id") or "",
                    "operator_id": route.get("agency_id") or "",
                    "mode": mode,
                    "route_type": route.get("route_type") or "",
                    "color": color,
                    "text_color": text_color,
                    "trip_count": trip_count_by_route.get(route_id, 0),
                    "stop_count": 0,
                    "sort_key": route_sort_key(route.get("route_type"), trip_count_by_route.get(route_id, 0)),
                },
                "geometry": geometry,
            }
        )

    routes_geojson = {"type": "FeatureCollection", "features": route_features}
    stops_geojson = {"type": "FeatureCollection", "features": stop_features}

    overall_bbox = combine_bboxes([bbox_from_points(stop_points), *route_bboxes])
    metadata = {
        "archive": os.path.basename(archive_path),
        "route_count": len(route_features),
        "stop_count": len(stop_features),
        "bbox": overall_bbox,
        "generated_at": int(time.time()),
        "source": {
            "archive": os.path.basename(archive_path),
            "size": archive_stat.st_size,
            "mtime": int(archive_stat.st_mtime),
        },
    }

    write_json(os.path.join(OUTPUT_DIR, "routes.geojson"), routes_geojson)
    write_json(os.path.join(OUTPUT_DIR, "stops.geojson"), stops_geojson)
    write_json(os.path.join(OUTPUT_DIR, "metadata.json"), metadata)

    print(
        f"Wrote {len(route_features)} routes and {len(stop_features)} stops from {os.path.basename(archive_path)}"
    )


if __name__ == "__main__":
    main()
