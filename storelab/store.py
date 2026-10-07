"""The demo store: geometry, fixtures, zones, display slots, products and constraints.

Everything here is fictional demo configuration. Units are metres; x grows to the
right, y grows towards the front of the store (the door side), matching SVG.
"""

from __future__ import annotations

from dataclasses import dataclass, field

Rect = tuple[float, float, float, float]  # (x0, y0, x1, y1)

CATEGORIES: list[str] = ["bakery", "coffee", "snacks", "beverages"]
CATEGORY_LABELS: dict[str, str] = {
    "bakery": "Bakery",
    "coffee": "Coffee",
    "snacks": "Snacks",
    "beverages": "Beverages",
}
CAT_INDEX: dict[str, int] = {c: i for i, c in enumerate(CATEGORIES)}
# Categories that physically need refrigeration and therefore live in refrigerated slots.
REFRIGERATED_CATEGORIES: set[str] = {"beverages"}


@dataclass(frozen=True)
class Fixture:
    id: str
    label: str
    rect: Rect
    kind: str  # shelf | gondola | cooler | counter | staff
    refrigerated: bool = False


@dataclass(frozen=True)
class AisleSlot:
    """A merchandising aisle. A category occupies exactly one aisle slot."""

    id: str
    label: str
    rect: Rect  # shopper-standing area (zone polygon)
    anchor: tuple[float, float]  # where a shopper browsing this aisle stands
    refrigerated: bool = False


@dataclass(frozen=True)
class DisplaySlot:
    """A place a promotional display can go (endcap, table, rack, floor stand)."""

    id: str
    label: str
    rect: Rect
    kind: str  # endcap | table | rack | stand
    add_cost: int  # PHP, fixture + POP material + labour
    free_standing: bool = False  # occupies floor space (becomes an obstacle)
    clear_width_m: float | None = None  # remaining walkway width when occupied
    restricted: bool = False
    restricted_reason: str = ""
    at_checkout: bool = False  # only shoppers queueing at checkout see it


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    category: str
    price: float  # PHP
    margin: float  # fraction of price
    share: float  # share of category units


@dataclass(frozen=True)
class NetworkStore:
    store_id: str
    name: str
    format: str
    weekly_visitors: int


@dataclass(frozen=True)
class StoreSpec:
    store_id: str
    name: str
    region: str
    currency: str
    timezone: str
    width: float
    height: float
    open_hour: int
    close_hour: int
    fixtures: list[Fixture]
    aisles: list[AisleSlot]
    displays: list[DisplaySlot]
    entrance_rect: Rect
    entrance_anchor: tuple[float, float]
    entrance_door: Rect
    checkout_rect: Rect
    checkout_anchor: tuple[float, float]
    exit_rect: Rect
    exit_anchor: tuple[float, float]
    exit_door: Rect
    products: list[Product]
    network: list[NetworkStore]
    # Change costs (PHP)
    move_display_cost: int = 6_000
    remove_display_cost: int = 2_000
    swap_categories_cost: int = 24_000
    # Physical / safety constraints
    min_aisle_width_m: float = 1.2
    max_changes_per_experiment: int = 3
    display_exposure_radius_m: float = 1.5
    checkout_lanes: int = 1
    peak_window: tuple[int, int] = (17, 19)  # 17:00-19:00
    baseline_category_slot: dict[str, str] = field(default_factory=dict)
    baseline_displays: dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------ lookups
    def aisle(self, slot_id: str) -> AisleSlot:
        for a in self.aisles:
            if a.id == slot_id:
                return a
        raise KeyError(slot_id)

    def display(self, slot_id: str) -> DisplaySlot:
        for d in self.displays:
            if d.id == slot_id:
                return d
        raise KeyError(slot_id)

    @property
    def aisle_ids(self) -> list[str]:
        return [a.id for a in self.aisles]

    @property
    def display_ids(self) -> list[str]:
        return [d.id for d in self.displays]

    def anchors(self) -> dict[str, tuple[float, float]]:
        out = {a.id: a.anchor for a in self.aisles}
        out["entrance"] = self.entrance_anchor
        out["checkout"] = self.checkout_anchor
        out["exit"] = self.exit_anchor
        return out

    def zone_rects(self) -> dict[str, Rect]:
        out = {"entrance": self.entrance_rect}
        out.update({a.id: a.rect for a in self.aisles})
        out["checkout"] = self.checkout_rect
        out["exit"] = self.exit_rect
        return out

    def products_in(self, category: str) -> list[Product]:
        return [p for p in self.products if p.category == category]


