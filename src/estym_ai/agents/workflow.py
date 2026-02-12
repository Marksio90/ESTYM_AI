"""Main LangGraph workflow — orchestrates all agents in the RFQ pipeline.

Architecture: Supervisor-Sequential Hybrid with human-in-the-loop interrupt.

Flow:
  intake → drawing_analysis → cost_calculation → qa_validation
    → [if needs review] INTERRUPT (human review) → erp_export
    → [if no review needed] erp_export
"""

from __future__ import annotations

from typing import Literal

import structlog

from .cost_agent import cost_calculator_node
from .drawing_agent import drawing_analyzer_node
from .erp_agent import erp_export_node
from .intake_agent import intake_node
from .qa_agent import qa_validation_node
from .state import RFQState

logger = structlog.get_logger()


def should_interrupt_for_review(state: RFQState) -> Literal["human_review", "erp_export"]:
    """Conditional edge: route to human review or directly to ERP export."""
    if state.awaiting_human_review:
        return "human_review"
    return "erp_export"


async def human_review_node(state: RFQState) -> dict:
    """
    Human-in-the-loop review node.

    In production, this node triggers an interrupt (LangGraph's interrupt mechanism)
    and waits for the estimator to approve/modify/reject the calculation.

    The UI sends back:
    - human_approved: bool
    - human_modifications: list of changes
    """
    # This node is where LangGraph's interrupt/resume happens.
    # When resumed, the state will contain human_approved and human_modifications.

    if state.human_approved:
        logger.info("human_review_approved", case=state.case.case_id if state.case else "?")
        return {
            "current_step": "erp_export",
            "messages": [{"agent": "human_review", "content": "Kosztorysant zatwierdził wycenę"}],
        }
    else:
        logger.info("human_review_pending", case=state.case.case_id if state.case else "?")
        return {
            "current_step": "human_review",
            "messages": [{"agent": "human_review", "content": "Oczekuje na przegląd kosztorysanta..."}],
        }


def build_rfq_workflow():
    """
    Build the complete LangGraph StateGraph for RFQ processing.

    Returns a compiled graph ready for invocation.
    """
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        logger.error("langgraph not installed — cannot build workflow")
        raise ImportError("langgraph is required: pip install langgraph")

    # Create the state graph
    workflow = StateGraph(RFQState)

    # Add nodes
    workflow.add_node("intake", intake_node)
    workflow.add_node("drawing_analysis", drawing_analyzer_node)
    workflow.add_node("cost_calculation", cost_calculator_node)
    workflow.add_node("qa_validation", qa_validation_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("erp_export", erp_export_node)

    # Define edges (sequential pipeline with conditional branch)
    workflow.set_entry_point("intake")
    workflow.add_edge("intake", "drawing_analysis")
    workflow.add_edge("drawing_analysis", "cost_calculation")
    workflow.add_edge("cost_calculation", "qa_validation")

    # Conditional: QA → human_review OR erp_export
    workflow.add_conditional_edges(
        "qa_validation",
        should_interrupt_for_review,
        {
            "human_review": "human_review",
            "erp_export": "erp_export",
        },
    )

    # Human review → ERP export (after approval)
    workflow.add_edge("human_review", "erp_export")

    # ERP export → END
    workflow.add_edge("erp_export", END)

    # Compile
    compiled = workflow.compile()

    logger.info("rfq_workflow_built", nodes=6, edges=7)
    return compiled


async def run_rfq_workflow(
    email_raw: str = "",
    files: list[dict] | None = None,
    config: dict | None = None,
) -> RFQState:
    """
    Convenience function to run the full RFQ workflow.

    Args:
        email_raw: Raw email content.
        files: List of file metadata dicts [{filename, path, storage_key, size}].
        config: LangGraph config (thread_id, checkpointer, etc.).

    Returns:
        Final RFQState after workflow completion.
    """
    graph = build_rfq_workflow()

    initial_state = RFQState(
        email_raw=email_raw,
        file_processing_results=files or [],
    )

    result = await graph.ainvoke(
        initial_state.model_dump(),
        config=config or {},
    )

    return RFQState(**result)
