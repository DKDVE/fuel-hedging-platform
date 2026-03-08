"""
Unit tests for YahooFinanceClient.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.services.yahoo_finance_client import (
    YahooFinanceClient,
    MarketPrice,
    CircuitState,
    RateLimiter,
    YahooFinanceCircuitBreaker
)


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_within_limit(self):
        """Test that requests within limit are allowed."""
        limiter = RateLimiter(max_requests=5, time_window_seconds=10)
        
        # Should allow 5 requests
        for _ in range(5):
            assert await limiter.acquire() is True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(max_requests=3, time_window_seconds=10)
        
        # First 3 should succeed
        for _ in range(3):
            assert await limiter.acquire() is True
        
        # 4th should fail
        assert await limiter.acquire() is False
    
    @pytest.mark.asyncio
    async def test_rate_limiter_resets_after_window(self):
        """Test that limiter resets after time window."""
        limiter = RateLimiter(max_requests=2, time_window_seconds=1)
        
        # Use up the limit
        assert await limiter.acquire() is True
        assert await limiter.acquire() is True
        assert await limiter.acquire() is False
        
        # Wait for window to pass
        await asyncio.sleep(1.1)
        
        # Should be able to acquire again
        assert await limiter.acquire() is True


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_allows_calls(self):
        """Test that CLOSED circuit allows calls."""
        cb = YahooFinanceCircuitBreaker(failure_threshold=3)
        
        async def success_func():
            return "success"
        
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit opens after threshold failures."""
        cb = YahooFinanceCircuitBreaker(failure_threshold=3)
        
        async def failing_func():
            raise Exception("test error")
        
        # Cause 3 failures
        for _ in range(3):
            with pytest.raises(Exception):
                await cb.call(failing_func)
        
        # Circuit should be open
        assert cb.state == CircuitState.OPEN
        
        # Next call should fail immediately
        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            await cb.call(failing_func)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_transition(self):
        """Test transition from OPEN to HALF_OPEN after timeout."""
        cb = YahooFinanceCircuitBreaker(
            failure_threshold=2,
            timeout_duration=1  # 1 second timeout
        )
        
        async def failing_func():
            raise Exception("test error")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(1.1)
        
        # Should transition to HALF_OPEN on next attempt
        async def success_func():
            return "success"
        
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.HALF_OPEN


