"""Repository pattern for hedge recommendations data access.

All database operations for recommendations go through this layer.
Never access DB directly from routers or services.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence
from uuid import UUID

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Approval,
    HedgeRecommendation,
    RecommendationStatus,
    User,
    AnalyticsRun,
    DecisionType,
)
from app.exceptions import DataIngestionError, NotFoundError

log = structlog.get_logger()


class RecommendationRepository:
    """Repository for hedge recommendation CRUD operations.
    
    All methods are async and use SQLAlchemy 2.0 syntax.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        run_id: UUID,
        optimal_hr: Decimal,
        instrument_mix: dict,
        proxy_weights: dict,
        var_hedged: Decimal,
        var_unhedged: Decimal,
        var_reduction_pct: Decimal,
        collateral_usd: Decimal,
        agent_outputs: dict,
        status: RecommendationStatus = RecommendationStatus.PENDING,
    ) -> HedgeRecommendation:
        """Create a new hedge recommendation.
        
        Validates that run_id references an existing AnalyticsRun.
        """
        log.info(
            "recommendation_repository.create",
            run_id=str(run_id),
            optimal_hr=float(optimal_hr),
            status=status.value,
        )

        # Verify analytics run exists
        run_exists = await self.session.execute(
            select(AnalyticsRun.id).where(AnalyticsRun.id == run_id)
        )
        if not run_exists.scalar_one_or_none():
            raise DataIngestionError(
                f"Analytics run {run_id} does not exist",
                source="recommendation_repository",
            )

        # Compute next sequence_number (DB has no sequence; autoincrement not supported for non-PK)
        next_seq_result = await self.session.execute(
            select(func.coalesce(func.max(HedgeRecommendation.sequence_number), 0) + 1)
        )
        next_seq = next_seq_result.scalar_one()

        recommendation = HedgeRecommendation(
            run_id=run_id,
            sequence_number=next_seq,
            optimal_hr=optimal_hr,
            instrument_mix=instrument_mix,
            proxy_weights=proxy_weights,
            var_hedged=var_hedged,
            var_unhedged=var_unhedged,
            var_reduction_pct=var_reduction_pct,
            collateral_usd=collateral_usd,
            agent_outputs=agent_outputs,
            status=status,
        )

        self.session.add(recommendation)
        await self.session.flush()  # Get sequence_number without commit
        await self.session.refresh(recommendation)
        # Eager-load approvals+approver to avoid lazy load in sync _to_response_schema (async incompatible)
        result = await self.session.execute(
            select(HedgeRecommendation)
            .where(HedgeRecommendation.id == recommendation.id)
            .options(
                selectinload(HedgeRecommendation.approvals).selectinload(Approval.approver)
            )
        )
        recommendation = result.scalar_one()

        log.info(
            "recommendation_created",
            recommendation_id=str(recommendation.id),
            sequence_number=recommendation.sequence_number,
        )

        return recommendation

    async def get_by_id(
        self,
        recommendation_id: UUID,
        *,
        load_approvals: bool = True,
    ) -> HedgeRecommendation:
        """Retrieve a single recommendation by ID.
        
        Raises NotFoundError if not found.
        """
        query = select(HedgeRecommendation).where(HedgeRecommendation.id == recommendation_id)

        if load_approvals:
            query = query.options(
                selectinload(HedgeRecommendation.approvals).selectinload(Approval.approver)
            )

        result = await self.session.execute(query)
        recommendation = result.scalar_one_or_none()

        if not recommendation:
            raise NotFoundError(f"Recommendation {recommendation_id} not found")

        return recommendation

    async def get_pending(self) -> Sequence[HedgeRecommendation]:
        """Get all pending recommendations, ordered by creation date (oldest first).
        
        Includes approvals and approver details.
        """
        query = (
            select(HedgeRecommendation)
            .where(HedgeRecommendation.status == RecommendationStatus.PENDING)
            .order_by(HedgeRecommendation.created_at.asc())
            .options(
                selectinload(HedgeRecommendation.approvals).selectinload(Approval.approver)
            )
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_paginated(
        self,
        page: int = 1,
        limit: int = 10,
        *,
        status: RecommendationStatus | None = None,
        load_approvals: bool = True,
    ) -> tuple[Sequence[HedgeRecommendation], int]:
        """Get paginated list of recommendations.
        
        Returns (recommendations, total_count).
        """
        # Build base query
        query = select(HedgeRecommendation).order_by(HedgeRecommendation.created_at.desc())
        count_query = select(HedgeRecommendation.id)

        if status:
            query = query.where(HedgeRecommendation.status == status)
            count_query = count_query.where(HedgeRecommendation.status == status)

        if load_approvals:
            query = query.options(
                selectinload(HedgeRecommendation.approvals).selectinload(Approval.approver)
            )

        # Get total count
        count_result = await self.session.execute(count_query)
        total = len(count_result.scalars().all())

        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        recommendations = result.scalars().all()

        return recommendations, total

    async def update_status(
        self,
        recommendation_id: UUID,
        new_status: RecommendationStatus,
    ) -> HedgeRecommendation:
        """Update recommendation status.
        
        Returns updated recommendation.
        """
        log.info(
            "recommendation_status_update",
            recommendation_id=str(recommendation_id),
            new_status=new_status.value,
        )

        await self.session.execute(
            update(HedgeRecommendation)
            .where(HedgeRecommendation.id == recommendation_id)
            .values(status=new_status, updated_at=datetime.now(timezone.utc))
        )

        # Return updated object
        return await self.get_by_id(recommendation_id)

    async def mark_expired(self, recommendation_id: UUID) -> HedgeRecommendation:
        """Mark a recommendation as expired (2-hour SLA passed)."""
        return await self.update_status(recommendation_id, RecommendationStatus.EXPIRED)

    async def add_approval(
        self,
        *,
        recommendation_id: UUID,
        approver_id: UUID,
        decision: DecisionType,
        response_lag_minutes: Decimal,
        override_reason: str | None,
        ip_address: str,
    ) -> Approval:
        """Record an approval/rejection/defer decision.
        
        Does NOT update recommendation status — caller must do that separately.
        """
        log.info(
            "adding_approval",
            recommendation_id=str(recommendation_id),
            approver_id=str(approver_id),
            decision=decision.value,
        )

        # Verify recommendation exists
        await self.get_by_id(recommendation_id, load_approvals=False)

        # Verify user exists
        user_result = await self.session.execute(
            select(User.id).where(User.id == approver_id)
        )
        if not user_result.scalar_one_or_none():
            raise NotFoundError(f"User {approver_id} not found")

        approval = Approval(
            recommendation_id=recommendation_id,
            approver_id=approver_id,
            decision=decision,
            response_lag_minutes=response_lag_minutes,
            override_reason=override_reason,
            ip_address=ip_address,
        )

        self.session.add(approval)
        await self.session.flush()
        await self.session.refresh(approval, attribute_names=['approver'])

        log.info(
            "approval_recorded",
            approval_id=str(approval.id),
            decision=decision.value,
        )

        return approval

    async def escalate(self, recommendation_id: UUID) -> HedgeRecommendation:
        """Set escalation flag for CFO review.
        
        Used when constraints are marginal or agents disagree.
        """
        log.info("escalating_recommendation", recommendation_id=str(recommendation_id))

        await self.session.execute(
            update(HedgeRecommendation)
            .where(HedgeRecommendation.id == recommendation_id)
            .values(escalation_flag=True, updated_at=datetime.now(timezone.utc))
        )

        return await self.get_by_id(recommendation_id)

    async def get_latest_approved(self) -> HedgeRecommendation | None:
        """Get the most recently approved recommendation.
        
        Returns None if no approved recommendations exist.
        """
        query = (
            select(HedgeRecommendation)
            .where(HedgeRecommendation.status == RecommendationStatus.APPROVED)
            .order_by(HedgeRecommendation.created_at.desc())
            .limit(1)
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def count_by_status(self) -> dict[str, int]:
        """Get count of recommendations by status.
        
        Useful for dashboard metrics.
        """
        query = select(
            HedgeRecommendation.status,
            HedgeRecommendation.id,
        )

        result = await self.session.execute(query)
        rows = result.all()

        # Count by status
        counts: dict[str, int] = {}
        for row in rows:
            status = row.status.value
            counts[status] = counts.get(status, 0) + 1

        return counts


def get_recommendation_repository(session: AsyncSession) -> RecommendationRepository:
    """Dependency injection factory for FastAPI."""
    return RecommendationRepository(session)
