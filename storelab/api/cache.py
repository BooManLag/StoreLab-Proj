"""Bounded, process-local cache for serialized, read-only API responses."""

from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha256
from threading import Lock
from time import monotonic
from typing import Callable, Hashable

from fastapi import Request
from fastapi.responses import Response

from ..config import CACHE_VERSION
from ..world import World


@dataclass(frozen=True)
class Payload:
    body: bytes
    etag: str
    expires_at: float


class ResponseCache:
    """LRU + TTL + byte budget. A lock coalesces concurrent cache misses.

    Factories must be short, synchronous read-only operations, never nested cache
    calls. Failed/oversized results are not retained. TTL starts after building.
    """

    def __init__(
        self,
        *,
        ttl: float = 60,
        max_entries: int = 128,
        max_bytes: int = 16 * 1024 * 1024,
        clock: Callable[[], float] = monotonic,
    ):
        self.ttl = ttl
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._clock = clock
        self._lock = Lock()
        self._entries: OrderedDict[Hashable, Payload] = OrderedDict()
        self._bytes = 0

    def _build(self, factory: Callable[[], bytes]) -> Payload:
        body = factory()
        return Payload(
            body, '"' + sha256(body).hexdigest() + '"', self._clock() + self.ttl
        )

    def get_or_create(
        self, key: Hashable, factory: Callable[[], bytes]
    ) -> tuple[Payload, bool]:
        if self.ttl <= 0 or self.max_entries <= 0 or self.max_bytes <= 0:
            return self._build(factory), False
        with self._lock:
            now = self._clock()
            for expired in [k for k, v in self._entries.items() if v.expires_at <= now]:
                self._bytes -= len(self._entries.pop(expired).body)
            if key in self._entries:
                self._entries.move_to_end(key)
                return self._entries[key], True
            payload = self._build(factory)
            if len(payload.body) <= self.max_bytes:
                while self._entries and (
                    len(self._entries) >= self.max_entries
                    or self._bytes + len(payload.body) > self.max_bytes
                ):
                    _, old = self._entries.popitem(last=False)
                    self._bytes -= len(old.body)
                self._entries[key] = payload
                self._bytes += len(payload.body)
            return payload, False

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._bytes = 0


def cached_response(
    request: Request, world: World, key: Hashable, factory: Callable[[], Response]
) -> Response:
    # World identity also protects dependency overrides or world replacement in a
    # running process; schema version and seed guard data-generation changes.
    namespace = (CACHE_VERSION, world.seed, world.built_at, id(world), key)
    payload, hit = request.app.state.runtime.cache.get_or_create(
        namespace, lambda: factory().body
    )
    headers = {
        "ETag": payload.etag,
        "Cache-Control": "private, no-cache",
        "X-Cache": "HIT" if hit else "MISS",
    }
    validators = [
        v.strip().removeprefix("W/")
        for v in request.headers.get("if-none-match", "").split(",")
    ]
    if "*" in validators or payload.etag in validators:
        return Response(status_code=304, headers=headers)
    return Response(payload.body, media_type="application/json", headers=headers)
