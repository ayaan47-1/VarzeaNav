"""Shared fixtures for both backend unit tests and frontend E2E tests.

Backend unit tests: stub jrc_data state so tests don't need network/disk
or 470 MB of monthly tiles. Also blocks any real Anthropic API call by
default — tests that want a fake response patch the client explicitly.

Frontend E2E tests: the Flask backend is expected to be running on :5050 —
start it before the test session if it isn't (the live preview server already
does this). The base_url fixture verifies the backend is reachable and skips
otherwise.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Defer the heavyweight init in app.py — the tests inject their own state.
os.environ.setdefault("AMAZON_NAV_DEFER_INIT", "1")
# Make absolutely sure no test ever calls live Claude. Setting the key to
# the empty string (not just popping it) prevents advisory.py's load_dotenv()
# from re-populating it at import time: load_dotenv defaults to override=False,
# so a present-but-empty value wins over the .env file. The fresh_advisory
# fixture in test_advisory.py also resets _CLIENT to None so a stale instance
# from a previous test can't slip through.
os.environ["ANTHROPIC_API_KEY"] = ""


BASE_URL = os.environ.get("FRONTEND_E2E_BASE_URL", "http://localhost:5050")

# ---------------------------------------------------------------------------
# Backend unit test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def toy_occurrence() -> np.ndarray:
    """4x4 occurrence covering all five class buckets, including 255 nodata."""
    return np.array(
        [
            [0,   10,  30,  100],   # land, rare, seasonal, permanent
            [0,   20,  50,  95],
            [255, 16,  90,  91],    # nodata, seasonal-low, seasonal-high, permanent-low
            [0,   15,  50,  92],    # 15 is the rare/seasonal boundary; the rule is occ <= 15 -> rare
        ],
        dtype=np.uint8,
    )


@pytest.fixture
def toy_monthly() -> np.ndarray:
    """Monthly tile aligned with toy_occurrence. Value 2 = water observed."""
    return np.array(
        [
            [1, 1, 2, 2],
            [1, 1, 2, 2],
            [0, 1, 2, 2],
            [1, 1, 1, 1],   # all-land row -> seasonals here remain inactive
        ],
        dtype=np.uint8,
    )


@pytest.fixture
def toy_transform():
    """Affine for a 4x4 crop spanning lon -60.5..-60.0, lat -3.5..-3.0."""
    from rasterio.transform import from_bounds
    return from_bounds(-60.5, -3.5, -60.0, -3.0, 4, 4)


@pytest.fixture
def loaded_jrc(monkeypatch, toy_occurrence, toy_monthly, toy_transform):
    """Stub jrc_data module state so classify/mid_lat work in tests."""
    import jrc_data
    monkeypatch.setattr(jrc_data, "OCCURRENCE", toy_occurrence)
    # Use the same monthly array for every month — tests that need different
    # month-to-month behavior override this directly.
    monkeypatch.setattr(jrc_data, "MONTHLY", {m: toy_monthly.copy() for m in range(1, 13)})
    monkeypatch.setattr(jrc_data, "TRANSFORM", toy_transform)
    monkeypatch.setattr(jrc_data, "BOUNDS", (-60.5, -3.5, -60.0, -3.0))
    monkeypatch.setattr(jrc_data, "SHAPE", toy_occurrence.shape)
    return jrc_data

# ---------------------------------------------------------------------------
# Frontend E2E fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL of the running Flask server."""
    try:
        r = requests.get(f"{BASE_URL}/api/init", timeout=5)
        r.raise_for_status()
    except Exception as e:
        pytest.skip(f"Flask backend not reachable at {BASE_URL}: {e}. "
                    "Start it with `python backend/app.py` from the main worktree.")
    return BASE_URL


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Default Playwright context: viewport big enough for the side-by-side
    map+sidebar layout, and a deny-by-default geolocation permission so the
    fallback path is exercised in tests that don't override it."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 800},
    }


def slider_drag_to(page, month: int) -> None:
    """Programmatically move the slider, mirroring what `input` event listeners do.

    Playwright's drag-on-range-input is fiddly across browsers; the app already
    listens to the `input` event, so dispatching it directly is more reliable
    and tests the same code path the real UI exercises.
    """
    page.evaluate(
        """([m]) => {
            const s = document.getElementById('month-slider');
            s.value = String(m);
            s.dispatchEvent(new Event('input', { bubbles: true }));
        }""",
        [month],
    )


def wait_for_advisory_change(page, prev_text: str, timeout_ms: int = 30_000) -> str:
    """Wait until the advisory has settled on text that:
      (a) differs from prev_text, AND
      (b) is not the transient 'Loading…' state, AND
      (c) is longer than 30 chars (not the static placeholder).
    Returns the new advisory text.
    """
    page.wait_for_function(
        """(prev) => {
            const t = document.getElementById('advisory').textContent.trim();
            return t !== prev && !t.includes('Loading') && t.length > 30;
        }""",
        arg=prev_text,
        timeout=timeout_ms,
    )
    return page.locator("#advisory").inner_text()
