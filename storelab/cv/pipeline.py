"""CV pipeline: video -> person detection -> multi-object tracking -> floor coordinates -> zones.

Detection here is background subtraction against an empty-store reference plate (or a
per-pixel median background), which suits fixed ceiling cameras. A deep person
detector can replace `detect()` without touching the rest. Privacy by design: no face
or appearance features are extracted, track ids are random per run, and frames are
discarded after processing (only a few annotated previews are returned for the demo).
"""

from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

from ..geometry import in_rect
from ..store import STORE, StoreSpec

MIN_AREA_PX = 12
MAX_AREA_PX = 900
DIFF_THRESHOLD = 26
GATE_M = 1.0
CONFIRM_HITS = 3
MAX_MISSED = 20  # frames a track survives without a detection (occlusion / merged blobs)


@dataclass
class Track:
    tid: str
    points: list[tuple[int, float, float]] = field(default_factory=list)  # (frame, x_m, y_m)
    pixels: list[tuple[int, float, float, int, int, int, int]] = field(default_factory=list)  # frame, cx, cy, box
    hits: int = 0
    missed: int = 0
    vx: float = 0.0
    vy: float = 0.0

    @property
    def last(self) -> tuple[float, float]:
        return self.points[-1][1], self.points[-1][2]

    def predict(self) -> tuple[float, float]:
        x, y = self.last
        k = self.missed + 1
        return x + self.vx * k, y + self.vy * k


def _homography(cal: dict) -> tuple[np.ndarray, np.ndarray]:
    img = np.float32(cal["image_points"])
    flr = np.float32(cal["floor_points"])
    return cv2.getPerspectiveTransform(img, flr), cv2.getPerspectiveTransform(flr, img)


def _median_background(cap: cv2.VideoCapture, n_frames: int, samples: int = 40) -> np.ndarray:
    idx = np.linspace(0, max(0, n_frames - 1), num=min(samples, max(1, n_frames))).astype(int)
    frames = []
    for i in idx:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, fr = cap.read()
        if ok:
            frames.append(fr)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    if not frames:
        raise ValueError("Could not read frames to build a background model")
    return np.median(np.stack(frames), axis=0).astype(np.uint8)


