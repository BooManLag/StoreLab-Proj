"""Synthetic demo history: 10,000 anonymous shopper journeys and their POS transactions.

This is clearly-labelled SYNTHETIC data. A hidden "true" behaviour model (shopping
missions the rest of StoreLab never sees) is run through the shared engine on the
baseline layout. Only what cameras + POS would record is exported as the observed
history: anonymous zone events, display passes/interactions, 2 Hz floor trajectories
and POS baskets. The POS <-> journey link is withheld; analytics re-derives it by
time-window matching at the checkout, as it would have to in a real store.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import norm

from .engine import BehaviorParams, CheckoutParams, EngineOutput, make_draws, run_engine, script_to_track
from .layout import Layout, baseline_layout
from .store import CATEGORIES, STORE, StoreSpec

N_JOURNEYS = 10_000
N_DAYS = 7
START_DATE = dt.date(2026, 9, 21)  # Monday
UTC_OFFSET = "+08:00"

# Hidden missions. Analytics must rediscover segments from behaviour alone.
_MISSIONS = ["breakfast", "snack_drink", "quick_drink", "browser"]


def _hour_profile() -> np.ndarray:
    w = np.zeros(24)
    for h, v in {6: 3, 7: 7, 8: 8, 9: 5, 10: 4, 11: 5, 12: 7, 13: 6, 14: 4, 15: 4, 16: 5,
                 17: 9, 18: 10, 19: 8, 20: 6, 21: 5, 22: 4}.items():
        w[h] = v
    return w / w.sum()


def _mission_by_hour() -> np.ndarray:
    m = np.zeros((24, 4))
    for h in range(24):
        if h <= 9:
            m[h] = [0.28, 0.06, 0.12, 0.54]
        elif h <= 11:
            m[h] = [0.12, 0.12, 0.16, 0.60]
        elif h <= 13:
            m[h] = [0.06, 0.16, 0.20, 0.58]
        elif h <= 16:
            m[h] = [0.05, 0.20, 0.14, 0.61]
        elif h <= 19:
            m[h] = [0.05, 0.24, 0.13, 0.58]
        else:
            m[h] = [0.03, 0.24, 0.10, 0.63]
    # Mall-front store: most visitors browse, so the browser share is boosted
    # (calibrated so ~10,000 journeys yield ~2,000 transactions).
    m[:, 3] *= 1.9
    return m / m.sum(axis=1, keepdims=True)


def _lognormal_table(offset: float, median: float, sigma: float) -> list[float]:
    probs = np.clip(np.linspace(0.0, 1.0, 201), 0.002, 0.998)
    return [float(offset + median * np.exp(sigma * z)) for z in norm.ppf(probs)]


def _uniform_table(lo: float, hi: float) -> list[float]:
    return [float(v) for v in np.linspace(lo, hi, 201)]


def basket_tables(store: StoreSpec):
    sku_ids, sku_price, sku_cum = [], [], []
    for c in CATEGORIES:
        prods = store.products_in(c)
        sku_ids.append([p.sku for p in prods])
        sku_price.append([p.price for p in prods])
        shares = np.array([p.share for p in prods], dtype=float)
        sku_cum.append(list(np.cumsum(shares / shares.sum())))
    return sku_ids, sku_price, sku_cum


def true_params(store: StoreSpec = STORE) -> BehaviorParams:
    sku_ids, sku_price, sku_cum = basket_tables(store)
    comp = np.zeros((4, 4), dtype=bool)
    for a, b in [("bakery", "coffee"), ("snacks", "beverages")]:
        ia, ib = CATEGORIES.index(a), CATEGORIES.index(b)
        comp[ia, ib] = comp[ib, ia] = True
    return BehaviorParams(
        segment_ids=list(_MISSIONS),
        segment_labels=["Breakfast run", "Snack & drink", "Quick drink", "Browser"],
        hour_weights=_hour_profile(),
        segment_given_hour=_mission_by_hour(),
        #                bakery coffee snacks beverages
        asc=np.array([
            [1.6, 1.4, -0.6, -0.2],   # breakfast
            [-1.0, -0.8, 1.3, 1.7],   # snack & drink
            [-1.5, -1.0, -0.2, 2.2],  # quick drink
            [0.3, 0.1, 0.5, 0.4],     # browser
        ]),
        asc_end=np.array([-1.3, -1.3, -0.8, -1.4]),
        beta_dist=0.10,
        beta_comp=0.9,
        beta_visited=2.5,
        beta_steps=0.65,
        comp=comp,
        p_engage=np.array([
            [0.85, 0.75, 0.20, 0.30],
            [0.20, 0.20, 0.70, 0.75],
            [0.10, 0.10, 0.30, 0.65],
            [0.30, 0.30, 0.35, 0.30],
        ]),
        dwell_engaged_q=[
            _lognormal_table(20.0, 25.0, 0.6),  # bakery  (median ~45 s)
            _lognormal_table(20.0, 30.0, 0.6),  # coffee  (~50 s)
            _lognormal_table(20.0, 20.0, 0.6),  # snacks  (~40 s)
            _lognormal_table(20.0, 15.0, 0.6),  # beverages (~35 s)
        ],
        dwell_passing_q=[_uniform_table(4.0, 19.0) for _ in CATEGORIES],
        zone_a=np.array([
            [-1.7, -2.0, -3.8, -3.4],
            [-3.8, -4.0, -2.2, -1.7],
            [-4.3, -3.8, -3.4, -1.3],
            [-5.5, -5.6, -5.3, -5.0],
        ]),
        zone_b_dwell=0.8,
        zone_b_engaged=1.3,
        zone_b_primed=1.0,
        # Promo displays mostly work on shoppers already "primed" by a complementary category.
        disp_engage_a=-2.0,
        disp_engage_b_primed=2.0,
        disp_buy_a=-2.8,
        disp_buy_b_primed=2.0,
        leak=0.001,
        sku_ids=sku_ids,
        sku_price=sku_price,
        sku_cum=sku_cum,
        qty_cum=[[0.55, 0.85, 1.0], [0.75, 0.95, 1.0], [0.60, 0.90, 1.0], [0.50, 0.82, 1.0]],
        walk_speed=0.9,
        shopper_noise_sd=0.4,
    )


def true_checkout() -> CheckoutParams:
    return CheckoutParams(base_s=35.0, per_item_s=7.0, sd_s=8.0, lanes=STORE.checkout_lanes, rack_dwell_s=14.0)


@dataclass
class History:
    """Observed tables, in the shape of the spec's data model (Â§10)."""

    store_id: str
    start_date: dt.date
    n_days: int
    layout: Layout
    # journeys
    track_id: list[str]
    day: np.ndarray
    t_arrive: np.ndarray
    t_leave: np.ndarray
    # zone events: one row per zone visit (entrance, aisles, checkout, exit)
    ze_track: np.ndarray
    ze_zone: list[str]
    ze_enter: np.ndarray
    ze_exit: np.ndarray
    ze_x: np.ndarray
    ze_y: np.ndarray
    # display events: every defined display slot passed, and whether the shopper interacted
    de_track: np.ndarray
    de_slot: list[str]
    de_time: np.ndarray
    de_engaged: np.ndarray
    # 2 Hz trajectories (CSR layout)
    traj_offsets: np.ndarray
    traj: np.ndarray  # (m, 3) float32: t, x, y
    # POS
    tx_id: list[str]
    tx_day: np.ndarray
    tx_time: np.ndarray
    tl_tx: np.ndarray  # line -> transaction row
    tl_sku: list[str]
    tl_category: list[str]
    tl_qty: np.ndarray
    tl_price: np.ndarray
    tl_revenue: np.ndarray
    tl_discount: np.ndarray
    # withheld ground truth, used only to *score* the pipeline (never to fit models)
    truth: dict = field(default_factory=dict)

    @property
    def n_journeys(self) -> int:
        return len(self.track_id)

    @property
    def n_transactions(self) -> int:
        return len(self.tx_id)

    def timestamp(self, day: int, seconds: float) -> str:
        d = self.start_date + dt.timedelta(days=int(day))
        s = int(round(seconds))
        return f"{d.isoformat()}T{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}{UTC_OFFSET}"


