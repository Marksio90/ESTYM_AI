"""Cost Calculator Agent — generates TechPlan and Quote from PartSpec."""

from __future__ import annotations

import structlog

from ..calc.cost_engine import generate_quote, generate_tech_plan
from ..calc.ml_corrector import CostMLCorrector, extract_feature_vector
from ..calc.time_norms import AllNorms
from .state import RFQState

logger = structlog.get_logger()


async def cost_calculator_node(state: RFQState) -> dict:
    """
    LangGraph node: generate TechPlan and Quote for each PartSpec.

    1. Generate parametric TechPlan (operations + PSI graph)
    2. Generate Quote (cost breakdown)
    3. Apply ML correction if model available
    """
    norms = AllNorms()
    ml_corrector = CostMLCorrector()  # Will use parametric-only if no model loaded

    tech_plans = []
    quotes = []
    batch_size = state.case.requested_qty if state.case and state.case.requested_qty else 1

    for spec in state.part_specs:
        try:
            # Generate technology plan
            plan = generate_tech_plan(spec, norms=norms, batch_size=batch_size)
            tech_plans.append(plan)

            # Generate quote
            quote = generate_quote(spec, plan, norms=norms)

            # ML correction (if model loaded)
            try:
                feature_vec = extract_feature_vector(spec, plan)
                ml_result = ml_corrector.predict(feature_vec, plan.total_time_with_overhead_sec)
                quote.ml_correction = ml_result.ml_correction_sec
                quote.ml_model_version = ml_result.model_version
            except Exception as e:
                logger.warning("ml_correction_skipped", error=str(e))

            quotes.append(quote)

            logger.info(
                "cost_calculated",
                part=spec.part_name,
                operations=len(plan.operations),
                total_cost=quote.total_cost,
                unit_cost=quote.unit_cost,
            )

        except Exception as e:
            logger.error("cost_calculation_failed", part=spec.part_name, error=str(e))
            state.errors.append(f"Błąd kalkulacji dla {spec.part_name}: {e}")

    return {
        "tech_plans": tech_plans,
        "quotes": quotes,
        "current_step": "qa_validation",
        "messages": [{
            "agent": "cost_calculator",
            "content": f"Wygenerowano {len(quotes)} wycen. "
                       f"Suma: {sum(q.total_cost for q in quotes):.2f} PLN",
        }],
    }
