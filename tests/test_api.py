import json

import pytest
from fastapi.testclient import TestClient

from storelab.config import DATA_DIR
from storelab.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_config_store(client):
    assert client.get("/api/health").json()["status"] == "ok"
    cfg = client.get("/api/config").json()
    assert cfg["synthetic_data"] is True and cfg["agent"]["mode"] == "offline"
    store = client.get("/api/store").json()
    assert len(store["aisles"]) == 4 and len(store["displays"]) == 9
    assert store["baseline_layout"]["category_slot"]["beverages"] == "aisle_4"


def test_web_app_and_modules_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "StoreLab" in r.text
    assert client.head("/").status_code == 200
    js = client.get("/static/js/app.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert js.headers["cache-control"] == "no-cache"


def test_analytics_is_valid_json_without_nans(client):
    r = client.get("/api/analytics")
    assert r.status_code == 200
    body = json.loads(r.text)  # strict: NaN would fail here
    assert len(body["heatmap"]) == 30 and body["summary"]["kpis"]["visitors"] == 10_000


def test_journey_sample(client):
    tracks = client.get("/api/journeys/sample").json()["tracks"]
    assert tracks and all(len(t["points"][0]) == 3 for t in tracks)


def test_lab_run_streams_sse_to_completion(client):
    events = []
    with client.stream("POST", "/api/lab/run", json={"objective": "Increase snack sales by 10%. Budget ₱30k.",
                                                      "rounds": 1}) as r:
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
        for line in r.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    assert events[0]["type"] == "run" and events[-1]["type"] == "done"
    assert events[-1]["recommendation"] is not None


def test_lab_run_input_validation(client):
    assert client.post("/api/lab/run", json={"objective": ""}).status_code == 422
    assert client.post("/api/lab/run", json={"objective": "x" * 601}).status_code == 422
    assert client.post("/api/lab/run", json={"objective": "snacks", "rounds": 5}).status_code == 422


def test_simulate_endpoint(client):
    ok = client.post("/api/simulate", json={"changes": [{"type": "add_display", "category": "snacks",
                                                         "slot": "endcap_g3_front"}]})
    assert ok.status_code == 200 and ok.json()["simulation"]["deltas"]["primary"]["relative_pct"] > 0
    bad = client.post("/api/simulate", json={"changes": [{"type": "swap_categories", "category_a": "beverages",
                                                          "category_b": "snacks"}]})
    assert bad.status_code == 422 and not bad.json()["validation"]["valid"]


def test_pilot_lifecycle(client):
    plan = {"title": "Test: x", "test_stores": [], "control_stores": [], "duration_days": 14, "primary_kpi": "k"}
    r = client.post("/api/pilots", json={"plan": plan})
    assert r.status_code == 201 and r.json()["status"] == "scheduled"
    assert any(p["pilot_id"] == r.json()["pilot_id"] for p in client.get("/api/pilots").json())
    assert client.post("/api/pilots", json={"plan": {"title": "x"}}).status_code == 422


def test_csv_export(client):
    r = client.get("/api/data/transactions.csv")
    assert r.status_code == 200 and r.text.startswith("transaction_id,")
    assert client.get("/api/data/secrets.csv").status_code == 404


def test_cv_demo_and_upload(client):
    demo = client.post("/api/cv/demo").json()
    assert demo["evaluation"]["recall"] >= 0.85
    video = (DATA_DIR / "cv" / "demo_cctv.avi").read_bytes()
    cal = (DATA_DIR / "cv" / "demo_cctv_calibration.json").read_text()
    up = client.post("/api/cv/upload", files={"file": ("clip.avi", video, "video/x-msvideo")},
                     data={"calibration": cal})
    assert up.status_code == 200 and len(up.json()["tracks"]) > 5
    bad = client.post("/api/cv/upload", files={"file": ("x.mp4", b"not a video", "video/mp4")})
    assert bad.status_code == 422


def test_tracks_endpoint_same_shoppers_every_layout(client):
    base = client.get("/api/store").json()["baseline_layout"]
    a = client.post("/api/tracks", json={"category_slot": base["category_slot"], "displays": base["displays"]}).json()
    disp = dict(base["displays"], endcap_g3_front="snacks")
    b = client.post("/api/tracks", json={"category_slot": base["category_slot"], "displays": disp}).json()
    assert [t["id"] for t in a["tracks"]] == [t["id"] for t in b["tracks"]]
    same = sum(ta["points"] == tb["points"] for ta, tb in zip(a["tracks"], b["tracks"]))
    assert same >= len(a["tracks"]) // 2, "an endcap should leave most shoppers' paths untouched"
    bad = client.post("/api/tracks", json={"category_slot": base["category_slot"], "displays": {"exit_stand": "snacks"}})
    assert bad.status_code == 422


def test_pilot_plan_for_any_option_and_overrides(client):
    events = []
    with client.stream("POST", "/api/lab/run", json={"objective": "Increase snack sales by 10%. Budget ₱30k.",
                                                      "mode": "fast", "overrides": {"budget_php": 40000}}) as r:
        for line in r.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    done = events[-1]
    assert done["objective"]["budget_php"] == 40000
    alt = next(c for c in done["candidates"] if c["simulation"] and c["id"] != done["recommendation"]["candidate_id"])
    plan = client.post("/api/pilot/plan", json={"objective": done["objective"], "candidate": alt})
    assert plan.status_code == 200 and plan.json()["experiment_id"] == alt["id"]
    assert client.post("/api/pilot/plan", json={"objective": done["objective"], "candidate": {"id": "X"}}).status_code == 422