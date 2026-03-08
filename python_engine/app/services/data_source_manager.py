"""
Data Source Manager for intelligent routing between Yahoo Finance, EIA API, and simulation.

This module provides a unified interface that automatically selects the best data source
based on availability, data quality, and configured priorities.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from dataclasses import dataclass
from enum import Enum
import structlog

from .yahoo_finance_client import YahooFinanceClient, MarketPrice
from app.config import settings

logger = structlog.get_logger(__name__)


class DataSourceType(str, Enum):
    """Available data sources."""
    YAHOO_FINANCE = "yahoo_finance"
    EIA_API = "eia_api"
    SIMULATION = "simulation"


class SourcePriority(str, Enum):
    """Source priority levels."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    FALLBACK = "fallback"


@dataclass
class PriceWithMetadata:
    """Price data with source metadata."""
    instrument: str
    price: float
    timestamp: datetime
    source: DataSourceType
    priority: SourcePriority
    confidence: float  # 0.0 to 1.0
    change_percent: Optional[float] = None
    volume: Optional[int] = None


@dataclass
class SourceHealth:
    """Health status for a data source."""
    source: DataSourceType
    available: bool
    success_rate: float  # Last 100 requests
    avg_latency_ms: float
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    failure_reason: Optional[str]


class DataSourceManager:
    """
    Intelligently routes price requests to the best available data source.
    
    Priority order (configurable):
    1. Yahoo Finance - Real-time futures (15-min delay)
    2. EIA API - Official spot prices (daily, 1-day lag)
    3. Simulation - Always available fallback
    """
    
    # Instrument to source mapping (Yahoo first for real-time; EIA for official jet fuel)
    INSTRUMENT_SOURCE_MAP = {
        'heating_oil': [DataSourceType.YAHOO_FINANCE, DataSourceType.SIMULATION],
        'brent_crude': [DataSourceType.YAHOO_FINANCE, DataSourceType.SIMULATION],
        'wti_crude': [DataSourceType.YAHOO_FINANCE, DataSourceType.SIMULATION],
        'jet_fuel': [DataSourceType.YAHOO_FINANCE, DataSourceType.EIA_API, DataSourceType.SIMULATION],
    }

    # Typical jet fuel premium over heating oil (USD/bbl) - used when Yahoo is proxy
    JET_FUEL_CRACK_SPREAD_BBL = 6.0
    
    def __init__(
        self,
        yahoo_client: Optional[YahooFinanceClient] = None,
        eia_client=None,  # Type hint omitted as it's optional
        simulation_enabled: bool = True
    ):
        """
        Initialize data source manager.
        
        Args:
            yahoo_client: Yahoo Finance client instance
            eia_client: EIA API client instance
            simulation_enabled: Whether to allow simulation fallback
        """
        self.yahoo_client = yahoo_client
        self.eia_client = eia_client
        self.simulation_enabled = simulation_enabled
        
        # Health tracking
        self.source_health: Dict[DataSourceType, SourceHealth] = {
            DataSourceType.YAHOO_FINANCE: SourceHealth(
                source=DataSourceType.YAHOO_FINANCE,
                available=True,
                success_rate=1.0,
                avg_latency_ms=0.0,
                last_success=None,
                last_failure=None,
                failure_reason=None
            ),
            DataSourceType.EIA_API: SourceHealth(
                source=DataSourceType.EIA_API,
                available=True,
                success_rate=1.0,
                avg_latency_ms=0.0,
                last_success=None,
                last_failure=None,
                failure_reason=None
            ),
            DataSourceType.SIMULATION: SourceHealth(
                source=DataSourceType.SIMULATION,
                available=simulation_enabled,
                success_rate=1.0,
                avg_latency_ms=0.0,
                last_success=None,
                last_failure=None,
                failure_reason=None
            ),
        }
        
        # Success/failure tracking (circular buffer)
        self._request_history: Dict[DataSourceType, List[bool]] = {
            source: [] for source in DataSourceType
        }
        self._max_history = 100
        
        logger.info(
            "data_source_manager_initialized",
            yahoo_enabled=yahoo_client is not None,
            eia_enabled=eia_client is not None,
            simulation_enabled=simulation_enabled
        )
    
    async def get_price(
        self,
        instrument: str,
        preferred_source: Optional[DataSourceType] = None
    ) -> Optional[PriceWithMetadata]:
        """
        Get latest price for an instrument from the best available source.
        
        Args:
            instrument: Instrument name (e.g., 'heating_oil')
            preferred_source: Override automatic source selection
            
        Returns:
            PriceWithMetadata if successful, None otherwise
        """
        # Get ordered list of sources to try
        if preferred_source:
            sources_to_try = [preferred_source]
        else:
            sources_to_try = self._get_source_priority(instrument)
        
        # Try each source in order
        for source in sources_to_try:
            try:
                price = await self._fetch_from_source(instrument, source)
                if price:
                    self._record_success(source)
                    logger.info(
                        "price_fetched_successfully",
                        instrument=instrument,
                        source=source.value,
                        price=price.price
                    )
                    return price
                    
            except Exception as e:
                self._record_failure(source, str(e))
                logger.warning(
                    "source_fetch_failed_trying_next",
                    instrument=instrument,
                    source=source.value,
                    error=str(e)
                )
                continue
        
        # All sources failed
        logger.error(
            "all_sources_failed",
            instrument=instrument,
            sources_tried=[s.value for s in sources_to_try]
        )
        return None
    
    async def get_multiple_prices(
        self,
        instruments: List[str]
    ) -> Dict[str, Optional[PriceWithMetadata]]:
        """
        Get prices for multiple instruments concurrently.
        
        Args:
            instruments: List of instrument names
            
        Returns:
            Dictionary mapping instrument to price
        """
        tasks = [self.get_price(instrument) for instrument in instruments]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            instrument: result if not isinstance(result, Exception) else None
            for instrument, result in zip(instruments, results)
        }
    
    def _get_source_priority(self, instrument: str) -> List[DataSourceType]:
        """
        Get ordered list of sources to try for an instrument.
        
        Args:
            instrument: Instrument name
            
        Returns:
            List of data sources in priority order
        """
        # Get configured sources for this instrument
        configured_sources = self.INSTRUMENT_SOURCE_MAP.get(
            instrument,
            [DataSourceType.SIMULATION]
        )
        
        # Filter based on availability and settings
        available_sources = []
        
        for source in configured_sources:
            if source == DataSourceType.YAHOO_FINANCE:
                if settings.USE_YAHOO_FINANCE and self.yahoo_client:
                    available_sources.append(source)
                    
            elif source == DataSourceType.EIA_API:
                if settings.USE_EIA_API and self.eia_client:
                    available_sources.append(source)
                    
            elif source == DataSourceType.SIMULATION:
                if self.simulation_enabled and settings.USE_SIMULATION_FALLBACK:
                    available_sources.append(source)
        
        return available_sources
    
    async def _fetch_from_source(
        self,
        instrument: str,
        source: DataSourceType
    ) -> Optional[PriceWithMetadata]:
        """
        Fetch price from a specific source.
        
        Args:
            instrument: Instrument name
            source: Data source to use
            
        Returns:
            PriceWithMetadata if successful, None otherwise
        """
        start_time = datetime.utcnow()
        
        try:
            if source == DataSourceType.YAHOO_FINANCE:
                result = await self._fetch_yahoo_finance(instrument)
                
            elif source == DataSourceType.EIA_API:
                result = await self._fetch_eia(instrument)
                
            elif source == DataSourceType.SIMULATION:
                result = await self._fetch_simulation(instrument)
                
            else:
                logger.error("unknown_data_source", source=source.value)
                return None
            
            # Update latency
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_latency(source, latency_ms)
            
            return result
            
        except Exception as e:
            logger.error(
                "source_fetch_error",
                instrument=instrument,
                source=source.value,
                error=str(e)
            )
            raise
    
    async def _fetch_yahoo_finance(self, instrument: str) -> Optional[PriceWithMetadata]:
        """Fetch from Yahoo Finance. Jet fuel uses heating oil (HO=F) + crack spread as proxy."""
        if not self.yahoo_client:
            return None

        # Yahoo has no direct jet fuel; use heating oil + crack spread as proxy
        if instrument == "jet_fuel":
            ho_data = await self.yahoo_client.get_price("heating_oil")
            if not ho_data:
                return None
            jet_price = ho_data.price + self.JET_FUEL_CRACK_SPREAD_BBL
            return PriceWithMetadata(
                instrument=instrument,
                price=jet_price,
                timestamp=ho_data.timestamp,
                source=DataSourceType.YAHOO_FINANCE,
                priority=SourcePriority.PRIMARY,
                confidence=0.90,  # Proxy, not direct
                change_percent=ho_data.change_percent,
                volume=ho_data.volume,
            )

        price_data = await self.yahoo_client.get_price(instrument)
        if not price_data:
            return None

        return PriceWithMetadata(
            instrument=instrument,
            price=price_data.price,
            timestamp=price_data.timestamp,
            source=DataSourceType.YAHOO_FINANCE,
            priority=SourcePriority.PRIMARY,
            confidence=0.95,  # High confidence for real-time data
            change_percent=price_data.change_percent,
            volume=price_data.volume,
        )
    
    async def _fetch_eia(self, instrument: str) -> Optional[PriceWithMetadata]:
        """Fetch from EIA API. EIA provides daily data (1-day lag). Cached per EIA_UPDATE_INTERVAL."""
        if not self.eia_client:
            return None

        # EIA returns jet_fuel_spot, wti_spot, brent_spot - map to our instruments
        eia_field_map = {
            "jet_fuel": ("jet_fuel_spot", lambda p: p.jet_fuel_spot),
            "wti_crude": ("wti_spot", lambda p: p.wti_spot),
            "brent_crude": ("brent_spot", lambda p: p.brent_spot),
        }
        if instrument not in eia_field_map:
            return None

        try:
            prices = await self.eia_client.get_latest_prices()
            _, extract = eia_field_map[instrument]
            price = extract(prices)
            return PriceWithMetadata(
                instrument=instrument,
                price=price,
                timestamp=datetime.utcnow(),  # EIA data is daily; we use now for display
                source=DataSourceType.EIA_API,
                priority=SourcePriority.SECONDARY,
                confidence=0.90,  # Official data but 1-day lag
                change_percent=None,
            )
        except Exception as e:
            logger.warning("eia_fetch_failed", instrument=instrument, error=str(e))
            raise
    
    async def _fetch_simulation(self, instrument: str) -> Optional[PriceWithMetadata]:
        """Fetch from simulation (always succeeds)."""
        # Import here to avoid circular dependency
        from random import gauss
        
        # Base prices (approximate real values)
        base_prices = {
            'jet_fuel': 2.85,       # $/gallon
            'heating_oil': 2.75,    # $/gallon
            'brent_crude': 85.0,    # $/barrel
            'wti_crude': 80.0,      # $/barrel
        }
        
        base_price = base_prices.get(instrument, 50.0)
        
        # Add realistic noise
        volatility = 0.02  # 2% volatility
        price = base_price * (1 + gauss(0, volatility))
        
        return PriceWithMetadata(
            instrument=instrument,
            price=price,
            timestamp=datetime.utcnow(),
            source=DataSourceType.SIMULATION,
            priority=SourcePriority.FALLBACK,
            confidence=0.70,  # Lower confidence for simulated data
            change_percent=gauss(0, 1.0),  # Random change %
        )
    
    def _record_success(self, source: DataSourceType):
        """Record successful request."""
        self._add_to_history(source, True)
        
        health = self.source_health[source]
        health.available = True
        health.last_success = datetime.utcnow()
        health.success_rate = self._calculate_success_rate(source)
    
    def _record_failure(self, source: DataSourceType, reason: str):
        """Record failed request."""
        self._add_to_history(source, False)
        
        health = self.source_health[source]
        health.last_failure = datetime.utcnow()
        health.failure_reason = reason
        health.success_rate = self._calculate_success_rate(source)
        
        # Mark as unavailable if success rate too low
        if health.success_rate < 0.5:
            health.available = False
            logger.warning(
                "source_marked_unavailable",
                source=source.value,
                success_rate=health.success_rate
            )
    
    def _add_to_history(self, source: DataSourceType, success: bool):
        """Add request result to history."""
        history = self._request_history[source]
        history.append(success)
        
        # Keep only last N requests
        if len(history) > self._max_history:
            history.pop(0)
    
    def _calculate_success_rate(self, source: DataSourceType) -> float:
        """Calculate success rate from history."""
        history = self._request_history[source]
        if not history:
            return 1.0
        
        successes = sum(1 for success in history if success)
        return successes / len(history)
    
    def _update_latency(self, source: DataSourceType, latency_ms: float):
        """Update rolling average latency."""
        health = self.source_health[source]
        
        # Simple exponential moving average
        alpha = 0.2
        if health.avg_latency_ms == 0:
            health.avg_latency_ms = latency_ms
        else:
            health.avg_latency_ms = (alpha * latency_ms + 
                                     (1 - alpha) * health.avg_latency_ms)
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status for all sources.
        
        Returns:
            Dictionary with health metrics per source
        """
        return {
            source.value: {
                "available": health.available,
                "success_rate": round(health.success_rate, 3),
                "avg_latency_ms": round(health.avg_latency_ms, 2),
                "last_success": health.last_success.isoformat() if health.last_success else None,
                "last_failure": health.last_failure.isoformat() if health.last_failure else None,
                "failure_reason": health.failure_reason,
            }
            for source, health in self.source_health.items()
        }
    
    def get_source_breakdown(self) -> Dict[str, List[str]]:
        """
        Get breakdown of which sources are used for each instrument.
        
        Returns:
            Dictionary mapping instrument to list of source names
        """
        breakdown = {}
        
        for instrument, sources in self.INSTRUMENT_SOURCE_MAP.items():
            available = self._get_source_priority(instrument)
            breakdown[instrument] = [s.value for s in available]
        
        return breakdown


# Singleton instance
_manager: Optional[DataSourceManager] = None


def get_data_source_manager(
    yahoo_client: Optional[YahooFinanceClient] = None,
    eia_client=None
) -> DataSourceManager:
    """
    Get or create singleton DataSourceManager.
    
    Args:
        yahoo_client: Yahoo Finance client
        eia_client: EIA API client
        
    Returns:
        DataSourceManager instance
    """
    global _manager
    
    if _manager is None:
        _manager = DataSourceManager(
            yahoo_client=yahoo_client,
            eia_client=eia_client,
            simulation_enabled=settings.USE_SIMULATION_FALLBACK
        )
    
    return _manager
