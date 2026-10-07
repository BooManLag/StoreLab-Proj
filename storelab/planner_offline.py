"""Offline heuristic planner: the agent's fallback when Gemini is not configured or a call fails.

It follows the same loop (diagnose -> design -> review/revise -> explain) with transparent
rules over the same tool outputs. The UI labels every step it handles as "offline planner".
"""

from __future__ import annotations

from .layout import Change, Layout
from .store import CATEGORIES, CATEGORY_LABELS, REFRIGERATED_CATEGORIES
from .tools import SINGULAR, AgentTools, place_name


def _pct(x: float) -> str:
    return f"{x:+.1f}%"


class OfflinePlanner:
    def __init__(self, tools: AgentTools):
        self.t = tools
        self.w = tools.w
        self.obj = tools.obj
        self.target = self._target_category()

    # ------------------------------------------------------------ helpers
    def _target_category(self) -> str:
        if self.obj.target_category:
            return self.obj.target_category
        best, best_val = CATEGORIES[0], -1.0
        for c in CATEGORIES:
            price = sum(self.w.params.sku_price[CATEGORIES.index(c)]) / 3.0
            gain = max(self.t.estimated_display_gain(d.id, c) for d in self.w.store.displays if not d.restricted)
            if gain * price > best_val:
                best, best_val = c, gain * price
        return best

    def _complements(self, cat: str) -> list[str]:
        i = CATEGORIES.index(cat)
        return [CATEGORIES[j] for j in range(len(CATEGORIES)) if self.w.params.comp[i, j]]

    def _allowed_slots(self, layout: Layout, budget_left: float) -> list:
        store = self.w.store
        out = []
        for d in store.displays:
            if d.restricted or d.id in layout.display_map or d.add_cost > budget_left:
                continue
            if d.free_standing and (d.clear_width_m or 0) < store.min_aisle_width_m:
                continue
            out.append(d)
        return out

    def _ranked_slots(self, cat: str, layout: Layout, budget_left: float, exclude: set[str] = frozenset()):
        slots = [d for d in self._allowed_slots(layout, budget_left) if d.id not in exclude]
        return sorted(slots, key=lambda d: -self.t.estimated_display_gain(d.id, cat))

    def _display_proposal(self, cat: str, d, why: str) -> dict:
        exp = self.t.slot_exposure()[d.id]
        passers = ", ".join(self.t._slot_context.get(d.id, [])[:2]) or "n/a"
        comp = self._complements(cat)
        primed = exp["primed_share_pct"][cat]
        return {
            "name": f"{SINGULAR[cat]} {place_name(self.w, d.id)}",
            "hypothesis": (f"A {CATEGORY_LABELS[cat].lower()} display where "
                           f"{'/'.join(CATEGORY_LABELS[c].lower() for c in comp) or 'complementary'}-engaged shoppers "
                           f"pass may lift {CATEGORY_LABELS[cat].lower()} purchases."),
            "rationale": (f"{why} Passed by ~{exp['passes_per_week']:,} shoppers/week "
                          f"({exp['share_of_shoppers_pct']}% of visitors); {primed}% of passers are primed for "
                          f"{CATEGORY_LABELS[cat].lower()}. Typical passers: {passers}."),
            "expected_mechanism": "More primed shoppers see and pick up the category.",
            "changes": [Change(type="add_display", category=cat, slot=d.id)],
        }

    def _swap_proposal(self, cat: str, budget: float) -> dict | None:
        store = self.w.store
        if store.swap_categories_cost > budget:
            return None
        base = self.w.baseline_layout
        fixed = set(self.obj.fixed_categories) | REFRIGERATED_CATEGORIES
        comps = self._complements(cat)
        if not comps:
            return None
        anchor = comps[0]
        current_gap = self.t.aisle_gap(base, cat, anchor)
        best = None
        for a in CATEGORIES:
            for b in CATEGORIES:
                if a >= b or a in fixed or b in fixed:
                    continue
                cs = dict(base.cat_slot)
                cs[a], cs[b] = cs[b], cs[a]
                lay = Layout.make(cs, base.display_map)
                gap = self.t.aisle_gap(lay, cat, anchor)
                if gap < current_gap and (best is None or gap < best[0]):
                    best = (gap, a, b)
        if best is None:
            return None
        _, a, b = best
        return {
            "name": f"Swap the {CATEGORY_LABELS[a]} and {CATEGORY_LABELS[b]} aisles",
            "hypothesis": (f"Placing {CATEGORY_LABELS[cat].lower()} next to {CATEGORY_LABELS[anchor].lower()} "
                           f"(currently {current_gap} aisles apart) may raise {CATEGORY_LABELS[anchor].lower()} → "
                           f"{CATEGORY_LABELS[cat].lower()} trips."),
            "rationale": "Shorter walks between complementary categories raise the chance shoppers combine them.",
            "expected_mechanism": "Transition model: utility falls with walking distance.",
            "changes": [Change(type="swap_categories", category_a=a, category_b=b)],
        }

    # ------------------------------------------------------------ steps
    def diagnose(self) -> list[dict]:
        s = self.w.analytics.summary
        T = self.target
        z = s["zones"][T]
        ranks = sorted(s["zones"].values(), key=lambda r: -r["visitors"])
        rank = [r["category"] for r in ranks].index(T) + 1
        out = [{
            "observation": (f"{CATEGORY_LABELS[T]} aisle: {z['visitors']:,} visitors (traffic rank {rank}/4), "
                            f"{100 * z['engagement_rate']:.0f}% engage 20 s+, zone conversion {100 * z['zone_conversion']:.1f}%."),
            "pattern": "Exposure is not the bottleneck; turning exposure into purchase is." if rank <= 2
                       else "The aisle gets comparatively little traffic.",
            "hypothesis": (f"Changing where {CATEGORY_LABELS[T].lower()} meets primed shoppers may matter more than "
                           "adding raw traffic." if rank <= 2 else
                           f"Bringing {CATEGORY_LABELS[T].lower()} onto busier routes may lift purchases."),
            "evidence": [f"visitors={z['visitors']}", f"engaged={z['engaged']}", f"purchases={z['purchases']}"],
            "categories": [T],
        }]
        for e in s["sequence_effects"]:
            if e["to"] == T and e["ratio"]:
                out.append({
                    "observation": (f"Shoppers who reach {CATEGORY_LABELS[T]} after engaging with "
                                    f"{CATEGORY_LABELS[e['from']]} buy it {e['ratio']:.1f}× as often "
                                    f"({100 * e['conversion_after_from']:.1f}% vs {100 * e['conversion_otherwise']:.1f}%)."),
                    "pattern": f"{CATEGORY_LABELS[e['from']]} engagement primes {CATEGORY_LABELS[T].lower()} purchases.",
                    "hypothesis": (f"Putting {CATEGORY_LABELS[T].lower()} in front of shoppers right after "
                                   f"{CATEGORY_LABELS[e['from']].lower()} may raise attachment."),
                    "evidence": [f"n_after={e['n_after']}", f"n_otherwise={e['n_otherwise']}"],
                    "categories": [e["from"], T],
                })
                break
        for c in self._complements(T):
            gap = self.t.aisle_gap(self.w.baseline_layout, T, c)
            if gap >= 2:
                out.append({
                    "observation": f"{CATEGORY_LABELS[T]} and {CATEGORY_LABELS[c]} are {gap} aisles apart.",
                    "pattern": "Complementary categories are not adjacent.",
                    "hypothesis": "Adjacency may increase combined trips, at the cost of a re-merchandising night.",
                    "evidence": [f"{T}={self.w.baseline_layout.cat_slot[T]}", f"{c}={self.w.baseline_layout.cat_slot[c]}"],
                    "categories": [T, c],
                })
        ph = s["peak_hour"]
        out.append({
            "observation": (f"Checkout congestion peaks at {ph['hour']:02d}:00 "
                            f"({ph['checkout_occupancy']:.2f} shoppers in the checkout area on average)."),
            "pattern": "Anything that adds counter time lands on the busiest hour.",
            "hypothesis": "Impulse displays inside the queue may sell but could slow the line.",
            "evidence": [f"peak_occupancy={s['kpis']['peak_checkout_occupancy']:.3f}"],
            "categories": [],
        })
        return out[:5]

    def design(self) -> list[dict]:
        T = self.target
        budget = self.obj.budget_php
        base = self.w.baseline_layout
        proposals: list[dict] = []
        used: set[str] = set()
        ranked = self._ranked_slots(T, base, budget)
        if ranked:
            top = ranked[0]
            proposals.append(self._display_proposal(T, top, "Highest estimated reach for the budget."))
            used.add(top.id)
        existing = [s for s, c in base.display_map.items() if c == T]
        swap = self._swap_proposal(T, budget)
        if existing and self.w.store.move_display_cost <= budget:
            dests = self._ranked_slots(T, base, budget, exclude=used | {d.id for d in self.w.store.displays if d.at_checkout})
            if dests:
                d = dests[0]
                exp = self.t.slot_exposure()
                proposals.append({
                    "name": f"Move the {CATEGORY_LABELS[T].lower()} promo to the {place_name(self.w, d.id)}",
                    "hypothesis": (f"The existing {CATEGORY_LABELS[T].lower()} promo may reach more primed shoppers at "
                                   f"{d.label}."),
                    "rationale": (f"Now passed by {exp[existing[0]]['passes_per_week']:,}/week; {d.label} by "
                                  f"{exp[d.id]['passes_per_week']:,}/week. Cheap: no new fixture."),
                    "expected_mechanism": "Same display, better exposure.",
                    "changes": [Change(type="move_display", category=T, from_slot=existing[0], to_slot=d.id)],
                })
                used.add(d.id)
        if swap and len(proposals) < 3:
            proposals.append(swap)
        endcaps = [d for d in self._ranked_slots(T, base, budget, exclude=used) if d.kind == "endcap"]
        if endcaps and len(proposals) < 3:
            proposals.append(self._display_proposal(T, endcaps[0], "Best endcap: no floor space taken."))
            used.add(endcaps[0].id)
        for d in self._ranked_slots(T, base, budget, exclude=used):
            if len(proposals) >= 3:
                break
            proposals.append(self._display_proposal(T, d, "Next-best reach."))
            used.add(d.id)
        return proposals[:3]

    def review(self, candidates: list[dict], tested: set[str], round_no: int) -> dict:
        verdicts = []
        for c in candidates:
            if c.get("verdict"):
                continue
            g = c.get("gate") or {}
            if not g.get("passed"):
                verdicts.append({"candidate_id": c["id"], "verdict": "reject", "reason": g.get("reason", "Failed checks.")})
            else:
                p = c["simulation"]["deltas"]["primary"]
                note = ""
                if self.obj.target_uplift_pct and p["relative_pct"] < self.obj.target_uplift_pct:
                    note = f" Below the +{self.obj.target_uplift_pct:g}% target."
                verdicts.append({"candidate_id": c["id"], "verdict": "keep",
                                 "reason": f"{p['label']} {_pct(p['relative_pct'])} "
                                           f"(95% CI {_pct(p['ci_low_pct'])} to {_pct(p['ci_high_pct'])}); "
                                           f"{g['reason']}{note}"})
        if round_no > 1:
            return {"verdicts": verdicts, "revisions": [], "stop": True, "reasoning": "Revision budget used."}
        T = self.target
        base = self.w.baseline_layout
        budget = self.obj.budget_php
        revisions: list[dict] = []
        tested_slots = {ch.slot or ch.to_slot for c in candidates for ch in c.get("change_models", []) if ch.slot or ch.to_slot}
        congested = [c for c in candidates if c.get("gate") and "congestion" in c["gate"].get("reason", "").lower()]
        for c in congested:
            alts = [d for d in self._ranked_slots(T, base, budget, exclude=tested_slots) if not d.at_checkout]
            if alts:
                d = alts[0]
                prop = self._display_proposal(T, d, f"Revision of {c['id']}: keep the impulse idea, move it off the queue.")
                revisions.append(prop)
                tested_slots.add(d.id)
                break
        kept = [c for c in candidates if (c.get("gate") or {}).get("passed")]
        kept.sort(key=lambda c: -c["simulation"]["deltas"]["primary"]["relative_pct"])
        if kept and len(revisions) < 2:
            best = kept[0]
            spent = best["cost"]
            extra = [d for d in self._ranked_slots(T, base, budget - spent, exclude=tested_slots) if not d.at_checkout]
            if extra and len(best["change_models"]) < self.w.store.max_changes_per_experiment:
                d = extra[0]
                revisions.append({
                    "name": f"{best['name']} + {place_name(self.w, d.id)}",
                    "hypothesis": f"Combining {best['id']} with a second {CATEGORY_LABELS[T].lower()} touchpoint may add reach.",
                    "rationale": f"{best['id']} is the strongest so far; ₱{budget - spent:,.0f} of budget remains.",
                    "expected_mechanism": "Additional primed exposure on a different route.",
                    "changes": list(best["change_models"]) + [Change(type="add_display", category=T, slot=d.id)],
                })
        return {
            "verdicts": verdicts,
            "revisions": revisions[:2],
            "stop": not revisions,
            "reasoning": ("Rejected candidates that break hard constraints; proposed revisions that keep the "
                          "best mechanism but avoid the queue or add reach within budget."
                          if revisions else "No better untested idea within budget."),
        }

    def explain(self, best: dict, others: list[dict]) -> dict:
        d = best["simulation"]["deltas"]
        p, c = d["primary"], d["congestion"]
        s = self.w.analytics.summary
        evidence = ""
        for e in s["sequence_effects"]:
            if e["to"] == self.target and e["ratio"]:
                evidence = (f"Shoppers coming from {CATEGORY_LABELS[e['from']]} already buy "
                            f"{CATEGORY_LABELS[self.target].lower()} {e['ratio']:.1f}× as often.")
                break
        T = CATEGORY_LABELS[self.target].lower()
        kinds = {ch.type for ch in best.get("change_models", [])}
        slots = [self.w.store.display(ch.slot or ch.to_slot) for ch in best.get("change_models", [])
                 if (ch.slot or ch.to_slot) and ch.type in ("add_display", "move_display")]
        if slots and all(d.at_checkout for d in slots):
            mechanism = f"Every paying shopper sees {T} at the counter, though it adds time in the queue."
        elif slots:
            mechanism = (f"The display sits on the route those shoppers already walk, so they meet {T} at the right "
                         "moment without adding a stop in the checkout queue.")
        elif "swap_categories" in kinds:
            mechanism = f"Moving {T} next to the category it sells with shortens the walk between the two."
        else:
            mechanism = f"It puts {T} in front of more of the right shoppers."
        why = (evidence.strip() + " " + mechanism).strip()
        risks = [
            "The simulator is calibrated on one week of synthetic history; real shoppers may react differently.",
            "Display novelty can fade after the first weeks.",
            "Extra purchases add counter time at peak hours.",
        ]
        if (best.get("gate") or {}).get("at_risk"):
            risks.insert(0, (f"Congestion is close to the limit: the 95% CI reaches {_pct(c['ci_high_pct'])} against "
                             f"+{self.obj.max_congestion_increase_pct:g}% allowed."))
        return {
            "title": best["name"],
            "why": why,
            "expected_summary": (f"{p['label']} {_pct(p['relative_pct'])} (likely {_pct(p['ci_low_pct'])} to "
                                 f"{_pct(p['ci_high_pct'])}), checkout congestion {_pct(c['relative_pct'])}, "
                                 f"cost ₱{best['cost']:,}."),
            "risks": risks,
            "what_to_watch": [p["label"], "Peak checkout congestion 17:00–19:00", "Total store revenue"],
        }
