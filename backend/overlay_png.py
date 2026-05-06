"""Per-month classification renderer — uint8 class array → transparent RGBA PNG.

Used by the Anthropic-video polish pass to replace the pixelated GeoJSON
render with a smooth raster overlay. Pre-rendered once at app startup; served
from disk on each /overlay.png request.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

import jrc_data

log = logging.getLogger("overlay_png")

# RGBA palette per class. Land + seasonal-inactive are fully transparent so
# the basemap shows through; seasonal-inactive intentionally has alpha 0 — the
# off-state is the *absence* of color, not gray-on-imagery.
PALETTE: dict[int, tuple[int, int, int, int]] = {
    jrc_data.CLS_LAND:              (0,   0,   0,   0),
    jrc_data.CLS_RARE:              (200, 230, 201, 80),
    jrc_data.CLS_SEASONAL_INACTIVE: (0,   0,   0,   0),
    # Seasonal-active alpha bumped to 250 so the cyan reads clearly even when
    # it sits over forest pixels in the basemap. Otherwise the underlying
    # green dominates and the route can look like it's crossing dry land.
    jrc_data.CLS_SEASONAL_ACTIVE:   (79,  195, 247, 250),
    jrc_data.CLS_PERMANENT:         (13,  71,  161, 235),
}


def render_rgba(class_arr: np.ndarray) -> Image.Image:
    """Map a uint8 class array to an RGBA Pillow image."""
    h, w = class_arr.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    for cls_value, color in PALETTE.items():
        rgba[class_arr == cls_value] = color
    return Image.fromarray(rgba, mode="RGBA")


def overlay_path(cache_dir: Path, month: int) -> Path:
    return cache_dir / f"overlay_{month:02d}.png"


def render_one(cache_dir: Path, month: int, *, force: bool = False) -> Path:
    """Render one month to disk. Idempotent — skips if already cached."""
    dest = overlay_path(cache_dir, month)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return dest
    cls = jrc_data.classify(month)
    img = render_rgba(cls)
    tmp = dest.with_suffix(".png.part")
    img.save(tmp, format="PNG", optimize=True)
    tmp.replace(dest)
    log.info(f"  overlay_{month:02d}.png ({dest.stat().st_size // 1024} KB)")
    return dest


def render_all(cache_dir: Path, *, force: bool = False, max_workers: int = 4) -> dict[int, Path]:
    """Render all 12 month overlays. Parallelized — Pillow releases the GIL on encode."""
    log.info(f"Rendering 12 PNG overlays (force={force}, workers={max_workers})...")
    paths: dict[int, Path] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(render_one, cache_dir, m, force=force): m for m in range(1, 13)}
        for fut in futures:
            m = futures[fut]
            paths[m] = fut.result()
    log.info(f"  {len(paths)}/12 PNG overlays rendered")
    return paths
