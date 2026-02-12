"""Drawing Analyzer Agent — extracts PartSpec from CAD files and PDFs."""

from __future__ import annotations

import uuid

import structlog

from ..config.settings import get_settings
from ..models.enums import FileType, MaterialForm, SurfaceFinish, WeldingType
from ..models.part_spec import (
    BOMItem,
    Geometry,
    HoleSpec,
    MaterialSpec,
    PartSpec,
    ProcessRequirements,
    SheetGeometry,
    UncertaintyItem,
    WeldSpec,
    WireGeometry,
)
from ..pipeline.dxf_parser import parse_dxf
from ..pipeline.pdf_processor import process_pdf
from ..pipeline.step_analyzer import analyze_mesh, analyze_step
from ..pipeline.vision_analyzer import analyze_drawing_with_openai
from .state import RFQState

logger = structlog.get_logger()


async def drawing_analyzer_node(state: RFQState) -> dict:
    """
    LangGraph node: analyze all attached files and generate PartSpecs.

    Pipeline per file:
    1. Route by file type
    2. For CAD (DXF/STEP): geometric extraction
    3. For PDF: render → vision analysis + text/table extraction
    4. Merge into PartSpec
    """
    settings = get_settings()
    part_specs: list[PartSpec] = []

    if not state.case:
        return {"errors": ["No case found in state"]}

    for attached_file in state.case.files:
        try:
            spec = await _analyze_single_file(attached_file, settings)
            if spec:
                part_specs.append(spec)
        except Exception as e:
            logger.error("file_analysis_failed", file=attached_file.filename, error=str(e))
            # Create minimal spec with uncertainty
            part_specs.append(PartSpec(
                part_id=f"P-{uuid.uuid4().hex[:8]}",
                part_name=attached_file.filename,
                source_file_id=attached_file.file_id,
                uncertainty=[UncertaintyItem(
                    field="all",
                    reason=f"Analiza pliku nie powiodła się: {e}",
                    needs_human_review=True,
                )],
            ))

    logger.info("drawing_analysis_complete", specs_generated=len(part_specs))

    return {
        "part_specs": part_specs,
        "current_step": "material_identification",
        "messages": [{"agent": "drawing_analyzer", "content": f"Wygenerowano {len(part_specs)} specyfikacji z rysunków"}],
    }


async def _analyze_single_file(attached_file, settings) -> PartSpec | None:
    """Analyze a single file based on its type."""
    file_type = attached_file.detected_type
    file_path = attached_file.storage_key  # In production: download from MinIO first

    spec = PartSpec(
        part_id=f"P-{uuid.uuid4().hex[:8]}",
        part_name=attached_file.filename,
        source_file_id=attached_file.file_id,
    )

    if file_type == FileType.DXF:
        spec = _process_dxf(file_path, spec)

    elif file_type == FileType.STEP:
        spec = _process_step(file_path, spec)

    elif file_type == FileType.PDF:
        spec = await _process_pdf(file_path, spec, settings)

    else:
        spec.uncertainty.append(UncertaintyItem(
            field="all",
            reason=f"Nieobsługiwany format pliku: {file_type.value}",
            needs_human_review=True,
        ))

    return spec


def _process_dxf(file_path: str, spec: PartSpec) -> PartSpec:
    """Process DXF file and populate PartSpec."""
    result = parse_dxf(file_path)

    if result.errors:
        for err in result.errors:
            spec.uncertainty.append(UncertaintyItem(field="geometry", reason=err))

    # Map DXF extraction to PartSpec geometry
    if result.bend_count > 0:
        spec.geometry.wire = WireGeometry(
            total_length_mm=result.total_line_length_mm,
            bend_count=result.bend_count,
            bend_angles_deg=result.bend_angles_deg,
        )

    # Circles → potential holes
    small_circles = [d for d in result.circle_diameters_mm if d < 50]
    if small_circles:
        spec.geometry.holes = HoleSpec(
            count=len(small_circles),
            diameters_mm=small_circles,
        )

    # Bounding box → overall dimensions
    if result.bbox_min and result.bbox_max:
        spec.geometry.overall_length_mm = result.bbox_max[0] - result.bbox_min[0]
        spec.geometry.overall_width_mm = result.bbox_max[1] - result.bbox_min[1]
        spec.geometry.overall_height_mm = result.bbox_max[2] - result.bbox_min[2]

    # Text annotations → material, notes
    for text in result.texts:
        _extract_from_text(text, spec)

    # Block references → potential multipliers
    if result.block_references:
        spec.drawing_notes.append(
            f"Znaleziono {len(result.block_references)} referencji bloków (potencjalne powtórzenia)"
        )

    logger.info("dxf_to_spec", bends=result.bend_count, holes=len(small_circles), texts=len(result.texts))
    return spec


