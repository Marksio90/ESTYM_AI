"""Tests for parametric time norm calculations."""

import pytest

from estym_ai.calc.time_norms import (
    WireBendingNorms,
    SheetBendingNorms,
    SpotWeldingNorms,
    MIGWeldingNorms,
    GalvanizingNorms,
    PowderCoatingNorms,
    calc_wire_bending_time,
    calc_sheet_bending_time,
    calc_spot_welding_time,
    calc_linear_welding_time,
    calc_galvanizing_cost,
    calc_powder_coating_cost,
    calc_cutting_time,
    calc_drilling_time,
    calc_bending_force_kn,
    apply_social_overhead,
    calc_series_multiplier,
)


class TestWireBending:
    def test_basic_wire_bending(self):
        result = calc_wire_bending_time(wire_length_mm=500, bend_count=4, batch_size=1)
        assert result["piece_time_sec"] > 0
        assert result["setup_time_sec"] == 900.0  # 15 min default
        assert result["total_per_piece_sec"] > result["piece_time_sec"]

    def test_more_bends_takes_longer(self):
        r1 = calc_wire_bending_time(wire_length_mm=500, bend_count=2)
        r2 = calc_wire_bending_time(wire_length_mm=500, bend_count=10)
        assert r2["piece_time_sec"] > r1["piece_time_sec"]

    def test_batch_amortizes_setup(self):
        r1 = calc_wire_bending_time(wire_length_mm=500, bend_count=4, batch_size=1)
        r100 = calc_wire_bending_time(wire_length_mm=500, bend_count=4, batch_size=100)
        assert r100["amortized_setup_per_piece_sec"] < r1["amortized_setup_per_piece_sec"]

    def test_custom_norms(self):
        norms = WireBendingNorms(time_per_bend_sec=3.0)
        result = calc_wire_bending_time(wire_length_mm=500, bend_count=4, norms=norms)
        # 4 bends × 3s = 12s for bending alone
        assert result["piece_time_sec"] > 12.0


class TestSheetBending:
    def test_basic_sheet_bending(self):
        result = calc_sheet_bending_time(bend_count=3)
        assert result["piece_time_sec"] > 0
        assert result["setup_time_sec"] == 1200.0  # 20 min default

    def test_learning_curve_kicks_in(self):
        r5 = calc_sheet_bending_time(bend_count=5)
        r6 = calc_sheet_bending_time(bend_count=6)
        # At 6 bends, the per-bend time drops (12s vs 15s)
        # But 6 bends should still take more total time than 5
        assert r6["piece_time_sec"] > r5["piece_time_sec"]


class TestSpotWelding:
    def test_basic_spot_welding(self):
        result = calc_spot_welding_time(point_count=20)
        assert result["piece_time_sec"] > 0
        assert result["weld_time_sec"] == 20 * 15.0  # 20 points × 15s

    def test_more_points_takes_longer(self):
        r10 = calc_spot_welding_time(point_count=10)
        r50 = calc_spot_welding_time(point_count=50)
        assert r50["piece_time_sec"] > r10["piece_time_sec"]


class TestLinearWelding:
    def test_mig_welding(self):
        result = calc_linear_welding_time(weld_length_mm=1000, material_thickness_mm=3.0, weld_type="MIG")
        assert result["piece_time_sec"] > 0
        assert result["passes"] == 1  # 3mm = single pass

    def test_thick_material_multi_pass(self):
        result = calc_linear_welding_time(weld_length_mm=1000, material_thickness_mm=10.0)
        assert result["passes"] == 2  # 10mm = 2 passes

    def test_tig_slower_than_mig(self):
        mig = calc_linear_welding_time(weld_length_mm=1000, weld_type="MIG")
        tig = calc_linear_welding_time(weld_length_mm=1000, weld_type="TIG")
        assert tig["piece_time_sec"] > mig["piece_time_sec"]


class TestGalvanizing:
    def test_basic_galvanizing(self):
        result = calc_galvanizing_cost(mass_kg=50)
        assert result["cost"] > 0
        assert result["zinc_addition_kg"] > 0
        assert result["total_mass_kg"] > result["base_mass_kg"]

    def test_minimum_charge(self):
        result = calc_galvanizing_cost(mass_kg=0.1)  # very small
        assert result["cost"] >= 150.0  # min charge


class TestPowderCoating:
    def test_basic_powder_coating(self):
        result = calc_powder_coating_cost(surface_area_m2=2.0)
        assert result["cost_per_piece"] > 0
        assert result["rate_per_m2"] == 45.0


class TestUtilities:
    def test_bending_force(self):
        force = calc_bending_force_kn(
            tensile_strength_mpa=400,
            bend_length_mm=1000,
            thickness_mm=3,
            die_opening_mm=24,
        )
        assert force > 0
        # F = 1.33 × 400 × 1000 × 9 / 24 = 199,500 N ≈ 199.5 kN
        assert 190 < force < 210

    def test_social_overhead(self):
        assert apply_social_overhead(100, 10.0) == 110.0
        assert apply_social_overhead(100, 0.0) == 100.0

    def test_series_multiplier(self):
        assert calc_series_multiplier(1) == 1.0
        assert calc_series_multiplier(10) == 0.95
        assert calc_series_multiplier(100) == 0.90
        assert calc_series_multiplier(500) == 0.85

    def test_cutting_methods(self):
        saw = calc_cutting_time(cut_length_mm=100, method="saw")
        laser = calc_cutting_time(cut_length_mm=100, method="laser")
        assert laser["piece_time_sec"] < saw["piece_time_sec"]  # laser is faster

    def test_drilling(self):
        result = calc_drilling_time(hole_count=5, thread_count=2)
        assert result["piece_time_sec"] > 0
        assert result["tap_time_sec"] > 0
