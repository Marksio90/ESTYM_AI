"""Cost calculation engine — maps PartSpec → TechPlan → Quote.

Combines parametric formulas with optional ML correction.
"""

from __future__ import annotations

import uuid
from typing import Optional

import structlog

from ..models.enums import (
    MaterialForm,
    OperationType,
    PrecedenceRelation,
    SurfaceFinish,
    WeldingType,
)
from ..models.part_spec import PartSpec
from ..models.quote import CostBreakdownItem, Quote
from ..models.tech_plan import Operation, PrecedenceEdge, TechPlan
from .time_norms import (
    AllNorms,
    apply_social_overhead,
    calc_cutting_time,
    calc_drilling_time,
    calc_galvanizing_cost,
    calc_linear_welding_time,
    calc_powder_coating_cost,
    calc_series_multiplier,
    calc_sheet_bending_time,
    calc_spot_welding_time,
    calc_wire_bending_time,
)

logger = structlog.get_logger()


# ============================================================================
# Rate tables (should be loaded from DB in production)
# ============================================================================

# Labor rates in PLN/hour per workcenter type
DEFAULT_LABOR_RATES = {
    "wire_bending_cnc": 80.0,
    "press_brake": 90.0,
    "spot_welder": 75.0,
    "mig_welding": 100.0,
    "tig_welding": 120.0,
    "robotic_welding": 60.0,
    "drilling": 70.0,
    "grinding": 70.0,
    "cutting_saw": 65.0,
    "cutting_laser": 150.0,
    "assembly": 70.0,
    "qa_inspection": 80.0,
    "packaging": 50.0,
    "degreasing": 55.0,
}

# Machine rates in PLN/hour (added to labor)
DEFAULT_MACHINE_RATES = {
    "wire_bending_cnc": 40.0,
    "press_brake": 50.0,
    "spot_welder": 20.0,
    "mig_welding": 15.0,
    "tig_welding": 15.0,
    "robotic_welding": 80.0,
    "drilling": 25.0,
    "cutting_laser": 200.0,
    "cutting_saw": 15.0,
}

# Material prices in PLN/kg
DEFAULT_MATERIAL_PRICES = {
    "S235": 4.50,
    "S355": 5.20,
    "DC01": 5.00,
    "DC04": 5.80,
    "304": 22.0,  # stainless
    "316": 28.0,  # stainless
    "default": 4.80,
}