def _process_step(file_path: str, spec: PartSpec) -> PartSpec:
    """Process STEP file and populate PartSpec."""
    result = analyze_step(file_path)

    if result.errors:
        for err in result.errors:
            spec.uncertainty.append(UncertaintyItem(field="geometry", reason=err))
        return spec

    spec.geometry.weight_kg = result.mass_kg
    spec.geometry.surface_area_m2 = result.surface_area_mm2 / 1e6  # mm² → m²

    if result.bbox_min and result.bbox_max:
        spec.geometry.overall_length_mm = result.bbox_max[0] - result.bbox_min[0]
        spec.geometry.overall_width_mm = result.bbox_max[1] - result.bbox_min[1]
        spec.geometry.overall_height_mm = result.bbox_max[2] - result.bbox_min[2]

    # Holes from cylindrical faces
    if result.detected_holes:
        spec.geometry.holes = HoleSpec(
            count=len(result.detected_holes),
            diameters_mm=[h["diameter_mm"] for h in result.detected_holes],
        )

    # Tube detection
    if result.is_likely_tube:
        spec.materials.append(MaterialSpec(
            form=MaterialForm.TUBE,
            diameter_mm=result.tube_outer_diameter_mm,
        ))

    # Sheet metal detection
    if result.is_likely_sheet:
        spec.materials.append(MaterialSpec(
            form=MaterialForm.SHEET,
            thickness_mm=result.sheet_thickness_mm,
        ))

    if not spec.materials:
        spec.uncertainty.append(UncertaintyItem(
            field="materials",
            reason="Nie udało się automatycznie określić materiału z geometrii 3D",
            needs_human_review=True,
        ))

    return spec


async def _process_pdf(file_path: str, spec: PartSpec, settings) -> PartSpec:
    """Process PDF file: render pages + vision analysis + text/table extraction."""
    pdf_result = process_pdf(file_path)

    if pdf_result.errors:
        for err in pdf_result.errors:
            spec.uncertainty.append(UncertaintyItem(field="all", reason=err))
        return spec

    # Extract info from title block
    tb = pdf_result.title_block
    if "material" in tb:
        _parse_material_string(tb["material"], spec)
    if "surface_finish" in tb:
        _parse_finish_string(tb["surface_finish"], spec)
    if "weight" in tb:
        try:
            spec.geometry.weight_kg = float(tb["weight"].replace(",", ".").split()[0])
        except (ValueError, IndexError):
            pass

    # Extract from text
    for text in pdf_result.page_texts:
        _extract_from_text(text, spec)

    # Vision analysis (if images available and API key configured)
    if pdf_result.page_images and settings.openai_api_key:
        additional_context = ""
        if pdf_result.full_text:
            additional_context += f"Tekst z PDF:\n{pdf_result.full_text[:2000]}\n\n"
        if pdf_result.tables:
            for table in pdf_result.tables:
                additional_context += f"Tabela (str. {table.page_number}):\n"
                additional_context += str(table.header) + "\n"
                for row in table.rows[:10]:
                    additional_context += str(row) + "\n"

        try:
            vision_result = await analyze_drawing_with_openai(
                page_images=pdf_result.page_images[:3],  # max 3 pages for cost control
                additional_context=additional_context,
                model=settings.llm_primary_model,
                api_key=settings.openai_api_key,
            )
            spec = _merge_vision_result(spec, vision_result)
        except Exception as e:
            logger.warning("vision_analysis_skipped", error=str(e))
            spec.uncertainty.append(UncertaintyItem(
                field="geometry",
                reason=f"Analiza wizualna nie powiodła się: {e}",
                needs_human_review=True,
            ))

    return spec


