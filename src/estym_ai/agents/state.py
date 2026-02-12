"""LangGraph shared state definition for the RFQ processing workflow."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from ..models.inquiry import InquiryCase
from ..models.part_spec import PartSpec
from ..models.quote import Quote
from ..models.tech_plan import TechPlan


def merge_lists(left: list, right: list) -> list:
    """Reducer: merge two lists (append right to left)."""
    return left + right


class RFQState(BaseModel):
    """
    Shared state for the RFQ processing LangGraph workflow.

    Each agent reads from and writes to this state.
    LangGraph checkpoints this state at every super-step.
    """
    # --- Intake ---
    case: Optional[InquiryCase] = None
    email_raw: str = ""

    # --- File processing ---
    file_processing_results: list[dict] = Field(default_factory=list)

    # --- Drawing analysis ---
    part_specs: list[PartSpec] = Field(default_factory=list)

    # --- Similarity search ---
    similar_cases: list[dict] = Field(default_factory=list)

    # --- Technology planning ---
    tech_plans: list[TechPlan] = Field(default_factory=list)

    # --- Cost estimation ---
    quotes: list[Quote] = Field(default_factory=list)

    # --- QA validation ---
    qa_issues: Annotated[list[str], merge_lists] = Field(default_factory=list)
    qa_passed: bool = False

    # --- Human review ---
    human_approved: bool = False
    human_modifications: list[dict] = Field(default_factory=list)
    awaiting_human_review: bool = False

    # --- ERP export ---
    erp_export_status: str = "pending"  # pending | exported | failed
    erp_export_results: list[dict] = Field(default_factory=list)

    # --- Workflow control ---
    current_step: str = "intake"
    errors: Annotated[list[str], merge_lists] = Field(default_factory=list)
    messages: Annotated[list[dict], merge_lists] = Field(default_factory=list)
