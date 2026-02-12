"""DXF file parser using ezdxf — extracts geometry and metadata for steel products."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()

try:
    import ezdxf
    from ezdxf.entities import Arc, Circle, DXFGraphic, Insert, Line, LWPolyline, MText, Polyline, Text
    from ezdxf.math import Vec3

    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False


@dataclass
class DXFExtractionResult:
    """Raw geometric data extracted from a DXF file."""
    # Lines and polylines
    total_line_length_mm: float = 0.0
    line_count: int = 0
    polyline_count: int = 0
    polyline_lengths_mm: list[float] = field(default_factory=list)

    # Arcs and circles (potential bends, holes)
    arc_count: int = 0
    arc_radii_mm: list[float] = field(default_factory=list)
    circle_count: int = 0
    circle_diameters_mm: list[float] = field(default_factory=list)

    # Bends (detected from polyline vertex angles)
    bend_count: int = 0
    bend_angles_deg: list[float] = field(default_factory=list)

    # Text and annotations
    texts: list[str] = field(default_factory=list)
    dimension_values: list[float] = field(default_factory=list)

    # Bounding box
    bbox_min: Optional[tuple[float, float, float]] = None
    bbox_max: Optional[tuple[float, float, float]] = None

    # Layer information
    layers: list[str] = field(default_factory=list)

    # Block references (may indicate repeated parts)
    block_references: list[dict] = field(default_factory=list)

    errors: list[str] = field(default_factory=list)


def _angle_between_segments(p1: tuple, p2: tuple, p3: tuple) -> float:
    """Compute the angle (degrees) at p2 between segments p1-p2 and p2-p3."""
    v1 = (p1[0] - p2[0], p1[1] - p2[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
    mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)
    if mag1 < 1e-9 or mag2 < 1e-9:
        return 0.0
    cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    angle = math.degrees(math.acos(cos_angle))
    return 180.0 - angle  # bend angle = deviation from straight


def _polyline_length(points: list[tuple]) -> float:
    """Compute total length of a polyline from its points."""
    total = 0.0
    for i in range(len(points) - 1):
        dx = points[i + 1][0] - points[i][0]
        dy = points[i + 1][1] - points[i][1]
        dz = 0.0
        if len(points[i]) > 2 and len(points[i + 1]) > 2:
            dz = points[i + 1][2] - points[i][2]
        total += math.sqrt(dx * dx + dy * dy + dz * dz)
    return total


def parse_dxf(file_path: str | Path, bend_threshold_deg: float = 5.0) -> DXFExtractionResult:
    """
    Parse a DXF file and extract geometric features relevant for steel product estimation.

    Args:
        file_path: Path to the DXF file.
        bend_threshold_deg: Minimum angle to consider a vertex as a bend.

    Returns:
        DXFExtractionResult with extracted geometry.
    """
    if not HAS_EZDXF:
        return DXFExtractionResult(errors=["ezdxf not installed"])

    result = DXFExtractionResult()
    path = Path(file_path)

    try:
        doc = ezdxf.readfile(str(path))
    except Exception as e:
        result.errors.append(f"Failed to read DXF: {e}")
        return result

    msp = doc.modelspace()

    # Collect layers
    result.layers = [layer.dxf.name for layer in doc.layers]

    all_points: list[tuple[float, float, float]] = []

    for entity in msp:
        try:
            _process_entity(entity, result, all_points, bend_threshold_deg)
        except Exception as e:
            result.errors.append(f"Error processing entity {entity.dxftype()}: {e}")

    # Process block references
    for entity in msp:
        if isinstance(entity, Insert):
            result.block_references.append({
                "block_name": entity.dxf.name,
                "insert_point": (entity.dxf.insert.x, entity.dxf.insert.y, entity.dxf.insert.z),
                "x_scale": getattr(entity.dxf, "xscale", 1.0),
                "y_scale": getattr(entity.dxf, "yscale", 1.0),
                "rotation": getattr(entity.dxf, "rotation", 0.0),
            })

    # Compute bounding box
    if all_points:
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        zs = [p[2] for p in all_points]
        result.bbox_min = (min(xs), min(ys), min(zs))
        result.bbox_max = (max(xs), max(ys), max(zs))

    # Extract dimension entities
    for entity in msp.query("DIMENSION"):
        try:
            val = entity.dxf.get("actual_measurement", None)
            if val is not None:
                result.dimension_values.append(float(val))
        except Exception:
            pass

    logger.info(
        "dxf_parsed",
        file=str(path.name),
        lines=result.line_count,
        arcs=result.arc_count,
        circles=result.circle_count,
        bends=result.bend_count,
        texts=len(result.texts),
    )

    return result


def _process_entity(
    entity: DXFGraphic,
    result: DXFExtractionResult,
    all_points: list,
    bend_threshold_deg: float,
) -> None:
    """Process a single DXF entity and update the result."""
    etype = entity.dxftype()

    if etype == "LINE":
        start = entity.dxf.start
        end = entity.dxf.end
        length = math.sqrt(
            (end.x - start.x) ** 2 + (end.y - start.y) ** 2 + (end.z - start.z) ** 2
        )
        result.total_line_length_mm += length
        result.line_count += 1
        all_points.append((start.x, start.y, start.z))
        all_points.append((end.x, end.y, end.z))

    elif etype == "LWPOLYLINE":
        points = [(p[0], p[1], 0.0) for p in entity.get_points(format="xy")]
        if entity.closed and len(points) > 1:
            points.append(points[0])

        length = _polyline_length(points)
        result.polyline_lengths_mm.append(length)
        result.total_line_length_mm += length
        result.polyline_count += 1
        all_points.extend(points)

        # Detect bends at vertices
        for i in range(1, len(points) - 1):
            angle = _angle_between_segments(points[i - 1], points[i], points[i + 1])
            if angle > bend_threshold_deg:
                result.bend_count += 1
                result.bend_angles_deg.append(round(angle, 1))

    elif etype == "POLYLINE":
        points = [(v.dxf.location.x, v.dxf.location.y, v.dxf.location.z) for v in entity.vertices]
        if entity.is_closed and len(points) > 1:
            points.append(points[0])

        length = _polyline_length(points)
        result.polyline_lengths_mm.append(length)
        result.total_line_length_mm += length
        result.polyline_count += 1
        all_points.extend(points)

        for i in range(1, len(points) - 1):
            angle = _angle_between_segments(points[i - 1], points[i], points[i + 1])
            if angle > bend_threshold_deg:
                result.bend_count += 1
                result.bend_angles_deg.append(round(angle, 1))

    elif etype == "CIRCLE":
        center = entity.dxf.center
        radius = entity.dxf.radius
        result.circle_count += 1
        result.circle_diameters_mm.append(round(radius * 2, 2))
        all_points.append((center.x, center.y, center.z))

    elif etype == "ARC":
        center = entity.dxf.center
        radius = entity.dxf.radius
        result.arc_count += 1
        result.arc_radii_mm.append(round(radius, 2))
        all_points.append((center.x, center.y, center.z))

    elif etype in ("TEXT", "MTEXT"):
        text_content = ""
        if etype == "TEXT":
            text_content = entity.dxf.text
        elif etype == "MTEXT":
            text_content = entity.text  # plain text content
        if text_content.strip():
            result.texts.append(text_content.strip())


def convert_dwg_to_dxf(dwg_path: str | Path, output_dir: str | Path | None = None) -> Path | None:
    """
    Convert DWG to DXF using ODA File Converter via ezdxf's odafc addon.

    Returns the path to the converted DXF file, or None on failure.
    """
    if not HAS_EZDXF:
        logger.error("ezdxf not installed, cannot convert DWG")
        return None

    try:
        from ezdxf.addons import odafc

        dwg_path = Path(dwg_path)
        if output_dir is None:
            output_dir = dwg_path.parent

        dxf_path = Path(output_dir) / dwg_path.with_suffix(".dxf").name
        odafc.convert(str(dwg_path), str(dxf_path))
        logger.info("dwg_converted", source=str(dwg_path.name), target=str(dxf_path.name))
        return dxf_path

    except ImportError:
        logger.error("ODA File Converter not found — install it from https://www.opendesign.com/guestfiles/oda_file_converter")
        return None
    except Exception as e:
        logger.error("dwg_conversion_failed", error=str(e))
        return None
