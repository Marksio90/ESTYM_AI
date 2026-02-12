"""Data access repository — CRUD operations with vector similarity search."""

from __future__ import annotations

from typing import Optional

import numpy as np
import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.part_spec import PartSpec
from ..models.quote import Quote, SimilarCaseReference
from .models import InquiryCaseDB, PartDB, ProductionFeedback, QuoteDB, TechPlanDB

logger = structlog.get_logger()


class CaseRepository:
    """Repository for inquiry case operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_case(self, case_data: dict) -> InquiryCaseDB:
        db_case = InquiryCaseDB(**case_data)
        self.session.add(db_case)
        await self.session.flush()
        return db_case

    async def get_case(self, case_id: str) -> Optional[InquiryCaseDB]:
        result = await self.session.execute(
            select(InquiryCaseDB).where(InquiryCaseDB.case_id == case_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, case_id: str, status: str) -> None:
        case = await self.get_case(case_id)
        if case:
            case.status = status


class PartRepository:
    """Repository for part operations with vector similarity search."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_part(self, spec: PartSpec, case_id: str, feature_embedding: list | None = None, text_embedding: list | None = None) -> PartDB:
        """Save a PartSpec to the database with embeddings."""
        g = spec.geometry

        db_part = PartDB(
            part_id=spec.part_id,
            case_id=case_id,
            part_name=spec.part_name,
            spec_json=spec.model_dump(),
            material_grade=spec.materials[0].grade if spec.materials else None,
            material_form=spec.materials[0].form.value if spec.materials else None,
            thickness_mm=spec.materials[0].thickness_mm if spec.materials else None,
            diameter_mm=spec.materials[0].diameter_mm if spec.materials else None,
            weight_kg=g.weight_kg,
            surface_finish=spec.process_requirements.surface_finish.value,
            bend_count=(
                (g.wire.bend_count if g.wire else 0)
                + (g.sheet.bend_count if g.sheet else 0)
                + (g.tube.bend_count if g.tube else 0)
            ),
            weld_point_count=g.welds.spot_weld_count,
            weld_length_mm=g.welds.linear_weld_length_mm,
            hole_count=g.holes.count,
            feature_embedding=feature_embedding,
            text_embedding=text_embedding,
        )

        self.session.add(db_part)
        await self.session.flush()
        return db_part

    async def find_similar_by_features(
        self,
        query_embedding: list[float],
        limit: int = 10,
        material_form: str | None = None,
        thickness_range: tuple[float, float] | None = None,
    ) -> list[PartDB]:
        """
        Find similar parts using pgvector cosine similarity with optional SQL filters.

        This is the hybrid query: vector similarity + structured filters.
        """
        # Build query with pgvector cosine distance operator <=>
        query = select(PartDB).where(PartDB.feature_embedding.isnot(None))

        if material_form:
            query = query.where(PartDB.material_form == material_form)

        if thickness_range:
            query = query.where(
                PartDB.thickness_mm.between(thickness_range[0], thickness_range[1])
            )

        # Order by cosine distance (pgvector <=> operator)
        query = query.order_by(
            PartDB.feature_embedding.cosine_distance(query_embedding)
        ).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def find_similar_by_text(
        self,
        query_embedding: list[float],
        limit: int = 10,
    ) -> list[PartDB]:
        """Find similar parts using text embedding similarity."""
        query = (
            select(PartDB)
            .where(PartDB.text_embedding.isnot(None))
            .order_by(PartDB.text_embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())


class QuoteRepository:
    """Repository for quote operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_quote(self, quote: Quote) -> QuoteDB:
        db_quote = QuoteDB(
            quote_id=quote.quote_id,
            case_id=quote.case_id,
            plan_id=quote.plan_id,
            quote_json=quote.model_dump(mode="json"),
            material_cost=quote.material_cost,
            labor_cost=quote.labor_cost,
            machine_cost=quote.machine_cost,
            fixture_cost=quote.fixture_cost,
            coating_cost=quote.coating_cost,
            overhead_cost=quote.overhead_cost,
            total_cost=quote.total_cost,
            unit_cost=quote.unit_cost,
            quantity=quote.quantity,
            currency=quote.currency,
            confidence=quote.confidence.value,
        )
        self.session.add(db_quote)
        await self.session.flush()
        return db_quote

    async def get_historical_quotes_for_part(
        self,
        part_id: str,
        limit: int = 5,
    ) -> list[QuoteDB]:
        result = await self.session.execute(
            select(QuoteDB)
            .where(QuoteDB.case_id == part_id)
            .order_by(QuoteDB.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class FeedbackRepository:
    """Repository for production feedback (ML training data)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_feedback(self, feedback_data: dict) -> ProductionFeedback:
        fb = ProductionFeedback(**feedback_data)
        self.session.add(fb)
        await self.session.flush()
        return fb

    async def get_training_data(self, limit: int = 10000) -> list[ProductionFeedback]:
        result = await self.session.execute(
            select(ProductionFeedback)
            .order_by(ProductionFeedback.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
