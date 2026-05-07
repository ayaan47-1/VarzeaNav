"""Flask backend for Amazon River Navigation hackathon demo.

Step 1 scope: stub /route?month=N + parallel HEAD-check of 12 monthly tiles
at startup. Pixel classification, GeoJSON, and Claude advisory come in later
steps.
"""
from __future__ import annotations

import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Make backend/ importable regardless of CWD
sys.path.insert(0, str(Path(__file__).parent))
import jrc_data  # noqa: E402
import navigability  # noqa: E402
import advisory  # noqa: E402
import vectorize  # noqa: E402
import overlay_png  # noqa: E402
import routing  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("app")

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
CACHE_DIR = ROOT / "backend" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ISLAND_LAT, ISLAND_LON = -3.339, -60.189

# Two fixed waypoints for the A* route. North is the town center of
# Iranduba (a real municipality on the south bank of the Rio Negro,
# opposite Manaus). South is Vila do Janauacá, a riverside community on
# Lago Janauacá in the Manaquiri municipality, across the Solimões.
#
# Both coords are real town centers (on land). routing._snap_to_traversable
# snaps each to the nearest navigable cell at A* time, so they end up on
# the closest river/seasonal channel. The diagonal Rio Negro → Solimões
# crossing forces the route across the main island in wet months (a
# seasonal-active shortcut through flooded forest) and around it in dry
# months (a longer permanent-water detour). That seasonal contrast is
# the demo's hook — "shortcuts emerge through flooded forest."
WAYPOINT_NORTH: tuple[float, float] = (-3.2847, -60.1861)
WAYPOINT_SOUTH: tuple[float, float] = (-3.3777, -60.2748)
WAYPOINT_NORTH_NAME: str = "Iranduba"
WAYPOINT_SOUTH_NAME: str = "Vila do Janauacá"

# JRC Global Surface Water v1.4 — monthly history shards
# Shard 0000320000-0000440000 covers (-70, -10, -60, 0) — same bounds as the
# cached occurrence tile, validated against the proto.
GSW_BUCKET = "https://storage.googleapis.com/global-surface-water"
MONTHLY_SHARD = "0000320000-0000440000.tif"


def monthly_url(month: int) -> str:
    return f"{GSW_BUCKET}/downloads2021/monthly2021/2021_{month:02d}/{MONTHLY_SHARD}"


def head_check(month: int) -> tuple[int, str | None, int]:
    """HEAD a monthly tile; return (month, error_or_none, content_length)."""
    url = monthly_url(month)
    try:
        r = requests.head(url, timeout=8, allow_redirects=True)
        if r.status_code == 200:
            length = int(r.headers.get("content-length", 0))
            return month, None, length
        return month, f"HTTP {r.status_code}", 0
    except requests.RequestException as e:
        return month, str(e), 0


def verify_monthly_tiles() -> dict:
    """Parallel HEAD-check all 12 monthly tile URLs. Returns availability map."""
    log.info("HEAD-checking 12 monthly tiles in parallel...")
    available, missing = [], []
    with ThreadPoolExecutor(max_workers=12) as pool:
        for month, err, length in pool.map(head_check, range(1, 13)):
            if err is None:
                available.append(month)
                log.info(f"  month {month:02d}: ok ({length / 1_000_000:.1f} MB)")
            else:
                missing.append(month)
                log.warning(f"  month {month:02d}: {err}")
    log.info(f"{len(available)}/12 monthly tiles available")
    return {"available": sorted(available), "missing": sorted(missing)}


# Build app
app = Flask(__name__, static_folder=None)
CORS(app)


def _serialize_route(route: "routing.RouteResult") -> dict:
    """Convert a RouteResult into the JSON shape consumed by the frontend."""
    base_endpoints = {
        "start": list(route.start_latlon),
        "end": list(route.end_latlon),
        "start_name": WAYPOINT_NORTH_NAME,
        "end_name": WAYPOINT_SOUTH_NAME,
    }
    if not route.exists:
        return {
            "exists": False,
            "geometry": None,
            "segments": None,
            "stats": {
                "length_km": 0.0,
                "permanent_km": 0.0,
                "seasonal_km": 0.0,
                "percent_permanent": 0.0,
                "percent_seasonal": 0.0,
                "longest_seasonal_segment_km": 0.0,
            },
            **base_endpoints,
        }
    total = route.length_km if route.length_km > 0 else 1.0
    pct_perm = route.permanent_km / total
    pct_seas = route.seasonal_km / total
    # GeoJSON LineString uses [lon, lat] ordering.
    geometry = {
        "type": "LineString",
        "coordinates": [[lon, lat] for (lat, lon) in route.coords],
    }
    return {
        "exists": True,
        "geometry": geometry,
        "segments": route.segments,
        "stats": {
            "length_km": route.length_km,
            "permanent_km": route.permanent_km,
            "seasonal_km": route.seasonal_km,
            "percent_permanent": round(pct_perm, 4),
            "percent_seasonal": round(pct_seas, 4),
            "longest_seasonal_segment_km": route.longest_seasonal_segment_km,
        },
        **base_endpoints,
    }

# Run startup checks once at import time so they show in the boot log.
# Tests set AMAZON_NAV_DEFER_INIT=1 to skip these (they hit the network and
# load ~470 MB of tiles); tests inject their own state via monkeypatching.
if os.environ.get("AMAZON_NAV_DEFER_INIT") == "1":
    TILE_AVAILABILITY = {"available": [], "missing": []}
    ROUTES: dict[int, routing.RouteResult] = {}
