"""Store Intelligence ("what's happening?"): journeys + POS -> funnels, transitions, clusters, heatmap.

Only observed data is used: anonymous zone/display events, 2 Hz trajectories and POS
baskets. POS baskets are linked to journeys by time-window matching at the checkout
(no identity needed).
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment

from .geometry import CELL
from .groundtruth import History
from .store import CATEGORIES, CATEGORY_LABELS, STORE, StoreSpec

ENGAGED_S = 20.0
_SINGULAR = {"bakery": "bakery", "coffee": "coffee", "snacks": "snack", "beverages": "beverage"}
MATCH_WINDOW_S = 90.0
N_CLUSTERS = 4


@dataclass
class Visit:
    cat: int
    t_enter: float
    t_exit: float
    dwell: float
    engaged: bool


@dataclass
class Journey:
    idx: int
    day: int
    t_arrive: float
    visits: list[Visit]
    checkout_enter: float | None
    checkout_exit: float | None
    bought: np.ndarray  # (C,) bool, from matched POS basket
    revenue: float
    items: int
    display_events: list[tuple[str, float, bool]]  # (slot, time, engaged)

    def primed_at(self, cat: int, t: float, comp: np.ndarray) -> bool:
        for v in self.visits:
            if v.engaged and v.t_exit <= t and comp[v.cat, cat] and v.cat != cat:
                return True
        return False


@dataclass
class Analytics:
    journeys: list[Journey]
    comp: np.ndarray  # (C, C) complement relation learned from POS
    lift: np.ndarray  # (C, C)
    match: dict
    cluster: np.ndarray  # (N,) journey cluster
    cluster_info: list[dict]
    summary: dict = field(default_factory=dict)  # JSON-ready dashboard payload
    heatmap: np.ndarray | None = None


# ---------------------------------------------------------------- POS join
def match_transactions(h: History) -> tuple[np.ndarray, dict]:
    """Link each POS transaction to the journey whose checkout visit ended closest in time."""
    co = np.array([z == "checkout" for z in h.ze_zone])
    co_track = h.ze_track[co]
    co_exit = h.ze_exit[co]
    co_day = h.day[co_track]
    tx_track = np.full(h.n_transactions, -1, dtype=int)
    for d in range(h.n_days):
        jt = np.nonzero(co_day == d)[0]
        tt = np.nonzero(h.tx_day == d)[0]
        if len(jt) == 0 or len(tt) == 0:
            continue
        cost = np.abs(h.tx_time[tt][:, None] - co_exit[jt][None, :])
        big = cost > MATCH_WINDOW_S
        cost = np.where(big, 1e6, cost)
        rows, cols = linear_sum_assignment(cost)
        ok = ~big[rows, cols]
        tx_track[tt[rows[ok]]] = co_track[jt[cols[ok]]]
    matched = tx_track >= 0
    stats = {
        "transactions": int(h.n_transactions),
        "matched": int(matched.sum()),
        "match_rate": float(matched.mean()) if h.n_transactions else 0.0,
        "window_s": MATCH_WINDOW_S,
        "method": "One-to-one assignment on |payment time - checkout-zone exit time| (Hungarian), per day",
    }
    truth = h.truth.get("tx_track")
    if truth is not None and len(truth) == len(tx_track):
        stats["accuracy_vs_synthetic_truth"] = float((tx_track[matched] == truth[matched]).mean()) if matched.any() else 0.0
    return tx_track, stats


def basket_lift(h: History, tx_track: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Category co-purchase lift over baskets, plus P(B|A) / P(B|not A)."""
    C = len(CATEGORIES)
    has = np.zeros((h.n_transactions, C), dtype=bool)
    cat_idx = {c: i for i, c in enumerate(CATEGORIES)}
    for row, cat in zip(h.tl_tx, h.tl_category):
        has[row, cat_idx[cat]] = True
    p = has.mean(axis=0)
    lift = np.ones((C, C))
    rel = np.ones((C, C))
    for a in range(C):
        for b in range(C):
            if a == b:
                continue
            both = (has[:, a] & has[:, b]).mean()
            lift[a, b] = both / (p[a] * p[b]) if p[a] > 0 and p[b] > 0 else 1.0
            pa = has[has[:, a], b].mean() if has[:, a].any() else 0.0
            pna = has[~has[:, a], b].mean() if (~has[:, a]).any() else 0.0
            rel[a, b] = pa / pna if pna > 0 else 1.0
    return lift, rel, has


