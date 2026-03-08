"""API routers package."""

from app.routers.alerts import router as alerts_router
from app.routers.analytics import router as analytics_router
from app.routers.compliance import router as compliance_router
from app.routers.audit import router as audit_router
from app.routers.auth import router as auth_router
from app.routers.market_data import router as market_data_router
from app.routers.positions import router as positions_router
from app.routers.recommendations import router as recommendations_router
from app.routers.reports import router as reports_router
from app.routers.stream import router as stream_router

__all__ = [
    "alerts_router",
    "analytics_router",
    "compliance_router",
    "audit_router",
    "auth_router",
    "market_data_router",
    "positions_router",
    "recommendations_router",
    "reports_router",
    "stream_router",
]
