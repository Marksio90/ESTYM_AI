"""Inquiry case model — the top-level container for an RFQ."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .enums import CaseStatus, ConversionStatus, FileType, ProductFamily, RiskLevel, SurfaceFinish


class CustomerInfo(BaseModel):
    """Customer metadata extracted from email / CRM."""
    name: str
    email_domain: str = ""
    account_id: Optional[str] = None
    contact_email: str = ""


class AttachedFile(BaseModel):
    """A single file attached to the inquiry."""
    file_id: str
    filename: str
    detected_type: FileType = FileType.UNKNOWN
    conversion_status: ConversionStatus = ConversionStatus.PENDING
    storage_key: str = ""  # key in MinIO
    preview_urls: list[str] = Field(default_factory=list)
    file_size_bytes: int = 0


class InquiryCase(BaseModel):
    """
    Top-level data contract for a single RFQ / inquiry.

    Created by the Email Intake Agent, enriched by subsequent agents,
    and tracked through its lifecycle via `status`.
    """
    case_id: str
    status: CaseStatus = CaseStatus.NEW
    received_at: datetime = Field(default_factory=datetime.utcnow)
    customer: CustomerInfo
    email_subject: str = ""
    email_body_summary: str = ""
    requested_qty: Optional[int] = None
    target_finish: list[SurfaceFinish] = Field(default_factory=lambda: [SurfaceFinish.UNKNOWN])
    files: list[AttachedFile] = Field(default_factory=list)
    product_family_guess: ProductFamily = ProductFamily.UNKNOWN
    missing_info_questions: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    assigned_estimator: Optional[str] = None
    notes: list[str] = Field(default_factory=list)

    # Traceability
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
