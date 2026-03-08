"""Repository package initialization.

Exports all repository classes for easy importing.
"""

from app.repositories.alerts import AlertRepository
from app.repositories.analytics import AnalyticsRepository
from app.repositories.audit import AuditRepository
from app.repositories.base import BaseRepository
from app.repositories.config import ConfigRepository
from app.repositories.market_data import MarketDataRepository
from app.repositories.positions import PositionRepository
from app.repositories.recommendations import RecommendationRepository
from app.repositories.users import UserRepository

__all__ = [
    "AlertRepository",
    "BaseRepository",
    "UserRepository",
    "RecommendationRepository",
    "PositionRepository",
    "AuditRepository",
    "AnalyticsRepository",
    "MarketDataRepository",
    "ConfigRepository",
]