else:
    TILE_AVAILABILITY = verify_monthly_tiles()
    jrc_data.load_all()
    # Pre-render 12 transparent RGBA PNGs at startup so /overlay.png is a
    # static-file lookup. Keeps the slider responsive on cellular over ngrok.
    overlay_png.render_all(CACHE_DIR)

    # Pre-compute 12 A* routes between the two fixed waypoints. Same start/end
    # every month -- the route's shape is the only thing that changes between
    # months because the seasonal-active mask shifts. Months with no connected
    # path return RouteResult(exists=False).
    log.info("Computing 12 A* routes...")
    ROUTES = {}
    if jrc_data.TRANSFORM is None:
        raise RuntimeError("jrc_data.TRANSFORM is None after load_all()")
    for _m in range(1, 13):
        ROUTES[_m] = routing.compute_route(
            jrc_data.classify(_m),
            jrc_data.TRANSFORM,
            WAYPOINT_NORTH,
            WAYPOINT_SOUTH,
        )
    _viable = sum(1 for r in ROUTES.values() if r.exists)
    log.info(f"  {_viable}/12 viable routes computed")


@app.route("/route")
def route():
    try:
        month = int(request.args.get("month", 3))
    except (TypeError, ValueError):
        return jsonify({"error": "month must be an integer 1-12"}), 400
    if not 1 <= month <= 12:
        return jsonify({"error": "month must be 1-12"}), 400

    if jrc_data.TRANSFORM is None:
        return jsonify({"error": "tiles not loaded"}), 503

    cls_now = jrc_data.classify(month)
    prev = month - 1 if month > 1 else 12
    cls_prev = jrc_data.classify(prev)

    stats_now = navigability.corridor_stats(cls_now)
    stats_prev = navigability.corridor_stats(cls_prev)
    mid_lat = jrc_data.mid_lat()

    features = vectorize.classes_to_geojson(cls_now, jrc_data.TRANSFORM)

    full_stats = {
        **stats_now,
        "mid_lat": mid_lat,
        "prev_month": {
            "month": prev,
            "seasonal_active_north": stats_prev["seasonal_active_north"],
            "seasonal_active_south": stats_prev["seasonal_active_south"],
        },
    }
    route = ROUTES.get(month)
    if route is None:
        # Defer-init mode or partial boot: produce a no-route placeholder so
        # the frontend still renders the pins.
        route = routing.RouteResult(
            exists=False, coords=[], segments=[],
            length_km=0.0, permanent_km=0.0, seasonal_km=0.0,
            longest_seasonal_segment_km=0.0,
            start_latlon=WAYPOINT_NORTH, end_latlon=WAYPOINT_SOUTH,
            n_nodes_explored=0,
        )
    advisory_text = advisory.get_advisory(month, route)
    claude_input = advisory.build_claude_input(month, route)

    return jsonify({
        "month": month,
        "type": "FeatureCollection",
        "features": features,
        "stats": full_stats,
        "advisory": advisory_text,
        "claude_input": claude_input,
        "route": _serialize_route(route),
    })


@app.route("/overlay.png")
def overlay_image():
    """Serve the pre-rendered RGBA PNG for ?month=N."""
    try:
        month = int(request.args.get("month", 3))
    except (TypeError, ValueError):
        return jsonify({"error": "month must be an integer 1-12"}), 400
    if not 1 <= month <= 12:
        return jsonify({"error": "month must be 1-12"}), 400
    path = overlay_png.overlay_path(CACHE_DIR, month)
    if not path.exists():
        # Lazy-render if startup hook didn't run (e.g. defer-init mode).
        try:
            overlay_png.render_one(CACHE_DIR, month)
        except RuntimeError:
            return jsonify({"error": "tiles not loaded"}), 503
    resp = send_from_directory(CACHE_DIR, path.name, mimetype="image/png")
    # Browser will cache by URL, but let's be explicit.
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


@app.route("/api/init")
def api_init():
    # jrc_data.BOUNDS is (left, bottom, right, top) = (west, south, east, north).
    # Leaflet's L.imageOverlay wants [[south, west], [north, east]].
    overlay_bounds = None
    if jrc_data.BOUNDS is not None:
        west, south, east, north = jrc_data.BOUNDS
        overlay_bounds = [[south, west], [north, east]]
    return jsonify({
        "default_center": [ISLAND_LAT, ISLAND_LON],
        "default_zoom": 12,
        "overlay_bounds": overlay_bounds,
        "months_available": TILE_AVAILABILITY["available"],
        "months_missing": TILE_AVAILABILITY["missing"],
    })


@app.route("/")
def index():
    if (FRONTEND_DIR / "index.html").exists():
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify({"error": "frontend/index.html not yet created (Step 2)"}), 404


@app.route("/<path:path>")
def static_files(path):
    if (FRONTEND_DIR / path).exists():
        return send_from_directory(FRONTEND_DIR, path)
    return jsonify({"error": f"not found: {path}"}), 404


if __name__ == "__main__":
    # 5000 = macOS AirPlay, 5001 = Docker on this machine. 5050 default; PORT env wins.
    import os
    port = int(os.environ.get("PORT", "5050"))
    app.run(host="0.0.0.0", port=port, debug=False)
