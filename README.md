# Amazon River Navigation

CBC AI Builders Hackathon — IIT, May 2026. Won "Most Creative."
Built by Gabriel and Ayaan.

A web app that finds the most viable boat route around an island near Manaus
in the Amazon basin and shows how that route reshapes month by month, using
JRC Global Surface Water v1.4 satellite data.

Drag the month slider — A* shortest-path runs on the per-month classified
raster, drawing the route on the map. In dry months it's a 12 km detour
through permanent channels. In wet months a 6.5 km **shortcut emerges
through flooded forest** (rendered as dashed segments — caution: only open
this month). Claude writes ONE sentence about that specific route.

The interesting bit: **Claude never touches the map.** The polyline you see
is A*'s output — pure numpy, no AI. Claude only writes the side-panel
sentence. The sidebar's "Input to Claude" details panel surfaces the
literal numbers being sent on every request.

## Stack

| Layer | Tech |
|---|---|
| Data | JRC Global Surface Water v1.4 (Copernicus, public domain) |
| Backend | Python + Flask + rasterio |
| AI | Anthropic Claude (Sonnet 4.5) |
| Frontend | Leaflet.js + ESRI World Imagery basemap |

## Quick start

```bash
# 1. Install deps
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. (Optional) Set Claude API key for live advisory
cp .env.example .env
# edit .env: ANTHROPIC_API_KEY=sk-ant-...
# Without a key, the app uses a deterministic stub advisory.

# 3. Run
python backend/app.py
# server boots on http://localhost:5050
# first run downloads ~470 MB of monthly tiles to backend/cache/ (one-time)

# 4. Open the demo
open http://localhost:5050/
```

### Running tests

```bash
pytest                              # unit tests, no network (conftest sets AMAZON_NAV_DEFER_INIT=1)
pytest tests/test_frontend_e2e.py   # Playwright E2E — needs backend already running on :5050
```

## Endpoints

- `GET /` — frontend
- `GET /api/init` — boot config: `default_center`, `default_zoom`,
  `overlay_bounds` (Leaflet `[[south, west], [north, east]]`), `months_available`
- `GET /overlay.png?month=N` — pre-rendered transparent RGBA PNG of the
  per-month classification, cached on disk for instant slider response
- `GET /route?month=N` — main query for month 1-12. Returns:
  ```json
  {
    "month": 6,
    "type": "FeatureCollection",
    "features": [/* invisible click-layer polygons */],
    "stats": { "permanent_pixels": 1481376, "seasonal_active_north": 234567,
               "seasonal_active_south": 194820, "mid_lat": -3.339,
               "prev_month": { "...": "..." } },
    "advisory": "This 6.5 km route is heavily dependent on June high water...",
    "claude_input": {
      "model": "claude-sonnet-4-5-20250929",
      "system_prompt": "...",
      "prompt": "Region: island near (-3.34, -60.19)... Month: June...",
      "values": { "month_name": "June", "length_km": 6.5,
                  "percent_seasonal_pct": 65.2, "...": "..." }
    },
    "route": {
      "exists": true,
      "geometry": { "type": "LineString", "coordinates": [[lon, lat], "..."] },
      "segments": [
        { "class": "permanent", "coordinates": [[lon, lat], "..."], "length_km": 1.5 },
        { "class": "seasonal-active", "coordinates": [[lon, lat], "..."], "length_km": 3.8 },
        { "class": "permanent", "coordinates": [[lon, lat], "..."], "length_km": 1.2 }
      ],
      "stats": {
        "length_km": 6.5,
        "permanent_km": 2.27, "seasonal_km": 4.23,
        "percent_permanent": 0.348, "percent_seasonal": 0.652,
        "longest_seasonal_segment_km": 3.8
      },
      "start": [-3.31, -60.20],
      "end":   [-3.36, -60.20]
    }
  }
  ```

Per-month routes are pre-computed at server startup (≈30 ms total) and
stored in memory. `route.exists: false` means the seasonal-active mask
doesn't connect the two waypoints this month — pins still ship in the
response, the map renders both pins with no polyline, and Claude writes a
one-sentence explanation. With the current waypoints all 12 months are
viable.

## Routing

