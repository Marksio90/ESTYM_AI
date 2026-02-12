"""Vision-based drawing analysis using multimodal LLMs (GPT-4o / Claude)."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Optional

import structlog

from ..models.part_spec import PartSpec

logger = structlog.get_logger()

# System prompt for drawing analysis — instructs the VLM to extract PartSpec fields
DRAWING_ANALYSIS_SYSTEM_PROMPT = """\
Jesteś ekspertem od kosztorysowania wyrobów stalowych. Analizujesz rysunki techniczne
i wyciągasz z nich ustrukturyzowane dane potrzebne do wyceny.

Twoje specjalizacje:
- Wyroby z drutu (gięcie CNC, cięcie)
- Wyroby z rur (gięcie, cięcie, łączenia)
- Wyroby z profili stalowych
- Wyroby z blachy (cięcie, gięcie na prasie krawędziowej, wykrawanie)
- Spawanie (MIG/TIG/punktowe/robotyczne)
- Cynkowanie ogniowe i malowanie proszkowe

Dla każdego rysunku wyciągnij:
1. MATERIAŁY: gatunek stali, forma (drut/rura/profil/blacha/pręt/płaskownik/kątownik),
   wymiary przekroju (średnica, grubość, szerokość, wysokość)
2. GEOMETRIA: długości, liczba gięć, kąty gięć, promienie gięcia,
   liczba i średnice otworów, gwinty, długości spawów, liczba punktów zgrzewanych
3. WYMAGANIA PROCESOWE: typ spawania, powłoka (cynk/farba/proszek), tolerancje, uwagi specjalne
4. BOM: lista komponentów z ilościami na wyrób
5. NIEPEWNOŚCI: pola, których nie jesteś pewien — oznacz je z powodem

Jeśli rysunek jest nieczytelny lub brakuje kluczowych danych, NIE zgaduj —
zamiast tego dodaj do listy uncertainty z wyjaśnieniem.

Odpowiedz WYŁĄCZNIE poprawnym JSON zgodnym ze schematem PartSpec.
"""

PART_SPEC_SCHEMA_HINT = """\
Schemat PartSpec (uproszczony):
{
  "part_name": "string",
  "units": "mm",
  "materials": [{"grade": "S235", "form": "wire|tube|sheet|bar|...", "diameter_mm": ..., "thickness_mm": ...}],
  "geometry": {
    "wire": {"total_length_mm": ..., "bend_count": ..., "bend_angles_deg": [...]},
    "sheet": {"area_mm2": ..., "bend_count": ..., "bend_angles_deg": [...]},
    "tube": {"length_mm": ..., "bend_count": ...},
    "welds": {"spot_weld_count": ..., "linear_weld_length_mm": ..., "weld_type": "MIG|TIG|spot|..."},
    "holes": {"count": ..., "diameters_mm": [...], "threaded_count": ..., "thread_specs": ["M8", ...]},
    "overall_length_mm": ..., "overall_width_mm": ..., "overall_height_mm": ..., "weight_kg": ...
  },
  "process_requirements": {"welding": "MIG", "surface_finish": "galvanized|painted|raw", "tolerances_notes": [...]},
  "bom": [{"component_name": "...", "qty_per_product": 1}],
  "uncertainty": [{"field": "materials[0].grade", "reason": "nieczytelne na rysunku", "needs_human_review": true}]
}
"""


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 data URI for LLM vision APIs."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


async def analyze_drawing_with_openai(
    page_images: list[bytes],
    additional_context: str = "",
    model: str = "gpt-4o",
    api_key: str = "",
) -> dict:
    """
    Analyze drawing page images using OpenAI's vision model.

    Args:
        page_images: List of PNG image bytes (one per page).
        additional_context: Extra context (e.g. extracted text, table data).
        model: OpenAI model ID.
        api_key: OpenAI API key.

    Returns:
        Raw parsed JSON dict (PartSpec-like structure).
    """
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)

    # Build message content with images
    content: list[dict] = []

    for i, img_bytes in enumerate(page_images[:5]):  # max 5 pages
        content.append({
            "type": "image_url",
            "image_url": {
                "url": encode_image_to_base64(img_bytes),
                "detail": "high",
            },
        })

    user_text = f"Przeanalizuj ten rysunek techniczny i wyciągnij dane do wyceny.\n\n{PART_SPEC_SCHEMA_HINT}"
    if additional_context:
        user_text += f"\n\nDodatkowy kontekst (tekst/tabele z rysunku):\n{additional_context}"

    content.insert(0, {"type": "text", "text": user_text})

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": DRAWING_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            response_format={"type": "json_object"},
            max_tokens=4096,
            temperature=0.1,
        )

        raw_text = response.choices[0].message.content
        parsed = json.loads(raw_text)

        logger.info("vision_analysis_complete", model=model, pages=len(page_images))
        return parsed

    except Exception as e:
        logger.error("vision_analysis_failed", model=model, error=str(e))
        return {"error": str(e), "uncertainty": [{"field": "all", "reason": f"Vision analysis failed: {e}"}]}


async def analyze_drawing_with_anthropic(
    page_images: list[bytes],
    additional_context: str = "",
    model: str = "claude-sonnet-4-20250514",
    api_key: str = "",
) -> dict:
    """
    Analyze drawing page images using Anthropic's Claude vision model.

    Args:
        page_images: List of PNG image bytes (one per page).
        additional_context: Extra context (e.g. extracted text, table data).
        model: Anthropic model ID.
        api_key: Anthropic API key.

    Returns:
        Raw parsed JSON dict (PartSpec-like structure).
    """
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key)

    content: list[dict] = []

    for img_bytes in page_images[:5]:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": b64,
            },
        })

    user_text = f"Przeanalizuj ten rysunek techniczny i wyciągnij dane do wyceny.\n\n{PART_SPEC_SCHEMA_HINT}"
    if additional_context:
        user_text += f"\n\nDodatkowy kontekst (tekst/tabele z rysunku):\n{additional_context}"

    content.append({"type": "text", "text": user_text})

    try:
        response = await client.messages.create(
            model=model,
            system=DRAWING_ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
            max_tokens=4096,
            temperature=0.1,
        )

        raw_text = response.content[0].text
        # Try to extract JSON from response
        parsed = _extract_json(raw_text)

        logger.info("vision_analysis_complete", model=model, pages=len(page_images))
        return parsed

    except Exception as e:
        logger.error("vision_analysis_failed", model=model, error=str(e))
        return {"error": str(e), "uncertainty": [{"field": "all", "reason": f"Vision analysis failed: {e}"}]}


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from code block
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return json.loads(text[start:end].strip())

    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return json.loads(text[start:end].strip())

    # Try finding JSON object in text
    brace_start = text.find("{")
    brace_end = text.rfind("}") + 1
    if brace_start >= 0 and brace_end > brace_start:
        return json.loads(text[brace_start:brace_end])

    raise ValueError(f"Could not extract JSON from response: {text[:200]}...")
