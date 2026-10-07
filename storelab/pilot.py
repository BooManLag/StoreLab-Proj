"""StoreLab Pilot: turn the winning simulated experiment into a real-store A/B test plan.

Simulation is a pre-screen, not proof. The plan sizes a test-vs-control pilot with a
simple power calculation on the simulated day-to-day variability of the primary KPI.
"""

from __future__ import annotations

import math

from scipy.stats import norm

from .objective import ObjectiveSpec
from .simulator import SimResult, metric_series
from .store import StoreSpec

ALPHA = 0.05
POWER = 0.80
PRE_PERIOD_DAYS = 14
MIN_DAYS = 14  # always cover two full weekly cycles
MAX_DAYS = 56


def _days_needed(cv: float, lift: float, k: int) -> float:
    """Days so a k-vs-k store comparison detects `lift` (relative) with 80% power at alpha 0.05.
    Per-arm mean over k stores x D days has variance sigma^2/(kD); the difference has 2 sigma^2/(kD)."""
    z = norm.ppf(1 - ALPHA / 2) + norm.ppf(POWER)
    if lift <= 0:
        return math.inf
    return 2.0 * (z * cv / lift) ** 2 / k


def _mde(cv: float, k: int, days: int) -> float:
    z = norm.ppf(1 - ALPHA / 2) + norm.ppf(POWER)
    return z * cv * math.sqrt(2.0 / (k * days))


def _pick_stores(store: StoreSpec, k: int) -> tuple[list[dict], list[dict]]:
    me = next(s for s in store.network if s.store_id == store.store_id)
    others = sorted(
        (s for s in store.network if s.store_id != store.store_id),
        key=lambda s: (s.format != me.format, abs(s.weekly_visitors - me.weekly_visitors)),
    )
    test = [me] + others[1::2]
    control = others[0::2]
    fmt = lambda s: {"store_id": s.store_id, "name": s.name, "format": s.format, "weekly_visitors": s.weekly_visitors}
    return [fmt(s) for s in test[:k]], [fmt(s) for s in control[:k]]


def plan_pilot(store: StoreSpec, objective: ObjectiveSpec, baseline: SimResult, candidate: dict) -> dict:
    sim = candidate["simulation"]
    primary = sim["deltas"]["primary"]
    congestion = sim["deltas"]["congestion"]
    lift = primary["relative_pct"] / 100.0
    _, daily = metric_series(baseline, objective.metric, objective.target_category)
    mu = float(daily.mean())
    sd = float(daily.std(ddof=1)) if len(daily) > 1 else 0.0
    cv = sd / mu if mu > 0 else 0.0

    max_k = max(1, (len(store.network)) // 2)
    choice = None
    for k in range(2, max_k + 1):
        need = _days_needed(cv, lift, k)
        days = max(MIN_DAYS, int(math.ceil(need / 7.0)) * 7) if math.isfinite(need) else MAX_DAYS
        if days <= 28 or k == max_k:
            choice = (k, min(days, MAX_DAYS), need)
            break
    assert choice is not None
    k, days, need = choice
    underpowered = not math.isfinite(need) or need > days
    test, control = _pick_stores(store, k)
    mde = _mde(cv, k, days) * 100.0 if cv > 0 else 0.0

    label = primary["label"]
    target = objective.target_uplift_pct
    criterion_pct = target if target else max(1.0, round(primary["ci_low_pct"], 1))
    plan = {
        "title": f"Test: {candidate['name']}",
        "experiment_id": candidate["id"],
        "changes": candidate["descriptions"],
        "cost_per_store_php": candidate["cost"],
        "total_install_cost_php": candidate["cost"] * k,
        "test_stores": test,
        "control_stores": control,
        "pre_period_days": PRE_PERIOD_DAYS,
        "duration_days": days,
        "primary_kpi": label,
        "success_criterion": (
            f"{label} lift of at least {criterion_pct:g}% versus control stores (difference-in-differences), "
            "with the 95% confidence interval above zero."
        ),
        "guardrails": [
            f"Peak checkout congestion ({store.peak_window[0]:02d}:00–{store.peak_window[1]:02d}:00) "
            f"rises no more than {objective.max_congestion_increase_pct:g}% vs control",
            "Total store revenue is not lower than control",
            "Walkways keep at least "
            f"{store.min_aisle_width_m:.1f} m clear width; emergency egress unobstructed",
        ],
        "expected": {
            "primary_pct": primary["relative_pct"],
            "primary_ci_pct": [primary["ci_low_pct"], primary["ci_high_pct"]],
            "congestion_pct": congestion["relative_pct"],
            "congestion_ci_pct": [congestion["ci_low_pct"], congestion["ci_high_pct"]],
            "revenue_pct": sim["deltas"]["revenue"]["relative_pct"],
        },
        "power": {
            "alpha": ALPHA,
            "power": POWER,
            "daily_kpi_cv": cv,
            "stores_per_arm": k,
            "days_needed_exact": need if math.isfinite(need) else None,
            "minimum_detectable_effect_pct": mde,
            "underpowered": underpowered,
            "method": "Two-arm comparison of store-day means; variability from the simulated baseline.",
        },
        "schedule": [
            f"Days −{PRE_PERIOD_DAYS} to −1: record the baseline in all {2 * k} stores (no changes).",
            f"Day 0: install in test stores ({', '.join(s['store_id'] for s in test)}).",
            f"Days 0–{days - 1}: run; monitor congestion guardrail daily.",
            f"Day {days + 2}: read out with difference-in-differences; feed actual results back to calibrate StoreLab Sim.",
        ],
        "status": "draft",
    }
    if underpowered:
        plan["power"]["note"] = (
            f"The expected effect is small relative to day-to-day noise; even {k} vs {k} stores for {days} days "
            f"only detects about {mde:.1f}% or more."
        )
    return plan
