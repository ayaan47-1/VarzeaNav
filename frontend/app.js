// Amazon River Navigation — frontend
//
// Architecture: raster PNG overlay (smooth) + invisible L.geoJSON click layer
// + per-month A* route drawn as split polylines (solid permanent, dashed
// seasonal). Two waypoint pins persist across slider moves.

const ISLAND = { lat: -3.339, lon: -60.189 };
const TILE_BOUNDS = { W: -70, S: -10, E: -60, N: 0 }; // 70W_0N JRC tile

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const map = L.map("map", { zoomControl: true }).setView([ISLAND.lat, ISLAND.lon], 12);

L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  {
    attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics",
    maxZoom: 18,
  }
).addTo(map);

L.circleMarker([ISLAND.lat, ISLAND.lon], {
  radius: 5, color: "#0d47a1", weight: 2, fillColor: "#fff", fillOpacity: 1,
}).addTo(map).bindPopup("Validated island (-3.339, -60.189)");

function inTile(lat, lon) {
  return (
    lat >= TILE_BOUNDS.S && lat <= TILE_BOUNDS.N &&
    lon >= TILE_BOUNDS.W && lon <= TILE_BOUNDS.E
  );
}

if ("geolocation" in navigator) {
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { latitude, longitude } = pos.coords;
      if (inTile(latitude, longitude)) {
        map.setView([latitude, longitude], 11);
      }
    },
    () => { /* Manaus default */ },
    { timeout: 5000, maximumAge: 60000 }
  );
}

// DOM handles
const slider = document.getElementById("month-slider");
const monthLabel = document.getElementById("month-label");
const advisoryEl = document.getElementById("advisory");
const routeCard = document.getElementById("route-card");
const routeLengthEl = document.getElementById("route-length");
const routePctPermEl = document.getElementById("route-pct-perm");
const routePctSeasEl = document.getElementById("route-pct-seas");
const routeBarPerm = document.getElementById("route-bar-perm");
const routeBarSeas = document.getElementById("route-bar-seas");
const claudeInputDl = document.getElementById("claude-input-dl");
const activePctEl = document.getElementById("active-pct");
const routeReadoutValueEl = document.getElementById("route-readout-value");
const whyCard = document.getElementById("why-card");
const whyDismiss = document.getElementById("why-dismiss");

function setMonthLabel(month) {
  monthLabel.textContent = MONTH_NAMES[month - 1];
}

// Map layers ----------------------------------------------------------------

const INVISIBLE_STYLE = { weight: 0, fillOpacity: 0, opacity: 0 };

let rasterLayer = null;
let geoJsonLayer = null;
let overlayBounds = null;

// Route layers
const routeLayerGroup = L.layerGroup().addTo(map);
const ROUTE_BASE_COLOR = "#0d47a1";
const ROUTE_CASING_COLOR = "#ffffff";

let waypointStartPin = null;
let waypointEndPin = null;

function setRasterMonth(month) {
  if (!overlayBounds) return;
  const url = `/overlay.png?month=${month}`;
  if (rasterLayer) {
    rasterLayer.setUrl(url);
    return;
  }
  rasterLayer = L.imageOverlay(url, overlayBounds, {
    opacity: 1.0,
    interactive: false,
  }).addTo(map);
}

function renderInvisibleGeoJson(features) {
  if (geoJsonLayer) {
    map.removeLayer(geoJsonLayer);
    geoJsonLayer = null;
  }
  if (!features || features.length === 0) return;
  geoJsonLayer = L.geoJSON(features, {
    style: () => INVISIBLE_STYLE,
    interactive: true,
  }).addTo(map);
}

