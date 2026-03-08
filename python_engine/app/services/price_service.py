"""
Real-time price data service with dual-mode operation:
1. Simulation mode: Geometric Brownian Motion (GBM) price generation
2. Live mode: Yahoo Finance + EIA API via DataSourceManager

Frontend is unaware of the mode - just consumes SSE stream.
"""

import asyncio
import json
import csv
import math
import random
import structlog
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Optional

from app.config import settings

logger = structlog.get_logger()


@dataclass
class PriceTick:
    """Single market price snapshot."""
    time: str  # ISO 8601 UTC
    jet_fuel_spot: float
    heating_oil_futures: float
    brent_futures: float
    wti_futures: float
    crack_spread: float
    volatility_index: float
    source: str  # "simulation" | "yahoo_finance" | "eia_api"
    quality_flag: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class PriceService:
    """
    Manages real-time price data stream.
    
    Architecture:
    - Single source of truth for market data
    - Publishes to multiple SSE subscribers via asyncio.Queue
    - Runs background task that generates/fetches prices every 2s
    - Keeps 500-tick history in memory
    
    Configuration:
    - USE_LIVE_FEED=false → GBM simulation (no API keys required)
    - USE_LIVE_FEED=true → Yahoo Finance + EIA API (EIA_API_KEY optional)
    """

    def __init__(self):
        self.use_live_feed: bool = settings.USE_LIVE_FEED
        self.tick_interval: float = (
            float(settings.YAHOO_FINANCE_UPDATE_INTERVAL)
            if settings.USE_LIVE_FEED
            else float(settings.SIMULATION_INTERVAL_SECONDS)
        )
        self.history: Deque[PriceTick] = deque(maxlen=500)
        self.subscribers: list[asyncio.Queue] = []
        self.task: Optional[asyncio.Task] = None
        self.running: bool = False

        # GBM simulation state
        self.current_prices = {
            "jet_fuel": 85.0,
            "heating_oil": 82.0,
            "brent": 78.0,
            "wti": 75.0,
        }
        
        # Load initial prices from dataset
        self._load_initial_prices()

        # DataSourceManager for live feed (lazy init to avoid import cycles)
        self._data_source_manager = None

    def _load_initial_prices(self):
        """Load starting prices from fuel_hedging_dataset.csv (last row)."""
        dataset_path = Path("data/fuel_hedging_dataset.csv")
        if dataset_path.exists():
            try:
                with open(dataset_path, 'r') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    if rows:
                        last_row = rows[-1]
                        self.current_prices = {
                            "jet_fuel": float(last_row.get("Jet_Fuel_Spot_USD_bbl", 85.0)),
                            "heating_oil": float(last_row.get("Heating_Oil_Futures_USD_bbl", 82.0)),
                            "brent": float(last_row.get("Brent_Crude_Futures_USD_bbl", 78.0)),
                            "wti": float(last_row.get("WTI_Crude_Futures_USD_bbl", 75.0)),
                        }
            except Exception as e:
                # Fallback to defaults if load fails
                pass

    def _generate_simulation_tick(self) -> PriceTick:
        """
        Generate next price tick using Geometric Brownian Motion.
        
        Formula: S(t+1) = S(t) * exp((μ - σ²/2)Δt + σ√Δt * Z)
        where Z ~ N(0,1)
        
        Calibrated parameters from fuel_hedging_dataset.csv analysis:
        - Jet Fuel: μ=0.0001, σ=0.0180 (highest volatility)
        - Heating Oil: μ=0.0001, σ=0.0165
        - Brent: μ=0.0001, σ=0.0150
        - WTI: μ=0.0001, σ=0.0145 (most stable)
        """
        dt = self.tick_interval / (24 * 3600)  # Convert seconds to days
        
        # GBM parameters (annualized)
        params = {
            "jet_fuel": {"mu": 0.0001, "sigma": 0.0180},
            "heating_oil": {"mu": 0.0001, "sigma": 0.0165},
            "brent": {"mu": 0.0001, "sigma": 0.0150},
            "wti": {"mu": 0.0001, "sigma": 0.0145},
        }
        
        # Generate correlated random shocks
        # Heating oil is highly correlated with jet fuel (ρ ≈ 0.90)
        z_market = random.gauss(0, 1)  # Common market shock
        
        for key, param in params.items():
            mu = param["mu"]
            sigma = param["sigma"]
            
            # Add correlation structure
            if key == "heating_oil":
                z = 0.90 * z_market + 0.10 * random.gauss(0, 1)
            elif key == "brent":
                z = 0.75 * z_market + 0.25 * random.gauss(0, 1)
            elif key == "wti":
                z = 0.70 * z_market + 0.30 * random.gauss(0, 1)
            else:  # jet_fuel
                z = z_market
            
            # GBM step
            drift = (mu - 0.5 * sigma ** 2) * dt
            diffusion = sigma * math.sqrt(dt) * z
            self.current_prices[key] *= math.exp(drift + diffusion)
            
            # Floor at $1/bbl (prevent negative prices)
            self.current_prices[key] = max(self.current_prices[key], 1.0)
        
        # Calculate derived values
        crack_spread = self.current_prices["jet_fuel"] - self.current_prices["heating_oil"]
        
        # Volatility index (VIX-style, varies 10-30 with spikes)
        base_vol = 18.0
        vol_shock = random.gauss(0, 2.0)
        volatility_index = max(10.0, min(30.0, base_vol + vol_shock))
        
        return PriceTick(
            time=datetime.now(timezone.utc).isoformat(),
            jet_fuel_spot=round(self.current_prices["jet_fuel"], 2),
            heating_oil_futures=round(self.current_prices["heating_oil"], 2),
            brent_futures=round(self.current_prices["brent"], 2),
            wti_futures=round(self.current_prices["wti"], 2),
            crack_spread=round(crack_spread, 2),
            volatility_index=round(volatility_index, 2),
            source="simulation",
            quality_flag=None,
        )

    def _get_data_source_manager(self):
        """Lazy-init DataSourceManager with Yahoo Finance and EIA clients."""
        if self._data_source_manager is None:
            from app.clients.eia import EIAClient
            from app.services.data_source_manager import get_data_source_manager
            from app.services.yahoo_finance_client import get_yahoo_finance_client

            yahoo_client = get_yahoo_finance_client(
                max_requests_per_hour=settings.MAX_YAHOO_REQUESTS_PER_HOUR,
                cache_ttl_seconds=settings.YAHOO_FINANCE_CACHE_TTL,
            )
            eia_client = EIAClient(settings.EIA_API_KEY) if settings.EIA_API_KEY else None
            self._data_source_manager = get_data_source_manager(
                yahoo_client=yahoo_client,
                eia_client=eia_client,
            )
        return self._data_source_manager

    async def _fetch_live_tick(self) -> PriceTick:
        """
        Fetch live prices from Yahoo Finance and EIA API via DataSourceManager.
        Falls back to simulation if all sources fail.
        """
        manager = self._get_data_source_manager()
        instruments = ["jet_fuel", "heating_oil", "brent_crude", "wti_crude"]
        results = await manager.get_multiple_prices(instruments)

        # Use last known prices as fallback for missing instruments
        prices = {
            "jet_fuel": self.current_prices["jet_fuel"],
            "heating_oil": self.current_prices["heating_oil"],
            "brent": self.current_prices["brent"],
            "wti": self.current_prices["wti"],
        }
        source_used = "simulation"

        for instrument, result in results.items():
            if result is not None:
                if instrument == "jet_fuel":
                    prices["jet_fuel"] = result.price
                elif instrument == "heating_oil":
                    prices["heating_oil"] = result.price
                elif instrument == "brent_crude":
                    prices["brent"] = result.price
                elif instrument == "wti_crude":
                    prices["wti"] = result.price
                source_used = result.source.value

        # If we got at least one live price, use it; otherwise fall back to simulation
        got_any_live = any(
            results[k] is not None for k in instruments
        )
        if not got_any_live:
            logger.warning("live_feed_all_sources_failed_falling_back_to_simulation")
            return self._generate_simulation_tick()

        # Update current prices for next fallback
        self.current_prices.update(prices)

        crack_spread = prices["jet_fuel"] - prices["heating_oil"]
        volatility_index = 18.0  # Placeholder; VIX could be added later

        return PriceTick(
            time=datetime.now(timezone.utc).isoformat(),
            jet_fuel_spot=round(prices["jet_fuel"], 2),
            heating_oil_futures=round(prices["heating_oil"], 2),
            brent_futures=round(prices["brent"], 2),
            wti_futures=round(prices["wti"], 2),
            crack_spread=round(crack_spread, 2),
            volatility_index=round(volatility_index, 2),
            source=source_used,
            quality_flag=None,
        )

    async def _price_loop(self):
        """Background task: generate/fetch prices and publish to subscribers."""
        while self.running:
            try:
                # Generate or fetch next tick
                if self.use_live_feed:
                    try:
                        tick = await self._fetch_live_tick()
                    except Exception as e:
                        logger.warning("live_feed_error_falling_back", error=str(e))
                        tick = self._generate_simulation_tick()
                else:
                    tick = self._generate_simulation_tick()
                
                # Store in history
                self.history.append(tick)
                
                # Publish to all subscribers (non-blocking)
                for queue in self.subscribers:
                    try:
                        queue.put_nowait(tick)
                    except asyncio.QueueFull:
                        # Drop tick if subscriber can't keep up
                        pass
                
                # Wait for next tick
                await asyncio.sleep(self.tick_interval)
            
            except Exception as e:
                # Log error but don't crash the loop
                await asyncio.sleep(self.tick_interval)

    async def start(self):
        """Start the price generation loop."""
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._price_loop())

    async def stop(self):
        """Stop the price generation loop."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to price updates. Returns a queue that receives PriceTick objects."""
        queue = asyncio.Queue(maxsize=50)
        self.subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from price updates."""
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    def get_history(self, n: int = 100) -> list[PriceTick]:
        """Get last N historical ticks."""
        return list(self.history)[-n:]

    def get_last_tick(self) -> Optional[PriceTick]:
        """Get the most recent price tick, or None if no ticks yet."""
        return self.history[-1] if self.history else None

    def publish_alert(self, alert_data: dict) -> None:
        """Publish an alert event to all price stream subscribers."""
        payload = json.dumps({"type": "alert", "data": alert_data})
        for queue in list(self.subscribers):
            try:
                queue.put_nowait({"__type": "alert", "payload": payload})
            except asyncio.QueueFull:
                pass

    def get_status(self) -> dict:
        """Get service status for health checks."""
        latest = self.history[-1] if self.history else None
        return {
            "running": self.running,
            "source": "live_feed" if self.use_live_feed else "simulation",
            "subscribers": len(self.subscribers),
            "history_size": len(self.history),
            "tick_interval_seconds": self.tick_interval,
            "latest_price": latest.to_dict() if latest else None,
        }


# Singleton instance
_price_service: Optional[PriceService] = None


def get_price_service() -> PriceService:
    """Get or create the global PriceService instance."""
    global _price_service
    if _price_service is None:
        _price_service = PriceService()
    return _price_service
