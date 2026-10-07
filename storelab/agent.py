"""StoreLab Agent: an autonomous spatial-experiment designer.

Loop:  interpret -> sense (tools) -> diagnose -> design -> validate -> simulate ->
       critique/revise -> simulate -> rank -> recommend + pilot plan

Gemini makes the judgement calls: reading the objective, forming hypotheses,
designing experiments, critiquing results and explaining. Deterministic tools do
everything that must be right: validation, simulation, ranking and pilot sizing.
The LLM never mutates the twin directly; it emits structured changes that the
validator checks. If Gemini is unavailable, or a call fails, that step falls back to
the offline planner and the event stream says so.
"""

from __future__ import annotations

import string
import time
import uuid
from typing import Iterator, Literal

from pydantic import BaseModel, Field

from .config import AgentSettings
from .layout import Change, Layout, layout_to_json
from .llm import JsonLLM, LLMError, compact_json
from .objective import (CATEGORY_METRICS, ObjectiveSpec, describe_objective, finalize_objective,
                        parse_objective_offline)
from .store import CATEGORY_LABELS
from .planner_offline import OfflinePlanner
from .tools import AgentTools
from .viz import render_floorplan_png
from .world import World

Cat = Literal["bakery", "coffee", "snacks", "beverages"]

SYSTEM_PROMPT = """You are StoreLab Agent, an autonomous spatial-experiment designer for physical retail.
You reason over anonymous shopper-behaviour analytics, a store floor plan and business constraints.
Rules:
1. You propose; deterministic tools validate and simulate. Never invent metrics: cite only numbers that appear in the tool results you are given.
2. Phrase findings as hypotheses ("may"), not conclusions.
3. Store changes must use only the allowed change types and the exact slot ids and category ids provided.
4. Respect constraints: budget, fixed or refrigerated categories, restricted slots, at most 3 changes per experiment.
5. Simulation is a pre-screen. The winner must still be validated with a real store A/B test.
6. No personal data exists or is needed: shoppers are anonymous tracks.
Respond with JSON only, matching the schema."""


# ---------------------------------------------------------------- Gemini wire schemas (no defaults, no nulls)
class WireObjective(BaseModel):
    language: str = Field(description="ISO 639-1 code of the manager's language, e.g. en, ja, ko, id, fil")
    normalized_objective_en: str = Field(description="One-sentence English restatement of the objective")
    metric: Literal["category_revenue", "category_units", "category_attachment", "total_revenue", "basket_value"]
    target_category: Literal["bakery", "coffee", "snacks", "beverages", "none"]
    target_uplift_pct: float = Field(description="Target relative increase in percent; 0 if not stated")
    budget_php: float = Field(description="Budget in Philippine pesos; 0 if not stated")
    max_congestion_increase_pct: float = Field(
        description="Max allowed increase in peak checkout congestion in percent. The stated number if given; "
                    "5 if the manager says not to increase or worsen congestion/queues without a number; "
                    "-1 if congestion or queues are not mentioned")
    fixed_categories: list[Cat] = Field(description="Categories that must not move")
    notes: list[str] = Field(description="Short assumptions you made, in English")


class WireInsight(BaseModel):
    observation: str
    pattern: str
    hypothesis: str
    evidence: list[str]
    categories: list[Cat]


class WireDiagnosis(BaseModel):
    insights: list[WireInsight]


class WireChange(BaseModel):
    type: Literal["add_display", "move_display", "remove_display", "swap_categories"]
    category: str = Field(description="Category id for add_display / move_display, else empty string")
    slot: str = Field(description="Display slot id for add_display / remove_display, else empty string")
    from_slot: str = Field(description="Source display slot id for move_display, else empty string")
    to_slot: str = Field(description="Destination display slot id for move_display, else empty string")
    category_a: str = Field(description="First category id for swap_categories, else empty string")
    category_b: str = Field(description="Second category id for swap_categories, else empty string")


class WireCandidate(BaseModel):
    name: str
    hypothesis: str
    rationale: str
    expected_mechanism: str
    changes: list[WireChange]


class WireDesign(BaseModel):
    candidates: list[WireCandidate]


class WireVerdict(BaseModel):
    candidate_id: str
    verdict: Literal["keep", "reject"]
    reason: str


