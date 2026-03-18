"""
Celery application instance with queue routing and serialization config.

This module is standalone — it does NOT import from FastAPI or the API layer.
Celery workers import this module directly via:
    celery -A src.tasks.celery_app worker ...

Two queues are defined:
    - interactive: user-facing tasks requiring faster processing (concurrency=3)
    - batch: background operations like bulk analysis (concurrency=5)

Task routing uses name prefixes:
    - tasks.interactive.* → interactive queue
    - tasks.batch.* → batch queue (also the default fallback)
"""

from celery import Celery
from kombu import Queue

from src.core.config import get_settings

settings = get_settings()
celery_settings = settings.celery

celery_app = Celery("reqruit")

celery_app.conf.update(
    broker_url=celery_settings.broker_url,
    result_backend=celery_settings.result_backend,
    task_acks_late=celery_settings.task_acks_late,
    worker_prefetch_multiplier=celery_settings.worker_prefetch_multiplier,
    task_reject_on_worker_lost=celery_settings.task_reject_on_worker_lost,
    task_track_started=celery_settings.task_track_started,
    task_default_queue=celery_settings.task_default_queue,
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Queue routing: task name prefix determines queue
    task_routes={
        "tasks.interactive.*": {"queue": "interactive"},
        "tasks.batch.*": {"queue": "batch"},
    },
    # Queue definitions
    task_queues=(
        Queue("interactive"),
        Queue("batch"),
    ),
    # Beat schedule — periodic monitoring tasks
    beat_schedule={
        "log-queue-health": {
            "task": "tasks.batch.log_queue_health",
            "schedule": 300.0,  # every 5 minutes
        },
        "aggregate-usage-rollups": {
            "task": "tasks.batch.aggregate_usage_rollups",
            "schedule": 900.0,  # every 15 minutes
        },
        "sync-email-integrations": {
            "task": "tasks.batch.sync_email_integrations",
            "schedule": 1800.0,  # every 30 minutes
        },
        "sync-calendar-integrations": {
            "task": "tasks.batch.sync_calendar_integrations",
            "schedule": 1800.0,  # every 30 minutes
        },
        "refresh-expiring-tokens": {
            "task": "tasks.batch.refresh_expiring_tokens",
            "schedule": 2700.0,  # every 45 minutes
        },
        "check-nudges": {
            "task": "tasks.batch.check_nudges",
            "schedule": 21600.0,  # every 6 hours
        },
        "check-source-health": {
            "task": "tasks.batch.check_source_health",
            "schedule": 300.0,  # every 5 minutes
        },
        "generate-daily-shortlists": {
            "task": "tasks.batch.generate_daily_shortlists",
            "schedule": 86400.0,  # daily (5 AM IST configured via deployment)
        },
        "refresh-external-data": {
            "task": "tasks.batch.refresh_external_data",
            "schedule": 21600.0,  # every 6 hours
        },
    },
    beat_schedule_filename=celery_settings.beat_schedule_filename,
)