def generate_tech_plan(
    spec: PartSpec,
    norms: AllNorms | None = None,
    batch_size: int | None = None,
) -> TechPlan:
    """
    Generate a manufacturing technology plan (TechPlan) from a PartSpec.

    Determines the sequence of operations, computes time norms,
    builds the PSI precedence graph.
    """
    norms = norms or AllNorms()
    batch = batch_size or spec.quantity or 1
    series_mult = calc_series_multiplier(batch)

    plan = TechPlan(
        plan_id=f"TP-{uuid.uuid4().hex[:8]}",
        part_id=spec.part_id,
        batch_size=batch,
        social_overhead_percent=norms.social_overhead_percent,
    )

    ops: list[Operation] = []
    edges: list[PrecedenceEdge] = []
    op_counter = 10

    def next_op_code() -> str:
        nonlocal op_counter
        code = f"OP{op_counter:03d}"
        op_counter += 10
        return code

    # --- 1. CUTTING ---
    needs_cutting = True  # almost always needed
    if needs_cutting:
        material_form = spec.materials[0].form if spec.materials else MaterialForm.OTHER
        if material_form in (MaterialForm.SHEET,):
            cut_method = "laser"
            wc = "cutting_laser"
            perimeter = spec.geometry.sheet.perimeter_mm if spec.geometry.sheet else 0
            cut_result = calc_cutting_time(cut_length_mm=perimeter, method="laser", norms=norms.cutting)
        elif material_form in (MaterialForm.WIRE,):
            cut_method = "shear"
            wc = "cutting_saw"
            cut_result = calc_cutting_time(cut_count=1, method="shear", norms=norms.cutting)
        else:
            cut_method = "saw"
            wc = "cutting_saw"
            cut_result = calc_cutting_time(cut_count=1, method="saw", norms=norms.cutting)

        cut_op = Operation(
            op_code=next_op_code(),
            op_name=f"Cięcie ({cut_method})",
            op_type=OperationType.CUTTING,
            workcenter=wc,
            cycle_time_sec=cut_result["piece_time_sec"],
            setup_time_sec=cut_result["setup_time_sec"],
            multiplier=1.0,
        )
        ops.append(cut_op)

    # --- 2. BENDING ---
    last_pre_weld_op = ops[-1].op_code if ops else None

    # Wire bending
    if spec.geometry.wire and spec.geometry.wire.bend_count > 0:
        wb = calc_wire_bending_time(
            wire_length_mm=spec.geometry.wire.total_length_mm or 0,
            bend_count=spec.geometry.wire.bend_count,
            batch_size=batch,
            norms=norms.wire_bending,
        )
        bend_op = Operation(
            op_code=next_op_code(),
            op_name=f"Gięcie drutu CNC ({spec.geometry.wire.bend_count} gięć)",
            op_type=OperationType.WIRE_BENDING,
            workcenter="wire_bending_cnc",
            cycle_time_sec=wb["piece_time_sec"],
            setup_time_sec=wb["setup_time_sec"],
            multiplier=1.0,
        )
        ops.append(bend_op)
        if last_pre_weld_op:
            edges.append(PrecedenceEdge(
                from_op_code=last_pre_weld_op,
                to_op_code=bend_op.op_code,
            ))
        last_pre_weld_op = bend_op.op_code

    # Sheet bending
    if spec.geometry.sheet and spec.geometry.sheet.bend_count > 0:
        sb = calc_sheet_bending_time(
            bend_count=spec.geometry.sheet.bend_count,
            batch_size=batch,
            norms=norms.sheet_bending,
        )
        bend_op = Operation(
            op_code=next_op_code(),
            op_name=f"Gięcie blachy ({spec.geometry.sheet.bend_count} gięć)",
            op_type=OperationType.SHEET_BENDING,
            workcenter="press_brake",
            cycle_time_sec=sb["piece_time_sec"],
            setup_time_sec=sb["setup_time_sec"],
            multiplier=1.0,
        )
        ops.append(bend_op)
        if last_pre_weld_op:
            edges.append(PrecedenceEdge(
                from_op_code=last_pre_weld_op,
                to_op_code=bend_op.op_code,
            ))
        last_pre_weld_op = bend_op.op_code

    # --- 3. DRILLING / THREADING ---
    hole_count = spec.geometry.holes.count if spec.geometry.holes else 0
    thread_count = spec.geometry.holes.threaded_count if spec.geometry.holes else 0

    if hole_count > 0 or thread_count > 0:
        dr = calc_drilling_time(hole_count, thread_count, norms=norms.drilling)
        drill_op = Operation(
            op_code=next_op_code(),
            op_name=f"Wiercenie ({hole_count} otw.) + gwintowanie ({thread_count})",
            op_type=OperationType.DRILLING,
            workcenter="drilling",
            cycle_time_sec=dr["piece_time_sec"],
            setup_time_sec=dr["setup_time_sec"],
            multiplier=1.0,
        )
        ops.append(drill_op)
        if last_pre_weld_op:
            edges.append(PrecedenceEdge(
                from_op_code=last_pre_weld_op,
                to_op_code=drill_op.op_code,
            ))
        last_pre_weld_op = drill_op.op_code

    # --- 4. WELDING ---
    weld_spec = spec.geometry.welds
    last_weld_op = None

    # Spot welding
    if weld_spec.spot_weld_count > 0:
        sw = calc_spot_welding_time(
            point_count=weld_spec.spot_weld_count,
            norms=norms.spot_welding,
        )
        spot_op = Operation(
            op_code=next_op_code(),
            op_name=f"Zgrzewanie punktowe ({weld_spec.spot_weld_count} pkt)",
            op_type=OperationType.SPOT_WELDING,
            workcenter="spot_welder",
            cycle_time_sec=sw["piece_time_sec"],
            setup_time_sec=sw["setup_time_sec"],
            multiplier=1.0,
            requires_fixture=True,
            fixture_type="szablon zgrzewalniczy",
        )
        ops.append(spot_op)
        if last_pre_weld_op:
            edges.append(PrecedenceEdge(
                from_op_code=last_pre_weld_op,
                to_op_code=spot_op.op_code,
            ))
        last_weld_op = spot_op.op_code

    # Linear welding (MIG/TIG)
    if weld_spec.linear_weld_length_mm > 0:
        thickness = spec.materials[0].thickness_mm or spec.materials[0].diameter_mm or 3.0 if spec.materials else 3.0
        wt = weld_spec.weld_type.value if weld_spec.weld_type != WeldingType.UNKNOWN else "MIG"
        lw = calc_linear_welding_time(
            weld_length_mm=weld_spec.linear_weld_length_mm,
            material_thickness_mm=thickness,
            weld_type=wt,
            norms_mig=norms.mig_welding,
            norms_tig=norms.tig_welding,
        )
        weld_op_type = OperationType.TIG_WELDING if wt == "TIG" else OperationType.MIG_WELDING
        wc = "tig_welding" if wt == "TIG" else "mig_welding"
        weld_op = Operation(
            op_code=next_op_code(),
            op_name=f"Spawanie {wt} ({weld_spec.linear_weld_length_mm:.0f}mm, {lw['passes']} ścieg)",
            op_type=weld_op_type,
            workcenter=wc,
            cycle_time_sec=lw["piece_time_sec"],
            setup_time_sec=lw["setup_time_sec"],
            multiplier=1.0,
            requires_fixture=True,
            fixture_type="oprzyrządowanie spawalnicze",
        )
        ops.append(weld_op)
        prev = last_weld_op or last_pre_weld_op
        if prev:
            edges.append(PrecedenceEdge(from_op_code=prev, to_op_code=weld_op.op_code))
        last_weld_op = weld_op.op_code

    # --- 5. GRINDING (post-weld) ---
    if last_weld_op:
        grind_op = Operation(
            op_code=next_op_code(),
            op_name="Szlifowanie po spawaniu",
            op_type=OperationType.GRINDING,
            workcenter="grinding",
            cycle_time_sec=60.0,  # base 1 min, scale with weld length
            setup_time_sec=120.0,
        )
        ops.append(grind_op)
        edges.append(PrecedenceEdge(from_op_code=last_weld_op, to_op_code=grind_op.op_code))
        last_post_processing_op = grind_op.op_code
    else:
        last_post_processing_op = last_pre_weld_op

    # --- 6. SURFACE FINISH ---
    finish = spec.process_requirements.surface_finish

    if finish == SurfaceFinish.GALVANIZED:
        # Degreasing before galvanizing
        degrease_op = Operation(
            op_code=next_op_code(),
            op_name="Odtłuszczanie",
            op_type=OperationType.DEGREASING,
            workcenter="degreasing",
            cycle_time_sec=120.0,  # 2 min per piece
            setup_time_sec=0.0,
        )
        ops.append(degrease_op)
        if last_post_processing_op:
            edges.append(PrecedenceEdge(from_op_code=last_post_processing_op, to_op_code=degrease_op.op_code))

        galv_op = Operation(
            op_code=next_op_code(),
            op_name="Cynkowanie ogniowe",
            op_type=OperationType.GALVANIZING,
            workcenter="outsourced_galvanizing",
            cycle_time_sec=0.0,  # outsourced, cost-based
            notes=["Usługa zewnętrzna — koszt na kg"],
        )
        ops.append(galv_op)
        edges.append(PrecedenceEdge(from_op_code=degrease_op.op_code, to_op_code=galv_op.op_code))
        last_post_processing_op = galv_op.op_code

    elif finish in (SurfaceFinish.POWDER_COATED, SurfaceFinish.PAINTED):
        degrease_op = Operation(
            op_code=next_op_code(),
            op_name="Odtłuszczanie",
            op_type=OperationType.DEGREASING,
            workcenter="degreasing",
            cycle_time_sec=120.0,
            setup_time_sec=0.0,
        )
        ops.append(degrease_op)
        if last_post_processing_op:
            edges.append(PrecedenceEdge(from_op_code=last_post_processing_op, to_op_code=degrease_op.op_code))

        paint_op = Operation(
            op_code=next_op_code(),
            op_name=f"Malowanie proszkowe (RAL {spec.process_requirements.paint_color_ral or '?'})",
            op_type=OperationType.POWDER_COATING,
            workcenter="outsourced_coating",
            cycle_time_sec=0.0,
            notes=["Usługa zewnętrzna — koszt na m²"],
        )
        ops.append(paint_op)
        edges.append(PrecedenceEdge(from_op_code=degrease_op.op_code, to_op_code=paint_op.op_code))
        last_post_processing_op = paint_op.op_code

    # --- 7. QA INSPECTION ---
    qa_op = Operation(
        op_code=next_op_code(),
        op_name="Kontrola jakości",
        op_type=OperationType.QA_INSPECTION,
        workcenter="qa_inspection",
        cycle_time_sec=60.0,
        qa_check_required=True,
        qa_check_description="Kontrola wymiarowa, wizualna, powłoki",
    )
    ops.append(qa_op)
    if last_post_processing_op:
        edges.append(PrecedenceEdge(from_op_code=last_post_processing_op, to_op_code=qa_op.op_code))

    # --- 8. PACKAGING ---
    pack_op = Operation(
        op_code=next_op_code(),
        op_name="Pakowanie",
        op_type=OperationType.PACKAGING,
        workcenter="packaging",
        cycle_time_sec=30.0,
    )
    ops.append(pack_op)
    edges.append(PrecedenceEdge(from_op_code=qa_op.op_code, to_op_code=pack_op.op_code))

    # Assign to plan
    plan.operations = ops
    plan.precedence_edges = edges
    plan.compute_totals()

    logger.info(
        "tech_plan_generated",
        plan_id=plan.plan_id,
        operations=len(ops),
        edges=len(edges),
        total_cycle_sec=round(plan.total_cycle_time_sec, 1),
    )

    return plan


