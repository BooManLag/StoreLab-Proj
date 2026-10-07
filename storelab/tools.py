"""The StoreLab Agent's tools (spec §13). Deterministic, bounded, and logged for the UI.

get_store_metrics · get_floorplan · get_constraints · create_experiment ·
validate_experiment · run_simulation · compare_experiments · recommend_physical_test
"""

from __future__ import annotations

from collections import defaultdict

from .engine import sigmoid
from .geometry import path_network
from .layout import Change, Layout
from .objective import ObjectiveSpec
from .pilot import plan_pilot
from .simulator import SimResult
from .store import CATEGORIES, CATEGORY_LABELS
from .validator import ValidationResult, validate_experiment
from .world import World


SINGULAR = {"bakery": "Bakery", "coffee": "Coffee", "snacks": "Snack", "beverages": "Beverage"}


def place_name(world: World, slot: str) -> str:
    """Name a display slot by what a shopper sees around it, e.g. 'endcap by Coffee & Beverages (back)'."""
    d = world.store.display(slot)
    if d.kind == "endcap":
        g = int(slot.split("_g")[1][0])  # endcap_g3_front -> 3: between aisle 3 and aisle 4
        slot_cat = world.baseline_layout.slot_category()
        a = CATEGORY_LABELS.get(slot_cat.get(f"aisle_{g}", ""), f"Aisle {g}")
        b = CATEGORY_LABELS.get(slot_cat.get(f"aisle_{g + 1}", ""), f"Aisle {g + 1}")
        return f"endcap by {a} & {b}" + (" (back)" if slot.endswith("_back") else "")
    if d.kind == "table":
        return "table at the entrance"
    if d.kind == "rack":
        return "rack in the checkout queue"
    return d.label


def anchor_name(world: World, anchor: str) -> str:
    if anchor in ("entrance", "checkout", "exit"):
        return anchor.capitalize()
    cat = world.baseline_layout.slot_category().get(anchor)
    label = world.store.aisle(anchor).label
    return f"{CATEGORY_LABELS[cat]} ({label})" if cat else label


