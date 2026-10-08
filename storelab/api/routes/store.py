"""Store endpoints."""

from __future__ import annotations

import dataclasses
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from ...layout import layout_to_json
from ...store import CATEGORIES, CATEGORY_LABELS
from ..cache import cached_response
from ..dependencies import WorldDep
from ..responses import json_response

router = APIRouter(prefix="/api", tags=["store"])


def _store_geometry(w: WorldDep) -> Response:
    s = w.store
    rect = lambda r: {"x0": r[0], "y0": r[1], "x1": r[2], "y1": r[3]}  # noqa: E731
    return json_response(
        {
            "id": s.store_id,
            "name": s.name,
            "region": s.region,
            "currency": s.currency,
            "timezone": s.timezone,
            "width": s.width,
            "height": s.height,
            "cell_m": 0.5,
            "fixtures": [
                {
                    "id": f.id,
                    "label": f.label,
                    "kind": f.kind,
                    "refrigerated": f.refrigerated,
                    **rect(f.rect),
                }
                for f in s.fixtures
            ],
            "aisles": [
                {
                    "id": a.id,
                    "label": a.label,
                    "refrigerated": a.refrigerated,
                    "anchor": a.anchor,
                    **rect(a.rect),
                }
                for a in s.aisles
            ],
            "displays": [
                {
                    "id": d.id,
                    "label": d.label,
                    "kind": d.kind,
                    "add_cost": d.add_cost,
                    "free_standing": d.free_standing,
                    "clear_width_m": d.clear_width_m,
                    "restricted": d.restricted,
                    "restricted_reason": d.restricted_reason,
                    "at_checkout": d.at_checkout,
                    **rect(d.rect),
                }
                for d in s.displays
            ],
            "areas": {
                "entrance": rect(s.entrance_rect),
                "checkout": rect(s.checkout_rect),
                "exit": rect(s.exit_rect),
                "entrance_door": rect(s.entrance_door),
                "exit_door": rect(s.exit_door),
            },
            "categories": [{"id": c, "label": CATEGORY_LABELS[c]} for c in CATEGORIES],
            "baseline_layout": layout_to_json(s, w.baseline_layout),
            "products": [dataclasses.asdict(p) for p in s.products],
            "network": [dataclasses.asdict(n) for n in s.network],
            "costs": {
                "move_display": s.move_display_cost,
                "remove_display": s.remove_display_cost,
                "swap_categories": s.swap_categories_cost,
            },
            "constraints": {
                "min_aisle_width_m": s.min_aisle_width_m,
                "max_changes": s.max_changes_per_experiment,
                "refrigerated_fixed": True,
                "peak_window": list(s.peak_window),
            },
        }
    )


def _analytics(w: WorldDep) -> Response:
    return json_response(
        {
            "summary": w.analytics.summary,
            "heatmap": np.round(w.analytics.heatmap, 1),
            "heatmap_units": "shopper-seconds per 0.5 m cell per day (observed)",
            "model": w.fit_report,
            "calibration": w.calibration,
        }
    )


def _journey_sample(
    w: WorldDep,
    day: int = 0,
    start_hour: float = 17.0,
    minutes: int = 40,
    limit: int = 80,
) -> Response:
    """Observed anonymous trajectories (2 Hz) for the Live Store animation."""
    h = w.history
    day = max(0, min(int(day), h.n_days - 1))
    t0 = float(start_hour) * 3600.0
    t1 = t0 + max(5, min(int(minutes), 120)) * 60.0
    idx = np.nonzero((h.day == day) & (h.t_arrive >= t0) & (h.t_arrive < t1))[0][
        : max(1, min(int(limit), 200))
    ]
    went = set()
    for i, z in zip(h.ze_track.tolist(), h.ze_zone):
        if z == "checkout":
            went.add(i)
    tracks = []
    for i in idx.tolist():
        a, b = h.traj_offsets[i], h.traj_offsets[i + 1]
        pts = h.traj[a:b]
        tracks.append(
            {
                "id": h.track_id[i],
                "bought": i in went,
                "points": [
                    [round(float(t - t0), 1), round(float(x), 2), round(float(y), 2)]
                    for t, x, y in pts
                ],
            }
        )
    return json_response(
        {"day": day, "start": t0, "window_s": t1 - t0, "tracks": tracks}
    )


@router.get("/store")
def store_geometry(request: Request, w: WorldDep) -> Response:
    return cached_response(request, w, "store", lambda: _store_geometry(w))


@router.get("/analytics")
def analytics(request: Request, w: WorldDep) -> Response:
    return cached_response(request, w, "analytics", lambda: _analytics(w))


@router.get("/journeys/sample")
def journey_sample(
    request: Request,
    w: WorldDep,
    day: Annotated[int, Query(ge=0, le=6)] = 0,
    start_hour: Annotated[float, Query(ge=0, lt=24, allow_inf_nan=False)] = 17.0,
    minutes: Annotated[int, Query(ge=5, le=120)] = 40,
    limit: Annotated[int, Query(ge=1, le=200)] = 80,
) -> Response:
    """Observed trajectories. Validated query parameters form the cache key."""
    key = ("journeys", day, start_hour, minutes, limit)
    return cached_response(
        request, w, key, lambda: _journey_sample(w, day, start_hour, minutes, limit)
    )
