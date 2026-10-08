"""Pilots endpoints."""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ...pilot import plan_pilot
from ..dependencies import WorldDep
from ..responses import json_response
from ..schemas import PilotPlanRequest, PilotRequest

router = APIRouter(prefix="/api", tags=["pilots"])


@router.post("/pilot/plan")
def pilot_plan(w: WorldDep, req: PilotPlanRequest) -> Response:
    """Pilot plan for any simulated experiment the manager picks (not only the recommended one)."""
    c = req.candidate
    try:
        c["simulation"]["deltas"]["primary"]["relative_pct"]
        c["simulation"]["deltas"]["congestion"]["relative_pct"]
        c["id"], c["name"], c["descriptions"], c["cost"]
    except (KeyError, TypeError):
        raise HTTPException(
            422, "candidate must be a simulated experiment from an AI Lab run"
        )
    return json_response(plan_pilot(w.store, req.objective, w.baseline, c))


@router.post("/pilots")
def create_pilot(request: Request, req: PilotRequest) -> Response:
    plan = req.plan
    for key in (
        "title",
        "test_stores",
        "control_stores",
        "duration_days",
        "primary_kpi",
    ):
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
    with request.app.state.runtime.pilots_lock:
        request.app.state.runtime.pilots[pid] = record
    return json_response(record, status=201)


@router.get("/pilots")
def list_pilots(request: Request) -> Response:
    with request.app.state.runtime.pilots_lock:
        return json_response(
            sorted(
                request.app.state.runtime.pilots.values(),
                key=lambda r: r["created_at"],
                reverse=True,
            )
        )
