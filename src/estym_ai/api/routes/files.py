"""File upload and processing API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from ...pipeline.file_router import detect_file_type

router = APIRouter()


class FileAnalysisResponse(BaseModel):
    file_id: str = ""
    filename: str
    detected_type: str
    needs_conversion: bool = False
    status: str = "uploaded"


@router.post("/upload", response_model=FileAnalysisResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a CAD/PDF file for analysis."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_type = detect_file_type(file.filename)

    # In production: save to MinIO, create DB record, queue for processing
    return FileAnalysisResponse(
        filename=file.filename,
        detected_type=file_type.value,
        needs_conversion=file_type.value in ("dwg", "sat", "sldprt", "sldasm"),
        status="uploaded",
    )


@router.post("/analyze/{file_id}")
async def analyze_file(file_id: str):
    """Trigger analysis of an uploaded file."""
    # In production: dispatch Celery task for analysis
    return {"file_id": file_id, "status": "analysis_queued"}


@router.get("/{file_id}/spec")
async def get_file_spec(file_id: str):
    """Get the extracted PartSpec for a processed file."""
    return {"file_id": file_id, "spec": "not_implemented_yet"}