class WireReview(BaseModel):
    verdicts: list[WireVerdict]
    revisions: list[WireCandidate]
    stop: bool
    reasoning: str


class WireRecommendation(BaseModel):
    title: str
    why: str
    expected_summary: str
    risks: list[str]
    what_to_watch: list[str]


def _wire_to_change(w: WireChange) -> Change:
    clean = lambda s: (s or "").strip() or None  # noqa: E731
    return Change(type=w.type, category=clean(w.category), slot=clean(w.slot), from_slot=clean(w.from_slot),
                  to_slot=clean(w.to_slot), category_a=clean(w.category_a), category_b=clean(w.category_b))


def _wire_to_proposal(w: WireCandidate) -> dict:
    return {"name": w.name.strip()[:80] or "Untitled experiment", "hypothesis": w.hypothesis, "rationale": w.rationale,
            "expected_mechanism": w.expected_mechanism, "changes": [_wire_to_change(c) for c in w.changes]}


LANG_NAMES = {"en": "English", "ja": "Japanese", "ko": "Korean", "id": "Bahasa Indonesia", "fil": "Filipino",
              "tl": "Filipino", "zh": "Chinese", "th": "Thai", "vi": "Vietnamese", "ms": "Malay"}


def apply_overrides(spec: ObjectiveSpec, overrides: dict | None) -> ObjectiveSpec:
    """Values the manager edited directly (objective chips) win over the interpretation of the text."""
    if not overrides:
        return spec
    s = spec.model_copy(deep=True)
    changed = []
    if overrides.get("budget_php") is not None:
        s.budget_php, s.budget_stated = float(overrides["budget_php"]), True
        s.notes = [n for n in s.notes if "budget" not in n.lower()]
        changed.append(f"budget ₱{s.budget_php:,.0f}")
    if overrides.get("max_congestion_increase_pct") is not None:
        s.max_congestion_increase_pct, s.congestion_stated = float(overrides["max_congestion_increase_pct"]), True
        s.notes = [n for n in s.notes if "congestion" not in n.lower()]
        changed.append(f"congestion limit +{s.max_congestion_increase_pct:g}%")
    if overrides.get("target_uplift_pct") is not None:
        s.target_uplift_pct = float(overrides["target_uplift_pct"]) or None
        changed.append(f"target +{s.target_uplift_pct or 0:g}%")
    if overrides.get("target_category"):
        s.target_category = overrides["target_category"]
        if s.metric not in CATEGORY_METRICS:
            s.metric = "category_revenue"
        changed.append(f"category {CATEGORY_LABELS[s.target_category]}")
    if changed:
        s.normalized_objective = describe_objective(s)
        s.notes = s.notes + ["Edited by you: " + ", ".join(changed) + "."]
    return s


