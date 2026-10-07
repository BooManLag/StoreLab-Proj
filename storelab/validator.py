"""Constraint Validator: deterministic checks on every proposed experiment before it is simulated.

Checks movability, refrigeration, budget, accessibility (clear walkway width),
restricted areas (emergency egress), geometry (walkable routes still exist) and
experiment size. The LLM proposes; this code decides what is physically allowed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .geometry import path_network
from .layout import Change, Layout, describe_change
from .store import CATEGORIES, CATEGORY_LABELS, REFRIGERATED_CATEGORIES, StoreSpec

_CATEGORY_ALIASES = {
    "bakery": "bakery", "bread": "bakery", "breads": "bakery", "pastry": "bakery", "pastries": "bakery",
    "coffee": "coffee", "coffees": "coffee",
    "snacks": "snacks", "snack": "snacks", "chips": "snacks",
    "beverages": "beverages", "beverage": "beverages", "drinks": "beverages", "drink": "beverages",
}


@dataclass
class Constraints:
    budget_php: float
    fixed_categories: set[str] = field(default_factory=set)
    protected_slots: set[str] = field(default_factory=set)
    max_congestion_increase_pct: float = 10.0

    def to_json(self, store: StoreSpec) -> dict:
        fixed = sorted(self.fixed_categories | REFRIGERATED_CATEGORIES)
        return {
            "budget_php": self.budget_php,
            "fixed_categories": fixed,
            "protected_slots": sorted(self.protected_slots),
            "max_checkout_congestion_increase_pct": self.max_congestion_increase_pct,
            "min_clear_walkway_m": store.min_aisle_width_m,
            "max_changes_per_experiment": store.max_changes_per_experiment,
            "refrigeration": "Refrigerated coolers cannot move; refrigerated categories stay in refrigerated slots.",
            "emergency_egress": "The exit lane must stay unobstructed.",
        }


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
    cost: int
    layout: Layout | None
    changes: list[Change]
    change_costs: list[int]
    descriptions: list[str]

    def to_json(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "cost": self.cost,
            "changes": [c.model_dump() for c in self.changes],
            "change_costs": self.change_costs,
            "descriptions": self.descriptions,
        }


def _norm(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def resolve_category(value: str | None) -> str | None:
    key = _norm(value)
    if not key:
        return None
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    for word in key.split():
        if word in _CATEGORY_ALIASES:
            return _CATEGORY_ALIASES[word]
    return None


def resolve_slot(store: StoreSpec, value: str | None) -> str | None:
    key = _norm(value)
    if not key:
        return None
    for d in store.displays:
        if key in (_norm(d.id), _norm(d.label)):
            return d.id
    return None


def validate_experiment(store: StoreSpec, base: Layout, changes: list[Change], constraints: Constraints) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    costs: list[int] = []
    normalized: list[Change] = []
    cat_slot = dict(base.cat_slot)
    displays = dict(base.display_map)
    fixed = set(constraints.fixed_categories) | REFRIGERATED_CATEGORIES

    if not changes:
        errors.append("The experiment has no changes.")
    if len(changes) > store.max_changes_per_experiment:
        errors.append(
            f"{len(changes)} changes proposed; at most {store.max_changes_per_experiment} per experiment "
            "so the result stays attributable."
        )

    for n, raw in enumerate(changes, start=1):
        tag = f"Change {n} ({raw.type})"
        if raw.type == "add_display":
            cat = resolve_category(raw.category)
            slot = resolve_slot(store, raw.slot)
            ch = Change(type="add_display", category=cat, slot=slot)
            if cat is None:
                errors.append(f"{tag}: unknown category '{raw.category}'. Use one of {CATEGORIES}.")
            if slot is None:
                errors.append(f"{tag}: unknown display slot '{raw.slot}'. Use one of {store.display_ids}.")
            if cat and slot:
                d = store.display(slot)
                if slot in displays:
                    errors.append(f"{tag}: {d.label} already holds a {CATEGORY_LABELS[displays[slot]]} display.")
                elif d.restricted:
                    errors.append(f"{tag}: {d.label} is restricted. {d.restricted_reason}.")
                elif slot in constraints.protected_slots:
                    errors.append(f"{tag}: {d.label} is protected by the objective's constraints.")
                elif d.free_standing and (d.clear_width_m or 0) < store.min_aisle_width_m:
                    errors.append(
                        f"{tag}: {d.label} would leave {d.clear_width_m:.1f} m of walkway; minimum is "
                        f"{store.min_aisle_width_m:.1f} m (accessibility)."
                    )
                else:
                    displays[slot] = cat
                    costs.append(d.add_cost)
            normalized.append(ch)
        elif raw.type == "move_display":
            src = resolve_slot(store, raw.from_slot)
            dst = resolve_slot(store, raw.to_slot)
            cat = resolve_category(raw.category) if raw.category else (displays.get(src) if src else None)
            ch = Change(type="move_display", category=cat, from_slot=src, to_slot=dst)
            if src is None:
                errors.append(f"{tag}: unknown source slot '{raw.from_slot}'.")
            if dst is None:
                errors.append(f"{tag}: unknown destination slot '{raw.to_slot}'.")
            if src and dst:
                if src == dst:
                    errors.append(f"{tag}: source and destination are the same slot.")
                elif src not in displays:
                    errors.append(f"{tag}: there is no display at {store.display(src).label} to move.")
                elif cat and displays[src] != cat:
                    errors.append(
                        f"{tag}: {store.display(src).label} holds {CATEGORY_LABELS[displays[src]]}, not "
                        f"{CATEGORY_LABELS.get(cat, cat)}."
                    )
                elif dst in displays:
                    errors.append(f"{tag}: {store.display(dst).label} is already occupied.")
                else:
                    d = store.display(dst)
                    if d.restricted:
                        errors.append(f"{tag}: {d.label} is restricted. {d.restricted_reason}.")
                    elif dst in constraints.protected_slots or src in constraints.protected_slots:
                        errors.append(f"{tag}: a protected slot cannot be changed.")
                    elif d.free_standing and (d.clear_width_m or 0) < store.min_aisle_width_m:
                        errors.append(f"{tag}: {d.label} would leave {d.clear_width_m:.1f} m of walkway; "
                                      f"minimum is {store.min_aisle_width_m:.1f} m.")
                    else:
                        displays[dst] = displays.pop(src)
                        ch = Change(type="move_display", category=displays[dst], from_slot=src, to_slot=dst)
                        costs.append(store.move_display_cost)
            normalized.append(ch)
        elif raw.type == "remove_display":
            slot = resolve_slot(store, raw.slot)
            ch = Change(type="remove_display", slot=slot, category=displays.get(slot) if slot else None)
            if slot is None:
                errors.append(f"{tag}: unknown display slot '{raw.slot}'.")
            elif slot not in displays:
                errors.append(f"{tag}: there is no display at {store.display(slot).label}.")
            elif slot in constraints.protected_slots:
                errors.append(f"{tag}: {store.display(slot).label} is protected.")
            else:
                displays.pop(slot)
                costs.append(store.remove_display_cost)
            normalized.append(ch)
        elif raw.type == "swap_categories":
            a = resolve_category(raw.category_a)
            b = resolve_category(raw.category_b)
            ch = Change(type="swap_categories", category_a=a, category_b=b)
            if a is None or b is None:
                errors.append(f"{tag}: unknown categories '{raw.category_a}' / '{raw.category_b}'.")
            elif a == b:
                errors.append(f"{tag}: cannot swap a category with itself.")
            else:
                blocked = [c for c in (a, b) if c in fixed]
                if blocked:
                    why = [
                        f"{CATEGORY_LABELS[c]} is refrigerated and refrigeration cannot move" if c in REFRIGERATED_CATEGORIES
                        else f"{CATEGORY_LABELS[c]} is fixed by the objective's constraints"
                        for c in blocked
                    ]
                    errors.append(f"{tag}: " + "; ".join(why) + ".")
                else:
                    sa, sb = cat_slot[a], cat_slot[b]
                    mismatch = False
                    for cat, slot in ((a, sb), (b, sa)):
                        if store.aisle(slot).refrigerated != (cat in REFRIGERATED_CATEGORIES):
                            mismatch = True
                            errors.append(f"{tag}: {CATEGORY_LABELS[cat]} cannot go into {store.aisle(slot).label} "
                                          "(refrigeration mismatch).")
                    if not mismatch:
                        cat_slot[a], cat_slot[b] = sb, sa
                        costs.append(store.swap_categories_cost)
            normalized.append(ch)
        else:  # pragma: no cover - pydantic restricts the literal
            errors.append(f"{tag}: unsupported change type.")
            normalized.append(raw)

    total = int(sum(costs))
    if total > constraints.budget_php:
        errors.append(f"Estimated cost ₱{total:,.0f} exceeds the ₱{constraints.budget_php:,.0f} budget.")

    layout = None
    if not errors:
        layout = Layout.make(cat_slot, displays)
        if layout.signature() == base.signature():
            errors.append("The changes cancel out; the layout is identical to the current store.")
            layout = None
        else:
            try:
                path_network(layout.obstacle_signature(store))
            except ValueError as exc:
                errors.append(f"Geometry: the layout blocks a walking route ({exc}).")
                layout = None
    for d_id, cat in (layout.display_map.items() if layout else []):
        if store.display(d_id).at_checkout:
            warnings.append("Displays in the checkout queue add counter time; watch congestion.")

    descriptions = []
    cost_iter = iter(costs)
    for ch in normalized:
        if errors:
            descriptions.append(describe_change(store, ch))
        else:
            descriptions.append(describe_change(store, ch, next(cost_iter)))
    return ValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        cost=total,
        layout=layout,
        changes=normalized,
        change_costs=costs if not errors else [],
        descriptions=descriptions,
    )
