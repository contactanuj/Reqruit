"""
Celery tasks for job discovery pipeline — source health checks and shortlist generation.

check_source_health: runs every 5 minutes via Beat, checks each registered
job source and updates DataSourceHealth records.

generate_daily_shortlists: runs daily at 5 AM IST via Beat, generates
curated job shortlists for all users with discovery preferences.
"""

import time

import structlog

from src.tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="tasks.batch.check_source_health",
    max_retries=1,
    default_retry_delay=30,
)
def check_source_health():
    """
    Periodic task: check health of all registered job sources.

    For each source in JOB_SOURCE_REGISTRY:
    1. Instantiate the client
    2. Run health_check()
    3. Record result in DataSourceHealth (upsert)
    4. Open circuit breaker after 3 consecutive failures (NFR-6.22)
    """
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_check_all_sources())
    finally:
        loop.close()


async def _check_all_sources():
    """Check health of all registered job sources."""
    from src.integrations.job_source_clients import JOB_SOURCE_REGISTRY
    from src.repositories.data_source_health_repository import (
        DataSourceHealthRepository,
    )

    repo = DataSourceHealthRepository()
    results = {}

    for source_name, client_cls in JOB_SOURCE_REGISTRY.items():
        start = time.monotonic()
        try:
            client = client_cls()
            healthy = await client.health_check()
            elapsed_ms = (time.monotonic() - start) * 1000
            await repo.record_check(
                source_name=source_name,
                success=healthy,
                response_ms=elapsed_ms,
                error="" if healthy else "Health check returned unhealthy",
            )
            results[source_name] = "healthy" if healthy else "degraded"
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            await repo.record_check(
                source_name=source_name,
                success=False,
                response_ms=elapsed_ms,
                error=str(exc)[:500],
            )
            results[source_name] = "error"
            logger.exception(
                "source_health_check_failed",
                source=source_name,
            )

    logger.info(
        "source_health_check_completed",
        results=results,
    )
    return results


@celery_app.task(
    name="tasks.batch.generate_daily_shortlists",
    max_retries=1,
    default_retry_delay=60,
)
def generate_daily_shortlists():
    """
    Daily task: generate curated job shortlists for all users with preferences.

    Scheduled at 5:00 AM IST via Beat. For each user with discovery_preferences:
    1. Fetch healthy job sources
    2. Query each source for matching jobs
    3. Score and rank jobs against user preferences
    4. Create JobShortlist with top 3-5 matches
    """
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_generate_all_shortlists())
    finally:
        loop.close()


async def _generate_all_shortlists():
    """Generate shortlists for all users with discovery preferences."""
    from datetime import UTC, datetime

    from src.db.documents.job_shortlist import JobShortlist, ShortlistJob
    from src.integrations.job_source_clients import JOB_SOURCE_REGISTRY
    from src.repositories.data_source_health_repository import (
        DataSourceHealthRepository,
    )
    from src.repositories.job_shortlist_repository import JobShortlistRepository
    from src.repositories.profile_repository import ProfileRepository

    profile_repo = ProfileRepository()
    shortlist_repo = JobShortlistRepository()
    health_repo = DataSourceHealthRepository()

    # Get healthy sources
    healthy_sources = await health_repo.get_healthy_sources()
    healthy_names = {s.source_name for s in healthy_sources}

    # Get all profiles with discovery_preferences set
    profiles = await profile_repo.find_many(
        filters={"discovery_preferences": {"$ne": None}},
        limit=1000,
    )

    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    generated = 0
    errors = 0

    for profile in profiles:
        try:
            prefs = profile.discovery_preferences
            if not prefs or not isinstance(prefs, dict):
                continue

            # Check if shortlist already exists for today
            existing = await shortlist_repo.get_by_user_and_date(
                profile.user_id, today
            )
            if existing is not None:
                continue

            # Aggregate jobs from healthy sources
            all_jobs = []
            for source_name, client_cls in JOB_SOURCE_REGISTRY.items():
                if source_name not in healthy_names:
                    continue
                try:
                    client = client_cls()
                    query = " ".join(prefs.get("roles", []))
                    location = ", ".join(prefs.get("locations", []))
                    jobs = await client.search_jobs(
                        query=query, location=location, limit=10
                    )
                    all_jobs.extend(jobs)
                except Exception:
                    logger.exception(
                        "source_query_failed",
                        source=source_name,
                        user_id=str(profile.user_id),
                    )

            # Score and select top jobs
            scored_jobs = _score_jobs(all_jobs, prefs)
            top_jobs = scored_jobs[:5]

            shortlist_jobs = [
                ShortlistJob(
                    source=j["listing"].source,
                    source_url=j["listing"].source_url,
                    title=j["listing"].title,
                    company=j["listing"].company,
                    location=j["listing"].location,
                    fit_score=j["score"],
                    salary_range=j["listing"].salary_range,
                    match_reasons=j["reasons"],
                )
                for j in top_jobs
            ]

            shortlist = JobShortlist(
                user_id=profile.user_id,
                date=today,
                jobs=shortlist_jobs,
                preferences_snapshot=prefs,
            )
            await shortlist_repo.create(shortlist)
            generated += 1

        except Exception:
            errors += 1
            logger.exception(
                "shortlist_generation_failed",
                user_id=str(profile.user_id),
            )

    logger.info(
        "daily_shortlists_generated",
        total_profiles=len(profiles),
        generated=generated,
        errors=errors,
    )
    return {"generated": generated, "errors": errors}


def _score_jobs(job_listings, preferences: dict) -> list[dict]:
    """Score job listings against user preferences. Returns sorted list."""
    pref_roles = {r.lower() for r in preferences.get("roles", [])}
    pref_locations = {loc.lower() for loc in preferences.get("locations", [])}
    remote_only = preferences.get("remote_only", False)

    scored = []
    for listing in job_listings:
        score = 0.0
        reasons = []

        # Title/role match
        title_lower = listing.title.lower()
        for role in pref_roles:
            if role in title_lower:
                score += 0.4
                reasons.append(f"Role match: {role}")
                break

        # Location match
        loc_lower = listing.location.lower()
        if remote_only and "remote" in loc_lower:
            score += 0.3
            reasons.append("Remote position")
        elif any(loc in loc_lower for loc in pref_locations):
            score += 0.2
            reasons.append("Location match")

        # Salary indication
        if listing.salary_range:
            score += 0.1
            reasons.append("Salary disclosed")

        # Base relevance
        if score == 0.0:
            score = 0.1
            reasons.append("General match")

        scored.append({
            "listing": listing,
            "score": round(min(score, 1.0), 2),
            "reasons": reasons[:3],
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored
