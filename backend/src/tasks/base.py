"""
BaseTask — Celery task base class that synchronizes lifecycle with TaskRecord.

All Celery tasks should use `base=BaseTask` so that TaskRecord is automatically
updated as the task moves through QUEUED → PROCESSING → COMPLETED/DEAD_LETTERED.

The key challenge: Celery workers run synchronously, but our TaskRecordRepository
uses async MongoDB. We solve this by running async updates via asyncio event loops
inside the synchronous Celery callbacks.

Retry semantics
---------------
- Retryable exceptions (ConnectionError, TimeoutError, OSError): retry with
  exponential backoff (2s, 4s, 8s).
- Non-retryable exceptions (ValueError, KeyError, TypeError): dead-letter
  immediately.
- Unknown exceptions: retry (optimistic — max_retries protects against loops).

Worker-lost recovery (NFR-6.23)
-------------------------------
acks_late=True + reject_on_worker_lost=True ensures zero task loss when a worker
process crashes or is killed (OOM, SIGKILL).

Usage
-----
    from src.tasks.celery_app import celery_app
    from src.tasks.base import BaseTask

    @celery_app.task(base=BaseTask, bind=True)
    def my_task(self, reqruit_task_id: str, **kwargs):
        # reqruit_task_id is the TaskRecord.task_id for status tracking
        return {"result": "done"}
"""

import asyncio
from datetime import UTC, datetime

import structlog

from src.tasks.celery_app import celery_app

logger = structlog.get_logger()

RETRYABLE_EXCEPTIONS = (ConnectionError, TimeoutError, OSError)
NON_RETRYABLE_EXCEPTIONS = (ValueError, KeyError, TypeError)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery callback."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=30)
        return loop.run_until_complete(coro)
    except concurrent.futures.TimeoutError:
        logger.error("run_async_timeout", coro=repr(coro))
        return None
    except RuntimeError:
        return asyncio.run(coro)


async def _update_task_record(task_id: str, **kwargs):
    """Update a TaskRecord by task_id with the given fields."""
    from src.repositories.task_record_repository import TaskRecordRepository

    repo = TaskRecordRepository()
    record = await repo.find_by_task_id(task_id)
    if record is None:
        logger.warning("task_record_not_found", task_id=task_id)
        return
    await record.set(kwargs)


class BaseTask(celery_app.Task):
    """
    Celery Task base class that updates TaskRecord on lifecycle transitions.

    Tasks using this base class MUST pass `reqruit_task_id` as the first
    positional argument or as a keyword argument. This is the TaskRecord.task_id
    that links the Celery task to its MongoDB record.
    """

    acks_late = True
    reject_on_worker_lost = True
    max_retries = 3

    def _get_reqruit_task_id(self, args, kwargs):
        """Extract reqruit_task_id from task args or kwargs."""
        if kwargs and "reqruit_task_id" in kwargs:
            return kwargs["reqruit_task_id"]
        if args and len(args) > 0:
            return args[0]
        return None

    def is_retryable(self, exc: Exception) -> bool:
        """
        Determine if an exception is retryable.

        Non-retryable exceptions (code bugs, invalid input) go straight to DLQ.
        Unknown exception types default to retryable — max_retries protects
        against infinite loops.
        """
        return not isinstance(exc, NON_RETRYABLE_EXCEPTIONS)

    def on_start(self, task_id, args, kwargs):
        """Called when the worker starts processing the task."""
        reqruit_task_id = self._get_reqruit_task_id(args, kwargs)
        if reqruit_task_id is None:
            logger.warning("on_start_no_reqruit_task_id", celery_task_id=task_id)
            return

        logger.info(
            "task_started",
            celery_task_id=task_id,
            reqruit_task_id=reqruit_task_id,
        )

        _run_async(
            _update_task_record(
                reqruit_task_id,
                status="processing",
                started_at=datetime.now(UTC),
                celery_task_id=task_id,
            )
        )

    def on_success(self, retval, task_id, args, kwargs):
        """Called when the task completes successfully."""
        reqruit_task_id = self._get_reqruit_task_id(args, kwargs)
        if reqruit_task_id is None:
            return

        now = datetime.now(UTC)
        update_fields = {
            "status": "completed",
            "result_payload": retval if isinstance(retval, dict) else {"result": retval},
            "completed_at": now,
        }

        if isinstance(retval, dict):
            if "llm_tokens_used" in retval:
                update_fields["llm_tokens_used"] = retval["llm_tokens_used"]
            if "llm_cost_usd" in retval:
                update_fields["llm_cost_usd"] = retval["llm_cost_usd"]

        logger.info(
            "task_completed",
            celery_task_id=task_id,
            reqruit_task_id=reqruit_task_id,
        )

        if isinstance(retval, dict) and (
            "llm_tokens_used" in retval or "llm_cost_usd" in retval
        ):
            logger.info(
                "task_cost_recorded",
                reqruit_task_id=reqruit_task_id,
                llm_tokens_used=retval.get("llm_tokens_used"),
                llm_cost_usd=retval.get("llm_cost_usd"),
            )

        _run_async(_update_task_record(reqruit_task_id, **update_fields))

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Called when the task fails.

        If the exception is retryable and retries remain, requeue with
        exponential backoff (2s, 4s, 8s). Otherwise, dead-letter with
        full diagnostic context.
        """
        reqruit_task_id = self._get_reqruit_task_id(args, kwargs)
        if reqruit_task_id is None:
            return

        retries = self.request.retries if self.request else 0
        max_retries = self.max_retries if self.max_retries else 3

        if self.is_retryable(exc) and retries < max_retries:
            delay = 2 ** (retries + 1)
            logger.warning(
                "task_retry_with_backoff",
                celery_task_id=task_id,
                reqruit_task_id=reqruit_task_id,
                retry=retries,
                delay=delay,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            _run_async(
                _update_task_record(
                    reqruit_task_id,
                    status="queued",
                    retry_count=retries + 1,
                )
            )
            raise self.retry(exc=exc, countdown=delay)

        # Dead-letter: retries exhausted or non-retryable
        logger.error(
            "task_dead_lettered",
            celery_task_id=task_id,
            reqruit_task_id=reqruit_task_id,
            error=str(exc),
            retries_exhausted=retries >= max_retries,
            non_retryable=not self.is_retryable(exc),
        )
        _run_async(
            _update_task_record(
                reqruit_task_id,
                status="dead_lettered",
                error_message=str(exc),
                error_traceback=str(einfo) if einfo else None,
                completed_at=datetime.now(UTC),
            )
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when the task is about to be retried."""
        reqruit_task_id = self._get_reqruit_task_id(args, kwargs)
        if reqruit_task_id is None:
            return

        retries = self.request.retries if self.request else 0

        logger.info(
            "task_retrying",
            celery_task_id=task_id,
            reqruit_task_id=reqruit_task_id,
            retry=retries,
        )

        _run_async(
            _update_task_record(
                reqruit_task_id,
                status="queued",
                retry_count=retries + 1,
            )
        )
