"""Render a synthetic ceiling-camera clip of the demo store (clearly labelled SYNTHETIC).

Shoppers come from the hidden ground-truth engine, are drawn as anonymous blobs (no
faces, no identity), and are filmed through an angled-camera perspective. Ground-truth
floor positions are saved alongside, so the CV pipeline can be scored honestly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from ..engine import make_draws, run_engine, script_to_track
from ..groundtruth import true_checkout, true_params
from ..layout import baseline_layout
from ..store import STORE, StoreSpec

FRAME_W, FRAME_H = 480, 340
FPS = 8
CLIP_SECONDS = 45
TIME_SCALE = 2.0  # store seconds per video second (2x fast-forward)
PX_PER_M_PLAN = 24

# Floor corners (m) -> image (px): an angled ceiling camera looking at the store from the front.
FLOOR_PTS = [(0.0, 0.0), (22.0, 0.0), (22.0, 15.0), (0.0, 15.0)]
IMAGE_PTS = [(70.0, 28.0), (410.0, 28.0), (468.0, 326.0), (12.0, 326.0)]


@dataclass
class DemoClip:
    video_path: Path
    background_path: Path
    calibration_path: Path
    truth_path: Path


def calibration(store: StoreSpec = STORE) -> dict:
    return {
        "image_points": [list(p) for p in IMAGE_PTS],
        "floor_points": [list(p) for p in FLOOR_PTS],
        "frame_size": [FRAME_W, FRAME_H],
        "time_scale": TIME_SCALE,
        "store_id": store.store_id,
        "camera": "cam-01 (synthetic angled ceiling camera)",
    }


def _floor_to_image() -> np.ndarray:
    return cv2.getPerspectiveTransform(np.float32(FLOOR_PTS), np.float32(IMAGE_PTS))


def _plan_image(store: StoreSpec) -> np.ndarray:
    s = PX_PER_M_PLAN
    W, H = int(store.width * s), int(store.height * s)
    img = np.full((H, W, 3), (196, 200, 204), dtype=np.uint8)
    rng = np.random.default_rng(3)
    img = np.clip(img.astype(int) + rng.integers(-6, 7, size=(H, W, 1)), 0, 255).astype(np.uint8)
    for x in range(0, W, s):  # floor tiles
        cv2.line(img, (x, 0), (x, H), (186, 190, 194), 1)
    for y in range(0, H, s):
        cv2.line(img, (0, y), (W, y), (186, 190, 194), 1)

    def R(r, color):
        cv2.rectangle(img, (int(r[0] * s), int(r[1] * s)), (int(r[2] * s) - 1, int(r[3] * s) - 1), color, -1)

    for f in store.fixtures:
        R(f.rect, (120, 104, 92) if f.kind != "cooler" else (160, 120, 70))
    for d in store.displays:
        if d.id in store.baseline_displays:
            R(d.rect, (60, 140, 200))
    R(store.entrance_door, (90, 160, 90))
    R(store.exit_door, (90, 90, 170))
    return img


def _people(store: StoreSpec, seed: int):
    """Pick a busy evening window from a ground-truth run and return per-person dense tracks."""
    tp, tck = true_params(store), true_checkout()
    draws = make_draws(1500, 1, tp.hour_weights, len(store.displays), seed)
    layout = baseline_layout(store)
    out = run_engine(tp, tck, store, layout, draws, script_ids=set(range(draws.n)))
    span = CLIP_SECONDS * TIME_SCALE
    starts = np.arange(17 * 3600, 19 * 3600, 30.0)
    best_t0, best_n = starts[0], -1
    for t0 in starts:
        n = int(((out.arrival < t0 + span) & (out.t_exit > t0)).sum())
        if n > best_n:
            best_t0, best_n = t0, n
    t0 = float(best_t0)
    people = []
    rng = np.random.default_rng(seed + 1)  # shoppers wander while browsing instead of standing on one spot
    for i in np.nonzero((out.arrival < t0 + span) & (out.t_exit > t0))[0]:
        tr = script_to_track(out, int(i), tp.walk_speed, rng=rng)
        if len(tr) >= 2:
            people.append(tr)
    return t0, people


def render_demo_clip(out_dir: Path, store: StoreSpec = STORE, seed: int = 4242) -> DemoClip:
    out_dir.mkdir(parents=True, exist_ok=True)
    video_path = out_dir / "demo_cctv.avi"
    bg_path = out_dir / "demo_cctv_background.png"
    cal_path = out_dir / "demo_cctv_calibration.json"
    truth_path = out_dir / "demo_cctv_truth.npz"

    H = _floor_to_image()
    plan = _plan_image(store)
    scale = np.float32([[1 / PX_PER_M_PLAN, 0, 0], [0, 1 / PX_PER_M_PLAN, 0], [0, 0, 1]])
    plate = cv2.warpPerspective(plan, H @ scale, (FRAME_W, FRAME_H), borderValue=(40, 40, 44))
    cv2.imwrite(str(bg_path), plate)

    t0, people = _people(store, seed)
    rng = np.random.default_rng(seed)
    colors = [tuple(int(c) for c in rng.integers(20, 110, size=3)) for _ in people]
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), FPS, (FRAME_W, FRAME_H))
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not open an MJPG video writer")
    truth_rows = []
    n_frames = CLIP_SECONDS * FPS
    try:
        for f in range(n_frames):
            t = t0 + (f / FPS) * TIME_SCALE
            frame = plate.copy()
            gain = 1.0 + 0.03 * np.sin(f / 9.0)  # lighting flicker
            for pid, (tr, col) in enumerate(zip(people, colors)):
                if t < tr[0, 0] or t > tr[-1, 0]:
                    continue
                x = float(np.interp(t, tr[:, 0], tr[:, 1]))
                y = float(np.interp(t, tr[:, 0], tr[:, 2]))
                p = cv2.perspectiveTransform(np.float32([[[x, y]]]), H)[0, 0]
                # body size in pixels from local perspective scale
                q = cv2.perspectiveTransform(np.float32([[[x + 0.32, y]]]), H)[0, 0]
                r = max(3, int(round(abs(q[0] - p[0]))))
                cv2.ellipse(frame, (int(p[0]), int(p[1])), (r, int(r * 1.15)), 0, 0, 360, col, -1, cv2.LINE_AA)
                cv2.circle(frame, (int(p[0]), int(p[1] - r * 0.25)), max(2, r // 2),
                           tuple(min(255, c + 70) for c in col), -1, cv2.LINE_AA)
                truth_rows.append((f, pid, x, y))
            frame = np.clip(frame.astype(np.float32) * gain + rng.normal(0, 3.0, frame.shape), 0, 255).astype(np.uint8)
            writer.write(frame)
    finally:
        writer.release()
    np.savez_compressed(truth_path, rows=np.asarray(truth_rows, dtype=np.float64), fps=FPS, t0=t0)
    cal_path.write_text(json.dumps(calibration(store), indent=2))
    return DemoClip(video_path, bg_path, cal_path, truth_path)


def demo_clip(out_dir: Path) -> DemoClip:
    clip = DemoClip(out_dir / "demo_cctv.avi", out_dir / "demo_cctv_background.png",
                    out_dir / "demo_cctv_calibration.json", out_dir / "demo_cctv_truth.npz")
    if all(p.exists() for p in (clip.video_path, clip.background_path, clip.calibration_path, clip.truth_path)):
        return clip
    return render_demo_clip(out_dir)
