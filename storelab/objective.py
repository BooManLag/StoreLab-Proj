"""Business objectives: the structured form of "increase snack sales 10% without worsening the queue".

Gemini normalises free text in any language into ObjectiveSpec. When Gemini is not
configured, a keyword parser (English, Filipino, Bahasa Indonesia, Japanese, Korean)
does the same, more literally.
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel

from .store import CATEGORIES, CATEGORY_LABELS, REFRIGERATED_CATEGORIES
from .validator import Constraints

MetricId = Literal["category_revenue", "category_units", "category_attachment", "total_revenue", "basket_value"]
CATEGORY_METRICS = {"category_revenue", "category_units", "category_attachment"}
METRIC_LABELS = {
    "category_revenue": "sales",
    "category_units": "units sold",
    "category_attachment": "attachment rate",
    "total_revenue": "store revenue",
    "basket_value": "average basket value",
}

DEFAULT_BUDGET_PHP = 50_000.0
DEFAULT_CONGESTION_TOLERANCE_PCT = 10.0  # guardrail when the objective does not mention queues
STATED_CONGESTION_TOLERANCE_PCT = 5.0  # "don't worsen congestion" without a number
MAX_OBJECTIVE_CHARS = 600


class ObjectiveSpec(BaseModel):
    raw_text: str
    language: str
    normalized_objective: str
    metric: MetricId
    target_category: Optional[str] = None
    target_uplift_pct: Optional[float] = None
    budget_php: float
    budget_stated: bool
    max_congestion_increase_pct: float
    congestion_stated: bool
    fixed_categories: list[str]
    notes: list[str]
    source: str  # "gemini" | "offline"

    def constraints(self) -> Constraints:
        return Constraints(
            budget_php=self.budget_php,
            fixed_categories=set(self.fixed_categories),
            max_congestion_increase_pct=self.max_congestion_increase_pct,
        )

    @property
    def metric_label(self) -> str:
        base = METRIC_LABELS[self.metric]
        if self.target_category:
            return f"{CATEGORY_LABELS[self.target_category]} {base}"
        return base[0].upper() + base[1:]


# ---------------------------------------------------------------- offline parser
_CAT_WORDS: dict[str, list[str]] = {
    "snacks": ["snack", "chips", "crisps", "chichirya", "sitsirya", "meryenda", "merienda", "camilan", "cemilan",
               "makanan ringan", "kudapan", "keripik", "スナック", "お菓子", "菓子", "과자", "스낵"],
    "coffee": ["coffee", "kape", "kopi", "コーヒー", "커피"],
    "bakery": ["bakery", "bread", "pastry", "pastries", "pandesal", "tinapay", "roti", "パン", "ベーカリー", "빵", "베이커리"],
    "beverages": ["beverage", "drink", "soda", "water", "inumin", "minuman", "飲料", "飲み物", "ドリンク", "음료"],
}
_CONGESTION_WORDS = ["congestion", "queue", "line at", "lines at", "checkout line", "waiting time", "crowd",
                     "pila", "antrean", "antrian", "macet", "混雑", "レジ待ち", "行列", "혼잡", "대기"]
_FIX_WORDS = ["don't move", "do not move", "dont move", "cannot move", "can't move", "keep", "fixed", "huwag ilipat",
              "jangan pindah", "動かさない", "移動しない", "옮기지"]
_REFRIGERATION_WORDS = ["refrigerat", "fridge", "cooler", "chiller", "冷蔵", "냉장", "kulkas", "pridyider", "ref "]


def detect_language(text: str) -> str:
    if re.search(r"[぀-ヿ]", text):
        return "ja"
    if re.search(r"[가-힯]", text):
        return "ko"
    if re.search(r"[一-鿿]", text):
        return "zh"
    low = f" {text.lower()} "
    if any(w in low for w in [" tingkatkan ", " penjualan ", " tanpa ", " anggaran ", " jangan "]):
        return "id"
    if any(w in low for w in [" dagdagan ", " benta ", " huwag ", " pataasin ", " ng "]):
        return "fil"
    return "en"


def _find_categories(text: str) -> list[tuple[int, str]]:
    low = text.lower()
    hits = []
    for cat, words in _CAT_WORDS.items():
        for w in words:
            i = low.find(w)
            if i >= 0:
                hits.append((i, cat))
                break
    return sorted(hits)


def _parse_amount(num: str, suffix: str) -> float:
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", num):  # 30.000 (dot as thousands separator)
        num = num.replace(".", "")
    value = float(num.replace(",", ""))
    s = (suffix or "").lower()
    if s == "k":
        value *= 1_000
    elif s in ("m", "mn"):
        value *= 1_000_000
    elif s in ("万", "만"):
        value *= 10_000
    return value


_NUM = r"(\d[\d,.]*\d|\d)"
_SUFFIX = r"(?:\s?(k|mn|m|万|만)(?![a-z]))?"


def _find_budget(text: str) -> float | None:
    patterns = [
        rf"(?:₱|\bphp\s?|\bp(?=\d)){_NUM}{_SUFFIX}",
        rf"{_NUM}{_SUFFIX}\s?(?:pesos?\b|php\b|ペソ|페소)",
        rf"(?:budget|badyet|anggaran|予算|예산)[^\d]{{0,15}}{_NUM}{_SUFFIX}",
        rf"{_NUM}{_SUFFIX}\s?(?:budget|badyet|anggaran)",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            try:
                return _parse_amount(m.group(1), m.group(2) or "")
            except ValueError:
                continue
    return None


def parse_objective_offline(text: str) -> ObjectiveSpec:
    raw = text.strip()[:MAX_OBJECTIVE_CHARS]
    low = raw.lower()
    notes: list[str] = []
    lang = detect_language(raw)

    cats = _find_categories(raw)
    fixed: set[str] = set()
    for w in _FIX_WORDS:
        i = low.find(w)
        if i < 0:
            continue
        window = low[i: i + 40]
        for cat, words in _CAT_WORDS.items():
            if any(x in window for x in words):
                fixed.add(cat)
    if any(w in low for w in _REFRIGERATION_WORDS):
        fixed |= REFRIGERATED_CATEGORIES
    target_cats = [c for _, c in cats if c not in fixed] or [c for _, c in cats]
    target = target_cats[0] if target_cats else None

    congestion_pos = [low.find(w) for w in _CONGESTION_WORDS if low.find(w) >= 0]
    congestion_stated = bool(congestion_pos)
    percents = [(m.start(), float(m.group(1))) for m in
                re.finditer(r"(\d+(?:\.\d+)?)\s?(?:%|percent\b|pct\b|persen\b|porsiyento\b|퍼센트|パーセント)", raw,
                            flags=re.IGNORECASE)]
    comparators = ["more than", "over", "above", "exceed", "max", "at most", "by more", "beyond", "lebih dari",
                   "higit", "以上", "이상", "超"]
    congestion_pct = None
    uplift = None
    for pos, val in percents:
        near_congestion = any(0 <= pos - cp <= 60 or 0 <= cp - pos <= 25 for cp in congestion_pos)
        before = low[max(0, pos - 30): pos]
        after = low[pos: pos + 15]
        has_comparator = any(w in before for w in comparators) or any(w in after for w in ("以上", "이상"))
        if near_congestion and has_comparator and congestion_pct is None:
            congestion_pct = val
        elif uplift is None:
            uplift = val

    if any(w in low for w in ["attach", "add-on", "cross-sell", "cross sell", "동반 구매", "동반구매", "併売", "ついで買い",
                              "同時購入", "pembelian bersama", "kasabay na bili"]):
        metric = "category_attachment"
    elif any(w in low for w in ["basket value", "basket size", "average transaction", "atv", "ticket size"]):
        metric = "basket_value"
    elif any(w in low for w in ["unit", "volume", "pieces"]):
        metric = "category_units"
    else:
        metric = "category_revenue"
    if metric in CATEGORY_METRICS and target is None:
        metric = "total_revenue"
        notes.append("No product category recognised, so the goal is store revenue.")

    budget = _find_budget(raw)
    budget_stated = budget is not None
    if budget is None:
        budget = DEFAULT_BUDGET_PHP
        notes.append(f"No budget stated; assumed ₱{DEFAULT_BUDGET_PHP:,.0f}.")
    if congestion_stated:
        tol = congestion_pct if congestion_pct is not None else STATED_CONGESTION_TOLERANCE_PCT
        if congestion_pct is None:
            notes.append(f"'Don't worsen congestion' is read as at most +{STATED_CONGESTION_TOLERANCE_PCT:.0f}% "
                         "peak checkout congestion (operational tolerance).")
    else:
        tol = DEFAULT_CONGESTION_TOLERANCE_PCT
        notes.append(f"Default guardrail: peak checkout congestion may rise at most +{tol:.0f}%.")
    if REFRIGERATED_CATEGORIES & fixed:
        notes.append("Refrigerated coolers stay where they are.")

    spec = ObjectiveSpec(
        raw_text=raw,
        language=lang,
        normalized_objective="",
        metric=metric,
        target_category=target if metric in CATEGORY_METRICS else None,
        target_uplift_pct=uplift,
        budget_php=budget,
        budget_stated=budget_stated,
        max_congestion_increase_pct=tol,
        congestion_stated=congestion_stated,
        fixed_categories=sorted(fixed),
        notes=notes,
        source="offline",
    )
    spec.normalized_objective = describe_objective(spec)
    return spec


def describe_objective(spec: ObjectiveSpec) -> str:
    parts = [f"Increase {spec.metric_label}"]
    if spec.target_uplift_pct:
        parts[0] += f" by {spec.target_uplift_pct:g}%"
    parts.append(f"keep peak checkout congestion within +{spec.max_congestion_increase_pct:g}%")
    parts.append(f"budget ₱{spec.budget_php:,.0f}")
    if spec.fixed_categories:
        parts.append("do not move " + ", ".join(CATEGORY_LABELS[c] for c in spec.fixed_categories))
    return "; ".join(parts) + "."


def finalize_objective(raw_text: str, *, language: str, normalized: str, metric: str, target_category: str,
                       target_uplift_pct: float, budget_php: float, max_congestion_increase_pct: float,
                       fixed_categories: list[str], notes: list[str]) -> ObjectiveSpec:
    """Turn Gemini's sentinel-valued output into a clean ObjectiveSpec with the same defaults as offline."""
    from .validator import resolve_category

    notes = list(notes)
    cat = resolve_category(target_category) if target_category and target_category != "none" else None
    if metric not in METRIC_LABELS:
        metric = "category_revenue" if cat else "total_revenue"
    if metric in CATEGORY_METRICS and cat is None:
        metric = "total_revenue"
        notes.append("No product category recognised, so the goal is store revenue.")
    budget_stated = budget_php is not None and budget_php > 0
    if not budget_stated:
        budget_php = DEFAULT_BUDGET_PHP
        notes.append(f"No budget stated; assumed ₱{DEFAULT_BUDGET_PHP:,.0f}.")
    congestion_stated = max_congestion_increase_pct is not None and max_congestion_increase_pct >= 0
    if not congestion_stated:
        max_congestion_increase_pct = DEFAULT_CONGESTION_TOLERANCE_PCT
        notes.append(f"Default guardrail: peak checkout congestion may rise at most +{DEFAULT_CONGESTION_TOLERANCE_PCT:.0f}%.")
    fixed = {c for c in (resolve_category(x) for x in fixed_categories) if c}
    spec = ObjectiveSpec(
        raw_text=raw_text[:MAX_OBJECTIVE_CHARS],
        language=language or detect_language(raw_text),
        normalized_objective=normalized,
        metric=metric,  # type: ignore[arg-type]
        target_category=cat if metric in CATEGORY_METRICS else None,
        target_uplift_pct=target_uplift_pct if target_uplift_pct and target_uplift_pct > 0 else None,
        budget_php=float(budget_php),
        budget_stated=budget_stated,
        max_congestion_increase_pct=float(max_congestion_increase_pct),
        congestion_stated=congestion_stated,
        fixed_categories=sorted(fixed),
        notes=notes,
        source="gemini",
    )
    if not spec.normalized_objective.strip():
        spec.normalized_objective = describe_objective(spec)
    return spec


assert set(_CAT_WORDS) == set(CATEGORIES)
