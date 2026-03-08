"""Tests for recommendation repository.

Tests all database operations for hedge recommendations.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    HedgeRecommendation,
    AnalyticsRun,
    User,
    UserRole,
    RecommendationStatus,
    DecisionType,
    AnalyticsRunStatus,
)
from app.repositories.recommendation_repository import RecommendationRepository
from app.exceptions import DataIngestionError, NotFoundError


@pytest.fixture
async def repository(db_session: AsyncSession) -> RecommendationRepository:
    """Create a recommendation repository instance."""
    return RecommendationRepository(db_session)


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@airline.com",
        hashed_password="hashed_password_123",
        role=UserRole.RISK_MANAGER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_analytics_run(db_session: AsyncSession) -> AnalyticsRun:
    """Create a test analytics run."""
    run = AnalyticsRun(
        run_date=datetime.now(timezone.utc).date(),
        mape=Decimal("6.5"),
        forecast_json={"model": "ensemble"},
        var_results={"dynamic_var": 8500000},
        basis_metrics={"r2": 0.85},
        optimizer_result={"optimal_hr": 0.72},
        model_versions={"forecast": "v1.0"},
        duration_seconds=Decimal("120.5"),
        status=AnalyticsRunStatus.COMPLETED,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return run


@pytest.mark.asyncio
async def test_create_recommendation(
    repository: RecommendationRepository,
    test_analytics_run: AnalyticsRun,
    db_session: AsyncSession,
):
    """Test creating a new recommendation."""
    recommendation = await repository.create(
        run_id=test_analytics_run.id,
        optimal_hr=Decimal("0.72"),
        instrument_mix={"futures": 0.45, "options": 0.30, "collars": 0.15, "swaps": 0.10},
        proxy_weights={"heating_oil": 0.60, "brent": 0.40},
        var_hedged=Decimal("8500000"),
        var_unhedged=Decimal("13200000"),
        var_reduction_pct=Decimal("35.61"),
        collateral_usd=Decimal("12500000"),
        agent_outputs={
            "agents": [
                {
                    "agent_id": "basis_risk",
                    "risk_level": "LOW",
                    "recommendation": "Test",
                    "metrics": {},
                    "constraints_satisfied": True,
                    "action_required": False,
                    "ifrs9_eligible": True,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        },
    )
    await db_session.commit()

    assert recommendation.id is not None
    assert recommendation.run_id == test_analytics_run.id
    assert recommendation.optimal_hr == Decimal("0.72")
    assert recommendation.status == RecommendationStatus.PENDING
    assert recommendation.sequence_number > 0


@pytest.mark.asyncio
async def test_create_recommendation_invalid_run_id(
    repository: RecommendationRepository,
    db_session: AsyncSession,
):
    """Test creating recommendation with non-existent run_id fails."""
    with pytest.raises(DataIngestionError, match="Analytics run .* does not exist"):
        await repository.create(
            run_id=uuid4(),  # Non-existent run
            optimal_hr=Decimal("0.72"),
            instrument_mix={},
            proxy_weights={},
            var_hedged=Decimal("0"),
            var_unhedged=Decimal("0"),
            var_reduction_pct=Decimal("0"),
            collateral_usd=Decimal("0"),
            agent_outputs={},
        )


@pytest.mark.asyncio
async def test_get_by_id(
    repository: RecommendationRepository,
    test_analytics_run: AnalyticsRun,
    db_session: AsyncSession,
):
    """Test retrieving a recommendation by ID."""
    # Create recommendation
    created = await repository.create(
        run_id=test_analytics_run.id,
        optimal_hr=Decimal("0.70"),
        instrument_mix={},
        proxy_weights={},
        var_hedged=Decimal("0"),
        var_unhedged=Decimal("0"),
        var_reduction_pct=Decimal("0"),
        collateral_usd=Decimal("0"),
        agent_outputs={},
    )
    await db_session.commit()

    # Retrieve it
    retrieved = await repository.get_by_id(created.id)
    assert retrieved.id == created.id
    assert retrieved.optimal_hr == Decimal("0.70")


@pytest.mark.asyncio
async def test_get_by_id_not_found(repository: RecommendationRepository):
    """Test get_by_id raises NotFoundError for non-existent ID."""
    with pytest.raises(NotFoundError, match="Recommendation .* not found"):
        await repository.get_by_id(uuid4())


@pytest.mark.asyncio
async def test_get_pending(
    repository: RecommendationRepository,
    test_analytics_run: AnalyticsRun,
    db_session: AsyncSession,
):
    """Test retrieving all pending recommendations."""
    # Create 2 pending, 1 approved
    for i in range(3):
        status = RecommendationStatus.PENDING if i < 2 else RecommendationStatus.APPROVED
        await repository.create(
            run_id=test_analytics_run.id,
            optimal_hr=Decimal(f"0.{70 + i}"),
            instrument_mix={},
            proxy_weights={},
            var_hedged=Decimal("0"),
            var_unhedged=Decimal("0"),
            var_reduction_pct=Decimal("0"),
            collateral_usd=Decimal("0"),
            agent_outputs={},
            status=status,
        )
    await db_session.commit()

    # Get pending
    pending = await repository.get_pending()
    assert len(pending) == 2
    assert all(rec.status == RecommendationStatus.PENDING for rec in pending)


@pytest.mark.asyncio
async def test_list_paginated(
    repository: RecommendationRepository,
    test_analytics_run: AnalyticsRun,
    db_session: AsyncSession,
):
    """Test paginated list of recommendations."""
    # Create 15 recommendations
    for i in range(15):
        await repository.create(
            run_id=test_analytics_run.id,
            optimal_hr=Decimal(f"0.{60 + i}"),
            instrument_mix={},
            proxy_weights={},
            var_hedged=Decimal("0"),
            var_unhedged=Decimal("0"),
            var_reduction_pct=Decimal("0"),
            collateral_usd=Decimal("0"),
            agent_outputs={},
        )
    await db_session.commit()

    # Get first page
    recs, total = await repository.list_paginated(page=1, limit=10)
    assert len(recs) == 10
    assert total == 15

    # Get second page
    recs, total = await repository.list_paginated(page=2, limit=10)
    assert len(recs) == 5
    assert total == 15


@pytest.mark.asyncio
async def test_update_status(
    repository: RecommendationRepository,
    test_analytics_run: AnalyticsRun,
    db_session: AsyncSession,
):
    """Test updating recommendation status."""
    # Create recommendation
    rec = await repository.create(
        run_id=test_analytics_run.id,
        optimal_hr=Decimal("0.72"),
        instrument_mix={},
        proxy_weights={},
        var_hedged=Decimal("0"),
        var_unhedged=Decimal("0"),
        var_reduction_pct=Decimal("0"),
        collateral_usd=Decimal("0"),
        agent_outputs={},
        status=RecommendationStatus.PENDING,
    )
    await db_session.commit()

    # Update status
    updated = await repository.update_status(rec.id, RecommendationStatus.APPROVED)
    await db_session.commit()

    assert updated.id == rec.id
    assert updated.status == RecommendationStatus.APPROVED


@pytest.mark.asyncio
async def test_add_approval(
    repository: RecommendationRepository,
    test_analytics_run: AnalyticsRun,
    test_user: User,
    db_session: AsyncSession,
):
    """Test adding an approval decision."""
    # Create recommendation
    rec = await repository.create(
        run_id=test_analytics_run.id,
        optimal_hr=Decimal("0.72"),
        instrument_mix={},
        proxy_weights={},
        var_hedged=Decimal("0"),
        var_unhedged=Decimal("0"),
        var_reduction_pct=Decimal("0"),
        collateral_usd=Decimal("0"),
        agent_outputs={},
    )
    await db_session.commit()

    # Add approval
    approval = await repository.add_approval(
        recommendation_id=rec.id,
        approver_id=test_user.id,
        decision=DecisionType.APPROVE,
        response_lag_minutes=Decimal("45.5"),
        override_reason="Looks good",
        ip_address="192.168.1.1",
    )
    await db_session.commit()

    assert approval.id is not None
    assert approval.recommendation_id == rec.id
    assert approval.approver_id == test_user.id
    assert approval.decision == DecisionType.APPROVE
    assert approval.response_lag_minutes == Decimal("45.5")


@pytest.mark.asyncio
async def test_count_by_status(
    repository: RecommendationRepository,
    test_analytics_run: AnalyticsRun,
    db_session: AsyncSession,
):
    """Test counting recommendations by status."""
    # Create recommendations with different statuses
    for i, status in enumerate(
        [
            RecommendationStatus.PENDING,
            RecommendationStatus.PENDING,
            RecommendationStatus.APPROVED,
            RecommendationStatus.REJECTED,
        ]
    ):
        await repository.create(
            run_id=test_analytics_run.id,
            optimal_hr=Decimal(f"0.{70 + i}"),
            instrument_mix={},
            proxy_weights={},
            var_hedged=Decimal("0"),
            var_unhedged=Decimal("0"),
            var_reduction_pct=Decimal("0"),
            collateral_usd=Decimal("0"),
            agent_outputs={},
            status=status,
        )
    await db_session.commit()

    # Get counts
    counts = await repository.count_by_status()
    assert counts["PENDING"] == 2
    assert counts["APPROVED"] == 1
    assert counts["REJECTED"] == 1
