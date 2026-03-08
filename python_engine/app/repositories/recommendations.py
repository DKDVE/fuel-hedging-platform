"""Recommendation repository for hedge recommendation CRUD and queries."""

import uuid
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HedgeRecommendation, RecommendationStatus
from app.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository[HedgeRecommendation]):
    """Repository for HedgeRecommendation model operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(HedgeRecommendation, db)

    async def get_pending(self) -> list[HedgeRecommendation]:
        """Get all pending recommendations ordered by creation time.
        
        Returns:
            List of pending recommendations (oldest first)
        """
        result = await self.db.execute(
            select(HedgeRecommendation)
            .where(HedgeRecommendation.status == RecommendationStatus.PENDING)
            .order_by(HedgeRecommendation.created_at)
        )
        return list(result.scalars().all())

    async def get_latest(self) -> Optional[HedgeRecommendation]:
        """Get the most recent recommendation regardless of status.
        
        Returns:
            Latest recommendation or None
        """
        result = await self.db.execute(
            select(HedgeRecommendation)
            .order_by(desc(HedgeRecommendation.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_pending(self) -> Optional[HedgeRecommendation]:
        """Get the most recent pending recommendation.
        
        Returns:
            Latest pending recommendation or None
        """
        result = await self.db.execute(
            select(HedgeRecommendation)
            .where(HedgeRecommendation.status == RecommendationStatus.PENDING)
            .order_by(desc(HedgeRecommendation.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history(self, limit: int = 50) -> list[HedgeRecommendation]:
        """Get recommendation history ordered by newest first.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of recommendations
        """
        result = await self.db.execute(
            select(HedgeRecommendation)
            .order_by(desc(HedgeRecommendation.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self, 
        recommendation_id: uuid.UUID, 
        new_status: RecommendationStatus
    ) -> Optional[HedgeRecommendation]:
        """Update recommendation status.
        
        Args:
            recommendation_id: Recommendation UUID
            new_status: New status to set
            
        Returns:
            Updated recommendation or None if not found
        """
        recommendation = await self.get_by_id(recommendation_id)
        if recommendation is None:
            return None
        recommendation.status = new_status
        await self.db.flush()
        await self.db.refresh(recommendation)
        return recommendation

    async def set_escalation_flag(
        self, 
        recommendation_id: uuid.UUID,
        escalate: bool = True
    ) -> Optional[HedgeRecommendation]:
        """Set or clear escalation flag on a recommendation.
        
        Args:
            recommendation_id: Recommendation UUID
            escalate: Whether to escalate (True) or clear escalation (False)
            
        Returns:
            Updated recommendation or None if not found
        """
        recommendation = await self.get_by_id(recommendation_id)
        if recommendation is None:
            return None
        recommendation.escalation_flag = escalate
        await self.db.flush()
        await self.db.refresh(recommendation)
        return recommendation

    async def get_escalated(self) -> list[HedgeRecommendation]:
        """Get all recommendations with escalation flag set.
        
        Returns:
            List of escalated recommendations
        """
        result = await self.db.execute(
            select(HedgeRecommendation)
            .where(HedgeRecommendation.escalation_flag == True)
            .where(HedgeRecommendation.status == RecommendationStatus.PENDING)
            .order_by(HedgeRecommendation.created_at)
        )
        return list(result.scalars().all())

    async def get_by_run_id(self, run_id: uuid.UUID) -> list[HedgeRecommendation]:
        """Get all recommendations from a specific analytics run.
        
        Args:
            run_id: Analytics run UUID
            
        Returns:
            List of recommendations for the run
        """
        result = await self.db.execute(
            select(HedgeRecommendation)
            .where(HedgeRecommendation.run_id == run_id)
            .order_by(HedgeRecommendation.sequence_number)
        )
        return list(result.scalars().all())