class AgentTools:
    def __init__(self, world: World, objective: ObjectiveSpec):
        self.w = world
        self.obj = objective
        self.constraints = objective.constraints()
        self.log: list[dict] = []
        self._slot_context = self._compute_slot_context()

    def _record(self, name: str, args: str, summary: str) -> dict:
        entry = {"type": "tool", "name": name, "args": args, "summary": summary}
        self.log.append(entry)
        return entry

    # ------------------------------------------------------------ context helpers
    def _compute_slot_context(self) -> dict[str, list[str]]:
        """Which walking legs pass each display slot most often (baseline)."""
        net = path_network(self.w.baseline_layout.obstacle_signature(self.w.store))
        weights: dict[str, dict[tuple[str, str], int]] = defaultdict(dict)
        for key, count in self.w.baseline.leg_counts.items():
            for _, slot in net.legs[key].display_hits:
                weights[slot][key] = weights[slot].get(key, 0) + count
        out: dict[str, list[str]] = {}
        for d in self.w.store.displays:
            if d.at_checkout:
                out[d.id] = ["every shopper queueing at checkout (buyers only)"]
                continue
            top = sorted(weights.get(d.id, {}).items(), key=lambda kv: -kv[1])[:3]
            out[d.id] = [f"{anchor_name(self.w, a)} → {anchor_name(self.w, b)}" for (a, b), _ in top]
        return out

    def slot_exposure(self) -> dict[str, dict]:
        """Observed exposure for every display slot (camera zone-mapper output), per week."""
        days = self.w.history.n_days
        out = {}
        for d in self.w.analytics.summary["displays"]:
            passes = d["passes"]
            out[d["slot"]] = {
                "passes_per_week": round(passes * 7 / days),
                "share_of_shoppers_pct": round(100 * d["pass_share"], 1),
                "primed_share_pct": {c: (round(100 * d["primed_passes"][c] / passes, 1) if passes else 0.0)
                                     for c in CATEGORIES},
                "current_category": d["category"],
            }
        return out

    def display_conversion_prior(self) -> tuple[float, float]:
        """Fitted P(purchase per pass) for primed and unprimed passers (pooled across categories)."""
        p = self.w.params
        primed = sigmoid(p.disp_engage_a + p.disp_engage_b_primed) * sigmoid(p.disp_buy_a + p.disp_buy_b_primed)
        unprimed = sigmoid(p.disp_engage_a) * sigmoid(p.disp_buy_a)
        return primed, unprimed

    # ------------------------------------------------------------ tools
    def get_store_metrics(self) -> dict:
        s = self.w.analytics.summary
        T = s["transitions"]
        trans = []
        for i, a in enumerate(T["labels"]):
            for j, b in enumerate(T["labels"]):
                p = T["probabilities"][i][j]
                if p >= 0.08 and T["counts"][i][j] >= 50:
                    trans.append({"from": a, "to": b, "p": round(p, 3)})
        trans.sort(key=lambda r: -r["p"])
        k = s["kpis"]
        result = {
            "data_note": "Synthetic demo history: 10,000 anonymous journeys over 7 days + POS baskets.",
            "kpis": {
                "visitors": k["visitors"], "transactions": k["transactions"],
                "conversion_pct": round(100 * k["conversion_rate"], 1), "avg_basket_php": round(k["avg_basket"], 1),
                "peak_checkout_occupancy": round(k["peak_checkout_occupancy"], 3), "peak_window": k["peak_window"],
            },
            "zones": {
                c: {
                    "aisle": z["slot"], "visitors": z["visitors"], "engaged_20s_plus": z["engaged"],
                    "purchases": z["purchases"], "zone_conversion_pct": round(100 * z["zone_conversion"], 1),
                    "avg_dwell_s": round(z["avg_dwell_s"], 1), "attachment_pct": round(100 * z["attachment_rate"], 1),
                    "revenue_php": round(z["revenue"]),
                } for c, z in s["zones"].items()
            },
            "top_transitions": trans[:14],
            "sequence_effects": [
                {"after_engaging": e["from"], "reach": e["to"], "buy_rate_pct": round(100 * e["conversion_after_from"], 1),
                 "otherwise_pct": round(100 * e["conversion_otherwise"], 1), "ratio": round(e["ratio"] or 0, 2)}
                for e in s["sequence_effects"]
            ],
            "complements": [[c["a"], c["b"]] for c in s["complements"]],
            "display_slot_exposure": self.slot_exposure(),
            "checkout_congestion_by_hour": [
                {"hour": r["hour"], "occupancy": r["checkout_occupancy"], "tx_per_day": r["transactions_per_day"]}
                for r in s["hourly"] if r["checkout_occupancy"] >= 0.2
            ],
            "journey_clusters": [
                {"name": c["name"], "share_pct": round(100 * c["share"], 1), "conversion_pct": round(100 * c["conversion"], 1),
                 "top_path": c["top_paths"][0]["path"] if c["top_paths"] else ""}
                for c in s["clusters"]
            ],
            "insights": [i["title"] for i in s["insights"]],
        }
        self._record("get_store_metrics", "", f"{k['visitors']:,} journeys, {k['transactions']:,} transactions, "
                     f"{len(trans)} key transitions, {len(result['display_slot_exposure'])} display slots")
        return result

    def get_floorplan(self) -> dict:
        store, layout = self.w.store, self.w.baseline_layout
        slot_cat = layout.slot_category()
        order = [a.id for a in store.aisles]
        aisles = []
        for i, a in enumerate(store.aisles):
            neighbours = [order[j] for j in (i - 1, i + 1) if 0 <= j < len(order)]
            aisles.append({"slot": a.id, "label": a.label, "category": slot_cat.get(a.id), "refrigerated": a.refrigerated,
                           "adjacent_aisles": neighbours})
        displays = []
        for d in store.displays:
            displays.append({
                "slot": d.id, "label": d.label, "kind": d.kind, "current_category": layout.display_map.get(d.id),
                "add_cost_php": d.add_cost, "free_standing": d.free_standing, "clear_width_m": d.clear_width_m,
                "restricted": d.restricted, "restricted_reason": d.restricted_reason or None,
                "typical_passers": self._slot_context.get(d.id, []),
            })
        result = {
            "store": {"id": store.store_id, "name": store.name, "width_m": store.width, "depth_m": store.height,
                      "layout_note": "Entrance bottom-left, checkout counter bottom-centre, exit bottom-right. "
                                     "Aisles 1–4 run front-to-back; a back corridor links them; Aisle 4 has the coolers."},
            "aisles": aisles,
            "display_slots": displays,
        }
        self._record("get_floorplan", "", f"{len(aisles)} aisles, {len(displays)} display slots "
                     f"({sum(1 for d in displays if d['current_category'])} occupied)")
        return result

    def change_catalog(self) -> list[dict]:
        s = self.w.store
        return [
            {"type": "add_display", "fields": "category, slot", "cost": "the slot's add_cost_php",
             "effect": "Promo display for a category at an empty display slot."},
            {"type": "move_display", "fields": "category, from_slot, to_slot", "cost": f"₱{s.move_display_cost:,}",
             "effect": "Move an existing promo display to an empty slot."},
            {"type": "remove_display", "fields": "slot", "cost": f"₱{s.remove_display_cost:,}",
             "effect": "Remove a promo display."},
            {"type": "swap_categories", "fields": "category_a, category_b", "cost": f"₱{s.swap_categories_cost:,}",
             "effect": "Swap the aisles of two non-refrigerated categories."},
        ]

    def get_constraints(self) -> dict:
        result = self.constraints.to_json(self.w.store)
        result["change_catalog"] = self.change_catalog()
        self._record("get_constraints", "", f"budget ₱{self.constraints.budget_php:,.0f}, congestion ≤ "
                     f"+{self.constraints.max_congestion_increase_pct:g}%, fixed {result['fixed_categories']}")
        return result

    def validate_experiment(self, cid: str, changes: list[Change]) -> ValidationResult:
        res = validate_experiment(self.w.store, self.w.baseline_layout, changes, self.constraints)
        self._record("validate_experiment", cid,
                     f"valid, cost ₱{res.cost:,}" if res.valid else f"invalid: {res.errors[0]}")
        return res

    def run_simulation(self, cid: str, layout: Layout) -> tuple[SimResult, dict]:
        res = self.w.simulator.run(layout)
        cmp = self.w.simulator.compare(self.w.baseline, res, self.obj.metric, self.obj.target_category)
        p, c = cmp["primary"], cmp["congestion"]
        self._record("run_simulation", cid, f"{res.n:,} synthetic journeys: {p['label']} {p['relative_pct']:+.1f}%, "
                     f"congestion {c['relative_pct']:+.1f}%")
        return res, cmp

    def gate(self, cand: dict) -> dict:
        """Hard constraints that no AI verdict can override."""
        if not cand.get("valid"):
            return {"passed": False, "reason": "Failed validation: " + "; ".join(cand.get("errors", [])[:2])}
        d = cand["simulation"]["deltas"]
        cong = d["congestion"]["relative_pct"]
        tol = self.constraints.max_congestion_increase_pct
        shown = f"{cong:+.2f}%" if abs(cong - tol) < 0.05 else f"{cong:+.1f}%"  # don't print "+5.0% > +5%"
        if cong > tol:
            return {"passed": False, "reason": f"Violates congestion constraint: peak checkout congestion "
                                               f"{shown} > +{tol:g}% allowed."}
        if d["primary"]["relative_pct"] <= 0:
            return {"passed": False, "reason": f"No improvement in {d['primary']['label']} "
                                               f"({d['primary']['relative_pct']:+.1f}%)."}
        hi = d["congestion"]["ci_high_pct"]
        if hi > tol:
            return {"passed": True, "at_risk": True,
                    "reason": f"Within constraints (congestion {shown} ≤ +{tol:g}%), but the upper 95% bound "
                              f"({hi:+.1f}%) exceeds the limit: watch congestion closely in the pilot."}
        return {"passed": True, "at_risk": False, "reason": f"Within constraints (congestion {shown} ≤ +{tol:g}%)."}

    def compare_experiments(self, candidates: list[dict]) -> list[dict]:
        rows = []
        for c in candidates:
            if not c.get("valid") or not c.get("simulation"):
                continue
            d = c["simulation"]["deltas"]
            rows.append({
                "id": c["id"], "name": c["name"], "eligible": c["status"] != "rejected",
                "primary_pct": d["primary"]["relative_pct"], "primary_ci_low": d["primary"]["ci_low_pct"],
                "congestion_pct": d["congestion"]["relative_pct"], "cost": c["cost"],
            })
        rows.sort(key=lambda r: (not r["eligible"], -r["primary_pct"], r["cost"]))
        for rank, r in enumerate(rows, start=1):
            r["rank"] = rank
        best = next((r for r in rows if r["eligible"]), None)
        self._record("compare_experiments", f"{len(rows)} simulated",
                     f"best: {best['id']} ({best['primary_pct']:+.1f}%)" if best else "no eligible experiment")
        return rows

    def recommend_physical_test(self, cand: dict) -> dict:
        plan = plan_pilot(self.w.store, self.obj, self.w.baseline, cand)
        self._record("recommend_physical_test", cand["id"],
                     f"{len(plan['test_stores'])} test + {len(plan['control_stores'])} control stores, "
                     f"{plan['duration_days']} days")
        return plan

    # ------------------------------------------------------------ planner helpers
    def estimated_display_gain(self, slot: str, category: str) -> float:
        """Rough weekly extra purchases from a display (used only to shortlist ideas)."""
        exp = self.slot_exposure()[slot]
        passes = exp["passes_per_week"]
        primed = passes * exp["primed_share_pct"][category] / 100.0
        p_primed, p_unprimed = self.display_conversion_prior()
        return primed * p_primed + (passes - primed) * p_unprimed

    def aisle_gap(self, layout: Layout, a: str, b: str) -> int:
        order = [x.id for x in self.w.store.aisles]
        cs = layout.cat_slot
        return abs(order.index(cs[a]) - order.index(cs[b]))
