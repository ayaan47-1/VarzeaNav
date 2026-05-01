"""Class array → GeoJSON FeatureCollection.

The full crop is ~11M pixels — vectorizing raw is infeasible. Block-downsample
to <= 256 cells per side via majority-vote, then run rasterio.features.shapes
on the reduced array. Filter to the 3 classes we render.
"""
from __future__ import annotations

from math import ceil

import numpy as np
import rasterio.features
from rasterio.transform import Affine

import jrc_data

MAX_CELLS = 256

# class -> string name in GeoJSON properties
RENDER_CLASSES = {
    jrc_data.CLS_PERMANENT: "permanent",
    jrc_data.CLS_SEASONAL_ACTIVE: "seasonal-active",
    jrc_data.CLS_SEASONAL_INACTIVE: "seasonal-inactive",
}


def block_majority(arr: np.ndarray, k: int, n_classes: int = 5) -> np.ndarray:
    """Downsample by factor k via per-block majority vote.

    For ties, the lower class wins (numpy argmax behaviour). That's fine here:
    seasonal-inactive < seasonal-active < permanent, so ties favor visual
    conservativeness rather than over-selling navigability.
    """
    if k <= 1:
        return arr
    H, W = arr.shape
    Ht = (H // k) * k
    Wt = (W // k) * k
    trimmed = arr[:Ht, :Wt]
    h2, w2 = Ht // k, Wt // k
    blocks = trimmed.reshape(h2, k, w2, k).transpose(0, 2, 1, 3).reshape(h2, w2, k * k)
    counts = np.zeros((h2, w2, n_classes), dtype=np.int32)
    for c in range(n_classes):
        counts[:, :, c] = (blocks == c).sum(axis=2)
    return counts.argmax(axis=2).astype(arr.dtype)


def classes_to_geojson(class_arr: np.ndarray, transform: Affine) -> list[dict]:
    """Vectorize the renderable classes and return a list of GeoJSON Features."""
    H, W = class_arr.shape
    k = max(1, ceil(max(H, W) / MAX_CELLS))
    reduced = block_majority(class_arr, k)
    # The downsampled affine is the original scaled by k in both axes.
    new_transform = transform * Affine.scale(k, k)

    features: list[dict] = []
    # rasterio.features.shapes yields (geom, value) for each connected region
    # of equal value. Mask param skips zero-valued pixels.
    mask = np.isin(reduced, list(RENDER_CLASSES.keys()))
    for geom, value in rasterio.features.shapes(reduced, mask=mask, transform=new_transform):
        cls_name = RENDER_CLASSES.get(int(value))
        if cls_name is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {"class": cls_name},
        })
    return features
