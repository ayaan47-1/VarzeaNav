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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("app")

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
CACHE_DIR = ROOT / "backend" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ISLAND_LAT, ISLAND_LON = -3.339, -60.189

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

# Run startup checks once at import time so they show in the boot log.
# Tests set AMAZON_NAV_DEFER_INIT=1 to skip these (they hit the network and
# load ~470 MB of tiles); tests inject their own state via monkeypatching.
if os.environ.get("AMAZON_NAV_DEFER_INIT") == "1":
    TILE_AVAILABILITY = {"available": [], "missing": []}
else:
    TILE_AVAILABILITY = verify_monthly_tiles()
    jrc_data.load_all()


@app.route("/route")
def route():
    try:
        month = int(request.args.get("month", 3))
    except (TypeError, ValueError):
        return jsonify({"error": "month must be an integer 1-12"}), 400
    if not 1 <= month <= 12:
        return jsonify({"error": "month must be 1-12"}), 400

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
    advisory_text = advisory.get_advisory(month, full_stats)

    return jsonify({
        "month": month,
        "type": "FeatureCollection",
        "features": features,
        "stats": full_stats,
        "advisory": advisory_text,
    })


@app.route("/api/init")
def api_init():
    return jsonify({
        "default_center": [ISLAND_LAT, ISLAND_LON],
        "default_zoom": 11,
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
