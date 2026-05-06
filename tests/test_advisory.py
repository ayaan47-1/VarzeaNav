"""Tests for advisory.get_advisory — stub fallback, caching, error handling.

Critical: NO test in this module should make a real Anthropic API call.
The conftest.py forces ANTHROPIC_API_KEY to "" by default, and tests that
exercise the live-call code path inject a fake client via monkeypatch.

Updated for the route-aware contract: get_advisory(month, RouteResult).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def fresh_advisory(monkeypatch):
    """Wipe per-month cache + lazy client so each test gets a clean slate."""
    import advisory
    advisory.clear_cache()
    monkeypatch.setattr(advisory, "_CLIENT", None)
    return advisory


def _route(
    *,
    exists: bool = True,
    length_km: float = 11.9,
    perm_km: float = 11.3,
    seas_km: float = 0.6,
    longest_seas: float = 0.6,
) -> SimpleNamespace:
    """Build a RouteResult-shaped object that get_advisory and the stub accept.

    advisory.py only reads attributes off `route` (`exists`, `length_km`,
    `permanent_km`, `seasonal_km`, `longest_seasonal_segment_km`). We use a
    SimpleNamespace instead of importing the dataclass so the fixture stays
    cheap and routing.py doesn't have to load for the unit tests.
    """
    return SimpleNamespace(
        exists=exists,
        length_km=length_km,
        permanent_km=perm_km,
        seasonal_km=seas_km,
        longest_seasonal_segment_km=longest_seas,
    )


def test_stub_used_when_no_api_key(fresh_advisory, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text = fresh_advisory.get_advisory(3, _route())
    assert "March" in text
    assert "stub" in text.lower()


def test_stub_mentions_seasonal_segment_when_present(fresh_advisory):
    """A wet-month route with a seasonal segment should be flagged in the stub."""
    text = fresh_advisory.get_advisory(6, _route(length_km=6.5, perm_km=2.3, seas_km=4.2, longest_seas=3.8))
    assert "June" in text
    assert "seasonal" in text.lower()


def test_stub_for_pure_permanent_route(fresh_advisory):
    """A dry-month route with zero seasonal km should NOT mention seasonal segments."""
    text = fresh_advisory.get_advisory(1, _route(length_km=11.9, perm_km=11.9, seas_km=0.0, longest_seas=0.0))
    assert "January" in text
    assert "permanent" in text.lower()


def test_stub_for_no_route_state(fresh_advisory):
    """When route.exists is False, the stub explains the broken connectivity."""
    text = fresh_advisory.get_advisory(9, _route(exists=False, length_km=0.0, perm_km=0.0, seas_km=0.0, longest_seas=0.0))
    assert "September" in text
    assert "no" in text.lower() or "dry" in text.lower()


def test_advisory_caches_per_month(fresh_advisory, monkeypatch):
    """Two calls with the same month must return the same cached string,
    even if the route stats change. This is the demo's slider-drag protection.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    a = fresh_advisory.get_advisory(5, _route(length_km=10))
    b = fresh_advisory.get_advisory(5, _route(length_km=20))
    assert a == b


