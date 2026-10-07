import re

import numpy as np

from storelab.export import TABLES, to_csv


def test_synthetic_history_matches_spec_volumes(world):
    h = world.history
    assert h.n_journeys == 10_000
    assert 1_800 <= h.n_transactions <= 2_200  # spec: ~2,000 transactions
    assert h.n_days == 7


def test_journeys_are_anonymous(world):
    h = world.history
    assert all(re.fullmatch(r"anon_[0-9a-f]{6}", t) for t in h.track_id)
    assert len(set(h.track_id)) == len(h.track_id)
    for table in TABLES:
        header = to_csv(world, table).splitlines()[0].lower()
        for pii in ("name,", "email", "phone", "face", "gender", "age"):
            if table in ("stores", "zones", "products") and pii == "name,":
                continue  # store / zone / product names, not people
            assert pii not in header, (table, pii)


def test_pos_join_links_baskets_to_journeys(world):
    m = world.analytics.match
    assert m["match_rate"] > 0.97
    assert m["accuracy_vs_synthetic_truth"] > 0.97


def test_funnel_is_monotone(world):
    for z in world.analytics.summary["zones"].values():
        assert z["visitors"] >= z["engaged"] >= 0
        assert z["visitors"] >= z["purchases"] >= 0
        assert 0 <= z["zone_conversion"] <= 1


def test_transition_rows_are_probabilities(world):
    T = world.analytics.summary["transitions"]
    P = np.array(T["probabilities"])
    counts = np.array(T["counts"])
    for r in range(len(P)):
        if counts[r].sum() > 0:
            assert abs(P[r].sum() - 1) < 1e-3


def test_complements_are_learned_from_behaviour(world):
    pairs = {frozenset(p) for p in world.fit_report["complements"]}
    assert frozenset({"bakery", "coffee"}) in pairs
    assert frozenset({"snacks", "beverages"}) in pairs


def test_insights_flag_snacks_traffic_vs_conversion(world):
    kinds = {(i["type"], i["category"]) for i in world.analytics.summary["insights"]}
    assert ("traffic_vs_conversion", "snacks") in kinds
    assert any(t == "congestion" for t, _ in kinds)


def test_heatmap_shape_and_mass(world):
    H = world.analytics.heatmap
    assert H.shape == (30, 44)
    assert (H >= 0).all() and H.sum() > 0


def test_csv_exports_have_rows(world):
    assert len(to_csv(world, "journey_events").splitlines()) > 40_000
    assert len(to_csv(world, "transactions").splitlines()) == len(world.history.tl_sku) + 1


def test_briefing_has_opportunity_friction_pattern(world):
    b = world.analytics.summary["briefing"]
    assert [x["kind"] for x in b] == ["opportunity", "friction", "pattern"]
    assert b[0]["category"] == "snacks" and b[0]["action"]["type"] == "goal"
    assert "snack sales" in b[0]["action"]["goal"]
    assert b[1]["zones"] == ["checkout"] and b[1]["action"]["type"] == "analytics"
    assert b[2]["title"].startswith("Shoppers coming from Beverages buy snacks")