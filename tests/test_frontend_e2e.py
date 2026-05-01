"""E2E tests for the Amazon River Navigation frontend.

These exercise the user-facing demo flow against a real Flask backend +
real Leaflet + real Claude (or stub if no API key). Assertions are
behavioural — they check that things change, not that exact text matches.
"""
from __future__ import annotations

from .conftest import slider_drag_to, wait_for_advisory_change


def test_page_loads_with_required_elements(page, base_url):
    """Smoke test: navigate to /, verify the core UI shells exist."""
    page.goto(base_url, wait_until="networkidle", timeout=15_000)
    assert page.title() != ""
    page.wait_for_selector("#map", state="visible")
    page.wait_for_selector("#sidebar", state="visible")
    page.wait_for_selector("#month-slider", state="attached")
    page.wait_for_selector("#advisory", state="visible")
    page.wait_for_selector("#legend", state="visible")
    # Initial slider position is March (the dataset default).
    assert page.locator("#month-slider").input_value() == "3"


def test_initial_load_populates_advisory_and_geojson(page, base_url):
    """After page load, the initial fetch should replace the placeholder advisory
    and inject a GeoJSON layer onto the map."""
    page.request.get(f"{base_url}/route?month=3")  # warm cache
    page.goto(base_url, wait_until="networkidle", timeout=15_000)
    advisory = wait_for_advisory_change(page, "Move the slider")
    assert len(advisory) > 30
    assert "Loading" not in advisory

    geojson_count = page.evaluate(
        """() => {
            let n = 0;
            map.eachLayer(l => { if (l instanceof L.GeoJSON) l.eachLayer(() => n++); });
            return n;
        }"""
    )
    assert geojson_count > 0, "expected at least one GeoJSON feature on the map after load"


def test_month_label_reflects_slider(page, base_url):
    page.goto(base_url, wait_until="networkidle", timeout=15_000)
    slider_drag_to(page, 6)
    page.wait_for_function(
        "document.getElementById('month-label').textContent.includes('June')",
        timeout=5_000,
    )
    # CSS uppercases the rendered label; assert against textContent (DOM-level).
    label_text = page.locator("#month-label").inner_text().lower()
    assert "june" in label_text


def test_slider_change_updates_advisory_and_layer(page, base_url):
    """Drag from March to July: advisory text changes and the GeoJSON layer
    updates. This is the core demo moment.

    Pre-warms the Claude cache via direct API hits so the page-driven
    fetch doesn't time out on the first cold call."""
    page.request.get(f"{base_url}/route?month=3")
    page.request.get(f"{base_url}/route?month=7")

    page.goto(base_url, wait_until="networkidle", timeout=15_000)
    march_text = wait_for_advisory_change(page, "Move the slider")

    slider_drag_to(page, 7)
    july_text = wait_for_advisory_change(page, march_text)
    assert july_text != march_text
    assert len(july_text) > 50

    july_count = page.evaluate(
        """() => { let n = 0; map.eachLayer(l => { if (l instanceof L.GeoJSON) l.eachLayer(() => n++); }); return n; }"""
    )
    assert july_count > 0


def test_slider_sweep_through_flood_cycle(page, base_url):
    """Walk through 4 months and confirm each month yields a distinct advisory.

    Loose assertion — exact prose comes from Claude. We can't assume the
    month name appears verbatim (Claude often writes 'this month' instead),
    so we assert each fetch produces a new, non-trivial advisory string."""
    months = [(1, "January"), (4, "April"), (7, "July"), (10, "October")]
    for m, _ in months:
        page.request.get(f"{base_url}/route?month={m}")

    page.goto(base_url, wait_until="networkidle", timeout=15_000)
    last_text = wait_for_advisory_change(page, "Move the slider")

    seen = [last_text]
    for month, _name in months:
        slider_drag_to(page, month)
        new_text = wait_for_advisory_change(page, last_text)
        seen.append(new_text)
        last_text = new_text

    # Every visited month should produce a distinct advisory (per-month cache).
    distinct = set(seen)
    assert len(distinct) >= len(months), \
        f"expected {len(months)}+ distinct advisories, saw {len(distinct)}"


