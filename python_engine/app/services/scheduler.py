"""Background scheduler for periodic tasks using APScheduler.

Handles:
- Daily analytics pipeline (at 00:00 UTC) — full Python pipeline + n8n at completion
- Recommendation SLA monitoring (every hour)
- Price data quality checks (every 15 minutes)
"""

from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.db.models import AnalyticsRunStatus
from app.services.pipeline_runner import run_analytics_pipeline_background

log = structlog.get_logger()
settings = get_settings()

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


async def trigger_daily_analytics_pipeline() -> None:
    """Run the full analytics pipeline daily (same as Dashboard → Run Pipeline).

    Previously only called the n8n webhook, which created placeholder analytics rows
    with no MAPE/VaR. The Python pipeline now runs first; it triggers n8n on success.
    """
    log.info("scheduler.trigger_daily_analytics_pipeline", utc_time=datetime.now(timezone.utc))
    notional = Decimal("10000000")
    try:
        run_id = await run_analytics_pipeline_background(notional)
        if run_id:
            log.info("daily_analytics_pipeline_finished", run_id=run_id)
        else:
            log.error("daily_analytics_pipeline_error", error="pipeline returned no run_id")
    except Exception as e:
        log.error("daily_analytics_pipeline_error", error=str(e), exc_info=True)


def _is_manual_placeholder_run(run: object) -> bool:
    """Detect n8n-only placeholder runs that lack full pipeline analytics."""
    forecast_json = getattr(run, "forecast_json", {}) or {}
    return isinstance(forecast_json, dict) and forecast_json.get("source") == "n8n_manual"


def _safe_scheduler_tz() -> str:
    """Return a valid timezone string for scheduler setup."""
    try:
        ZoneInfo(settings.SCHEDULER_TIMEZONE)
        return settings.SCHEDULER_TIMEZONE
    except ZoneInfoNotFoundError:
        log.warning(
            "invalid_scheduler_timezone_fallback",
            configured_timezone=settings.SCHEDULER_TIMEZONE,
            fallback_timezone="UTC",
        )
        return "UTC"


async def run_startup_catchup_if_needed() -> None:
    """Backfill missed daily run if service starts after schedule."""
    if not settings.SCHEDULER_CATCHUP_ON_STARTUP:
        return

    scheduler_tz = _safe_scheduler_tz()
    now_local = datetime.now(ZoneInfo(scheduler_tz))
    scheduled_today = now_local.replace(
        hour=max(0, min(23, settings.SCHEDULER_DAILY_HOUR)),
        minute=max(0, min(59, settings.SCHEDULER_DAILY_MINUTE)),
        second=0,
        microsecond=0,
    )
    if now_local < scheduled_today:
        log.info(
            "scheduler_startup_catchup_skipped_not_due",
            now_local=now_local.isoformat(),
            scheduled_today=scheduled_today.isoformat(),
        )
        return

    from app.db.base import AsyncSessionLocal
    from app.repositories import AnalyticsRepository

    async with AsyncSessionLocal() as db:
        repo = AnalyticsRepository(db)
        run_today = await repo.get_by_date(now_local.date())
        if run_today is not None:
            if run_today.status == AnalyticsRunStatus.RUNNING:
                log.info("scheduler_startup_catchup_skipped_running_pipeline")
                return
            if run_today.status == AnalyticsRunStatus.COMPLETED and not _is_manual_placeholder_run(run_today):
                log.info(
                    "scheduler_startup_catchup_skipped_completed",
                    run_id=str(run_today.id),
                    run_date=str(run_today.run_date),
                )
                return

    log.warning(
        "scheduler_startup_catchup_triggered",
        reason="missing_or_placeholder_daily_run",
        run_date=str(now_local.date()),
    )
    await trigger_daily_analytics_pipeline()


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

    if not settings.SCHEDULER_ENABLED:
        log.info("scheduler_disabled_by_env")
        return

    log.info("starting_scheduler")

    scheduler_tz = _safe_scheduler_tz()
    daily_hour = max(0, min(23, settings.SCHEDULER_DAILY_HOUR))
    daily_minute = max(0, min(59, settings.SCHEDULER_DAILY_MINUTE))
    misfire_grace = max(60, settings.SCHEDULER_MISFIRE_GRACE_SECONDS)
    _scheduler = AsyncIOScheduler(timezone=scheduler_tz)

    # Daily analytics pipeline trigger
    _scheduler.add_job(
        trigger_daily_analytics_pipeline,
        trigger=CronTrigger(hour=daily_hour, minute=daily_minute, timezone=scheduler_tz),
        id="daily_analytics_pipeline",
        name="Daily Analytics Pipeline Trigger",
        replace_existing=True,
        coalesce=True,  # If missed, run once (don't queue multiple)
        max_instances=1,  # Only one instance at a time
        misfire_grace_time=misfire_grace,
    )
    log.info(
        "scheduled_job_added",
        job_id="daily_analytics_pipeline",
        schedule=f"{daily_hour:02d}:{daily_minute:02d} {scheduler_tz} daily",
        misfire_grace_time=misfire_grace,
    )

    # Recommendation SLA monitoring (every hour)
    _scheduler.add_job(
        check_recommendation_slas,
        trigger=IntervalTrigger(hours=1),
        id="recommendation_sla_check",
        name="Recommendation SLA Monitor",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=misfire_grace,
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
        misfire_grace_time=misfire_grace,
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
        misfire_grace_time=misfire_grace,
    )
    log.info("scheduled_job_added", job_id="alert_check", schedule="every 15 minutes")

    if settings.SCHEDULER_CATCHUP_ON_STARTUP:
        _scheduler.add_job(
            run_startup_catchup_if_needed,
            trigger=DateTrigger(run_date=datetime.now(ZoneInfo(scheduler_tz))),
            id="startup_catchup_check",
            name="Startup Catchup Check",
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=misfire_grace,
        )
        log.info("scheduled_job_added", job_id="startup_catchup_check", schedule="on_startup")

    # Start scheduler
    _scheduler.start()
    log.info(
        "scheduler_started",
        num_jobs=len(_scheduler.get_jobs()),
        timezone=scheduler_tz,
        daily_hour=daily_hour,
        daily_minute=daily_minute,
        misfire_grace_time=misfire_grace,
    )


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
