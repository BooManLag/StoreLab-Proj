"""Runtime configuration, read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
DATA_DIR = Path(os.environ.get("STORELAB_DATA_DIR", str(ROOT / "data")))

# One seed drives the synthetic world, so every build produces the same demo data.
SEED = int(os.environ.get("STORELAB_SEED", "20261018"))

# Bump when the synthetic world, the fitted models or the cache format change.
CACHE_VERSION = "storelab-cache-v5"

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AgentSettings:
    mode: str  # "gemini-api" | "vertex-ai" | "offline"
    model: str
    reason: str
    timeout_s: float
    thinking_level: str | None

    @property
    def uses_gemini(self) -> bool:
        return self.mode != "offline"

    def public(self) -> dict:
        return {
            "mode": self.mode,
            "model": self.model if self.uses_gemini else None,
            "reason": self.reason,
        }


def agent_settings() -> AgentSettings:
    """Decide how the StoreLab Agent reaches Gemini.

    Vertex AI (recommended on Cloud Run): GOOGLE_GENAI_USE_VERTEXAI=true plus
    GOOGLE_CLOUD_PROJECT (and optionally GOOGLE_CLOUD_LOCATION, default "global").
    Gemini Developer API: GEMINI_API_KEY (or GOOGLE_API_KEY).
    Neither: the offline heuristic planner runs instead, and the UI says so.
    """
    model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    timeout_s = float(os.environ.get("GEMINI_TIMEOUT_S", "90"))
    # Gemini 3 thinking depth: minimal | low | medium | high. "low" keeps an AI Lab run interactive;
    # set GEMINI_THINKING_LEVEL=default to use the model's own default.
    thinking_level = (os.environ.get("GEMINI_THINKING_LEVEL") or "low").strip().lower()
    if thinking_level in ("", "default", "none"):
        thinking_level = None

    if (os.environ.get("STORELAB_AGENT_MODE") or "").strip().lower() == "offline":
        return AgentSettings("offline", model, "STORELAB_AGENT_MODE=offline", timeout_s, thinking_level)

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    use_vertex = _truthy(os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")) or _truthy(
        os.environ.get("GOOGLE_GENAI_USE_ENTERPRISE")
    )
    if use_vertex and (os.environ.get("GOOGLE_CLOUD_PROJECT") or api_key):
        return AgentSettings("vertex-ai", model, "Vertex AI credentials configured", timeout_s, thinking_level)
    if api_key:
        return AgentSettings("gemini-api", model, "Gemini API key configured", timeout_s, thinking_level)
    return AgentSettings(
        "offline",
        model,
        "No Gemini credentials found (set GOOGLE_GENAI_USE_VERTEXAI + GOOGLE_CLOUD_PROJECT, or GEMINI_API_KEY)",
        timeout_s,
        thinking_level,
    )


def lab_rate_limit_per_minute() -> int:
    return int(os.environ.get("STORELAB_LAB_RUNS_PER_MINUTE", "6"))
