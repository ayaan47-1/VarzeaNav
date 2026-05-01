// Amazon River Navigation — frontend
// Step 2: Leaflet init, geolocation w/ Manaus fallback, slider input handler.
// Step 3 will add fetchRoutes() and wire it to the slider.

const ISLAND = { lat: -3.339, lon: -60.189 };
const TILE_BOUNDS = { W: -70, S: -10, E: -60, N: 0 }; // 70W_0N JRC tile

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const map = L.map("map", { zoomControl: true }).setView([ISLAND.lat, ISLAND.lon], 11);

L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  {
    attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics",
    maxZoom: 18,
  }
).addTo(map);

// Marker so people can see the validated island regardless of pan/zoom.
L.marker([ISLAND.lat, ISLAND.lon])
  .addTo(map)
  .bindPopup("Validated island (-3.339, -60.189)");

// Geolocation: try to center on user; fall back to Manaus if denied or
// outside the JRC tile coverage.
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
      // else: silently keep Manaus default (user is outside the dataset)
    },
    () => {
      // Permission denied or error — Manaus default already set.
    },
    { timeout: 5000, maximumAge: 60000 }
  );
}

// Slider — month label updates immediately, advisory fetched (debounced).
const slider = document.getElementById("month-slider");
const monthLabel = document.getElementById("month-label");
const advisoryEl = document.getElementById("advisory");

function setMonthLabel(month) {
  monthLabel.textContent = `Month: ${MONTH_NAMES[month - 1]}`;
}

// GeoJSON layer + per-class style.
const CLASS_STYLE = {
  "permanent":         { color: "#0d47a1", weight: 0, fillColor: "#0d47a1", fillOpacity: 0.85 },
  "seasonal-active":   { color: "#4fc3f7", weight: 0, fillColor: "#4fc3f7", fillOpacity: 0.70 },
  "seasonal-inactive": { color: "#888888", weight: 0, fillColor: "#888888", fillOpacity: 0.35 },
};
let waterLayer = null;

function renderFeatures(features) {
  if (waterLayer) {
    map.removeLayer(waterLayer);
    waterLayer = null;
  }
  if (!features || features.length === 0) return;
  waterLayer = L.geoJSON(features, {
    style: (f) => CLASS_STYLE[f.properties.class] || { weight: 0, fillOpacity: 0 },
    interactive: false,  // overlays should not eat map clicks
  }).addTo(map);
}

let inflight = null;
async function fetchRoutes(month) {
  // Cancel any in-flight request — only the latest month matters.
  if (inflight) inflight.abort();
  const controller = new AbortController();
  inflight = controller;
  advisoryEl.textContent = "Loading…";
  try {
    const res = await fetch(`/route?month=${month}`, { signal: controller.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    advisoryEl.textContent = data.advisory ?? "(no advisory)";
    renderFeatures(data.features);
    return data;
  } catch (err) {
    if (err.name !== "AbortError") {
      advisoryEl.textContent = `Error: ${err.message}`;
    }
  } finally {
    if (inflight === controller) inflight = null;
  }
}

// Debounce so a fast drag doesn't hammer the backend.
let debounceTimer = null;
function onSliderChange() {
  const month = parseInt(slider.value, 10);
  setMonthLabel(month);
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => fetchRoutes(month), 200);
}

setMonthLabel(parseInt(slider.value, 10));
slider.addEventListener("input", onSliderChange);
fetchRoutes(parseInt(slider.value, 10)); // initial load

// Recenter button
document.getElementById("recenter").addEventListener("click", () => {
  map.setView([ISLAND.lat, ISLAND.lon], 11);
});