class LabAgent:
    def __init__(self, world: World, objective_text: str, settings: AgentSettings, llm: JsonLLM | None,
                 max_rounds: int = 1, overrides: dict | None = None):
        self.w = world
        self.overrides = overrides or {}
        self.text = objective_text.strip()
        self.settings = settings
        self.llm = llm
        self.max_rounds = max(1, min(int(max_rounds), 2))
        self.run_id = uuid.uuid4().hex[:12]
        self.candidates: list[dict] = []
        self.tested: set[str] = set()
        self.objective: ObjectiveSpec | None = None
        self.tools: AgentTools | None = None
        self.planner: OfflinePlanner | None = None
        self.fallbacks: list[dict] = []
        self.gemini_calls = 0

    # ------------------------------------------------------------ plumbing
    def _step(self, sid: str, title: str, status: str, source: str, detail: str = "", **extra) -> dict:
        ev = {"type": "step", "id": sid, "title": title, "status": status, "source": source, "detail": detail}
        ev.update(extra)
        return ev

    def _ask(self, step: str, prompt: str, schema: type[BaseModel], image: bytes | None = None):
        """Call Gemini; return (result, meta) or (None, fallback_reason)."""
        if self.llm is None:
            return None, self.settings.reason
        try:
            self.gemini_calls += 1
            result, meta = self.llm.generate_json(system=SYSTEM_PROMPT, prompt=prompt, schema=schema, image_png=image)
            return result, meta
        except LLMError as exc:
            self.fallbacks.append({"step": step, "reason": str(exc)})
            return None, str(exc)

    def _next_id(self) -> str:
        n = len(self.candidates)
        letters = string.ascii_uppercase
        return letters[n] if n < 26 else f"X{n}"

    def _public(self, c: dict) -> dict:
        return {k: v for k, v in c.items() if k != "change_models"}

    # ------------------------------------------------------------ steps
    def _interpret(self):
        if self.llm is not None:
            prompt = (
                "Store categories: bakery, coffee, snacks, beverages. Beverages are refrigerated; coolers cannot move.\n"
                "Currency: Philippine peso (PHP, ₱). Convert shorthand such as 30k to 30000.\n"
                f"Manager's objective (any language):\n\"\"\"{self.text}\"\"\"\n\n"
                "Map it to the schema. metric: category_revenue for sales of a category; category_units for units "
                "or volume; category_attachment for attachment, cross-sell or 'add to baskets'; total_revenue for "
                "store sales; basket_value for basket size or average transaction. Use target_category 'none' "
                "when no category is named. Include beverages in fixed_categories if the manager says "
                "refrigeration, fridges or coolers cannot move."
            )
            res, meta = self._ask("interpret", prompt, WireObjective)
            if res is not None:
                spec = finalize_objective(
                    self.text, language=res.language, normalized=res.normalized_objective_en, metric=res.metric,
                    target_category=res.target_category, target_uplift_pct=res.target_uplift_pct,
                    budget_php=res.budget_php, max_congestion_increase_pct=res.max_congestion_increase_pct,
                    fixed_categories=list(res.fixed_categories), notes=list(res.notes))
                return spec, "gemini", meta, None
            return parse_objective_offline(self.text), "offline", {}, meta
        return parse_objective_offline(self.text), "offline", {}, self.settings.reason

    def _diagnose(self, metrics: dict):
        obj = self.objective
        prompt = (
            f"Objective (structured): {compact_json(obj.model_dump(exclude={'raw_text'}))}\n\n"
            f"Tool result get_store_metrics(): {compact_json(metrics)}\n\n"
            "Find unusual patterns relevant to the objective and propose hypotheses, not conclusions. "
            "Return 3 or 4 insights. observation: what the data shows, citing numbers from the tool result only. "
            "pattern: the relationship. hypothesis: a testable idea phrased with 'may'. evidence: the metrics used."
        )
        res, meta = self._ask("diagnose", prompt, WireDiagnosis)
        if res is not None and res.insights:
            return [i.model_dump() for i in res.insights[:5]], "gemini", meta, None
        return self.planner.diagnose(), "offline", {}, meta if res is None else "Gemini returned no insights"

    def _design(self, metrics: dict, floor: dict, cons: dict, insights: list[dict]):
        obj = self.objective
        p_primed, p_unprimed = self.tools.display_conversion_prior()
        prompt = (
            f"Objective: {compact_json(obj.model_dump(exclude={'raw_text'}))}\n\n"
            f"Tool result get_constraints(): {compact_json(cons)}\n\n"
            f"Tool result get_floorplan(): {compact_json(floor)}\n"
            "(The attached image shows the same floor plan; slot ids are printed on it.)\n\n"
            f"Display slot exposure per week: {compact_json(metrics['display_slot_exposure'])}\n"
            f"Sequence effects: {compact_json(metrics['sequence_effects'])}\n"
            f"Complement pairs: {compact_json(metrics['complements'])}\n"
            f"Fitted display response: a 'primed' passer (engaged with a complementary category earlier in the trip) "
            f"buys from a promo display about {100 * p_primed:.1f}% of the time vs {100 * p_unprimed:.1f}% for others.\n\n"
            f"Diagnosis: {compact_json(insights)}\n\n"
            "Design exactly 3 candidate physical experiments that test different mechanisms (for example a display "
            "placement on a primed route, an aisle adjacency change, an impulse point in the checkout queue, or "
            "moving an existing display). Rules: use only change types from change_catalog with exact slot ids and "
            "category ids; at most 3 changes each; total cost within budget; add_display only on empty, "
            "unrestricted slots; never move fixed categories. Give each a short name (at most 8 words), the "
            "hypothesis it tests, a rationale citing tool numbers, and the expected mechanism. Do not predict "
            "effect sizes; the simulator will estimate them."
        )
        image = render_floorplan_png(self.w.store, self.w.baseline_layout)
        res, meta = self._ask("design", prompt, WireDesign, image=image)
        if res is not None and res.candidates:
            return [_wire_to_proposal(c) for c in res.candidates[:3]], "gemini", meta, None
        return self.planner.design(), "offline", {}, meta if res is None else "Gemini returned no candidates"

    def _sim_brief(self, c: dict) -> dict:
        brief = {"id": c["id"], "name": c["name"], "round": c["round"], "changes": c["descriptions"], "cost_php": c["cost"],
                 "valid": c["valid"], "verdict": c.get("verdict")}
        if not c["valid"]:
            brief["validation_errors"] = c["errors"]
        if c.get("simulation"):
            d = c["simulation"]["deltas"]
            brief["simulated"] = {
                "primary": f"{d['primary']['label']} {d['primary']['relative_pct']:+.1f}% "
                           f"(95% CI {d['primary']['ci_low_pct']:+.1f} to {d['primary']['ci_high_pct']:+.1f})",
                "checkout_congestion": f"{d['congestion']['relative_pct']:+.1f}% "
                                       f"(95% CI {d['congestion']['ci_low_pct']:+.1f} to {d['congestion']['ci_high_pct']:+.1f})",
                "store_revenue": f"{d['revenue']['relative_pct']:+.1f}%",
                "basket_value": f"{d['basket']['relative_pct']:+.1f}%",
            }
        if c.get("gate"):
            brief["hard_constraint_check"] = c["gate"]
        return brief

    def _review(self, round_no: int, allow_revisions: bool):
        obj = self.objective
        pending = [c for c in self.candidates if not c.get("verdict")]
        k = 2 if allow_revisions else 0
        untested = {s: v for s, v in self.tools.slot_exposure().items()
                    if not v["current_category"] and s not in self._used_slots()}
        prompt = (
            f"Objective: {compact_json(obj.model_dump(exclude={'raw_text'}))}\n"
            f"Hard constraints: peak checkout congestion at most +{obj.max_congestion_increase_pct:g}%, "
            f"budget ₱{obj.budget_php:,.0f}, max {self.w.store.max_changes_per_experiment} changes.\n\n"
            f"Tool results run_simulation (each on {self.w.simulator.n:,} synthetic journeys, same shoppers as "
            f"baseline, paired 95% CIs): {compact_json([self._sim_brief(c) for c in self.candidates])}\n\n"
            f"Unused display slots and their weekly exposure: {compact_json(untested)}\n"
            f"Change catalog: {compact_json(self.tools.change_catalog())}\n\n"
            f"Give a verdict (keep or reject, with a one-sentence reason citing the numbers) for each candidate "
            f"without a verdict yet: {[c['id'] for c in pending]}. Candidates that fail a hard constraint must be "
            "rejected. "
            + (f"Then, if a better idea is plausible, propose up to {k} revised experiments that differ from all "
               "tested ones, for example fixing a rejected idea's flaw or combining the strongest mechanisms "
               "within budget. Return an empty revisions list and stop=true if nothing promising remains."
               if allow_revisions else "Do not propose revisions: return an empty revisions list and stop=true.")
        )
        res, meta = self._ask(f"review_{round_no}", prompt, WireReview)
        if res is not None:
            verdicts = [v.model_dump() for v in res.verdicts]
            revisions = [_wire_to_proposal(r) for r in res.revisions[:k]] if allow_revisions else []
            return {"verdicts": verdicts, "revisions": revisions, "stop": res.stop or not revisions,
                    "reasoning": res.reasoning}, "gemini", meta, None
        out = self.planner.review(self.candidates, self.tested, round_no if allow_revisions else 99)
        return out, "offline", {}, meta

    def _explain(self, best: dict):
        obj = self.objective
        others = [self._sim_brief(c) for c in self.candidates if c["id"] != best["id"]]
        s = self.w.analytics.summary
        lang = LANG_NAMES.get(obj.language, "English")
        prompt = (
            f"Objective: {compact_json(obj.model_dump(exclude={'raw_text'}))}\n\n"
            f"Winner chosen by compare_experiments: {compact_json(self._sim_brief(best))}\n"
            f"Winner hypothesis: {best['hypothesis']}\n"
            f"Other candidates: {compact_json(others)}\n"
            f"Evidence available: sequence effects {compact_json(s['sequence_effects'])}; "
            f"winner slot exposure {compact_json({k: v for k, v in self.tools.slot_exposure().items() if k in self._slots_of(best)})}\n\n"
            "Write the recommendation for a busy store manager, in plain language with no statistics jargon. "
            "title: at most 8 words, naming the change (e.g. 'Snack endcap after Beverages'). why: at most 2 short "
            "sentences: which shoppers it reaches and why that should work, citing at most one number from the "
            "evidence above. expected_summary: one sentence with the expected change in the goal metric, the "
            "checkout congestion change and the cost, using the given numbers. risks: 2-3 short items. "
            f"what_to_watch: 2-3 KPIs. Write every field in {lang}."
        )
        res, meta = self._ask("recommend", prompt, WireRecommendation)
        if res is not None:
            return res.model_dump(), "gemini", meta, None
        return self.planner.explain(best, [c for c in self.candidates if c["id"] != best["id"]]), "offline", {}, meta

    # ------------------------------------------------------------ evaluation
    def _used_slots(self) -> set[str]:
        out = set()
        for c in self.candidates:
            for ch in c.get("change_models", []):
                for s in (ch.slot, ch.to_slot):
                    if s:
                        out.add(s)
        return out

    def _slots_of(self, c: dict) -> set[str]:
        return {s for ch in c.get("change_models", []) for s in (ch.slot, ch.to_slot, ch.from_slot) if s}

    def _new_candidate(self, proposal: dict, round_no: int, source: str) -> dict:
        cid = self._next_id()
        c = {
            "id": cid, "round": round_no, "source": source, "name": proposal["name"],
            "hypothesis": proposal.get("hypothesis", ""), "rationale": proposal.get("rationale", ""),
            "expected_mechanism": proposal.get("expected_mechanism", ""),
            "change_models": list(proposal["changes"]),
            "changes": [ch.model_dump() for ch in proposal["changes"]],
            "descriptions": [], "cost": 0, "valid": None, "errors": [], "warnings": [],
            "simulation": None, "gate": None, "verdict": None, "verdict_reason": None, "verdict_source": None,
            "status": "proposed",
        }
        self.candidates.append(c)
        return c

    def _evaluate(self, c: dict) -> Iterator[dict]:
        v = self.tools.validate_experiment(c["id"], c["change_models"])
        yield self.tools.log[-1]
        c["change_models"] = v.changes
        c["changes"] = [ch.model_dump() for ch in v.changes]
        c["descriptions"] = v.descriptions
        c["cost"] = v.cost
        c["valid"] = v.valid
        c["errors"] = v.errors
        c["warnings"] = v.warnings
        if v.valid and v.layout is not None:
            sig = v.layout.signature()
            c["layout"] = layout_to_json(self.w.store, v.layout)
            if sig in self.tested:
                c["valid"] = False
                c["errors"] = ["Duplicate of an experiment already simulated."]
            else:
                self.tested.add(sig)
        yield {"type": "validation", "id": c["id"], "valid": c["valid"], "errors": c["errors"],
               "warnings": c["warnings"], "cost": c["cost"], "descriptions": c["descriptions"],
               "changes": c["changes"], "layout": c.get("layout")}
        if not c["valid"]:
            c["gate"] = self.tools.gate(c)
            c["status"] = "rejected"
            c["verdict"], c["verdict_reason"], c["verdict_source"] = "reject", c["gate"]["reason"], "validator"
            yield {"type": "critique", "id": c["id"], "verdict": "reject", "reason": c["verdict_reason"],
                   "source": "validator"}
            return
        yield {"type": "simulation", "id": c["id"], "status": "running"}
        t0 = time.perf_counter()
        res, cmp = self.tools.run_simulation(c["id"], v.layout)
        yield self.tools.log[-1]
        c["simulation"] = {
            "deltas": cmp,
            "kpis": res.kpis,
            "congestion": res.congestion,
            "category": res.categories.get(self.planner.target),
            "heatmap": [[round(x, 1) for x in row] for row in res.heat.tolist()],
            "journeys": res.n,
            "seconds": round(time.perf_counter() - t0, 2),
        }
        c["gate"] = self.tools.gate(c)
        c["status"] = "simulated"
        yield {"type": "simulation", "id": c["id"], "status": "done", "result": c["simulation"], "gate": c["gate"]}

    def _apply_verdicts(self, verdicts: list[dict], source: str) -> Iterator[dict]:
        by_id = {c["id"]: c for c in self.candidates}
        for v in verdicts:
            c = by_id.get(str(v.get("candidate_id", "")).strip().upper())
            if c is None or c.get("verdict"):
                continue
            verdict, reason, vsource = v["verdict"], v["reason"], source
            gate = c.get("gate") or {}
            if not gate.get("passed") and verdict == "keep":
                verdict, reason, vsource = "reject", gate.get("reason", "Failed hard constraints."), "constraint check"
            c["verdict"], c["verdict_reason"], c["verdict_source"] = verdict, reason, vsource
            c["status"] = "rejected" if verdict == "reject" else "kept"
            yield {"type": "critique", "id": c["id"], "verdict": verdict, "reason": reason, "source": vsource}
        # Anything the reviewer skipped gets a deterministic verdict.
        for c in self.candidates:
            if c.get("verdict") or not c.get("simulation"):
                continue
            gate = c.get("gate") or {}
            verdict = "keep" if gate.get("passed") else "reject"
            c["verdict"], c["verdict_reason"], c["verdict_source"] = verdict, gate.get("reason", ""), "constraint check"
            c["status"] = "kept" if verdict == "keep" else "rejected"
            yield {"type": "critique", "id": c["id"], "verdict": verdict, "reason": c["verdict_reason"],
                   "source": "constraint check"}

    # ------------------------------------------------------------ main loop
    def run(self) -> Iterator[dict]:
        t_start = time.perf_counter()
        yield {"type": "run", "run_id": self.run_id, "agent": self.settings.public(), "objective_text": self.text,
               "simulated_journeys": self.w.simulator.n}

        yield self._step("interpret", "Understand the objective", "running", "gemini" if self.llm else "offline")
        obj, src, meta, why = self._interpret()
        obj = apply_overrides(obj, self.overrides)
        self.objective = obj
        self.tools = AgentTools(self.w, obj)
        self.planner = OfflinePlanner(self.tools)
        yield self._step("interpret", "Understand the objective", "done", src, obj.normalized_objective,
                         fallback_reason=why if (self.llm and src == "offline") else None, meta=meta)
        yield {"type": "objective", "objective": obj.model_dump(),
               "constraints": self.tools.constraints.to_json(self.w.store), "target_category": self.planner.target}

        yield self._step("sense", "Read the store twin", "running", "engine")
        metrics = self.tools.get_store_metrics()
        yield self.tools.log[-1]
        floor = self.tools.get_floorplan()
        yield self.tools.log[-1]
        cons = self.tools.get_constraints()
        yield self.tools.log[-1]
        yield self._step("sense", "Read the store twin", "done", "engine",
                         f"{metrics['kpis']['visitors']:,} anonymous journeys, {metrics['kpis']['transactions']:,} baskets")

        yield self._step("diagnose", "Find patterns & hypotheses", "running", "gemini" if self.llm else "offline")
        insights, src, meta, why = self._diagnose(metrics)
        yield {"type": "diagnosis", "insights": insights, "source": src}
        yield self._step("diagnose", "Find patterns & hypotheses", "done", src, f"{len(insights)} hypotheses",
                         fallback_reason=why if (self.llm and src == "offline") else None, meta=meta)

        yield self._step("design", "Design candidate experiments", "running", "gemini" if self.llm else "offline")
        proposals, src, meta, why = self._design(metrics, floor, cons, insights)
        new = [self._new_candidate(p, 1, src) for p in proposals]
        for c in new:
            yield {"type": "candidate", "candidate": self._public(c)}
        yield self._step("design", "Design candidate experiments", "done", src, f"{len(new)} candidates",
                         fallback_reason=why if (self.llm and src == "offline") else None, meta=meta)

        yield self._step("simulate", "Validate & simulate", "running", "engine")
        for c in new:
            yield from self._evaluate(c)
        yield self._step("simulate", "Validate & simulate", "done", "engine",
                         f"{sum(1 for c in new if c['simulation'])} simulated, {sum(1 for c in new if not c['valid'])} invalid")

        for r in range(1, self.max_rounds + 1):
            yield self._step(f"review_{r}", f"Critique & revise (round {r})", "running", "gemini" if self.llm else "offline")
            review, src, meta, why = self._review(r, allow_revisions=True)
            yield from self._apply_verdicts(review["verdicts"], src)
            revisions = review["revisions"]
            yield {"type": "review", "round": r, "reasoning": review.get("reasoning", ""), "source": src,
                   "revisions": len(revisions)}
            yield self._step(f"review_{r}", f"Critique & revise (round {r})", "done", src,
                             f"{len(revisions)} revised experiment(s)" if revisions else "No further revisions",
                             fallback_reason=why if (self.llm and src == "offline") else None, meta=meta)
            if not revisions:
                break
            added = [self._new_candidate(p, r + 1, src) for p in revisions]
            for c in added:
                yield {"type": "candidate", "candidate": self._public(c)}
            yield self._step(f"resim_{r}", "Simulate revisions", "running", "engine")
            for c in added:
                yield from self._evaluate(c)
            yield self._step(f"resim_{r}", "Simulate revisions", "done", "engine", f"{len(added)} simulated")

        if any(not c.get("verdict") for c in self.candidates):
            yield self._step("final_review", "Final critique", "running", "gemini" if self.llm else "offline")
            review, src, meta, why = self._review(self.max_rounds + 1, allow_revisions=False)
            yield from self._apply_verdicts(review["verdicts"], src)
            yield self._step("final_review", "Final critique", "done", src, "Verdicts recorded",
                             fallback_reason=why if (self.llm and src == "offline") else None, meta=meta)

        yield self._step("rank", "Rank experiments", "running", "engine")
        ranking = self.tools.compare_experiments(self.candidates)
        yield self.tools.log[-1]
        yield {"type": "ranking", "ranking": ranking}
        yield self._step("rank", "Rank experiments", "done", "engine",
                         f"{sum(1 for r in ranking if r['eligible'])} eligible of {len(ranking)} simulated")

        best_row = next((r for r in ranking if r["eligible"]), None)
        recommendation = plan = None
        if best_row is None:
            yield self._step("recommend", "Recommend a physical test", "done", "engine",
                             "No experiment met the constraints. Loosen the budget or congestion tolerance, "
                             "or try a different objective.")
        else:
            best = next(c for c in self.candidates if c["id"] == best_row["id"])
            best["status"] = "recommended"
            yield self._step("recommend", "Recommend a physical test", "running", "gemini" if self.llm else "offline")
            explanation, src, meta, why = self._explain(best)
            plan = self.tools.recommend_physical_test(best)
            yield self.tools.log[-1]
            target = self.objective.target_uplift_pct
            p = best["simulation"]["deltas"]["primary"]
            recommendation = {
                "candidate_id": best["id"],
                "explanation": explanation,
                "explanation_source": src,
                "meets_target": (p["relative_pct"] >= target) if target else None,
                "target_pct": target,
            }
            yield {"type": "recommendation", "recommendation": recommendation, "plan": plan,
                   "candidate": self._public(best)}
            yield self._step("recommend", "Recommend a physical test", "done", src, explanation["title"],
                             fallback_reason=why if (self.llm and src == "offline") else None, meta=meta)

        yield {
            "type": "done",
            "run_id": self.run_id,
            "objective": self.objective.model_dump(),
            "candidates": [self._public(c) for c in self.candidates],
            "ranking": ranking,
            "recommendation": recommendation,
            "plan": plan,
            "agent": self.settings.public(),
            "gemini_calls": self.gemini_calls,
            "fallbacks": self.fallbacks,
            "tool_calls": self.tools.log,
            "seconds": round(time.perf_counter() - t_start, 1),
        }

    def _layout_of(self, c: dict) -> Layout:
        lay = c["layout"]
        return Layout.make(lay["category_slot"], lay["displays"])
