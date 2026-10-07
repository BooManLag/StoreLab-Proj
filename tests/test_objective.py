import pytest

from storelab.objective import finalize_objective, parse_objective_offline


@pytest.mark.parametrize("text,cat,metric,budget,tol,lang", [
    ("Increase snack sales by 10%. Budget ₱30k. Don't increase checkout congestion.",
     "snacks", "category_revenue", 30_000, 5, "en"),
    ("Increase coffee attachment without creating checkout congestion. Budget ₱50,000. Refrigerators cannot move.",
     "coffee", "category_attachment", 50_000, 5, "en"),
    ("Grow basket value, checkout queue cannot worsen more than 3%, budget of 25,000 pesos",
     None, "basket_value", 25_000, 3, "en"),
    ("スナックの売上を10%伸ばしたい。予算は3万ペソ。レジの混雑は増やさないこと。冷蔵庫は動かせない。",
     "snacks", "category_revenue", 30_000, 5, "ja"),
    ("커피 동반 구매율을 높이고 싶어요. 예산 5만 페소, 계산대 혼잡은 늘리지 마세요.",
     "coffee", "category_attachment", 50_000, 5, "ko"),
    ("Tingkatkan penjualan camilan 10% tanpa menambah antrean kasir. Anggaran ₱30.000.",
     "snacks", "category_revenue", 30_000, 5, "id"),
    ("Dagdagan ang benta ng snacks ng 10%, budget P30,000, huwag dagdagan ang pila sa kahera.",
     "snacks", "category_revenue", 30_000, 5, "fil"),
])
def test_offline_parser(text, cat, metric, budget, tol, lang):
    s = parse_objective_offline(text)
    assert s.target_category == cat
    assert s.metric == metric
    assert s.budget_php == budget
    assert s.max_congestion_increase_pct == tol
    assert s.language == lang


def test_defaults_are_explicit():
    s = parse_objective_offline("Sell more bread")
    assert s.target_category == "bakery"
    assert s.budget_php == 50_000 and not s.budget_stated
    assert s.max_congestion_increase_pct == 10 and not s.congestion_stated
    assert any("budget" in n.lower() for n in s.notes)


def test_refrigeration_phrase_fixes_beverages():
    s = parse_objective_offline("Increase snack sales by at least 10%. Don't move refrigeration. Budget ₱40,000.")
    assert "beverages" in s.fixed_categories and s.target_category == "snacks"


def test_no_false_budget_from_words():
    s = parse_objective_offline("Push snack sales up 10 percent")
    assert s.budget_php == 50_000 and not s.budget_stated
    assert s.target_uplift_pct == 10


def test_finalize_gemini_sentinels():
    s = finalize_objective("x", language="en", normalized="", metric="category_revenue", target_category="none",
                           target_uplift_pct=0, budget_php=0, max_congestion_increase_pct=-1,
                           fixed_categories=["beverage"], notes=[])
    assert s.metric == "total_revenue" and s.target_category is None
    assert s.budget_php == 50_000 and s.max_congestion_increase_pct == 10
    assert s.fixed_categories == ["beverages"] and s.normalized_objective
