"""Tests for core data models."""

import pytest

from estym_ai.models import (
    InquiryCase,
    CustomerInfo,
    AttachedFile,
    PartSpec,
    MaterialSpec,
    Geometry,
    WireGeometry,
    SheetGeometry,
    WeldSpec,
    HoleSpec,
    TechPlan,
    Operation,
    PrecedenceEdge,
    Quote,
    CostBreakdownItem,
)
from estym_ai.models.enums import (
    CaseStatus,
    FileType,
    MaterialForm,
    OperationType,
    PrecedenceRelation,
    SurfaceFinish,
    WeldingType,
)


class TestInquiryCase:
    def test_create_minimal(self):
        case = InquiryCase(
            case_id="RFQ-001",
            customer=CustomerInfo(name="Test Co"),
        )
        assert case.case_id == "RFQ-001"
        assert case.status == CaseStatus.NEW

    def test_with_files(self):
        case = InquiryCase(
            case_id="RFQ-002",
            customer=CustomerInfo(name="Test"),
            files=[
                AttachedFile(file_id="F1", filename="part.dxf", detected_type=FileType.DXF),
                AttachedFile(file_id="F2", filename="drawing.pdf", detected_type=FileType.PDF),
            ],
        )
        assert len(case.files) == 2
        assert case.files[0].detected_type == FileType.DXF


class TestPartSpec:
    def test_wire_product(self):
        spec = PartSpec(
            part_id="P-001",
            part_name="Drut gięty ø6",
            materials=[MaterialSpec(grade="S235", form=MaterialForm.WIRE, diameter_mm=6.0)],
            geometry=Geometry(
                wire=WireGeometry(total_length_mm=1200, bend_count=8, bend_angles_deg=[90, 90, 45, 90, 90, 45, 90, 90]),
            ),
        )
        assert spec.materials[0].form == MaterialForm.WIRE
        assert spec.geometry.wire.bend_count == 8

    def test_welded_assembly(self):
        spec = PartSpec(
            part_id="P-002",
            geometry=Geometry(
                welds=WeldSpec(spot_weld_count=24, weld_type=WeldingType.SPOT),
                holes=HoleSpec(count=4, diameters_mm=[8.5, 8.5, 10.5, 10.5]),
            ),
        )
        assert spec.geometry.welds.spot_weld_count == 24
        assert spec.geometry.holes.count == 4


class TestTechPlan:
    def test_topological_order(self):
        plan = TechPlan(
            operations=[
                Operation(op_code="OP010", op_name="Cięcie", op_type=OperationType.CUTTING, workcenter="saw"),
                Operation(op_code="OP020", op_name="Gięcie", op_type=OperationType.WIRE_BENDING, workcenter="cnc"),
                Operation(op_code="OP030", op_name="Spawanie", op_type=OperationType.SPOT_WELDING, workcenter="spot"),
                Operation(op_code="OP040", op_name="Cynkowanie", op_type=OperationType.GALVANIZING, workcenter="galv"),
            ],
            precedence_edges=[
                PrecedenceEdge(from_op_code="OP010", to_op_code="OP020"),
                PrecedenceEdge(from_op_code="OP020", to_op_code="OP030"),
                PrecedenceEdge(from_op_code="OP030", to_op_code="OP040"),
            ],
        )
        order = plan.topological_order()
        assert order == ["OP010", "OP020", "OP030", "OP040"]

    def test_compute_totals(self):
        plan = TechPlan(
            batch_size=10,
            operations=[
                Operation(op_code="OP010", op_name="Cut", op_type=OperationType.CUTTING,
                         workcenter="saw", cycle_time_sec=5.0, setup_time_sec=300.0, multiplier=1.0),
                Operation(op_code="OP020", op_name="Bend", op_type=OperationType.WIRE_BENDING,
                         workcenter="cnc", cycle_time_sec=12.0, setup_time_sec=900.0, multiplier=1.0),
            ],
        )
        plan.compute_totals()
        assert plan.total_cycle_time_sec == 17.0  # 5 + 12
        assert plan.total_setup_time_sec == 1200.0  # 300 + 900
        assert plan.total_time_with_overhead_sec > 0


class TestQuote:
    def test_compute_total(self):
        quote = Quote(
            material_cost=100,
            labor_cost=200,
            machine_cost=50,
            fixture_cost=80,
            coating_cost=60,
            overhead_cost=73.5,
            quantity=10,
        )
        quote.compute_total()
        assert quote.total_cost == 563.5
        assert quote.unit_cost == pytest.approx(56.35, abs=0.01)