def detect(frame: np.ndarray, bg_gray: np.ndarray, floor_mask: np.ndarray) -> list[tuple[float, float, tuple]]:
    gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    diff = cv2.absdiff(gray, bg_gray)
    _, fg = cv2.threshold(diff, DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
    fg = cv2.bitwise_and(fg, floor_mask)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, _, stats, cents = cv2.connectedComponentsWithStats(fg, connectivity=8)
    out = []
    for k in range(1, n):
        x, y, w, h, area = stats[k]
        if MIN_AREA_PX <= area <= MAX_AREA_PX:
            out.append((float(cents[k][0]), float(cents[k][1]), (int(x), int(y), int(w), int(h))))
    return out


def process_video(video_path: Path, cal: dict, background_path: Path | None = None, store: StoreSpec = STORE,
                  truth_path: Path | None = None, preview_frames: int = 12, max_frames: int = 3000) -> dict:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError("Could not open the video file")
    fps = cap.get(cv2.CAP_PROP_FPS) or 8.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    time_scale = float(cal.get("time_scale", 1.0))
    H_i2f, H_f2i = _homography(cal)

    if background_path is not None and Path(background_path).exists():
        bg = cv2.imread(str(background_path))
        bg_mode = "reference plate (empty store)"
    else:
        bg = _median_background(cap, n_frames)
        bg_mode = "per-pixel median of sampled frames"
    if bg is None or bg.shape[:2] != (h, w):
        raise ValueError("Background does not match the video size")
    bg_gray = cv2.GaussianBlur(cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    floor_poly = cv2.perspectiveTransform(
        np.float32([[[0, 0], [store.width, 0], [store.width, store.height], [0, store.height]]]), H_f2i)[0]
    floor_mask = np.zeros((h, w), np.uint8)
    cv2.fillConvexPoly(floor_mask, floor_poly.astype(np.int32), 255)

    active: list[Track] = []
    finished: list[Track] = []
    preview_idx = set(np.linspace(0, max(0, min(n_frames, max_frames) - 1), num=preview_frames).astype(int).tolist())
    previews = []
    frame_no = 0
    detections_total = 0
    while frame_no < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        dets = detect(frame, bg_gray, floor_mask)
        detections_total += len(dets)
        floor = (cv2.perspectiveTransform(np.float32([[[d[0], d[1]] for d in dets]]), H_i2f)[0]
                 if dets else np.zeros((0, 2), np.float32))
        # --- associate (Hungarian on predicted floor positions, gated)
        matched_t, matched_d = set(), set()
        if active and dets:
            preds = np.array([t.predict() for t in active])
            cost = np.linalg.norm(preds[:, None, :] - floor[None, :, :], axis=2)
            rows, cols = linear_sum_assignment(cost)
            for r, c in zip(rows, cols):
                if cost[r, c] <= GATE_M * (1 + 0.5 * active[r].missed):
                    tr = active[r]
                    px, py = tr.last
                    nx, ny = float(floor[c][0]), float(floor[c][1])
                    gap = active[r].missed + 1
                    tr.vx = 0.6 * tr.vx + 0.4 * (nx - px) / gap
                    tr.vy = 0.6 * tr.vy + 0.4 * (ny - py) / gap
                    tr.points.append((frame_no, nx, ny))
                    bx = dets[c][2]
                    tr.pixels.append((frame_no, dets[c][0], dets[c][1], *bx))
                    tr.hits += 1
                    tr.missed = 0
                    matched_t.add(r)
                    matched_d.add(c)
        for k, tr in enumerate(active):
            if k not in matched_t:
                tr.missed += 1
        for c, d in enumerate(dets):
            if c not in matched_d:
                tr = Track(tid=f"anon_{secrets.token_hex(3)}")
                tr.points.append((frame_no, float(floor[c][0]), float(floor[c][1])))
                tr.pixels.append((frame_no, d[0], d[1], *d[2]))
                tr.hits = 1
                active.append(tr)
        still = []
        for tr in active:
            if tr.missed > MAX_MISSED:
                finished.append(tr)
            else:
                still.append(tr)
        active = still
        if frame_no in preview_idx:
            previews.append(_annotate(frame, active, frame_no, fps))
        frame_no += 1
    cap.release()
    finished.extend(active)
    tracks = [t for t in finished if t.hits >= CONFIRM_HITS]

    zones = store.zone_rects()
    out_tracks, events = [], []
    for t in tracks:
        pts = [{"t": round(f / fps * time_scale, 2), "x": round(x, 2), "y": round(y, 2), "zone": _zone_of(zones, x, y)}
               for f, x, y in t.points]
        visits = _zone_visits(pts)
        out_tracks.append({"anonymous_track_id": t.tid, "points": pts, "zone_visits": visits,
                           "journey": [v["zone"] for v in visits]})
        for v in visits:
            events.append({"anonymous_track_id": t.tid, "zone_id": v["zone"], "t_enter_s": v["t_enter"],
                           "dwell_seconds": v["dwell_s"], "x": v["x"], "y": v["y"], "event_type": "zone_visit"})
    result = {
        "frames": frame_no,
        "fps": fps,
        "frame_size": [w, h],
        "time_scale": time_scale,
        "background": bg_mode,
        "detections": detections_total,
        "tracks": out_tracks,
        "events": events,
        "previews": previews,
        "privacy": {
            "faces_or_biometrics": "not extracted",
            "track_ids": "random per processing run; no cross-visit identity",
            "raw_frames": "discarded after processing; preview frames returned for this demo only",
        },
    }
    if truth_path is not None and Path(truth_path).exists():
        result["evaluation"] = evaluate(tracks, Path(truth_path))
    return result


def _zone_of(zones: dict, x: float, y: float) -> str | None:
    for zid, rect in zones.items():
        if in_rect(np.array([x]), np.array([y]), rect)[0]:
            return zid
    return None


def _zone_visits(pts: list[dict]) -> list[dict]:
    visits: list[dict] = []
    for p in pts:
        z = p["zone"]
        if z is None:
            continue
        if visits and visits[-1]["zone"] == z and p["t"] - visits[-1]["t_exit"] <= 3.0:
            v = visits[-1]
            v["t_exit"] = p["t"]
            v["n"] += 1
            v["x"] += (p["x"] - v["x"]) / v["n"]
            v["y"] += (p["y"] - v["y"]) / v["n"]
        else:
            visits.append({"zone": z, "t_enter": p["t"], "t_exit": p["t"], "x": p["x"], "y": p["y"], "n": 1})
    for v in visits:
        v["dwell_s"] = round(v["t_exit"] - v["t_enter"], 1)
        v["x"], v["y"] = round(v["x"], 2), round(v["y"], 2)
        v.pop("n")
    return visits


def _annotate(frame: np.ndarray, active: list[Track], frame_no: int, fps: float) -> dict:
    img = frame.copy()
    for t in active:
        if t.hits < CONFIRM_HITS or t.missed:
            continue
        trail = [(int(cx), int(cy)) for _, cx, cy, *_ in t.pixels[-12:]]
        for a, b in zip(trail[:-1], trail[1:]):
            cv2.line(img, a, b, (0, 220, 255), 1, cv2.LINE_AA)
        _, cx, cy, x, y, w, h = t.pixels[-1]
        cv2.rectangle(img, (x - 2, y - 2), (x + w + 2, y + h + 2), (0, 255, 120), 1)
        cv2.putText(img, t.tid.replace("anon_", ""), (x, max(8, y - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.32,
                    (0, 255, 120), 1, cv2.LINE_AA)
    cv2.putText(img, f"cam-01  t={frame_no / fps:5.1f}s  SYNTHETIC", (6, img.shape[0] - 6), cv2.FONT_HERSHEY_SIMPLEX,
                0.38, (255, 255, 255), 1, cv2.LINE_AA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return {"frame": frame_no, "jpeg_base64": base64.b64encode(buf.tobytes()).decode("ascii") if ok else ""}


def evaluate(tracks: list[Track], truth_path: Path) -> dict:
    """Score tracks against the synthetic clip's ground-truth floor positions."""
    data = np.load(truth_path)
    rows = data["rows"]  # frame, pid, x, y
    by_frame: dict[int, list[tuple[int, float, float]]] = {}
    for f, pid, x, y in rows:
        by_frame.setdefault(int(f), []).append((int(pid), x, y))
    people = sorted({int(p) for p in rows[:, 1]})
    # majority-vote association of each track to a person
    assign: dict[str, int] = {}
    errors: list[float] = []
    for t in tracks:
        votes: dict[int, list[float]] = {}
        for f, x, y in t.points:
            cands = by_frame.get(f, [])
            if not cands:
                continue
            d = [(np.hypot(x - cx, y - cy), pid) for pid, cx, cy in cands]
            dist, pid = min(d)
            if dist <= 1.0:
                votes.setdefault(pid, []).append(dist)
        if votes:
            pid = max(votes, key=lambda k: len(votes[k]))
            assign[t.tid] = pid
            errors.extend(votes[pid])
    covered = {}
    for tid, pid in assign.items():
        covered.setdefault(pid, []).append(tid)
    # people visible for at least 2 s of clip are expected to be tracked
    fps = float(data["fps"])
    visible = {pid: int((rows[:, 1] == pid).sum()) for pid in people}
    expected = [pid for pid, n in visible.items() if n >= 2 * fps]
    found = [pid for pid in expected if pid in covered]
    return {
        "people_in_clip": len(expected),
        "people_tracked": len(found),
        "recall": len(found) / len(expected) if expected else 0.0,
        "tracks": len(tracks),
        "fragmented_people": sum(1 for pid in found if len(covered[pid]) > 1),
        "unmatched_tracks": sum(1 for t in tracks if t.tid not in assign),
        "mean_position_error_m": float(np.mean(errors)) if errors else None,
        "note": "Scored against the synthetic clip's hidden ground truth.",
    }
