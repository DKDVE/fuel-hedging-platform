"""
Application configuration.
Loads from environment variables with sensible defaults.
"""

import os
from typing import Optional


def _env_bool(key: str, default: bool) -> bool:
    """Parse boolean environment variables safely."""
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    """Parse integer environment variables with safe fallback."""
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


class Settings:
    """Application settings loaded from environment variables."""

    # Database — no default with real credentials; use .env
    # Treat empty string as unset (GitHub Actions passes empty when secret missing)
    # Render/Heroku provide postgres:// or postgresql:// — asyncpg requires postgresql+asyncpg://
    _db_url = os.getenv("DATABASE_URL", "").strip()
    if _db_url and "postgresql+asyncpg" not in _db_url:
        for prefix in ("postgresql://", "postgres://"):
            if _db_url.startswith(prefix):
                _db_url = "postgresql+asyncpg://" + _db_url[len(prefix) :]
                break
    DATABASE_URL: str = (
        _db_url
        if _db_url
        else "postgresql+asyncpg://hedgeuser:CHANGE_ME@localhost:5432/hedge_db"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # JWT Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-min-32-chars")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "240"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Aliases for auth module
    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.SECRET_KEY

    @property
    def JWT_ALGORITHM(self) -> str:
        return self.ALGORITHM

    # Real-time Data Layer Configuration
    USE_LIVE_FEED: bool = os.getenv("USE_LIVE_FEED", "true").lower() == "true"
    MASSIVE_API_KEY: Optional[str] = os.getenv("MASSIVE_API_KEY", None)
    EIA_API_KEY: Optional[str] = os.getenv("EIA_API_KEY", None)
    CME_API_KEY: Optional[str] = os.getenv("CME_API_KEY", None)
    ICE_API_KEY: Optional[str] = os.getenv("ICE_API_KEY", None)
    
    # Data Source Priority (when USE_LIVE_FEED=true)
    USE_YAHOO_FINANCE: bool = os.getenv("USE_YAHOO_FINANCE", "true").lower() == "true"
    USE_EIA_API: bool = os.getenv("USE_EIA_API", "true").lower() == "true"
    USE_SIMULATION_FALLBACK: bool = os.getenv("USE_SIMULATION_FALLBACK", "true").lower() == "true"
    
    # Yahoo Finance Configuration (stay under ~100 req/hr to avoid rate limit/ban)
    YAHOO_FINANCE_UPDATE_INTERVAL: int = int(os.getenv("YAHOO_FINANCE_UPDATE_INTERVAL", "300"))
    YAHOO_FINANCE_CACHE_TTL: int = int(os.getenv("YAHOO_FINANCE_CACHE_TTL", "300"))
    MAX_YAHOO_REQUESTS_PER_HOUR: int = int(os.getenv("MAX_YAHOO_REQUESTS_PER_HOUR", "100"))
    
    # EIA API Configuration
    EIA_UPDATE_INTERVAL: int = int(os.getenv("EIA_UPDATE_INTERVAL", "86400"))  # Once per day
    MAX_EIA_REQUESTS_PER_HOUR: int = int(os.getenv("MAX_EIA_REQUESTS_PER_HOUR", "150"))

    # Simulation parameters (used when USE_LIVE_FEED=false)
    SIMULATION_INTERVAL_SECONDS: float = float(os.getenv("SIMULATION_INTERVAL_SECONDS", "2.0"))
    SIMULATION_INITIAL_PRICE: float = float(os.getenv("SIMULATION_INITIAL_PRICE", "85.0"))
    SIMULATION_VOLATILITY: float = float(os.getenv("SIMULATION_VOLATILITY", "0.02"))

    # n8n Integration
    # Demand-strategy advisor webhook (separate from pipeline trigger webhook).
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/fuel-hedge-advisor")
    # Preferred explicit URL for demand-strategy workflow to avoid accidental cross-routing.
    N8N_DEMAND_STRATEGY_URL: str = os.getenv("N8N_DEMAND_STRATEGY_URL", "").strip()
    N8N_INTERNAL_URL: str = os.getenv("N8N_INTERNAL_URL", "http://n8n:5678")
    N8N_TRIGGER_PATH: str = os.getenv("N8N_TRIGGER_PATH", "/webhook/fuel-hedge-trigger")
    # Full URL override — use when N8N_INTERNAL_URL hostname fails to resolve (e.g. Render)
    N8N_TRIGGER_URL: str = os.getenv("N8N_TRIGGER_URL", "").strip()
    N8N_WEBHOOK_SECRET: str = os.getenv("N8N_WEBHOOK_SECRET", "change_me_in_production")
    N8N_REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("N8N_REQUEST_TIMEOUT_SECONDS", "20"))
    N8N_REQUEST_MAX_RETRIES: int = _env_int("N8N_REQUEST_MAX_RETRIES", 2)
    N8N_REQUEST_RETRY_BACKOFF_SECONDS: float = float(
        os.getenv("N8N_REQUEST_RETRY_BACKOFF_SECONDS", "1.5")
    )
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip()
    GROQ_DASHBOARD_MODEL: str = os.getenv("GROQ_DASHBOARD_MODEL", "llama-3.3-70b-versatile").strip()

    # API Configuration
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    API_INTERNAL_URL: str = os.getenv("API_INTERNAL_URL", "http://api:8000")
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000"
    ).split(",")
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    REPORTING_ENTITY_NAME: str = os.getenv("REPORTING_ENTITY_NAME", "Airline Operations Ltd").strip()
    REPORTING_CURRENCY: str = os.getenv("REPORTING_CURRENCY", "USD").strip()
    IFRS9_REPORT_V2: bool = _env_bool("IFRS9_REPORT_V2", True)

    # Domain constants (from .cursorrules)
    HR_HARD_CAP: float = 0.80
    HR_SOFT_WARN: float = 0.70
    COLLATERAL_LIMIT: float = 0.15
    IFRS9_R2_MIN_PROSPECTIVE: float = 0.80
    IFRS9_R2_WARN: float = 0.65
    IFRS9_RETRO_LOW: float = 0.80
    IFRS9_RETRO_HIGH: float = 1.25
    MAPE_TARGET: float = 8.0
    MAPE_ALERT: float = 10.0
    VAR_REDUCTION_TARGET: float = 0.40
    MAX_COVERAGE_RATIO: float = 1.10
    PIPELINE_TIMEOUT_MINUTES: int = 15
    PIPELINE_MIN_OBSERVATIONS: int = _env_int("PIPELINE_MIN_OBSERVATIONS", 252)
    PIPELINE_LOOKBACK_DAYS: int = _env_int("PIPELINE_LOOKBACK_DAYS", 1460)

    # Scheduler (Render-safe defaults)
    SCHEDULER_ENABLED: bool = _env_bool("SCHEDULER_ENABLED", True)
    SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE", "UTC").strip() or "UTC"
    SCHEDULER_DAILY_HOUR: int = _env_int("SCHEDULER_DAILY_HOUR", 0)
    SCHEDULER_DAILY_MINUTE: int = _env_int("SCHEDULER_DAILY_MINUTE", 0)
    SCHEDULER_MISFIRE_GRACE_SECONDS: int = _env_int("SCHEDULER_MISFIRE_GRACE_SECONDS", 21600)
    SCHEDULER_CATCHUP_ON_STARTUP: bool = _env_bool("SCHEDULER_CATCHUP_ON_STARTUP", True)

    # Inference: TensorFlow + LSTM uses ~200–400MB+ RAM. Default off (ARIMA + XGBoost only).
    # Set ENABLE_LSTM_INFERENCE=true when server has enough RAM (e.g. 1GB+).
    ENABLE_LSTM_INFERENCE: bool = os.getenv("ENABLE_LSTM_INFERENCE", "false").lower() == "true"


settings = Settings()


def get_settings() -> Settings:
    """Dependency for FastAPI routes to access settings."""
    return settings
