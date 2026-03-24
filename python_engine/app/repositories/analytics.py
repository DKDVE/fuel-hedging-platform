"""Analytics run repository for pipeline execution tracking."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnalyticsRun, AnalyticsRunStatus
from app.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository[AnalyticsRun]):
    """Repository for AnalyticsRun model operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(AnalyticsRun, db)

    async def get_by_date(self, run_date: date) -> Optional[AnalyticsRun]:
        """Get analytics run for a specific date.
        
        Args:
            run_date: Date of the analytics run
            
        Returns:
            Analytics run or None if not found
        """
        result = await self.db.execute(
            select(AnalyticsRun).where(AnalyticsRun.run_date == run_date)
        )
        return result.scalar_one_or_none()

    async def get_running_pipeline(self) -> Optional[AnalyticsRun]:
        """Get currently running pipeline (status=RUNNING), if any."""
        result = await self.db.execute(
            select(AnalyticsRun)
            .where(AnalyticsRun.status == AnalyticsRunStatus.RUNNING)
            .order_by(desc(AnalyticsRun.run_date))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_completed(self) -> Optional[AnalyticsRun]:
        """Returns the most recent analytics run with status=COMPLETED."""
        return await self.get_latest()

    async def get_completed_since(self, days: int) -> list[AnalyticsRun]:
        """Returns all completed analytics runs within the last N days."""
        return await self.get_mape_history(n_days=days)

    async def get_latest(self) -> Optional[AnalyticsRun]:
        """Get the most recent completed analytics run with real pipeline metrics.

        Excludes n8n-only placeholder rows (source=n8n_manual) created when
        recommendations arrive before the Python pipeline has run.
        """
        result = await self.db.execute(
            select(AnalyticsRun)
            .where(AnalyticsRun.status == AnalyticsRunStatus.COMPLETED)
            .where(text("(forecast_json->>'source') IS DISTINCT FROM 'n8n_manual'"))
            .order_by(desc(AnalyticsRun.run_date))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def reset_stale_running_runs(self, max_age_hours: int = 2) -> int:
        """Mark RUNNING pipelines older than max_age_hours as FAILED. Returns count updated."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        result = await self.db.execute(
            select(AnalyticsRun).where(
                AnalyticsRun.status == AnalyticsRunStatus.RUNNING,
                AnalyticsRun.created_at < cutoff,
            )
        )
        rows = result.scalars().all()
        count = 0
        for r in rows:
            r.status = AnalyticsRunStatus.FAILED
            fj = dict(r.forecast_json or {})
            fj["error"] = "pipeline_stale_timeout"
            r.forecast_json = fj
            count += 1
        if count:
            await self.db.commit()
        return count

    async def get_mape_history(self, n_days: int = 30) -> list[AnalyticsRun]:
        """Get MAPE history for the last N days.
        
        Args:
            n_days: Number of days to look back
            
        Returns:
            List of analytics runs with MAPE data (chronological order)
        """
        cutoff_date = date.today() - timedelta(days=n_days)
        result = await self.db.execute(
            select(AnalyticsRun)
            .where(AnalyticsRun.run_date >= cutoff_date)
            .where(AnalyticsRun.status == AnalyticsRunStatus.COMPLETED)
            .order_by(AnalyticsRun.run_date)
        )
        return list(result.scalars().all())

    async def get_recent_runs(
        self, 
        limit: int = 10, 
        status: Optional[AnalyticsRunStatus] = None
    ) -> list[AnalyticsRun]:
        """Get recent analytics runs.
        
        Args:
            limit: Maximum number of records to return
            status: Optional status filter
            
        Returns:
            List of analytics runs (newest first)
        """
        query = select(AnalyticsRun)
        if status is not None:
            query = query.where(AnalyticsRun.status == status)
        query = query.order_by(desc(AnalyticsRun.run_date)).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_average_mape(self, n_days: int = 30) -> Optional[float]:
        """Calculate average MAPE over the last N days.
        
        Args:
            n_days: Number of days to average over
            
        Returns:
            Average MAPE or None if no data
        """
        from sqlalchemy import func
        
        cutoff_date = date.today() - timedelta(days=n_days)
        result = await self.db.execute(
            select(func.avg(AnalyticsRun.mape))
            .where(AnalyticsRun.run_date >= cutoff_date)
            .where(AnalyticsRun.status == AnalyticsRunStatus.COMPLETED)
        )
        avg_mape = result.scalar_one_or_none()
        return float(avg_mape) if avg_mape else None

    async def get_failed_runs(self, days: int = 7) -> list[AnalyticsRun]:
        """Get failed analytics runs in the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of failed runs
        """
        cutoff_date = date.today() - timedelta(days=days)
        result = await self.db.execute(
            select(AnalyticsRun)
            .where(AnalyticsRun.run_date >= cutoff_date)
            .where(AnalyticsRun.status == AnalyticsRunStatus.FAILED)
            .order_by(desc(AnalyticsRun.run_date))
        )
        return list(result.scalars().all())

    async def update_status(
        self, 
        run_id: UUID, 
        new_status: AnalyticsRunStatus
    ) -> Optional[AnalyticsRun]:
        """Update analytics run status.
        
        Args:
            run_id: Analytics run UUID
            new_status: New status to set
            
        Returns:
            Updated run or None if not found
        """
        run = await self.get_by_id(run_id)
        if run is None:
            return None
        run.status = new_status
        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def get_or_create_manual_run(self, run_date: date) -> AnalyticsRun:
        """Get existing run for date or create minimal run for n8n manual triggers.
        
        Used when run_id is 'manual-xxx' and no pipeline run exists.
        Returns run to use as recommendation.run_id.
        """
        existing = await self.get_by_date(run_date)
        if existing:
            return existing
        run = AnalyticsRun(
            run_date=run_date,
            status=AnalyticsRunStatus.COMPLETED,
            mape=Decimal("0"),
            forecast_json={"source": "n8n_manual"},
            var_results={"source": "n8n_manual"},
            basis_metrics={"source": "n8n_manual"},
            optimizer_result={"source": "n8n_manual"},
            model_versions={"pipeline": "n8n_manual"},
            duration_seconds=Decimal("0.01"),  # Must be > 0 per CheckConstraint
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)
        return run
