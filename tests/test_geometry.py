import numpy as np

from storelab.geometry import PathNetwork, path_network, rect_distance
from storelab.store import STORE


def test_all_anchor_pairs_have_walkable_paths():
    net = path_network(())
    names = list(STORE.anchors())
    assert len(net.legs) == len(names) * (len(names) - 1)
    for (a, b), leg in net.legs.items():
        assert leg.length > 0
        # every densified sample stays on walkable (inflated-free) floor
        rows = np.clip((leg.samples[:, 1] / 0.5).astype(int), 0, net.grid.ny - 1)
        cols = np.clip((leg.samples[:, 0] / 0.5).astype(int), 0, net.grid.nx - 1)
        assert net.grid.free[rows, cols].all(), (a, b)


def test_paths_are_symmetric_in_length():
    net = path_network(())
    for (a, b), leg in net.legs.items():
        assert abs(leg.length - net.legs[(b, a)].length) < 1e-6


def test_paths_never_cut_through_fixtures():
    net = path_network(())
    for leg in net.legs.values():
        for f in STORE.fixtures:
            assert rect_distance(leg.samples[:, 0], leg.samples[:, 1], f.rect).min() > 0.2


def test_display_exposure_geometry_matches_store_story():
    net = path_network(("entrance_table",))
    hits = lambda a, b: {s for _, s in net.legs[(a, b)].display_hits}  # noqa: E731
    # the front endcap between aisles 3|4 sits on the beverages -> checkout route...
    assert "endcap_g3_front" in hits("aisle_4", "checkout")
    # ...but not on the beverages -> exit route
    assert "endcap_g3_front" not in hits("aisle_4", "exit")
    # the checkout rack is only seen while queueing, never from a walking path
    assert all("checkout_rack" not in hits(a, b) for a, b in net.legs)


def test_free_standing_display_changes_paths():
    plain = PathNetwork(STORE, ())
    with_table = PathNetwork(STORE, ("entrance_table",))
    assert with_table.distance("entrance", "aisle_3") >= plain.distance("entrance", "aisle_3") - 1e-9
