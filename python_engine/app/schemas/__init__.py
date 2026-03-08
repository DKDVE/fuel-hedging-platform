"""Pydantic schemas package."""

from app.schemas.analytics import (
    AnalyticsRunDetail,
    AnalyticsRunQueryParams,
    AnalyticsRunResponse,
    AnalyticsSummary,
    TriggerAnalyticsRequest,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    CreateUserRequest,
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
    UpdateUserRequest,
    UserResponse,
)
from app.schemas.common import (
    HealthResponse,
    PaginatedResponse,
    PaginationParams,
    TimestampMixin,
    UUIDMixin,
)
from app.schemas.market_data import (
    LatestPricesResponse,
    MarketDataQueryParams,
    MarketDataStatsResponse,
    PriceStatistics,
    PriceTickList,
    PriceTickResponse,
)
from app.schemas.recommendations import (
    ApproveRequest,
    HedgeRecommendationResponse,
    RecommendationQueryParams,
    RecommendationWithRun,
    UpdateRecommendationRequest,
)

__all__ = [
    # Auth schemas
    "LoginRequest",
    "RefreshTokenRequest",
    "CreateUserRequest",
    "UpdateUserRequest",
    "ChangePasswordRequest",
    "UserResponse",
    "TokenResponse",
    "LoginResponse",
    "MessageResponse",
    "ErrorResponse",
    # Common schemas
    "PaginationParams",
    "PaginatedResponse",
    "TimestampMixin",
    "UUIDMixin",
    "HealthResponse",
    # Market data schemas
    "PriceTickResponse",
    "MarketDataQueryParams",
    "PriceTickList",
    "LatestPricesResponse",
    "PriceStatistics",
    "MarketDataStatsResponse",
    # Recommendations schemas
    "HedgeRecommendationResponse",
    "RecommendationQueryParams",
    "UpdateRecommendationRequest",
    "ApproveRequest",
    "RecommendationWithRun",
    # Analytics schemas
    "AnalyticsRunResponse",
    "AnalyticsRunQueryParams",
    "TriggerAnalyticsRequest",
    "AnalyticsRunDetail",
    "AnalyticsSummary",
]
