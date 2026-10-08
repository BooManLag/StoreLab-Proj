"""Experiments endpoints."""

from __future__ import annotations

import dataclasses
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from ...agent import LabAgent
from ...config import agent_settings
from ...layout import Layout
from ...llm import GeminiLLM
from ...simulator import METRICS
from ...store import CATEGORIES
from ...validator import Constraints, validate_experiment
from ..dependencies import WorldDep
from ..responses import dumps, json_response
from ..schemas import LabRequest, LayoutRequest, SimulateRequest

log = logging.getLogger("storelab")

router = APIRouter(prefix="/api", tags=["experiments"])


@router.post("/lab/run")
def lab_run(request: Request, w: WorldDep, req: LabRequest) -> StreamingResponse:
    request.app.state.runtime.rate_limit()
    settings = agent_settings()
    llm = None
    if settings.uses_gemini:
        try:
            llm = GeminiLLM(settings)
        except Exception as exc:  # e.g. Vertex selected but no project/credentials
            log.warning("Gemini client unavailable: %s", exc)
            settings = dataclasses.replace(
                settings, mode="offline", reason="Gemini client unavailable"
            )
    rounds = req.rounds or (2 if req.mode == "thorough" else 1)
    overrides = req.overrides.model_dump(exclude_none=True) if req.overrides else None
    agent = LabAgent(
        w, req.objective, settings, llm, max_rounds=rounds, overrides=overrides
    )

    def stream():
        try:
            for ev in agent.run():
                yield f"data: {dumps(ev)}\n\n"
        except Exception:  # never leave the client hanging
            log.exception("Lab run failed")
            yield f"data: {dumps({'type': 'error', 'message': 'Lab run failed. Please try again.'})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/simulate")
def simulate(w: WorldDep, req: SimulateRequest) -> Response:
    """Manual what-if: validate and simulate one experiment against the baseline."""
    if req.metric not in METRICS:
        raise HTTPException(422, f"metric must be one of {list(METRICS)}")
    if req.metric.startswith("category_") and req.category not in CATEGORIES:
        raise HTTPException(422, f"category must be one of {CATEGORIES}")
    cons = Constraints(
        budget_php=req.budget_php,
        max_congestion_increase_pct=req.max_congestion_increase_pct,
    )
    v = validate_experiment(w.store, w.baseline_layout, req.changes, cons)
    if not v.valid:
        return json_response(
            {"validation": v.to_json(), "simulation": None}, status=422
        )
    res = w.simulator.run(v.layout)
    cmp = w.simulator.compare(
        w.baseline,
        res,
        req.metric,
        req.category if req.metric.startswith("category_") else None,
    )
    return json_response(
        {
            "validation": v.to_json(),
            "simulation": {"deltas": cmp, **res.to_json(include_heat=True)},
        }
    )


def _checked_layout(req: LayoutRequest, w: WorldDep) -> Layout:
    s = w.store
    if set(req.category_slot) != set(CATEGORIES) or sorted(
        req.category_slot.values()
    ) != sorted(s.aisle_ids):
        raise HTTPException(
            422, "category_slot must map every category to a distinct aisle"
        )
    for slot, cat in req.displays.items():
        if slot not in s.display_ids or cat not in CATEGORIES:
            raise HTTPException(422, f"Unknown display {slot}: {cat}")
    for slot in req.displays:
        if s.display(slot).restricted:
            raise HTTPException(422, f"{slot} is restricted")
    return Layout.make(req.category_slot, req.displays)


@router.post("/tracks")
def tracks(w: WorldDep, req: LayoutRequest) -> Response:
    """Animated virtual shoppers (17:00-17:40) for a layout; the same shoppers for every layout."""
    layout = _checked_layout(req, w)
    res = w.simulator.run(layout, with_tracks=True)
    return json_response({"start": 17 * 3600, "window_s": 2400, "tracks": res.tracks})
