"""Validated HTTP request contracts, exposed through OpenAPI."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..layout import Change
from ..objective import MAX_OBJECTIVE_CHARS, ObjectiveSpec


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ObjectiveOverrides(RequestModel):
    """Values the manager edits directly on the objective chips."""

    budget_php: Optional[float] = Field(default=None, gt=0, le=10_000_000)
    max_congestion_increase_pct: Optional[float] = Field(default=None, ge=0, le=100)
    target_uplift_pct: Optional[float] = Field(default=None, ge=0, le=500)
    target_category: Optional[Literal["bakery", "coffee", "snacks", "beverages"]] = None


class LabRequest(RequestModel):
    objective: str = Field(min_length=3, max_length=MAX_OBJECTIVE_CHARS)
    mode: Literal["fast", "thorough"] = "fast"
    rounds: Optional[int] = Field(
        default=None, ge=1, le=2
    )  # legacy; overrides mode when given
    overrides: Optional[ObjectiveOverrides] = None


class SimulateRequest(RequestModel):
    changes: list[Change] = Field(min_length=1, max_length=5)
    budget_php: float = Field(default=50_000, gt=0, le=10_000_000)
    metric: str = "category_revenue"
    category: Optional[str] = "snacks"
    max_congestion_increase_pct: float = Field(default=10.0, ge=0, le=100)


class LayoutRequest(RequestModel):
    category_slot: dict[str, str]
    displays: dict[str, str] = Field(default_factory=dict)


class PilotPlanRequest(RequestModel):
    objective: ObjectiveSpec
    candidate: dict


class PilotRequest(RequestModel):
    plan: dict
    objective: Optional[str] = None
