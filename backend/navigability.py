"""Corridor stats — split the crop horizontally at the midpoint and count
seasonal-active pixels in each half.
"""
from __future__ import annotations

import numpy as np

import jrc_data


def corridor_stats(class_arr: np.ndarray) -> dict:
    h, _ = class_arr.shape
    mid = h // 2
    north = class_arr[:mid]
    south = class_arr[mid:]
    return {
        "permanent_pixels": int((class_arr == jrc_data.CLS_PERMANENT).sum()),
        "seasonal_active_north": int((north == jrc_data.CLS_SEASONAL_ACTIVE).sum()),
        "seasonal_active_south": int((south == jrc_data.CLS_SEASONAL_ACTIVE).sum()),
        "seasonal_inactive_north": int((north == jrc_data.CLS_SEASONAL_INACTIVE).sum()),
        "seasonal_inactive_south": int((south == jrc_data.CLS_SEASONAL_INACTIVE).sum()),
    }
