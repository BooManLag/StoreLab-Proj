"""Application-scoped mutable services; no cross-application pilot/rate state."""

import collections
import threading
import time

from fastapi import HTTPException

from ..config import lab_rate_limit_per_minute
from .cache import ResponseCache


class RuntimeState:
    def __init__(self, cache: ResponseCache):
        self.cache = cache
        self.pilots: dict[str, dict] = {}
        self.pilots_lock = threading.Lock()
        self._runs: collections.deque[float] = collections.deque()
        self._runs_lock = threading.Lock()

    def rate_limit(self) -> None:
        limit = lab_rate_limit_per_minute()
        now = time.monotonic()
        with self._runs_lock:
            while self._runs and now - self._runs[0] >= 60:
                self._runs.popleft()
            if len(self._runs) >= limit:
                retry_after = (
                    max(1, int(60 - (now - self._runs[0])) + 1) if self._runs else 60
                )
                raise HTTPException(
                    429,
                    f"Too many AI Lab runs; limit is {limit} per minute.",
                    headers={"Retry-After": str(retry_after)},
                )
            self._runs.append(now)
