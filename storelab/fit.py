"""Behavioural model calibration (StoreLab Twin): fit the simulator's agents from observed history.

* Zone choice: conditional logit P(next zone | current zone, visited, segment) with
  segment-specific attraction, walking distance, complement pull, revisit penalty and
  a "done shopping" option. Distances make it transferable to new layouts.
* Dwell: per-segment engagement rates + empirical dwell quantiles per category.
* Purchases: noisy-OR over purchase opportunities (aisle visits, promo-display
  interactions, a small background rate), fitted by maximum likelihood.
* Checkout: service time regressed on basket size, using customers who met an empty queue.

Only observed data is used. The hidden generator parameters are never read here.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from .analytics import ENGAGED_S, Analytics
from .engine import MAX_STEPS, BehaviorParams, CheckoutParams, LayoutContext, quantile_table
from .groundtruth import History
from .store import CATEGORIES, STORE, StoreSpec

RIDGE = 1e-3
DEFAULT_RACK_DWELL_S = 12.0  # assumption: no checkout rack exists in the baseline store to learn from


def _log_sigmoid(z: np.ndarray) -> np.ndarray:
    return -np.logaddexp(0.0, -z)


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return np.exp(_log_sigmoid(z))


# ---------------------------------------------------------------- zone choice
def fit_transitions(a: Analytics, dist: list[list[float]], S: int) -> tuple[dict, dict]:
    C = len(CATEGORIES)
    P = S * C + S + 4
    i_dist, i_comp, i_vis, i_steps = S * C + S, S * C + S + 1, S * C + S + 2, S * C + S + 3
    rows_X, rows_avail, rows_y = [], [], []
    for j in a.journeys:
        s = int(a.cluster[j.idx])
        cats = [v.cat for v in j.visits]
        engs = [v.engaged for v in j.visits]
        visited = np.zeros(C, dtype=bool)
        cur_node, cur_cat, cur_eng = 0, -1, False
        for k in range(len(cats) + 1):
            if k >= MAX_STEPS:
                break  # the trip is forced to end here; not a choice
            X = np.zeros((C + 1, P))
            avail = np.ones(C + 1, dtype=bool)
            for c in range(C):
                if c == cur_cat:
                    avail[c] = False
                    continue
                X[c, s * C + c] = 1.0
                X[c, i_dist] = -dist[cur_node][c]
                X[c, i_comp] = 1.0 if (cur_eng and cur_cat >= 0 and a.comp[cur_cat, c]) else 0.0
                X[c, i_vis] = -1.0 if visited[c] else 0.0
            X[C, S * C + s] = 1.0
            X[C, i_steps] = float(k)
            choice = cats[k] if k < len(cats) else C
            rows_X.append(X)
            rows_avail.append(avail)
            rows_y.append(choice)
            if k < len(cats):
                c = cats[k]
                visited[c] = True
                cur_node, cur_cat, cur_eng = 1 + c, c, engs[k]
    X = np.stack(rows_X)  # (n, A, P)
    avail = np.stack(rows_avail)
    y = np.asarray(rows_y)
    n = len(y)
    idx = np.arange(n)

    def nll(theta: np.ndarray):
        U = X @ theta
        U = np.where(avail, U, -np.inf)
        m = U.max(axis=1, keepdims=True)
        e = np.where(avail, np.exp(U - m), 0.0)
        Z = e.sum(axis=1, keepdims=True)
        p = e / Z
        ll = (U[idx, y] - (m[:, 0] + np.log(Z[:, 0]))).sum()
        grad = (X[idx, y, :] - (p[:, :, None] * X).sum(axis=1)).sum(axis=0)
        return -ll + RIDGE * theta @ theta, -grad + 2 * RIDGE * theta

    theta0 = np.zeros(P)
    theta0[i_dist] = 0.05
    res = minimize(nll, theta0, jac=True, method="L-BFGS-B", options={"maxiter": 500})
    th = res.x
    params = {
        "asc": th[: S * C].reshape(S, C),
        "asc_end": th[S * C: S * C + S],
        "beta_dist": float(th[i_dist]),
        "beta_comp": float(th[i_comp]),
        "beta_visited": float(th[i_vis]),
        "beta_steps": float(th[i_steps]),
    }
    report = {"n_choices": int(n), "log_likelihood": float(-res.fun), "converged": bool(res.success),
              "beta_dist_per_m": params["beta_dist"], "beta_complement": params["beta_comp"],
              "beta_revisit": params["beta_visited"], "beta_done_per_zone": params["beta_steps"]}
    return params, report


# ---------------------------------------------------------------- logistic helper
def _fit_logistic(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    def nll(w):
        z = X @ w
        ll = (y * _log_sigmoid(z) + (1 - y) * _log_sigmoid(-z)).sum()
        p = _sigmoid(z)
        return -ll + RIDGE * w @ w, -(X.T @ (y - p)) + 2 * RIDGE * w

    res = minimize(nll, np.zeros(X.shape[1]), jac=True, method="L-BFGS-B")
    return res.x


# ---------------------------------------------------------------- purchases (noisy-OR)
def fit_purchases(h: History, a: Analytics, S: int) -> tuple[dict, dict]:
    C = len(CATEGORIES)
    # parameter layout: zone_a (S*C), b_dwell, b_engaged, b_primed, disp_a, disp_b_primed, leak_logit
    P = S * C + 6
    i_dw, i_en, i_pr, i_da, i_db, i_lk = S * C, S * C + 1, S * C + 2, S * C + 3, S * C + 4, S * C + 5
    disp_cat = {slot: CATEGORIES.index(cat) for slot, cat in h.layout.displays}
    rows_x, rows_obs = [], []
    y = []
    obs = 0
    for j in a.journeys:
        s = int(a.cluster[j.idx])
        for c in range(C):
            for v in j.visits:
                if v.cat != c:
                    continue
                x = np.zeros(P)
                x[s * C + c] = 1.0
                x[i_dw] = np.log1p(v.dwell / 30.0)
                x[i_en] = 1.0 if v.engaged else 0.0
                x[i_pr] = 1.0 if j.primed_at(c, v.t_enter, a.comp) else 0.0
                rows_x.append(x)
                rows_obs.append(obs)
            for slot, t, eng in j.display_events:
                if eng and disp_cat.get(slot) == c:
                    x = np.zeros(P)
                    x[i_da] = 1.0
                    x[i_db] = 1.0 if j.primed_at(c, t, a.comp) else 0.0
                    rows_x.append(x)
                    rows_obs.append(obs)
            x = np.zeros(P)
            x[i_lk] = 1.0
            rows_x.append(x)
            rows_obs.append(obs)
            y.append(1.0 if j.bought[c] else 0.0)
            obs += 1
    X = np.vstack(rows_x)
    o = np.asarray(rows_obs)
    yv = np.asarray(y)

    def nll(theta: np.ndarray):
        z = X @ theta
        ls_neg = _log_sigmoid(-z)  # log(1 - p_k)
        L0 = np.bincount(o, weights=ls_neg, minlength=obs)  # log P(no purchase)
        L0 = np.minimum(L0, -1e-12)
        ll = np.where(yv > 0, np.log(-np.expm1(L0)), L0).sum()
        coef = np.where(yv > 0, -np.exp(L0) / (-np.expm1(L0)), 1.0)  # d ll / d L0
        dL0 = -_sigmoid(z)  # d log(1 - p_k) / d z_k
        grad = X.T @ (coef[o] * dL0)
        return -ll + RIDGE * theta @ theta, -grad + 2 * RIDGE * theta

    theta0 = np.zeros(P)
    theta0[: S * C] = -3.0
    theta0[i_lk] = -6.0
    theta0[i_da] = -2.0
    res = minimize(nll, theta0, jac=True, method="L-BFGS-B", options={"maxiter": 1000})
    th = res.x
    params = {
        "zone_a": th[: S * C].reshape(S, C),
        "zone_b_dwell": float(th[i_dw]),
        "zone_b_engaged": float(th[i_en]),
        "zone_b_primed": float(th[i_pr]),
        "disp_buy_a": float(th[i_da]),
        "disp_buy_b_primed": float(th[i_db]),
        "leak": float(1.0 / (1.0 + np.exp(-th[i_lk]))),
    }
    report = {"n_journey_category_pairs": int(obs), "n_opportunities": int(len(o)),
              "log_likelihood": float(-res.fun), "converged": bool(res.success),
              "dwell_coef": params["zone_b_dwell"], "engaged_coef": params["zone_b_engaged"],
              "primed_coef": params["zone_b_primed"], "display_buy_intercept": params["disp_buy_a"],
              "display_buy_primed_coef": params["disp_buy_b_primed"]}
    return params, report


def fit_display_engagement(h: History, a: Analytics) -> tuple[float, float, int]:
    disp_cat = {slot: CATEGORIES.index(cat) for slot, cat in h.layout.displays}
    rows, ys = [], []
    for j in a.journeys:
        for slot, t, eng in j.display_events:
            c = disp_cat.get(slot)
            if c is None:
                continue
            rows.append([1.0, 1.0 if j.primed_at(c, t, a.comp) else 0.0])
            ys.append(1.0 if eng else 0.0)
    w = _fit_logistic(np.asarray(rows), np.asarray(ys))
    return float(w[0]), float(w[1]), len(ys)


def fit_checkout(h: History, a: Analytics, store: StoreSpec) -> tuple[CheckoutParams, dict]:
    """Service time from customers who arrived at an idle counter (dwell == service)."""
    rows = sorted(
        ((j.day, j.checkout_enter, j.checkout_exit, j.items) for j in a.journeys
         if j.checkout_enter is not None and j.items > 0),
        key=lambda r: (r[0], r[1]),
    )
    xs, ys = [], []
    prev_day, prev_exit = -1, -np.inf
    for day, t0, t1, items in rows:
        if day != prev_day:
            prev_exit = -np.inf
        if t0 >= prev_exit + 1.0:  # counter free when they arrived
            xs.append(items)
            ys.append(t1 - t0)
        prev_day, prev_exit = day, max(prev_exit, t1)
    X = np.column_stack([np.ones(len(xs)), np.asarray(xs, dtype=float)])
    beta, *_ = np.linalg.lstsq(X, np.asarray(ys), rcond=None)
    resid = np.asarray(ys) - X @ beta
    params = CheckoutParams(
        base_s=float(beta[0]),
        per_item_s=float(beta[1]),
        sd_s=float(resid.std(ddof=2)),
        lanes=store.checkout_lanes,
        rack_dwell_s=DEFAULT_RACK_DWELL_S,
    )
    report = {"n_idle_counter_customers": len(xs), "base_s": params.base_s, "per_item_s": params.per_item_s,
              "sd_s": params.sd_s, "lanes": params.lanes,
              "rack_dwell_s": params.rack_dwell_s, "rack_dwell_source": "assumption (no rack in baseline data)"}
    return params, report


def fit_behavior(h: History, a: Analytics, store: StoreSpec = STORE) -> tuple[BehaviorParams, CheckoutParams, dict]:
    C = len(CATEGORIES)
    S = len(a.cluster_info)
    N = len(a.journeys)

    # ---- arrivals and segment mix by hour
    hours = np.clip((h.t_arrive // 3600).astype(int), 0, 23)
    hour_counts = np.bincount(hours, minlength=24).astype(float)
    hour_weights = hour_counts / hour_counts.sum()
    seg_hour = np.zeros((24, S))
    for hr, s in zip(hours, a.cluster):
        seg_hour[hr, s] += 1
    seg_hour = (seg_hour + 0.5) / (seg_hour + 0.5).sum(axis=1, keepdims=True)

    # ---- zone choice
    ctx = LayoutContext(store, h.layout, 0.9)
    trans, trans_report = fit_transitions(a, ctx.dist, S)

    # ---- engagement & dwell
    visits = np.zeros((S, C))
    engaged = np.zeros((S, C))
    dwell_eng = [[] for _ in range(C)]
    dwell_pass = [[] for _ in range(C)]
    for j in a.journeys:
        s = int(a.cluster[j.idx])
        for v in j.visits:
            visits[s, v.cat] += 1
            engaged[s, v.cat] += v.engaged
            (dwell_eng if v.engaged else dwell_pass)[v.cat].append(v.dwell)
    cat_rate = engaged.sum(axis=0) / np.maximum(visits.sum(axis=0), 1)
    p_engage = (engaged + 2.0 * cat_rate) / (visits + 2.0)
    dq_eng = [quantile_table(np.asarray(d) if d else np.array([ENGAGED_S, 2 * ENGAGED_S])) for d in dwell_eng]
    dq_pass = [quantile_table(np.asarray(d) if d else np.array([2.0, ENGAGED_S - 1])) for d in dwell_pass]

    # ---- purchases and displays
    purch, purch_report = fit_purchases(h, a, S)
    de_a, de_b, de_n = fit_display_engagement(h, a)

    # ---- basket composition from POS
    sku_ids, sku_price, sku_cum, qty_cum = [], [], [], []
    tl_cat = np.asarray(h.tl_category)
    tl_sku = np.asarray(h.tl_sku)
    for cat in CATEGORIES:
        m = tl_cat == cat
        prods = store.products_in(cat)
        ids = [p.sku for p in prods]
        counts = np.array([(tl_sku[m] == sid).sum() for sid in ids], dtype=float) + 0.5
        prices = [float(h.tl_price[m][tl_sku[m] == sid].mean()) if (tl_sku[m] == sid).any() else p.price
                  for sid, p in zip(ids, prods)]
        qty = np.clip(h.tl_qty[m], 1, 3)
        qcounts = np.array([(qty == q).sum() for q in (1, 2, 3)], dtype=float) + 0.5
        sku_ids.append(ids)
        sku_price.append(prices)
        sku_cum.append(list(np.cumsum(counts / counts.sum())))
        qty_cum.append(list(np.cumsum(qcounts / qcounts.sum())))

    checkout, checkout_report = fit_checkout(h, a, store)

    params = BehaviorParams(
        segment_ids=[f"segment_{k}" for k in range(S)],
        segment_labels=[c["name"] for c in a.cluster_info],
        hour_weights=hour_weights,
        segment_given_hour=seg_hour,
        asc=trans["asc"],
        asc_end=trans["asc_end"],
        beta_dist=trans["beta_dist"],
        beta_comp=trans["beta_comp"],
        beta_visited=trans["beta_visited"],
        beta_steps=trans["beta_steps"],
        comp=a.comp.copy(),
        p_engage=p_engage,
        dwell_engaged_q=dq_eng,
        dwell_passing_q=dq_pass,
        zone_a=purch["zone_a"],
        zone_b_dwell=purch["zone_b_dwell"],
        zone_b_engaged=purch["zone_b_engaged"],
        zone_b_primed=purch["zone_b_primed"],
        disp_engage_a=de_a,
        disp_engage_b_primed=de_b,
        disp_buy_a=purch["disp_buy_a"],
        disp_buy_b_primed=purch["disp_buy_b_primed"],
        leak=purch["leak"],
        sku_ids=sku_ids,
        sku_price=sku_price,
        sku_cum=sku_cum,
        qty_cum=qty_cum,
        walk_speed=0.9,
        engaged_threshold_s=ENGAGED_S,
        shopper_noise_sd=0.0,
    )
    report = {
        "segments": [c["name"] for c in a.cluster_info],
        "journeys": N,
        "transition_model": trans_report,
        "purchase_model": purch_report,
        "display_engagement": {"intercept": de_a, "primed_coef": de_b, "n_display_passes": de_n},
        "checkout_model": checkout_report,
        "complements": [[CATEGORIES[x], CATEGORIES[y]] for x in range(C) for y in range(x + 1, C) if a.comp[x, y]],
    }
    return params, checkout, report
