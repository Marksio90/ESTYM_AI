"""Quality Assurance Agent — validates calculations and flags anomalies."""

from __future__ import annotations

import structlog

from ..models.enums import Confidence, RiskLevel, SurfaceFinish
from .state import RFQState

logger = structlog.get_logger()

# Validation thresholds
MAX_UNIT_COST_DEVIATION_PERCENT = 50.0  # flag if >50% off from similar cases
MIN_MATERIAL_COST_RATIO = 0.05  # material should be at least 5% of total
MAX_MATERIAL_COST_RATIO = 0.70  # material should be at most 70% of total


async def qa_validation_node(state: RFQState) -> dict:
    """
    LangGraph node: validate calculations, check for anomalies.

    Checks:
    1. Missing fields in PartSpec
    2. Cost sanity checks
    3. Comparison with similar historical cases
    4. Process consistency (e.g. galvanizing after welding)
    5. Risk assessment
    """
    issues: list[str] = []
    all_passed = True

    for i, (spec, quote) in enumerate(zip(state.part_specs, state.quotes)):
        part_issues = []

        # --- Check 1: Missing critical fields ---
        if not spec.materials:
            part_issues.append(f"[{spec.part_name}] BRAK: materiał nie określony")
            all_passed = False

        if spec.geometry.weight_kg is None or spec.geometry.weight_kg == 0:
            part_issues.append(f"[{spec.part_name}] UWAGA: masa nie określona — szacunki materiałowe mogą być niedokładne")

        for unc in spec.uncertainty:
            if unc.needs_human_review:
                part_issues.append(f"[{spec.part_name}] WERYFIKACJA: {unc.field} — {unc.reason}")
                all_passed = False

        # --- Check 2: Cost sanity ---
        if quote.total_cost <= 0:
            part_issues.append(f"[{spec.part_name}] BŁĄD: koszt całkowity = 0")
            all_passed = False

        if quote.total_cost > 0:
            mat_ratio = quote.material_cost / quote.total_cost
            if mat_ratio < MIN_MATERIAL_COST_RATIO and quote.material_cost > 0:
                part_issues.append(
                    f"[{spec.part_name}] UWAGA: koszt materiału stanowi tylko {mat_ratio*100:.1f}% kosztu całkowitego"
                )
            if mat_ratio > MAX_MATERIAL_COST_RATIO:
                part_issues.append(
                    f"[{spec.part_name}] UWAGA: koszt materiału stanowi aż {mat_ratio*100:.1f}% kosztu całkowitego"
                )

        # --- Check 3: Process consistency ---
        finish = spec.process_requirements.surface_finish
        has_welding = (
            spec.geometry.welds.spot_weld_count > 0
            or spec.geometry.welds.linear_weld_length_mm > 0
        )

        if finish == SurfaceFinish.GALVANIZED and not has_welding:
            # Not an error, but note
            pass

        if has_welding and spec.process_requirements.welding.value == "unknown":
            part_issues.append(f"[{spec.part_name}] UWAGA: wykryto spawy, ale typ spawania nie określony")

        # --- Check 4: Comparison with similar cases ---
        for similar in quote.similar_cases:
            if similar.similarity_score > 0.8:
                deviation = abs(quote.unit_cost - similar.historical_total_cost) / max(similar.historical_total_cost, 1) * 100
                if deviation > MAX_UNIT_COST_DEVIATION_PERCENT:
                    part_issues.append(
                        f"[{spec.part_name}] ODCHYLENIE: {deviation:.0f}% od podobnej sprawy {similar.case_id} "
                        f"(hist: {similar.historical_total_cost:.2f}, teraz: {quote.unit_cost:.2f})"
                    )
                    all_passed = False

        # --- Check 5: Set confidence ---
        if len(part_issues) == 0:
            quote.confidence = Confidence.HIGH
        elif any("BŁĄD" in i or "BRAK" in i for i in part_issues):
            quote.confidence = Confidence.LOW
        else:
            quote.confidence = Confidence.MEDIUM

        issues.extend(part_issues)

    # Determine if human review is needed
    needs_review = not all_passed or (state.case and state.case.risk_level == RiskLevel.HIGH)

    logger.info(
        "qa_validation_complete",
        issues=len(issues),
        passed=all_passed,
        needs_review=needs_review,
    )

    return {
        "qa_issues": issues,
        "qa_passed": all_passed,
        "awaiting_human_review": needs_review,
        "current_step": "human_review" if needs_review else "erp_export",
        "messages": [{
            "agent": "qa",
            "content": f"Walidacja: {'PASSED' if all_passed else 'ISSUES FOUND'} ({len(issues)} uwag). "
                       f"{'Wymaga przeglądu kosztorysanta.' if needs_review else 'Gotowe do eksportu.'}",
        }],
    }
