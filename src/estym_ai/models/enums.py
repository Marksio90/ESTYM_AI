"""Shared enumerations for the ESTYM_AI platform."""

from __future__ import annotations

from enum import Enum


class MaterialForm(str, Enum):
    """Physical form of the raw material."""
    WIRE = "wire"
    TUBE = "tube"
    PROFILE = "profile"
    SHEET = "sheet"
    BAR = "bar"
    FLATBAR = "flatbar"
    ANGLE = "angle"
    OTHER = "other"


class SurfaceFinish(str, Enum):
    """Required surface finish / coating."""
    GALVANIZED = "galvanized"
    PAINTED = "painted"
    POWDER_COATED = "powder_coated"
    RAW = "raw"
    OUTSOURCED = "outsourced"
    UNKNOWN = "unknown"


class WeldingType(str, Enum):
    """Welding process type."""
    NONE = "none"
    MIG = "MIG"
    TIG = "TIG"
    SPOT = "spot"
    ROBOTIC = "robotic"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ProductFamily(str, Enum):
    """High-level product family classification."""
    WIRE = "wire"
    TUBE = "tube"
    PROFILE = "profile"
    SHEET_METAL = "sheet_metal"
    WELDED_ASSEMBLY = "welded_assembly"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class FileType(str, Enum):
    """Detected CAD/drawing file type."""
    PDF = "pdf"
    DXF = "dxf"
    DWG = "dwg"
    STEP = "step"
    SAT = "sat"
    SLDPRT = "sldprt"
    SLDASM = "sldasm"
    UNKNOWN = "unknown"


class ConversionStatus(str, Enum):
    PENDING = "pending"
    OK = "ok"
    FAILED = "failed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PrecedenceRelation(str, Enum):
    """Relation type in PSI precedence graph."""
    MUST_FINISH_BEFORE = "must_finish_before"
    CAN_PARALLELIZE = "can_parallelize"


class CaseStatus(str, Enum):
    """Lifecycle status of an inquiry case."""
    NEW = "new"
    ANALYZING = "analyzing"
    AWAITING_INFO = "awaiting_info"
    CALCULATED = "calculated"
    REVIEW = "review"
    APPROVED = "approved"
    EXPORTED_TO_ERP = "exported_to_erp"
    REJECTED = "rejected"


class OperationType(str, Enum):
    """Standard manufacturing operation types."""
    CUTTING = "cutting"
    WIRE_BENDING = "wire_bending"
    SHEET_BENDING = "sheet_bending"
    TUBE_BENDING = "tube_bending"
    SPOT_WELDING = "spot_welding"
    MIG_WELDING = "mig_welding"
    TIG_WELDING = "tig_welding"
    ROBOTIC_WELDING = "robotic_welding"
    GRINDING = "grinding"
    DRILLING = "drilling"
    THREADING = "threading"
    DEBURRING = "deburring"
    GALVANIZING = "galvanizing"
    POWDER_COATING = "powder_coating"
    PAINTING = "painting"
    ASSEMBLY = "assembly"
    QA_INSPECTION = "qa_inspection"
    PACKAGING = "packaging"
    DEGREASING = "degreasing"
    FIXTURE_SETUP = "fixture_setup"