function ensureWaypointPins(routeData) {
  // routeData.start/end are [lat, lon]; start_name/end_name are the place
  // labels rendered next to the pin.
  if (!routeData?.start || !routeData?.end) return;
  const { start, end, start_name, end_name } = routeData;
  const popup = (name, ll) => `<strong>${name}</strong><br>${ll[0].toFixed(3)}, ${ll[1].toFixed(3)}`;

  if (!waypointStartPin) {
    waypointStartPin = L.circleMarker(start, {
      radius: 7, color: ROUTE_BASE_COLOR, weight: 2,
      fillColor: "#ffffff", fillOpacity: 1,
    }).addTo(map);
    waypointStartPin.bindTooltip(start_name || "Start", {
      permanent: true, direction: "top", offset: [0, -8],
      className: "waypoint-label",
    });
  } else {
    waypointStartPin.setLatLng(start);
    if (start_name) waypointStartPin.setTooltipContent(start_name);
  }
  waypointStartPin.bindPopup(popup(start_name || "Start", start));

  if (!waypointEndPin) {
    waypointEndPin = L.circleMarker(end, {
      radius: 7, color: ROUTE_BASE_COLOR, weight: 2,
      fillColor: "#ffffff", fillOpacity: 1,
    }).addTo(map);
    waypointEndPin.bindTooltip(end_name || "End", {
      permanent: true, direction: "bottom", offset: [0, 8],
      className: "waypoint-label",
    });
  } else {
    waypointEndPin.setLatLng(end);
    if (end_name) waypointEndPin.setTooltipContent(end_name);
  }
  waypointEndPin.bindPopup(popup(end_name || "End", end));
}

function renderRoute(routeData) {
  // Wipe previous route polylines (keep pins; they're owned outside the group).
  routeLayerGroup.clearLayers();
  if (!routeData) return;
  ensureWaypointPins(routeData);
  if (!routeData.exists || !routeData.segments) return;

  for (const seg of routeData.segments) {
    if (!seg.coordinates || seg.coordinates.length < 2) continue;
    // GeoJSON ships [lon, lat]; Leaflet polylines want [lat, lon].
    const latlngs = seg.coordinates.map(([lon, lat]) => [lat, lon]);
    const isSeasonal = seg.class === "seasonal-active";
    const dashArray = isSeasonal ? "10,8" : null;

    // Casing (under the colored line) for legibility on satellite imagery.
    L.polyline(latlngs, {
      color: ROUTE_CASING_COLOR, weight: 9, opacity: 0.85,
      lineCap: "round", lineJoin: "round", interactive: false,
    }).addTo(routeLayerGroup);

    // Colored line (interactive: clickable for popup).
    const line = L.polyline(latlngs, {
      color: ROUTE_BASE_COLOR, weight: 5, opacity: 1.0,
      dashArray, lineCap: "round", lineJoin: "round",
    }).addTo(routeLayerGroup);
    line.bindPopup(
      `<strong>${seg.class === "permanent" ? "Permanent" : "Seasonal — active"}</strong><br>${seg.length_km.toFixed(1)} km`
    );
  }
}

// Sidebar updates -----------------------------------------------------------

const VALUE_KEYS_ORDER = [
  ["month",                          "month_name"],
  ["route_exists",                   "route_exists"],
  ["length_km",                      "length_km"],
  ["permanent_km",                   "permanent_km"],
  ["seasonal_km",                    "seasonal_km"],
  ["percent_permanent_pct",          "percent_permanent_pct"],
  ["percent_seasonal_pct",           "percent_seasonal_pct"],
  ["longest_seasonal_segment_km",    "longest_seasonal_segment_km"],
];

function fmtValue(v) {
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "number") return v.toLocaleString("en-US");
  return String(v ?? "—");
}

function renderClaudeInput(values) {
  claudeInputDl.replaceChildren();
  if (!values) return;
  const frag = document.createDocumentFragment();
  for (const [label, key] of VALUE_KEYS_ORDER) {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = fmtValue(values[key]);
    frag.appendChild(dt);
    frag.appendChild(dd);
  }
  claudeInputDl.appendChild(frag);
}

function renderActivePct(stats) {
  if (!stats) { activePctEl.textContent = "—"; return; }
  const an  = stats.seasonal_active_north   || 0;
  const as_ = stats.seasonal_active_south   || 0;
  const inN = stats.seasonal_inactive_north || 0;
  const inS = stats.seasonal_inactive_south || 0;
  const num = an + as_;
  const den = num + inN + inS;
  if (den === 0) { activePctEl.textContent = "0%"; return; }
  activePctEl.textContent = `${Math.round((num / den) * 100)}%`;
}

