"""Database package initialization.

Imports all models so Alembic can detect them.
"""

from app.db.base import Base, AsyncSessionLocal, engine, get_db
from app.db.models import (
    User,
    UserRole,
    PlatformConfig,
    PriceTick,
    AnalyticsRun,
    AnalyticsRunStatus,
    BacktestRun,
    HedgeRecommendation,
    RecommendationStatus,
    Approval,
    DecisionType,
    HedgePosition,
    InstrumentType,
    PositionStatus,
    AuditLog,
)

__all__ = [
    # Base
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    # Models
    "User",
    "UserRole",
    "PlatformConfig",
    "PriceTick",
    "AnalyticsRun",
    "AnalyticsRunStatus",
    "BacktestRun",
    "HedgeRecommendation",
    "RecommendationStatus",
    "Approval",
    "DecisionType",
    "HedgePosition",
    "InstrumentType",
    "PositionStatus",
    "AuditLog",
]
