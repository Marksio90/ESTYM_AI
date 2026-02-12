"""Tests for similarity search and embeddings."""

import numpy as np
import pytest

from estym_ai.models.enums import MaterialForm, SurfaceFinish, WeldingType
from estym_ai.models.part_spec import (
    Geometry,
    MaterialSpec,
    PartSpec,
    ProcessRequirements,
    WeldSpec,
    WireGeometry,
)
from estym_ai.similarity.embeddings import (
    FEATURE_EMBEDDING_DIM,
    compute_weighted_similarity,
    generate_feature_embedding,
)


def _make_spec(bend_count: int = 5, form: MaterialForm = MaterialForm.WIRE) -> PartSpec:
    return PartSpec(
        part_id="TEST",
        materials=[MaterialSpec(form=form, diameter_mm=6.0)],
        geometry=Geometry(
            wire=WireGeometry(total_length_mm=800, bend_count=bend_count) if form == MaterialForm.WIRE else None,
        ),
        process_requirements=ProcessRequirements(surface_finish=SurfaceFinish.GALVANIZED),
    )


class TestFeatureEmbedding:
    def test_correct_dimension(self):
        spec = _make_spec()
        emb = generate_feature_embedding(spec)
        assert emb.shape == (FEATURE_EMBEDDING_DIM,)

    def test_normalized(self):
        spec = _make_spec()
        emb = generate_feature_embedding(spec)
        norm = np.linalg.norm(emb)
        assert abs(norm - 1.0) < 1e-5

    def test_similar_specs_close(self):
        spec1 = _make_spec(bend_count=5)
        spec2 = _make_spec(bend_count=6)
        emb1 = generate_feature_embedding(spec1)
        emb2 = generate_feature_embedding(spec2)
        sim = np.dot(emb1, emb2)
        assert sim > 0.9  # very similar products

    def test_different_forms_less_similar(self):
        wire = _make_spec(form=MaterialForm.WIRE)
        sheet = _make_spec(form=MaterialForm.SHEET)
        emb_wire = generate_feature_embedding(wire)
        emb_sheet = generate_feature_embedding(sheet)
        sim = np.dot(emb_wire, emb_sheet)
        assert sim < 0.9  # different product families


class TestWeightedSimilarity:
    def test_identical_vectors(self):
        v = np.random.randn(64).astype(np.float32)
        v /= np.linalg.norm(v)
        sim = compute_weighted_similarity(v, None, v, None)
        assert abs(sim - 1.0) < 1e-5

    def test_with_text_embeddings(self):
        feat = np.random.randn(64).astype(np.float32)
        text = np.random.randn(1536).astype(np.float32)
        sim = compute_weighted_similarity(feat, text, feat, text, alpha=0.6, beta=0.4)
        assert abs(sim - 1.0) < 1e-5  # identical → 1.0
