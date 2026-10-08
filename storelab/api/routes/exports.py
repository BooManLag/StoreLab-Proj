"""Exports endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ...export import TABLES, to_csv
from ..dependencies import WorldDep

router = APIRouter(prefix="/api", tags=["exports"])


@router.get("/data/{table}.csv")
def export_table(w: WorldDep, table: str) -> PlainTextResponse:
    if table not in TABLES:
        raise HTTPException(404, f"Unknown table. Available: {list(TABLES)}")
    return PlainTextResponse(
        to_csv(w, table),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="storelab_{table}.csv"'},
    )
