"""A* shortest-path routing over the per-month classified raster.

Pure numpy + heapq. No new dependencies.

Public API:
  compute_route(class_arr, transform, start_latlon, end_latlon, ...) -> RouteResult

Algorithm:
  1. Block-majority downsample the class array (256x172-ish for our crop).
  2. Build a cost grid (permanent=1.0, seasonal-active=1.5, else inf).
  3. Snap start/end lat/lon to the nearest traversable cell within a small
     radius. If neither finds a cell, return RouteResult(exists=False, ...).
  4. A* with 8-connectivity, Euclidean heuristic, sqrt(2) diagonal cost.
  5. Traceback parents -> pixel path.
  6. Convert pixels -> lat/lon via the downsampled affine transform.
  7. Split into same-class segments. Compute haversine distances per segment.
  8. Douglas-Peucker simplify per segment (preserves class transitions).
"""
from __future__ import annotations

import heapq
import logging
import math
from dataclasses import dataclass

import numpy as np
from rasterio.transform import Affine

import jrc_data

log = logging.getLogger("routing")

# Default A* cost per traversable class. Anything not in the table is blocked.
DEFAULT_COST_TABLE: dict[int, float] = {
    jrc_data.CLS_PERMANENT:       1.0,
    jrc_data.CLS_SEASONAL_ACTIVE: 1.5,
}

# String labels emitted in the API response for the frontend's per-segment styling.
CLASS_LABELS: dict[int, str] = {
    jrc_data.CLS_PERMANENT:       "permanent",
    jrc_data.CLS_SEASONAL_ACTIVE: "seasonal-active",
}

EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class RouteResult:
    exists: bool
    coords: list[tuple[float, float]]            # (lat, lon)
    segments: list[dict]                          # [{class, coordinates [[lon,lat]...], length_km}, ...]
    length_km: float
    permanent_km: float
    seasonal_km: float
    longest_seasonal_segment_km: float
    start_latlon: tuple[float, float]
    end_latlon: tuple[float, float]
    n_nodes_explored: int = 0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a)) / 1000.0


