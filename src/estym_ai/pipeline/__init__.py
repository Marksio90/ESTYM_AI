"""CAD/PDF processing pipeline — file routing, parsing, and feature extraction."""

from .dxf_parser import DXFExtractionResult, convert_dwg_to_dxf, parse_dxf
from .file_router import detect_file_type, get_conversion_target, needs_conversion
from .pdf_processor import PDFExtractionResult, process_pdf
from .step_analyzer import STEPExtractionResult, analyze_mesh, analyze_step
from .vision_analyzer import analyze_drawing_with_anthropic, analyze_drawing_with_openai
