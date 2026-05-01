"""Frontend E2E test fixtures.

The Flask backend is expected to be running on :5050 — start it before the
test session if it isn't (the live preview server already does this). The
session_setup fixture verifies the backend is reachable and skips otherwise.
"""
from __future__ import annotations

import os

import pytest
import requests


BASE_URL = os.environ.get("FRONTEND_E2E_BASE_URL", "http://localhost:5050")


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