def _block_majority(arr: np.ndarray, k: int, n_classes: int = 5) -> np.ndarray:
    """Downsample by factor k via per-block majority vote.

    Mirrors vectorize.block_majority but is duplicated here intentionally so
    routing has no import-time dependency on the GeoJSON pipeline.
    """
    if k <= 1:
        return arr
    h, w = arr.shape
    ht = (h // k) * k
    wt = (w // k) * k
    trimmed = arr[:ht, :wt]
    h2, w2 = ht // k, wt // k
    blocks = trimmed.reshape(h2, k, w2, k).transpose(0, 2, 1, 3).reshape(h2, w2, k * k)
    counts = np.zeros((h2, w2, n_classes), dtype=np.int32)
    for c in range(n_classes):
        counts[:, :, c] = (blocks == c).sum(axis=2)
    return counts.argmax(axis=2).astype(arr.dtype)


def _scaled_coeffs(transform: Affine, k: int) -> tuple[float, float, float, float, float, float]:
    """Return the (a, b, c, d, e, f) coefficients of the downsampled affine.

    Forward map: (col, row) -> (x, y) = (a*col + b*row + c, d*col + e*row + f).
    For JRC tiles a, e are pixel sizes in degrees; b, d are zero (axis-aligned);
    c, f are the top-left corner. Scaling rows/cols by k multiplies a, b, d, e.
    """
    a, b, c = float(transform.a), float(transform.b), float(transform.c)
    d, e, f = float(transform.d), float(transform.e), float(transform.f)
    return a * k, b * k, c, d * k, e * k, f


def _invert_affine(a: float, b: float, c: float, d: float, e: float, f: float) -> tuple[float, float, float, float, float, float]:
    """Invert a 2x3 affine. (col, row) = inv * (x - c, y - f) effectively."""
    det = a * e - b * d
    if det == 0:
        raise ValueError("singular affine; cannot invert")
    ia = e / det
    ib = -b / det
    id_ = -d / det
    ie = a / det
    ic = -(ia * c + ib * f)
    if_ = -(id_ * c + ie * f)
    return ia, ib, ic, id_, ie, if_


def _latlon_to_rc(lat: float, lon: float, transform: Affine, k: int, shape: tuple[int, int]) -> tuple[int, int]:
    """Map (lat, lon) to (row, col) in the downsampled grid. Clamped to shape."""
    a, b, c, d, e, f = _scaled_coeffs(transform, k)
    ia, ib, ic, id_, ie, if_ = _invert_affine(a, b, c, d, e, f)
    # Forward: x=lon, y=lat. inv * (lon, lat) = (col, row).
    col_f = ia * lon + ib * lat + ic
    row_f = id_ * lon + ie * lat + if_
    r = int(round(row_f))
    col = int(round(col_f))
    h, w = shape
    return max(0, min(h - 1, r)), max(0, min(w - 1, col))


def _rc_to_latlon(r: int, c: int, transform: Affine, k: int) -> tuple[float, float]:
    """Map a downsampled (row, col) cell center back to (lat, lon)."""
    a, b, ca, d, e, f = _scaled_coeffs(transform, k)
    # forward: (col + 0.5, row + 0.5) -> (lon, lat)
    lon = a * (c + 0.5) + b * (r + 0.5) + ca
    lat = d * (c + 0.5) + e * (r + 0.5) + f
    return float(lat), float(lon)


def _component_mask_at(cost: np.ndarray, anchor_rc: tuple[int, int], search_radius: int = 30) -> np.ndarray:
    """Return the boolean mask of the connected component containing the cell
    closest to `anchor_rc` (within `search_radius`).

    If the anchor cell is itself non-traversable, walk outward to the nearest
    finite-cost cell within the search radius, then return its component.

    Uses 4-connectivity to match the worst-case A* connectivity.
    """
    from collections import deque
    finite = np.isfinite(cost)
    h, w = cost.shape
    ar, ac = anchor_rc

    # Find a seed: the closest finite cell to the anchor within search_radius.
    seed: tuple[int, int] | None = None
    if 0 <= ar < h and 0 <= ac < w and finite[ar, ac]:
        seed = (ar, ac)
    else:
        for radius in range(1, search_radius + 1):
            found_seed = False
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if max(abs(dr), abs(dc)) != radius:
                        continue
                    r, c = ar + dr, ac + dc
                    if 0 <= r < h and 0 <= c < w and finite[r, c]:
                        seed = (r, c)
                        found_seed = True
                        break
                if found_seed:
                    break
            if found_seed:
                break

    mask = np.zeros((h, w), dtype=bool)
    if seed is None:
        return mask

    # BFS the seed's component.
    q = deque([seed])
    mask[seed] = True
    while q:
        r, c = q.popleft()
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and finite[nr, nc] and not mask[nr, nc]:
                mask[nr, nc] = True
                q.append((nr, nc))
    return mask


def _snap_to_traversable(
    cost: np.ndarray,
    r0: int,
    c0: int,
    max_radius: int = 60,
    component_mask: np.ndarray | None = None,
) -> tuple[int, int] | None:
    """Ring search outward from (r0, c0) for the nearest traversable cell.

    If `component_mask` is provided, only cells in that mask are accepted —
    use this to constrain the snap to the largest connected water component
    so A* is guaranteed a path between two snapped waypoints.

    Default radius is 60 cells (≈30 km at our 16x downsample) — generous
    enough that a waypoint dropped in jungle still resolves to the main channel.
    """
    def ok(r: int, c: int) -> bool:
        if not (0 <= r < cost.shape[0] and 0 <= c < cost.shape[1]):
            return False
        if not math.isfinite(cost[r, c]):
            return False
        if component_mask is not None and not component_mask[r, c]:
            return False
        return True

    if ok(r0, c0):
        return (r0, c0)
    for radius in range(1, max_radius + 1):
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if max(abs(dr), abs(dc)) != radius:
                    continue
                r, c = r0 + dr, c0 + dc
                if ok(r, c):
                    return (r, c)
    return None


# 8-connectivity: (dr, dc, step_multiplier). Diagonals cost sqrt(2)x.
_NEIGHBOURS: list[tuple[int, int, float]] = [
    (-1, -1, math.sqrt(2)), (-1, 0, 1.0), (-1, 1, math.sqrt(2)),
    ( 0, -1, 1.0),                         ( 0, 1, 1.0),
    ( 1, -1, math.sqrt(2)), ( 1, 0, 1.0), ( 1, 1, math.sqrt(2)),
]


def _astar(cost: np.ndarray, start: tuple[int, int], goal: tuple[int, int]) -> tuple[list[tuple[int, int]], int] | None:
    """Run A* on the cost grid. Returns (path, n_explored) or None if no path.

    Path is a list of (row, col) including start and goal.
    """
    h, w = cost.shape
    sr, sc = start
    gr, gc = goal
    if not math.isfinite(cost[sr, sc]) or not math.isfinite(cost[gr, gc]):
        return None

    # g_score[i] = best known cost to reach cell i. -1 means unvisited.
    g = np.full(cost.shape, np.inf, dtype=np.float64)
    g[sr, sc] = 0.0
    parent = -np.ones(h * w, dtype=np.int64)

    def heuristic(r: int, c: int) -> float:
        # Euclidean in cell units; admissible because the cheapest cell is 1.0.
        return math.hypot(r - gr, c - gc)

    open_heap: list[tuple[float, float, int, int]] = []
    # tie-break by smaller h to prefer straighter paths (smoothes meandering)
    heapq.heappush(open_heap, (heuristic(sr, sc), heuristic(sr, sc), sr, sc))

    n_explored = 0
    while open_heap:
        # Heap entries: (f, h_for_tiebreak, row, col). f and h_for_tiebreak
        # are not needed past the pop -- only the cell coordinates.
        _, _, r, c = heapq.heappop(open_heap)
        if (r, c) == goal:
            # Traceback. Cast through int() because parent stores numpy int64.
            path: list[tuple[int, int]] = []
            idx: int = r * w + c
            while idx != -1:
                pr, pc = divmod(idx, w)
                path.append((int(pr), int(pc)))
                if (int(pr), int(pc)) == start:
                    break
                idx = int(parent[idx])
            path.reverse()
            return path, n_explored

        n_explored += 1
        cur_g = g[r, c]

        for dr, dc, step in _NEIGHBOURS:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < h and 0 <= nc < w):
                continue
            ncost = cost[nr, nc]
            if not math.isfinite(ncost):
                continue
            tentative = cur_g + step * ncost
            if tentative < g[nr, nc]:
                g[nr, nc] = tentative
                parent[nr * w + nc] = r * w + c
                heapq.heappush(open_heap, (tentative + heuristic(nr, nc), heuristic(nr, nc), nr, nc))

    return None  # unreachable


def _chaikin_smooth(points: list[tuple[float, float]], iterations: int = 2) -> list[tuple[float, float]]:
    """Chaikin's corner-rounding algorithm — replaces each interior vertex with
    two new vertices at 1/4 and 3/4 along its incident edges, rounding the
    corner. Endpoints are preserved.

    One iteration removes 90-degree corners; two gives near-circular bends.
    Vertex count grows as ~2N per iteration; for our ≤80-vertex segments two
    iterations is fine (~320 vertices per segment, well under any payload limit).
    """
    if iterations <= 0 or len(points) < 3:
        return points[:]
    pts = points[:]
    for _ in range(iterations):
        smoothed: list[tuple[float, float]] = [pts[0]]
        for i in range(len(pts) - 1):
            p0 = pts[i]
            p1 = pts[i + 1]
            q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            smoothed.append(q)
            smoothed.append(r)
        smoothed.append(pts[-1])
        pts = smoothed
    return pts


def _douglas_peucker(points: list[tuple[float, float]], tolerance_m: float) -> list[tuple[float, float]]:
    """Simplify a (lat, lon) polyline. Distances measured in meters via haversine."""
    if len(points) < 3:
        return points[:]

    def perp_dist_m(p, a, b) -> float:
        # Project p onto great-circle a->b in approximate flat-earth meters.
        # Good enough for ~10 km island scale.
        # Convert to local meters via small-angle haversine.
        def to_m(p1, p2):
            return _haversine_km(*p1, *p2) * 1000.0
        ab = to_m(a, b)
        if ab == 0:
            return to_m(p, a)
        ap = to_m(a, p)
        bp = to_m(b, p)
        # Heron's formula for triangle area; height from base ab is the perp distance.
        s = (ab + ap + bp) / 2.0
        area2 = max(0.0, s * (s - ab) * (s - ap) * (s - bp))
        return 2.0 * math.sqrt(area2) / ab

    def simplify(start: int, end: int, keep: list[bool]) -> None:
        if end - start < 2:
            return
        max_d = -1.0
        max_i = -1
        a, b = points[start], points[end]
        for i in range(start + 1, end):
            d = perp_dist_m(points[i], a, b)
            if d > max_d:
                max_d = d
                max_i = i
        if max_d > tolerance_m and max_i != -1:
            keep[max_i] = True
            simplify(start, max_i, keep)
            simplify(max_i, end, keep)

    keep = [False] * len(points)
    keep[0] = True
    keep[-1] = True
    simplify(0, len(points) - 1, keep)
    return [p for p, k in zip(points, keep) if k]


def _build_segments(
    pixel_path: list[tuple[int, int]],
    class_at: np.ndarray,
    transform: Affine,
    k: int,
    simplify_tolerance_m: float,
) -> list[dict]:
    """Split the pixel path at every class transition, return segment list with km."""
    if not pixel_path:
        return []

    segments: list[dict] = []
    cur_class = int(class_at[pixel_path[0]])
    cur_pixels: list[tuple[int, int]] = [pixel_path[0]]

    def flush():
        nonlocal cur_pixels
        # Pixel-step path -> lat/lon, then DP-simplify (keeps endpoints) ->
        # one pass of Chaikin smoothing to round 90-degree corners without
        # pulling the line meaningfully off its A* cells. (Two iterations
        # cut corners hard enough that on narrow channels the line could
        # drift onto adjacent land in the satellite basemap.) Length is
        # measured on the FINAL smoothed polyline so what the UI shows
        # matches what the stats say.
        latlons = [_rc_to_latlon(r, c, transform, k) for r, c in cur_pixels]
        simplified = _douglas_peucker(latlons, simplify_tolerance_m)
        smoothed = _chaikin_smooth(simplified, iterations=1)
        # GeoJSON wants [lon, lat]
        coords = [[lon, lat] for lat, lon in smoothed]
        length_km = sum(
            _haversine_km(smoothed[i][0], smoothed[i][1], smoothed[i + 1][0], smoothed[i + 1][1])
            for i in range(len(smoothed) - 1)
        )
        segments.append({
            "class": CLASS_LABELS.get(cur_class, "unknown"),
            "coordinates": coords,
            "length_km": round(length_km, 3),
        })
        cur_pixels = []

    for px in pixel_path[1:]:
        cls = int(class_at[px])
        if cls != cur_class:
            # Boundary cell goes to BOTH segments so the polylines visually connect.
            cur_pixels.append(px)
            flush()
            cur_class = cls
            cur_pixels = [px]
        else:
            cur_pixels.append(px)
    if cur_pixels:
        flush()
    return segments


def compute_route(
    class_arr: np.ndarray,
    transform: Affine,
    start_latlon: tuple[float, float],
    end_latlon: tuple[float, float],
    *,
    anchor_latlon: tuple[float, float] | None = None,
    downsample: int = 8,
    cost_table: dict[int, float] | None = None,
    simplify_tolerance_m: float = 80.0,
) -> RouteResult:
    """Compute the A* route for one month's classification.

    If `anchor_latlon` is provided, both waypoints are snapped into the
    connected component containing the anchor cell. This is how we keep the
    route 'around the island' even when the largest connected water region
    in the crop is somewhere else (e.g. a distant Rio Negro stretch).
    """
    cost_table = cost_table or DEFAULT_COST_TABLE
    k = max(1, int(downsample))

    reduced = _block_majority(class_arr, k)
    cost = np.full(reduced.shape, np.inf, dtype=np.float64)
    for cls_value, c in cost_table.items():
        cost[reduced == cls_value] = float(c)

    # Pick the target connected component. With an anchor, use the component
    # containing the anchor cell; without, fall back to no restriction.
    if anchor_latlon is not None:
        ar, ac = _latlon_to_rc(anchor_latlon[0], anchor_latlon[1], transform, k, reduced.shape)
        target_component: np.ndarray | None = _component_mask_at(cost, (ar, ac))
        if target_component is not None and not target_component.any():
            target_component = None
    else:
        target_component = None

    sr, sc = _latlon_to_rc(start_latlon[0], start_latlon[1], transform, k, reduced.shape)
    gr, gc = _latlon_to_rc(end_latlon[0], end_latlon[1], transform, k, reduced.shape)
    snapped_start = _snap_to_traversable(cost, sr, sc, component_mask=target_component)
    snapped_goal = _snap_to_traversable(cost, gr, gc, component_mask=target_component)

    if snapped_start is None or snapped_goal is None:
        log.warning(f"  waypoint snap failed: start={snapped_start} goal={snapped_goal}")
        return RouteResult(
            exists=False, coords=[], segments=[],
            length_km=0.0, permanent_km=0.0, seasonal_km=0.0, longest_seasonal_segment_km=0.0,
            start_latlon=start_latlon, end_latlon=end_latlon, n_nodes_explored=0,
        )

    result = _astar(cost, snapped_start, snapped_goal)
    if result is None:
        return RouteResult(
            exists=False, coords=[], segments=[],
            length_km=0.0, permanent_km=0.0, seasonal_km=0.0, longest_seasonal_segment_km=0.0,
            start_latlon=start_latlon, end_latlon=end_latlon, n_nodes_explored=0,
        )

    pixel_path, n_explored = result
    segments = _build_segments(pixel_path, reduced, transform, k, simplify_tolerance_m)

    perm_km = sum(s["length_km"] for s in segments if s["class"] == "permanent")
    seas_km = sum(s["length_km"] for s in segments if s["class"] == "seasonal-active")
    total_km = perm_km + seas_km
    longest_seasonal = max(
        (s["length_km"] for s in segments if s["class"] == "seasonal-active"),
        default=0.0,
    )

    # Flat list of (lat, lon) for the geometry. Use simplified per-segment endpoints.
    coords: list[tuple[float, float]] = []
    for seg in segments:
        for lon, lat in seg["coordinates"]:
            if not coords or coords[-1] != (lat, lon):
                coords.append((lat, lon))

    return RouteResult(
        exists=True,
        coords=coords,
        segments=segments,
        length_km=round(total_km, 3),
        permanent_km=round(perm_km, 3),
        seasonal_km=round(seas_km, 3),
        longest_seasonal_segment_km=round(longest_seasonal, 3),
        start_latlon=start_latlon,
        end_latlon=end_latlon,
        n_nodes_explored=n_explored,
    )
