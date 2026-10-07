import json

import pytest

from storelab.config import DATA_DIR
from storelab.cv.pipeline import process_video
from storelab.cv.render import demo_clip


@pytest.fixture(scope="module")
def clip():
    return demo_clip(DATA_DIR / "cv")


def test_pipeline_recovers_anonymous_trajectories(clip):
    cal = json.loads(clip.calibration_path.read_text())
    r = process_video(clip.video_path, cal, clip.background_path, truth_path=clip.truth_path)
    ev = r["evaluation"]
    assert r["frames"] == 360
    assert ev["recall"] >= 0.85
    assert ev["mean_position_error_m"] < 0.3
    assert len(r["tracks"]) <= 2 * ev["people_in_clip"]
    assert all(t["anonymous_track_id"].startswith("anon_") for t in r["tracks"])
    assert any(t["journey"] for t in r["tracks"])
    assert r["previews"] and r["previews"][0]["jpeg_base64"]


def test_pipeline_works_without_reference_plate(clip):
    cal = json.loads(clip.calibration_path.read_text())
    r = process_video(clip.video_path, cal, None, truth_path=clip.truth_path)
    assert "median" in r["background"]
    assert r["evaluation"]["recall"] >= 0.8


def test_track_ids_are_random_per_run(clip):
    cal = json.loads(clip.calibration_path.read_text())
    a = {t["anonymous_track_id"] for t in process_video(clip.video_path, cal, clip.background_path)["tracks"]}
    b = {t["anonymous_track_id"] for t in process_video(clip.video_path, cal, clip.background_path)["tracks"]}
    assert a.isdisjoint(b)