function renderRouteCard(routeData) {
  if (!routeData || !routeData.exists) {
    routeCard.classList.add("no-route");
    routeLengthEl.textContent = "No viable route";
    routePctPermEl.textContent = "—";
    routePctSeasEl.textContent = "—";
    routeBarPerm.style.flex = "0 0 0%";
    routeBarSeas.style.flex = "0 0 0%";
    routeReadoutValueEl.textContent = "closed";
    return;
  }
  routeCard.classList.remove("no-route");
  const s = routeData.stats;
  routeLengthEl.textContent = `${s.length_km.toFixed(1)} km`;
  const pp = Math.round(s.percent_permanent * 100);
  const ps = Math.round(s.percent_seasonal * 100);
  routePctPermEl.textContent = pp;
  routePctSeasEl.textContent = ps;
  routeBarPerm.style.flex = `${pp} 0 0%`;
  routeBarSeas.style.flex = `${ps} 0 0%`;
  routeReadoutValueEl.textContent = `${s.length_km.toFixed(1)} km`;
}

function fadeAdvisoryUpdate(text) {
  routeCard.classList.add("is-fading");
  setTimeout(() => {
    advisoryEl.textContent = text;
    routeCard.classList.remove("is-fading");
  }, 120);
}

// Fetch / wire --------------------------------------------------------------

let inflight = null;

async function fetchInit() {
  try {
    const res = await fetch("/api/init");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.overlay_bounds && Array.isArray(data.overlay_bounds)) {
      overlayBounds = data.overlay_bounds;
    }
    // NOTE: do NOT setView from /api/init. The map is already centered on
    // the island by L.map(...).setView at module load, and a real user's
    // geolocation may fire before or after this fetch resolves. Calling
    // setView here would race against the geolocation callback and (when
    // it lands second) snap the map back to the island.
    return data;
  } catch (err) {
    console.warn("init failed:", err);
    overlayBounds = [[-3.839, -60.689], [-2.839, -60.0]];
  }
}

async function fetchRoutes(month) {
  if (inflight) inflight.abort();
  const controller = new AbortController();
  inflight = controller;
  try {
    const res = await fetch(`/route?month=${month}`, { signal: controller.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    fadeAdvisoryUpdate(data.advisory ?? "(no advisory)");
    renderInvisibleGeoJson(data.features);
    renderClaudeInput(data.claude_input?.values);
    renderActivePct(data.stats);
    renderRouteCard(data.route);
    renderRoute(data.route);
    return data;
  } catch (err) {
    if (err.name !== "AbortError") {
      fadeAdvisoryUpdate(`Error: ${err.message}`);
    }
  } finally {
    if (inflight === controller) inflight = null;
  }
}

let debounceTimer = null;
function onSliderChange() {
  const month = parseInt(slider.value, 10);
  setMonthLabel(month);
  setRasterMonth(month);
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => fetchRoutes(month), 200);
}

whyDismiss.addEventListener("click", () => {
  whyCard.classList.add("dismissed");
});

document.getElementById("recenter").addEventListener("click", () => {
  map.setView([ISLAND.lat, ISLAND.lon], 11);
});

slider.addEventListener("input", onSliderChange);

// Theme toggle — shares localStorage.theme with the landing site so a visitor
// who picks dark mode there stays in dark when they hit the demo.
const themeToggle = document.getElementById("theme-toggle");
if (themeToggle) {
  const syncPressed = () => {
    themeToggle.setAttribute(
      "aria-pressed",
      document.documentElement.classList.contains("dark") ? "true" : "false"
    );
  };
  syncPressed();
  themeToggle.addEventListener("click", () => {
    const isDark = document.documentElement.classList.toggle("dark");
    try { localStorage.setItem("theme", isDark ? "dark" : "light"); } catch (e) {}
    syncPressed();
  });
}

(async () => {
  await fetchInit();
  const month = parseInt(slider.value, 10);
  setMonthLabel(month);
  setRasterMonth(month);
  fetchRoutes(month);
})();
