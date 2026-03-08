"""External API clients for market data ingestion.

Implements circuit breaker pattern for resilience.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import httpx
import structlog
from decimal import Decimal

from app.config import get_settings
from app.exceptions import DataIngestionError

settings = get_settings()
logger = structlog.get_logger()


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker for external API calls.

    Prevents cascade failures by opening circuit after threshold failures.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        half_open_attempts: int = 1,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Consecutive failures before opening circuit
            timeout_seconds: Seconds to wait before attempting recovery
            half_open_attempts: Number of test requests in half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_attempts = half_open_attempts

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_successes = 0

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            # Check if timeout elapsed
            if (
                self.last_failure_time
                and datetime.utcnow() - self.last_failure_time
                > timedelta(seconds=self.timeout_seconds)
            ):
                logger.info("circuit_breaker_half_open")
                self.state = CircuitState.HALF_OPEN
                self.half_open_successes = 0
            else:
                raise DataIngestionError(
                    message="Circuit breaker is OPEN",
                    source="circuit_breaker",
                    context={
                        "failure_count": self.failure_count,
                        "last_failure": self.last_failure_time.isoformat()
                        if self.last_failure_time
                        else None,
                    },
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.half_open_attempts:
                logger.info("circuit_breaker_closed")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("circuit_breaker_opened_from_half_open")
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            logger.warning(
                "circuit_breaker_opened",
                failure_count=self.failure_count,
            )
            self.state = CircuitState.OPEN


class EIAAPIClient:
    """U.S. Energy Information Administration API client."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize EIA client.

        Args:
            api_key: EIA API key (or from settings)
        """
        self.api_key = api_key or settings.EIA_API_KEY
        self.base_url = "https://api.eia.gov/v2"
        self.circuit_breaker = CircuitBreaker()

        if not self.api_key:
            logger.warning("eia_api_key_missing")

    async def fetch_jet_fuel_price(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[dict]:
        """Fetch jet fuel spot prices from EIA.

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            List of price records

        Raises:
            DataIngestionError: If API call fails
        """
        if not self.api_key:
            raise DataIngestionError(
                message="EIA API key not configured",
                source="eia_api",
            )

        # EIA series ID for jet fuel (example - verify actual series)
        series_id = "PET.EER_EPJK_PF4_RGC_DPG.D"

        params = {
            "api_key": self.api_key,
            "frequency": "daily",
        }

        if start_date:
            params["start"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["end"] = end_date.strftime("%Y-%m-%d")

        url = f"{self.base_url}/seriesid/{series_id}"

        async def _fetch():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()

        try:
            data = await self.circuit_breaker.call(_fetch)
            logger.info("eia_fetch_success", records=len(data.get("data", [])))
            return data.get("data", [])
        except Exception as e:
            raise DataIngestionError(
                message=f"EIA API call failed: {str(e)}",
                source="eia_api",
                context={"error": str(e)},
            )


class CMEAPIClient:
    """Chicago Mercantile Exchange API client for futures prices."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize CME client.

        Args:
            api_key: CME API key (or from settings)
        """
        self.api_key = api_key or settings.CME_API_KEY
        self.base_url = "https://www.cmegroup.com/api/v1"
        self.circuit_breaker = CircuitBreaker()

        if not self.api_key:
            logger.warning("cme_api_key_missing")

    async def fetch_heating_oil_futures(
        self,
        contract_month: Optional[str] = None,
    ) -> dict:
        """Fetch heating oil futures from CME.

        Args:
            contract_month: Contract month (e.g., 'H24' for March 2024)

        Returns:
            Futures price data

        Raises:
            DataIngestionError: If API call fails
        """
        if not self.api_key:
            raise DataIngestionError(
                message="CME API key not configured",
                source="cme_api",
            )

        # CME product code for heating oil (example)
        product_code = "HO"

        params = {
            "api_key": self.api_key,
            "product": product_code,
        }

        if contract_month:
            params["contract"] = contract_month

        url = f"{self.base_url}/quotes"

        async def _fetch():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()

        try:
            data = await self.circuit_breaker.call(_fetch)
            logger.info("cme_fetch_success")
            return data
        except Exception as e:
            raise DataIngestionError(
                message=f"CME API call failed: {str(e)}",
                source="cme_api",
                context={"error": str(e)},
            )


class ICEAPIClient:
    """Intercontinental Exchange API client for Brent/WTI crude."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize ICE client.

        Args:
            api_key: ICE API key (or from settings)
        """
        self.api_key = api_key or settings.ICE_API_KEY
        self.base_url = "https://api.ice.com/v1"
        self.circuit_breaker = CircuitBreaker()

        if not self.api_key:
            logger.warning("ice_api_key_missing")

    async def fetch_brent_crude(self) -> dict:
        """Fetch Brent crude futures from ICE.

        Returns:
            Brent crude price data

        Raises:
            DataIngestionError: If API call fails
        """
        if not self.api_key:
            raise DataIngestionError(
                message="ICE API key not configured",
                source="ice_api",
            )

        url = f"{self.base_url}/market-data/brent-crude"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async def _fetch():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()

        try:
            data = await self.circuit_breaker.call(_fetch)
            logger.info("ice_fetch_success")
            return data
        except Exception as e:
            raise DataIngestionError(
                message=f"ICE API call failed: {str(e)}",
                source="ice_api",
                context={"error": str(e)},
            )
