"""Email Intake Agent — classifies incoming emails and creates InquiryCase."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import structlog

from ..config.settings import get_settings
from ..models.enums import CaseStatus, FileType, ProductFamily, RiskLevel, SurfaceFinish
from ..models.inquiry import AttachedFile, CustomerInfo, InquiryCase
from ..pipeline.file_router import detect_file_type
from .state import RFQState

logger = structlog.get_logger()

INTAKE_SYSTEM_PROMPT = """\
Jesteś agentem klasyfikacji zapytań ofertowych w firmie produkującej wyroby stalowe.
Analizujesz treść maila i załączniki, aby sklasyfikować zapytanie.

Na podstawie treści maila określ:
1. Typ zapytania: "rfq" (zapytanie ofertowe), "info" (zapytanie informacyjne),
   "order" (zamówienie), "followup" (kontynuacja)
2. Rodzina produktowa: wire, tube, profile, sheet_metal, welded_assembly, mixed, unknown
3. Wykończenie powierzchni: galvanized, painted, powder_coated, raw, unknown
4. Ilość (jeśli podana)
5. Brakujące informacje — lista pytań do klienta/handlowca
6. Poziom ryzyka wyceny: low (standardowy produkt), medium (modyfikacja), high (nowy/złożony)

Odpowiedz WYŁĄCZNIE w formacie JSON:
{
  "query_type": "rfq|info|order|followup",
  "product_family": "wire|tube|...",
  "surface_finish": ["galvanized", ...],
  "quantity": null or number,
  "missing_info": ["pytanie 1", ...],
  "risk_level": "low|medium|high",
  "summary": "krótkie podsumowanie zapytania"
}
"""


async def intake_node(state: RFQState) -> dict:
    """
    LangGraph node: process incoming email and create InquiryCase.

    1. Parse email metadata
    2. Classify with LLM
    3. Detect file types
    4. Create InquiryCase
    """
    settings = get_settings()

    # Extract email info (in production, this comes from email monitoring)
    email_raw = state.email_raw or ""
    case_id = f"RFQ-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    # Classify email with LLM
    classification = await _classify_email(email_raw, settings)

    # Map classification to enums
    family_map = {
        "wire": ProductFamily.WIRE,
        "tube": ProductFamily.TUBE,
        "profile": ProductFamily.PROFILE,
        "sheet_metal": ProductFamily.SHEET_METAL,
        "welded_assembly": ProductFamily.WELDED_ASSEMBLY,
        "mixed": ProductFamily.MIXED,
    }
    risk_map = {"low": RiskLevel.LOW, "medium": RiskLevel.MEDIUM, "high": RiskLevel.HIGH}
    finish_map = {
        "galvanized": SurfaceFinish.GALVANIZED,
        "painted": SurfaceFinish.PAINTED,
        "powder_coated": SurfaceFinish.POWDER_COATED,
        "raw": SurfaceFinish.RAW,
    }

    # Process attached files
    files = []
    for fp_result in state.file_processing_results:
        filename = fp_result.get("filename", "unknown")
        file_type = detect_file_type(filename) if "path" in fp_result else FileType.UNKNOWN
        files.append(AttachedFile(
            file_id=f"F-{uuid.uuid4().hex[:8]}",
            filename=filename,
            detected_type=file_type,
            storage_key=fp_result.get("storage_key", ""),
            file_size_bytes=fp_result.get("size", 0),
        ))

    case = InquiryCase(
        case_id=case_id,
        status=CaseStatus.ANALYZING,
        customer=CustomerInfo(
            name=classification.get("customer_name", "Unknown"),
            email_domain=classification.get("email_domain", ""),
        ),
        email_subject=classification.get("subject", ""),
        email_body_summary=classification.get("summary", ""),
        requested_qty=classification.get("quantity"),
        target_finish=[finish_map.get(f, SurfaceFinish.UNKNOWN) for f in classification.get("surface_finish", ["unknown"])],
        files=files,
        product_family_guess=family_map.get(classification.get("product_family", "unknown"), ProductFamily.UNKNOWN),
        missing_info_questions=classification.get("missing_info", []),
        risk_level=risk_map.get(classification.get("risk_level", "medium"), RiskLevel.MEDIUM),
    )

    logger.info(
        "intake_complete",
        case_id=case_id,
        family=case.product_family_guess.value,
        files=len(files),
        risk=case.risk_level.value,
    )

    return {
        "case": case,
        "current_step": "file_processing",
        "messages": [{"agent": "intake", "content": f"Sprawa {case_id} utworzona. Rodzina: {case.product_family_guess.value}"}],
    }


async def _classify_email(email_raw: str, settings) -> dict:
    """Classify email using LLM (GPT-4o-mini for cost efficiency)."""
    if not email_raw:
        return {
            "query_type": "rfq",
            "product_family": "unknown",
            "surface_finish": ["unknown"],
            "quantity": None,
            "missing_info": [],
            "risk_level": "medium",
            "summary": "Brak treści maila",
        }

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.llm_secondary_model,
            messages=[
                {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
                {"role": "user", "content": email_raw},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1024,
        )
        return json.loads(response.choices[0].message.content)

    except Exception as e:
        logger.error("email_classification_failed", error=str(e))
        return {
            "query_type": "rfq",
            "product_family": "unknown",
            "surface_finish": ["unknown"],
            "quantity": None,
            "missing_info": ["Nie udało się sklasyfikować maila automatycznie"],
            "risk_level": "high",
            "summary": f"Błąd klasyfikacji: {e}",
        }
