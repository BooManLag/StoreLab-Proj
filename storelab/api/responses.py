"""Strict JSON serialization for scientific Python values."""

import json
import math
from typing import Any

import numpy as np
from fastapi.responses import Response


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
    return json.dumps(
        _clean(data), ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def json_response(data: Any, status: int = 200) -> Response:
    return Response(
        content=dumps(data), media_type="application/json", status_code=status
    )
