from storelab.layout import Change, baseline_layout
from storelab.store import STORE
from storelab.validator import Constraints, validate_experiment

BASE = baseline_layout(STORE)


def check(changes, budget=50_000, **kw):
    return validate_experiment(STORE, BASE, changes, Constraints(budget_php=budget, **kw))


def test_valid_display_addition_costs_the_slot_price():
    r = check([Change(type="add_display", category="snacks", slot="endcap_g3_front")])
    assert r.valid and r.cost == 28_000
    assert r.layout.display_map["endcap_g3_front"] == "snacks"


def test_aliases_and_labels_are_resolved():
    r = check([Change(type="add_display", category="Snack", slot="front endcap between aisles 3 and 4")])
    assert r.valid and r.changes[0].category == "snacks" and r.changes[0].slot == "endcap_g3_front"


def test_refrigeration_cannot_move():
    r = check([Change(type="swap_categories", category_a="beverages", category_b="snacks")])
    assert not r.valid and "refrigerat" in r.errors[0].lower()


def test_user_fixed_category_cannot_move():
    r = check([Change(type="swap_categories", category_a="coffee", category_b="snacks")], fixed_categories={"coffee"})
    assert not r.valid


def test_budget_is_enforced():
    r = check([Change(type="add_display", category="snacks", slot="endcap_g3_front")], budget=20_000)
    assert not r.valid and any("budget" in e for e in r.errors)


def test_emergency_egress_slot_is_restricted():
    r = check([Change(type="add_display", category="snacks", slot="exit_stand")])
    assert not r.valid and any("restricted" in e.lower() for e in r.errors)


def test_occupied_slot_and_missing_display():
    assert not check([Change(type="add_display", category="snacks", slot="entrance_table")]).valid
    assert not check([Change(type="remove_display", slot="endcap_g1_front")]).valid
    assert not check([Change(type="move_display", from_slot="endcap_g1_front", to_slot="endcap_g2_front")]).valid


def test_move_existing_display_is_cheap():
    r = check([Change(type="move_display", category="coffee", from_slot="endcap_g2_back", to_slot="endcap_g1_front")])
    assert r.valid and r.cost == STORE.move_display_cost


def test_unknown_ids_and_too_many_changes():
    assert not check([Change(type="add_display", category="durian", slot="endcap_g3_front")]).valid
    assert not check([Change(type="add_display", category="snacks", slot="aisle_9")]).valid
    many = [Change(type="add_display", category="snacks", slot=s) for s in
            ("endcap_g1_front", "endcap_g2_front", "endcap_g3_front", "endcap_g1_back")]
    r = check(many, budget=500_000)
    assert not r.valid and any("at most" in e for e in r.errors)


def test_cancelling_changes_are_rejected():
    r = check([Change(type="swap_categories", category_a="coffee", category_b="snacks"),
               Change(type="swap_categories", category_a="snacks", category_b="coffee")])
    assert not r.valid and any("identical" in e for e in r.errors)