- **Algorithm:** A* shortest-path on the downsampled (16×) classified raster
  with 8-connectivity, Euclidean heuristic, √2 diagonal step cost.
- **Cost rule:** permanent water = 1.0, seasonal-active = 1.5, everything
  else blocked.
- **Waypoints:** two fixed lat/lons north and south of the validated island,
  picked so the optimal path goes the long way around in dry months
  (≈12 km, 95% permanent) and through flooded forest in wet months
  (≈6.5 km, 65% seasonal). The waypoints themselves don't move; only the
  route between them changes.
- **Connectivity guard:** at boot we compute the connected component
  containing the island anchor and constrain waypoint snap to that
  component, so we never pick endpoints in disjoint watersheds.
- **Simplification:** Douglas-Peucker per-segment with 200 m tolerance,
  preserves class-transition vertices (so dashed-vs-solid switches stay
  pixel-perfect).

## Demo (4-minute pitch flow)

1. **Hook (0:00-0:30)** — Personal story. Pull up the map at March (current
   slider position). "This is an island near Manaus. My family knows it. In
   the wet season, you can take a shortcut north through flooded forest.
   In the dry season that channel disappears. No digital map shows that."
2. **Problem (0:30-1:15)** — Google Maps, ANA, INPE: static or monitoring.
   Nothing routes around seasonality. Municipal logistics has no tool.
3. **Demo (1:15-3:00)** — Drag the slider:
   - Jan (low water): "Most of the floodplain is dry."
   - Apr → Jun: light-blue floods outward, "a 3x increase in seasonal channels."
   - Aug → Oct: the floods recede. The southern corridor stays open longer.
   - Each move: read Claude's advisory. "Notice it tells you which
     corridor is more navigable, what changed last month, with caution flags."
4. **Use of AI (3:00-3:30)** — "Pixel counts are scientific data. Claude
   sits between satellite data and operational decision-making — translation,
   not decoration."
5. **Limitations (3:30-4:00)** — Historical 2021 only (would use ANA real-time
   in production). Surface water, not bathymetry. Climatological — drought
   years masked. Future: per-vessel draft input.

## Project structure

```
backend/
  app.py              Flask app — /, /api/init, /route, /overlay.png
  jrc_data.py         Tile download + crop + classify
  navigability.py     Corridor stats (north/south of midpoint)
  vectorize.py        Class array → GeoJSON (invisible click layer)
  overlay_png.py      Class array → transparent RGBA PNG (the visual layer)
  routing.py          A* shortest-path + Douglas-Peucker simplification
  advisory.py         Claude API integration + stub fallback + build_claude_input
  cache/              Downloaded JRC tiles + 12 pre-rendered PNGs (gitignored)
frontend/
  index.html          Map div, slider, sidebar, legend
  app.js              Leaflet init, debounced slider → fetch → render
  style.css           Layout
tests/                pytest unit tests + Playwright E2E (see conftest.py)
.claude/launch.json   Claude Preview server config
.env.example          ANTHROPIC_API_KEY=
pytest.ini, pyrightconfig.json   Test runner + pyright config
```

## Live demo over the network (optional)

```bash
ngrok http 5050
# share the https URL — works on phone, no install needed
```

## What's in the sidebar

- **"Why this exists"** — dismissible card with the problem statement and
  dataset attribution
- **Big month label** — current slider position
- **ROUTE card** — total length in km (hero number), a stacked bar
  showing % permanent vs % seasonal, and Claude's one-sentence caption
  about *this specific* route. Header shows the `claude-sonnet-4-5` chip.
- **Input to Claude** (collapsible) — the literal structured values being
  sent to the API on every request, so viewers can see the AI's seam
- **Legend** — five rows: three classification swatches plus solid/dashed
  route line swatches
- **Slider readout** — live "X% of seasonal corridors active" + "route this
  month: X.X km" dual indicator

## Known limitations

See the pitch slide. Documented up front, not pretended away.

## Credits

JRC Global Surface Water v1.4 — Copernicus / European Commission /
Google Earth Engine. ESRI World Imagery basemap (Maxar, Earthstar Geographics).

## License

Released under the [MIT License](LICENSE).
