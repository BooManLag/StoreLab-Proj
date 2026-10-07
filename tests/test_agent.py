import os
from types import SimpleNamespace

import pytest

from storelab.agent import (LabAgent, WireCandidate, WireChange, WireDesign, WireDiagnosis, WireInsight,
                            WireObjective, WireRecommendation, WireReview, WireVerdict)
from storelab.config import AgentSettings
from storelab.llm import GeminiLLM, LLMError, inline_schema

OFFLINE = AgentSettings("offline", "gemini-3.5-flash", "tests", 30, None)
GEMINI = AgentSettings("gemini-api", "gemini-3.5-flash", "tests", 30, "low")


def run(world, text, settings=OFFLINE, llm=None, rounds=1):
    return list(LabAgent(world, text, settings, llm, max_rounds=rounds).run())


def chg(type_, **kw):
    base = dict(category="", slot="", from_slot="", to_slot="", category_a="", category_b="")
    base.update(kw)
    return WireChange(type=type_, **base)


class FakeGemini:
    """Plays the Gemini role with canned, schema-valid answers."""

    model = "fake-gemini"

    def __init__(self, fail_steps=()):
        self.calls = []
        self.fail_steps = set(fail_steps)

    def generate_json(self, *, system, prompt, schema, image_png=None):
        self.calls.append((schema.__name__, image_png is not None))
        if schema.__name__ in self.fail_steps:
            raise LLMError("simulated outage")
        if schema is WireObjective:
            return WireObjective(language="en", normalized_objective_en="Grow snack sales 10% within ₱30k, no extra queue.",
                                 metric="category_revenue", target_category="snacks", target_uplift_pct=10,
                                 budget_php=30_000, max_congestion_increase_pct=5, fixed_categories=["beverages"],
                                 notes=["Interpreted 'no extra queue' as +5%."]), {"latency_s": 0.1}
        if schema is WireDiagnosis:
            return WireDiagnosis(insights=[WireInsight(observation="Snacks: 5,267 visitors, 9.8% convert.",
                                                       pattern="High exposure, weak conversion.",
                                                       hypothesis="Placing snacks on the beverages route may lift sales.",
                                                       evidence=["visitors=5267"], categories=["snacks"])]), {}
        if schema is WireDesign:
            return WireDesign(candidates=[
                WireCandidate(name="Snacks at checkout", hypothesis="h", rationale="r", expected_mechanism="m",
                              changes=[chg("add_display", category="snacks", slot="checkout_rack")]),
                WireCandidate(name="Snacks by the exit", hypothesis="h", rationale="r", expected_mechanism="m",
                              changes=[chg("add_display", category="snacks", slot="exit_stand")]),  # restricted!
                WireCandidate(name="Snacks endcap after beverages", hypothesis="h", rationale="r", expected_mechanism="m",
                              changes=[chg("add_display", category="snacks", slot="endcap_g3_front")]),
            ]), {}
        if schema is WireReview:
            # keep the rack (the hard-constraint check must override this) and propose one revision
            return WireReview(verdicts=[WireVerdict(candidate_id="A", verdict="keep", reason="sells most"),
                                        WireVerdict(candidate_id="C", verdict="keep", reason="good")],
                              revisions=[WireCandidate(name="Back endcap", hypothesis="h", rationale="r",
                                                       expected_mechanism="m",
                                                       changes=[chg("add_display", category="snacks",
                                                                    slot="endcap_g3_back")])] if "Do not propose" not in prompt else [],
                              stop=False, reasoning="Try the back endcap."), {}
        if schema is WireRecommendation:
            return WireRecommendation(title="Snacks endcap", why="Because.", expected_summary="Sales up.",
                                      risks=["novelty"], what_to_watch=["snacks sales"]), {}
        raise AssertionError(schema)


def by_type(events, t):
    return [e for e in events if e["type"] == t]


def test_offline_loop_rejects_queue_idea_and_recommends(world):
    ev = run(world, "Increase snack sales by 10%. Budget ₱30k. Don't increase checkout congestion.")
    done = ev[-1]
    assert done["type"] == "done" and done["recommendation"] and done["plan"]
    cands = {c["id"]: c for c in done["candidates"]}
    rack = next(c for c in cands.values() if any(ch.get("slot") == "checkout_rack" for ch in c["changes"]))
    assert rack["status"] == "rejected" and "congestion" in rack["verdict_reason"].lower()
    rec = cands[done["recommendation"]["candidate_id"]]
    assert rec["status"] == "recommended"
    assert rec["simulation"]["deltas"]["congestion"]["relative_pct"] <= 5
    assert any(c["round"] == 2 for c in cands.values()), "the agent should revise after critique"
    names = {t["name"] for t in done["tool_calls"]}
    assert {"get_store_metrics", "get_floorplan", "get_constraints", "validate_experiment",
            "run_simulation", "compare_experiments", "recommend_physical_test"} <= names
    assert done["plan"]["duration_days"] >= 14 and len(done["plan"]["test_stores"]) >= 2


