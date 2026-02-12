"""PartSpec — structured extraction from a drawing or CAD file."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .enums import MaterialForm, SurfaceFinish, WeldingType


# ---------------------------------------------------------------------------
# Material specification
# ---------------------------------------------------------------------------

class MaterialSpec(BaseModel):
    """A single material entry (a part may use multiple materials)."""
    standard: Optional[str] = None  # e.g. "EN 10025"
    grade: Optional[str] = None  # e.g. "S235JR", "DC01"
    form: MaterialForm = MaterialForm.OTHER
    diameter_mm: Optional[float] = None  # for wire / bar / tube OD
    wall_thickness_mm: Optional[float] = None  # for tube
    thickness_mm: Optional[float] = None  # for sheet / flatbar
    width_mm: Optional[float] = None  # for flatbar / profile
    height_mm: Optional[float] = None  # for profile / angle
    leg1_mm: Optional[float] = None  # for angle
    leg2_mm: Optional[float] = None  # for angle
    density_kg_m3: float = 7850.0  # steel default


# ---------------------------------------------------------------------------
# Geometry sub-specs
# ---------------------------------------------------------------------------

class WireGeometry(BaseModel):
    total_length_mm: Optional[float] = None
    bend_count: int = 0
    bend_angles_deg: list[float] = Field(default_factory=list)
    min_bend_radius_mm: Optional[float] = None


class SheetGeometry(BaseModel):
    area_mm2: Optional[float] = None
    perimeter_mm: Optional[float] = None
    bend_count: int = 0
    bend_lengths_mm: list[float] = Field(default_factory=list)
    bend_angles_deg: list[float] = Field(default_factory=list)
    cutout_count: int = 0
    cutout_perimeter_mm: float = 0.0


class TubeGeometry(BaseModel):
    length_mm: Optional[float] = None
    bend_count: int = 0
    bend_angles_deg: list[float] = Field(default_factory=list)
    min_bend_radius_mm: Optional[float] = None


class WeldSpec(BaseModel):
    spot_weld_count: int = 0
    linear_weld_length_mm: float = 0.0
    weld_type: WeldingType = WeldingType.UNKNOWN
    weld_throat_mm: Optional[float] = None  # "a" dimension
    weld_positions: list[str] = Field(default_factory=list)  # e.g. ["PA", "PB"]


class HoleSpec(BaseModel):
    count: int = 0
    diameters_mm: list[float] = Field(default_factory=list)
    threaded_count: int = 0
    thread_specs: list[str] = Field(default_factory=list)  # e.g. ["M8", "M10x1.25"]


class Geometry(BaseModel):
    wire: Optional[WireGeometry] = None
    sheet: Optional[SheetGeometry] = None
    tube: Optional[TubeGeometry] = None
    welds: WeldSpec = Field(default_factory=WeldSpec)
    holes: HoleSpec = Field(default_factory=HoleSpec)
    overall_length_mm: Optional[float] = None
    overall_width_mm: Optional[float] = None
    overall_height_mm: Optional[float] = None
    weight_kg: Optional[float] = None
    surface_area_m2: Optional[float] = None


# ---------------------------------------------------------------------------
# Process requirements
# ---------------------------------------------------------------------------

class ProcessRequirements(BaseModel):
    welding: WeldingType = WeldingType.UNKNOWN
    surface_finish: SurfaceFinish = SurfaceFinish.UNKNOWN
    paint_color_ral: Optional[str] = None
    coating_thickness_um: Optional[float] = None
    tolerances_notes: list[str] = Field(default_factory=list)
    special_requirements: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# BOM component
# ---------------------------------------------------------------------------

class BOMItem(BaseModel):
    component_name: str
    qty_per_product: float = 1.0
    material: Optional[MaterialSpec] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Uncertainty tracking
# ---------------------------------------------------------------------------

class UncertaintyItem(BaseModel):
    """Tracks a single uncertain/missing field for human review."""
    field: str  # dotted path, e.g. "materials[0].grade"
    reason: str
    needs_human_review: bool = True
    suggested_value: Optional[str] = None


# ---------------------------------------------------------------------------
# PartSpec — the main output of Drawing Understanding agent
# ---------------------------------------------------------------------------

class PartSpec(BaseModel):
    """
    Structured specification of a single part/product extracted from drawings.

    This is the primary data contract between the Drawing Understanding agent
    and the Process Planning / Costing agents.
    """
    part_id: str = ""
    part_name: str = ""
    source_file_id: str = ""
    units: str = "mm"

    materials: list[MaterialSpec] = Field(default_factory=list)
    geometry: Geometry = Field(default_factory=Geometry)
    process_requirements: ProcessRequirements = Field(default_factory=ProcessRequirements)
    bom: list[BOMItem] = Field(default_factory=list)

    quantity: int = 1
    drawing_revision: Optional[str] = None
    drawing_notes: list[str] = Field(default_factory=list)

    uncertainty: list[UncertaintyItem] = Field(default_factory=list)

    # Embedding cache (filled by similarity module)
    feature_embedding: Optional[list[float]] = Field(default=None, exclude=True)
    visual_embedding: Optional[list[float]] = Field(default=None, exclude=True)
