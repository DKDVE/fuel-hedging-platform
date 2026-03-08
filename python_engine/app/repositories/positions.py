"""Position repository for hedge position tracking."""

import uuid
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HedgePosition, PositionStatus
from app.repositories.base import BaseRepository


class PositionRepository(BaseRepository[HedgePosition]):
    """Repository for HedgePosition model operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(HedgePosition, db)

    async def get_open_positions(self) -> list[HedgePosition]:
        """Get all currently open positions.
        
        Returns:
            List of open positions ordered by expiry date
        """
        result = await self.db.execute(
            select(HedgePosition)
            .where(HedgePosition.status == PositionStatus.OPEN)
            .order_by(HedgePosition.expiry_date)
        )
        return list(result.scalars().all())

    async def get_expiring_soon(self, days_ahead: int = 30) -> list[HedgePosition]:
        """Get positions expiring within specified days.
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            List of positions expiring within the specified period
        """
        expiry_threshold = date.today() + timedelta(days=days_ahead)
        result = await self.db.execute(
            select(HedgePosition)
            .where(HedgePosition.status == PositionStatus.OPEN)
            .where(HedgePosition.expiry_date <= expiry_threshold)
            .order_by(HedgePosition.expiry_date)
        )
        return list(result.scalars().all())

    async def get_by_recommendation_id(
        self, 
        recommendation_id: uuid.UUID
    ) -> list[HedgePosition]:
        """Get all positions created from a specific recommendation.
        
        Args:
            recommendation_id: Recommendation UUID
            
        Returns:
            List of positions for the recommendation
        """
        result = await self.db.execute(
            select(HedgePosition)
            .where(HedgePosition.recommendation_id == recommendation_id)
            .order_by(HedgePosition.created_at)
        )
        return list(result.scalars().all())

    async def close_position(
        self, 
        position_id: uuid.UUID
    ) -> Optional[HedgePosition]:
        """Mark a position as closed.
        
        Args:
            position_id: Position UUID
            
        Returns:
            Updated position or None if not found
        """
        position = await self.get_by_id(position_id)
        if position is None:
            return None
        position.status = PositionStatus.CLOSED
        await self.db.flush()
        await self.db.refresh(position)
        return position

    async def expire_position(
        self, 
        position_id: uuid.UUID
    ) -> Optional[HedgePosition]:
        """Mark a position as expired.
        
        Args:
            position_id: Position UUID
            
        Returns:
            Updated position or None if not found
        """
        position = await self.get_by_id(position_id)
        if position is None:
            return None
        position.status = PositionStatus.EXPIRED
        await self.db.flush()
        await self.db.refresh(position)
        return position

    async def get_total_open_collateral(self) -> float:
        """Calculate total collateral for all open positions.
        
        Returns:
            Total collateral in USD
        """
        from sqlalchemy import func
        
        result = await self.db.execute(
            select(func.sum(HedgePosition.collateral_usd))
            .where(HedgePosition.status == PositionStatus.OPEN)
        )
        total = result.scalar_one_or_none()
        return float(total) if total else 0.0

    async def get_total_open_notional(self) -> float:
        """Calculate total notional for all open positions.
        
        Returns:
            Total notional in USD
        """
        from sqlalchemy import func
        
        result = await self.db.execute(
            select(func.sum(HedgePosition.notional_usd))
            .where(HedgePosition.status == PositionStatus.OPEN)
        )
        total = result.scalar_one_or_none()
        return float(total) if total else 0.0

    async def get_positions_by_status(
        self, 
        status: PositionStatus
    ) -> list[HedgePosition]:
        """Get all positions with a specific status.
        
        Args:
            status: Position status to filter by
            
        Returns:
            List of positions with the specified status
        """
        result = await self.db.execute(
            select(HedgePosition)
            .where(HedgePosition.status == status)
            .order_by(desc(HedgePosition.created_at))
        )
        return list(result.scalars().all())