# ---------------------------------------------------------------- journeys
def build_journeys(h: History, tx_track: np.ndarray, store: StoreSpec = STORE) -> list[Journey]:
    slot_cat = h.layout.slot_category()
    cat_idx = {c: i for i, c in enumerate(CATEGORIES)}
    n = h.n_journeys
    visits: list[list[Visit]] = [[] for _ in range(n)]
    co_enter: list[float | None] = [None] * n
    co_exit: list[float | None] = [None] * n
    for i, zone, t0, t1 in zip(h.ze_track.tolist(), h.ze_zone, h.ze_enter.tolist(), h.ze_exit.tolist()):
        if zone in slot_cat:
            dwell = max(0.0, t1 - t0)
            visits[i].append(Visit(cat_idx[slot_cat[zone]], t0, t1, dwell, dwell >= ENGAGED_S))
        elif zone == "checkout":
            co_enter[i], co_exit[i] = t0, t1
    for v in visits:
        v.sort(key=lambda x: x.t_enter)
    disp: list[list[tuple[str, float, bool]]] = [[] for _ in range(n)]
    for i, slot, t, eng in zip(h.de_track.tolist(), h.de_slot, h.de_time.tolist(), h.de_engaged.tolist()):
        disp[i].append((slot, t, bool(eng)))
    bought = np.zeros((n, len(CATEGORIES)), dtype=bool)
    revenue = np.zeros(n)
    items = np.zeros(n, dtype=int)
    for row, cat, qty, rev in zip(h.tl_tx.tolist(), h.tl_category, h.tl_qty.tolist(), h.tl_revenue.tolist()):
        j = tx_track[row]
        if j < 0:
            continue
        bought[j, cat_idx[cat]] = True
        revenue[j] += rev
        items[j] += qty
    return [
        Journey(i, int(h.day[i]), float(h.t_arrive[i]), visits[i], co_enter[i], co_exit[i], bought[i],
                float(revenue[i]), int(items[i]), sorted(disp[i], key=lambda e: e[1]))
        for i in range(n)
    ]


# ---------------------------------------------------------------- clusters
def _kmeans(X: np.ndarray, k: int, seed: int, n_init: int = 8, iters: int = 100) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    best = (np.inf, None, None)
    for _restart in range(n_init):
        centers = [X[rng.integers(len(X))]]
        for _k in range(1, k):
            d2 = np.min(((X[:, None, :] - np.asarray(centers)[None]) ** 2).sum(-1), axis=1)
            probs = d2 / d2.sum() if d2.sum() > 0 else np.full(len(X), 1 / len(X))
            centers.append(X[rng.choice(len(X), p=probs)])
        C = np.asarray(centers, dtype=float)
        labels = np.zeros(len(X), dtype=int)
        for it in range(iters):
            d = ((X[:, None, :] - C[None]) ** 2).sum(-1)
            new = d.argmin(axis=1)
            if it > 0 and np.array_equal(new, labels):
                break
            labels = new
            for j in range(k):
                if (labels == j).any():
                    C[j] = X[labels == j].mean(axis=0)
        inertia = ((X - C[labels]) ** 2).sum()
        if inertia < best[0]:
            best = (inertia, labels.copy(), C.copy())
    return best[1], best[2]


def journey_features(journeys: list[Journey]) -> np.ndarray:
    C = len(CATEGORIES)
    X = np.zeros((len(journeys), 2 * C + 1))
    for j in journeys:
        for v in j.visits:
            X[j.idx, v.cat] = 1.0 if v.engaged else max(X[j.idx, v.cat], 0.0)
            X[j.idx, C + v.cat] = 0.5
        X[j.idx, 2 * C] = min(len(j.visits), 4) / 4.0
    return X


