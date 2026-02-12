"""Application configuration using pydantic-settings."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ERPMode(str, Enum):
    API = "api"
    DATABASE = "database"
    FILE_EXPORT = "file_export"
    DISABLED = "disabled"


class EmailProvider(str, Enum):
    IMAP = "imap"
    MS_GRAPH = "ms_graph"
    GMAIL = "gmail"
    DISABLED = "disabled"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Application ---
    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = True
    app_secret_key: str = "changeme-in-production"
    log_level: str = "INFO"

    # --- LLM Providers ---
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_primary_model: str = "gpt-4o"
    llm_secondary_model: str = "gpt-4o-mini"
    llm_embedding_model: str = "text-embedding-3-large"
    llm_embedding_dimensions: int = 1536

    # --- Database (PostgreSQL + pgvector) ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "estym_ai"
    postgres_user: str = "estym"
    postgres_password: str = "changeme"
    database_url: str = "postgresql+asyncpg://estym:changeme@localhost:5432/estym_ai"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Neo4j ---
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"

    # --- MinIO ---
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_raw: str = "raw-uploads"
    minio_bucket_processed: str = "processed"
    minio_bucket_thumbnails: str = "thumbnails"
    minio_use_ssl: bool = False

    # --- Email ---
    email_provider: EmailProvider = EmailProvider.DISABLED
    imap_host: str = ""
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    ms_graph_client_id: str = ""
    ms_graph_client_secret: str = ""
    ms_graph_tenant_id: str = ""

    # --- ERP Graffiti ---
    graffiti_erp_mode: ERPMode = ERPMode.DISABLED
    graffiti_erp_api_url: str = ""
    graffiti_erp_api_key: str = ""
    graffiti_erp_db_url: str = ""

    # --- Werk24 OCR ---
    werk24_api_key: str = ""

    # --- Cost Calculation ---
    social_overhead_percent: float = 10.0
    default_currency: str = "PLN"

    # --- Paths ---
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3])

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "+psycopg")


@lru_cache
def get_settings() -> Settings:
    return Settings()