def test_recenter_button_returns_to_island(page, base_url):
    """Pan the map far away, then click 'Center on Manaus' to return."""
    page.goto(base_url, wait_until="networkidle", timeout=15_000)

    page.evaluate("map.setView([10, 10], 5)")  # somewhere very not-Amazon
    after_pan = page.evaluate("[map.getCenter().lat, map.getCenter().lng]")
    assert abs(after_pan[0] - 10) < 0.1

    page.click("#recenter")
    after_click = page.evaluate("[map.getCenter().lat, map.getCenter().lng]")
    assert abs(after_click[0] - (-3.339)) < 0.1
    assert abs(after_click[1] - (-60.189)) < 0.1


def test_legend_lists_three_classes(page, base_url):
    """Spec: legend shows Permanent / Seasonal-active / Seasonal-inactive."""
    page.goto(base_url, wait_until="networkidle", timeout=15_000)
    legend_text = page.locator("#legend").inner_text().lower()
    assert "permanent" in legend_text
    assert "active" in legend_text
    assert "inactive" in legend_text


def test_geojson_classes_match_expected_set(page, base_url):
    """Each rendered feature must carry one of the three render classes."""
    page.goto(base_url, wait_until="networkidle", timeout=15_000)
    page.wait_for_function(
        "!document.getElementById('advisory').textContent.includes('Move the slider')",
        timeout=15_000,
    )
    classes = page.evaluate(
        """() => {
            const set = new Set();
            map.eachLayer(l => {
                if (l instanceof L.GeoJSON) {
                    l.eachLayer(sub => set.add(sub.feature.properties.class));
                }
            });
            return Array.from(set);
        }"""
    )
    valid = {"permanent", "seasonal-active", "seasonal-inactive"}
    assert set(classes) <= valid, f"unexpected feature class(es): {set(classes) - valid}"
    assert len(classes) >= 1


def test_geolocation_outside_tile_keeps_island_default(page, base_url, browser):
    """Spoof geolocation to Chicago (outside the JRC tile) — map should
    stay on the validated island, not jump to Chicago."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        permissions=["geolocation"],
        geolocation={"latitude": 41.836, "longitude": -87.626},  # IIT, Chicago
    )
    p = context.new_page()
    p.goto(base_url, wait_until="networkidle", timeout=15_000)
    p.wait_for_timeout(800)  # let the geolocation callback fire
    center = p.evaluate("[map.getCenter().lat, map.getCenter().lng]")
    assert abs(center[0] - (-3.339)) < 0.5, f"map should stay near Manaus, got {center}"
    context.close()


def test_geolocation_inside_tile_centers_on_user(page, base_url, browser):
    """Spoof geolocation to a point inside the tile — map should center there."""
    inside_tile_lat, inside_tile_lon = -3.5, -60.5  # within (-70..-60, -10..0)
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        permissions=["geolocation"],
        geolocation={"latitude": inside_tile_lat, "longitude": inside_tile_lon},
    )
    p = context.new_page()
    p.goto(base_url, wait_until="networkidle", timeout=15_000)
    p.wait_for_timeout(1500)
    center = p.evaluate("[map.getCenter().lat, map.getCenter().lng]")
    # Should be near the spoofed location, not the default island
    assert abs(center[0] - inside_tile_lat) < 0.1
    assert abs(center[1] - inside_tile_lon) < 0.1
    context.close()


def test_no_console_errors_during_normal_use(page, base_url):
    """Smoke test: no JS errors / failed network requests during the
    primary slider flow."""
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.goto(base_url, wait_until="networkidle", timeout=15_000)
    page.wait_for_function(
        "!document.getElementById('advisory').textContent.includes('Move the slider')",
        timeout=15_000,
    )
    for m in [5, 8, 11, 2]:
        slider_drag_to(page, m)
        page.wait_for_timeout(400)

    assert errors == [], f"console / page errors during normal flow: {errors}"


def test_route_endpoint_returns_geojson(page, base_url):
    """Sanity check that the backend the frontend talks to is the one we expect.
    Catches misrouting (e.g. CORS misconfig, wrong port) before chasing
    Leaflet bugs."""
    response = page.request.get(f"{base_url}/route?month=3")
    assert response.ok
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert isinstance(data["features"], list)
    assert "advisory" in data
    assert "stats" in data
