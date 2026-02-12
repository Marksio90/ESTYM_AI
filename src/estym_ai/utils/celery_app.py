"""Celery application configuration for async task processing."""

from __future__ import annotations

from celery import Celery

from ..config.settings import get_settings

settings = get_settings()

app = Celery(
    "estym_ai",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Warsaw",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "estym_ai.tasks.pdf.*": {"queue": "pdf"},
        "estym_ai.tasks.cad.*": {"queue": "cad"},
        "estym_ai.tasks.embeddings.*": {"queue": "gpu"},
    },
    task_default_retry_delay=30,
    task_max_retries=3,
)

app.autodiscover_tasks(["estym_ai.tasks"])
