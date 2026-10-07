"""Walkable-floor geometry: occupancy grid, A* paths, display exposure and heat footprints."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
from scipy import ndimage

from .store import STORE, Rect, StoreSpec

CELL = 0.5  # metres per grid cell
SAMPLE_STEP = 0.25  # metres between densified path samples
_SQRT2 = math.sqrt(2.0)


def rect_distance(xs: np.ndarray, ys: np.ndarray, rect: Rect) -> np.ndarray:
    """Euclidean distance from points to an axis-aligned rectangle (0 inside)."""
    x0, y0, x1, y1 = rect
    dx = np.maximum(np.maximum(x0 - xs, 0.0), xs - x1)
    dy = np.maximum(np.maximum(y0 - ys, 0.0), ys - y1)
    return np.hypot(dx, dy)


def in_rect(xs: np.ndarray, ys: np.ndarray, rect: Rect) -> np.ndarray:
    x0, y0, x1, y1 = rect
    return (xs >= x0) & (xs <= x1) & (ys >= y0) & (ys <= y1)


class Grid:
    """Occupancy grid. Obstacles are inflated by one cell so paths keep ~0.5 m clearance."""

    def __init__(self, store: StoreSpec, extra_obstacles: list[Rect] | tuple[Rect, ...] = ()):
        self.store = store
        self.nx = int(round(store.width / CELL))
        self.ny = int(round(store.height / CELL))
        xs = (np.arange(self.nx) + 0.5) * CELL
        ys = (np.arange(self.ny) + 0.5) * CELL
        blocked = np.zeros((self.ny, self.nx), dtype=bool)
        for x0, y0, x1, y1 in [f.rect for f in store.fixtures] + list(extra_obstacles):
            rows = (ys > y0) & (ys < y1)
            cols = (xs > x0) & (xs < x1)
            blocked[np.ix_(rows, cols)] = True
        self.blocked = blocked
        self.free = ~ndimage.binary_dilation(blocked, structure=np.ones((3, 3), dtype=bool), iterations=1)

    # ---------------------------------------------------------------- helpers
    def cell_of(self, x: float, y: float) -> tuple[int, int]:
        col = min(max(int(x / CELL), 0), self.nx - 1)
        row = min(max(int(y / CELL), 0), self.ny - 1)
        return row, col

    def center(self, row: int, col: int) -> tuple[float, float]:
        return ((col + 0.5) * CELL, (row + 0.5) * CELL)

    def is_free_point(self, x: float, y: float) -> bool:
        if not (0.0 <= x < self.store.width and 0.0 <= y < self.store.height):
            return False
        r, c = self.cell_of(x, y)
        return bool(self.free[r, c])

    def line_free(self, p: tuple[float, float], q: tuple[float, float]) -> bool:
        dist = math.hypot(q[0] - p[0], q[1] - p[1])
        n = max(2, int(math.ceil(dist / 0.1)) + 1)
        xs = np.linspace(p[0], q[0], n)
        ys = np.linspace(p[1], q[1], n)
        cols = np.clip((xs / CELL).astype(int), 0, self.nx - 1)
        rows = np.clip((ys / CELL).astype(int), 0, self.ny - 1)
        return bool(self.free[rows, cols].all())

    # ---------------------------------------------------------------- A*
    def astar(self, start: tuple[float, float], goal: tuple[float, float]) -> list[tuple[float, float]] | None:
        """Shortest 8-connected path (no corner cutting), smoothed by string pulling."""
        sr, sc = self.cell_of(*start)
        gr, gc = self.cell_of(*goal)
        if not self.free[sr, sc] or not self.free[gr, gc]:
            return None
        ny, nx = self.ny, self.nx
        free = self.free
        g = np.full((ny, nx), np.inf)
        came: dict[tuple[int, int], tuple[int, int]] = {}
        g[sr, sc] = 0.0

        def h(r: int, c: int) -> float:
            dr, dc = abs(r - gr), abs(c - gc)
            return (dr + dc) + (_SQRT2 - 2.0) * min(dr, dc)

        heap: list[tuple[float, float, int, int]] = [(h(sr, sc), 0.0, sr, sc)]
        closed = np.zeros((ny, nx), dtype=bool)
        moves = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
                 (-1, -1, _SQRT2), (-1, 1, _SQRT2), (1, -1, _SQRT2), (1, 1, _SQRT2)]
        found = False
        while heap:
            _, gcur, r, c = heapq.heappop(heap)
            if closed[r, c]:
                continue
            closed[r, c] = True
            if r == gr and c == gc:
                found = True
                break
            for dr, dc, cost in moves:
                nr, nc = r + dr, c + dc
                if nr < 0 or nr >= ny or nc < 0 or nc >= nx or not free[nr, nc] or closed[nr, nc]:
                    continue
                if dr != 0 and dc != 0 and not (free[r + dr, c] and free[r, c + dc]):
                    continue
                ng = gcur + cost
                if ng < g[nr, nc]:
                    g[nr, nc] = ng
                    came[(nr, nc)] = (r, c)
                    heapq.heappush(heap, (ng + h(nr, nc), ng, nr, nc))
        if not found:
            return None
        cells = [(gr, gc)]
        while cells[-1] != (sr, sc):
            cells.append(came[cells[-1]])
        cells.reverse()
        pts = [start] + [self.center(r, c) for r, c in cells[1:-1]] + [goal]
        return self._string_pull(pts)

    def _string_pull(self, pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
        out = [pts[0]]
        i = 0
        last = len(pts) - 1
        while i < last:
            j = last
            while j > i + 1 and not self.line_free(pts[i], pts[j]):
                j -= 1
            out.append(pts[j])
            i = j
        return out


@dataclass
class Leg:
    """A walking leg between two anchors, with everything the engine needs precomputed."""

    key: tuple[str, str]
    vertices: np.ndarray  # (k, 2)
    samples: np.ndarray  # (n, 2), every SAMPLE_STEP metres
    arc: np.ndarray  # (n,) arc length at each sample
    length: float
    display_hits: list[tuple[float, str]]  # (fraction along leg, slot id), ordered by fraction
    heat_idx: np.ndarray  # flat grid-cell indices
    heat_m: np.ndarray  # metres walked inside each cell
    zones_passed: list[str] = field(default_factory=list)


def _densify(vertices: list[tuple[float, float]]) -> tuple[np.ndarray, np.ndarray]:
    pts = [np.asarray(vertices[0], dtype=float)]
    arcs = [0.0]
    total = 0.0
    for a, b in zip(vertices[:-1], vertices[1:]):
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        seg = float(np.hypot(*(b - a)))
        if seg <= 1e-9:
            continue
        n = max(1, int(math.ceil(seg / SAMPLE_STEP)))
        for k in range(1, n + 1):
            t = k / n
            pts.append(a + (b - a) * t)
            arcs.append(total + seg * t)
        total += seg
    return np.vstack(pts), np.asarray(arcs)


class PathNetwork:
    """All anchor-to-anchor legs for one obstacle configuration."""

    def __init__(self, store: StoreSpec, occupied_free_standing: tuple[str, ...] = ()):
        self.store = store
        extra = [store.display(s).rect for s in occupied_free_standing]
        self.grid = Grid(store, extra)
        self.anchors = store.anchors()
        for name, (x, y) in self.anchors.items():
            if not self.grid.is_free_point(x, y):
                raise ValueError(f"Anchor {name} at ({x}, {y}) is not on walkable floor")
        self.zone_rects = store.zone_rects()
        self.legs: dict[tuple[str, str], Leg] = {}
        names = list(self.anchors)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                verts = self.grid.astar(self.anchors[a], self.anchors[b])
                if verts is None:
                    raise ValueError(f"No walkable path between {a} and {b}")
                self.legs[(a, b)] = self._make_leg((a, b), verts)
                self.legs[(b, a)] = self._make_leg((b, a), list(reversed(verts)))

    def _make_leg(self, key: tuple[str, str], verts: list[tuple[float, float]]) -> Leg:
        samples, arc = _densify(verts)
        length = float(arc[-1])
        xs, ys = samples[:, 0], samples[:, 1]
        hits: list[tuple[float, str]] = []
        radius = self.store.display_exposure_radius_m
        for d in self.store.displays:
            if d.at_checkout:
                continue  # only seen while queueing, handled by the checkout model
            near = np.nonzero(rect_distance(xs, ys, d.rect) <= radius)[0]
            if near.size:
                frac = float(arc[near[0]] / length) if length > 0 else 0.0
                hits.append((frac, d.id))
        hits.sort()
        cols = np.clip((xs / CELL).astype(int), 0, self.grid.nx - 1)
        rows = np.clip((ys / CELL).astype(int), 0, self.grid.ny - 1)
        flat = rows * self.grid.nx + cols
        # Each sample stands for the SAMPLE_STEP metres walked up to it.
        weights = np.full(flat.shape, SAMPLE_STEP)
        weights[0] = 0.0
        uniq, inv = np.unique(flat, return_inverse=True)
        heat_m = np.bincount(inv, weights=weights).astype(float)
        first_entry: list[tuple[int, str]] = []
        for zid, rect in self.zone_rects.items():
            inside = np.nonzero(in_rect(xs, ys, rect))[0]
            if inside.size:
                first_entry.append((int(inside[0]), zid))
        zones_passed = [zid for _, zid in sorted(first_entry)]
        return Leg(key, np.asarray(verts), samples, arc, length, hits, uniq, heat_m, zones_passed)

    def leg(self, a: str, b: str) -> Leg:
        return self.legs[(a, b)]

    def distance(self, a: str, b: str) -> float:
        return 0.0 if a == b else self.legs[(a, b)].length


def zone_heat_kernel(store: StoreSpec, grid: Grid, rect: Rect, anchor: tuple[float, float], spread: float = 1.2):
    """Where dwell time lands on the heatmap: free cells in the zone, weighted towards the anchor."""
    xs = (np.arange(grid.nx) + 0.5) * CELL
    ys = (np.arange(grid.ny) + 0.5) * CELL
    gx, gy = np.meshgrid(xs, ys)
    mask = in_rect(gx, gy, rect) & ~grid.blocked
    w = np.exp(-((gx - anchor[0]) ** 2 + (gy - anchor[1]) ** 2) / (2 * spread**2)) * mask
    total = w.sum()
    if total <= 0:
        r, c = grid.cell_of(*anchor)
        w = np.zeros_like(w)
        w[r, c] = 1.0
        total = 1.0
    flat = (w / total).ravel()
    idx = np.nonzero(flat)[0]
    return idx, flat[idx]


@lru_cache(maxsize=32)
def path_network(occupied_free_standing: tuple[str, ...] = ()) -> PathNetwork:
    return PathNetwork(STORE, occupied_free_standing)
