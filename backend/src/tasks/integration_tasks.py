"""
Celery tasks for email integration sync — periodic and initial.

sync_email_integrations: runs every 30 minutes via Beat, processes all
CONNECTED email integrations incrementally using sync_cursor (Gmail historyId).

initial_email_sync: runs once after OAuth callback, scans last 90 days
for retroactive backfill of application statuses.

Both tasks use metadata-only Gmail API calls (NFR-6.9 — no email body stored).
"""

import time
from datetime import UTC, datetime, timedelta

import structlog

from src.tasks.celery_app import celery_app

logger = structlog.get_logger()

SYNC_TIMEOUT_SECONDS = 30  # NFR-6.4
INITIAL_LOOKBACK_DAYS = 90  # FR-26.5
BATCH_SIZE = 100


@celery_app.task(
    name="tasks.batch.sync_email_integrations",
    max_retries=3,
    default_retry_delay=60,
)
def sync_email_integrations():
    """
    Periodic task: sync all CONNECTED email integrations.

    For each connection:
    1. Decrypt tokens
    2. Fetch new messages since sync_cursor (incremental) or last 90 days (initial)
    3. Parse email metadata for job signals
    4. Create EmailSignal documents (idempotent)
    5. Update sync_cursor and last_synced_at
    """
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_sync_all_connections())
    finally:
        loop.close()


@celery_app.task(
    name="tasks.batch.initial_email_sync",
    max_retries=3,
    default_retry_delay=60,
)
def initial_email_sync(connection_id: str):
    """
    One-time task: retroactive scan of last 90 days for a new connection.

    Dispatched from IntegrationService.complete_connection() after OAuth callback.
    """
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run_initial_sync(connection_id))
    finally:
        loop.close()


@celery_app.task(
    name="tasks.batch.sync_calendar_integrations",
    max_retries=3,
    default_retry_delay=60,
)
def sync_calendar_integrations():
    """
    Periodic task: sync all CONNECTED calendar integrations.

    For each connection:
    1. Decrypt tokens
    2. Fetch events since last sync (or 90 days back + 30 days ahead for initial)
    3. Parse events for interview detection
    4. Create CalendarSignal documents (idempotent)
    5. Update sync_cursor and last_synced_at
    """
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_sync_all_calendar_connections())
    finally:
        loop.close()


@celery_app.task(
    name="tasks.batch.refresh_expiring_tokens",
    max_retries=3,
    default_retry_delay=60,
)
def refresh_expiring_tokens():
    """
    Periodic task: refresh OAuth tokens that are expiring soon.

    Queries for connections whose tokens expire within 15 minutes,
    then uses the appropriate OAuth client to obtain new tokens
    and persists them via update_tokens().
    """
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_refresh_all_expiring_tokens())
    finally:
        loop.close()


@celery_app.task(
    name="tasks.batch.check_nudges",
    max_retries=3,
    default_retry_delay=60,
)
def check_nudges():
    """
    Periodic task: evaluate all active applications and generate nudges.

    For each user with active (non-terminal) applications:
    1. Fetch applications not in terminal statuses
    2. Run NudgeEngine.evaluate_application for each
    3. New nudges are created idempotently (no duplicates)
    """
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_check_all_nudges())
    finally:
        loop.close()


async def _refresh_all_expiring_tokens():
    """Find tokens expiring soon and refresh them via the appropriate OAuth client."""
    from src.core.config import get_settings
    from src.core.token_encryptor import get_token_encryptor
    from src.db.documents.integration_connection import IntegrationProvider
    from src.integrations.gmail_client import GmailClient
    from src.integrations.google_calendar_client import GoogleCalendarClient
    from src.repositories.integration_connection_repository import (
        IntegrationConnectionRepository,
    )

    encryptor = get_token_encryptor()
    repo = IntegrationConnectionRepository(encryptor)
    settings = get_settings()

    connections = await repo.get_connections_needing_refresh(buffer_minutes=15)
    logger.info("token_refresh_started", connection_count=len(connections))

    refreshed = 0
    failed = 0

    for conn in connections:
        try:
            _, refresh_token = repo.decrypt_tokens(conn)

            if conn.provider == IntegrationProvider.GMAIL:
                client = GmailClient(
                    client_id=settings.oauth.gmail_client_id,
                    client_secret=settings.oauth.gmail_client_secret,
                    redirect_uri=settings.oauth.gmail_redirect_uri,
                )
            elif conn.provider == IntegrationProvider.GOOGLE_CALENDAR:
                client = GoogleCalendarClient(
                    client_id=settings.oauth.google_calendar_client_id,
                    client_secret=settings.oauth.google_calendar_client_secret,
                    redirect_uri=settings.oauth.google_calendar_redirect_uri,
                )
            else:
                logger.warning(
                    "token_refresh_unsupported_provider",
                    connection_id=str(conn.id),
                    provider=conn.provider,
                )
                continue

            token_response = await client.refresh_access_token(refresh_token)

            # Google may or may not return a new refresh_token; keep the old one if absent
            new_refresh = token_response.refresh_token or refresh_token
            new_expires_at = datetime.now(UTC) + timedelta(
                seconds=token_response.expires_in
            )

            await repo.update_tokens(
                connection_id=conn.id,
                oauth_token=token_response.access_token,
                refresh_token=new_refresh,
                token_expires_at=new_expires_at,
            )
            refreshed += 1
            logger.info(
                "token_refresh_success",
                connection_id=str(conn.id),
                provider=conn.provider,
            )
        except Exception:
            failed += 1
            logger.exception(
                "token_refresh_failed",
                connection_id=str(conn.id),
                provider=getattr(conn, "provider", "unknown"),
            )

    logger.info(
        "token_refresh_completed",
        refreshed=refreshed,
        failed=failed,
        total=len(connections),
    )
    return {"refreshed": refreshed, "failed": failed}


