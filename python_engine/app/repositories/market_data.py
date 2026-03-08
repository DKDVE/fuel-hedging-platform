"""Market data repository for price tick CRUD and time-series queries."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, desc, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PriceTick
from app.repositories.base import BaseRepository


class MarketDataRepository(BaseRepository[PriceTick]):
    """Repository for PriceTick model operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(PriceTick, db)

    async def upsert_tick(self, tick: PriceTick) -> PriceTick:
        """Insert or update a price tick (idempotent operation).
        
        Uses PostgreSQL ON CONFLICT DO UPDATE to ensure idempotency.
        Same timestamp + source = update existing record.
        
        Args:
            tick: PriceTick instance to upsert
            
        Returns:
            Upserted tick instance
        """
        stmt = pg_insert(PriceTick).values(
            id=tick.id,
            time=tick.time,
            jet_fuel_spot=tick.jet_fuel_spot,
            heating_oil_futures=tick.heating_oil_futures,
            brent_futures=tick.brent_futures,
            wti_futures=tick.wti_futures,
            crack_spread=tick.crack_spread,
            volatility_index=tick.volatility_index,
            quality_flag=tick.quality_flag,
            source=tick.source,
        ).on_conflict_do_update(
            constraint='unique_tick_time_source',
            set_={
                'jet_fuel_spot': tick.jet_fuel_spot,
                'heating_oil_futures': tick.heating_oil_futures,
                'brent_futures': tick.brent_futures,
                'wti_futures': tick.wti_futures,
                'crack_spread': tick.crack_spread,
                'volatility_index': tick.volatility_index,
                'quality_flag': tick.quality_flag,
                'updated_at': datetime.utcnow(),
            }
        ).returning(PriceTick)
        
        result = await self.db.execute(stmt)
        upserted = result.scalar_one()
        await self.db.refresh(upserted)
        return upserted

    async def get_latest_tick(self) -> Optional[PriceTick]:
        """Get the most recent price tick.
        
        Returns:
            Latest tick or None
        """
        result = await self.db.execute(
            select(PriceTick)
            .order_by(desc(PriceTick.time))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_ticks_since(
        self, 
        since: datetime, 
        limit: Optional[int] = None
    ) -> list[PriceTick]:
        """Get all ticks since a specific datetime.
        
        Args:
            since: Starting datetime (inclusive)
            limit: Optional maximum number of records
            
        Returns:
            List of ticks in chronological order
        """
        query = (
            select(PriceTick)
            .where(PriceTick.time >= since)
            .order_by(PriceTick.time)
        )
        if limit is not None:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_ticks_range(
        self, 
        start: datetime, 
        end: datetime
    ) -> list[PriceTick]:
        """Get all ticks within a datetime range.
        
        Args:
            start: Start datetime (inclusive)
            end: End datetime (inclusive)
            
        Returns:
            List of ticks in chronological order
        """
        result = await self.db.execute(
            select(PriceTick)
            .where(and_(PriceTick.time >= start, PriceTick.time <= end))
            .order_by(PriceTick.time)
        )
        return list(result.scalars().all())

    async def get_recent_ticks(self, limit: int = 500) -> list[PriceTick]:
        """Get most recent ticks.
        
        Args:
            limit: Maximum number of ticks to return
            
        Returns:
            List of recent ticks (newest first)
        """
        result = await self.db.execute(
            select(PriceTick)
            .order_by(desc(PriceTick.time))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_ticks_with_quality_flags(
        self, 
        days: int = 7
    ) -> list[PriceTick]:
        """Get ticks with quality flags in the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of flagged ticks
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(PriceTick)
            .where(PriceTick.time >= cutoff)
            .where(PriceTick.quality_flag.isnot(None))
            .order_by(desc(PriceTick.time))
        )
        return list(result.scalars().all())

    async def get_last_n_days(self, n_days: int = 365) -> list[PriceTick]:
        """Get all ticks from the last N days.
        
        Used for loading dataset for analytics.
        
        Args:
            n_days: Number of days to look back
            
        Returns:
            List of ticks in chronological order
        """
        cutoff = datetime.utcnow() - timedelta(days=n_days)
        result = await self.db.execute(
            select(PriceTick)
            .where(PriceTick.time >= cutoff)
            .order_by(PriceTick.time)
        )
        return list(result.scalars().all())