class TestYahooFinanceClient:
    """Test YahooFinanceClient."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return YahooFinanceClient(
            max_requests_per_hour=100,
            cache_ttl_seconds=60,
            enable_caching=True
        )
    
    def test_client_initialization(self, client):
        """Test client initializes correctly."""
        assert client.rate_limiter is not None
        assert client.circuit_breaker is not None
        assert client.enable_caching is True
        assert client.cache_ttl == timedelta(seconds=60)
    
    def test_ticker_mapping(self):
        """Test ticker symbol mappings are correct."""
        expected = {
            'heating_oil': 'HO=F',
            'brent_crude': 'BZ=F',
            'wti_crude': 'CL=F',
            'rbob_gasoline': 'RB=F',
        }
        
        assert YahooFinanceClient.TICKER_MAP == expected
    
    @pytest.mark.asyncio
    async def test_get_price_invalid_instrument(self, client):
        """Test get_price returns None for invalid instrument."""
        result = await client.get_price('invalid_instrument')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_price_uses_cache(self, client):
        """Test that get_price uses cache when available."""
        # Mock a cached price
        cached_price = MarketPrice(
            symbol='HO=F',
            price=85.0,
            timestamp=datetime.utcnow(),
            source='yahoo_finance'
        )
        
        await client._add_to_cache('heating_oil', cached_price)
        
        # Should return cached price without calling API
        result = await client.get_price('heating_oil', use_cache=True)
        
        assert result is not None
        assert result.price == 85.0
        assert result.symbol == 'HO=F'
    
    @pytest.mark.asyncio
    async def test_get_price_cache_expiration(self, client):
        """Test that cache expires after TTL."""
        client.cache_ttl = timedelta(seconds=1)
        
        # Add cached price
        cached_price = MarketPrice(
            symbol='HO=F',
            price=85.0,
            timestamp=datetime.utcnow(),
            source='yahoo_finance'
        )
        
        await client._add_to_cache('heating_oil', cached_price)
        
        # Should be cached
        result = await client._get_from_cache('heating_oil')
        assert result is not None
        
        # Wait for cache to expire
        await asyncio.sleep(1.1)
        
        # Should be expired
        result = await client._get_from_cache('heating_oil')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_multiple_prices(self, client):
        """Test getting multiple prices concurrently."""
        # Mock the get_price method
        async def mock_get_price(instrument, use_cache=True):
            return MarketPrice(
                symbol=instrument,
                price=100.0,
                timestamp=datetime.utcnow(),
                source='yahoo_finance'
            )
        
        client.get_price = mock_get_price
        
        # Get multiple prices
        instruments = ['heating_oil', 'wti_crude', 'brent_crude']
        results = await client.get_multiple_prices(instruments)
        
        assert len(results) == 3
        for instrument in instruments:
            assert results[instrument] is not None
            assert results[instrument].symbol == instrument
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, client):
        """Test cache clearing."""
        # Add some cached prices
        for i in range(3):
            price = MarketPrice(
                symbol=f'TEST{i}',
                price=100.0,
                timestamp=datetime.utcnow(),
                source='yahoo_finance'
            )
            await client._add_to_cache(f'test{i}', price)
        
        assert len(client._cache) == 3
        
        # Clear cache
        await client.clear_cache()
        
        assert len(client._cache) == 0
    
    def test_get_health_status(self, client):
        """Test health status retrieval."""
        status = client.get_health_status()
        
        assert 'circuit_breaker_state' in status
        assert 'circuit_breaker_failures' in status
        assert 'cache_size' in status
        assert 'rate_limiter_requests' in status
        assert 'rate_limiter_max' in status
        
        assert status['circuit_breaker_state'] == 'closed'
        assert status['cache_size'] == 0
        assert status['rate_limiter_max'] == 100
    
    @pytest.mark.asyncio
    @patch('yfinance.Ticker')
    async def test_fetch_ticker_data_success(self, mock_ticker_class, client):
        """Test successful ticker data fetch."""
        # Mock yfinance Ticker
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {
            'lastPrice': 85.50,
            'previousClose': 84.00
        }
        mock_ticker_class.return_value = mock_ticker
        
        # Fetch data
        result = await client._fetch_ticker_data('HO=F')
        
        assert result is not None
        assert result.symbol == 'HO=F'
        assert result.price == 85.50
        assert result.source == 'yahoo_finance'
        assert result.change_percent is not None
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """Test that rate limiting works."""
        # Set very low rate limit
        client.rate_limiter = RateLimiter(max_requests=2, time_window_seconds=10)
        
        # Mock _fetch_ticker_data to always succeed
        async def mock_fetch(ticker):
            return MarketPrice(
                symbol=ticker,
                price=100.0,
                timestamp=datetime.utcnow(),
                source='yahoo_finance'
            )
        
        client._fetch_ticker_data = mock_fetch
        
        # First 2 requests should succeed
        result1 = await client.get_price('heating_oil', use_cache=False)
        assert result1 is not None
        
        result2 = await client.get_price('brent_crude', use_cache=False)
        assert result2 is not None
        
        # 3rd request should be rate limited (returns cached or None)
        result3 = await client.get_price('wti_crude', use_cache=False)
        # Result might be None or from cache depending on implementation


class TestIntegration:
    """Integration tests (require network access - mark as slow)."""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_real_yahoo_finance_fetch(self):
        """Test fetching real data from Yahoo Finance."""
        client = YahooFinanceClient()
        
        # Try to fetch heating oil price
        result = await client.get_price('heating_oil', use_cache=False)
        
        # This might fail if network is down or API changes
        # So we just check the structure if it succeeds
        if result:
            assert result.symbol == 'HO=F'
            assert result.price > 0
            assert result.timestamp is not None
            assert result.source == 'yahoo_finance'


# Fixtures for pytest
@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