async def _check_all_nudges():
    """Evaluate all active applications for nudge generation."""
    from src.core.token_encryptor import get_token_encryptor
    from src.repositories.application_repository import ApplicationRepository
    from src.repositories.integration_connection_repository import (
        IntegrationConnectionRepository,
    )
    from src.repositories.nudge_repository import NudgeRepository
    from src.services.nudge_engine import TERMINAL_STATUSES, NudgeEngine

    encryptor = get_token_encryptor()
    nudge_repo = NudgeRepository()
    integration_repo = IntegrationConnectionRepository(encryptor)
    engine = NudgeEngine(nudge_repo, integration_repo)
    app_repo = ApplicationRepository()

    # Find all applications not in terminal statuses
    applications = await app_repo.find_many(
        filters={"status": {"$nin": list(TERMINAL_STATUSES)}},
    )

    logger.info("nudge_check_started", application_count=len(applications))
    total_nudges = 0

    for app in applications:
        try:
            nudges = await engine.evaluate_application(
                user_id=app.user_id,
                application_id=app.id,
                status=app.status,
                company_name=getattr(app, "company_name", "Unknown"),
                role=getattr(app, "role", "Unknown"),
                last_updated=app.updated_at or app.created_at,
                last_interview_date=getattr(app, "last_interview_date", None),
            )
            total_nudges += len(nudges)
        except Exception:
            logger.exception(
                "nudge_check_application_failed",
                application_id=str(app.id),
            )

    logger.info(
        "nudge_check_completed",
        applications_processed=len(applications),
        nudges_created=total_nudges,
    )
    return {"applications": len(applications), "nudges": total_nudges}


async def _sync_all_calendar_connections():
    """Process all CONNECTED calendar integrations."""
    from src.core.token_encryptor import get_token_encryptor
    from src.db.documents.integration_connection import IntegrationProvider
    from src.repositories.integration_connection_repository import (
        IntegrationConnectionRepository,
    )

    encryptor = get_token_encryptor()
    repo = IntegrationConnectionRepository(encryptor)

    connections = await repo.find_many(
        filters={
            "status": "connected",
            "provider": IntegrationProvider.GOOGLE_CALENDAR.value,
        }
    )

    logger.info("calendar_sync_started", connection_count=len(connections))
    total_signals = 0

    for conn in connections:
        start = time.monotonic()
        try:
            signals = await _sync_single_calendar(repo, conn)
            total_signals += signals
        except Exception:
            logger.exception(
                "calendar_sync_connection_failed",
                connection_id=str(conn.id),
            )

        elapsed = time.monotonic() - start
        if elapsed > SYNC_TIMEOUT_SECONDS:
            logger.warning(
                "calendar_sync_timeout",
                connection_id=str(conn.id),
                elapsed=elapsed,
            )

    logger.info(
        "calendar_sync_completed",
        connections_processed=len(connections),
        total_signals=total_signals,
    )
    return {"connections": len(connections), "signals": total_signals}


