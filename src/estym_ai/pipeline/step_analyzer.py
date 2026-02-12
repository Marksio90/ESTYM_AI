"""STEP/STP file analyzer — extracts B-Rep topology and manufacturing features.

Requires PythonOCC (pythonocc-core) installed via conda.
Falls back to trimesh for STL/OBJ mesh analysis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()

# PythonOCC is conda-only, so we handle import gracefully
try:
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepGProp import brepgprop
    from OCP.GeomAbs import (
        GeomAbs_Cone,
        GeomAbs_Cylinder,
        GeomAbs_Plane,
        GeomAbs_Sphere,
        GeomAbs_Torus,
    )
    from OCP.GProp import GProp_GProperties
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer

    HAS_OCC = True
except ImportError:
    HAS_OCC = False

try:
    import trimesh

    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False


@dataclass
class SurfaceInfo:
    """Classified B-Rep surface."""
    surface_type: str  # "planar", "cylindrical", "conical", "spherical", "toroidal", "other"
    area_mm2: float = 0.0
    # Cylindrical specifics
    radius_mm: Optional[float] = None
    # Planar specifics
    normal: Optional[tuple[float, float, float]] = None


@dataclass
class STEPExtractionResult:
    """Result of STEP file analysis."""
    # Global properties
    volume_mm3: float = 0.0
    surface_area_mm2: float = 0.0
    mass_kg: float = 0.0  # estimated with steel density 7850 kg/m³
    center_of_gravity: Optional[tuple[float, float, float]] = None

    # Bounding box
    bbox_min: Optional[tuple[float, float, float]] = None
    bbox_max: Optional[tuple[float, float, float]] = None

    # Topology counts
    face_count: int = 0
    edge_count: int = 0

    # Classified surfaces
    planar_faces: int = 0
    cylindrical_faces: int = 0
    conical_faces: int = 0
    spherical_faces: int = 0
    toroidal_faces: int = 0
    other_faces: int = 0

    surfaces: list[SurfaceInfo] = field(default_factory=list)

    # Feature detection (heuristic)
    detected_holes: list[dict] = field(default_factory=list)  # {diameter_mm, depth_mm}
    detected_bends: int = 0  # from dihedral angle analysis
    detected_weld_zones: list[dict] = field(default_factory=list)  # close-proximity edges

    # Pipe/tube detection
    is_likely_tube: bool = False
    tube_outer_diameter_mm: Optional[float] = None

    # Sheet metal detection
    is_likely_sheet: bool = False
    sheet_thickness_mm: Optional[float] = None

    errors: list[str] = field(default_factory=list)


def analyze_step(file_path: str | Path, density_kg_m3: float = 7850.0) -> STEPExtractionResult:
    """
    Analyze a STEP file: extract topology, classify surfaces, detect manufacturing features.

    Args:
        file_path: Path to the STEP/STP file.
        density_kg_m3: Material density for mass estimation (default: steel 7850 kg/m³).

    Returns:
        STEPExtractionResult with extracted features.
    """
    result = STEPExtractionResult()

    if not HAS_OCC:
        result.errors.append(
            "PythonOCC (pythonocc-core) not installed. Install via: conda install -c conda-forge pythonocc-core"
        )
        return result

    path = Path(file_path)
    if not path.exists():
        result.errors.append(f"File not found: {path}")
        return result

    try:
        reader = STEPControl_Reader()
        status = reader.ReadFile(str(path))
        if status != 1:  # IFSelect_RetDone
            result.errors.append(f"STEP read failed with status {status}")
            return result

        reader.TransferRoots()
        shape = reader.OneShape()

        # Global properties
        props = GProp_GProperties()
        brepgprop.VolumeProperties(shape, props)
        result.volume_mm3 = props.Mass()  # Mass() returns volume when computing VolumeProperties
        result.mass_kg = (result.volume_mm3 / 1e9) * density_kg_m3  # mm³ → m³ → kg

        cog = props.CentreOfMass()
        result.center_of_gravity = (cog.X(), cog.Y(), cog.Z())

        # Surface area
        sprops = GProp_GProperties()
        brepgprop.SurfaceProperties(shape, sprops)
        result.surface_area_mm2 = sprops.Mass()

        # Count and classify faces
        face_explorer = TopExp_Explorer(shape, TopAbs_FACE)
        cylinders: list[float] = []

        while face_explorer.More():
            face = face_explorer.Current()
            result.face_count += 1

            adaptor = BRepAdaptor_Surface(face)
            surf_type = adaptor.GetType()

            # Surface area of this face
            face_props = GProp_GProperties()
            brepgprop.SurfaceProperties(face, face_props)
            face_area = face_props.Mass()

            info = SurfaceInfo(surface_type="other", area_mm2=face_area)

            if surf_type == GeomAbs_Plane:
                result.planar_faces += 1
                info.surface_type = "planar"
                pln = adaptor.Plane()
                n = pln.Axis().Direction()
                info.normal = (n.X(), n.Y(), n.Z())

            elif surf_type == GeomAbs_Cylinder:
                result.cylindrical_faces += 1
                info.surface_type = "cylindrical"
                cyl = adaptor.Cylinder()
                r = cyl.Radius()
                info.radius_mm = r
                cylinders.append(r)

            elif surf_type == GeomAbs_Cone:
                result.conical_faces += 1
                info.surface_type = "conical"

            elif surf_type == GeomAbs_Sphere:
                result.spherical_faces += 1
                info.surface_type = "spherical"

            elif surf_type == GeomAbs_Torus:
                result.toroidal_faces += 1
                info.surface_type = "toroidal"

            else:
                result.other_faces += 1

            result.surfaces.append(info)
            face_explorer.Next()

        # Count edges
        edge_explorer = TopExp_Explorer(shape, TopAbs_EDGE)
        while edge_explorer.More():
            result.edge_count += 1
            edge_explorer.Next()

        # Heuristic: detect holes (small cylindrical faces)
        for surf in result.surfaces:
            if surf.surface_type == "cylindrical" and surf.radius_mm is not None:
                diameter = surf.radius_mm * 2
                if diameter < 50:  # likely a hole, not a tube body
                    result.detected_holes.append({"diameter_mm": round(diameter, 2)})

        # Heuristic: tube detection
        if cylinders:
            max_r = max(cylinders)
            large_cyl_count = sum(1 for r in cylinders if abs(r - max_r) / max_r < 0.05)
            if large_cyl_count >= 2 and result.planar_faces <= 4:
                result.is_likely_tube = True
                result.tube_outer_diameter_mm = round(max_r * 2, 2)

        # Heuristic: sheet metal detection
        if result.planar_faces >= 2 and result.face_count > 0:
            planar_ratio = result.planar_faces / result.face_count
            if planar_ratio > 0.3:
                # Check for thin volume relative to surface area
                if result.surface_area_mm2 > 0 and result.volume_mm3 > 0:
                    estimated_thickness = result.volume_mm3 / (result.surface_area_mm2 / 2)
                    if estimated_thickness < 20:  # less than 20mm thick
                        result.is_likely_sheet = True
                        result.sheet_thickness_mm = round(estimated_thickness, 2)

        logger.info(
            "step_analyzed",
            file=path.name,
            faces=result.face_count,
            edges=result.edge_count,
            volume_mm3=round(result.volume_mm3, 1),
            mass_kg=round(result.mass_kg, 3),
            holes=len(result.detected_holes),
            is_tube=result.is_likely_tube,
            is_sheet=result.is_likely_sheet,
        )

    except Exception as e:
        result.errors.append(f"STEP analysis failed: {e}")
        logger.error("step_analysis_failed", file=str(path.name), error=str(e))

    return result


def analyze_mesh(file_path: str | Path, density_kg_m3: float = 7850.0) -> STEPExtractionResult:
    """
    Analyze a mesh file (STL/OBJ) using trimesh as fallback when PythonOCC is unavailable.

    Less precise than B-Rep analysis but useful for quick estimation.
    """
    result = STEPExtractionResult()

    if not HAS_TRIMESH:
        result.errors.append("trimesh not installed")
        return result

    try:
        mesh = trimesh.load(str(file_path))

        if isinstance(mesh, trimesh.Scene):
            # Combine all geometries in scene
            mesh = mesh.dump(concatenate=True)

        if hasattr(mesh, "volume"):
            result.volume_mm3 = mesh.volume
            result.mass_kg = (result.volume_mm3 / 1e9) * density_kg_m3

        if hasattr(mesh, "area"):
            result.surface_area_mm2 = mesh.area

        if hasattr(mesh, "bounds"):
            result.bbox_min = tuple(mesh.bounds[0])
            result.bbox_max = tuple(mesh.bounds[1])

        if hasattr(mesh, "faces"):
            result.face_count = len(mesh.faces)

        if hasattr(mesh, "center_mass"):
            result.center_of_gravity = tuple(mesh.center_mass)

        logger.info(
            "mesh_analyzed",
            file=Path(file_path).name,
            faces=result.face_count,
            volume=round(result.volume_mm3, 1),
        )

    except Exception as e:
        result.errors.append(f"Mesh analysis failed: {e}")

    return result
