"""Agent-based shopper engine.

One engine, two uses:
  * groundtruth.py runs it with hidden "true" parameters to synthesise the demo history
    (what store cameras + POS would have recorded);
  * simulator.py runs it with parameters *fitted from that history* to predict how a
    candidate layout would perform.

Shoppers are statistical agents, not sentient ones: a zone-choice model (conditional
logit over aisles + "done"), a dwell model, and noisy-OR purchase opportunities at
aisles, promo displays and the checkout rack. Checkout queues are a FIFO multi-lane
discrete-event simulation. Random draws are pre-generated per shopper ("common random
numbers") so baseline and candidate layouts are compared on identical shoppers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .geometry import PathNetwork, path_network, zone_heat_kernel
from .layout import Layout
from .store import CATEGORIES, StoreSpec

MAX_STEPS = 8
N_CAT = len(CATEGORIES)
SRC_NONE, SRC_ZONE, SRC_DISPLAY, SRC_RACK, SRC_LEAK = 0, 1, 2, 3, 4
SOURCE_NAMES = {SRC_ZONE: "aisle", SRC_DISPLAY: "display", SRC_RACK: "checkout_rack", SRC_LEAK: "other"}
QUANTILE_POINTS = 201


def sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


@dataclass
class BehaviorParams:
    segment_ids: list[str]
    segment_labels: list[str]
    hour_weights: np.ndarray  # (24,) arrival share by hour of day
    segment_given_hour: np.ndarray  # (24, S)
    # zone choice (conditional logit)
    asc: np.ndarray  # (S, C)
    asc_end: np.ndarray  # (S,)
    beta_dist: float  # utility per metre walked (positive number = disutility)
    beta_comp: float  # pull towards a complementary category right after engaging
    beta_visited: float  # penalty for revisiting
    beta_steps: float  # "done" utility per aisle already visited
    comp: np.ndarray  # (C, C) bool complement relation
    # dwell
    p_engage: np.ndarray  # (S, C) P(dwell >= threshold | visit)
    dwell_engaged_q: list[list[float]]  # per category quantile table (seconds)
    dwell_passing_q: list[list[float]]
    # purchases
    zone_a: np.ndarray  # (S, C)
    zone_b_dwell: float
    zone_b_engaged: float
    zone_b_primed: float
    disp_engage_a: float
    disp_engage_b_primed: float
    disp_buy_a: float
    disp_buy_b_primed: float
    leak: float
    # basket composition
    sku_ids: list[list[str]]
    sku_price: list[list[float]]
    sku_cum: list[list[float]]
    qty_cum: list[list[float]]  # cumulative P(qty = 1, 2, 3)
    walk_speed: float = 0.9  # m/s
    engaged_threshold_s: float = 20.0
    display_dwell_s: float = 8.0
    shopper_noise_sd: float = 0.0  # unobserved per-shopper purchase propensity (ground truth only)


@dataclass
class CheckoutParams:
    base_s: float = 35.0
    per_item_s: float = 7.0
    sd_s: float = 8.0
    min_s: float = 15.0
    lanes: int = 1
    rack_dwell_s: float = 12.0  # extra counter time when a queueing shopper engages the rack


@dataclass
class Draws:
    """Common random numbers: identical shoppers for every layout that is simulated."""

    n: int
    days: int
    day: np.ndarray
    arrival: np.ndarray  # seconds since midnight
    hour: np.ndarray
    seg_u: np.ndarray
    u_choice: np.ndarray  # (n, MAX_STEPS + 1)
    u_engage: np.ndarray  # (n, MAX_STEPS)
    u_dwell: np.ndarray  # (n, MAX_STEPS)
    u_disp: np.ndarray  # (n, n_display_slots)
    u_buy: np.ndarray  # (n, C)
    u_sku: np.ndarray
    u_qty: np.ndarray
    z_service: np.ndarray  # (n,)
    z_shopper: np.ndarray  # (n,)


def make_draws(n: int, days: int, hour_weights: np.ndarray, n_displays: int, seed: int) -> Draws:
    rng = np.random.default_rng(seed)
    per_day = np.full(days, n // days)
    per_day[: n % days] += 1
    day = np.repeat(np.arange(days), per_day)
    w = np.asarray(hour_weights, dtype=float)
    w = w / w.sum()
    hour = rng.choice(24, size=n, p=w)
    arrival = hour * 3600.0 + rng.uniform(0.0, 3600.0, size=n)
    order = np.lexsort((arrival, day))
    day, hour, arrival = day[order], hour[order], arrival[order]
    return Draws(
        n=n,
        days=days,
        day=day,
        arrival=arrival,
        hour=hour,
        seg_u=rng.random(n),
        u_choice=rng.random((n, MAX_STEPS + 1)),
        u_engage=rng.random((n, MAX_STEPS)),
        u_dwell=rng.random((n, MAX_STEPS)),
        u_disp=rng.random((n, n_displays)),
        u_buy=rng.random((n, N_CAT)),
        u_sku=rng.random((n, N_CAT)),
        u_qty=rng.random((n, N_CAT)),
        z_service=rng.standard_normal(n),
        z_shopper=rng.standard_normal(n),
    )


def quantile_table(samples: np.ndarray) -> list[float]:
    probs = np.linspace(0.0, 1.0, QUANTILE_POINTS)
    return [float(v) for v in np.quantile(np.asarray(samples, dtype=float), probs)]


def _qlookup(table: list[float], u: float) -> float:
    pos = u * (len(table) - 1)
    lo = int(pos)
    if lo >= len(table) - 1:
        return table[-1]
    frac = pos - lo
    return table[lo] + frac * (table[lo + 1] - table[lo])


def _cum_pick(cum: list[float], u: float) -> int:
    for k, c in enumerate(cum):
        if u < c:
            return k
    return len(cum) - 1


@dataclass
class EngineOutput:
    n: int
    days: int
    store: StoreSpec
    layout: Layout
    seg: np.ndarray
    day: np.ndarray
    arrival: np.ndarray
    # zone visits (flat)
    v_shopper: list[int] = field(default_factory=list)
    v_cat: list[int] = field(default_factory=list)
    v_enter: list[float] = field(default_factory=list)
    v_dwell: list[float] = field(default_factory=list)
    v_engaged: list[bool] = field(default_factory=list)
    v_primed: list[bool] = field(default_factory=list)
    # display slot passes (every defined slot, occupied or not)
    d_shopper: list[int] = field(default_factory=list)
    d_slot: list[int] = field(default_factory=list)
    d_time: list[float] = field(default_factory=list)
    d_primed_mask: list[int] = field(default_factory=list)  # bit c set = primed for category c
    d_cat: list[int] = field(default_factory=list)  # category on display, -1 if empty
    d_engaged: list[bool] = field(default_factory=list)
    d_bought: list[bool] = field(default_factory=list)
    # purchases
    buy_qty: np.ndarray | None = None  # (n, C)
    buy_rev: np.ndarray | None = None
    buy_src: np.ndarray | None = None
    buy_sku: np.ndarray | None = None
    # checkout
    went_checkout: np.ndarray | None = None
    t_queue: np.ndarray | None = None
    service: np.ndarray | None = None
    wait: np.ndarray | None = None
    t_depart: np.ndarray | None = None
    t_exit: np.ndarray | None = None
    rack_engaged: np.ndarray | None = None
    distance: np.ndarray | None = None
    zone_seq: list[list[int]] = field(default_factory=list)
    # heat accounting
    leg_counts: dict = field(default_factory=dict)
    zone_dwell_s: dict = field(default_factory=dict)
    # optional per-shopper movement script for rendering trajectories
    scripts: dict = field(default_factory=dict)


class LayoutContext:
    """Per-layout lookups, precomputed once so the per-shopper loop stays cheap."""

    def __init__(self, store: StoreSpec, layout: Layout, speed: float):
        self.store = store
        self.layout = layout
        self.net: PathNetwork = path_network(layout.obstacle_signature(store))
        cat_slot = layout.cat_slot
        self.cat_anchor = [cat_slot[c] for c in CATEGORIES]
        self.slot_ids = store.display_ids
        self.slot_index = {s: k for k, s in enumerate(self.slot_ids)}
        self.display_cat = [-1] * len(self.slot_ids)
        for slot, cat in layout.displays:
            self.display_cat[self.slot_index[slot]] = CATEGORIES.index(cat)
        rack_k = next((k for k, d in enumerate(store.displays) if d.at_checkout), None)
        self.rack_k = rack_k
        self.rack_cat = self.display_cat[rack_k] if rack_k is not None else -1
        nodes = ["entrance"] + self.cat_anchor
        self.dist = [[self.net.distance(a, b) for b in self.cat_anchor] for a in nodes]
        # leg info keyed by (from_anchor, to_anchor): (length, walk_s, [(frac, slot_k)])
        self.leg_info: dict[tuple[str, str], tuple[float, float, list[tuple[float, int]]]] = {}
        for key, leg in self.net.legs.items():
            hits = [(f, self.slot_index[s]) for f, s in leg.display_hits]
            self.leg_info[key] = (leg.length, leg.length / speed, hits)


def run_engine(
    params: BehaviorParams,
    checkout: CheckoutParams,
    store: StoreSpec,
    layout: Layout,
    draws: Draws,
    script_ids: set[int] | None = None,
) -> EngineOutput:
    ctx = LayoutContext(store, layout, params.walk_speed)
    n = draws.n
    S = len(params.segment_ids)
    seg_cum = np.cumsum(params.segment_given_hour, axis=1)
    seg = np.array(
        [min(int(np.searchsorted(seg_cum[h], u, side="right")), S - 1) for h, u in zip(draws.hour, draws.seg_u)],
        dtype=int,
    )
    out = EngineOutput(n=n, days=draws.days, store=store, layout=layout, seg=seg, day=draws.day, arrival=draws.arrival)
    script_ids = script_ids or set()

    # ---- local bindings for speed
    asc = params.asc.tolist()
    asc_end = params.asc_end.tolist()
    b_dist, b_comp, b_vis, b_steps = params.beta_dist, params.beta_comp, params.beta_visited, params.beta_steps
    comp = params.comp.astype(bool).tolist()
    comp_of = [[k for k in range(N_CAT) if comp[k][c] and k != c] for c in range(N_CAT)]
    p_engage = params.p_engage.tolist()
    dq_eng, dq_pass = params.dwell_engaged_q, params.dwell_passing_q
    zone_a = params.zone_a.tolist()
    zb_dwell, zb_eng, zb_primed = params.zone_b_dwell, params.zone_b_engaged, params.zone_b_primed
    de_a, de_b, db_a, db_b = params.disp_engage_a, params.disp_engage_b_primed, params.disp_buy_a, params.disp_buy_b_primed
    leak = params.leak
    speed = params.walk_speed
    thr = params.engaged_threshold_s
    disp_dwell = params.display_dwell_s
    noise_sd = params.shopper_noise_sd
    dist = ctx.dist
    cat_anchor = ctx.cat_anchor
    leg_info = ctx.leg_info
    display_cat = ctx.display_cat
    rack_k, rack_cat = ctx.rack_k, ctx.rack_cat
    leg_counts: dict[tuple[str, str], int] = {}
    zone_dwell: dict[str, float] = {}

    buy_qty = np.zeros((n, N_CAT), dtype=int)
    buy_rev = np.zeros((n, N_CAT))
    buy_src = np.zeros((n, N_CAT), dtype=int)
    buy_sku = np.full((n, N_CAT), -1, dtype=int)
    went = np.zeros(n, dtype=bool)
    t_queue = np.full(n, np.nan)
    service = np.zeros(n)
    rack_engaged = np.zeros(n, dtype=bool)
    distance = np.zeros(n)
    t_end_browse = np.zeros(n)  # time a non-buyer reaches the exit

    v_shopper, v_cat, v_enter, v_dwell, v_engaged, v_primed = (
        out.v_shopper, out.v_cat, out.v_enter, out.v_dwell, out.v_engaged, out.v_primed)
    d_shopper, d_slot, d_time, d_mask, d_cat, d_eng, d_bought = (
        out.d_shopper, out.d_slot, out.d_time, out.d_primed_mask, out.d_cat, out.d_engaged, out.d_bought)

    u_choice_all = draws.u_choice.tolist()
    u_engage_all = draws.u_engage.tolist()
    u_dwell_all = draws.u_dwell.tolist()
    u_disp_all = draws.u_disp.tolist()
    u_buy_all = draws.u_buy.tolist()
    z_shopper = draws.z_shopper.tolist()
    arrival = draws.arrival.tolist()
    seg_l = seg.tolist()

    for i in range(n):
        s = seg_l[i]
        t = arrival[i]
        u_choice = u_choice_all[i]
        u_eng = u_engage_all[i]
        u_dw = u_dwell_all[i]
        u_disp = u_disp_all[i]
        u_buy = u_buy_all[i]
        noise = noise_sd * z_shopper[i] if noise_sd else 0.0
        notbuy = [1.0] * N_CAT
        bought_src = [0] * N_CAT
        engaged_end = [math.inf] * N_CAT  # when an engaged visit to each category finished
        visited = [False] * N_CAT
        seen_slots: set[int] = set()
        cur_anchor = "entrance"
        cur_node = 0  # row in dist: 0 = entrance, 1 + c = category c
        cur_cat = -1
        cur_engaged = False
        steps = 0
        walked = 0.0
        seq: list[int] = []
        script = [] if i in script_ids else None

        def primed_mask_at(tt: float) -> int:
            m = 0
            for c in range(N_CAT):
                for k in comp_of[c]:
                    if engaged_end[k] <= tt:
                        m |= 1 << c
                        break
            return m

        def opportunity(c: int, p: float, src: int) -> bool:
            if bought_src[c]:
                return False
            nb = notbuy[c] * (1.0 - p)
            notbuy[c] = nb
            if u_buy[c] < 1.0 - nb:
                bought_src[c] = src
                return True
            return False

        def walk(a: str, b: str, t0: float) -> float:
            """Walk a leg, handling every display slot passed. Returns the arrival time."""
            nonlocal walked
            length, walk_s, hits = leg_info[(a, b)]
            leg_counts[(a, b)] = leg_counts.get((a, b), 0) + 1
            walked += length
            extra = 0.0
            for frac, k in hits:
                if k in seen_slots:
                    continue
                seen_slots.add(k)
                th = t0 + frac * walk_s + extra
                mask = primed_mask_at(th)
                dc = display_cat[k]
                engaged = bought = False
                if dc >= 0:
                    primed = (mask >> dc) & 1
                    engaged = u_disp[k] < sigmoid(de_a + de_b * primed)
                    if engaged:
                        extra += disp_dwell
                        bought = opportunity(dc, sigmoid(db_a + db_b * primed), SRC_DISPLAY)
                d_shopper.append(i)
                d_slot.append(k)
                d_time.append(th)
                d_mask.append(mask)
                d_cat.append(dc)
                d_eng.append(engaged)
                d_bought.append(bought)
            if script is not None:
                script.append(("walk", a, b, t0, t0 + walk_s + extra))
            return t0 + walk_s + extra

        # ---------------------------------------------------------- browse loop
        while True:
            if steps >= MAX_STEPS:
                choice = -1
            else:
                drow = dist[cur_node]
                utils: list[tuple[int, float]] = []
                for c in range(N_CAT):
                    if c == cur_cat:
                        continue
                    u = asc[s][c] - b_dist * drow[c]
                    if cur_engaged and cur_cat >= 0 and comp[cur_cat][c]:
                        u += b_comp
                    if visited[c]:
                        u -= b_vis
                    utils.append((c, u))
                utils.append((-1, asc_end[s] + b_steps * steps))
                m = max(u for _, u in utils)
                weights = [(c, math.exp(u - m)) for c, u in utils]
                total = sum(w for _, w in weights)
                r = u_choice[steps] * total
                acc = 0.0
                choice = weights[-1][0]
                for c, w in weights:
                    acc += w
                    if r < acc:
                        choice = c
                        break
            if choice < 0:
                break
            c = choice
            target = cat_anchor[c]
            t = walk(cur_anchor, target, t)
            engaged = u_eng[steps] < p_engage[s][c]
            dwell = _qlookup(dq_eng[c] if engaged else dq_pass[c], u_dw[steps])
            engaged = dwell >= thr
            primed = False
            for k in comp_of[c]:
                if engaged_end[k] <= t:
                    primed = True
                    break
            logit = (zone_a[s][c] + zb_dwell * math.log1p(dwell / 30.0) + (zb_eng if engaged else 0.0)
                     + (zb_primed if primed else 0.0) + noise)
            opportunity(c, sigmoid(logit), SRC_ZONE)
            v_shopper.append(i)
            v_cat.append(c)
            v_enter.append(t)
            v_dwell.append(dwell)
            v_engaged.append(engaged)
            v_primed.append(primed)
            seq.append(c)
            if script is not None:
                script.append(("stay", target, t, t + dwell))
            zone_dwell[target] = zone_dwell.get(target, 0.0) + dwell
            t += dwell
            if engaged and engaged_end[c] == math.inf:
                engaged_end[c] = t
            visited[c] = True
            cur_anchor = target
            cur_node = 1 + c
            cur_cat = c
            cur_engaged = engaged
            steps += 1

        # ---------------------------------------------------------- finish trip
        if leak > 0:
            for c in range(N_CAT):
                opportunity(c, leak, SRC_LEAK)
        if any(bought_src):
            t = walk(cur_anchor, "checkout", t)
            went[i] = True
        else:
            t = walk(cur_anchor, "exit", t)
            if any(bought_src):  # picked something up from a display on the way out
                t = walk("exit", "checkout", t)
                went[i] = True
            else:
                t_end_browse[i] = t
        if went[i]:
            t_queue[i] = t
            if rack_k is not None:
                # Every queueing shopper passes the rack location; only an occupied rack can sell.
                k = rack_k
                mask = primed_mask_at(t)
                eng = bought = False
                if rack_cat >= 0:
                    primed = (mask >> rack_cat) & 1
                    eng = u_disp[k] < sigmoid(de_a + de_b * primed)
                    if eng:
                        rack_engaged[i] = True
                        bought = opportunity(rack_cat, sigmoid(db_a + db_b * primed), SRC_RACK)
                d_shopper.append(i)
                d_slot.append(k)
                d_time.append(t)
                d_mask.append(mask)
                d_cat.append(rack_cat)
                d_eng.append(eng)
                d_bought.append(bought)
            for c in range(N_CAT):
                if bought_src[c]:
                    buy_src[i, c] = bought_src[c]
        distance[i] = walked
        out.zone_seq.append(seq)
        if script is not None:
            out.scripts[i] = script

    # ---------------------------------------------------------- baskets
    u_sku = draws.u_sku
    u_qty = draws.u_qty
    for i, c in zip(*np.nonzero(buy_src)):
        k = _cum_pick(params.sku_cum[c], float(u_sku[i, c]))
        q = _cum_pick(params.qty_cum[c], float(u_qty[i, c])) + 1
        buy_sku[i, c] = k
        buy_qty[i, c] = q
        buy_rev[i, c] = q * params.sku_price[c][k]
    items = buy_qty.sum(axis=1)
    service[:] = np.maximum(
        checkout.min_s,
        checkout.base_s + checkout.per_item_s * items + checkout.sd_s * draws.z_service,
    ) + np.where(rack_engaged, checkout.rack_dwell_s, 0.0)
    service[~went] = 0.0

    # ---------------------------------------------------------- checkout queue (FIFO, multi-lane)
    wait = np.zeros(n)
    t_depart = np.full(n, np.nan)
    lanes = max(1, int(checkout.lanes))
    for d in range(draws.days):
        idx = np.nonzero(went & (draws.day == d))[0]
        idx = idx[np.argsort(t_queue[idx], kind="stable")]
        free = [0.0] * lanes
        for i in idx.tolist():
            lane = min(range(lanes), key=free.__getitem__)
            start = max(t_queue[i], free[lane])
            wait[i] = start - t_queue[i]
            t_depart[i] = start + service[i]
            free[lane] = t_depart[i]
    exit_len, exit_walk, _ = ctx.leg_info[("checkout", "exit")]
    t_exit = np.where(went, t_depart + exit_walk, t_end_browse)
    leg_counts[("checkout", "exit")] = leg_counts.get(("checkout", "exit"), 0) + int(went.sum())
    distance[went] += exit_len
    zone_dwell["checkout"] = float((wait + service)[went].sum())
    for i in out.scripts:
        if went[i]:
            out.scripts[i].append(("stay", "checkout", float(t_queue[i]), float(t_depart[i])))
            out.scripts[i].append(("walk", "checkout", "exit", float(t_depart[i]), float(t_exit[i])))

    out.buy_qty, out.buy_rev, out.buy_src, out.buy_sku = buy_qty, buy_rev, buy_src, buy_sku
    out.went_checkout, out.t_queue, out.service, out.wait = went, t_queue, service, wait
    out.t_depart, out.t_exit, out.rack_engaged, out.distance = t_depart, t_exit, rack_engaged, distance
    out.leg_counts, out.zone_dwell_s = leg_counts, zone_dwell
    return out


def heatmap(out: EngineOutput, speed: float) -> np.ndarray:
    """Seconds spent per grid cell over the whole run."""
    net = path_network(out.layout.obstacle_signature(out.store))
    grid = net.grid
    heat = np.zeros(grid.nx * grid.ny)
    for key, count in out.leg_counts.items():
        leg = net.legs[key]
        np.add.at(heat, leg.heat_idx, leg.heat_m * (count / speed))
    rects = out.store.zone_rects()
    anchors = out.store.anchors()
    for anchor_id, seconds in out.zone_dwell_s.items():
        idx, w = zone_heat_kernel(out.store, grid, rects[anchor_id], anchors[anchor_id])
        np.add.at(heat, idx, w * seconds)
    return heat.reshape(grid.ny, grid.nx)


def script_to_track(out: EngineOutput, i: int, speed: float, rng: np.random.Generator | None = None,
                    noise_m: float = 0.0, stay_step_s: float = 3.0) -> np.ndarray:
    """Turn a shopper's movement script into (t, x, y) samples (dense walking + wandering dwell)."""
    net = path_network(out.layout.obstacle_signature(out.store))
    anchors = out.store.anchors()
    rects = out.store.zone_rects()
    rows: list[tuple[float, float, float]] = []
    for item in out.scripts.get(i, []):
        if item[0] == "walk":
            _, a, b, t0, t1 = item
            leg = net.legs[(a, b)]
            if leg.length <= 0:
                continue
            walk_s = leg.length / speed
            ts = t0 + leg.arc / leg.length * walk_s
            # any display stop time is added at the end of the leg
            for (x, y), tt in zip(leg.samples, ts):
                rows.append((float(tt), float(x), float(y)))
            if t1 > ts[-1] + 0.5:
                rows.append((float(t1), float(leg.samples[-1, 0]), float(leg.samples[-1, 1])))
        else:
            _, anchor_id, t0, t1 = item
            ax, ay = anchors[anchor_id]
            x0, y0, x1, y1 = rects[anchor_id]
            k = max(1, int((t1 - t0) // stay_step_s))
            for j in range(k + 1):
                tt = t0 + (t1 - t0) * j / k
                if rng is not None and 0 < j < k:
                    x = float(np.clip(ax + rng.normal(0, 0.6), x0 + 0.3, x1 - 0.3))
                    y = float(np.clip(ay + rng.normal(0, 1.2), y0 + 0.3, y1 - 0.3))
                else:
                    x, y = ax, ay
                rows.append((tt, x, y))
    if not rows:
        return np.zeros((0, 3))
    arr = np.asarray(rows, dtype=float)
    arr = arr[np.argsort(arr[:, 0], kind="stable")]
    if rng is not None and noise_m > 0:
        arr[:, 1:] += rng.normal(0, noise_m, size=(len(arr), 2))
        arr[:, 1] = np.clip(arr[:, 1], 0.05, out.store.width - 0.05)
        arr[:, 2] = np.clip(arr[:, 2], 0.05, out.store.height - 0.05)
    return arr
