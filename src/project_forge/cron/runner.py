"""CLI entry point for cron-based idea generation."""

import asyncio
import logging
import sys

from project_forge.config import settings
from project_forge.cron.scheduler import run_full_cycle
from project_forge.engine.generator import IdeaGenerator
from project_forge.storage.db import Database

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _run():
    db = Database(settings.db_path)
    await db.connect()
    try:
        generator = IdeaGenerator()
        idea = await run_full_cycle(db, generator)
        logger.info("Generated: %s (score: %.2f, category: %s)", idea.name, idea.feasibility_score, idea.category.value)
    except Exception:
        logger.exception("Generation cycle failed")
        sys.exit(1)
    finally:
        await db.close()


def main():
    asyncio.run(_run())


if __name__ == "__main__":
    main()
