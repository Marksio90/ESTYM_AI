"""Embedding generation for product similarity search.

Three embedding types:
1. Feature embedding — composite vector from PartSpec numeric/categorical features
2. Visual embedding — CLIP ViT-L/14 from rendered drawing images
3. Text embedding — text-embedding-3-large from product description
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import structlog

from ..models.enums import MaterialForm, SurfaceFinish, WeldingType
from ..models.part_spec import PartSpec

logger = structlog.get_logger()

# Feature embedding dimensionality
FEATURE_EMBEDDING_DIM = 64


def generate_feature_embedding(spec: PartSpec) -> np.ndarray:
    """
    Generate a composite feature embedding from PartSpec.

    Encodes: material type, dimensions, operation codes, complexity metrics.
    ~64 dimensions, normalized to unit length.
    """
    features = []

    # --- Material type (one-hot, 8 dims) ---
    mat_forms = list(MaterialForm)
    mat_one_hot = [0.0] * len(mat_forms)
    if spec.materials:
        for m in spec.materials:
            idx = mat_forms.index(m.form) if m.form in mat_forms else len(mat_forms) - 1
            mat_one_hot[idx] = 1.0
    features.extend(mat_one_hot)

    # --- Dimensions (normalized, 8 dims) ---
    thickness = 0.0
    diameter = 0.0
    if spec.materials:
        m = spec.materials[0]
        thickness = (m.thickness_mm or 0.0) / 20.0  # normalize to ~[0,1]
        diameter = (m.diameter_mm or 0.0) / 100.0

    features.extend([
        thickness,
        diameter,
        (spec.geometry.overall_length_mm or 0) / 2000.0,
        (spec.geometry.overall_width_mm or 0) / 1000.0,
        (spec.geometry.overall_height_mm or 0) / 500.0,
        (spec.geometry.weight_kg or 0) / 50.0,
        (spec.geometry.surface_area_m2 or 0) / 5.0,
        0.0,  # padding
    ])

    # --- Operation codes (multi-hot, 10 dims) ---
    op_features = [0.0] * 10
    g = spec.geometry
    if g.wire and g.wire.bend_count > 0:
        op_features[0] = 1.0
    if g.sheet and g.sheet.bend_count > 0:
        op_features[1] = 1.0
    if g.tube and g.tube.bend_count > 0:
        op_features[2] = 1.0
    if g.welds.spot_weld_count > 0:
        op_features[3] = 1.0
    if g.welds.linear_weld_length_mm > 0:
        op_features[4] = 1.0
    if g.holes.count > 0:
        op_features[5] = 1.0
    if g.holes.threaded_count > 0:
        op_features[6] = 1.0
    if spec.process_requirements.surface_finish == SurfaceFinish.GALVANIZED:
        op_features[7] = 1.0
    if spec.process_requirements.surface_finish in (SurfaceFinish.PAINTED, SurfaceFinish.POWDER_COATED):
        op_features[8] = 1.0
    features.extend(op_features)

    # --- Complexity metrics (10 dims) ---
    total_bends = (
        (g.wire.bend_count if g.wire else 0)
        + (g.sheet.bend_count if g.sheet else 0)
        + (g.tube.bend_count if g.tube else 0)
    )
    features.extend([
        total_bends / 20.0,
        g.welds.spot_weld_count / 100.0,
        g.welds.linear_weld_length_mm / 5000.0,
        g.holes.count / 50.0,
        g.holes.threaded_count / 20.0,
        len(spec.bom) / 20.0,
        len(spec.materials) / 5.0,
        spec.quantity / 1000.0,
        len(spec.uncertainty) / 10.0,  # proxy for complexity
        0.0,  # padding
    ])

    # --- Surface finish (one-hot, 6 dims) ---
    finishes = list(SurfaceFinish)
    finish_one_hot = [0.0] * len(finishes)
    idx = finishes.index(spec.process_requirements.surface_finish) if spec.process_requirements.surface_finish in finishes else 0
    finish_one_hot[idx] = 1.0
    features.extend(finish_one_hot)

    # --- Welding type (one-hot, 7 dims) ---
    weld_types = list(WeldingType)
    weld_one_hot = [0.0] * len(weld_types)
    wt = spec.geometry.welds.weld_type
    if wt in weld_types:
        weld_one_hot[weld_types.index(wt)] = 1.0
    features.extend(weld_one_hot)

    # Pad/trim to fixed size
    vec = np.array(features[:FEATURE_EMBEDDING_DIM], dtype=np.float32)
    if len(vec) < FEATURE_EMBEDDING_DIM:
        vec = np.pad(vec, (0, FEATURE_EMBEDDING_DIM - len(vec)))

    # L2 normalize
    norm = np.linalg.norm(vec)
    if norm > 1e-8:
        vec = vec / norm

    return vec


async def generate_text_embedding(
    spec: PartSpec,
    api_key: str = "",
    model: str = "text-embedding-3-large",
) -> np.ndarray:
    """
    Generate a text embedding from PartSpec description using OpenAI API.

    Builds a natural-language description of the product and embeds it.
    """
    description = _build_product_description(spec)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        response = await client.embeddings.create(
            input=description,
            model=model,
        )
        return np.array(response.data[0].embedding, dtype=np.float32)

    except Exception as e:
        logger.error("text_embedding_failed", error=str(e))
        return np.zeros(1536, dtype=np.float32)


def _build_product_description(spec: PartSpec) -> str:
    """Build a natural-language description for embedding."""
    parts = [f"Produkt: {spec.part_name}"]

    if spec.materials:
        m = spec.materials[0]
        parts.append(f"Materiał: {m.grade or '?'}, forma: {m.form.value}")
        if m.diameter_mm:
            parts.append(f"Średnica: {m.diameter_mm}mm")
        if m.thickness_mm:
            parts.append(f"Grubość: {m.thickness_mm}mm")

    g = spec.geometry
    if g.wire and g.wire.bend_count > 0:
        parts.append(f"Drut gięty: {g.wire.bend_count} gięć, długość {g.wire.total_length_mm}mm")
    if g.sheet and g.sheet.bend_count > 0:
        parts.append(f"Blacha gięta: {g.sheet.bend_count} gięć")
    if g.welds.spot_weld_count > 0:
        parts.append(f"Zgrzewanie punktowe: {g.welds.spot_weld_count} punktów")
    if g.welds.linear_weld_length_mm > 0:
        parts.append(f"Spawanie {g.welds.weld_type.value}: {g.welds.linear_weld_length_mm}mm")
    if g.holes.count > 0:
        parts.append(f"Otwory: {g.holes.count} szt")
    if g.weight_kg:
        parts.append(f"Masa: {g.weight_kg}kg")

    finish = spec.process_requirements.surface_finish
    if finish != SurfaceFinish.UNKNOWN:
        parts.append(f"Wykończenie: {finish.value}")

    return ". ".join(parts)


def compute_weighted_similarity(
    query_feature: np.ndarray,
    query_text: Optional[np.ndarray],
    db_feature: np.ndarray,
    db_text: Optional[np.ndarray],
    alpha: float = 0.6,  # feature weight
    beta: float = 0.4,  # text weight
) -> float:
    """
    Compute weighted cosine similarity between two products.

    Final_Score = α × cos(feature, feature) + β × cos(text, text)
    """

    def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-8 or norm_b < 1e-8:
            return 0.0
        return float(dot / (norm_a * norm_b))

    feat_sim = cosine_sim(query_feature, db_feature)

    text_sim = 0.0
    if query_text is not None and db_text is not None:
        text_sim = cosine_sim(query_text, db_text)

    if query_text is None or db_text is None:
        return feat_sim

    return alpha * feat_sim + beta * text_sim
