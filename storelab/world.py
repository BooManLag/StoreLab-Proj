"""The StoreLab world: synthetic history -> analytics -> fitted twin -> simulator, built once and cached."""

from __future__ import annotations

import datetime as dt
import logging
import pickle
import threading
import time
from dataclasses import dataclass

from .analytics import Analytics, analyze
from .config import CACHE_VERSION, DATA_DIR, SEED
from .engine import BehaviorParams, CheckoutParams
from .fit import fit_behavior
from .groundtruth import History, generate_history
from .layout import Layout, baseline_layout
from .simulator import SimResult, Simulator
from .store import CATEGORIES, CATEGORY_LABELS, STORE, StoreSpec

log = logging.getLogger("storelab")


@dataclass
class World:
    store: StoreSpec
    seed: int
    history: History
    analytics: Analytics
    params: BehaviorParams
    checkout: CheckoutParams
    fit_report: dict
    simulator: Simulator
    baseline_layout: Layout
    baseline: SimResult
    calibration: dict
    built_at: str


def _calibration(h: History, a: Analytics, base: SimResult) -> dict:
    """Simulated baseline (fitted twin) vs what was actually observed, per week."""
    obs_w = 7.0 / h.n_days
    sim_w = 7.0 / base.days
    s = a.summary
    rows = [
        ("Transactions / week", s["kpis"]["transactions"] * obs_w, base.kpis["transactions"] * sim_w),
        ("Store conversion", s["kpis"]["conversion_rate"], base.kpis["conversion_rate"]),
        ("Revenue / week (₱)", s["kpis"]["revenue"] * obs_w, base.kpis["revenue"] * sim_w),
        ("Average basket (₱)", s["kpis"]["avg_basket"], base.kpis["avg_basket"]),
        ("Peak checkout congestion", s["kpis"]["peak_checkout_occupancy"], base.congestion["peak_occupancy"]),
    ]
    for c in CATEGORIES:
        rows.append((f"{CATEGORY_LABELS[c]} buyers / week", s["zones"][c]["category_buyers"] * obs_w,
                     base.categories[c]["buyers"] * sim_w))
        rows.append((f"{CATEGORY_LABELS[c]} aisle visitors / week", s["zones"][c]["visitors"] * obs_w,
                     base.categories[c]["visitors"] * sim_w))
    out = []
    for name, obs, sim in rows:
        err = (sim / obs - 1.0) * 100.0 if obs else 0.0
        out.append({"metric": name, "observed": obs, "simulated": sim, "error_pct": err})
    worst = max(abs(r["error_pct"]) for r in out)
    return {"rows": out, "max_abs_error_pct": worst,
            "note": "Twin fitted on 7 observed days; simulated over 28 synthetic days, normalised per week."}


def build_world(seed: int = SEED, store: StoreSpec = STORE) -> World:
    t0 = time.perf_counter()
    history = generate_history(seed, store)
    analytics = analyze(history, seed, store)
    params, checkout, report = fit_behavior(history, analytics, store)
    sim = Simulator(params, checkout, store, seed + 101)
    base_layout = baseline_layout(store)
    baseline = sim.run(base_layout, with_tracks=True)
    calibration = _calibration(history, analytics, baseline)
    log.info("World built in %.1fs", time.perf_counter() - t0)
    return World(store, seed, history, analytics, params, checkout, report, sim, base_layout, baseline, calibration,
                 dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))


def _cache_path(seed: int):
    return DATA_DIR / f"world-{CACHE_VERSION}-{seed}.pkl"


def save_world(w: World) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": CACHE_VERSION, "seed": w.seed, "history": w.history, "analytics": w.analytics,
        "params": w.params, "checkout": w.checkout, "fit_report": w.fit_report, "baseline": w.baseline,
        "calibration": w.calibration, "built_at": w.built_at,
    }
    tmp = _cache_path(w.seed).with_suffix(".tmp")
    with open(tmp, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(_cache_path(w.seed))


def load_world(seed: int = SEED, store: StoreSpec = STORE) -> World | None:
    path = _cache_path(seed)
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            p = pickle.load(f)
        if p.get("version") != CACHE_VERSION or p.get("seed") != seed:
            return None
        sim = Simulator(p["params"], p["checkout"], store, seed + 101)
        base_layout = baseline_layout(store)
        baseline: SimResult = p["baseline"]
        sim._cache[base_layout.signature() + "|tracks"] = baseline
        return World(store, seed, p["history"], p["analytics"], p["params"], p["checkout"], p["fit_report"], sim,
                     base_layout, baseline, p["calibration"], p["built_at"])
    except Exception as exc:  # stale or corrupt cache: rebuild
        log.warning("Ignoring world cache %s: %s", path, exc)
        return None


_world: World | None = None
_lock = threading.Lock()


def get_world() -> World:
    global _world
    if _world is None:
        with _lock:
            if _world is None:
                w = load_world()
                if w is None:
                    w = build_world()
                    try:
                        save_world(w)
                    except OSError as exc:
                        log.warning("Could not write world cache: %s", exc)
                _world = w
    return _world
