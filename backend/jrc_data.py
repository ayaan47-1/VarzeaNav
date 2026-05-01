"""JRC Global Surface Water v1.4 — tile cache + pixel classification.

Loads a ~4000x2756 crop around the validated island (-3.339, -60.189) for
the occurrence layer plus all 12 months of 2021 monthly history. Tiles are
downloaded once into backend/cache/, then read with rasterio at boot.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.transform import Affine
from rasterio.windows import Window, bounds as window_bounds

log = logging.getLogger("jrc")

BUCKET = "https://storage.googleapis.com/global-surface-water"
SHARD = "0000320000-0000440000.tif"  # 70W_0N tile in the monthly2021 sharding
ISLAND_LAT, ISLAND_LON = -3.339, -60.189
CROP_HALF = 2000  # pixels — proto used 2000 -> 4000x4000 max; truncates near east edge

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Class codes
CLS_LAND = 0
CLS_RARE = 1
CLS_SEASONAL_INACTIVE = 2
CLS_SEASONAL_ACTIVE = 3
CLS_PERMANENT = 4

# Module state (populated by load_all)
OCCURRENCE: np.ndarray | None = None
MONTHLY: dict[int, np.ndarray] = {}
TRANSFORM: Affine | None = None
BOUNDS: tuple[float, float, float, float] | None = None  # (left, bottom, right, top)
SHAPE: tuple[int, ...] | None = None


def occurrence_url() -> str:
    return f"{BUCKET}/downloads2021/occurrence/occurrence_70W_0Nv1_4_2021.tif"


def monthly_url(month: int) -> str:
    return f"{BUCKET}/downloads2021/monthly2021/2021_{month:02d}/{SHARD}"


def _download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return
    log.info(f"  downloading {dest.name}...")
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    log.info(f"  -> {dest.name} ({dest.stat().st_size // 1_000_000} MB)")


def _read_island_crop(tif_path: Path) -> tuple[np.ndarray, Affine, tuple[float, float, float, float]]:
    with rasterio.open(tif_path) as ds:
        row, col = ds.index(ISLAND_LON, ISLAND_LAT)
        c0 = max(0, col - CROP_HALF)
        c1 = min(ds.width, col + CROP_HALF)
        r0 = max(0, row - CROP_HALF)
        r1 = min(ds.height, row + CROP_HALF)
        win = Window(c0, r0, c1 - c0, r1 - r0)
        arr = ds.read(1, window=win)
        transform = ds.window_transform(win)
        b = window_bounds(win, ds.transform)
        return arr, transform, (b[0], b[1], b[2], b[3])


def _ensure_monthly_tile(month: int) -> Path:
    dest = CACHE_DIR / f"monthly_2021_{month:02d}.tif"
    _download(monthly_url(month), dest)
    return dest


def load_all() -> None:
    """Idempotent: downloads tiles if missing, loads crops into RAM."""
    global OCCURRENCE, TRANSFORM, BOUNDS, SHAPE

    log.info("Loading JRC occurrence + 12 monthly tiles...")
    occ_path = CACHE_DIR / "occurrence_70W_0N.tif"
    if not occ_path.exists():
        _download(occurrence_url(), occ_path)

    occ_arr, occ_transform, occ_bounds = _read_island_crop(occ_path)
    OCCURRENCE = occ_arr
    TRANSFORM = occ_transform
    BOUNDS = occ_bounds
    SHAPE = occ_arr.shape
    log.info(f"  occurrence: shape={occ_arr.shape} bounds={occ_bounds}")

    # Parallel-download monthly tiles
    log.info("  fetching missing monthly tiles in parallel...")
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(_ensure_monthly_tile, range(1, 13)))

    # Then read crops sequentially (rasterio not always thread-safe)
    for month in range(1, 13):
        path = CACHE_DIR / f"monthly_2021_{month:02d}.tif"
        arr, _, _ = _read_island_crop(path)
        if arr.shape != occ_arr.shape:
            log.warning(f"  month {month:02d} shape {arr.shape} != occurrence {occ_arr.shape}")
        MONTHLY[month] = arr
    log.info(f"  monthly tiles loaded ({len(MONTHLY)} months, {sum(a.nbytes for a in MONTHLY.values()) // 1_000_000} MB)")


def classify(month: int) -> np.ndarray:
    """Return uint8 class array. See CLS_* codes."""
    if OCCURRENCE is None or month not in MONTHLY:
        raise RuntimeError("jrc_data.load_all() must be called before classify()")
    occ = OCCURRENCE
    monthly = MONTHLY[month]
    cls = np.zeros(occ.shape, dtype=np.uint8)  # default = land
    valid = occ != 255  # 255 = nodata (rare for occurrence; 0 means observed-no-water)
    cls[valid & (occ > 0) & (occ <= 15)] = CLS_RARE
    seasonal_mask = valid & (occ > 15) & (occ <= 90)
    cls[seasonal_mask] = CLS_SEASONAL_INACTIVE
    cls[seasonal_mask & (monthly == 2)] = CLS_SEASONAL_ACTIVE
    cls[valid & (occ > 90)] = CLS_PERMANENT
    return cls


def mid_lat() -> float:
    """Geographic midpoint latitude of the loaded crop (for corridor labels).

    Uses BOUNDS so the result is the exact geographic midpoint, not the
    center of the row=h//2 cell (which is off by half a pixel).
    """
    if BOUNDS is None:
        raise RuntimeError("not loaded")
    return (BOUNDS[1] + BOUNDS[3]) / 2
