"""Store layouts (which category sits where) and the structured changes the agent may propose."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from pydantic import BaseModel

from .store import CATEGORIES, CATEGORY_LABELS, StoreSpec

ChangeType = Literal["add_display", "move_display", "remove_display", "swap_categories"]
CHANGE_TYPES: tuple[str, ...] = ("add_display", "move_display", "remove_display", "swap_categories")


class Change(BaseModel):
    """One structured, machine-checkable store change. The LLM never mutates the twin directly."""

    type: ChangeType
    category: Optional[str] = None  # add_display / move_display
    slot: Optional[str] = None  # add_display / remove_display
    from_slot: Optional[str] = None  # move_display
    to_slot: Optional[str] = None  # move_display
    category_a: Optional[str] = None  # swap_categories
    category_b: Optional[str] = None  # swap_categories


@dataclass(frozen=True)
class Layout:
    """category -> aisle slot, and display slot -> category. Hashable so it can key caches."""

    category_slot: tuple[tuple[str, str], ...]
    displays: tuple[tuple[str, str], ...]

    @staticmethod
    def make(category_slot: dict[str, str], displays: dict[str, str]) -> "Layout":
        return Layout(tuple(sorted(category_slot.items())), tuple(sorted(displays.items())))

    @property
    def cat_slot(self) -> dict[str, str]:
        return dict(self.category_slot)

    @property
    def display_map(self) -> dict[str, str]:
        return dict(self.displays)

    def slot_category(self) -> dict[str, str]:
        return {slot: cat for cat, slot in self.category_slot}

    def signature(self) -> str:
        cats = ",".join(f"{c}@{s}" for c, s in self.category_slot)
        disp = ",".join(f"{s}:{c}" for s, c in self.displays)
        return f"{cats}|{disp}"

    def obstacle_signature(self, store: StoreSpec) -> tuple[str, ...]:
        """Free-standing displays become floor obstacles, so they change walking paths."""
        return tuple(sorted(s for s, _ in self.displays if store.display(s).free_standing))


def baseline_layout(store: StoreSpec) -> Layout:
    return Layout.make(store.baseline_category_slot, store.baseline_displays)


def describe_change(store: StoreSpec, change: Change, cost: int | None = None) -> str:
    def slot_label(slot_id: str | None) -> str:
        if not slot_id:
            return "?"
        try:
            label = store.display(slot_id).label
            return label[0].lower() + label[1:]
        except KeyError:
            return slot_id

    def cat_label(cat: str | None) -> str:
        return CATEGORY_LABELS.get(cat or "", cat or "?")

    def cat_word(cat: str | None) -> str:
        return cat_label(cat).lower()

    if change.type == "add_display":
        text = f"Add a {cat_word(change.category)} promo display on the {slot_label(change.slot)}"
    elif change.type == "move_display":
        text = (
            f"Move the {cat_word(change.category)} promo display from the {slot_label(change.from_slot)}"
            f" to the {slot_label(change.to_slot)}"
        )
    elif change.type == "remove_display":
        text = f"Remove the promo display on the {slot_label(change.slot)}"
    else:
        text = f"Swap the {cat_label(change.category_a)} and {cat_label(change.category_b)} aisles"
    if cost is not None:
        text += f" (₱{cost:,.0f})"
    return text


def layout_to_json(store: StoreSpec, layout: Layout) -> dict:
    return {
        "category_slot": layout.cat_slot,
        "displays": layout.display_map,
        "slot_category": layout.slot_category(),
        "categories": CATEGORIES,
    }
