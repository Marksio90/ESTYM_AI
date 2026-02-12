"""PDF processing pipeline — renders pages, extracts text/tables, prepares for vision analysis."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()

try:
    import fitz  # PyMuPDF

    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pdfplumber

    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@dataclass
class ExtractedTable:
    """A table extracted from a PDF page."""
    page_number: int
    rows: list[list[str]] = field(default_factory=list)
    header: list[str] = field(default_factory=list)
    bbox: Optional[tuple[float, float, float, float]] = None


@dataclass
class PDFExtractionResult:
    """Complete extraction result from a PDF drawing."""
    page_count: int = 0

    # Rendered page images (as PNG bytes)
    page_images: list[bytes] = field(default_factory=list)
    page_image_paths: list[str] = field(default_factory=list)

    # Text content
    full_text: str = ""
    page_texts: list[str] = field(default_factory=list)

    # Tables (BOM, title block, etc.)
    tables: list[ExtractedTable] = field(default_factory=list)

    # Title block fields (heuristic extraction)
    title_block: dict[str, str] = field(default_factory=dict)

    # Drawing metadata
    has_vector_content: bool = False
    embedded_fonts: list[str] = field(default_factory=list)

    errors: list[str] = field(default_factory=list)


def render_pdf_pages(
    file_path: str | Path,
    dpi: int = 300,
    output_dir: str | Path | None = None,
) -> list[bytes]:
    """
    Render all pages of a PDF as PNG images at specified DPI.

    Args:
        file_path: Path to the PDF file.
        dpi: Resolution for rendering (300 DPI recommended for OCR/vision).
        output_dir: If provided, also saves PNG files to this directory.

    Returns:
        List of PNG image bytes (one per page).
    """
    if not HAS_PYMUPDF:
        logger.error("PyMuPDF not installed")
        return []

    images: list[bytes] = []
    path = Path(file_path)
    zoom = dpi / 72.0  # PDF default is 72 DPI
    matrix = fitz.Matrix(zoom, zoom)

    try:
        doc = fitz.open(str(path))
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=matrix)
            png_bytes = pix.tobytes("png")
            images.append(png_bytes)

            if output_dir:
                out_path = Path(output_dir) / f"{path.stem}_page_{page_num + 1}.png"
                pix.save(str(out_path))

        doc.close()
        logger.info("pdf_rendered", file=path.name, pages=len(images), dpi=dpi)
    except Exception as e:
        logger.error("pdf_render_failed", file=path.name, error=str(e))

    return images


def extract_text_pymupdf(file_path: str | Path) -> tuple[str, list[str]]:
    """Extract text from PDF using PyMuPDF (fast, handles embedded text well)."""
    if not HAS_PYMUPDF:
        return "", []

    path = Path(file_path)
    page_texts: list[str] = []

    try:
        doc = fitz.open(str(path))
        for page in doc:
            text = page.get_text("text")
            page_texts.append(text)
        doc.close()
    except Exception as e:
        logger.error("text_extraction_failed", file=path.name, error=str(e))

    full_text = "\n\n".join(page_texts)
    return full_text, page_texts


def extract_tables_pdfplumber(file_path: str | Path) -> list[ExtractedTable]:
    """Extract tables from PDF using pdfplumber (best for BOM tables and title blocks)."""
    if not HAS_PDFPLUMBER:
        return []

    tables: list[ExtractedTable] = []
    path = Path(file_path)

    try:
        with pdfplumber.open(str(path)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                for raw_table in page_tables:
                    if not raw_table or len(raw_table) < 2:
                        continue

                    # Clean cells
                    cleaned = []
                    for row in raw_table:
                        cleaned.append([cell.strip() if cell else "" for cell in row])

                    extracted = ExtractedTable(
                        page_number=page_num + 1,
                        header=cleaned[0] if cleaned else [],
                        rows=cleaned[1:] if len(cleaned) > 1 else [],
                    )
                    tables.append(extracted)

        logger.info("tables_extracted", file=path.name, table_count=len(tables))
    except Exception as e:
        logger.error("table_extraction_failed", file=path.name, error=str(e))

    return tables


def check_vector_content(file_path: str | Path) -> bool:
    """Check if PDF contains vector drawings (not just raster images)."""
    if not HAS_PYMUPDF:
        return False

    try:
        doc = fitz.open(str(Path(file_path)))
        for page in doc:
            # Check for drawing operators in content stream
            drawings = page.get_drawings()
            if drawings:
                doc.close()
                return True
        doc.close()
    except Exception:
        pass

    return False


def extract_title_block(tables: list[ExtractedTable], page_texts: list[str]) -> dict[str, str]:
    """
    Attempt to extract title block information from the last page / bottom-right table.

    Common fields: material, surface finish, drawing number, revision, scale, weight.
    """
    title_block: dict[str, str] = {}

    # Heuristic: title block is usually in the last/largest table on the last page
    # or in text near bottom-right of the drawing
    keywords = {
        "materiał": "material",
        "material": "material",
        "werkstoff": "material",
        "powłoka": "surface_finish",
        "surface": "surface_finish",
        "oberfläche": "surface_finish",
        "skala": "scale",
        "scale": "scale",
        "maßstab": "scale",
        "masa": "weight",
        "weight": "weight",
        "gewicht": "weight",
        "nr rys": "drawing_number",
        "drawing": "drawing_number",
        "zeichnung": "drawing_number",
        "rewizja": "revision",
        "revision": "revision",
        "rev": "revision",
        "tolerancja": "tolerance",
        "tolerance": "tolerance",
        "ilość": "quantity",
        "qty": "quantity",
        "menge": "quantity",
    }

    for table in tables:
        for row in [table.header] + table.rows:
            for i, cell in enumerate(row):
                cell_lower = cell.lower().strip()
                for keyword, field_name in keywords.items():
                    if keyword in cell_lower and i + 1 < len(row):
                        value = row[i + 1].strip()
                        if value and field_name not in title_block:
                            title_block[field_name] = value

    # Also search in page texts
    for text in page_texts:
        for line in text.split("\n"):
            line_lower = line.lower().strip()
            for keyword, field_name in keywords.items():
                if keyword in line_lower and field_name not in title_block:
                    # Try to extract value after the keyword
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        title_block[field_name] = parts[1].strip()

    return title_block


def process_pdf(file_path: str | Path, output_dir: str | Path | None = None) -> PDFExtractionResult:
    """
    Full PDF processing pipeline: render + text extraction + table extraction + title block.

    Args:
        file_path: Path to the PDF file.
        output_dir: Optional directory to save rendered page images.

    Returns:
        PDFExtractionResult with all extracted data.
    """
    result = PDFExtractionResult()
    path = Path(file_path)

    if not path.exists():
        result.errors.append(f"File not found: {path}")
        return result

    # Render pages as images (for vision model analysis)
    result.page_images = render_pdf_pages(path, dpi=300, output_dir=output_dir)
    result.page_count = len(result.page_images)

    # Extract text
    result.full_text, result.page_texts = extract_text_pymupdf(path)

    # Extract tables (BOM, title block)
    result.tables = extract_tables_pdfplumber(path)

    # Check for vector content
    result.has_vector_content = check_vector_content(path)

    # Extract title block
    result.title_block = extract_title_block(result.tables, result.page_texts)

    # Get font info
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(str(path))
            fonts = set()
            for page in doc:
                for font in page.get_fonts():
                    if font[3]:  # font name
                        fonts.add(font[3])
            result.embedded_fonts = sorted(fonts)
            doc.close()
        except Exception:
            pass

    logger.info(
        "pdf_processed",
        file=path.name,
        pages=result.page_count,
        text_length=len(result.full_text),
        tables=len(result.tables),
        has_vectors=result.has_vector_content,
        title_block_fields=len(result.title_block),
    )

    return result