def _merge_vision_result(spec: PartSpec, vision: dict) -> PartSpec:
    """Merge VLM analysis result into existing PartSpec (VLM fills gaps)."""
    # Materials
    for mat_data in vision.get("materials", []):
        if not spec.materials:  # only fill if empty
            spec.materials.append(MaterialSpec(
                grade=mat_data.get("grade"),
                form=MaterialForm(mat_data["form"]) if "form" in mat_data else MaterialForm.OTHER,
                diameter_mm=mat_data.get("diameter_mm"),
                thickness_mm=mat_data.get("thickness_mm"),
            ))

    # Geometry
    geom = vision.get("geometry", {})
    wire = geom.get("wire")
    if wire and not spec.geometry.wire:
        spec.geometry.wire = WireGeometry(
            total_length_mm=wire.get("total_length_mm"),
            bend_count=wire.get("bend_count", 0),
            bend_angles_deg=wire.get("bend_angles_deg", []),
        )

    sheet = geom.get("sheet")
    if sheet and not spec.geometry.sheet:
        spec.geometry.sheet = SheetGeometry(
            area_mm2=sheet.get("area_mm2"),
            bend_count=sheet.get("bend_count", 0),
        )

    welds = geom.get("welds", {})
    if welds:
        spec.geometry.welds = WeldSpec(
            spot_weld_count=welds.get("spot_weld_count", spec.geometry.welds.spot_weld_count),
            linear_weld_length_mm=welds.get("linear_weld_length_mm", spec.geometry.welds.linear_weld_length_mm),
            weld_type=WeldingType(welds["weld_type"]) if "weld_type" in welds else spec.geometry.welds.weld_type,
        )

    holes = geom.get("holes", {})
    if holes:
        spec.geometry.holes = HoleSpec(
            count=holes.get("count", 0),
            diameters_mm=holes.get("diameters_mm", []),
            threaded_count=holes.get("threaded_count", 0),
            thread_specs=holes.get("thread_specs", []),
        )

    # Overall dims
    spec.geometry.overall_length_mm = geom.get("overall_length_mm", spec.geometry.overall_length_mm)
    spec.geometry.overall_width_mm = geom.get("overall_width_mm", spec.geometry.overall_width_mm)
    spec.geometry.weight_kg = geom.get("weight_kg", spec.geometry.weight_kg)

    # Process requirements
    proc = vision.get("process_requirements", {})
    if proc:
        if "welding" in proc:
            try:
                spec.process_requirements.welding = WeldingType(proc["welding"])
            except ValueError:
                pass
        if "surface_finish" in proc:
            try:
                spec.process_requirements.surface_finish = SurfaceFinish(proc["surface_finish"])
            except ValueError:
                pass
        spec.process_requirements.tolerances_notes.extend(proc.get("tolerances_notes", []))

    # BOM
    for bom_item in vision.get("bom", []):
        spec.bom.append(BOMItem(
            component_name=bom_item.get("component_name", ""),
            qty_per_product=bom_item.get("qty_per_product", 1),
        ))

    # Uncertainty from VLM
    for unc in vision.get("uncertainty", []):
        spec.uncertainty.append(UncertaintyItem(
            field=unc.get("field", "unknown"),
            reason=unc.get("reason", ""),
            needs_human_review=unc.get("needs_human_review", True),
        ))

    return spec


def _extract_from_text(text: str, spec: PartSpec) -> None:
    """Extract material/process info from text annotations (heuristic)."""
    text_upper = text.upper()

    # Material grades
    for grade in ["S235", "S355", "DC01", "DC04", "ST37", "ST52", "304", "316"]:
        if grade in text_upper:
            if not any(m.grade == grade for m in spec.materials):
                spec.materials.append(MaterialSpec(grade=grade))

    # Surface finish keywords
    finish_keywords = {
        "CYNK": SurfaceFinish.GALVANIZED,
        "GALWAN": SurfaceFinish.GALVANIZED,
        "MALOWA": SurfaceFinish.PAINTED,
        "PROSZK": SurfaceFinish.POWDER_COATED,
        "RAL": SurfaceFinish.POWDER_COATED,
    }
    for kw, finish in finish_keywords.items():
        if kw in text_upper:
            spec.process_requirements.surface_finish = finish

    # RAL color extraction
    import re
    ral_match = re.search(r"RAL\s*(\d{4})", text_upper)
    if ral_match:
        spec.process_requirements.paint_color_ral = ral_match.group(1)


def _parse_material_string(material_str: str, spec: PartSpec) -> None:
    """Parse a material description string (e.g. from title block)."""
    _extract_from_text(material_str, spec)


def _parse_finish_string(finish_str: str, spec: PartSpec) -> None:
    """Parse a surface finish description string."""
    _extract_from_text(finish_str, spec)