def _anon_ids(rng: np.random.Generator, n: int, prefix: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    while len(out) < n:
        v = f"{prefix}{int(rng.integers(0, 16**6)):06x}"
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def generate_history(seed: int, store: StoreSpec = STORE, n: int = N_JOURNEYS, days: int = N_DAYS) -> History:
    params = true_params(store)
    checkout = true_checkout()
    layout = baseline_layout(store)
    draws = make_draws(n, days, params.hour_weights, len(store.displays), seed)
    out: EngineOutput = run_engine(params, checkout, store, layout, draws, script_ids=set(range(n)))
    rng = np.random.default_rng(seed + 1)

    track_id = _anon_ids(rng, n, "anon_")
    # ---- trajectories at ~2 Hz with CV-like position noise
    offsets = [0]
    chunks = []
    for i in range(n):
        tr = script_to_track(out, i, params.walk_speed, rng=rng, noise_m=0.12)
        if len(tr) > 2:
            keep = np.zeros(len(tr), dtype=bool)
            keep[::2] = True
            keep[-1] = True
            tr = tr[keep]
        chunks.append(tr.astype(np.float32))
        offsets.append(offsets[-1] + len(tr))
    traj = np.vstack(chunks) if chunks else np.zeros((0, 3), dtype=np.float32)
    t_leave = np.array([float(chunks[i][-1, 0]) if len(chunks[i]) else out.arrival[i] for i in range(n)])

    # ---- zone events
    anchors = store.anchors()
    ze_track, ze_zone, ze_enter, ze_exit, ze_x, ze_y = [], [], [], [], [], []

    def add_zone(i: int, zone: str, t0: float, t1: float) -> None:
        ax, ay = anchors[zone]
        ze_track.append(i)
        ze_zone.append(zone)
        ze_enter.append(t0 + rng.normal(0, 0.5))
        ze_exit.append(t1 + rng.normal(0, 0.5))
        ze_x.append(ax + rng.normal(0, 0.3))
        ze_y.append(ay + rng.normal(0, 0.3))

    visits_by_shopper: dict[int, list[int]] = {}
    for row, i in enumerate(out.v_shopper):
        visits_by_shopper.setdefault(i, []).append(row)
    slot_of = layout.cat_slot
    for i in range(n):
        add_zone(i, "entrance", out.arrival[i], out.arrival[i] + 2.0)
        for row in visits_by_shopper.get(i, []):
            c = out.v_cat[row]
            t0 = out.v_enter[row]
            add_zone(i, slot_of[CATEGORIES[c]], t0, t0 + out.v_dwell[row])
        if out.went_checkout[i]:
            add_zone(i, "checkout", float(out.t_queue[i]), float(out.t_depart[i]))
        add_zone(i, "exit", float(out.t_exit[i]) - 2.0, float(out.t_exit[i]))
    ze_enter_a = np.asarray(ze_enter)
    ze_exit_a = np.maximum(np.asarray(ze_exit), ze_enter_a)

    # ---- display events (camera zone-mapper output: passes + interactions)
    slot_ids = store.display_ids
    de_track = np.asarray(out.d_shopper, dtype=int)
    de_slot = [slot_ids[k] for k in out.d_slot]
    de_time = np.asarray(out.d_time) + rng.normal(0, 0.5, size=len(out.d_time))
    de_engaged = np.asarray(out.d_engaged, dtype=bool)

    # ---- POS: one transaction per checkout visit, timestamped at payment with clock jitter
    buyers = np.nonzero(out.went_checkout)[0]
    tx_rows = []
    for i in buyers:
        tx_rows.append((int(out.day[i]), float(out.t_depart[i]) + rng.normal(0, 2.0), int(i)))
    tx_rows.sort(key=lambda r: (r[0], r[1]))
    tx_id = _anon_ids(rng, len(tx_rows), "TX")
    tl_tx, tl_sku, tl_cat, tl_qty, tl_price, tl_rev = [], [], [], [], [], []
    tx_truth_track = []
    for row, (d, t, i) in enumerate(tx_rows):
        tx_truth_track.append(i)
        for c in range(len(CATEGORIES)):
            q = int(out.buy_qty[i, c])
            if q <= 0:
                continue
            k = int(out.buy_sku[i, c])
            price = params.sku_price[c][k]
            tl_tx.append(row)
            tl_sku.append(params.sku_ids[c][k])
            tl_cat.append(CATEGORIES[c])
            tl_qty.append(q)
            tl_price.append(price)
            tl_rev.append(price * q)

    return History(
        store_id=store.store_id,
        start_date=START_DATE,
        n_days=days,
        layout=layout,
        track_id=track_id,
        day=np.asarray(out.day, dtype=int),
        t_arrive=np.asarray(out.arrival, dtype=float),
        t_leave=t_leave,
        ze_track=np.asarray(ze_track, dtype=int),
        ze_zone=ze_zone,
        ze_enter=ze_enter_a,
        ze_exit=ze_exit_a,
        ze_x=np.asarray(ze_x),
        ze_y=np.asarray(ze_y),
        de_track=de_track,
        de_slot=de_slot,
        de_time=de_time,
        de_engaged=de_engaged,
        traj_offsets=np.asarray(offsets, dtype=np.int64),
        traj=traj,
        tx_id=tx_id,
        tx_day=np.asarray([r[0] for r in tx_rows], dtype=int),
        tx_time=np.asarray([r[1] for r in tx_rows], dtype=float),
        tl_tx=np.asarray(tl_tx, dtype=int),
        tl_sku=tl_sku,
        tl_category=tl_cat,
        tl_qty=np.asarray(tl_qty, dtype=int),
        tl_price=np.asarray(tl_price, dtype=float),
        tl_revenue=np.asarray(tl_rev, dtype=float),
        tl_discount=np.zeros(len(tl_qty)),
        truth={
            "tx_track": np.asarray(tx_truth_track, dtype=int),
            "mission": out.seg.copy(),
            "missions": list(_MISSIONS),
        },
    )
