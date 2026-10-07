"""Server-side floor-plan rendering (PNG) so Gemini can *see* the store, not just read JSON."""

from __future__ import annotations

import cv2
import numpy as np

from .layout import Layout
from .store import StoreSpec

PX_PER_M = 40
MARGIN = 30

_CAT_BGR = {
    "bakery": (60, 150, 225),
    "coffee": (60, 90, 140),
    "snacks": (40, 170, 240),
    "beverages": (200, 140, 40),
}


def _pt(x: float, y: float) -> tuple[int, int]:
    return int(MARGIN + x * PX_PER_M), int(MARGIN + y * PX_PER_M)


def _rect(img, r, color, thickness=-1):
    cv2.rectangle(img, _pt(r[0], r[1]), _pt(r[2], r[3]), color, thickness)


def _text(img, s: str, x: float, y: float, scale=0.42, color=(30, 30, 30), center=True):
    (w, h), _ = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    px, py = _pt(x, y)
    if center:
        px -= w // 2
        py += h // 2
    cv2.putText(img, s, (px, py), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def render_floorplan_png(store: StoreSpec, layout: Layout) -> bytes:
    W = int(store.width * PX_PER_M) + 2 * MARGIN
    H = int(store.height * PX_PER_M) + 2 * MARGIN
    img = np.full((H, W, 3), 250, dtype=np.uint8)
    _rect(img, (0, 0, store.width, store.height), (235, 235, 235))
    _rect(img, (0, 0, store.width, store.height), (80, 80, 80), 2)
    slot_cat = layout.slot_category()
    for a in store.aisles:
        cat = slot_cat.get(a.id)
        color = _CAT_BGR.get(cat or "", (220, 220, 220))
        tint = tuple(int(255 - (255 - c) * 0.35) for c in color)
        _rect(img, a.rect, tint)
        cx = (a.rect[0] + a.rect[2]) / 2
        _text(img, a.id.upper(), cx, a.rect[1] + 0.6, 0.38)
        _text(img, (cat or "empty").upper(), cx, (a.rect[1] + a.rect[3]) / 2, 0.5)
        if a.refrigerated:
            _text(img, "(refrigerated)", cx, (a.rect[1] + a.rect[3]) / 2 + 0.7, 0.36)
    for f in store.fixtures:
        _rect(img, f.rect, (90, 90, 90) if f.kind != "cooler" else (150, 110, 60))
    _rect(img, store.checkout_rect, (210, 230, 210))
    _text(img, "CHECKOUT", (store.checkout_rect[0] + store.checkout_rect[2]) / 2, store.checkout_rect[1] + 0.5, 0.42)
    _rect(img, store.entrance_door, (60, 170, 60))
    _text(img, "ENTRANCE", (store.entrance_rect[0] + store.entrance_rect[2]) / 2, store.entrance_rect[1] + 1.2, 0.42)
    _rect(img, store.exit_door, (60, 60, 200))
    _text(img, "EXIT", (store.exit_rect[0] + store.exit_rect[2]) / 2, store.exit_rect[1] + 1.2, 0.42)
    occupied = layout.display_map
    for d in store.displays:
        cat = occupied.get(d.id)
        color = _CAT_BGR.get(cat or "", (255, 255, 255))
        _rect(img, d.rect, color)
        _rect(img, d.rect, (0, 0, 200) if d.restricted else (20, 20, 20), 1)
        cx, cy = (d.rect[0] + d.rect[2]) / 2, (d.rect[1] + d.rect[3]) / 2
        label = d.id + (f" [{cat}]" if cat else "") + (" RESTRICTED" if d.restricted else "")
        dy = -0.45 if cy > 11 else (0.55 if cy > 9 else -0.4)
        _text(img, label, cx, cy + dy, 0.33, (0, 0, 160) if d.restricted else (20, 20, 20))
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("PNG encoding failed")
    return buf.tobytes()
