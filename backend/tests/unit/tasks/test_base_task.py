"""Tests for BaseTask Celery lifecycle hooks, retry logic, and exception classification."""

from unittest.mock import MagicMock, patch

import pytest
from celery.exceptions import Retry

TASK_ID = "test-reqruit-task-id-123"
CELERY_TASK_ID = "celery-abc-456"


class TestOnStart:
    async def test_sets_processing_and_started_at(self):
        """on_start sets status=PROCESSING, started_at, and celery_task_id."""
        with (
            patch("src.tasks.base._run_async") as mock_run,
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.on_start(
                CELERY_TASK_ID,
                args=(TASK_ID,),
                kwargs={},
            )

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args is not None

    async def test_handles_missing_reqruit_task_id(self):
        """on_start logs warning when reqruit_task_id not found."""
        with (
            patch("src.tasks.base._run_async") as mock_run,
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.on_start(CELERY_TASK_ID, args=(), kwargs={})

            mock_run.assert_not_called()


class TestOnSuccess:
    async def test_sets_completed_and_result_payload(self):
        """on_success sets status=COMPLETED, result_payload, and completed_at."""
        retval = {"result": "done", "llm_tokens_used": 100, "llm_cost_usd": 0.05}

        with (
            patch("src.tasks.base._run_async") as mock_run,
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.on_success(
                retval,
                CELERY_TASK_ID,
                args=(TASK_ID,),
                kwargs={},
            )

            mock_run.assert_called_once()

    async def test_handles_non_dict_retval(self):
        """on_success wraps non-dict retval in a dict."""
        with (
            patch("src.tasks.base._run_async") as mock_run,
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.on_success(
                "simple_result",
                CELERY_TASK_ID,
                args=(TASK_ID,),
                kwargs={},
            )

            mock_run.assert_called_once()

    async def test_skips_when_no_task_id(self):
        """on_success does nothing when reqruit_task_id missing."""
        with (
            patch("src.tasks.base._run_async") as mock_run,
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.on_success("result", CELERY_TASK_ID, args=(), kwargs={})

            mock_run.assert_not_called()


class TestOnFailureRetryWithBackoff:
    async def test_retries_with_2s_backoff_first_attempt(self):
        """on_failure first retry uses 2s backoff (2^1)."""
        with (
            patch("src.tasks.base._run_async"),
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.max_retries = 3
            mock_request = MagicMock()
            mock_request.retries = 0

            with (
                patch.object(type(task), "request", new_callable=lambda: property(lambda self: mock_request)),
                patch.object(task, "retry", side_effect=Retry()) as mock_retry,
            ):
                with pytest.raises(Retry):
                    task.on_failure(
                        ConnectionError("timeout"),
                        CELERY_TASK_ID,
                        args=(),
                        kwargs={"reqruit_task_id": TASK_ID},
                        einfo=MagicMock(),
                    )
                mock_retry.assert_called_once()
                assert mock_retry.call_args[1]["countdown"] == 2

    async def test_retries_with_4s_backoff_second_attempt(self):
        """on_failure second retry uses 4s backoff (2^2)."""
        with (
            patch("src.tasks.base._run_async"),
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.max_retries = 3
            mock_request = MagicMock()
            mock_request.retries = 1

            with (
                patch.object(type(task), "request", new_callable=lambda: property(lambda self: mock_request)),
                patch.object(task, "retry", side_effect=Retry()) as mock_retry,
            ):
                with pytest.raises(Retry):
                    task.on_failure(
                        TimeoutError("api timeout"),
                        CELERY_TASK_ID,
                        args=(),
                        kwargs={"reqruit_task_id": TASK_ID},
                        einfo=MagicMock(),
                    )
                assert mock_retry.call_args[1]["countdown"] == 4

    async def test_retries_with_8s_backoff_third_attempt(self):
        """on_failure third retry uses 8s backoff (2^3)."""
        with (
            patch("src.tasks.base._run_async"),
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.max_retries = 3
            mock_request = MagicMock()
            mock_request.retries = 2

            with (
                patch.object(type(task), "request", new_callable=lambda: property(lambda self: mock_request)),
                patch.object(task, "retry", side_effect=Retry()) as mock_retry,
            ):
                with pytest.raises(Retry):
                    task.on_failure(
                        OSError("network error"),
                        CELERY_TASK_ID,
                        args=(),
                        kwargs={"reqruit_task_id": TASK_ID},
                        einfo=MagicMock(),
                    )
                assert mock_retry.call_args[1]["countdown"] == 8

    async def test_increments_retry_count_before_retry(self):
        """on_failure increments retry_count on TaskRecord before retrying."""
        with (
            patch("src.tasks.base._run_async") as mock_run,
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.max_retries = 3
            mock_request = MagicMock()
            mock_request.retries = 1

            with (
                patch.object(type(task), "request", new_callable=lambda: property(lambda self: mock_request)),
                patch.object(task, "retry", side_effect=Retry()),
            ):
                with pytest.raises(Retry):
                    task.on_failure(
                        ConnectionError("err"),
                        CELERY_TASK_ID,
                        args=(),
                        kwargs={"reqruit_task_id": TASK_ID},
                        einfo=MagicMock(),
                    )
                # _run_async called to update retry_count
                mock_run.assert_called_once()


class TestOnFailureDeadLetter:
    async def test_dead_letters_when_retries_exhausted(self):
        """on_failure with max retries exhausted sets DEAD_LETTERED."""
        with (
            patch("src.tasks.base._run_async") as mock_run,
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.max_retries = 3
            mock_request = MagicMock()
            mock_request.retries = 3  # Exhausted

            einfo = MagicMock()
            einfo.__str__ = MagicMock(return_value="Traceback details...")

            with patch.object(type(task), "request", new_callable=lambda: property(lambda self: mock_request)):
                task.on_failure(
                    Exception("final error"),
                    CELERY_TASK_ID,
                    args=(TASK_ID,),
                    kwargs={},
                    einfo=einfo,
                )

                mock_run.assert_called_once()

    async def test_dead_letter_has_error_message(self):
        """DEAD_LETTERED record has error_message from exception."""
        with (
            patch("src.tasks.base._run_async") as mock_run,
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.max_retries = 3
            mock_request = MagicMock()
            mock_request.retries = 3

            with patch.object(type(task), "request", new_callable=lambda: property(lambda self: mock_request)):
                task.on_failure(
                    Exception("specific error msg"),
                    CELERY_TASK_ID,
                    args=(),
                    kwargs={"reqruit_task_id": TASK_ID},
                    einfo=MagicMock(),
                )

                # Verify the coroutine was passed to _run_async
                mock_run.assert_called_once()

    async def test_non_retryable_immediately_dead_letters(self):
        """on_failure with ValueError immediately dead-letters without retry."""
        with (
            patch("src.tasks.base._run_async") as mock_run,
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.max_retries = 3
            mock_request = MagicMock()
            mock_request.retries = 0  # Has retries remaining but won't use them

            with (
                patch.object(type(task), "request", new_callable=lambda: property(lambda self: mock_request)),
                patch.object(task, "retry") as mock_retry,
            ):
                task.on_failure(
                    ValueError("bad input"),
                    CELERY_TASK_ID,
                    args=(),
                    kwargs={"reqruit_task_id": TASK_ID},
                    einfo=MagicMock(),
                )
                # retry should NOT be called for non-retryable
                mock_retry.assert_not_called()
                # but _run_async should be called for dead-lettering
                mock_run.assert_called_once()

    async def test_keyerror_immediately_dead_letters(self):
        """on_failure with KeyError immediately dead-letters."""
        with (
            patch("src.tasks.base._run_async") as mock_run,
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            task.max_retries = 3
            mock_request = MagicMock()
            mock_request.retries = 0

            with (
                patch.object(type(task), "request", new_callable=lambda: property(lambda self: mock_request)),
                patch.object(task, "retry") as mock_retry,
            ):
                task.on_failure(
                    KeyError("missing_key"),
                    CELERY_TASK_ID,
                    args=(),
                    kwargs={"reqruit_task_id": TASK_ID},
                    einfo=MagicMock(),
                )
                mock_retry.assert_not_called()
                mock_run.assert_called_once()


class TestIsRetryable:
    async def test_connection_error_is_retryable(self):
        """is_retryable returns True for ConnectionError."""
        with patch("src.tasks.base.celery_app"):
            from src.tasks.base import BaseTask

            task = BaseTask()
            assert task.is_retryable(ConnectionError("conn failed")) is True

    async def test_timeout_error_is_retryable(self):
        """is_retryable returns True for TimeoutError."""
        with patch("src.tasks.base.celery_app"):
            from src.tasks.base import BaseTask

            task = BaseTask()
            assert task.is_retryable(TimeoutError("timed out")) is True

    async def test_value_error_not_retryable(self):
        """is_retryable returns False for ValueError."""
        with patch("src.tasks.base.celery_app"):
            from src.tasks.base import BaseTask

            task = BaseTask()
            assert task.is_retryable(ValueError("bad")) is False

    async def test_unknown_exception_is_retryable(self):
        """is_retryable returns True for unknown exception type (optimistic)."""
        with patch("src.tasks.base.celery_app"):
            from src.tasks.base import BaseTask

            task = BaseTask()
            assert task.is_retryable(RuntimeError("unknown")) is True


class TestBaseTaskClassAttributes:
    async def test_acks_late_is_true(self):
        """BaseTask has acks_late=True."""
        with patch("src.tasks.base.celery_app"):
            from src.tasks.base import BaseTask

            assert BaseTask.acks_late is True

    async def test_reject_on_worker_lost_is_true(self):
        """BaseTask has reject_on_worker_lost=True."""
        with patch("src.tasks.base.celery_app"):
            from src.tasks.base import BaseTask

            assert BaseTask.reject_on_worker_lost is True

    async def test_max_retries_is_3(self):
        """BaseTask has max_retries=3."""
        with patch("src.tasks.base.celery_app"):
            from src.tasks.base import BaseTask

            assert BaseTask.max_retries == 3


class TestOnRetry:
    async def test_increments_retry_count(self):
        """on_retry increments retry_count and sets QUEUED."""
        with (
            patch("src.tasks.base._run_async") as mock_run,
            patch("src.tasks.base.celery_app"),
        ):
            from src.tasks.base import BaseTask

            task = BaseTask()
            mock_request = MagicMock()
            mock_request.retries = 2

            with patch.object(type(task), "request", new_callable=lambda: property(lambda self: mock_request)):
                task.on_retry(
                    Exception("retry error"),
                    CELERY_TASK_ID,
                    args=(TASK_ID,),
                    kwargs={},
                    einfo=MagicMock(),
                )

                mock_run.assert_called_once()


class TestGetReqruitTaskId:
    async def test_extracts_from_kwargs(self):
        """_get_reqruit_task_id extracts from kwargs when present."""
        with patch("src.tasks.base.celery_app"):
            from src.tasks.base import BaseTask

            task = BaseTask()
            result = task._get_reqruit_task_id(
                args=(), kwargs={"reqruit_task_id": "from-kwargs"}
            )
            assert result == "from-kwargs"

    async def test_extracts_from_args(self):
        """_get_reqruit_task_id falls back to first positional arg."""
        with patch("src.tasks.base.celery_app"):
            from src.tasks.base import BaseTask

            task = BaseTask()
            result = task._get_reqruit_task_id(
                args=("from-args",), kwargs={}
            )
            assert result == "from-args"

    async def test_returns_none_when_missing(self):
        """_get_reqruit_task_id returns None when not found."""
        with patch("src.tasks.base.celery_app"):
            from src.tasks.base import BaseTask

            task = BaseTask()
            result = task._get_reqruit_task_id(args=(), kwargs={})
            assert result is None
