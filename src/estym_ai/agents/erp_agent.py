"""ERP Integration Agent — exports TechPlan and Quote to Graffiti ERP."""

from __future__ import annotations

import json
from typing import Optional

import structlog

from ..config.settings import ERPMode, get_settings
from ..models.tech_plan import TechPlan
from ..models.quote import Quote
from .state import RFQState

logger = structlog.get_logger()


async def erp_export_node(state: RFQState) -> dict:
    """
    LangGraph node: export technology and cost data to Graffiti ERP.

    Supports three modes:
    1. API — REST calls to Graffiti ERP API
    2. Database — direct SQL insert via stored procedures
    3. File export — generate JSON/CSV files for manual import
    """
    settings = get_settings()

    if not state.human_approved and state.awaiting_human_review:
        return {
            "erp_export_status": "pending",
            "messages": [{"agent": "erp", "content": "Eksport wstrzymany — oczekuje na zatwierdzenie kosztorysanta"}],
        }

    results = []

    for plan, quote in zip(state.tech_plans, state.quotes):
        try:
            if settings.graffiti_erp_mode == ERPMode.API:
                result = await _export_via_api(plan, quote, settings)
            elif settings.graffiti_erp_mode == ERPMode.DATABASE:
                result = await _export_via_db(plan, quote, settings)
            elif settings.graffiti_erp_mode == ERPMode.FILE_EXPORT:
                result = _export_to_file(plan, quote, state.case.case_id if state.case else "unknown")
            else:
                result = {"status": "skipped", "reason": "ERP integration disabled"}

            results.append(result)

        except Exception as e:
            logger.error("erp_export_failed", plan_id=plan.plan_id, error=str(e))
            results.append({"status": "failed", "error": str(e)})

    all_ok = all(r.get("status") in ("ok", "skipped") for r in results)

    return {
        "erp_export_status": "exported" if all_ok else "failed",
        "erp_export_results": results,
        "current_step": "complete",
        "messages": [{
            "agent": "erp",
            "content": f"Eksport ERP: {'sukces' if all_ok else 'błąd'} ({len(results)} planów)",
        }],
    }


async def _export_via_api(plan: TechPlan, quote: Quote, settings) -> dict:
    """Export to Graffiti ERP via REST API."""
    import httpx

    payload = _build_erp_payload(plan, quote)

    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {settings.graffiti_erp_api_key}"}

        # Create production order
        response = await client.post(
            f"{settings.graffiti_erp_api_url}/production-orders",
            json=payload["production_order"],
            headers=headers,
        )
        response.raise_for_status()
        order_id = response.json().get("id")

        # Create technology (PSI)
        for op_payload in payload["operations"]:
            op_payload["production_order_id"] = order_id
            resp = await client.post(
                f"{settings.graffiti_erp_api_url}/technologies",
                json=op_payload,
                headers=headers,
            )
            resp.raise_for_status()

        # Create material requirements
        for mat_payload in payload["material_requirements"]:
            mat_payload["production_order_id"] = order_id
            resp = await client.post(
                f"{settings.graffiti_erp_api_url}/material-requirements",
                json=mat_payload,
                headers=headers,
            )
            resp.raise_for_status()

    logger.info("erp_api_export_ok", order_id=order_id)
    return {"status": "ok", "order_id": order_id}


async def _export_via_db(plan: TechPlan, quote: Quote, settings) -> dict:
    """Export to Graffiti ERP via direct database insert."""
    from sqlalchemy import create_engine, text

    engine = create_engine(settings.graffiti_erp_db_url)
    payload = _build_erp_payload(plan, quote)

    with engine.begin() as conn:
        # Call stored procedure for production order
        result = conn.execute(
            text("EXEC sp_CreateProductionOrder :data"),
            {"data": json.dumps(payload["production_order"])},
        )
        order_id = result.scalar()

        # Insert operations
        for op in payload["operations"]:
            conn.execute(
                text("EXEC sp_AddOperation :order_id, :data"),
                {"order_id": order_id, "data": json.dumps(op)},
            )

    logger.info("erp_db_export_ok", order_id=order_id)
    return {"status": "ok", "order_id": order_id}


def _export_to_file(plan: TechPlan, quote: Quote, case_id: str) -> dict:
    """Export to JSON file for manual import into ERP."""
    from pathlib import Path

    payload = _build_erp_payload(plan, quote)
    output_dir = Path("data/erp_exports")
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / f"{case_id}_{plan.plan_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    logger.info("erp_file_export_ok", path=str(file_path))
    return {"status": "ok", "file_path": str(file_path)}


def _build_erp_payload(plan: TechPlan, quote: Quote) -> dict:
    """Build the ERP-compatible payload from TechPlan and Quote."""

    # Build operation sequence with PSI predecessors/successors
    op_order = plan.topological_order()
    op_map = {op.op_code: op for op in plan.operations}

    # Build predecessor map
    predecessors: dict[str, list[str]] = {op.op_code: [] for op in plan.operations}
    successors: dict[str, list[str]] = {op.op_code: [] for op in plan.operations}
    for edge in plan.precedence_edges:
        predecessors[edge.to_op_code].append(edge.from_op_code)
        successors[edge.from_op_code].append(edge.to_op_code)

    operations = []
    for seq_num, op_code in enumerate(op_order, start=1):
        op = op_map[op_code]
        operations.append({
            "sequence_number": seq_num * 10,
            "operation_code": op.op_code,
            "operation_name": op.op_name,
            "workcenter_code": op.workcenter,
            "cycle_time_sec": op.cycle_time_sec,
            "setup_time_sec": op.setup_time_sec,
            "multiplier": op.multiplier,
            "predecessors": predecessors.get(op_code, []),
            "successors": successors.get(op_code, []),
            "requires_fixture": op.requires_fixture,
            "fixture_type": op.fixture_type,
            "notes": op.notes,
        })

    return {
        "production_order": {
            "plan_id": plan.plan_id,
            "part_id": plan.part_id,
            "batch_size": plan.batch_size,
            "total_cost": quote.total_cost,
            "unit_cost": quote.unit_cost,
            "currency": quote.currency,
        },
        "operations": operations,
        "material_requirements": [
            {
                "category": item.category,
                "description": item.description,
                "quantity": item.quantity,
                "unit": item.unit,
                "unit_cost": item.unit_cost,
                "total_cost": item.total_cost,
            }
            for item in quote.breakdown
            if item.category == "material"
        ],
        "cost_breakdown": [item.model_dump() for item in quote.breakdown],
    }