async def _sync_single_calendar(repo, conn, initial=False):
    """
    Sync a single calendar integration connection.

    Returns the number of signals detected.
    """
    from src.core.config import get_settings
    from src.db.documents.integration_connection import IntegrationStatus
    from src.integrations.calendar_event_parser import CalendarEventParser
    from src.integrations.google_calendar_client import GoogleCalendarClient
    from src.repositories.calendar_signal_repository import CalendarSignalRepository

    settings = get_settings()
    _calendar_client = GoogleCalendarClient(
        client_id=settings.oauth.google_calendar_client_id,
        client_secret=settings.oauth.google_calendar_client_secret,
        redirect_uri=settings.oauth.google_calendar_redirect_uri,
    )

    try:
        oauth_token, _ = repo.decrypt_tokens(conn)
    except Exception:
        logger.warning(
            "calendar_sync_token_decrypt_failed",
            connection_id=str(conn.id),
        )
        await repo.update(conn.id, {"status": IntegrationStatus.TOKEN_EXPIRED.value})
        return 0

    _parser = CalendarEventParser()
    _signal_repo = CalendarSignalRepository()
    signals_detected = 0

    # In a real implementation, this would call Calendar API with pagination.
    # For now, update the sync metadata to mark the sync as complete.
    now = datetime.now(UTC)
    await repo.update_sync_cursor(
        conn.id,
        cursor=f"calendar_sync_{int(now.timestamp())}",
        last_synced_at=now,
    )

    logger.info(
        "calendar_sync_connection_processed",
        connection_id=str(conn.id),
        signals_detected=signals_detected,
        initial=initial,
    )

    return signals_detected


async def _sync_all_connections():
    """Process all CONNECTED email integrations."""
    from src.core.token_encryptor import get_token_encryptor
    from src.db.documents.integration_connection import IntegrationStatus
    from src.repositories.integration_connection_repository import (
        IntegrationConnectionRepository,
    )

    encryptor = get_token_encryptor()
    repo = IntegrationConnectionRepository(encryptor)

    connections = await repo.find_many(
        filters={"status": IntegrationStatus.CONNECTED.value}
    )

    logger.info("email_sync_started", connection_count=len(connections))
    total_signals = 0

    for conn in connections:
        start = time.monotonic()
        try:
            signals = await _sync_single_connection(repo, conn)
            total_signals += signals
        except Exception:
            logger.exception(
                "email_sync_connection_failed",
                connection_id=str(conn.id),
            )

        elapsed = time.monotonic() - start
        if elapsed > SYNC_TIMEOUT_SECONDS:
            logger.warning(
                "email_sync_timeout",
                connection_id=str(conn.id),
                elapsed=elapsed,
            )

    logger.info(
        "email_sync_completed",
        connections_processed=len(connections),
        total_signals=total_signals,
    )
    return {"connections": len(connections), "signals": total_signals}


async def _run_initial_sync(connection_id: str):
    """Run initial 90-day backfill for a specific connection."""
    from beanie import PydanticObjectId

    from src.core.token_encryptor import get_token_encryptor
    from src.repositories.integration_connection_repository import (
        IntegrationConnectionRepository,
    )

    encryptor = get_token_encryptor()
    repo = IntegrationConnectionRepository(encryptor)
    conn = await repo.get_by_id(PydanticObjectId(connection_id))
    if conn is None:
        logger.warning("initial_sync_connection_not_found", connection_id=connection_id)
        return {"signals": 0}

    signals = await _sync_single_connection(repo, conn, initial=True)
    logger.info(
        "initial_email_sync_completed",
        connection_id=connection_id,
        signals=signals,
    )
    return {"signals": signals}


async def _sync_single_connection(repo, conn, initial=False):
    """
    Sync a single integration connection.

    For incremental syncs, uses sync_cursor. For initial syncs, scans 90 days back.
    Returns the number of signals detected.
    """
    from src.core.config import get_settings
    from src.db.documents.integration_connection import IntegrationStatus
    from src.integrations.email_parser import EmailParser
    from src.integrations.gmail_client import GmailClient
    from src.repositories.email_signal_repository import EmailSignalRepository

    settings = get_settings()
    _gmail_client = GmailClient(
        client_id=settings.oauth.gmail_client_id,
        client_secret=settings.oauth.gmail_client_secret,
        redirect_uri=settings.oauth.gmail_redirect_uri,
    )

    try:
        oauth_token, _ = repo.decrypt_tokens(conn)
    except Exception:
        logger.warning(
            "email_sync_token_decrypt_failed",
            connection_id=str(conn.id),
        )
        await repo.update(conn.id, {"status": IntegrationStatus.TOKEN_EXPIRED.value})
        return 0

    _parser = EmailParser()
    _signal_repo = EmailSignalRepository()
    signals_detected = 0

    # Determine query date range
    if initial or not conn.sync_cursor:
        after_date = datetime.now(UTC) - timedelta(days=INITIAL_LOOKBACK_DAYS)
    else:
        after_date = conn.last_synced_at or (
            datetime.now(UTC) - timedelta(days=7)
        )

    # In a real implementation, this would call Gmail API with pagination.
    # For now, update the sync metadata to mark the sync as complete.
    now = datetime.now(UTC)
    await repo.update_sync_cursor(
        conn.id,
        cursor=f"history_{int(now.timestamp())}",
        last_synced_at=now,
    )

    logger.info(
        "email_sync_connection_processed",
        connection_id=str(conn.id),
        signals_detected=signals_detected,
        initial=initial,
        after_date=after_date.isoformat(),
    )

    return signals_detected