def cluster_journeys(journeys: list[Journey], seed: int) -> tuple[np.ndarray, list[dict]]:
    X = journey_features(journeys)
    labels, _ = _kmeans(X, N_CLUSTERS, seed)
    C = len(CATEGORIES)
    raw = []
    for k in range(N_CLUSTERS):
        members = [j for j in journeys if labels[j.idx] == k]
        eng = X[labels == k, :C].mean(axis=0) if members else np.zeros(C)
        visits = np.mean([len(j.visits) for j in members]) if members else 0.0
        top = [c for c in np.argsort(-eng) if eng[c] >= 0.35]
        if not top:
            name = "Browsers" if visits >= 1.0 else "Walk-through"
        else:
            name = " + ".join(CATEGORY_LABELS[CATEGORIES[c]] for c in top[:2])
        paths = Counter(
            " → ".join(["Entrance"] + [CATEGORY_LABELS[CATEGORIES[v.cat]] for v in j.visits]
                       + ["Checkout" if j.checkout_exit is not None else "Exit"])
            for j in members
        )
        conv = np.mean([j.checkout_exit is not None for j in members]) if members else 0.0
        raw.append({
            "id": k,
            "name": name,
            "share": len(members) / len(journeys),
            "journeys": len(members),
            "avg_zones": float(visits),
            "conversion": float(conv),
            "engagement": {CATEGORIES[c]: float(eng[c]) for c in range(C)},
            "top_paths": [{"path": p, "share": cnt / max(1, len(members))} for p, cnt in paths.most_common(3)],
        })
    # Order clusters by size for a stable presentation; relabel to 0..K-1.
    order = sorted(range(N_CLUSTERS), key=lambda k: -raw[k]["journeys"])
    remap = {old: new for new, old in enumerate(order)}
    new_labels = np.array([remap[l] for l in labels], dtype=int)
    info = []
    names_seen: Counter = Counter()
    for new, old in enumerate(order):
        item = dict(raw[old])
        item["id"] = new
        names_seen[item["name"]] += 1
        if names_seen[item["name"]] > 1:
            item["name"] = f"{item['name']} ({names_seen[item['name']]})"
        info.append(item)
    return new_labels, info


# ---------------------------------------------------------------- heatmap
def trajectory_heatmap(h: History, store: StoreSpec = STORE) -> np.ndarray:
    """Seconds of shopper presence per 0.5 m cell, averaged per day."""
    nx, ny = int(round(store.width / CELL)), int(round(store.height / CELL))
    t = h.traj[:, 0].astype(float)
    dt = np.zeros_like(t)
    dt[:-1] = np.diff(t)
    ends = h.traj_offsets[1:] - 1
    dt[ends[ends >= 0]] = 0.0
    dt = np.clip(dt, 0.0, 10.0)
    H, _, _ = np.histogram2d(h.traj[:, 2], h.traj[:, 1], bins=[ny, nx], range=[[0, store.height], [0, store.width]],
                             weights=dt)
    return H / h.n_days


