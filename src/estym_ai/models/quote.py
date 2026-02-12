"""Quote — the cost estimation output."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .enums import Confidence


class CostBreakdownItem(BaseModel):
    """A single line in the cost breakdown."""
    category: str  # e.g. "material", "labor", "machine", "fixture", "coating", "overhead"
    description: str
    quantity: float = 1.0
    unit: str = "szt"  # szt, m, m2, kg, h
    unit_cost: float = 0.0
    total_cost: float = 0.0
    notes: str = ""


class SimilarCaseReference(BaseModel):
    """Reference to a historically similar case used for comparison."""
    case_id: str
    similarity_score: float
    historical_total_cost: float
    historical_qty: int = 1
    key_differences: list[str] = Field(default_factory=list)


class Quote(BaseModel):
    """
    Complete cost estimation for one part/product.

    Combines material, process (labor + machine), fixture, coating,
    and overhead costs into a final quote.
    """
    quote_id: str = ""
    case_id: str = ""
    part_id: str = ""
    plan_id: str = ""

    # Summary costs
    material_cost: float = 0.0
    labor_cost: float = 0.0
    machine_cost: float = 0.0
    fixture_cost: float = 0.0
    coating_cost: float = 0.0
    overhead_cost: float = 0.0
    total_cost: float = 0.0
    unit_cost: float = 0.0  # total / quantity

    quantity: int = 1
    currency: str = "PLN"

    # Detailed breakdown
    breakdown: list[CostBreakdownItem] = Field(default_factory=list)

    # Comparison to historical cases
    similar_cases: list[SimilarCaseReference] = Field(default_factory=list)
    deviation_from_similar_percent: Optional[float] = None

    # Metadata
    assumptions: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    risk_notes: list[str] = Field(default_factory=list)

    # ML correction
    parametric_estimate: Optional[float] = None  # before ML correction
    ml_correction: Optional[float] = None  # delta from ML model
    ml_model_version: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    def compute_total(self) -> None:
        """Recompute total from components."""
        self.total_cost = (
            self.material_cost
            + self.labor_cost
            + self.machine_cost
            + self.fixture_cost
            + self.coating_cost
            + self.overhead_cost
        )
        self.unit_cost = self.total_cost / max(self.quantity, 1)
