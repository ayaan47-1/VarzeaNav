# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Run / test commands

```bash
python backend/app.py                                        # boot Flask on :5050; first run downloads ~470 MB of JRC tiles + pre-renders 12 PNGs + computes 12 A* routes
PORT=5051 python backend/app.py                              # override port (5000=AirPlay, 5001=Docker on this machine)
pytest                                                       # unit tests; auto-defers heavyweight init via conftest.py
pytest tests/test_app.py::test_route_returns_geojson_envelope  # single test
pytest tests/test_frontend_e2e.py                            # Playwright E2E — requires backend running on :5050, otherwise tests skip
```

Dev deps: `backend/requirements.txt` plus `pytest` and `pytest-playwright` for tests.

## Architecture

The app has a **strict deterministic-data / Claude-only-prose** boundary. Numbers, routes, polylines, pixel classifications — all numpy. Claude writes one sentence about the route. **Don't push numbers or decisions into the LLM.**

### Backend pipeline (boot order matters)

```
jrc_data.load_all()       # downloads JRC tiles, populates module-level OCCURRENCE/MONTHLY/TRANSFORM/BOUNDS/SHAPE
overlay_png.render_all()  # pre-renders 12 transparent RGBA PNGs into backend/cache/, served by /overlay.png
routing.compute_route() x 12  # A* shortest-path between WAYPOINT_NORTH (Iranduba, -3.31,-60.20) and WAYPOINT_SOUTH (Catalão, -3.36,-60.20)
                              # for each month; results cached in app.ROUTES
```

This whole sequence is gated on `AMAZON_NAV_DEFER_INIT != "1"`. Tests set that var, then inject toy state via the `loaded_jrc` fixture.

### Module-level state

`backend/jrc_data.py` exposes `OCCURRENCE`, `MONTHLY`, `TRANSFORM`, `BOUNDS`, `SHAPE` as module globals, populated by `load_all()` at import time and read directly by `app.py`, `navigability.py`, `vectorize.py`, `routing.py`, `overlay_png.py`. Tests stub these via `monkeypatch.setattr` (see the `loaded_jrc` fixture in `tests/conftest.py`) — do **not** import-mock the module.

`backend/app.py` similarly keeps `TILE_AVAILABILITY` and `ROUTES: dict[int, RouteResult]` as module globals.

### Pixel pipeline

```
monthly tile + occurrence layer
  -> jrc_data.classify(month)          # uint8 ndarray, 5 classes: LAND, RARE, SEASONAL_INACTIVE, SEASONAL_ACTIVE, PERMANENT
  -> overlay_png.render_one()          # RGBA PNG; LAND/SEASONAL_INACTIVE alpha 0, RARE/PERMANENT/SEASONAL_ACTIVE colored
  -> routing.compute_route()           # block-majority downsample -> cost grid (perm=1.0, seasonal-active=1.5) -> A* 8-conn -> segments
  -> Leaflet renders the imageOverlay + the route polylines + invisible click GeoJSON
```

Frontend never sees the 5-class GeoJSON visually — it's an invisible interactive layer underneath the raster overlay so users can click pixels for class info. The visible water is the PNG.

### Routing (`backend/routing.py`)

Pure numpy + `heapq`. No new deps. `RouteResult` is a frozen dataclass with `coords` (lat,lon list), `segments` (per-class GeoJSON-ready dicts with `length_km`), and aggregate stats (`length_km`, `permanent_km`, `seasonal_km`, `longest_seasonal_segment_km`). Splits the path into same-class runs so the frontend can draw permanent water as solid lines and seasonal-active as dashed.

Two waypoints are fixed (`WAYPOINT_NORTH/SOUTH` in `app.py`) — chosen specifically so the wet-month shortcut threads through flooded seasonal forest (~6.5 km) and the dry-month detour goes the long way through permanent channels (~12.8 km). That's the demo's hook.

### Advisory (`backend/advisory.py`)

Takes a `RouteResult`, not raw pixel stats. System prompt now constrains Claude to **ONE sentence (max 25 words)**. Two prompt templates: route-exists vs no-route. `_stub()` fallback runs when `ANTHROPIC_API_KEY` is empty/missing or the API errors. Both paths cache by month.

`build_claude_input(month, route)` returns `{model, system_prompt, prompt, values}` — used both internally to call Claude *and* exposed via the `/route` response so the frontend's "Input to Claude" panel shows the literal numbers being sent. Keep these in sync.

### Endpoints

- `GET /` — frontend
- `GET /api/init` — boot config (incl. `overlay_bounds: [[south, west], [north, east]]` for `L.imageOverlay`)
- `GET /overlay.png?month=N` — pre-rendered transparent RGBA PNG, lazily rendered if missing, `Cache-Control: max-age=86400`
- `GET /route?month=N` — returns `{features, stats, advisory, claude_input, route: {exists, geometry, segments, stats, start, end, start_name, end_name}}`

### Test-time API safety

`tests/conftest.py` sets `ANTHROPIC_API_KEY=""` (empty string, *not* `del`) so `load_dotenv(override=False)` in `advisory.py` can't repopulate it from a real `.env` at import. Don't "clean this up" to `monkeypatch.delenv` — the present-but-empty defense is intentional, and `test_advisory.py` has a `fresh_advisory` fixture that also resets `_CLIENT` to `None`.

## Frontend conventions

- Plain ES + Leaflet from a CDN — no bundler, no npm, no build step. Edit `frontend/app.js` directly.
- Layered map: ESRI World Imagery basemap → `/overlay.png` `imageOverlay` (water) → invisible `L.geoJSON` (click handler) → `routeLayerGroup` (split polylines with white casing for legibility) → waypoint `circleMarker` pins (persist across slider moves; only the route polylines are cleared per fetch).
- Slider `input` is debounced 200 ms; in-flight `/route` requests are aborted on a new drag (`AbortController` in `fetchRoutes`).
- Route polyline styling: solid for `class === "permanent"`, `dashArray: "10,8"` for `seasonal-active`. Don't change colors without updating the legend in `index.html`.
- Sidebar shows live route stats (`route-length`, `route-pct-perm`, `route-pct-seas` + bar chart) and an "Input to Claude" `<dl>` (`claude-input-dl`) populated from `data.claude_input.values`.
- Geolocation silently falls back to Manaus if the user is outside the JRC tile bbox `(-70..-60 lon, -10..0 lat)`.

## Pointers

- User-level memory: `~/.claude/projects/-Users-ayaan-Projects-Claude-Builder-Club-Hackathon/memory/` (team, project status, integration philosophy).
- `Proto_code.ipynb` at the repo root is the notebook the backend was extracted from — read it for the numeric thresholds (`occ > 90` ⇒ permanent, `monthly == 2` ⇒ water observed that month).
- `pyrightconfig.json` points pyright at `backend/` with the local `.venv`.
