"""Background scheduler for periodic tasks using APScheduler.

Handles:
- Daily analytics pipeline trigger (at 00:00 UTC)
- Recommendation SLA monitoring (every hour)
- Price data quality checks (every 15 minutes)
"""

from datetime import datetime, timezone

import httpx
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


async def trigger_daily_analytics_pipeline() -> None:
    """Trigger n8n workflow to run daily analytics + recommendation generation.
    
    Called at 00:00 UTC daily.
    Calls n8n webhook directly (avoids API_INTERNAL_URL resolution on Render).
    """
    log.info("scheduler.trigger_daily_analytics_pipeline", utc_time=datetime.now(timezone.utc))

    n8n_url = settings.N8N_TRIGGER_URL or f"{settings.N8N_INTERNAL_URL.rstrip('/')}{settings.N8N_TRIGGER_PATH}"
    payload = {
        "run_id": f"scheduled-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "analytics_summary": {},
        "trigger_type": "daily_scheduled",
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                n8n_url,
                json=payload,
                headers={"X-N8N-API-Key": settings.N8N_WEBHOOK_SECRET},
            )
            response.raise_for_status()

            log.info(
                "daily_analytics_triggered",
                status_code=response.status_code,
                run_id=payload["run_id"],
            )

    except httpx.HTTPStatusError as e:
        log.error(
            "daily_analytics_trigger_failed",
            status_code=e.response.status_code,
            body=e.response.text,
        )
    except httpx.RequestError as e:
        log.error(
            "daily_analytics_trigger_network_error",
            error=str(e),
            target_host=n8n_url.split("/")[2] if "//" in n8n_url else "unknown",
            hint="Set N8N_TRIGGER_URL to full URL: https://hedge-n8n-xxx.onrender.com/webhook/fuel-hedge-trigger",
        )
    except Exception as e:
        log.error("daily_analytics_trigger_unexpected_error", error=str(e), exc_info=True)


async def check_recommendation_slas() -> None:
    """Check for pending recommendations approaching or past SLA.
    
    Called every hour.
    Sends alerts via SSE for recommendations > 1.5 hours old (30 min before expiry).
    """
    log.debug("scheduler.check_recommendation_slas")

    try:
        from app.db.base import get_db
        from app.services.event_broker import get_price_broker
        from app.services.recommendation_service import get_recommendation_service

        # Get pending recommendations
        async for session in get_db():
            try:
                broker = get_price_broker()
                service = get_recommendation_service(session, broker)
                pending = await service.get_pending()

                now = datetime.now(timezone.utc)
                for rec in pending:
                    age_hours = (now - rec.created_at).total_seconds() / 3600

                    # Alert if > 1.5 hours old (30 min before 2-hour SLA)
                    if age_hours >= 1.5:
                        log.warning(
                            "recommendation_approaching_sla",
                            recommendation_id=str(rec.id),
                            age_hours=age_hours,
                        )

                        # Broadcast SSE event
                        await broker.broadcast_recommendation_event(
                            event_type="approaching_expiry",
                            recommendation_id=rec.id,
                            status=rec.status,
                            data={
                                "age_hours": age_hours,
                                "expires_at": rec.expires_at.isoformat() if rec.expires_at else None,
                            },
                        )
                break
            finally:
                await session.close()

    except Exception as e:
        log.error("sla_check_failed", error=str(e), exc_info=True)


async def check_alerts() -> None:
    """Run alert threshold checks (VaR, collateral, MAPE, IFRS9, HR, SLA, price spike).
    
    Called every 15 minutes.
    Creates alerts for violations and publishes via SSE.
    """
    log.debug("scheduler.check_alerts")

    try:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.db.base import AsyncSessionLocal
        from app.db.models import HedgeRecommendation, RecommendationStatus
        from app.repositories import AnalyticsRepository
        from app.services.alert_service import AlertService

        async with AsyncSessionLocal() as db:
            try:
                analytics_repo = AnalyticsRepository(db)
                latest_run = await analytics_repo.get_latest_completed()

                # Get pending recommendations
                result = await db.execute(
                    select(HedgeRecommendation)
                    .where(HedgeRecommendation.status == RecommendationStatus.PENDING)
                    .order_by(HedgeRecommendation.created_at)
                )
                pending_recs = list(result.scalars().all())

                alert_service = AlertService()
                await alert_service.check_all(db, latest_run, pending_recs)
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    except Exception as e:
        log.error("alert_check_failed", error=str(e), exc_info=True)