def generate_quote(
    spec: PartSpec,
    plan: TechPlan,
    norms: AllNorms | None = None,
    labor_rates: dict | None = None,
    machine_rates: dict | None = None,
    material_prices: dict | None = None,
) -> Quote:
    """
    Generate a cost quote from a PartSpec and TechPlan.

    Computes material cost, labor, machine, fixture, coating, and overhead.
    """
    norms = norms or AllNorms()
    lr = labor_rates or DEFAULT_LABOR_RATES
    mr = machine_rates or DEFAULT_MACHINE_RATES
    mp = material_prices or DEFAULT_MATERIAL_PRICES

    batch = plan.batch_size
    series_mult = calc_series_multiplier(batch)

    quote = Quote(
        quote_id=f"Q-{uuid.uuid4().hex[:8]}",
        case_id=spec.part_id,
        part_id=spec.part_id,
        plan_id=plan.plan_id,
        quantity=batch,
    )

    breakdown: list[CostBreakdownItem] = []

    # --- Material cost ---
    weight_kg = spec.geometry.weight_kg or 0.0
    if weight_kg == 0 and spec.materials:
        # Rough estimate if weight not provided
        mat = spec.materials[0]
        if mat.form == MaterialForm.WIRE and mat.diameter_mm and spec.geometry.wire:
            # Wire: volume = π/4 × d² × L
            import math
            vol_mm3 = (math.pi / 4) * (mat.diameter_mm ** 2) * (spec.geometry.wire.total_length_mm or 0)
            weight_kg = (vol_mm3 / 1e9) * mat.density_kg_m3

    grade = spec.materials[0].grade if spec.materials else "default"
    price_per_kg = mp.get(grade, mp.get("default", 4.80))
    mat_cost = weight_kg * price_per_kg * batch

    breakdown.append(CostBreakdownItem(
        category="material",
        description=f"Materiał {grade} @ {price_per_kg} PLN/kg",
        quantity=weight_kg * batch,
        unit="kg",
        unit_cost=price_per_kg,
        total_cost=round(mat_cost, 2),
    ))
    quote.material_cost = round(mat_cost, 2)

    # --- Labor + Machine cost per operation ---
    total_labor = 0.0
    total_machine = 0.0

    for op in plan.operations:
        # Per-piece time with series multiplier
        effective_time_sec = (op.cycle_time_sec + op.handling_time_sec) * op.multiplier * series_mult
        # Amortized setup
        setup_per_piece_sec = op.setup_time_sec / max(batch, 1)
        total_per_piece_sec = effective_time_sec + setup_per_piece_sec
        # Apply social overhead
        total_with_overhead = apply_social_overhead(total_per_piece_sec, norms.social_overhead_percent)

        hours = total_with_overhead / 3600.0
        labor_rate = lr.get(op.workcenter, 70.0)
        machine_rate = mr.get(op.workcenter, 0.0)

        op_labor = hours * labor_rate * batch
        op_machine = hours * machine_rate * batch

        total_labor += op_labor
        total_machine += op_machine

        breakdown.append(CostBreakdownItem(
            category="labor",
            description=f"{op.op_name} — praca ({op.workcenter})",
            quantity=batch,
            unit="szt",
            unit_cost=round(hours * labor_rate, 2),
            total_cost=round(op_labor, 2),
            notes=f"{total_per_piece_sec:.1f}s/szt + {norms.social_overhead_percent}% naddatek",
        ))

        if machine_rate > 0:
            breakdown.append(CostBreakdownItem(
                category="machine",
                description=f"{op.op_name} — maszyna ({op.workcenter})",
                quantity=batch,
                unit="szt",
                unit_cost=round(hours * machine_rate, 2),
                total_cost=round(op_machine, 2),
            ))

    quote.labor_cost = round(total_labor, 2)
    quote.machine_cost = round(total_machine, 2)

    # --- Fixture cost ---
    total_fixture = 0.0
    for op in plan.operations:
        if op.requires_fixture and op.fixture_cost > 0:
            total_fixture += op.fixture_cost
        elif op.requires_fixture:
            # Estimate fixture cost: design + build
            estimated = (op.fixture_design_time_h + op.fixture_build_time_h) * 100.0  # 100 PLN/h estimate
            if estimated == 0:
                estimated = 500.0  # default fixture cost
            total_fixture += estimated
            breakdown.append(CostBreakdownItem(
                category="fixture",
                description=f"Przyrząd: {op.fixture_type or 'standard'}",
                quantity=1,
                unit="szt",
                unit_cost=estimated,
                total_cost=round(estimated, 2),
                notes="Amortyzowany na partię",
            ))
    quote.fixture_cost = round(total_fixture, 2)

    # --- Coating cost ---
    coating_cost = 0.0
    finish = spec.process_requirements.surface_finish

    if finish == SurfaceFinish.GALVANIZED and weight_kg > 0:
        gc = calc_galvanizing_cost(weight_kg * batch, norms.galvanizing)
        coating_cost = gc["cost"]
        breakdown.append(CostBreakdownItem(
            category="coating",
            description=f"Cynkowanie ogniowe @ {norms.galvanizing.rate_per_kg} PLN/kg",
            quantity=gc["total_mass_kg"],
            unit="kg",
            unit_cost=norms.galvanizing.rate_per_kg,
            total_cost=round(coating_cost, 2),
        ))

    elif finish in (SurfaceFinish.POWDER_COATED, SurfaceFinish.PAINTED):
        area = spec.geometry.surface_area_m2 or 0.0
        if area > 0:
            pc = calc_powder_coating_cost(area * batch, hole_count=spec.geometry.holes.count, batch_size=batch, norms=norms.powder_coating)
            coating_cost = pc["cost_per_piece"] * batch
            breakdown.append(CostBreakdownItem(
                category="coating",
                description=f"Malowanie proszkowe @ {norms.powder_coating.rate_per_m2} PLN/m²",
                quantity=round(area * batch, 2),
                unit="m²",
                unit_cost=norms.powder_coating.rate_per_m2,
                total_cost=round(coating_cost, 2),
            ))

    quote.coating_cost = round(coating_cost, 2)

    # --- Overhead (general factory overhead, e.g. 15%) ---
    subtotal = quote.material_cost + quote.labor_cost + quote.machine_cost + quote.fixture_cost + quote.coating_cost
    overhead = subtotal * 0.15  # 15% general overhead
    quote.overhead_cost = round(overhead, 2)

    breakdown.append(CostBreakdownItem(
        category="overhead",
        description="Narzut ogólnozakładowy 15%",
        quantity=1,
        unit="kpl",
        total_cost=round(overhead, 2),
    ))

    quote.breakdown = breakdown
    quote.parametric_estimate = round(subtotal + overhead, 2)
    quote.compute_total()

    quote.assumptions = [
        f"Wielkość partii: {batch} szt",
        f"Mnożnik seryjności: {series_mult}",
        f"Naddatek socjalny: {norms.social_overhead_percent}%",
        f"Narzut ogólnozakładowy: 15%",
        f"Cena materiału {grade}: {price_per_kg} PLN/kg",
    ]

    logger.info(
        "quote_generated",
        quote_id=quote.quote_id,
        total=quote.total_cost,
        unit_cost=quote.unit_cost,
        items=len(breakdown),
    )

    return quote
