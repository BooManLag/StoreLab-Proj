"""Application factory and lifecycle; routers contain only HTTP concerns."""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .. import __version__
from ..config import WEB_DIR
from ..world import get_world
from .cache import ResponseCache
from .responses import json_response
from .routes import experiments, exports, pilots, store, system, vision
from .state import RuntimeState
from .web import RevalidatedStaticFiles
from .web import router as web_router

log = logging.getLogger("storelab")


class BackendSettings(BaseModel):
    cache_ttl_seconds: float = Field(default=60, ge=0, allow_inf_nan=False)
    cache_max_entries: int = Field(default=128, ge=0)
    cache_max_bytes: int = Field(default=16 * 1024 * 1024, ge=0)

    @classmethod
    def from_environment(cls) -> "BackendSettings":
        return cls(
            **{
                name: os.environ[env]
                for name, env in {
                    "cache_ttl_seconds": "STORELAB_CACHE_TTL_SECONDS",
                    "cache_max_entries": "STORELAB_CACHE_MAX_ENTRIES",
                    "cache_max_bytes": "STORELAB_CACHE_MAX_BYTES",
                }.items()
                if env in os.environ
            }
        )


def create_app(settings: BackendSettings | None = None) -> FastAPI:
    settings = settings or BackendSettings.from_environment()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        t0 = time.perf_counter()
        await run_in_threadpool(get_world)
        log.info("StoreLab world ready in %.1fs", time.perf_counter() - t0)
        try:
            yield
        finally:
            app.state.runtime.cache.clear()

    app = FastAPI(
        title="StoreLab",
        version=__version__,
        lifespan=lifespan,
        description="A/B testing for physical retail: understand the store, simulate the change, test what matters.",
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Pydantic includes rejected input in its errors. NaN/Infinity must not
        # turn a validation failure into a JSON serialization error (HTTP 500).
        return json_response({"detail": jsonable_encoder(exc.errors())}, status=422)

    app.state.runtime = RuntimeState(
        ResponseCache(
            ttl=settings.cache_ttl_seconds,
            max_entries=settings.cache_max_entries,
            max_bytes=settings.cache_max_bytes,
        )
    )
    for router in (
        system.router,
        store.router,
        experiments.router,
        pilots.router,
        vision.router,
        exports.router,
    ):
        app.include_router(router)
    app.mount("/static", RevalidatedStaticFiles(directory=str(WEB_DIR)), name="static")
    app.include_router(web_router)
    return app
