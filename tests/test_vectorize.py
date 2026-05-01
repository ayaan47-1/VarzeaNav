"""Tests for vectorize: block_majority + classes_to_geojson."""
from __future__ import annotations

import numpy as np


def test_block_majority_k1_is_identity(loaded_jrc):
    import vectorize
    arr = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    out = vectorize.block_majority(arr, 1)
    assert np.array_equal(out, arr)


def test_block_majority_uniform_block_returns_that_value(loaded_jrc):
    import vectorize
    arr = np.full((4, 4), 3, dtype=np.uint8)
    out = vectorize.block_majority(arr, 2)
    assert out.shape == (2, 2)
    assert (out == 3).all()


def test_block_majority_picks_most_common(loaded_jrc):
    import vectorize
    # 2x2 block with 3 of class A, 1 of class B -> A wins
    arr = np.array([
        [2, 2],
        [2, 4],
    ], dtype=np.uint8)
    out = vectorize.block_majority(arr, 2)
    assert out.shape == (1, 1)
    assert out[0, 0] == 2


def test_block_majority_truncates_non_divisible_shape(loaded_jrc):
    """5x5 array with k=2 should produce 2x2 output (last row+col dropped)."""
    import vectorize
    arr = np.zeros((5, 5), dtype=np.uint8)
    out = vectorize.block_majority(arr, 2)
    assert out.shape == (2, 2)


def test_block_majority_tie_favors_lower_class(loaded_jrc):
    """A 2x2 block with 2 each of class 2 and class 4 -> argmax picks the lowest count-tied class.
    The implementation says ties favor lower class numerically (numpy argmax behaviour),
    which means inactive seasonal beats active when counts equal — visually conservative."""
    import vectorize
    import jrc_data as J
    arr = np.array([
        [J.CLS_SEASONAL_ACTIVE, J.CLS_SEASONAL_INACTIVE],
        [J.CLS_SEASONAL_INACTIVE, J.CLS_SEASONAL_ACTIVE],
    ], dtype=np.uint8)
    out = vectorize.block_majority(arr, 2)
    assert out[0, 0] == J.CLS_SEASONAL_INACTIVE


def test_classes_to_geojson_returns_only_render_classes(loaded_jrc):
    import vectorize
    import jrc_data as J
    # 8x8 patch with each render class in a distinct quadrant + some land
    arr = np.zeros((8, 8), dtype=np.uint8)
    arr[:4, :4] = J.CLS_PERMANENT
    arr[:4, 4:] = J.CLS_SEASONAL_ACTIVE
    arr[4:, :4] = J.CLS_SEASONAL_INACTIVE
    arr[4:, 4:] = J.CLS_LAND  # transparent — must NOT appear
    arr[6, 6] = J.CLS_RARE     # also must NOT appear
    features = vectorize.classes_to_geojson(arr, loaded_jrc.TRANSFORM)
    classes = {f["properties"]["class"] for f in features}
    assert "land" not in classes
    assert "rare" not in classes
    assert classes <= {"permanent", "seasonal-active", "seasonal-inactive"}


def test_classes_to_geojson_features_have_required_shape(loaded_jrc):
    import vectorize
    import jrc_data as J
    arr = np.full((4, 4), J.CLS_PERMANENT, dtype=np.uint8)
    features = vectorize.classes_to_geojson(arr, loaded_jrc.TRANSFORM)
    assert len(features) >= 1
    for f in features:
        assert f["type"] == "Feature"
        assert f["geometry"]["type"] in ("Polygon", "MultiPolygon")
        assert "class" in f["properties"]


def test_classes_to_geojson_coords_are_in_lon_lat(loaded_jrc):
    """Polygon coordinates must be lon/lat within the crop bounds set by the transform."""
    import vectorize
    import jrc_data as J
    arr = np.full((4, 4), J.CLS_PERMANENT, dtype=np.uint8)
    features = vectorize.classes_to_geojson(arr, loaded_jrc.TRANSFORM)
    # Transform bounds: lon [-60.5, -60.0], lat [-3.5, -3.0]
    for f in features:
        ring = f["geometry"]["coordinates"][0]
        for lon, lat in ring:
            assert -60.5 <= lon <= -60.0
            assert -3.5 <= lat <= -3.0


def test_classes_to_geojson_empty_when_no_render_classes(loaded_jrc):
    import vectorize
    import jrc_data as J
    arr = np.full((4, 4), J.CLS_LAND, dtype=np.uint8)
    features = vectorize.classes_to_geojson(arr, loaded_jrc.TRANSFORM)
    assert features == []
