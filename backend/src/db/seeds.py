"""
Seed data loader for MarketConfig documents.

Reads JSON files from the seeds/ directory and upserts them into MongoDB.
Called during application startup to ensure baseline market configurations
exist. Existing documents are not overwritten — only missing markets are
seeded.

Design decisions
----------------
Why JSON files (not Python dicts):
    JSON is editable by non-developers (product managers, market specialists)
    and can be version-controlled with clear diffs. Python dicts would work
    but couple seed data to code.

Why upsert (not insert):
    Idempotent seeding — running the seed loader twice does not fail or
    create duplicates. If a market already exists (by region_code), it is
    skipped. Admin API updates are preserved.
"""

import json
from pathlib import Path

import structlog

from src.db.documents.market_config import MarketConfig

logger = structlog.get_logger()

_SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds"


async def seed_market_configs() -> int:
    """
    Load market config seed files and insert any that don't exist.

    Returns the number of new documents inserted.
    """
    seed_files = sorted(_SEEDS_DIR.glob("market_config_*.json"))
    inserted = 0

    for seed_file in seed_files:
        try:
            data = json.loads(seed_file.read_text(encoding="utf-8"))
            region_code = data.get("region_code", "")

            if not region_code:
                logger.warning("seed_missing_region_code", file=seed_file.name)
                continue

            existing = await MarketConfig.find_one(
                {"region_code": region_code}
            )
            if existing:
                logger.debug("seed_skipped_existing", region_code=region_code)
                continue

            config = MarketConfig(**data)
            await config.insert()
            inserted += 1
            logger.info("seed_inserted", region_code=region_code, file=seed_file.name)

        except Exception:
            logger.exception("seed_load_failed", file=seed_file.name)

    logger.info("seed_market_configs_complete", inserted=inserted, total_files=len(seed_files))
    return inserted
