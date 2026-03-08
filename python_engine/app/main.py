"""Main FastAPI application entry point.

Configures:
- CORS middleware
- Rate limiting
- Exception handlers
- Structured logging
- API router registration
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.exceptions import HedgePlatformError

settings = get_settings()
logger = structlog.get_logger()

# Rate limiter
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.
    
    Runs startup and shutdown logic.
    """
    # Startup
    logger.info("application_startup", environment=settings.ENVIRONMENT)
    
    # Start price service for real-time feeds
    from app.services.price_service import get_price_service
    price_service = get_price_service()
    await price_service.start()
    logger.info("price_service_started", mode="live" if settings.USE_LIVE_FEED else "simulation")
    
    # Start scheduler if not in test mode
    if settings.ENVIRONMENT != "test":
        from app.services.scheduler import start_scheduler
        start_scheduler()
        logger.info("scheduler_started")
    
    yield
    
    # Shutdown
    if settings.ENVIRONMENT != "test":
        from app.services.scheduler import stop_scheduler
        stop_scheduler()
        logger.info("scheduler_stopped")
    
    # Stop price service
    await price_service.stop()
    logger.info("price_service_stopped")
    
    logger.info("application_shutdown")


# Create FastAPI app
app = FastAPI(
    title="Fuel Hedging Platform API",
    description="Aviation fuel hedging optimization platform with AI-driven risk analysis",
    version="1.0.0",
    docs_url="/api/v1/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/api/v1/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration — allow frontend origins for cookie-based auth
_origins = [o.strip() for o in settings.CORS_ORIGINS if o.strip()]
if settings.FRONTEND_ORIGIN and settings.FRONTEND_ORIGIN not in _origins:
    _origins.append(settings.FRONTEND_ORIGIN)
_origins.extend(["http://localhost:5173", "http://127.0.0.1:5173"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(_origins)),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-N8N-API-Key", "X-Request-ID"],
    expose_headers=["X-Total-Count", "X-Page", "X-Per-Page", "X-Request-ID"],
)


# Global exception handlers
@app.exception_handler(HedgePlatformError)
async def platform_exception_handler(request: Request, exc: HedgePlatformError) -> JSONResponse:
    """Handle all custom platform exceptions."""
    logger.warning(
        "platform_error",
        error_code=exc.error_code,
        message=exc.message,
        path=request.url.path,
        context=exc.context,
    )
    
    status_code_map = {
        "CONSTRAINT_VIOLATION": status.HTTP_400_BAD_REQUEST,
        "DATA_INGESTION_ERROR": status.HTTP_400_BAD_REQUEST,
        "MODEL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "AUTH_ERROR": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_ERROR": status.HTTP_403_FORBIDDEN,
        "AUDIT_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    # Default to 500 if error code not found
    status_code = status_code_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.warning(
        "validation_error",
        path=request.url.path,
        errors=exc.errors(),
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        exception=str(exc),
        exc_info=True,
    )
    
    # In production, don't leak internal details
    if settings.ENVIRONMENT == "production":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
            },
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": str(exc),
        },
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


# Convenience redirects (docs live at /api/v1/docs for versioning)
@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect root to API docs."""
    return RedirectResponse(url="/api/v1/docs", status_code=status.HTTP_302_FOUND)


@app.get("/docs", include_in_schema=False)
async def docs_redirect() -> RedirectResponse:
    """Redirect /docs to versioned docs."""
    return RedirectResponse(url="/api/v1/docs", status_code=status.HTTP_302_FOUND)


# API v1 routers
from app.routers import (
    alerts_router,
    analytics_router,
    compliance_router,
    audit_router,
    auth_router,
    market_data_router,
    positions_router,
    recommendations_router,
    reports_router,
    stream_router,
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(market_data_router, prefix="/api/v1/market-data", tags=["Market Data"])
app.include_router(recommendations_router, prefix="/api/v1/recommendations", tags=["Recommendations"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(compliance_router, prefix="/api/v1", tags=["Compliance"])
app.include_router(positions_router, prefix="/api/v1/positions", tags=["Positions"])
app.include_router(audit_router, prefix="/api/v1/audit", tags=["Audit"])
app.include_router(alerts_router, prefix="/api/v1", tags=["Alerts"])
app.include_router(reports_router, prefix="/api/v1", tags=["Reports"])
app.include_router(stream_router, prefix="/api/v1", tags=["Streaming"])