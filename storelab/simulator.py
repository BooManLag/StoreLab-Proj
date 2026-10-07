"""StoreLab Sim: run synthetic shopper journeys on a layout and compare against the baseline.

Gemini never computes these numbers. The simulator uses only the behaviour model
fitted from observed history (fit.py), and every layout is evaluated on the same
synthetic shoppers (common random numbers). Confidence intervals come from the paired
day-level differences.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field

import numpy as np
from scipy import stats

from .engine import (SRC_DISPLAY, SRC_RACK, SRC_ZONE, BehaviorParams, CheckoutParams, EngineOutput, heatmap,
                     make_draws, run_engine, script_to_track)
from .layout import Layout
from .store import CATEGORIES, CATEGORY_LABELS, StoreSpec

# Four synthetic weeks of traffic (~1,430 shoppers/day). Paired day-level CIs over 28 days
# are tight enough (about ±1-3 pts) for accept/reject decisions not to hinge on noise.
N_SIM = 40_000
SIM_DAYS = 28

# metric id -> (label, unit, higher_is_better)
METRICS: dict[str, tuple[str, str, bool]] = {
    "category_revenue": ("Category revenue", "PHP", True),
    "category_units": ("Category units", "units", True),
    "category_attachment": ("Category attachment rate", "share of transactions", True),
    "total_revenue": ("Store revenue", "PHP", True),
    "basket_value": ("Average basket value", "PHP", True),
    "conversion": ("Store conversion", "share of visitors", True),
    "checkout_congestion": ("Peak checkout congestion", "avg shoppers in checkout area, 17:00–19:00", False),
}


@dataclass
class SimResult:
    signature: str
    layout: Layout
    n: int
    days: int
    kpis: dict
    categories: dict
    congestion: dict
    displays: list
    daily: dict  # key -> np.ndarray(days)
    heat: np.ndarray
    journey: dict
    tracks: list = field(default_factory=list)
    leg_counts: dict = field(default_factory=dict)  # (from_anchor, to_anchor) -> walks

    def to_json(self, include_heat: bool = True) -> dict:
        out = {
            "signature": self.signature,
            "layout": {"category_slot": self.layout.cat_slot, "displays": self.layout.display_map},
            "simulated_journeys": self.n,
            "days": self.days,
            "kpis": self.kpis,
            "categories": self.categories,
            "congestion": self.congestion,
            "displays": self.displays,
            "journey": self.journey,
        }
        if include_heat:
            out["heatmap"] = np.round(self.heat, 1).tolist()
        if self.tracks:
            out["tracks"] = self.tracks
        return out


def _peak_occupancy(out: EngineOutput, lo: float, hi: float) -> tuple[np.ndarray, np.ndarray]:
    went = out.went_checkout
    occ = np.zeros(out.days)
    waits = np.zeros(out.days)
    for d in range(out.days):
        m = went & (out.day == d)
        a = np.clip(out.t_queue[m], lo, hi)
        b = np.clip(out.t_depart[m], lo, hi)
        occ[d] = (b - a).sum() / (hi - lo)
        pk = m & (out.t_queue >= lo) & (out.t_queue < hi)
        waits[d] = out.wait[pk].mean() if pk.any() else 0.0
    return occ, waits


def summarize(out: EngineOutput, params: BehaviorParams, store: StoreSpec, tracks: list | None = None) -> SimResult:
    n, days, C = out.n, out.days, len(CATEGORIES)
    went = out.went_checkout
    bought = out.buy_qty > 0
    lo, hi = store.peak_window[0] * 3600.0, store.peak_window[1] * 3600.0
    occ, waits = _peak_occupancy(out, lo, hi)
    pk = went & (out.t_queue >= lo) & (out.t_queue < hi)

    daily: dict[str, np.ndarray] = {}
    day = out.day
    daily["visitors"] = np.bincount(day, minlength=days).astype(float)
    daily["transactions"] = np.bincount(day[went], minlength=days).astype(float)
    rev_i = out.buy_rev.sum(axis=1)
    daily["revenue"] = np.bincount(day, weights=rev_i, minlength=days)
    daily["peak_congestion"] = occ
    daily["peak_wait"] = waits
    for c, cat in enumerate(CATEGORIES):
        daily[f"revenue_{cat}"] = np.bincount(day, weights=out.buy_rev[:, c], minlength=days)
        daily[f"units_{cat}"] = np.bincount(day, weights=out.buy_qty[:, c], minlength=days).astype(float)
        daily[f"buyers_{cat}"] = np.bincount(day[bought[:, c]], minlength=days).astype(float)

    tx = int(went.sum())
    revenue = float(rev_i.sum())
    kpis = {
        "visitors": n,
        "transactions": tx,
        "conversion_rate": tx / n,
        "revenue": revenue,
        "avg_basket": revenue / tx if tx else 0.0,
        "items_per_basket": float(out.buy_qty.sum() / tx) if tx else 0.0,
    }
    v_cat = np.asarray(out.v_cat, dtype=int)
    v_shop = np.asarray(out.v_shopper, dtype=int)
    v_eng = np.asarray(out.v_engaged, dtype=bool)
    categories = {}
    for c, cat in enumerate(CATEGORIES):
        visitors = np.unique(v_shop[v_cat == c])
        engaged = np.unique(v_shop[(v_cat == c) & v_eng])
        categories[cat] = {
            "label": CATEGORY_LABELS[cat],
            "slot": out.layout.cat_slot[cat],
            "revenue": float(out.buy_rev[:, c].sum()),
            "units": int(out.buy_qty[:, c].sum()),
            "buyers": int(bought[:, c].sum()),
            "attachment_rate": float(bought[went, c].mean()) if tx else 0.0,
            "visitors": int(len(visitors)),
            "engaged": int(len(engaged)),
            "zone_purchases": int((out.buy_src[:, c] == SRC_ZONE).sum()),
            "display_purchases": int((out.buy_src[:, c] == SRC_DISPLAY).sum()),
            "rack_purchases": int((out.buy_src[:, c] == SRC_RACK).sum()),
        }
    congestion = {
        "peak_occupancy": float(occ.mean()),
        "peak_mean_wait_s": float(out.wait[pk].mean()) if pk.any() else 0.0,
        "peak_p90_wait_s": float(np.percentile(out.wait[pk], 90)) if pk.any() else 0.0,
        "peak_window": f"{store.peak_window[0]:02d}:00–{store.peak_window[1]:02d}:00",
    }
    d_slot = np.asarray(out.d_slot, dtype=int)
    d_eng = np.asarray(out.d_engaged, dtype=bool)
    d_bought = np.asarray(out.d_bought, dtype=bool)
    d_mask = np.asarray(out.d_primed_mask, dtype=int)
    occupied = out.layout.display_map
    displays = []
    for k, d in enumerate(store.displays):
        m = d_slot == k
        displays.append({
            "slot": d.id,
            "label": d.label,
            "category": occupied.get(d.id),
            "passes": int(m.sum()),
            "engaged": int((m & d_eng).sum()),
            "purchases": int((m & d_bought).sum()),
            "primed_passes": {cat: int((m & ((d_mask >> c) & 1).astype(bool)).sum()) for c, cat in enumerate(CATEGORIES)},
        })
    journey = {
        "avg_length_m": float(out.distance.mean()),
        "avg_duration_s": float(np.mean(out.t_exit - out.arrival)),
        "avg_zones": float(len(out.v_cat) / n),
    }
    heat = heatmap(out, params.walk_speed) / days
    return SimResult(out.layout.signature(), out.layout, n, days, kpis, categories, congestion, displays, daily,
                     heat, journey, tracks or [], dict(out.leg_counts))


def metric_series(res: SimResult, metric: str, category: str | None) -> tuple[float, np.ndarray]:
    """Return (overall value, per-day values) for a metric."""
    dly = res.daily
    if metric in ("category_revenue", "category_units", "category_attachment") and category not in CATEGORIES:
        raise ValueError(f"Metric {metric} needs a category")
    if metric == "category_revenue":
        s = dly[f"revenue_{category}"]
        return float(s.sum()), s
    if metric == "category_units":
        s = dly[f"units_{category}"]
        return float(s.sum()), s
    if metric == "category_attachment":
        b, t = dly[f"buyers_{category}"], dly["transactions"]
        return float(b.sum() / t.sum()) if t.sum() else 0.0, np.divide(b, t, out=np.zeros_like(b), where=t > 0)
    if metric == "total_revenue":
        return float(dly["revenue"].sum()), dly["revenue"]
    if metric == "basket_value":
        r, t = dly["revenue"], dly["transactions"]
        return float(r.sum() / t.sum()) if t.sum() else 0.0, np.divide(r, t, out=np.zeros_like(r), where=t > 0)
    if metric == "conversion":
        t, v = dly["transactions"], dly["visitors"]
        return float(t.sum() / v.sum()), np.divide(t, v, out=np.zeros_like(t), where=v > 0)
    if metric == "checkout_congestion":
        s = dly["peak_congestion"]
        return float(s.mean()), s
    raise ValueError(f"Unknown metric {metric}")


_CATEGORY_METRIC_NOUN = {"category_revenue": "sales", "category_units": "units", "category_attachment": "attachment rate"}


_SINGULAR_LABEL = {"bakery": "Bakery", "coffee": "Coffee", "snacks": "Snack", "beverages": "Beverage"}


def metric_label(metric: str, category: str | None) -> str:
    if metric in _CATEGORY_METRIC_NOUN and category in _SINGULAR_LABEL:
        return f"{_SINGULAR_LABEL[category]} {_CATEGORY_METRIC_NOUN[metric]}"
    return METRICS[metric][0]


def relative_delta(base: SimResult, cand: SimResult, metric: str, category: str | None) -> dict:
    """Point estimate and 95% CI of the relative change, paired by simulated day."""
    b_tot, b_day = metric_series(base, metric, category)
    c_tot, c_day = metric_series(cand, metric, category)
    point = (c_tot / b_tot - 1.0) if b_tot else 0.0
    ok = b_day > 0
    rel = c_day[ok] / b_day[ok] - 1.0
    if len(rel) >= 2 and np.any(rel != rel[0]):
        se = rel.std(ddof=1) / np.sqrt(len(rel))
        t = stats.t.ppf(0.975, len(rel) - 1)
        lo, hi = point - t * se, point + t * se
    else:
        lo = hi = point
    return {
        "metric": metric,
        "category": category,
        "label": metric_label(metric, category),
        "baseline": b_tot,
        "candidate": c_tot,
        "relative_pct": 100.0 * point,
        "ci_low_pct": 100.0 * lo,
        "ci_high_pct": 100.0 * hi,
        "higher_is_better": METRICS[metric][2],
    }


class Simulator:
    def __init__(self, params: BehaviorParams, checkout: CheckoutParams, store: StoreSpec, seed: int,
                 n: int = N_SIM, days: int = SIM_DAYS):
        self.params = params
        self.checkout = checkout
        self.store = store
        self.n = n
        self.days = days
        self.draws = make_draws(n, days, params.hour_weights, len(store.displays), seed)
        self._cache: OrderedDict[str, SimResult] = OrderedDict()
        self._lock = threading.Lock()
        # Shoppers used for route animations: day 0, arriving 17:00-17:40.
        win = np.nonzero((self.draws.day == 0) & (self.draws.arrival >= 17 * 3600) & (self.draws.arrival < 17 * 3600 + 2400))[0]
        self.track_ids = [int(i) for i in win[:70]]

    def run(self, layout: Layout, with_tracks: bool = False) -> SimResult:
        key = layout.signature() + ("|tracks" if with_tracks else "")
        # A run with tracks has identical metrics, so it also satisfies a request without tracks.
        candidates = [key] if with_tracks else [key, key + "|tracks"]
        with self._lock:
            for k in candidates:
                if k in self._cache:
                    self._cache.move_to_end(k)
                    return self._cache[k]
        script_ids = set(self.track_ids) if with_tracks else None
        out = run_engine(self.params, self.checkout, self.store, layout, self.draws, script_ids=script_ids)
        tracks = self._tracks(out) if with_tracks else None
        res = summarize(out, self.params, self.store, tracks)
        with self._lock:
            self._cache[key] = res
            while len(self._cache) > 64:
                self._cache.popitem(last=False)
        return res

    def _tracks(self, out: EngineOutput) -> list:
        t0 = 17 * 3600.0
        tracks = []
        for i in self.track_ids:
            # Per-shopper seed: the same shopper wanders identically in every layout unless their trip changes.
            rng = np.random.default_rng(7_000 + i)
            tr = script_to_track(out, i, self.params.walk_speed, rng=rng)
            if len(tr) == 0:
                continue
            tr = tr[::2] if len(tr) > 4 else tr
            pts = [[round(float(t - t0), 1), round(float(x), 2), round(float(y), 2)] for t, x, y in tr]
            tracks.append({"id": int(i), "bought": bool(out.went_checkout[i]), "points": pts})
        return tracks

    def compare(self, base: SimResult, cand: SimResult, primary_metric: str, primary_category: str | None) -> dict:
        deltas = {
            "primary": relative_delta(base, cand, primary_metric, primary_category),
            "revenue": relative_delta(base, cand, "total_revenue", None),
            "basket": relative_delta(base, cand, "basket_value", None),
            "conversion": relative_delta(base, cand, "conversion", None),
            "congestion": relative_delta(base, cand, "checkout_congestion", None),
        }
        if primary_category:
            deltas["attachment"] = relative_delta(base, cand, "category_attachment", primary_category)
            deltas["category_revenue"] = relative_delta(base, cand, "category_revenue", primary_category)
        deltas["peak_wait_s"] = {
            "baseline": base.congestion["peak_mean_wait_s"],
            "candidate": cand.congestion["peak_mean_wait_s"],
        }
        return deltas
