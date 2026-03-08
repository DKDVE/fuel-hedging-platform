"""Stress testing scenarios for extreme market conditions."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class StressScenario:
    """Definition of a stress test scenario."""

    name: str
    description: str
    jet_fuel_shock_pct: float
    proxy_shock_pct: float
    volatility_multiplier: float
    duration_days: int


# Five stress test scenarios
STRESS_SCENARIOS = [
    StressScenario(
        name="Oil Supply Shock",
        description="Geopolitical disruption causes crude oil price spike",
        jet_fuel_shock_pct=25.0,
        proxy_shock_pct=30.0,  # Proxies rise more than jet fuel
        volatility_multiplier=2.5,
        duration_days=30,
    ),
    StressScenario(
        name="Refinery Capacity Crisis",
        description="Refinery shutdowns widen crack spreads",
        jet_fuel_shock_pct=40.0,  # Jet fuel rises much more
        proxy_shock_pct=15.0,
        volatility_multiplier=3.0,
        duration_days=60,
    ),
    StressScenario(
        name="Global Recession",
        description="Demand collapse causes price crash",
        jet_fuel_shock_pct=-35.0,
        proxy_shock_pct=-30.0,
        volatility_multiplier=2.0,
        duration_days=180,
    ),
    StressScenario(
        name="Basis Risk Spike",
        description="Correlation breakdown between jet fuel and heating oil",
        jet_fuel_shock_pct=15.0,
        proxy_shock_pct=-10.0,  # Opposite direction move
        volatility_multiplier=4.0,
        duration_days=45,
    ),
    StressScenario(
        name="Market Liquidity Crisis",
        description="Extreme volatility with thin markets",
        jet_fuel_shock_pct=20.0,
        proxy_shock_pct=25.0,
        volatility_multiplier=5.0,
        duration_days=14,
    ),
]


@dataclass(frozen=True)
class StressTestResult:
    """Result of a stress test scenario."""

    scenario_name: str
    hedge_ratio: float
    portfolio_loss_usd: float
    unhedged_loss_usd: float
    hedge_effectiveness_pct: float
    max_drawdown_usd: float
    collateral_requirement_usd: float
    passes_collateral_limit: bool


class StressTestEngine:
    """Runs stress test scenarios on hedged portfolios."""

    def __init__(self, notional: float, cash_reserves: float) -> None:
        """Initialize stress test engine.
        
        Args:
            notional: Portfolio notional in USD
            cash_reserves: Available cash reserves in USD
        """
        self.notional = notional
        self.cash_reserves = cash_reserves

    def run_scenario(
        self,
        scenario: StressScenario,
        current_jet_fuel_price: float,
        current_proxy_price: float,
        hedge_ratio: float,
    ) -> StressTestResult:
        """Run a single stress test scenario.
        
        Args:
            scenario: Scenario definition
            current_jet_fuel_price: Current jet fuel price (USD/bbl)
            current_proxy_price: Current proxy price (USD/bbl)
            hedge_ratio: Current hedge ratio
        
        Returns:
            StressTestResult with losses and effectiveness
        """
        # Compute shocked prices
        shocked_jet_fuel = current_jet_fuel_price * (
            1 + scenario.jet_fuel_shock_pct / 100
        )
        shocked_proxy = current_proxy_price * (
            1 + scenario.proxy_shock_pct / 100
        )

        # Unhedged loss (full exposure to jet fuel price change)
        unhedged_loss = (shocked_jet_fuel - current_jet_fuel_price) * (
            self.notional / current_jet_fuel_price
        )

        # Hedge P&L (opposite direction to exposure)
        hedge_pnl = (shocked_proxy - current_proxy_price) * (
            self.notional * hedge_ratio / current_proxy_price
        )

        # Portfolio loss = unhedged loss - hedge P&L
        portfolio_loss = unhedged_loss - hedge_pnl

        # Hedge effectiveness
        if abs(unhedged_loss) > 0:
            hedge_effectiveness = (
                1 - abs(portfolio_loss) / abs(unhedged_loss)
            ) * 100
        else:
            hedge_effectiveness = 100.0

        # Max drawdown (assume linear price move over duration)
        max_drawdown = abs(min(portfolio_loss, 0.0))

        # Collateral requirement (simplified: 15% of notional hedged + variation margin)
        base_collateral = self.notional * hedge_ratio * 0.15
        variation_margin = abs(hedge_pnl)
        collateral_requirement = base_collateral + variation_margin

        # Check collateral limit (15% of cash reserves)
        collateral_limit = self.cash_reserves * 0.15
        passes_collateral = collateral_requirement <= collateral_limit

        return StressTestResult(
            scenario_name=scenario.name,
            hedge_ratio=round(hedge_ratio, 4),
            portfolio_loss_usd=round(portfolio_loss, 2),
            unhedged_loss_usd=round(unhedged_loss, 2),
            hedge_effectiveness_pct=round(hedge_effectiveness, 2),
            max_drawdown_usd=round(max_drawdown, 2),
            collateral_requirement_usd=round(collateral_requirement, 2),
            passes_collateral_limit=passes_collateral,
        )

    def run_all_scenarios(
        self,
        current_jet_fuel_price: float,
        current_proxy_price: float,
        hedge_ratio: float,
    ) -> list[StressTestResult]:
        """Run all five stress test scenarios.
        
        Args:
            current_jet_fuel_price: Current jet fuel price
            current_proxy_price: Current proxy price
            hedge_ratio: Current hedge ratio
        
        Returns:
            List of stress test results
        """
        results = []
        for scenario in STRESS_SCENARIOS:
            result = self.run_scenario(
                scenario,
                current_jet_fuel_price,
                current_proxy_price,
                hedge_ratio,
            )
            results.append(result)
        return results
