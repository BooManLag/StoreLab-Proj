"""Pre-build everything expensive (synthetic world, fitted twin, baseline run, demo CCTV clip).

Runs at Docker build time so a Cloud Run cold start only loads a cache:
    python -m storelab.bootstrap
"""

from __future__ import annotations

import json
import time

from .config import DATA_DIR
from .cv.pipeline import process_video
from .cv.render import demo_clip
from .world import get_world


def main() -> None:
    t0 = time.perf_counter()
    w = get_world()
    print(f"world: {w.history.n_journeys:,} journeys, {w.history.n_transactions:,} transactions, "
          f"calibration max error {w.calibration['max_abs_error_pct']:.1f}%")
    clip = demo_clip(DATA_DIR / "cv")
    r = process_video(clip.video_path, json.loads(clip.calibration_path.read_text()), clip.background_path,
                      truth_path=clip.truth_path, preview_frames=1)
    print(f"cv: {len(r['tracks'])} tracks, recall {r['evaluation']['recall']:.0%}")
    print(f"bootstrap done in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
