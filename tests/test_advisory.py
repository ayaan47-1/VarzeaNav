"""Tests for advisory.get_advisory — stub fallback, caching, error handling.

Critical: NO test in this module should make a real Anthropic API call.
The conftest.py removes ANTHROPIC_API_KEY by default, and tests that want
to exercise the live-call code path patch advisory._CLIENT directly.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def fresh_advisory(monkeypatch):
    """Wipe per-month cache + lazy client so each test gets a clean slate."""
    import advisory
    advisory.clear_cache()
    monkeypatch.setattr(advisory, "_CLIENT", None)
    return advisory


def _stats(perm=1000, n_active=200, s_active=400, n_prev=150, s_prev=350, mid_lat=-3.34):
    return {
        "permanent_pixels": perm,
        "seasonal_active_north": n_active,
        "seasonal_active_south": s_active,
        "seasonal_inactive_north": 100,
        "seasonal_inactive_south": 100,
        "mid_lat": mid_lat,
        "prev_month": {
            "month": 2,
            "seasonal_active_north": n_prev,
            "seasonal_active_south": s_prev,
        },
    }


def test_stub_used_when_no_api_key(fresh_advisory, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text = fresh_advisory.get_advisory(3, _stats())
    assert "March" in text
    assert "stub" in text.lower()


def test_stub_picks_corridor_with_more_active_pixels(fresh_advisory):
    """Southern corridor with more active pixels -> stub mentions 'southern'."""
    text = fresh_advisory.get_advisory(7, _stats(n_active=100, s_active=900))
    assert "southern" in text.lower()
    assert "northern" not in text.lower()


def test_stub_picks_north_when_north_dominates(fresh_advisory):
    text = fresh_advisory.get_advisory(7, _stats(n_active=900, s_active=100))
    assert "northern" in text.lower()


def test_advisory_caches_per_month(fresh_advisory, monkeypatch):
    """Two calls with the same month must return the same cached string,
    even if the input stats change. This is the demo's slider-drag protection.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    a = fresh_advisory.get_advisory(5, _stats(s_active=100))
    b = fresh_advisory.get_advisory(5, _stats(s_active=999_999))
    assert a == b


def test_advisory_does_not_cache_across_months(fresh_advisory, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    a = fresh_advisory.get_advisory(5, _stats())
    b = fresh_advisory.get_advisory(6, _stats())
    assert a != b
    assert "May" in a and "June" in b


def test_clear_cache_actually_clears(fresh_advisory, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fresh_advisory.get_advisory(5, _stats())
    assert 5 in fresh_advisory._CACHE
    fresh_advisory.clear_cache()
    assert 5 not in fresh_advisory._CACHE


def test_live_call_uses_returned_text_when_client_present(fresh_advisory, monkeypatch):
    """When a fake client is injected, its response text should be returned (not the stub)."""
    fake_block = MagicMock()
    fake_block.text = "Real Claude says: corridor open."
    fake_response = MagicMock()
    fake_response.content = [fake_block]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    monkeypatch.setattr(fresh_advisory, "_CLIENT", fake_client)

    out = fresh_advisory.get_advisory(3, _stats())
    assert out == "Real Claude says: corridor open."
    fake_client.messages.create.assert_called_once()
    # Make sure we sent the right model
    kwargs = fake_client.messages.create.call_args.kwargs
    assert kwargs["model"] == fresh_advisory.MODEL
    # And the system prompt + user message both reference our task
    assert "navigation advisor" in kwargs["system"].lower()
    assert "March" in kwargs["messages"][0]["content"]


def test_live_call_falls_back_to_stub_on_exception(fresh_advisory, monkeypatch):
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = RuntimeError("rate limit")
    monkeypatch.setattr(fresh_advisory, "_CLIENT", fake_client)

    out = fresh_advisory.get_advisory(3, _stats())
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

    out = fresh_advisory.get_advisory(3, _stats())
    assert "stub" in out.lower()


def test_user_message_references_corridor_midpoint_lat(fresh_advisory, monkeypatch):
    """The Claude prompt must anchor its corridor labels to the mid_lat we computed."""
    fake_block = MagicMock()
    fake_block.text = "x"
    fake_response = MagicMock()
    fake_response.content = [fake_block]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    monkeypatch.setattr(fresh_advisory, "_CLIENT", fake_client)

    fresh_advisory.get_advisory(3, _stats(mid_lat=-3.339))
    user_msg = fake_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "-3.34" in user_msg or "-3.339" in user_msg or "-3.33" in user_msg