def test_event_stream_order(world):
    ev = run(world, "Increase coffee attachment. Budget ₱50,000.")
    types = [e["type"] for e in ev]
    assert types[0] == "run" and types[-1] == "done"
    assert types.index("objective") < types.index("candidate") < types.index("ranking") < types.index("done")
    for e in by_type(ev, "simulation"):
        if e["status"] == "done":
            assert len(e["result"]["heatmap"]) == 30


def test_gemini_path_with_hard_constraint_override(world):
    fake = FakeGemini()
    ev = run(world, "snacks +10%", GEMINI, fake)
    done = ev[-1]
    assert done["gemini_calls"] >= 5 and not done["fallbacks"]
    assert ("WireDesign", True) in fake.calls, "the floor-plan image must be sent with the design prompt"
    cands = {c["id"]: c for c in done["candidates"]}
    assert cands["B"]["valid"] is False and cands["B"]["verdict_source"] == "validator"
    # Gemini said keep, but the rack breaks the congestion limit: the constraint check wins.
    assert cands["A"]["status"] == "rejected" and cands["A"]["verdict_source"] == "constraint check"
    assert "D" in cands and cands["D"]["round"] == 2
    assert done["recommendation"]["explanation"]["title"] == "Snacks endcap"
    srcs = {e["id"]: e["source"] for e in by_type(ev, "step") if e["status"] == "done"}
    assert srcs["design"] == "gemini" and srcs["simulate"] == "engine"


def test_gemini_outage_falls_back_per_step(world):
    fake = FakeGemini(fail_steps={"WireDesign", "WireRecommendation"})
    ev = run(world, "snacks +10%", GEMINI, fake)
    done = ev[-1]
    steps = {e["id"]: e for e in by_type(ev, "step") if e["status"] == "done"}
    assert steps["design"]["source"] == "offline" and "outage" in steps["design"]["fallback_reason"]
    assert steps["interpret"]["source"] == "gemini"
    assert done["recommendation"]["explanation_source"] == "offline"
    assert len(done["fallbacks"]) == 2


def test_inline_schema_is_gemini_safe():
    for model in (WireObjective, WireDesign, WireReview, WireDiagnosis, WireRecommendation):
        text = str(inline_schema(model))
        assert "$ref" not in text and "$defs" not in text and "anyOf" not in text and "'default'" not in text


def _llm(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")
    return GeminiLLM(GEMINI)


def test_gemini_wrapper_retries_invalid_json(monkeypatch):
    llm = _llm(monkeypatch)
    replies = iter([SimpleNamespace(text="not json", usage_metadata=None),
                    SimpleNamespace(text=WireRecommendation(title="t", why="w", expected_summary="e", risks=[],
                                                            what_to_watch=[]).model_dump_json(), usage_metadata=None)])
    monkeypatch.setattr(llm, "_call", lambda contents, config: next(replies))
    out, meta = llm.generate_json(system="s", prompt="p", schema=WireRecommendation)
    assert out.title == "t" and meta["attempts"] == 2


def test_gemini_wrapper_gives_up_after_two_bad_replies(monkeypatch):
    llm = _llm(monkeypatch)
    monkeypatch.setattr(llm, "_call", lambda contents, config: SimpleNamespace(text="{}", usage_metadata=None))
    with pytest.raises(LLMError):
        llm.generate_json(system="s", prompt="p", schema=WireRecommendation)


def test_gemini_wrapper_drops_unsupported_thinking_config(monkeypatch):
    llm = _llm(monkeypatch)
    seen = []

    def call(contents, config):
        seen.append(config.thinking_config is not None)
        if config.thinking_config is not None:
            raise RuntimeError("400 INVALID_ARGUMENT: thinking_level is not supported for this model")
        return SimpleNamespace(text=WireRecommendation(title="t", why="w", expected_summary="e", risks=[],
                                                       what_to_watch=[]).model_dump_json(), usage_metadata=None)

    monkeypatch.setattr(llm, "_call", call)
    out, _ = llm.generate_json(system="s", prompt="p", schema=WireRecommendation)
    assert out.title == "t" and seen == [True, False]
    assert os.environ["GEMINI_API_KEY"] == "test-key-not-used"


def test_manager_overrides_win_over_interpretation(world):
    ev = run_with(world, "Increase snack sales by 10%. Budget ₱30k.",
                  overrides={"budget_php": 15_000, "max_congestion_increase_pct": 8, "target_category": "coffee"})
    o = ev[-1]["objective"]
    assert o["budget_php"] == 15_000 and o["max_congestion_increase_pct"] == 8 and o["target_category"] == "coffee"
    assert any("Edited by you" in n for n in o["notes"])
    assert all(c["cost"] <= 15_000 for c in ev[-1]["candidates"] if c["valid"])


def test_offline_names_and_explanations_are_plain(world):
    done = run(world, "Increase snack sales by 10%. Budget ₱30k. Don't increase checkout congestion.")[-1]
    names = [c["name"] for c in done["candidates"]]
    assert any(n.startswith("Snack endcap by") for n in names), names
    why = done["recommendation"]["explanation"]["why"]
    assert len(why) < 300 and "CI" not in why and "Rejected" not in why


def run_with(world, text, overrides):
    return list(LabAgent(world, text, OFFLINE, None, max_rounds=1, overrides=overrides).run())