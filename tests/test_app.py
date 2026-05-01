"""Tests for the Flask app routes — uses the test client, no live server.

The conftest sets AMAZON_NAV_DEFER_INIT=1 so importing app.py does NOT call
verify_monthly_tiles() or jrc_data.load_all() (both of which hit the network).
The loaded_jrc fixture stubs the in-memory state separately.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def client(loaded_jrc, monkeypatch):  # noqa: ARG001 — loaded_jrc has setup side effects
    """Flask test client with jrc_data state stubbed and Claude pinned to stub mode."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import advisory
    advisory.clear_cache()
    monkeypatch.setattr(advisory, "_CLIENT", None)

    import app as app_module
    app_module.TILE_AVAILABILITY = {"available": list(range(1, 13)), "missing": []}
    app_module.app.testing = True
    return app_module.app.test_client()


def test_route_rejects_non_integer_month(client):
    rv = client.get("/route?month=abc")
    assert rv.status_code == 400
    body = rv.get_json()
    assert "error" in body


@pytest.mark.parametrize("bad_month", [0, 13, -1, 99])
def test_route_rejects_out_of_range_month(client, bad_month):
    rv = client.get(f"/route?month={bad_month}")
    assert rv.status_code == 400


def test_route_returns_geojson_envelope(client):
    rv = client.get("/route?month=3")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["type"] == "FeatureCollection"
    assert isinstance(body["features"], list)
    assert "stats" in body
    assert "advisory" in body
    assert body["month"] == 3


def test_route_stats_contain_required_fields(client):
    body = client.get("/route?month=3").get_json()
    stats = body["stats"]
    assert "permanent_pixels" in stats
    assert "seasonal_active_north" in stats
    assert "seasonal_active_south" in stats
    assert "mid_lat" in stats
    assert "prev_month" in stats
    assert stats["prev_month"]["month"] == 2


def test_route_january_prev_month_wraps_to_december(client):
    body = client.get("/route?month=1").get_json()
    assert body["stats"]["prev_month"]["month"] == 12


def test_route_features_are_typed(client):
    body = client.get("/route?month=3").get_json()
    valid_classes = {"permanent", "seasonal-active", "seasonal-inactive"}
    for feat in body["features"]:
        assert feat["type"] == "Feature"
        assert feat["properties"]["class"] in valid_classes
        assert feat["geometry"]["type"] in ("Polygon", "MultiPolygon")


def test_api_init_returns_required_fields(client):
    body = client.get("/api/init").get_json()
    assert body["default_center"] == [-3.339, -60.189]
    assert isinstance(body["default_zoom"], int)
    assert body["months_available"] == list(range(1, 13))
    assert body["months_missing"] == []


def test_route_default_month_is_three(client):
    rv = client.get("/route")
    body = rv.get_json()
    assert rv.status_code == 200
    assert body["month"] == 3


def test_route_advisory_is_deterministic_when_stubbed(client):
    """Without an API key, calling the same month twice yields identical advisory text."""
    a = client.get("/route?month=4").get_json()["advisory"]
    b = client.get("/route?month=4").get_json()["advisory"]
    assert a == b


def test_route_advisory_changes_between_months(client):
    a = client.get("/route?month=4").get_json()["advisory"]
    b = client.get("/route?month=10").get_json()["advisory"]
    assert a != b
    assert "April" in a
    assert "October" in b


def test_index_returns_404_when_frontend_missing(client, monkeypatch):
    """If frontend/index.html is missing, the root route should report it,
    not crash."""
    import app as app_module
    fake_dir = app_module.FRONTEND_DIR.parent / "nonexistent_frontend"
    monkeypatch.setattr(app_module, "FRONTEND_DIR", fake_dir)
    rv = client.get("/")
    assert rv.status_code == 404
    body = rv.get_json()
    assert "frontend" in body["error"].lower()


def test_static_path_returns_404_for_missing_file(client):
    rv = client.get("/does-not-exist.js")
    assert rv.status_code == 404


def test_index_serves_html_when_present(client):
    """The frontend/index.html shipped with the repo should be served at /."""
    rv = client.get("/")
    assert rv.status_code == 200
    assert b"<html" in rv.data.lower() or b"<!doctype" in rv.data.lower()


def test_static_path_serves_app_js(client):
    rv = client.get("/app.js")
    assert rv.status_code == 200


def test_head_check_success_with_mocked_request(monkeypatch):
    """head_check returns (month, None, content_length) on HTTP 200."""
    import app as app_module
    import requests

    class FakeResp:
        status_code = 200
        headers = {"content-length": "12345"}

    def fake_head(url, timeout, allow_redirects):
        assert "monthly2021/2021_03" in url
        return FakeResp()

    monkeypatch.setattr(requests, "head", fake_head)
    month, err, length = app_module.head_check(3)
    assert month == 3
    assert err is None
    assert length == 12345


def test_head_check_returns_error_on_non_200(monkeypatch):
    import app as app_module
    import requests

    class FakeResp:
        status_code = 404
        headers = {}

    monkeypatch.setattr(requests, "head", lambda *a, **k: FakeResp())
    month, err, length = app_module.head_check(7)
    assert month == 7
    assert err == "HTTP 404"
    assert length == 0


def test_head_check_returns_error_on_request_exception(monkeypatch):
    import app as app_module
    import requests

    def boom(*a, **k):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(requests, "head", boom)
    month, err, length = app_module.head_check(11)
    assert month == 11
    assert err is not None and "network down" in err
    assert length == 0


def test_verify_monthly_tiles_logs_availability(monkeypatch):
    """verify_monthly_tiles aggregates HEAD-checks across all 12 months."""
    import app as app_module

    def fake_head_check(month):
        # Simulate month 5 missing, others present
        if month == 5:
            return month, "HTTP 404", 0
        return month, None, 1_000_000

    monkeypatch.setattr(app_module, "head_check", fake_head_check)
    result = app_module.verify_monthly_tiles()
    assert result["available"] == [1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12]
    assert result["missing"] == [5]
