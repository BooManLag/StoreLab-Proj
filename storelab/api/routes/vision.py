"""Vision endpoints."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

import cv2
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from ...config import DATA_DIR
from ...cv.pipeline import process_video
from ...cv.render import calibration as demo_calibration
from ...cv.render import demo_clip
from ..dependencies import WorldDep
from ..responses import json_response

MAX_UPLOAD_BYTES = 30 * 1024 * 1024

router = APIRouter(prefix="/api", tags=["vision"])


@router.post("/cv/demo")
def cv_demo() -> Response:
    clip = demo_clip(DATA_DIR / "cv")
    cal = json.loads(clip.calibration_path.read_text())
    result = process_video(
        clip.video_path, cal, clip.background_path, truth_path=clip.truth_path
    )
    result["calibration"] = cal
    result["source"] = (
        "Synthetic demo CCTV clip (rendered from the hidden ground-truth world)"
    )
    return json_response(result)


@router.post("/cv/upload")
async def cv_upload(
    w: WorldDep, file: UploadFile = File(...), calibration: Optional[str] = Form(None)
) -> Response:
    """Process your own fixed-camera clip. Calibration maps 4 image points to 4 floor points (metres)."""
    if calibration:
        try:
            cal = json.loads(calibration)
            assert len(cal["image_points"]) == 4 and len(cal["floor_points"]) == 4
        except Exception as exc:
            raise HTTPException(
                422,
                f"calibration must be JSON with 4 image_points and 4 floor_points: {exc}",
            )
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
            fw, fh = (
                int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )
            cap.release()
            if fw <= 0 or fh <= 0:
                raise HTTPException(422, "Could not read the video")
            cal = {
                "image_points": [[0, 0], [fw, 0], [fw, fh], [0, fh]],
                "floor_points": [
                    [0, 0],
                    [w.store.width, 0],
                    [w.store.width, w.store.height],
                    [0, w.store.height],
                ],
                "time_scale": 1.0,
                "note": "Default calibration assumes a top-down camera framing the whole floor.",
            }
        try:
            result = await run_in_threadpool(
                process_video, Path(tmp), cal, None, store=w.store, max_frames=2400
            )
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


@router.get("/cv/calibration")
def cv_calibration() -> Response:
    return json_response(demo_calibration())
