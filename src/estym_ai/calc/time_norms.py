"""Parametric time norm formulas for steel manufacturing operations.

All times are in SECONDS unless otherwise noted.
These formulas provide the deterministic baseline; the ML model
learns residuals on top of these estimates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


# ============================================================================
# Configurable norm parameters (versioned, overridable per-company)
# ============================================================================

@dataclass
class WireBendingNorms:
    """Time norms for CNC wire bending."""
    load_time_sec: float = 4.0  # 3-5s
    time_per_bend_sec: float = 2.0  # standard 2s/bend
    feed_speed_mm_per_sec: float = 200.0  # wire feed speed
    cut_time_sec: float = 1.5  # 1-2s
    unload_time_sec: float = 2.5  # 2-3s
    setup_time_sec: float = 900.0  # 15 min per new part
    efficiency_factor: float = 0.90  # 0.85-0.95 for series


@dataclass
class SheetBendingNorms:
    """Time norms for press brake sheet bending."""
    load_time_sec: float = 7.0  # 5-10s
    time_per_bend_sec: float = 15.0  # standard 15s
    time_per_bend_high_volume_sec: float = 12.0  # >5 bends learning curve
    reposition_time_sec: float = 4.0  # 3-5s per bend
    unload_time_sec: float = 7.0  # 5-10s
    setup_time_sec: float = 1200.0  # 15-30 min per new part
    high_volume_bend_threshold: int = 5  # above this → use learning curve rate


@dataclass
class SpotWeldingNorms:
    """Time norms for spot welding."""
    time_per_point_sec: float = 15.0  # includes positioning, pressing, weld, hold, retract
    actual_weld_time_sec: float = 0.5  # real weld time 0.25-0.75s
    electrode_travel_sec_per_100mm: float = 6.0  # 6s per 100mm travel
    part_reposition_sec: float = 5.0  # per reposition
    setup_time_sec: float = 600.0  # 10 min


@dataclass
class MIGWeldingNorms:
    """Time norms for MIG welding on steel."""
    weld_speed_mm_per_min: float = 225.0  # 150-300 mm/min average
    preparation_factor: float = 0.35  # 20-50% for prep, fixturing, cleaning
    arc_on_time_ratio: float = 0.25  # only 25% of shift is actual arc-on
    passes_threshold_mm: float = 6.0  # above this thickness → multi-pass
    setup_time_sec: float = 600.0


@dataclass
class TIGWeldingNorms:
    """Time norms for TIG welding (slower, higher quality)."""
    weld_speed_mm_per_min: float = 120.0  # TIG is slower than MIG
    preparation_factor: float = 0.40
    arc_on_time_ratio: float = 0.20
    setup_time_sec: float = 900.0


@dataclass
class GalvanizingNorms:
    """Cost norms for hot-dip galvanizing."""
    rate_per_kg: float = 3.50  # PLN/kg (typical Polish market)
    zinc_mass_addition_percent: float = 6.0  # 5-7% mass increase
    min_charge: float = 150.0  # minimum charge per batch


@dataclass
class PowderCoatingNorms:
    """Cost norms for powder coating."""
    rate_per_m2: float = 45.0  # PLN/m² (typical Polish market)
    masking_time_per_hole_sec: float = 30.0
    hanging_time_per_piece_sec: float = 60.0
    curing_time_per_batch_sec: float = 1200.0  # 20 min oven time
    min_charge: float = 200.0  # minimum charge per batch


@dataclass
class CuttingNorms:
    """Time norms for cutting operations."""
    saw_speed_mm_per_sec: float = 5.0  # band saw on steel
    laser_speed_mm_per_sec: float = 50.0  # fiber laser cutting
    shear_time_sec: float = 3.0  # guillotine shear per cut
    setup_time_sec: float = 300.0  # 5 min


@dataclass
class DrillingNorms:
    """Time norms for drilling."""
    time_per_hole_sec: float = 15.0  # including approach/retract
    time_per_thread_sec: float = 20.0  # tapping
    setup_time_sec: float = 300.0


@dataclass
class AllNorms:
    """Complete set of time/cost norms for the factory."""
    wire_bending: WireBendingNorms = None
    sheet_bending: SheetBendingNorms = None
    spot_welding: SpotWeldingNorms = None
    mig_welding: MIGWeldingNorms = None
    tig_welding: TIGWeldingNorms = None
    galvanizing: GalvanizingNorms = None
    powder_coating: PowderCoatingNorms = None
    cutting: CuttingNorms = None
    drilling: DrillingNorms = None

    social_overhead_percent: float = 10.0  # "naddatek socjalny"

    def __post_init__(self):
        if self.wire_bending is None:
            self.wire_bending = WireBendingNorms()
        if self.sheet_bending is None:
            self.sheet_bending = SheetBendingNorms()
        if self.spot_welding is None:
            self.spot_welding = SpotWeldingNorms()
        if self.mig_welding is None:
            self.mig_welding = MIGWeldingNorms()
        if self.tig_welding is None:
            self.tig_welding = TIGWeldingNorms()
        if self.galvanizing is None:
            self.galvanizing = GalvanizingNorms()
        if self.powder_coating is None:
            self.powder_coating = PowderCoatingNorms()
        if self.cutting is None:
            self.cutting = CuttingNorms()
        if self.drilling is None:
            self.drilling = DrillingNorms()


# ============================================================================
# Time calculation functions
# ============================================================================

def calc_wire_bending_time(
    wire_length_mm: float,
    bend_count: int,
    batch_size: int = 1,
    norms: WireBendingNorms | None = None,
) -> dict:
    """
    Calculate wire bending cycle time.

    Formula: T = T_load + (N_bends × 2.0s) + T_feed(length/speed) + T_cut + T_unload
    Series: T_series = T_piece × N × efficiency
    """
    n = norms or WireBendingNorms()

    feed_time = wire_length_mm / n.feed_speed_mm_per_sec
    piece_time = (
        n.load_time_sec
        + (bend_count * n.time_per_bend_sec)
        + feed_time
        + n.cut_time_sec
        + n.unload_time_sec
    )

    batch_time = piece_time * batch_size * n.efficiency_factor
    amortized_setup = n.setup_time_sec / max(batch_size, 1)

    return {
        "piece_time_sec": round(piece_time, 2),
        "batch_time_sec": round(batch_time, 2),
        "setup_time_sec": n.setup_time_sec,
        "amortized_setup_per_piece_sec": round(amortized_setup, 2),
        "total_per_piece_sec": round(piece_time + amortized_setup, 2),
    }


def calc_sheet_bending_time(
    bend_count: int,
    batch_size: int = 1,
    norms: SheetBendingNorms | None = None,
) -> dict:
    """
    Calculate press brake bending cycle time.

    Formula: T = T_load + (N_bends × T_per_bend) + N_bends × T_reposition + T_unload
    """
    n = norms or SheetBendingNorms()

    time_per_bend = (
        n.time_per_bend_high_volume_sec
        if bend_count > n.high_volume_bend_threshold
        else n.time_per_bend_sec
    )

    piece_time = (
        n.load_time_sec
        + (bend_count * time_per_bend)
        + (bend_count * n.reposition_time_sec)
        + n.unload_time_sec
    )

    amortized_setup = n.setup_time_sec / max(batch_size, 1)

    return {
        "piece_time_sec": round(piece_time, 2),
        "setup_time_sec": n.setup_time_sec,
        "amortized_setup_per_piece_sec": round(amortized_setup, 2),
        "total_per_piece_sec": round(piece_time + amortized_setup, 2),
    }


def calc_spot_welding_time(
    point_count: int,
    avg_electrode_travel_mm: float = 50.0,
    repositions: int = 0,
    norms: SpotWeldingNorms | None = None,
) -> dict:
    """
    Calculate spot welding cycle time.

    Formula: T = N_points × 15s + T_travel + T_reposition
    """
    n = norms or SpotWeldingNorms()

    weld_time = point_count * n.time_per_point_sec
    travel_time = (avg_electrode_travel_mm / 100.0) * n.electrode_travel_sec_per_100mm * point_count
    reposition_time = repositions * n.part_reposition_sec

    piece_time = weld_time + travel_time + reposition_time

    return {
        "piece_time_sec": round(piece_time, 2),
        "weld_time_sec": round(weld_time, 2),
        "travel_time_sec": round(travel_time, 2),
        "setup_time_sec": n.setup_time_sec,
    }


def calc_linear_welding_time(
    weld_length_mm: float,
    material_thickness_mm: float = 3.0,
    weld_type: str = "MIG",
    norms_mig: MIGWeldingNorms | None = None,
    norms_tig: TIGWeldingNorms | None = None,
) -> dict:
    """
    Calculate MIG/TIG welding time.

    Formula: T = (length / speed) × N_passes × (1 + prep_factor)
    """
    if weld_type.upper() == "TIG":
        n = norms_tig or TIGWeldingNorms()
    else:
        n = norms_mig or MIGWeldingNorms()

    # Number of passes based on thickness
    if material_thickness_mm <= 6:
        passes = 1
    elif material_thickness_mm <= 12:
        passes = 2
    else:
        passes = max(2, math.ceil(material_thickness_mm / 6))

    base_time_sec = (weld_length_mm / n.weld_speed_mm_per_min) * 60  # convert to seconds
    total_time = base_time_sec * passes * (1 + n.preparation_factor)

    return {
        "piece_time_sec": round(total_time, 2),
        "base_weld_time_sec": round(base_time_sec, 2),
        "passes": passes,
        "preparation_factor": n.preparation_factor,
        "setup_time_sec": n.setup_time_sec,
    }


def calc_galvanizing_cost(
    mass_kg: float,
    norms: GalvanizingNorms | None = None,
) -> dict:
    """
    Calculate hot-dip galvanizing cost.

    Cost = max(mass × rate/kg, min_charge). Zinc adds 5-7% mass.
    """
    n = norms or GalvanizingNorms()

    zinc_mass = mass_kg * (n.zinc_mass_addition_percent / 100)
    total_mass = mass_kg + zinc_mass
    cost = max(total_mass * n.rate_per_kg, n.min_charge)

    return {
        "cost": round(cost, 2),
        "base_mass_kg": round(mass_kg, 3),
        "zinc_addition_kg": round(zinc_mass, 3),
        "total_mass_kg": round(total_mass, 3),
        "rate_per_kg": n.rate_per_kg,
    }


def calc_powder_coating_cost(
    surface_area_m2: float,
    hole_count: int = 0,
    batch_size: int = 1,
    norms: PowderCoatingNorms | None = None,
) -> dict:
    """
    Calculate powder coating cost.

    Cost = area × rate/m² + masking + hanging + curing (amortized per batch)
    """
    n = norms or PowderCoatingNorms()

    coating_cost = surface_area_m2 * n.rate_per_m2
    masking_time = hole_count * n.masking_time_per_hole_sec
    hanging_time = n.hanging_time_per_piece_sec
    curing_amortized = n.curing_time_per_batch_sec / max(batch_size, 1)

    total = max(coating_cost, n.min_charge / max(batch_size, 1))

    return {
        "cost_per_piece": round(total, 2),
        "coating_cost": round(coating_cost, 2),
        "masking_time_sec": round(masking_time, 2),
        "hanging_time_sec": round(hanging_time, 2),
        "curing_time_amortized_sec": round(curing_amortized, 2),
        "rate_per_m2": n.rate_per_m2,
    }


def calc_cutting_time(
    cut_length_mm: float = 0.0,
    cut_count: int = 1,
    method: str = "saw",
    norms: CuttingNorms | None = None,
) -> dict:
    """Calculate cutting time for saw, laser, or shear."""
    n = norms or CuttingNorms()

    if method == "laser":
        piece_time = cut_length_mm / n.laser_speed_mm_per_sec
    elif method == "shear":
        piece_time = n.shear_time_sec * cut_count
    else:  # saw
        piece_time = cut_length_mm / n.saw_speed_mm_per_sec if cut_length_mm > 0 else n.shear_time_sec * cut_count

    return {
        "piece_time_sec": round(piece_time, 2),
        "setup_time_sec": n.setup_time_sec,
        "method": method,
    }


def calc_drilling_time(
    hole_count: int,
    thread_count: int = 0,
    norms: DrillingNorms | None = None,
) -> dict:
    """Calculate drilling and tapping time."""
    n = norms or DrillingNorms()

    drill_time = hole_count * n.time_per_hole_sec
    tap_time = thread_count * n.time_per_thread_sec
    piece_time = drill_time + tap_time

    return {
        "piece_time_sec": round(piece_time, 2),
        "drill_time_sec": round(drill_time, 2),
        "tap_time_sec": round(tap_time, 2),
        "setup_time_sec": n.setup_time_sec,
    }


def calc_bending_force_kn(
    tensile_strength_mpa: float,
    bend_length_mm: float,
    thickness_mm: float,
    die_opening_mm: float,
) -> float:
    """
    Calculate required bending force for press brake.

    Formula: F = (1.33 × σ_t × L × T²) / V
    Returns force in kN.
    """
    force_n = (1.33 * tensile_strength_mpa * bend_length_mm * thickness_mm ** 2) / die_opening_mm
    return round(force_n / 1000.0, 2)  # N → kN


def apply_social_overhead(time_sec: float, overhead_percent: float = 10.0) -> float:
    """Apply the social/technical overhead factor."""
    return time_sec * (1 + overhead_percent / 100)


def calc_series_multiplier(batch_size: int) -> float:
    """
    Calculate efficiency multiplier for series production.

    Learning curve: bigger batches → slightly less time per piece.
    """
    if batch_size <= 1:
        return 1.0
    elif batch_size <= 10:
        return 0.95
    elif batch_size <= 50:
        return 0.90
    elif batch_size <= 200:
        return 0.87
    else:
        return 0.85
