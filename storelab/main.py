"""StoreLab API + web app (one Cloud Run service).

    uvicorn storelab.main:app --port 8080
"""

from __future__ import annotations

import collections
import dataclasses
import datetime as dt
import json
import logging
import math
import mimetypes
import os
import tempfile
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal, Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .agent import LabAgent
from .config import DATA_DIR, WEB_DIR, agent_settings, lab_rate_limit_per_minute
from .cv.pipeline import process_video
from .cv.render import calibration as demo_calibration
from .cv.render import demo_clip
from .export import TABLES, to_csv
from .layout import Change, Layout, layout_to_json
from .llm import GeminiLLM
from .objective import MAX_OBJECTIVE_CHARS, ObjectiveSpec
from .pilot import plan_pilot
from .simulator import METRICS
from .store import CATEGORIES, CATEGORY_LABELS
from .validator import Constraints, validate_experiment
from .world import get_world

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("storelab")

# Some hosts (notably Windows registries) map .js to text/plain, which breaks ES modules.
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

MAX_UPLOAD_BYTES = 30 * 1024 * 1024


# ---------------------------------------------------------------- JSON helpers
def _clean(o: Any) -> Any:
    """Make numpy / NaN-laden structures valid JSON."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, set):
        return [_clean(v) for v in sorted(o)]
    return o


def dumps(data: Any) -> str:
    return json.dumps(_clean(data), ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def json_response(data: Any, status: int = 200) -> Response:
    return Response(content=dumps(data), media_type="application/json", status_code=status)


# ---------------------------------------------------------------- app
@asynccontextmanager
async def lifespan(_: FastAPI):
    t0 = time.perf_counter()
    get_world()
    log.info("StoreLab world ready in %.1fs", time.perf_counter() - t0)
    yield


app = FastAPI(title="StoreLab", version=__version__, lifespan=lifespan,
              description="A/B testing for physical retail: understand the store, simulate the change, test what matters.")

_runs_lock = threading.Lock()
_recent_runs: collections.deque[float] = collections.deque()
_pilots: dict[str, dict] = {}
_pilots_lock = threading.Lock()


def _rate_limit() -> None:
    limit = lab_rate_limit_per_minute()
    now = time.monotonic()
    with _runs_lock:
        while _recent_runs and now - _recent_runs[0] > 60:
            _recent_runs.popleft()
        if len(_recent_runs) >= limit:
            raise HTTPException(429, f"Too many AI Lab runs; limit is {limit} per minute.")
        _recent_runs.append(now)


@app.get("/api/health")
def health() -> Response:
    return json_response({"status": "ok", "version": __version__})


@app.get("/api/config")
def config() -> Response:
    w = get_world()
    s = agent_settings()
    return json_response({
        "version": __version__,
        "agent": s.public(),
        "synthetic_data": True,
        "store": {"id": w.store.store_id, "name": w.store.name, "region": w.store.region, "currency": w.store.currency},
        "history": {"journeys": w.history.n_journeys, "transactions": w.history.n_transactions,
                    "days": w.history.n_days, "period": w.analytics.summary["kpis"]["period"]},
        "simulator": {"journeys_per_run": w.simulator.n, "days_per_run": w.simulator.days},
        "built_at": w.built_at,
    })


@app.get("/api/store")
def store_geometry() -> Response:
    w = get_world()
    s = w.store
    rect = lambda r: {"x0": r[0], "y0": r[1], "x1": r[2], "y1": r[3]}  # noqa: E731
    return json_response({
        "id": s.store_id, "name": s.name, "region": s.region, "currency": s.currency, "timezone": s.timezone,
        "width": s.width, "height": s.height, "cell_m": 0.5,
        "fixtures": [{"id": f.id, "label": f.label, "kind": f.kind, "refrigerated": f.refrigerated, **rect(f.rect)}
                     for f in s.fixtures],
        "aisles": [{"id": a.id, "label": a.label, "refrigerated": a.refrigerated, "anchor": a.anchor, **rect(a.rect)}
                   for a in s.aisles],
        "displays": [{"id": d.id, "label": d.label, "kind": d.kind, "add_cost": d.add_cost,
                      "free_standing": d.free_standing, "clear_width_m": d.clear_width_m, "restricted": d.restricted,
                      "restricted_reason": d.restricted_reason, "at_checkout": d.at_checkout, **rect(d.rect)}
                     for d in s.displays],
        "areas": {"entrance": rect(s.entrance_rect), "checkout": rect(s.checkout_rect), "exit": rect(s.exit_rect),
                  "entrance_door": rect(s.entrance_door), "exit_door": rect(s.exit_door)},
        "categories": [{"id": c, "label": CATEGORY_LABELS[c]} for c in CATEGORIES],
        "baseline_layout": layout_to_json(s, w.baseline_layout),
        "products": [dataclasses.asdict(p) for p in s.products],
        "network": [dataclasses.asdict(n) for n in s.network],
        "costs": {"move_display": s.move_display_cost, "remove_display": s.remove_display_cost,
                  "swap_categories": s.swap_categories_cost},
        "constraints": {"min_aisle_width_m": s.min_aisle_width_m, "max_changes": s.max_changes_per_experiment,
                        "refrigerated_fixed": True, "peak_window": list(s.peak_window)},
    })


@app.get("/api/analytics")
def analytics() -> Response:
    w = get_world()
    return json_response({
        "summary": w.analytics.summary,
        "heatmap": np.round(w.analytics.heatmap, 1),
        "heatmap_units": "shopper-seconds per 0.5 m cell per day (observed)",
        "model": w.fit_report,
        "calibration": w.calibration,
    })


@app.get("/api/journeys/sample")
def journey_sample(day: int = 0, start_hour: float = 17.0, minutes: int = 40, limit: int = 80) -> Response:
    """Observed anonymous trajectories (2 Hz) for the Live Store animation."""
    w = get_world()
    h = w.history
    day = max(0, min(int(day), h.n_days - 1))
    t0 = float(start_hour) * 3600.0
    t1 = t0 + max(5, min(int(minutes), 120)) * 60.0
    idx = np.nonzero((h.day == day) & (h.t_arrive >= t0) & (h.t_arrive < t1))[0][: max(1, min(int(limit), 200))]
    went = set()
    for i, z in zip(h.ze_track.tolist(), h.ze_zone):
        if z == "checkout":
            went.add(i)
    tracks = []
    for i in idx.tolist():
        a, b = h.traj_offsets[i], h.traj_offsets[i + 1]
        pts = h.traj[a:b]
        tracks.append({"id": h.track_id[i], "bought": i in went,
                       "points": [[round(float(t - t0), 1), round(float(x), 2), round(float(y), 2)] for t, x, y in pts]})
    return json_response({"day": day, "start": t0, "window_s": t1 - t0, "tracks": tracks})


class ObjectiveOverrides(BaseModel):
    """Values the manager edits directly on the objective chips."""

    budget_php: Optional[float] = Field(default=None, gt=0, le=10_000_000)
    max_congestion_increase_pct: Optional[float] = Field(default=None, ge=0, le=100)
    target_uplift_pct: Optional[float] = Field(default=None, ge=0, le=500)
    target_category: Optional[Literal["bakery", "coffee", "snacks", "beverages"]] = None


class LabRequest(BaseModel):
    objective: str = Field(min_length=3, max_length=MAX_OBJECTIVE_CHARS)
    mode: Literal["fast", "thorough"] = "fast"
    rounds: Optional[int] = Field(default=None, ge=1, le=2)  # legacy; overrides mode when given
    overrides: Optional[ObjectiveOverrides] = None


@app.post("/api/lab/run")
def lab_run(req: LabRequest) -> StreamingResponse:
    _rate_limit()
    w = get_world()
    settings = agent_settings()
    llm = None
    if settings.uses_gemini:
        try:
            llm = GeminiLLM(settings)
        except Exception as exc:  # e.g. Vertex selected but no project/credentials
            log.warning("Gemini client unavailable: %s", exc)
            settings = dataclasses.replace(settings, mode="offline", reason=f"Gemini client error: {exc}")
    rounds = req.rounds or (2 if req.mode == "thorough" else 1)
    overrides = req.overrides.model_dump(exclude_none=True) if req.overrides else None
    agent = LabAgent(w, req.objective, settings, llm, max_rounds=rounds, overrides=overrides)

    def stream():
        try:
            for ev in agent.run():
                yield f"data: {dumps(ev)}\n\n"
        except Exception as exc:  # never leave the client hanging
            log.exception("Lab run failed")
            yield f"data: {dumps({'type': 'error', 'message': f'{type(exc).__name__}: {exc}'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class SimulateRequest(BaseModel):
    changes: list[Change] = Field(min_length=1, max_length=5)
    budget_php: float = 50_000
    metric: str = "category_revenue"
    category: Optional[str] = "snacks"
    max_congestion_increase_pct: float = 10.0


@app.post("/api/simulate")
def simulate(req: SimulateRequest) -> Response:
    """Manual what-if: validate and simulate one experiment against the baseline."""
    w = get_world()
    if req.metric not in METRICS:
        raise HTTPException(422, f"metric must be one of {list(METRICS)}")
    if req.metric.startswith("category_") and req.category not in CATEGORIES:
        raise HTTPException(422, f"category must be one of {CATEGORIES}")
    cons = Constraints(budget_php=req.budget_php, max_congestion_increase_pct=req.max_congestion_increase_pct)
    v = validate_experiment(w.store, w.baseline_layout, req.changes, cons)
    if not v.valid:
        return json_response({"validation": v.to_json(), "simulation": None}, status=422)
    res = w.simulator.run(v.layout)
    cmp = w.simulator.compare(w.baseline, res, req.metric, req.category if req.metric.startswith("category_") else None)
    return json_response({"validation": v.to_json(), "simulation": {"deltas": cmp, **res.to_json(include_heat=True)}})


class LayoutRequest(BaseModel):
    category_slot: dict[str, str]
    displays: dict[str, str] = Field(default_factory=dict)


def _checked_layout(req: LayoutRequest) -> Layout:
    w = get_world()
    s = w.store
    if set(req.category_slot) != set(CATEGORIES) or sorted(req.category_slot.values()) != sorted(s.aisle_ids):
        raise HTTPException(422, "category_slot must map every category to a distinct aisle")
    for slot, cat in req.displays.items():
        if slot not in s.display_ids or cat not in CATEGORIES:
            raise HTTPException(422, f"Unknown display {slot}: {cat}")
    for slot in req.displays:
        if s.display(slot).restricted:
            raise HTTPException(422, f"{slot} is restricted")
    return Layout.make(req.category_slot, req.displays)


@app.post("/api/tracks")
def tracks(req: LayoutRequest) -> Response:
    """Animated virtual shoppers (17:00-17:40) for a layout; the same shoppers for every layout."""
    w = get_world()
    layout = _checked_layout(req)
    res = w.simulator.run(layout, with_tracks=True)
    return json_response({"start": 17 * 3600, "window_s": 2400, "tracks": res.tracks})


class PilotPlanRequest(BaseModel):
    objective: ObjectiveSpec
    candidate: dict


@app.post("/api/pilot/plan")
def pilot_plan(req: PilotPlanRequest) -> Response:
    """Pilot plan for any simulated experiment the manager picks (not only the recommended one)."""
    w = get_world()
    c = req.candidate
    try:
        c["simulation"]["deltas"]["primary"]["relative_pct"]
        c["simulation"]["deltas"]["congestion"]["relative_pct"]
        c["id"], c["name"], c["descriptions"], c["cost"]
    except (KeyError, TypeError):
        raise HTTPException(422, "candidate must be a simulated experiment from an AI Lab run")
    return json_response(plan_pilot(w.store, req.objective, w.baseline, c))


@app.post("/api/cv/demo")
def cv_demo() -> Response:
    clip = demo_clip(DATA_DIR / "cv")
    cal = json.loads(clip.calibration_path.read_text())
    result = process_video(clip.video_path, cal, clip.background_path, truth_path=clip.truth_path)
    result["calibration"] = cal
    result["source"] = "Synthetic demo CCTV clip (rendered from the hidden ground-truth world)"
    return json_response(result)


@app.post("/api/cv/upload")
async def cv_upload(file: UploadFile = File(...), calibration: Optional[str] = Form(None)) -> Response:
    """Process your own fixed-camera clip. Calibration maps 4 image points to 4 floor points (metres)."""
    w = get_world()
    if calibration:
        try:
            cal = json.loads(calibration)
            assert len(cal["image_points"]) == 4 and len(cal["floor_points"]) == 4
        except Exception as exc:
            raise HTTPException(422, f"calibration must be JSON with 4 image_points and 4 floor_points: {exc}")
    else:
        cal = None
    suffix = Path(file.filename or "clip").suffix.lower()[:8] or ".mp4"
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    size = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Video too large (max 30 MB)")
                out.write(chunk)
        if cal is None:
            cap = cv2.VideoCapture(tmp)
            fw, fh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            if fw <= 0 or fh <= 0:
                raise HTTPException(422, "Could not read the video")
            cal = {"image_points": [[0, 0], [fw, 0], [fw, fh], [0, fh]],
                   "floor_points": [[0, 0], [w.store.width, 0], [w.store.width, w.store.height], [0, w.store.height]],
                   "time_scale": 1.0,
                   "note": "Default calibration assumes a top-down camera framing the whole floor."}
        try:
            result = process_video(Path(tmp), cal, None, store=w.store, max_frames=2400)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        result["calibration"] = cal
        result["source"] = "Uploaded clip (deleted after processing)"
        return json_response(result)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


@app.get("/api/cv/calibration")
def cv_calibration() -> Response:
    return json_response(demo_calibration())


class PilotRequest(BaseModel):
    plan: dict
    objective: Optional[str] = None


@app.post("/api/pilots")
def create_pilot(req: PilotRequest) -> Response:
    plan = req.plan
    for key in ("title", "test_stores", "control_stores", "duration_days", "primary_kpi"):
        if key not in plan:
            raise HTTPException(422, f"plan is missing '{key}'")
    pid = "PIL-" + uuid.uuid4().hex[:8].upper()
    record = {
        "pilot_id": pid,
        "status": "scheduled",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "objective": req.objective,
        "plan": plan,
        "note": "Demo: pilots are kept in memory on this instance.",
    }
    with _pilots_lock:
        _pilots[pid] = record
    return json_response(record, status=201)


@app.get("/api/pilots")
def list_pilots() -> Response:
    with _pilots_lock:
        return json_response(sorted(_pilots.values(), key=lambda r: r["created_at"], reverse=True))


@app.get("/api/data/{table}.csv")
def export_table(table: str) -> PlainTextResponse:
    if table not in TABLES:
        raise HTTPException(404, f"Unknown table. Available: {list(TABLES)}")
    return PlainTextResponse(to_csv(get_world(), table), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="storelab_{table}.csv"'})


# ---------------------------------------------------------------- web app
class RevalidatedStaticFiles(StaticFiles):
    """Always revalidate (cheap 304s via ETag) so a redeploy never leaves users on stale JS modules."""

    def file_response(self, *args, **kwargs):
        resp = super().file_response(*args, **kwargs)
        resp.headers["Cache-Control"] = "no-cache"
        return resp


app.mount("/static", RevalidatedStaticFiles(directory=str(WEB_DIR)), name="static")


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(str(WEB_DIR / "index.html"), headers={"Cache-Control": "no-cache"})
