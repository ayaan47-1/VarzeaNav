"""Claude API integration — captions the A* route in one sentence.

This module's job: given a precomputed route (or its absence), produce a
single-sentence advisory for a small-craft operator. Falls back to a
deterministic stub if ANTHROPIC_API_KEY is missing or the API errors.

Caches by month — the route doesn't change within a server boot, so a slider
drag back to a prior month is free.
"""
from __future__ import annotations

import logging
import os
from threading import Lock
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv

if TYPE_CHECKING:  # pragma: no cover - typing-only import
    from routing import RouteResult

log = logging.getLogger("advisory")

load_dotenv()

MODEL = "claude-sonnet-4-5-20250929"
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

_SYSTEM_PROMPT = (
    "You are an Amazon river navigation advisor for municipal logistics. "
    "Write ONE sentence (max 25 words). No bullet points, no headings, no AI "
    "disclaimers, no caveats."
)

_ROUTE_USER_TEMPLATE = """Region: island near (-3.34, -60.19) in the Amazon basin near Manaus.
Month: {month_name}
Route exists: yes
Total length: {length_km:.1f} km
In permanent water: {permanent_km:.1f} km ({percent_permanent_pct}%)
In seasonal-active water: {seasonal_km:.1f} km ({percent_seasonal_pct}%)
Longest seasonal segment: {longest_seasonal_segment_km:.1f} km

Write ONE sentence describing this route to a small-craft operator. Mention the seasonal segment if there is one."""

_NO_ROUTE_USER_TEMPLATE = """Region: island near (-3.34, -60.19) in the Amazon basin near Manaus.
Month: {month_name}
No connected water route exists between the northern and southern shores this month — the seasonal channels that would link them are not active.

Write ONE sentence explaining this to a small-craft operator."""

# (month) -> advisory text cache
_CACHE: dict[int, str] = {}
_CACHE_LOCK = Lock()
_CLIENT = None  # lazy


def _get_client():
    """Lazy import to avoid a hard dependency when only stubbing."""
    global _CLIENT
    if _CLIENT is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        from anthropic import Anthropic
        _CLIENT = Anthropic(api_key=api_key)
    return _CLIENT


def _values_from_route(month: int, route: "RouteResult") -> dict[str, Any]:
    """Construct the {key: value} dict shown in the 'Input to Claude' panel.

    Identical fields whether the route exists or not, so the frontend can
    render the same dl rows in either state. Numbers are pre-rounded.
    """
    if route.exists:
        total = route.length_km if route.length_km > 0 else 1.0
        pct_perm = round(100 * route.permanent_km / total, 1)
        pct_seas = round(100 * route.seasonal_km / total, 1)
    else:
        pct_perm = 0.0
        pct_seas = 0.0
    return {
        "month_name": MONTH_NAMES[month - 1],
        "route_exists": bool(route.exists),
        "length_km": round(float(route.length_km), 1),
        "permanent_km": round(float(route.permanent_km), 1),
        "seasonal_km": round(float(route.seasonal_km), 1),
        "percent_permanent_pct": pct_perm,
        "percent_seasonal_pct": pct_seas,
        "longest_seasonal_segment_km": round(float(route.longest_seasonal_segment_km), 1),
    }


def build_claude_input(month: int, route: "RouteResult") -> dict[str, Any]:
    """Construct the structured input shipped to Claude for `month`.

    Returns the model id, the rendered prompt string, and the named values
    used to render it. Both `get_advisory()` and the /route handler call this
    so the 'Input to Claude' panel shows exactly what the API receives.
    """
    values = _values_from_route(month, route)
    template = _ROUTE_USER_TEMPLATE if route.exists else _NO_ROUTE_USER_TEMPLATE
    prompt = template.format(**values)
    return {
        "model": MODEL,
        "system_prompt": _SYSTEM_PROMPT,
        "prompt": prompt,
        "values": values,
    }


def _stub(month: int, route: "RouteResult") -> str:
    """Deterministic fallback when ANTHROPIC_API_KEY is missing or the API errors."""
    name = MONTH_NAMES[month - 1]
    if not route.exists:
        return (
            f"In {name}, no viable water route connects the two shores — the seasonal "
            "channels between them are dry. (stub advisory — set ANTHROPIC_API_KEY.)"
        )
    if route.seasonal_km > 0:
        return (
            f"In {name}, this {route.length_km:.1f}-km route stays in permanent water "
            f"for {route.permanent_km:.1f} km, then crosses {route.seasonal_km:.1f} km "
            f"of seasonal channels (longest segment {route.longest_seasonal_segment_km:.1f} km). "
            "(stub advisory — set ANTHROPIC_API_KEY for live Claude output.)"
        )
    return (
        f"In {name}, this {route.length_km:.1f}-km route stays entirely in "
        "permanent channels. (stub advisory — set ANTHROPIC_API_KEY.)"
    )


def get_advisory(month: int, route: "RouteResult") -> str:
    """Return cached or freshly-generated advisory text for the given month + route."""
    with _CACHE_LOCK:
        if month in _CACHE:
            return _CACHE[month]

    client = _get_client()
    if client is None:
        text = _stub(month, route)
        with _CACHE_LOCK:
            _CACHE[month] = text
        return text

    payload = build_claude_input(month, route)

    try:
        resp = client.messages.create(
            model=payload["model"],
            max_tokens=200,
            system=payload["system_prompt"],
            messages=[{"role": "user", "content": payload["prompt"]}],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content).strip()
        if not text:
            raise ValueError("empty response from Claude")
    except Exception as e:
        log.warning(f"Claude call failed for month {month}: {e}; falling back to stub")
        text = _stub(month, route)

    with _CACHE_LOCK:
        _CACHE[month] = text
    return text


def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()
