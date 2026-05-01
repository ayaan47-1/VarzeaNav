# Amazon River Navigation

CBC AI Builders Hackathon — IIT, May 2026.

A web app that visualizes seasonal navigability around an island near Manaus
in the Amazon basin, using JRC Global Surface Water v1.4 satellite data.
Drag a month slider — the map shows which corridors are permanent water vs
seasonally active vs dry, and Claude writes a 2-3 sentence advisory for a
small-craft operator.

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

## Endpoints

- `GET /` — frontend
- `GET /api/init` — boot config: default center, zoom, months availability
- `GET /route?month=N` — main query for month 1-12. Returns:
  ```json
  {
    "month": 6,
    "type": "FeatureCollection",
    "features": [/* permanent / seasonal-active / seasonal-inactive polygons */],
    "stats": {
      "permanent_pixels": 1481376,
      "seasonal_active_north": 234567,
      "seasonal_active_south": 194820,
      "mid_lat": -3.339,
      "prev_month": { ... }
    },
    "advisory": "In June, the southern corridor..."
  }
  ```

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
  app.py              Flask app — /, /api/init, /route
  jrc_data.py         Tile download + crop + classify
  navigability.py     Corridor stats (north/south of midpoint)
  vectorize.py        Class array → GeoJSON (block-majority downsample)
  advisory.py         Claude API integration + stub fallback
  cache/              Downloaded JRC tiles (gitignored)
frontend/
  index.html          Map div, slider, sidebar, legend
  app.js              Leaflet init, debounced slider → fetch → render
  style.css           Layout
.claude/launch.json   Claude Preview server config
.env.example          ANTHROPIC_API_KEY=
```

## Live demo over the network (optional)

```bash
ngrok http 5050
# share the https URL — works on phone, no install needed
```

## Known limitations

See the pitch slide. Documented up front, not pretended away.

## Credits

JRC Global Surface Water v1.4 — Copernicus / European Commission /
Google Earth Engine. ESRI World Imagery basemap (Maxar, Earthstar Geographics).
