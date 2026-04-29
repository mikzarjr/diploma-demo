from celery import Celery

from core.config import settings

celery_app = Celery(
    "ai_calls_analytics",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.analysis", "tasks.integrations"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    task_time_limit=15 * 60,
    task_soft_time_limit=13 * 60,

    result_expires=60 * 60 * 24,
    result_extended=True,

    broker_connection_retry_on_startup=True,
)
