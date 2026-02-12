"""Tests for the cost calculation engine."""

import pytest

from estym_ai.calc.cost_engine import generate_quote, generate_tech_plan
from estym_ai.calc.time_norms import AllNorms
from estym_ai.models.enums import MaterialForm, SurfaceFinish, WeldingType
from estym_ai.models.part_spec import (
    Geometry,
    HoleSpec,
    MaterialSpec,
    PartSpec,
    ProcessRequirements,
    SheetGeometry,
    WeldSpec,
    WireGeometry,
)


def _make_wire_spec() -> PartSpec:
    """Create a typical wire product spec for testing."""
    return PartSpec(
        part_id="TEST-WIRE-001",
        part_name="Drut gięty ø6 S235",
        materials=[MaterialSpec(grade="S235", form=MaterialForm.WIRE, diameter_mm=6.0, density_kg_m3=7850)],
        geometry=Geometry(
            wire=WireGeometry(total_length_mm=800, bend_count=6, bend_angles_deg=[90, 90, 45, 90, 90, 45]),
            weight_kg=0.18,
        ),
        process_requirements=ProcessRequirements(surface_finish=SurfaceFinish.GALVANIZED),
        quantity=100,
    )


def _make_welded_assembly_spec() -> PartSpec:
    """Create a welded assembly spec for testing."""
    return PartSpec(
        part_id="TEST-WELD-001",
        part_name="Zespół spawany z blachy 3mm",
        materials=[MaterialSpec(grade="S235", form=MaterialForm.SHEET, thickness_mm=3.0)],
        geometry=Geometry(
            sheet=SheetGeometry(area_mm2=50000, perimeter_mm=1000, bend_count=2),
            welds=WeldSpec(spot_weld_count=12, linear_weld_length_mm=500, weld_type=WeldingType.MIG),
            holes=HoleSpec(count=4, diameters_mm=[8.5, 8.5, 10.5, 10.5], threaded_count=2, thread_specs=["M8", "M10"]),
            weight_kg=3.2,
            surface_area_m2=0.12,
        ),
        process_requirements=ProcessRequirements(
            welding=WeldingType.MIG,
            surface_finish=SurfaceFinish.POWDER_COATED,
            paint_color_ral="7035",
        ),
        quantity=50,
    )


class TestTechPlanGeneration:
    def test_wire_product_generates_valid_plan(self):
        spec = _make_wire_spec()
        plan = generate_tech_plan(spec, batch_size=100)

        assert len(plan.operations) > 0
        assert plan.batch_size == 100
        assert plan.total_cycle_time_sec > 0

        # Should have cutting + wire bending at minimum
        op_types = [op.op_type.value for op in plan.operations]
        assert "cutting" in op_types
        assert "wire_bending" in op_types

    def test_welded_assembly_has_welding_ops(self):
        spec = _make_welded_assembly_spec()
        plan = generate_tech_plan(spec, batch_size=50)

        op_types = [op.op_type.value for op in plan.operations]
        assert "spot_welding" in op_types
        assert "mig_welding" in op_types
        assert "drilling" in op_types

    def test_galvanized_product_has_degreasing(self):
        spec = _make_wire_spec()
        plan = generate_tech_plan(spec)

        op_types = [op.op_type.value for op in plan.operations]
        assert "degreasing" in op_types
        assert "galvanizing" in op_types

    def test_precedence_graph_is_valid(self):
        spec = _make_welded_assembly_spec()
        plan = generate_tech_plan(spec)

        # Topological sort should return all operations
        order = plan.topological_order()
        assert len(order) == len(plan.operations)

        # All op_codes should be in the order
        op_codes = {op.op_code for op in plan.operations}
        assert set(order) == op_codes

    def test_qa_and_packaging_always_present(self):
        spec = _make_wire_spec()
        plan = generate_tech_plan(spec)

        op_types = [op.op_type.value for op in plan.operations]
        assert "qa_inspection" in op_types
        assert "packaging" in op_types


class TestQuoteGeneration:
    def test_wire_product_quote(self):
        spec = _make_wire_spec()
        norms = AllNorms()
        plan = generate_tech_plan(spec, norms=norms, batch_size=100)
        quote = generate_quote(spec, plan, norms=norms)

        assert quote.total_cost > 0
        assert quote.unit_cost > 0
        assert quote.material_cost >= 0
        assert quote.labor_cost > 0
        assert len(quote.breakdown) > 0
        assert len(quote.assumptions) > 0

    def test_welded_assembly_quote(self):
        spec = _make_welded_assembly_spec()
        norms = AllNorms()
        plan = generate_tech_plan(spec, norms=norms, batch_size=50)
        quote = generate_quote(spec, plan, norms=norms)

        assert quote.total_cost > 0
        assert quote.coating_cost > 0  # powder coating
        assert quote.fixture_cost > 0  # welding fixtures

    def test_larger_batch_lower_unit_cost(self):
        spec = _make_wire_spec()
        norms = AllNorms()

        plan1 = generate_tech_plan(spec, norms=norms, batch_size=1)
        quote1 = generate_quote(spec, plan1, norms=norms)

        plan100 = generate_tech_plan(spec, norms=norms, batch_size=100)
        quote100 = generate_quote(spec, plan100, norms=norms)

        # Unit cost should be lower for larger batch (setup amortization)
        assert quote100.unit_cost < quote1.unit_cost

    def test_quote_has_correct_currency(self):
        spec = _make_wire_spec()
        plan = generate_tech_plan(spec)
        quote = generate_quote(spec, plan)
        assert quote.currency == "PLN"
