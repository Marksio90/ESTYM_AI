"""Quote management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ...calc.cost_engine import generate_quote, generate_tech_plan
from ...calc.time_norms import AllNorms
from ...models.part_spec import PartSpec

router = APIRouter()


class QuickQuoteRequest(BaseModel):
    """Simplified input for quick cost estimation without full RFQ workflow."""
    part_spec: dict  # PartSpec as dict
    batch_size: int = 1


@router.post("/quick-estimate")
async def quick_estimate(request: QuickQuoteRequest):
    """
    Quick cost estimation from a PartSpec.

    Bypasses the full agent workflow — directly generates TechPlan + Quote.
    Useful for testing and manual estimation.
    """
    spec = PartSpec(**request.part_spec)
    norms = AllNorms()

    plan = generate_tech_plan(spec, norms=norms, batch_size=request.batch_size)
    quote = generate_quote(spec, plan, norms=norms)

    return {
        "quote": quote.model_dump(mode="json"),
        "tech_plan": plan.model_dump(mode="json"),
        "summary": {
            "total_cost": quote.total_cost,
            "unit_cost": quote.unit_cost,
            "currency": quote.currency,
            "operations": len(plan.operations),
            "confidence": quote.confidence.value,
        },
    }


@router.get("/{quote_id}")
async def get_quote(quote_id: str):
    """Get a specific quote by ID."""
    return {"quote_id": quote_id, "status": "not_implemented_yet"}


@router.get("/{quote_id}/breakdown")
async def get_quote_breakdown(quote_id: str):
    """Get detailed cost breakdown for a quote."""
    return {"quote_id": quote_id, "breakdown": "not_implemented_yet"}


@router.post("/{quote_id}/export-erp")
async def export_to_erp(quote_id: str):
    """Export a quote to Graffiti ERP."""
    return {"quote_id": quote_id, "erp_status": "not_implemented_yet"}
