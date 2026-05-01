"""Tests for jrc_data.classify and jrc_data.mid_lat.

Locks in the proto-validated thresholds:
  occ == 0       -> LAND
  0 < occ <= 15  -> RARE
  15 < occ <= 90 -> SEASONAL_INACTIVE (or _ACTIVE if monthly == 2)
  occ > 90       -> PERMANENT
  occ == 255     -> LAND (nodata treated as land for visual)
"""
from __future__ import annotations

import numpy as np
import pytest


def test_classify_assigns_correct_classes(loaded_jrc):
    """Lock in the proto thresholds against the conftest toy data.
    Row 0: occ=[0,10,30,100], monthly=[1,1,2,2] -> [land, rare, active, perm]
    Row 1: occ=[0,20,50,95],  monthly=[1,1,2,2] -> [land, inactive, active, perm]
    Row 2: occ=[255,16,90,91], monthly=[0,1,2,2] -> [land(nodata), inactive, active, perm]
    Row 3: occ=[0,15,50,92],  monthly=[1,1,1,1] -> [land, rare(occ=15), inactive, perm]
    """
    cls = loaded_jrc.classify(3)
    L, R, SI, SA, P = (
        loaded_jrc.CLS_LAND,
        loaded_jrc.CLS_RARE,
        loaded_jrc.CLS_SEASONAL_INACTIVE,
        loaded_jrc.CLS_SEASONAL_ACTIVE,
        loaded_jrc.CLS_PERMANENT,
    )
    expected = np.array(
        [
            [L, R,  SA, P],
            [L, SI, SA, P],
            [L, SI, SA, P],
            [L, R,  SI, P],
        ],
        dtype=np.uint8,
    )
    assert np.array_equal(cls, expected)


def test_classify_threshold_15_is_rare_not_seasonal(loaded_jrc):
    """occ == 15 must be rare; occ == 16 must be seasonal."""
    occ = np.array([[15, 16]], dtype=np.uint8)
    monthly = np.array([[1, 2]], dtype=np.uint8)
    loaded_jrc.OCCURRENCE = occ
    loaded_jrc.MONTHLY[3] = monthly
    cls = loaded_jrc.classify(3)
    assert cls[0, 0] == loaded_jrc.CLS_RARE
    assert cls[0, 1] == loaded_jrc.CLS_SEASONAL_ACTIVE


def test_classify_threshold_90_is_seasonal_not_permanent(loaded_jrc):
    """occ == 90 must be seasonal; occ == 91 must be permanent."""
    occ = np.array([[90, 91]], dtype=np.uint8)
    monthly = np.array([[1, 1]], dtype=np.uint8)
    loaded_jrc.OCCURRENCE = occ
    loaded_jrc.MONTHLY[3] = monthly
    cls = loaded_jrc.classify(3)
    assert cls[0, 0] == loaded_jrc.CLS_SEASONAL_INACTIVE
    assert cls[0, 1] == loaded_jrc.CLS_PERMANENT


def test_classify_returns_uint8_with_same_shape(loaded_jrc):
    cls = loaded_jrc.classify(3)
    assert cls.dtype == np.uint8
    assert cls.shape == loaded_jrc.OCCURRENCE.shape


def test_classify_raises_when_not_loaded(monkeypatch):
    """If load_all() never ran, classify must fail loudly rather than crash mysteriously."""
    import jrc_data
    monkeypatch.setattr(jrc_data, "OCCURRENCE", None)
    monkeypatch.setattr(jrc_data, "MONTHLY", {})
    with pytest.raises(RuntimeError, match="load_all"):
        jrc_data.classify(3)


def test_classify_raises_for_unknown_month(loaded_jrc):
    """Asking for a month we didn't load must raise rather than silently succeed."""
    loaded_jrc.MONTHLY.pop(7)
    with pytest.raises(RuntimeError, match="load_all"):
        loaded_jrc.classify(7)


def test_mid_lat_is_geographic_midpoint(loaded_jrc):
    """Crop spans -3.5..-3.0, midpoint should be ~-3.25."""
    assert loaded_jrc.mid_lat() == pytest.approx(-3.25, abs=0.05)


def test_mid_lat_raises_when_not_loaded(monkeypatch):
    import jrc_data
    monkeypatch.setattr(jrc_data, "BOUNDS", None)
    with pytest.raises(RuntimeError, match="not loaded"):
        jrc_data.mid_lat()


def test_seasonal_inactive_when_monthly_says_no_water(loaded_jrc):
    """Seasonal pixels stay INACTIVE when the monthly tile shows no water."""
    occ = np.array([[50]], dtype=np.uint8)
    loaded_jrc.OCCURRENCE = occ
    loaded_jrc.MONTHLY[5] = np.array([[1]], dtype=np.uint8)  # land observation
    assert loaded_jrc.classify(5)[0, 0] == loaded_jrc.CLS_SEASONAL_INACTIVE
    loaded_jrc.MONTHLY[5] = np.array([[0]], dtype=np.uint8)  # no observation
    assert loaded_jrc.classify(5)[0, 0] == loaded_jrc.CLS_SEASONAL_INACTIVE


def test_nodata_pixel_stays_land(loaded_jrc):
    """occ == 255 is JRC nodata — must render as land (transparent), not seasonal."""
    occ = np.array([[255]], dtype=np.uint8)
    loaded_jrc.OCCURRENCE = occ
    loaded_jrc.MONTHLY[3] = np.array([[2]], dtype=np.uint8)  # even with water observed
    assert loaded_jrc.classify(3)[0, 0] == loaded_jrc.CLS_LAND
