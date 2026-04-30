"""Background execution of the analytics pipeline (shared by API and scheduler)."""

from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.services.analytics_pipeline import AnalyticsPipeline

log = structlog.get_logger()


async def run_analytics_pipeline_background(notional_usd: Decimal) -> str | None:
    """Run the full analytics pipeline in a fresh DB session.

    Returns:
        Run ID on success, otherwise None.
    """
    async with AsyncSessionLocal() as session:
        try:
            pipeline = AnalyticsPipeline(session, notional_usd=notional_usd)
            return await pipeline.execute_daily_run()
        except Exception as e:
            log.error("pipeline_background_failed", error=str(e), exc_info=True)
            return None
