"""System endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from ... import __version__
from ...config import agent_settings
from ..dependencies import WorldDep
from ..responses import json_response

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health() -> Response:
    return json_response({"status": "ok", "version": __version__})


@router.get("/config")
def config(w: WorldDep) -> Response:
    s = agent_settings()
    return json_response(
        {
            "version": __version__,
            "agent": s.public(),
            "synthetic_data": True,
            "store": {
                "id": w.store.store_id,
                "name": w.store.name,
                "region": w.store.region,
                "currency": w.store.currency,
            },
            "history": {
                "journeys": w.history.n_journeys,
                "transactions": w.history.n_transactions,
                "days": w.history.n_days,
                "period": w.analytics.summary["kpis"]["period"],
            },
            "simulator": {
                "journeys_per_run": w.simulator.n,
                "days_per_run": w.simulator.days,
            },
            "built_at": w.built_at,
        }
    )
