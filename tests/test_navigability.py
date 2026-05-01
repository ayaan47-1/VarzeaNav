"""Tests for navigability.corridor_stats — north/south split at array midpoint."""
from __future__ import annotations

import numpy as np


def test_corridor_stats_keys_present(loaded_jrc):
    import navigability
    cls = loaded_jrc.classify(3)
    stats = navigability.corridor_stats(cls)
    assert set(stats.keys()) == {
        "permanent_pixels",
        "seasonal_active_north", "seasonal_active_south",
        "seasonal_inactive_north", "seasonal_inactive_south",
    }
    assert all(isinstance(v, int) for v in stats.values())


def test_corridor_stats_split_at_midpoint(loaded_jrc):
    """Active pixels in row 0 should land in 'north', row 3 in 'south' (mid=2)."""
    import navigability
    import jrc_data as J
    # 4-row array: place active pixels in known rows
    arr = np.array([
        [J.CLS_SEASONAL_ACTIVE, 0, 0, 0],   # row 0 -> north
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, J.CLS_SEASONAL_ACTIVE],  # row 3 -> south
    ], dtype=np.uint8)
    stats = navigability.corridor_stats(arr)
    assert stats["seasonal_active_north"] == 1
    assert stats["seasonal_active_south"] == 1


def test_corridor_stats_counts_permanent_globally(loaded_jrc):
    import navigability
    import jrc_data as J
    arr = np.full((4, 4), J.CLS_PERMANENT, dtype=np.uint8)
    stats = navigability.corridor_stats(arr)
    assert stats["permanent_pixels"] == 16


def test_corridor_stats_handles_all_zero(loaded_jrc):
    import navigability
    arr = np.zeros((4, 4), dtype=np.uint8)
    stats = navigability.corridor_stats(arr)
    assert all(v == 0 for v in stats.values())


def test_corridor_stats_split_with_odd_height(loaded_jrc):
    """h//2 == 2 when h == 5: rows 0-1 are north, rows 2-4 are south."""
    import navigability
    import jrc_data as J
    arr = np.zeros((5, 2), dtype=np.uint8)
    arr[0, 0] = J.CLS_SEASONAL_ACTIVE   # north
    arr[2, 0] = J.CLS_SEASONAL_ACTIVE   # south (boundary)
    arr[4, 0] = J.CLS_SEASONAL_ACTIVE   # south
    stats = navigability.corridor_stats(arr)
    assert stats["seasonal_active_north"] == 1
    assert stats["seasonal_active_south"] == 2


def test_corridor_stats_distinguishes_active_from_inactive(loaded_jrc):
    """Active vs inactive seasonal pixels must not bleed into each other."""
    import navigability
    import jrc_data as J
    arr = np.array([
        [J.CLS_SEASONAL_ACTIVE, J.CLS_SEASONAL_INACTIVE],  # north
        [J.CLS_SEASONAL_INACTIVE, J.CLS_SEASONAL_ACTIVE],  # south
    ], dtype=np.uint8)
    stats = navigability.corridor_stats(arr)
    assert stats["seasonal_active_north"] == 1
    assert stats["seasonal_inactive_north"] == 1
    assert stats["seasonal_active_south"] == 1
    assert stats["seasonal_inactive_south"] == 1