# ---------------------------------------------------------------- main
def sequence_effects(journeys: list[Journey]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """For each ordered pair (a, b): purchase rate of b among shoppers who reach b right after
    an engaged visit to a, vs. everyone else who reaches b."""
    C = len(CATEGORIES)
    conv_after = np.zeros((C, C))
    conv_other = np.zeros((C, C))
    n_after = np.zeros((C, C), dtype=int)
    n_other = np.zeros((C, C), dtype=int)
    for j in journeys:
        first: dict[int, Visit] = {}
        for v in j.visits:
            first.setdefault(v.cat, v)
        for b, vb in first.items():
            for a in range(C):
                if a == b:
                    continue
                prior = any(v.cat == a and v.engaged and v.t_exit <= vb.t_enter for v in j.visits)
                if prior:
                    n_after[a, b] += 1
                    conv_after[a, b] += j.bought[b]
                else:
                    n_other[a, b] += 1
                    conv_other[a, b] += j.bought[b]
    with np.errstate(invalid="ignore", divide="ignore"):
        conv_after = np.where(n_after > 0, conv_after / np.maximum(n_after, 1), 0.0)
        conv_other = np.where(n_other > 0, conv_other / np.maximum(n_other, 1), 0.0)
    return conv_after, conv_other, n_after, n_other


def complement_relation(lift: np.ndarray, conv_after: np.ndarray, conv_other: np.ndarray,
                        n_after: np.ndarray, min_n: int = 30) -> np.ndarray:
    """Two categories are complements if baskets co-occur (lift >= 1.25) or if engaging with one
    raises purchase of the other in both directions (geometric-mean sequence ratio >= 1.5)."""
    C = len(CATEGORIES)
    comp = np.zeros((C, C), dtype=bool)
    for a in range(C):
        for b in range(a + 1, C):
            basket = lift[a, b] >= 1.25
            ok_n = n_after[a, b] >= min_n and n_after[b, a] >= min_n
            ratio_ab = conv_after[a, b] / conv_other[a, b] if conv_other[a, b] > 0 else 0.0
            ratio_ba = conv_after[b, a] / conv_other[b, a] if conv_other[b, a] > 0 else 0.0
            sequence = ok_n and ratio_ab > 0 and ratio_ba > 0 and np.sqrt(ratio_ab * ratio_ba) >= 1.5
            if basket or sequence:
                comp[a, b] = comp[b, a] = True
    return comp


def analyze(h: History, seed: int, store: StoreSpec = STORE) -> Analytics:
    tx_track, match = match_transactions(h)
    lift, rel, _ = basket_lift(h, tx_track)
    journeys = build_journeys(h, tx_track, store)
    seq = sequence_effects(journeys)
    comp = complement_relation(lift, seq[0], seq[1], seq[2])
    labels, cinfo = cluster_journeys(journeys, seed)
    a = Analytics(journeys=journeys, comp=comp, lift=lift, match=match, cluster=labels, cluster_info=cinfo)
    a.heatmap = trajectory_heatmap(h, store)
    a.summary = _summary(h, a, rel, seq, store)
    return a


def _pct(x: float) -> float:
    return round(100.0 * x, 1)


def _summary(h: History, a: Analytics, rel: np.ndarray, seq_stats: tuple, store: StoreSpec) -> dict:
    C = len(CATEGORIES)
    J = a.journeys
    N = len(J)
    days = h.n_days
    slot_of = h.layout.cat_slot
    buyers = [j for j in J if j.checkout_exit is not None]
    n_tx = h.n_transactions
    revenue_total = float(h.tl_revenue.sum())
    items_total = int(h.tl_qty.sum())

    # ---- KPIs
    co_rows = np.array([z == "checkout" for z in h.ze_zone])
    q_enter, q_exit = h.ze_enter[co_rows], h.ze_exit[co_rows]
    q_day = h.day[h.ze_track[co_rows]]
    lo, hi = store.peak_window[0] * 3600, store.peak_window[1] * 3600
    peak_L = [
        float((np.clip(q_exit[q_day == d], lo, hi) - np.clip(q_enter[q_day == d], lo, hi)).sum() / (hi - lo))
        for d in range(days)
    ]
    hourly_occ = []
    for hr in range(store.open_hour, store.close_hour):
        a0, a1 = hr * 3600, (hr + 1) * 3600
        occ = (np.clip(q_exit, a0, a1) - np.clip(q_enter, a0, a1)).sum() / (3600 * days)
        arrivals = int(((h.t_arrive >= a0) & (h.t_arrive < a1)).sum())
        tx = int(((h.tx_time >= a0) & (h.tx_time < a1)).sum())
        hourly_occ.append({"hour": hr, "checkout_occupancy": round(float(occ), 3),
                           "visitors_per_day": round(arrivals / days, 1), "transactions_per_day": round(tx / days, 1)})
    peak_hour = max(hourly_occ, key=lambda r: r["checkout_occupancy"])

    kpis = {
        "visitors": N,
        "transactions": n_tx,
        "conversion_rate": n_tx / N if N else 0.0,
        "revenue": revenue_total,
        "avg_basket": revenue_total / n_tx if n_tx else 0.0,
        "items_per_basket": items_total / n_tx if n_tx else 0.0,
        "avg_journey_min": float(np.mean(h.t_leave - h.t_arrive) / 60.0),
        "peak_checkout_occupancy": float(np.mean(peak_L)),
        "peak_window": f"{store.peak_window[0]:02d}:00–{store.peak_window[1]:02d}:00",
        "days": days,
        "period": f"{h.start_date.isoformat()} to {(h.start_date + dt.timedelta(days=days - 1)).isoformat()}",
    }

    # ---- zones / categories
    zones = {}
    cat_rev = {c: 0.0 for c in CATEGORIES}
    cat_units = {c: 0 for c in CATEGORIES}
    cat_tx = {c: set() for c in CATEGORIES}
    for row, cat, q, rev in zip(h.tl_tx.tolist(), h.tl_category, h.tl_qty.tolist(), h.tl_revenue.tolist()):
        cat_rev[cat] += rev
        cat_units[cat] += q
        cat_tx[cat].add(row)
    for c, cat in enumerate(CATEGORIES):
        visitors = engaged = purchases = 0
        dwell = []
        for j in J:
            vs = [v for v in j.visits if v.cat == c]
            if not vs:
                continue
            visitors += 1
            dwell.append(sum(v.dwell for v in vs))
            if any(v.engaged for v in vs):
                engaged += 1
            if j.bought[c]:
                purchases += 1
        zones[cat] = {
            "category": cat,
            "label": CATEGORY_LABELS[cat],
            "slot": slot_of[cat],
            "visitors": visitors,
            "engaged": engaged,
            "purchases": purchases,
            "zone_conversion": purchases / visitors if visitors else 0.0,
            "engagement_rate": engaged / visitors if visitors else 0.0,
            "avg_dwell_s": float(np.mean(dwell)) if dwell else 0.0,
            "traffic_share": visitors / N,
            "category_buyers": len(cat_tx[cat]),
            "attachment_rate": len(cat_tx[cat]) / n_tx if n_tx else 0.0,
            "revenue": cat_rev[cat],
            "units": cat_units[cat],
        }

    # ---- transitions (entrance / categories / checkout / exit)
    nodes = ["entrance"] + CATEGORIES + ["checkout", "exit"]
    T = np.zeros((len(nodes), len(nodes)))
    backtrack = 0
    multi = 0
    for j in J:
        seq = [0] + [1 + v.cat for v in j.visits] + [len(nodes) - 2 if j.checkout_exit is not None else len(nodes) - 1]
        for x, y in zip(seq[:-1], seq[1:]):
            T[x, y] += 1
        cats_seq = [v.cat for v in j.visits]
        if len(cats_seq) >= 2:
            multi += 1
            if len(set(cats_seq)) < len(cats_seq):
                backtrack += 1
    P = T / np.maximum(T.sum(axis=1, keepdims=True), 1)
    transitions = {
        "nodes": nodes,
        "labels": ["Entrance"] + [CATEGORY_LABELS[c] for c in CATEGORIES] + ["Checkout", "Exit"],
        "counts": T.astype(int).tolist(),
        "probabilities": np.round(P, 4).tolist(),
    }

    # ---- sequence effect: does reaching B after an engaged complement visit raise purchase?
    conv_after, conv_other, n_after, n_other = seq_stats
    seq_effects = []
    for a_ in range(C):
        for b in range(C):
            if a_ == b or not a.comp[a_, b] or n_after[a_, b] < 30 or n_other[a_, b] < 30:
                continue
            pa, pn = float(conv_after[a_, b]), float(conv_other[a_, b])
            seq_effects.append({
                "from": CATEGORIES[a_], "to": CATEGORIES[b],
                "conversion_after_from": pa, "conversion_otherwise": pn,
                "ratio": (pa / pn) if pn > 0 else None,
                "n_after": int(n_after[a_, b]), "n_otherwise": int(n_other[a_, b]),
            })
    seq_effects.sort(key=lambda e: -(e["ratio"] or 0.0))

    # ---- display slots: exposure for every slot, funnel for occupied ones
    slot_rows: dict[str, dict] = {}
    occupied = h.layout.display_map
    for d in store.displays:
        slot_rows[d.id] = {"slot": d.id, "label": d.label, "kind": d.kind, "category": occupied.get(d.id),
                           "passes": 0, "engaged": 0, "engaged_and_bought": 0,
                           "primed_passes": {c: 0 for c in CATEGORIES}}
    cat_idx = {c: i for i, c in enumerate(CATEGORIES)}
    for j in J:
        for slot, t, eng in j.display_events:
            r = slot_rows[slot]
            r["passes"] += 1
            for c in range(C):
                if j.primed_at(c, t, a.comp):
                    r["primed_passes"][CATEGORIES[c]] += 1
            if eng:
                r["engaged"] += 1
                if r["category"] and j.bought[cat_idx[r["category"]]]:
                    r["engaged_and_bought"] += 1
    for r in slot_rows.values():
        r["passes_per_day"] = r["passes"] / days
        r["pass_share"] = r["passes"] / N
    displays = list(slot_rows.values())

    # ---- clusters
    clusters = a.cluster_info

    # ---- heat by area (for dead-zone detection)
    heat = a.heatmap
    areas = {
        "Back corridor": (1.0, 0.0, 21.0, 2.0),
        "Front corridor": (1.0, 10.0, 21.0, 11.8),
        "Entrance": store.entrance_rect,
        "Checkout": store.checkout_rect,
    }
    for cat in CATEGORIES:
        areas[f"{CATEGORY_LABELS[cat]} aisle"] = store.aisle(slot_of[cat]).rect
    ys = (np.arange(heat.shape[0]) + 0.5) * CELL
    xs = (np.arange(heat.shape[1]) + 0.5) * CELL
    gx, gy = np.meshgrid(xs, ys)
    area_rows = []
    for name, (x0, y0, x1, y1) in areas.items():
        m = (gx >= x0) & (gx <= x1) & (gy >= y0) & (gy <= y1)
        area_m2 = float(m.sum() * CELL * CELL)
        secs = float(heat[m].sum())
        area_rows.append({"area": name, "shopper_seconds_per_day": secs, "area_m2": area_m2,
                          "density": secs / area_m2 if area_m2 else 0.0})
    dens = np.array([r["density"] for r in area_rows])
    for r in area_rows:
        r["dead_zone"] = bool(r["density"] < 0.25 * np.median(dens))

    complements = [
        {"a": CATEGORIES[x], "b": CATEGORIES[y], "lift": float(a.lift[x, y]), "relative_likelihood": float(rel[x, y])}
        for x in range(C) for y in range(C) if x < y and a.comp[x, y]
    ]
    relative = [
        {"if_bought": CATEGORIES[x], "then": CATEGORIES[y], "times_more_likely": float(rel[x, y])}
        for x in range(C) for y in range(C) if x != y
    ]
    summary = {
        "synthetic": True,
        "kpis": kpis,
        "zones": zones,
        "transitions": transitions,
        "backtracking_rate": backtrack / multi if multi else 0.0,
        "sequence_effects": seq_effects,
        "displays": displays,
        "clusters": clusters,
        "hourly": hourly_occ,
        "peak_hour": peak_hour,
        "areas": area_rows,
        "complements": complements,
        "relative_likelihood": relative,
        "pos_join": a.match,
    }
    summary["insights"] = _insights(summary, a)
    summary["briefing"] = _briefing(summary)
    return summary


def _briefing(s: dict) -> list[dict]:
    """The three things a store manager should see first: one opportunity, one friction, one pattern."""
    zones = list(s["zones"].values())
    convs = sorted(z["zone_conversion"] for z in zones)
    median_conv = convs[len(convs) // 2]
    weak = [z for z in zones if z["zone_conversion"] <= median_conv] or zones
    opp = max(weak, key=lambda z: z["visitors"])
    label = opp["label"]
    out = [{
        "kind": "opportunity",
        "title": f"{label}: lots of traffic, few buyers",
        "detail": (f"{_pct(opp['traffic_share']):.0f}% of shoppers visit the {label.lower()} aisle, "
                   f"but only {_pct(opp['zone_conversion']):.0f}% of them buy."),
        "zones": [opp["slot"]],
        "category": opp["category"],
        "action": {"type": "goal", "label": f"Improve {label}",
                   "goal": f"Increase {_SINGULAR[opp['category']]} sales by 10%. Budget ₱30k. Don't worsen checkout congestion."},
    }]
    hours = [r for r in s["hourly"] if r["checkout_occupancy"] > 0]
    ph = s["peak_hour"]
    avg = sum(r["checkout_occupancy"] for r in hours) / len(hours) if hours else 0.0
    out.append({
        "kind": "friction",
        "title": f"Checkout gets crowded {ph['hour']:02d}:00–{ph['hour'] + 1:02d}:00",
        "detail": (f"The checkout area is {ph['checkout_occupancy'] / avg:.1f}× busier than the daily average "
                   "at that hour." if avg else "The checkout area is busiest at that hour."),
        "zones": ["checkout"],
        "category": None,
        "action": {"type": "analytics", "label": "Investigate", "target": "hourly"},
    })
    effects = [e for e in s["sequence_effects"] if e["ratio"]]
    e = next((x for x in effects if x["to"] == opp["category"]), effects[0] if effects else None)
    if e:
        frm, to = CATEGORY_LABELS[e["from"]], CATEGORY_LABELS[e["to"]]
        out.append({
            "kind": "pattern",
            "title": f"Shoppers coming from {frm} buy {to.lower()} {e['ratio']:.1f}× as often",
            "detail": f"{_pct(e['conversion_after_from']):.0f}% of them buy {to.lower()}, vs "
                      f"{_pct(e['conversion_otherwise']):.0f}% of other {to.lower()}-aisle shoppers.",
            "zones": [s["zones"][e["from"]]["slot"], s["zones"][e["to"]]["slot"]],
            "category": e["to"],
            "action": {"type": "goal", "label": f"Use the {frm.lower()} → {to.lower()} link",
                       "goal": (f"Increase {_SINGULAR[e['to']]} attachment by 10% using the "
                                f"{_SINGULAR[e['from']]} connection. "
                                "Budget ₱30k. Don't worsen checkout congestion.")},
        })
    return out


def _insights(s: dict, a: Analytics) -> list[dict]:
    """Deterministic observations (not conclusions) for the Live Store screen."""
    out: list[dict] = []
    zones = s["zones"]
    by_traffic = sorted(zones.values(), key=lambda z: -z["visitors"])
    by_conv = sorted(zones.values(), key=lambda z: z["zone_conversion"])
    # High traffic, weak conversion
    for z in by_traffic[:3]:
        if z in by_conv[:2]:
            out.append({
                "type": "traffic_vs_conversion",
                "category": z["category"],
                "title": f"{z['label']}: lots of traffic, few buyers",
                "detail": (f"{z['visitors']:,} visitors ({_pct(z['traffic_share'])}% of shoppers) but only "
                           f"{_pct(z['zone_conversion'])}% buy {z['label'].lower()}; "
                           f"{_pct(z['engagement_rate'])}% stop for 20 s or more."),
            })
            break
    # Complement attachment (one basket-level insight; the pair is symmetric)
    for c in sorted(s["relative_likelihood"], key=lambda r: -r["times_more_likely"])[:1]:
        if c["times_more_likely"] >= 1.5:
            out.append({
                "type": "attachment",
                "category": c["then"],
                "title": f"{CATEGORY_LABELS[c['if_bought']]} buyers are {c['times_more_likely']:.1f}× more likely to buy "
                         f"{CATEGORY_LABELS[c['then']].lower()}",
                "detail": "Seen in POS baskets over the last 7 days.",
            })
    seen_pairs: set[frozenset] = set()
    for e in s["sequence_effects"]:  # strongest direction of each complement pair
        pair = frozenset((e["from"], e["to"]))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        if e["ratio"] and e["ratio"] >= 1.3:
            out.append({
                "type": "sequence",
                "category": e["to"],
                "title": (f"Shoppers coming from {CATEGORY_LABELS[e['from']]} buy "
                          f"{CATEGORY_LABELS[e['to']].lower()} {e['ratio']:.1f}× as often"),
                "detail": (f"{_pct(e['conversion_after_from'])}% of them buy, vs {_pct(e['conversion_otherwise'])}% "
                           f"of other shoppers in the {CATEGORY_LABELS[e['to']].lower()} aisle."),
            })
    # Displays
    occ = [d for d in s["displays"] if d["category"]]
    empty_front = [d for d in s["displays"] if not d["category"] and d["kind"] == "endcap"]
    for d in occ:
        best_empty = max(empty_front, key=lambda r: r["passes"], default=None)
        if best_empty and best_empty["passes"] > 1.2 * d["passes"]:
            out.append({
                "type": "display_placement",
                "category": d["category"],
                "title": f"{CATEGORY_LABELS[d['category']]} promo at {d['label']} is passed by {_pct(d['pass_share'])}% of shoppers",
                "detail": f"The empty {best_empty['label']} is passed by {_pct(best_empty['pass_share'])}%.",
            })
    # Dead zones
    for r in s["areas"]:
        if r["dead_zone"]:
            out.append({"type": "dead_zone", "category": None, "title": f"Low-traffic area: {r['area']}",
                        "detail": f"{r['density']:.1f} shopper-seconds per m² per day, well below the store median."})
    # Congestion
    ph = s["peak_hour"]
    out.append({
        "type": "congestion",
        "category": None,
        "title": f"Checkout congestion peaks {ph['hour']:02d}:00–{ph['hour'] + 1:02d}:00",
        "detail": f"{ph['checkout_occupancy']:.2f} shoppers in the checkout area on average, "
                  f"{ph['transactions_per_day']:.0f} transactions/hour.",
    })
    if s["backtracking_rate"] > 0.05:
        out.append({"type": "backtracking", "category": None,
                    "title": f"{_pct(s['backtracking_rate'])}% of multi-aisle journeys backtrack",
                    "detail": "They return to an aisle already visited."})
    return out