def build_store() -> StoreSpec:
    fixtures = [
        Fixture("shelf_left", "Wall shelving", (0.0, 1.0, 1.0, 10.0), "shelf"),
        Fixture("g1", "Gondola 1", (5.0, 2.0, 6.0, 10.0), "gondola"),
        Fixture("g2", "Gondola 2", (10.0, 2.0, 11.0, 10.0), "gondola"),
        Fixture("g3", "Gondola 3", (15.0, 2.0, 16.0, 10.0), "gondola"),
        Fixture("coolers", "Refrigerated coolers", (21.0, 1.0, 22.0, 10.0), "cooler", refrigerated=True),
        Fixture("counter", "Checkout counter", (12.0, 13.5, 18.0, 14.0), "counter"),
        Fixture("cashier", "Cashier (staff only)", (12.0, 14.0, 18.0, 15.0), "staff"),
    ]
    aisles = [
        AisleSlot("aisle_1", "Aisle 1", (1.0, 2.5, 5.0, 9.5), (3.0, 5.0)),
        AisleSlot("aisle_2", "Aisle 2", (6.0, 2.5, 10.0, 9.5), (8.0, 5.0)),
        AisleSlot("aisle_3", "Aisle 3", (11.0, 2.5, 15.0, 9.5), (13.0, 5.0)),
        AisleSlot("aisle_4", "Aisle 4 · coolers", (16.0, 2.5, 21.0, 9.5), (18.5, 5.0), refrigerated=True),
    ]
    displays = [
        DisplaySlot("endcap_g1_front", "Front endcap between aisles 1 and 2", (5.0, 9.5, 6.0, 10.0), "endcap", 28_000),
        DisplaySlot("endcap_g2_front", "Front endcap between aisles 2 and 3", (10.0, 9.5, 11.0, 10.0), "endcap", 28_000),
        DisplaySlot("endcap_g3_front", "Front endcap between aisles 3 and 4", (15.0, 9.5, 16.0, 10.0), "endcap", 28_000),
        DisplaySlot("endcap_g1_back", "Back endcap between aisles 1 and 2", (5.0, 2.0, 6.0, 2.5), "endcap", 18_000),
        DisplaySlot("endcap_g2_back", "Back endcap between aisles 2 and 3", (10.0, 2.0, 11.0, 2.5), "endcap", 18_000),
        DisplaySlot("endcap_g3_back", "Back endcap between aisles 3 and 4", (15.0, 2.0, 16.0, 2.5), "endcap", 18_000),
        DisplaySlot(
            "entrance_table", "Promo table at the entrance", (5.5, 12.0, 7.0, 13.0), "table", 22_000,
            free_standing=True, clear_width_m=1.8,
        ),
        DisplaySlot(
            "checkout_rack", "Impulse rack in the checkout queue", (11.0, 12.0, 11.5, 13.5), "rack", 14_000,
            free_standing=True, clear_width_m=1.4, at_checkout=True,
        ),
        DisplaySlot(
            "exit_stand", "Floor stand in the exit lane", (19.5, 12.2, 20.5, 13.0), "stand", 9_000,
            free_standing=True, clear_width_m=0.8, restricted=True,
            restricted_reason="Emergency egress route to the exit door must stay unobstructed",
        ),
    ]
    products = [
        Product("BKY-001", "Pandesal pack (10s)", "bakery", 45.0, 0.38, 0.45),
        Product("BKY-002", "Ensaymada", "bakery", 38.0, 0.40, 0.35),
        Product("BKY-003", "Butter croissant", "bakery", 65.0, 0.42, 0.20),
        Product("COF-001", "3-in-1 coffee sachets (10s)", "coffee", 95.0, 0.22, 0.45),
        Product("COF-002", "Ground coffee 250g", "coffee", 245.0, 0.28, 0.20),
        Product("COF-003", "Canned iced coffee", "coffee", 55.0, 0.30, 0.35),
        Product("SNK-001", "Potato chips 150g", "snacks", 68.0, 0.30, 0.40),
        Product("SNK-002", "Crackers 10s", "snacks", 42.0, 0.27, 0.35),
        Product("SNK-003", "Chocolate bar", "snacks", 55.0, 0.33, 0.25),
        Product("BEV-001", "Bottled water 500ml", "beverages", 25.0, 0.35, 0.40),
        Product("BEV-002", "Soft drink 1.5L", "beverages", 85.0, 0.24, 0.30),
        Product("BEV-003", "Iced tea 500ml", "beverages", 35.0, 0.32, 0.30),
    ]
    network = [
        NetworkStore("DM-001", "Demo Mart BGC (this store)", "mall-front", 10_000),
        NetworkStore("DM-002", "Demo Mart Ortigas", "mall-front", 9_600),
        NetworkStore("DM-003", "Demo Mart Makati CBD", "street", 11_200),
        NetworkStore("DM-004", "Demo Mart Cebu IT Park", "mall-front", 10_400),
        NetworkStore("DM-005", "Demo Mart Alabang", "street", 8_700),
        NetworkStore("DM-006", "Demo Mart Katipunan", "mall-front", 9_100),
    ]
    return StoreSpec(
        store_id="DM-001",
        name="Demo Mart BGC (fictional demo store)",
        region="Metro Manila, PH",
        currency="PHP",
        timezone="Asia/Manila",
        width=22.0,
        height=15.0,
        open_hour=6,
        close_hour=23,
        fixtures=fixtures,
        aisles=aisles,
        displays=displays,
        entrance_rect=(1.0, 12.5, 4.5, 15.0),
        entrance_anchor=(2.25, 14.25),
        entrance_door=(1.0, 14.8, 3.5, 15.0),
        checkout_rect=(11.5, 11.8, 18.0, 13.5),
        checkout_anchor=(15.0, 12.75),
        exit_rect=(19.0, 13.0, 22.0, 15.0),
        exit_anchor=(20.5, 14.25),
        exit_door=(19.5, 14.8, 21.5, 15.0),
        products=products,
        network=network,
        baseline_category_slot={
            "bakery": "aisle_1",
            "snacks": "aisle_2",
            "coffee": "aisle_3",
            "beverages": "aisle_4",
        },
        baseline_displays={
            # The coffee promo sits on a back endcap; the beverage multipack promo greets shoppers.
            "endcap_g2_back": "coffee",
            "entrance_table": "beverages",
        },
    )


STORE: StoreSpec = build_store()
