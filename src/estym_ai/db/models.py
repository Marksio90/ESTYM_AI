"""SQLAlchemy ORM models for PostgreSQL + pgvector."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

try:
    from pgvector.sqlalchemy import Vector

    HAS_PGVECTOR = True
except ImportError:
    # Fallback: use JSON for vector storage if pgvector not available
    Vector = lambda dim: JSON
    HAS_PGVECTOR = False


class Base(DeclarativeBase):
    pass


class InquiryCaseDB(Base):
    """Persistent inquiry case record."""

    __tablename__ = "inquiry_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="new")
    received_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Customer
    customer_name: Mapped[str] = mapped_column(String(200), default="")
    customer_email: Mapped[str] = mapped_column(String(200), default="")
    customer_account_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Email
    email_subject: Mapped[str] = mapped_column(String(500), default="")
    email_body_summary: Mapped[str] = mapped_column(Text, default="")

    # Classification
    product_family: Mapped[str] = mapped_column(String(30), default="unknown")
    risk_level: Mapped[str] = mapped_column(String(10), default="medium")
    requested_qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # JSON fields for flexible data
    files_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    missing_info_questions: Mapped[list] = mapped_column(JSON, default=list)
    target_finish: Mapped[list] = mapped_column(JSON, default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    parts: Mapped[list["PartDB"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    quotes: Mapped[list["QuoteDB"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class PartDB(Base):
    """Persistent part specification with embeddings for similarity search."""

    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    case_id: Mapped[str] = mapped_column(String(50), ForeignKey("inquiry_cases.case_id"))
    part_name: Mapped[str] = mapped_column(String(300), default="")

    # Full PartSpec as JSON (source of truth)
    spec_json: Mapped[dict] = mapped_column(JSON, default=dict)

    # Key searchable fields (denormalized for SQL WHERE)
    material_grade: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    material_form: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    thickness_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    diameter_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    surface_finish: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    bend_count: Mapped[int] = mapped_column(Integer, default=0)
    weld_point_count: Mapped[int] = mapped_column(Integer, default=0)
    weld_length_mm: Mapped[float] = mapped_column(Float, default=0.0)
    hole_count: Mapped[int] = mapped_column(Integer, default=0)

    # Cluster membership
    cluster_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    cluster_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Vector embeddings for similarity search (pgvector)
    feature_embedding: Mapped[Optional[list]] = mapped_column(Vector(64), nullable=True)
    text_embedding: Mapped[Optional[list]] = mapped_column(Vector(1536), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    case: Mapped["InquiryCaseDB"] = relationship(back_populates="parts")
    tech_plans: Mapped[list["TechPlanDB"]] = relationship(back_populates="part", cascade="all, delete-orphan")


class TechPlanDB(Base):
    """Persistent technology plan."""

    __tablename__ = "tech_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    part_id: Mapped[str] = mapped_column(String(50), ForeignKey("parts.part_id"))
    plan_version: Mapped[int] = mapped_column(Integer, default=1)

    # Full TechPlan as JSON
    plan_json: Mapped[dict] = mapped_column(JSON, default=dict)

    # Summary fields
    batch_size: Mapped[int] = mapped_column(Integer, default=1)
    operation_count: Mapped[int] = mapped_column(Integer, default=0)
    total_setup_sec: Mapped[float] = mapped_column(Float, default=0.0)
    total_cycle_sec: Mapped[float] = mapped_column(Float, default=0.0)
    total_with_overhead_sec: Mapped[float] = mapped_column(Float, default=0.0)

    # ERP export tracking
    erp_exported: Mapped[bool] = mapped_column(Boolean, default=False)
    erp_order_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    part: Mapped["PartDB"] = relationship(back_populates="tech_plans")


class QuoteDB(Base):
    """Persistent cost quote."""

    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    case_id: Mapped[str] = mapped_column(String(50), ForeignKey("inquiry_cases.case_id"))
    plan_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Full Quote as JSON
    quote_json: Mapped[dict] = mapped_column(JSON, default=dict)

    # Summary costs
    material_cost: Mapped[float] = mapped_column(Float, default=0.0)
    labor_cost: Mapped[float] = mapped_column(Float, default=0.0)
    machine_cost: Mapped[float] = mapped_column(Float, default=0.0)
    fixture_cost: Mapped[float] = mapped_column(Float, default=0.0)
    coating_cost: Mapped[float] = mapped_column(Float, default=0.0)
    overhead_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    currency: Mapped[str] = mapped_column(String(5), default="PLN")
    confidence: Mapped[str] = mapped_column(String(10), default="medium")

    # Approval
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    case: Mapped["InquiryCaseDB"] = relationship(back_populates="quotes")


class ProductionFeedback(Base):
    """Actual production data for ML training feedback loop."""

    __tablename__ = "production_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(String(50), index=True)
    part_id: Mapped[str] = mapped_column(String(50), index=True)

    # Actual times from production
    actual_total_time_sec: Mapped[float] = mapped_column(Float, default=0.0)
    actual_setup_time_sec: Mapped[float] = mapped_column(Float, default=0.0)

    # Per-operation actuals
    operation_actuals: Mapped[dict] = mapped_column(JSON, default=dict)

    # Feature vector at time of estimation (for ML training)
    feature_vector: Mapped[list] = mapped_column(JSON, default=list)
    parametric_estimate_sec: Mapped[float] = mapped_column(Float, default=0.0)

    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class MaterialPrice(Base):
    """Material price cache/registry."""

    __tablename__ = "material_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    grade: Mapped[str] = mapped_column(String(30), index=True)
    form: Mapped[str] = mapped_column(String(20))
    price_per_kg: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(5), default="PLN")
    supplier: Mapped[str] = mapped_column(String(200), default="")
    valid_from: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
