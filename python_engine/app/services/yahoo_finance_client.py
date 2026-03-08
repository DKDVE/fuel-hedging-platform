"""
Yahoo Finance client for real-time futures data.

This module provides async access to Yahoo Finance market data via the yfinance library.
Implements circuit breaker pattern, rate limiting, and graceful error handling.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass(frozen=True)
class MarketPrice:
    """Market price data point."""
    symbol: str
    price: float
    timestamp: datetime
    volume: Optional[int] = None
    change_percent: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    source: str = "yahoo_finance"


class RateLimiter:
    """Simple token bucket rate limiter."""
    
    def __init__(self, max_requests: int, time_window_seconds: int = 3600):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window_seconds: Time window in seconds (default 1 hour)
        """
        self.max_requests = max_requests
        self.time_window = timedelta(seconds=time_window_seconds)
        self.requests: list[datetime] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Try to acquire a rate limit token.
        
        Returns:
            True if request allowed, False if rate limited
        """
        async with self._lock:
            now = datetime.utcnow()
            
            # Remove old requests outside time window
            cutoff = now - self.time_window
            self.requests = [req_time for req_time in self.requests if req_time > cutoff]
            
            # Check if we can make another request
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            logger.warning(
                "rate_limit_exceeded",
                current_requests=len(self.requests),
                max_requests=self.max_requests,
                time_window_seconds=self.time_window.total_seconds()
            )
            return False


class YahooFinanceCircuitBreaker:
    """Circuit breaker for Yahoo Finance API calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_duration: int = 60,
        half_open_max_requests: int = 3
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_duration: Seconds to wait before attempting half-open
            half_open_max_requests: Max requests to test in half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout_duration = timeout_duration
        self.half_open_max_requests = half_open_max_requests
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_attempts = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to call
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        async with self._lock:
            # Check if circuit should transition from OPEN to HALF_OPEN
            if self.state == CircuitState.OPEN:
                if self.last_failure_time:
                    elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                    if elapsed >= self.timeout_duration:
                        logger.info("circuit_breaker_transitioning_to_half_open")
                        self.state = CircuitState.HALF_OPEN
                        self.half_open_attempts = 0
                    else:
                        raise Exception(f"Circuit breaker OPEN - retry in {self.timeout_duration - elapsed:.0f}s")
            
            # Reject if circuit is still OPEN
            if self.state == CircuitState.OPEN:
                raise Exception("Circuit breaker OPEN - service unavailable")
        
        # Execute the function
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise e
    
    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_attempts += 1
                if self.half_open_attempts >= self.half_open_max_requests:
                    logger.info("circuit_breaker_closing_after_recovery")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.half_open_attempts = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0
    
    async def _on_failure(self):
        """Handle failed call."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.state == CircuitState.HALF_OPEN:
                logger.warning("circuit_breaker_reopening_after_half_open_failure")
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.failure_threshold:
                logger.warning(
                    "circuit_breaker_opening",
                    failure_count=self.failure_count,
                    threshold=self.failure_threshold
                )
                self.state = CircuitState.OPEN


class YahooFinanceClient:
    """
    Yahoo Finance API client for real-time futures prices.
    
    Provides async access to market data with:
    - Circuit breaker pattern for reliability
    - Rate limiting to respect service limits
    - Caching to reduce API calls
    - Graceful error handling
    """
    
    # Ticker symbol mappings
    TICKER_MAP = {
        'heating_oil': 'HO=F',      # NYMEX Heating Oil Futures
        'brent_crude': 'BZ=F',      # ICE Brent Crude Futures
        'wti_crude': 'CL=F',        # NYMEX WTI Crude Futures
        'rbob_gasoline': 'RB=F',    # NYMEX RBOB Gasoline (proxy for jet fuel)
    }
    
    def __init__(
        self,
        max_requests_per_hour: int = 100,
        cache_ttl_seconds: int = 60,
        enable_caching: bool = True
    ):
        """
        Initialize Yahoo Finance client.
        
        Args:
            max_requests_per_hour: Rate limit for API calls
            cache_ttl_seconds: How long to cache prices
            enable_caching: Whether to use caching
        """
        self.rate_limiter = RateLimiter(max_requests_per_hour)
        self.circuit_breaker = YahooFinanceCircuitBreaker()
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.enable_caching = enable_caching
        
        # Simple in-memory cache
        self._cache: Dict[str, tuple[MarketPrice, datetime]] = {}
        self._cache_lock = asyncio.Lock()
        
        logger.info(
            "yahoo_finance_client_initialized",
            max_requests_per_hour=max_requests_per_hour,
            cache_ttl_seconds=cache_ttl_seconds,
            enable_caching=enable_caching
        )
    
    async def get_price(
        self,
        instrument: str,
        use_cache: bool = True
    ) -> Optional[MarketPrice]:
        """
        Get latest price for an instrument.
        
        Args:
            instrument: Instrument name (e.g., 'heating_oil')
            use_cache: Whether to use cached data if available
            
        Returns:
            MarketPrice if successful, None otherwise
        """
        # Check cache first
        if use_cache and self.enable_caching:
            cached = await self._get_from_cache(instrument)
            if cached:
                logger.debug("yahoo_finance_cache_hit", instrument=instrument)
                return cached
        
        # Get ticker symbol
        ticker = self.TICKER_MAP.get(instrument)
        if not ticker:
            logger.error("unknown_instrument", instrument=instrument)
            return None
        
        # Check rate limit
        if not await self.rate_limiter.acquire():
            logger.warning("yahoo_finance_rate_limited", instrument=instrument)
            # Return cached data even if stale
            return await self._get_from_cache(instrument, ignore_ttl=True)
        
        try:
            # Fetch data with circuit breaker
            price_data = await self.circuit_breaker.call(
                self._fetch_ticker_data,
                ticker
            )
            
            if price_data:
                # Cache the result
                if self.enable_caching:
                    await self._add_to_cache(instrument, price_data)
                
                logger.info(
                    "yahoo_finance_price_fetched",
                    instrument=instrument,
                    ticker=ticker,
                    price=price_data.price
                )
                return price_data
            
        except Exception as e:
            logger.error(
                "yahoo_finance_fetch_failed",
                instrument=instrument,
                ticker=ticker,
                error=str(e)
            )
        
        return None
    
    async def get_multiple_prices(
        self,
        instruments: list[str],
        use_cache: bool = True
    ) -> Dict[str, Optional[MarketPrice]]:
        """
        Get prices for multiple instruments concurrently.
        
        Args:
            instruments: List of instrument names
            use_cache: Whether to use cached data
            
        Returns:
            Dictionary mapping instrument name to price
        """
        tasks = [
            self.get_price(instrument, use_cache)
            for instrument in instruments
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            instrument: result if not isinstance(result, Exception) else None
            for instrument, result in zip(instruments, results)
        }
    
    async def _fetch_ticker_data(self, ticker: str) -> Optional[MarketPrice]:
        """
        Fetch data for a single ticker from Yahoo Finance.
        
        Args:
            ticker: Yahoo Finance ticker symbol
            
        Returns:
            MarketPrice if successful, None otherwise
        """
        try:
            # Import yfinance here to avoid issues if not installed
            import yfinance as yf
            
            # Run blocking call in executor to keep async
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, ticker)
            
            # Get fast info (this is much faster than .info)
            info = await loop.run_in_executor(None, lambda: ticker_obj.fast_info)
            
            # Extract price data
            current_price = info.get('lastPrice') or info.get('last_price')
            if not current_price:
                logger.warning("no_price_data_from_yahoo", ticker=ticker)
                return None
            
            # Get additional data if available
            previous_close = info.get('previousClose') or info.get('previous_close')
            change_percent = None
            if previous_close and previous_close > 0:
                change_percent = ((current_price - previous_close) / previous_close) * 100
            
            return MarketPrice(
                symbol=ticker,
                price=float(current_price),
                timestamp=datetime.utcnow(),
                change_percent=change_percent,
                source="yahoo_finance"
            )
            
        except ImportError:
            logger.error("yfinance_not_installed")
            raise Exception("yfinance library not installed. Run: pip install yfinance")
        except Exception as e:
            logger.error("yahoo_finance_api_error", ticker=ticker, error=str(e))
            raise
    
    async def _get_from_cache(
        self,
        instrument: str,
        ignore_ttl: bool = False
    ) -> Optional[MarketPrice]:
        """
        Get price from cache if available and fresh.
        
        Args:
            instrument: Instrument name
            ignore_ttl: If True, return cached data even if stale
            
        Returns:
            Cached MarketPrice if available, None otherwise
        """
        async with self._cache_lock:
            if instrument in self._cache:
                price, cached_at = self._cache[instrument]
                age = datetime.utcnow() - cached_at
                
                if ignore_ttl or age < self.cache_ttl:
                    return price
        
        return None
    
    async def _add_to_cache(self, instrument: str, price: MarketPrice):
        """Add price to cache."""
        async with self._cache_lock:
            self._cache[instrument] = (price, datetime.utcnow())
    
    async def clear_cache(self):
        """Clear all cached prices."""
        async with self._cache_lock:
            self._cache.clear()
            logger.info("yahoo_finance_cache_cleared")
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the client.
        
        Returns:
            Dictionary with health metrics
        """
        return {
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "circuit_breaker_failures": self.circuit_breaker.failure_count,
            "cache_size": len(self._cache),
            "rate_limiter_requests": len(self.rate_limiter.requests),
            "rate_limiter_max": self.rate_limiter.max_requests,
        }


# Singleton instance (optional - can also instantiate per use)
_yahoo_client: Optional[YahooFinanceClient] = None


def get_yahoo_finance_client(
    max_requests_per_hour: int = 100,
    cache_ttl_seconds: int = 60
) -> YahooFinanceClient:
    """
    Get or create singleton Yahoo Finance client.
    
    Args:
        max_requests_per_hour: Rate limit
        cache_ttl_seconds: Cache TTL
        
    Returns:
        YahooFinanceClient instance
    """
    global _yahoo_client
    
    if _yahoo_client is None:
        _yahoo_client = YahooFinanceClient(
            max_requests_per_hour=max_requests_per_hour,
            cache_ttl_seconds=cache_ttl_seconds
        )
    
    return _yahoo_client