def test_advisory_does_not_cache_across_months(fresh_advisory, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    a = fresh_advisory.get_advisory(5, _route())
    b = fresh_advisory.get_advisory(6, _route())
    assert a != b
    assert "May" in a and "June" in b


def test_clear_cache_actually_clears(fresh_advisory, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fresh_advisory.get_advisory(5, _route())
    assert 5 in fresh_advisory._CACHE
    fresh_advisory.clear_cache()
    assert 5 not in fresh_advisory._CACHE


def test_live_call_uses_returned_text_when_client_present(fresh_advisory, monkeypatch):
    """When a fake client is injected, its response text should be returned (not the stub)."""
    fake_block = MagicMock()
    fake_block.text = "Real Claude says: route is clear."
    fake_response = MagicMock()
    fake_response.content = [fake_block]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    monkeypatch.setattr(fresh_advisory, "_CLIENT", fake_client)

    out = fresh_advisory.get_advisory(3, _route())
    assert out == "Real Claude says: route is clear."
    fake_client.messages.create.assert_called_once()
    kwargs = fake_client.messages.create.call_args.kwargs
    assert kwargs["model"] == fresh_advisory.MODEL
    assert "navigation advisor" in kwargs["system"].lower()
    assert "March" in kwargs["messages"][0]["content"]


def test_live_call_falls_back_to_stub_on_exception(fresh_advisory, monkeypatch):
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = RuntimeError("rate limit")
    monkeypatch.setattr(fresh_advisory, "_CLIENT", fake_client)

    out = fresh_advisory.get_advisory(3, _route())
    assert "stub" in out.lower()
    assert "March" in out


def test_live_call_falls_back_to_stub_on_empty_response(fresh_advisory, monkeypatch):
    """Empty/whitespace text should not be passed through silently."""
    fake_block = MagicMock()
    fake_block.text = "   "
    fake_response = MagicMock()
    fake_response.content = [fake_block]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    monkeypatch.setattr(fresh_advisory, "_CLIENT", fake_client)

    out = fresh_advisory.get_advisory(3, _route())
    assert "stub" in out.lower()


def test_route_prompt_includes_length_and_permanent_seasonal_split(fresh_advisory, monkeypatch):
    """The Claude prompt must include length_km, permanent_km, and seasonal_km
    so the model can write a route-specific caption (not a generic one)."""
    fake_block = MagicMock()
    fake_block.text = "x"
    fake_response = MagicMock()
    fake_response.content = [fake_block]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    monkeypatch.setattr(fresh_advisory, "_CLIENT", fake_client)

    fresh_advisory.get_advisory(6, _route(length_km=6.5, perm_km=2.3, seas_km=4.2, longest_seas=3.8))
    user_msg = fake_client.messages.create.call_args.kwargs["messages"][0]["content"]
    # length and class breakdown must be in the prompt
    assert "6.5" in user_msg
    assert "2.3" in user_msg
    assert "4.2" in user_msg
    assert "3.8" in user_msg
    assert "June" in user_msg


def test_no_route_prompt_uses_distinct_template(fresh_advisory, monkeypatch):
    """When route.exists is False, the prompt must not advertise route stats —
    it should explain the broken connectivity instead.

    Regression guard: an earlier draft of build_claude_input rendered the
    route template even for exists=False, producing nonsense like
    'Total length: 0.0 km, percent permanent: 0%'.
    """
    fake_block = MagicMock()
    fake_block.text = "x"
    fake_response = MagicMock()
    fake_response.content = [fake_block]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    monkeypatch.setattr(fresh_advisory, "_CLIENT", fake_client)

    fresh_advisory.get_advisory(9, _route(exists=False, length_km=0, perm_km=0, seas_km=0, longest_seas=0))
    user_msg = fake_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "September" in user_msg
    # No-route template explicitly says no connected route exists
    assert "no connected" in user_msg.lower() or "not active" in user_msg.lower()


def test_build_claude_input_values_include_route_keys(fresh_advisory):
    """Regression: the values dict shipped to the frontend must include the
    route-specific keys the 'Input to Claude' panel expects to render."""
    payload = fresh_advisory.build_claude_input(
        6, _route(length_km=6.5, perm_km=2.3, seas_km=4.2, longest_seas=3.8)
    )
    values = payload["values"]
    expected_keys = {
        "month_name", "route_exists", "length_km", "permanent_km",
        "seasonal_km", "percent_permanent_pct", "percent_seasonal_pct",
        "longest_seasonal_segment_km",
    }
    assert expected_keys.issubset(values.keys())
    assert values["month_name"] == "June"
    assert values["route_exists"] is True
    assert values["length_km"] == 6.5
    # Percents are pre-rounded ints/floats; the panel renders them directly.
    assert abs(values["percent_permanent_pct"] - (2.3 / 6.5 * 100)) < 0.5
