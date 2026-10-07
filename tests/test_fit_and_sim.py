import numpy as np

from storelab.engine import make_draws, run_engine
from storelab.groundtruth import true_checkout, true_params
from storelab.layout import Layout
from storelab.simulator import relative_delta, summarize
from storelab.store import STORE


def _layout(world, cats=None, displays=None):
    cs = dict(world.baseline_layout.cat_slot)
    dm = dict(world.baseline_layout.display_map)
    cs.update(cats or {})
    for k, v in (displays or {}).items():
        if v is None:
            dm.pop(k, None)
        else:
            dm[k] = v
    return Layout.make(cs, dm)


def test_fitted_parameters_recover_the_hidden_world(world):
    rep = world.fit_report
    tp = true_params()
    assert rep["transition_model"]["converged"] and rep["purchase_model"]["converged"]
    assert abs(rep["transition_model"]["beta_dist_per_m"] - tp.beta_dist) < 0.03
    assert abs(rep["checkout_model"]["base_s"] - 35.0) < 3.0
    assert abs(rep["checkout_model"]["per_item_s"] - 7.0) < 1.0
    assert abs(rep["display_engagement"]["intercept"] - tp.disp_engage_a) < 0.4


def test_twin_reproduces_observed_store(world):
    rows = {r["metric"]: r for r in world.calibration["rows"]}
    assert abs(rows["Transactions / week"]["error_pct"]) < 6
    assert abs(rows["Peak checkout congestion"]["error_pct"]) < 10
    assert world.calibration["max_abs_error_pct"] < 20


def test_simulation_is_deterministic_and_uses_common_random_numbers(world):
    sim = world.simulator
    base = sim.run(world.baseline_layout)
    again = sim.run(world.baseline_layout)
    d = relative_delta(base, again, "category_revenue", "snacks")
    assert d["relative_pct"] == 0 and d["ci_low_pct"] == 0 and d["ci_high_pct"] == 0
    assert base.n == 40_000


def test_checkout_rack_sells_but_congests(world):
    sim = world.simulator
    base = world.baseline
    rack = sim.run(_layout(world, displays={"checkout_rack": "snacks"}))
    endcap = sim.run(_layout(world, displays={"endcap_g3_front": "snacks"}))
    c_rack = sim.compare(base, rack, "category_revenue", "snacks")
    c_end = sim.compare(base, endcap, "category_revenue", "snacks")
    assert c_rack["primary"]["relative_pct"] > 8
    assert c_rack["congestion"]["relative_pct"] > 8
    assert c_end["primary"]["relative_pct"] > 5
    assert c_end["congestion"]["relative_pct"] < 5
    assert c_end["congestion"]["relative_pct"] < c_rack["congestion"]["relative_pct"]


def test_confidence_intervals_bracket_the_point(world):
    sim = world.simulator
    res = sim.run(_layout(world, displays={"endcap_g2_front": "snacks"}))
    for d in sim.compare(world.baseline, res, "category_revenue", "snacks").values():
        if "ci_low_pct" in d:
            assert d["ci_low_pct"] <= d["relative_pct"] <= d["ci_high_pct"]


def test_simulator_ranks_experiments_like_the_hidden_truth(world):
    """Spec §22: does the simulator rank real-world winners above losers? Checked against the hidden world."""
    experiments = {
        "checkout rack": _layout(world, displays={"checkout_rack": "snacks"}),
        "front endcap 3|4": _layout(world, displays={"endcap_g3_front": "snacks"}),
        "front endcap 1|2": _layout(world, displays={"endcap_g1_front": "snacks"}),
        "swap snacks/coffee": _layout(world, cats={"snacks": "aisle_3", "coffee": "aisle_2"}),
    }
    tp, tck = true_params(), true_checkout()
    draws = make_draws(40_000, 28, tp.hour_weights, len(STORE.displays), 4321)
    tb = summarize(run_engine(tp, tck, STORE, world.baseline_layout, draws), tp, STORE)
    pred, truth = {}, {}
    for name, lay in experiments.items():
        pred[name] = world.simulator.compare(world.baseline, world.simulator.run(lay), "category_revenue",
                                             "snacks")["primary"]["relative_pct"]
        truth[name] = relative_delta(tb, summarize(run_engine(tp, tck, STORE, lay, draws), tp, STORE),
                                     "category_revenue", "snacks")["relative_pct"]
    for name in experiments:
        assert np.sign(pred[name]) == np.sign(truth[name]), name
        assert abs(pred[name] - truth[name]) < 8, (name, pred[name], truth[name])
    assert sorted(pred, key=pred.get) == sorted(truth, key=truth.get), (pred, truth)
