"""Base API client with circuit breaker and retry logic."""

import asyncio
import structlog
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.exceptions import DataIngestionError

log = structlog.get_logger()


@dataclass
class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""

    failure_threshold: int = 3
    recovery_timeout_seconds: int = 60
    consecutive_failures: int = 0
    opened_at: datetime | None = None
    state: str = "CLOSED"  # 'CLOSED' | 'OPEN' | 'HALF_OPEN'

    def record_failure(self) -> None:
        """Record a failed request."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.state = "OPEN"
            self.opened_at = datetime.now(timezone.utc)

    def record_success(self) -> None:
        """Record a successful request."""
        self.consecutive_failures = 0
        self.state = "CLOSED"
        self.opened_at = None

    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.state == "OPEN" and self.opened_at:
            elapsed = (datetime.now(timezone.utc) - self.opened_at).total_seconds()
            if elapsed >= self.recovery_timeout_seconds:
                self.state = "HALF_OPEN"
                return False
        return self.state == "OPEN"


class BaseAPIClient:
    """Base client for external API interactions with retry logic."""

    def __init__(self, api_key: str | None, base_url: str, timeout: int = 15) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self._circuit = CircuitBreaker()
        self._client_name = self.__class__.__name__

    async def _fetch(
        self, method: str, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute HTTP request with retries and circuit breaker."""
        if self._circuit.is_open():
            raise DataIngestionError(
                f"{self._client_name} circuit breaker is OPEN — skipping request",
                source=self._client_name,
            )

        delays = [1, 2, 4]
        last_error: Exception | None = None

        for attempt, delay in enumerate(delays, start=1):
            try:
                start = datetime.now(timezone.utc)
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method, f"{self.base_url}{path}", params=params
                    )
                    duration_ms = (
                        datetime.now(timezone.utc) - start
                    ).total_seconds() * 1000
                    log.info(
                        "api_request",
                        client=self._client_name,
                        method=method,
                        path=path,
                        status=response.status_code,
                        duration_ms=round(duration_ms, 1),
                        attempt=attempt,
                    )
                    response.raise_for_status()
                    self._circuit.record_success()
                    return response.json()
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_error = e
                self._circuit.record_failure()
                log.warning(
                    "api_request_failed",
                    client=self._client_name,
                    attempt=attempt,
                    error=str(e),
                )
                if attempt < len(delays):
                    await asyncio.sleep(delay)

        raise DataIngestionError(
            f"{self._client_name} failed after {len(delays)} attempts: {last_error}",
            source=self._client_name,
        )