async def check_price_data_quality() -> None:
    """Check market data feed health and quality.
    
    Called every 15 minutes.
    Logs warnings if data feed is stale or showing anomalies.
    """
    log.debug("scheduler.check_price_data_quality")

    try:
        from app.services.price_service import get_price_service

        price_service = get_price_service()
        status = price_service.get_status()

        # Check if feed is healthy — use actual PriceService status fields
        running = status.get("running", False)
        latest_price = status.get("latest_price")
        source = status.get("source", "unknown")
        source_healthy = running and latest_price is not None

        if not source_healthy:
            log.warning(
                "price_feed_unhealthy",
                mode=source,
                last_tick=latest_price.get("time") if isinstance(latest_price, dict) else None,
            )

        # Check tick rate — PriceService has tick_interval_seconds, estimate ticks/min
        tick_interval = status.get("tick_interval_seconds", 2.0)
        ticks_per_minute = 60.0 / tick_interval if tick_interval > 0 else 0
        if ticks_per_minute < 1.0 and running:
            log.warning(
                "price_feed_slow",
                ticks_per_minute=ticks_per_minute,
            )

    except Exception as e:
        log.error("price_quality_check_failed", error=str(e), exc_info=True)


def start_scheduler() -> None:
    """Start the background scheduler with all periodic tasks."""
    global _scheduler

    if _scheduler is not None:
        log.warning("scheduler_already_running")
        return

    log.info("starting_scheduler")

    _scheduler = AsyncIOScheduler(timezone="UTC")

    # Daily analytics pipeline trigger (00:00 UTC)
    _scheduler.add_job(
        trigger_daily_analytics_pipeline,
        trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="daily_analytics_pipeline",
        name="Daily Analytics Pipeline Trigger",
        replace_existing=True,
        coalesce=True,  # If missed, run once (don't queue multiple)
        max_instances=1,  # Only one instance at a time
    )
    log.info("scheduled_job_added", job_id="daily_analytics_pipeline", schedule="00:00 UTC daily")

    # Recommendation SLA monitoring (every hour)
    _scheduler.add_job(
        check_recommendation_slas,
        trigger=IntervalTrigger(hours=1),
        id="recommendation_sla_check",
        name="Recommendation SLA Monitor",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    log.info("scheduled_job_added", job_id="recommendation_sla_check", schedule="hourly")

    # Price data quality check (every 15 minutes)
    _scheduler.add_job(
        check_price_data_quality,
        trigger=IntervalTrigger(minutes=15),
        id="price_quality_check",
        name="Price Data Quality Check",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    log.info("scheduled_job_added", job_id="price_quality_check", schedule="every 15 minutes")

    # Alert threshold checks (every 15 minutes)
    _scheduler.add_job(
        check_alerts,
        trigger=IntervalTrigger(minutes=15),
        id="alert_check",
        name="Alert Threshold Check",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    log.info("scheduled_job_added", job_id="alert_check", schedule="every 15 minutes")

    # Start scheduler
    _scheduler.start()
    log.info("scheduler_started", num_jobs=len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Stop the background scheduler gracefully."""
    global _scheduler

    if _scheduler is None:
        log.warning("scheduler_not_running")
        return

    log.info("stopping_scheduler")
    _scheduler.shutdown(wait=True)
    _scheduler = None
    log.info("scheduler_stopped")


def get_scheduler() -> AsyncIOScheduler | None:
    """Get the running scheduler instance (for debugging)."""
    return _scheduler
