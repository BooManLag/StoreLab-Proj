"""Backend contracts beyond the end-to-end product workflow."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from storelab.api.application import BackendSettings, create_app
from storelab.api.cache import ResponseCache
from storelab.api.routes import store


def test_cache_expiry_lru_byte_budget_and_clear():
    now = [0.0]
    cache = ResponseCache(ttl=5, max_entries=2, max_bytes=4, clock=lambda: now[0])
    assert cache.get_or_create("a", lambda: b"aa")[1] is False
    assert cache.get_or_create("b", lambda: b"bb")[1] is False
    assert cache.get_or_create("a", lambda: pytest.fail("cache miss"))[1] is True
    cache.get_or_create("c", lambda: b"cc")  # a was touched; b must be evicted
    assert cache.get_or_create("b", lambda: b"bb")[1] is False
    now[0] = 5
    assert cache.get_or_create("b", lambda: b"new")[1] is False
    assert cache.get_or_create("oversized", lambda: b"12345")[1] is False
    assert cache.get_or_create("oversized", lambda: b"12345")[1] is False
    cache.clear()
    assert cache.get_or_create("b", lambda: b"bb")[1] is False


def test_cache_failure_is_retried_and_disabled_cache_never_hits():
    cache = ResponseCache()

    def fail():
        raise ValueError("unavailable")

    with pytest.raises(ValueError):
        cache.get_or_create("key", fail)
    assert cache.get_or_create("key", lambda: b"ok")[0].body == b"ok"
    disabled = ResponseCache(ttl=0)
    assert not disabled.get_or_create("key", lambda: b"old")[1]
    assert disabled.get_or_create("key", lambda: b"new")[0].body == b"new"


def test_cache_coalesces_concurrent_misses():
    cache = ResponseCache()
    barrier = Barrier(4)
    calls = []

    def build():
        calls.append(1)
        return b"value"

    def get():
        barrier.wait()
        return cache.get_or_create("same", build)

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: get(), range(4)))
    assert len(calls) == 1
    assert sum(hit for _, hit in results) == 3


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


def test_http_cache_reuses_serialization_and_supports_revalidation(client, monkeypatch):
    original = store._analytics
    calls = []

    def build(w):
        calls.append(1)
        return original(w)

    monkeypatch.setattr(store, "_analytics", build)
    first = client.get("/api/analytics")
    second = client.get("/api/analytics")
    assert first.headers["x-cache"] == "MISS"
    assert second.headers["x-cache"] == "HIT"
    assert first.content == second.content and len(calls) == 1
    etag = first.headers["etag"]
    response = client.get(
        "/api/analytics", headers={"If-None-Match": f'"different", W/{etag}'}
    )
    assert response.status_code == 304 and not response.content
    assert response.headers["cache-control"] == "private, no-cache"
    assert (
        client.get("/api/analytics", headers={"If-None-Match": '"other"'}).status_code
        == 200
    )


def test_cache_query_keys_and_mutable_routes(client):
    one = client.get("/api/journeys/sample?limit=1")
    two = client.get("/api/journeys/sample?limit=2")
    assert len(one.json()["tracks"]) == 1 and len(two.json()["tracks"]) == 2
    assert one.headers["etag"] != two.headers["etag"]
    assert client.get("/api/journeys/sample?limit=1").headers["x-cache"] == "HIT"
    for path in ["/api/pilots", "/api/config", "/api/health"]:
        assert "x-cache" not in client.get(path).headers


@pytest.mark.parametrize(
    "query", ["limit=201", "minutes=0", "start_hour=nan", "start_hour=24", "day=-1"]
)
def test_journey_query_validation(client, query):
    assert client.get("/api/journeys/sample?" + query).status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [("budget_php", -1), ("max_congestion_increase_pct", -1), ("unexpected", 1)],
)
def test_simulation_input_validation(client, field, value):
    body = {
        "changes": [
            {"type": "add_display", "category": "snacks", "slot": "endcap_g3_front"}
        ],
        field: value,
    }
    assert client.post("/api/simulate", json=body).status_code == 422


def test_app_instances_isolate_pilots_rate_limits_and_cache(monkeypatch):
    monkeypatch.setenv("STORELAB_LAB_RUNS_PER_MINUTE", "1")
    app1, app2 = create_app(), create_app()
    with TestClient(app1) as first, TestClient(app2) as second:
        plan = {
            "title": "Test",
            "test_stores": [],
            "control_stores": [],
            "duration_days": 14,
            "primary_kpi": "sales",
        }
        assert first.post("/api/pilots", json={"plan": plan}).status_code == 201
        assert len(first.get("/api/pilots").json()) == 1
        assert second.get("/api/pilots").json() == []
        app1.state.runtime.rate_limit()
        r = first.post("/api/lab/run", json={"objective": "Increase snack sales"})
        assert r.status_code == 429 and int(r.headers["retry-after"]) > 0
        app2.state.runtime.rate_limit()  # independent budget
        assert first.get("/api/store").headers["x-cache"] == "MISS"
        assert second.get("/api/store").headers["x-cache"] == "MISS"


def test_openapi_contains_grouped_routes_and_validation(client):
    schema = client.get("/openapi.json").json()
    assert schema["paths"]["/api/simulate"]["post"]["tags"] == ["experiments"]
    request = schema["components"]["schemas"]["SimulateRequest"]
    assert request["additionalProperties"] is False
    assert request["properties"]["budget_php"]["exclusiveMinimum"] == 0


def test_cache_configuration_rejects_invalid_environment(monkeypatch):
    monkeypatch.setenv("STORELAB_CACHE_TTL_SECONDS", "-1")
    with pytest.raises(ValueError):
        BackendSettings.from_environment()


def test_cache_byte_limit_independent_of_entry_limit():
    cache = ResponseCache(max_entries=100, max_bytes=3)
    cache.get_or_create("first", lambda: b"aa")
    cache.get_or_create("second", lambda: b"bb")
    assert not cache.get_or_create("first", lambda: b"aa")[1]


def test_http_cache_expires_and_world_replacement_invalidates(client):
    from dataclasses import replace

    from storelab.world import get_world

    now = [0.0]
    client.app.state.runtime.cache = ResponseCache(ttl=5, clock=lambda: now[0])
    assert client.get("/api/store").headers["x-cache"] == "MISS"
    assert client.get("/api/store").headers["x-cache"] == "HIT"
    now[0] = 5
    assert client.get("/api/store").headers["x-cache"] == "MISS"
    replacement = replace(get_world(), seed=123)
    client.app.dependency_overrides[get_world] = lambda: replacement
    assert client.get("/api/store").headers["x-cache"] == "MISS"


def test_video_processing_runs_outside_event_loop(client, monkeypatch):
    import threading

    from storelab.api.routes import vision

    event_loop_thread = []

    @client.app.get("/_test/thread")
    async def thread_id():
        return threading.get_ident()

    event_loop_thread.append(client.get("/_test/thread").json())
    processing_thread = []

    def process(*args, **kwargs):
        processing_thread.append(threading.get_ident())
        return {"tracks": []}

    monkeypatch.setattr(vision, "process_video", process)
    calibration = '{"image_points":[[0,0],[1,0],[1,1],[0,1]],"floor_points":[[0,0],[1,0],[1,1],[0,1]]}'
    response = client.post(
        "/api/cv/upload",
        files={"file": ("clip.avi", b"test")},
        data={"calibration": calibration},
    )
    assert response.status_code == 200
    assert processing_thread and processing_thread != event_loop_thread


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_json_input_returns_validation_error(client, value):
    body = (
        '{"changes":[{"type":"add_display","category":"snacks",'
        '"slot":"endcap_g3_front"}],"budget_php":' + value + "}"
    )
    response = client.post(
        "/api/simulate", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "finite_number"
    assert response.json()["detail"][0]["input"] is None
