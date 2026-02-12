"""File format detection and routing to appropriate parsers."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from ..models.enums import FileType

# Extension → FileType mapping
_EXT_MAP: dict[str, FileType] = {
    ".pdf": FileType.PDF,
    ".dxf": FileType.DXF,
    ".dwg": FileType.DWG,
    ".step": FileType.STEP,
    ".stp": FileType.STEP,
    ".sat": FileType.SAT,
    ".sldprt": FileType.SLDPRT,
    ".sldasm": FileType.SLDASM,
}

# Magic bytes for format verification
_MAGIC_SIGNATURES: dict[bytes, FileType] = {
    b"%PDF": FileType.PDF,
    b"AC10": FileType.DWG,  # DWG magic number prefix
    b"ISO-10303-21": FileType.STEP,
}


def detect_file_type(file_path: str | Path) -> FileType:
    """Detect CAD/drawing file type from extension and magic bytes."""
    path = Path(file_path)

    # Try extension first
    ext = path.suffix.lower()
    if ext in _EXT_MAP:
        return _EXT_MAP[ext]

    # Fallback: check magic bytes
    try:
        with open(path, "rb") as f:
            header = f.read(64)
        for sig, ftype in _MAGIC_SIGNATURES.items():
            if sig in header:
                return ftype
    except (OSError, IOError):
        pass

    return FileType.UNKNOWN


def needs_conversion(file_type: FileType) -> bool:
    """Check if this file type needs conversion before parsing."""
    return file_type in {FileType.DWG, FileType.SAT, FileType.SLDPRT, FileType.SLDASM}


def get_conversion_target(file_type: FileType) -> FileType | None:
    """Return the target format for conversion, or None if no conversion needed."""
    conversion_map = {
        FileType.DWG: FileType.DXF,
        FileType.SAT: FileType.STEP,
        FileType.SLDPRT: FileType.STEP,
        FileType.SLDASM: FileType.STEP,
    }
    return conversion_map.get(file_type)
