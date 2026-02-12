"""Case management API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from ...agents.state import RFQState
from ...agents.workflow import build_rfq_workflow

router = APIRouter()


class CreateCaseRequest(BaseModel):
    email_subject: str = ""
    email_body: str = ""
    customer_name: str = ""
    customer_email: str = ""
    requested_qty: Optional[int] = None
    notes: str = ""


class CaseStatusResponse(BaseModel):
    case_id: str
    status: str
    product_family: str = "unknown"
    risk_level: str = "medium"
    missing_info: list[str] = []
    messages: list[dict] = []


class ApproveRequest(BaseModel):
    approved: bool = True
    modifications: list[dict] = []
    notes: str = ""


@router.post("/", response_model=CaseStatusResponse)
async def create_case(request: CreateCaseRequest):
    """Create a new RFQ case and start the analysis workflow."""
    email_raw = f"Subject: {request.email_subject}\n\n{request.email_body}"

    # Build and run intake step
    graph = build_rfq_workflow()
    initial_state = RFQState(email_raw=email_raw)

    # Run just the intake step (in production, use LangGraph checkpointing)
    try:
        result = await graph.ainvoke(initial_state.model_dump())
        state = RFQState(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow error: {e}")

    case = state.case
    if not case:
        raise HTTPException(status_code=500, detail="Case creation failed")

    return CaseStatusResponse(
        case_id=case.case_id,
        status=case.status.value,
        product_family=case.product_family_guess.value,
        risk_level=case.risk_level.value,
        missing_info=case.missing_info_questions,
        messages=state.messages,
    )


@router.get("/{case_id}")
async def get_case(case_id: str):
    """Get case details and current status."""
    # In production: load from database
    return {"case_id": case_id, "status": "not_implemented_yet"}


@router.post("/{case_id}/approve")
async def approve_case(case_id: str, request: ApproveRequest):
    """
    Approve or modify a case after human review.

    This resumes the LangGraph workflow from the human_review interrupt.
    """
    # In production: resume LangGraph workflow with human approval
    return {
        "case_id": case_id,
        "approved": request.approved,
        "status": "approved" if request.approved else "modifications_requested",
    }


@router.get("/{case_id}/tech-plan")
async def get_tech_plan(case_id: str):
    """Get the generated technology plan (PSI graph) for a case."""
    return {"case_id": case_id, "tech_plan": "not_implemented_yet"}


@router.get("/{case_id}/similar")
async def find_similar_cases(case_id: str, limit: int = 5):
    """Find historically similar cases for reference."""
    return {"case_id": case_id, "similar_cases": [], "limit": limit}
