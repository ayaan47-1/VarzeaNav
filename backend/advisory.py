"""Claude API integration — turns pixel stats into a 2-3 sentence advisory.

Falls back to a deterministic stub if ANTHROPIC_API_KEY is missing or the API
errors. Caches by month so a slider drag back to a prior month is free.
"""
from __future__ import annotations

import logging
import os
from threading import Lock

from dotenv import load_dotenv

log = logging.getLogger("advisory")

load_dotenv()  # picks up .env at project root

MODEL = "claude-sonnet-4-5-20250929"
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

_SYSTEM_PROMPT = (
    "You are an Amazon river navigation advisor for municipal logistics. "
    "Write 2-3 sentences. No bullet points, no headings, no AI disclaimers."
)

_USER_TEMPLATE = """Region: island near (-3.34, -60.19) in the Amazon basin near Manaus.
Month: {month_name}
Permanent water pixels: {perm} (year-round navigable)
Northern corridor (north of latitude {mid_lat:.2f}) — seasonal active: {n_now} (was {n_prev} in {prev_name})
Southern corridor (south of latitude {mid_lat:.2f}) — seasonal active: {s_now} (was {s_prev} in {prev_name})

Tell a small-craft operator which corridor is more navigable this month, what changed from last month, and any caution flag."""

# (month) -> advisory text cache
_CACHE: dict[int, str] = {}
_CACHE_LOCK = Lock()
_CLIENT = None  # lazy


def _get_client():
    """Lazy import to avoid hard dependency when only stubbing."""
    global _CLIENT
    if _CLIENT is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        from anthropic import Anthropic
        _CLIENT = Anthropic(api_key=api_key)
    return _CLIENT


def _stub(month: int, stats: dict) -> str:
    n, s = stats["seasonal_active_north"], stats["seasonal_active_south"]
    side = "northern" if n > s else "southern"
    return (
        f"In {MONTH_NAMES[month-1]}, the {side} corridor shows the most active "
        f"seasonal water ({max(n, s):,} pixels). Permanent channels remain navigable. "
        "(stub advisory — set ANTHROPIC_API_KEY for live Claude output.)"
    )


def get_advisory(month: int, stats: dict) -> str:
    """Return cached or freshly-generated advisory text for the given month + stats."""
    with _CACHE_LOCK:
        if month in _CACHE:
            return _CACHE[month]

    client = _get_client()
    if client is None:
        text = _stub(month, stats)
        with _CACHE_LOCK:
            _CACHE[month] = text
        return text

    prev_idx = month - 1 if month > 1 else 12
    prev_stats = stats.get("prev_month", {})
    user_msg = _USER_TEMPLATE.format(
        month_name=MONTH_NAMES[month - 1],
        prev_name=MONTH_NAMES[prev_idx - 1],
        perm=stats.get("permanent_pixels", 0),
        mid_lat=stats.get("mid_lat", -3.34),
        n_now=stats.get("seasonal_active_north", 0),
        s_now=stats.get("seasonal_active_south", 0),
        n_prev=prev_stats.get("seasonal_active_north", 0),
        s_prev=prev_stats.get("seasonal_active_south", 0),
    )

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        # Concatenate text blocks defensively
        text = "".join(getattr(b, "text", "") for b in resp.content).strip()
        if not text:
            raise ValueError("empty response from Claude")
    except Exception as e:
        log.warning(f"Claude call failed for month {month}: {e}; falling back to stub")
        text = _stub(month, stats)

    with _CACHE_LOCK:
        _CACHE[month] = text
    return text


def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()
