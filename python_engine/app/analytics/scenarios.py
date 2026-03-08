"""
scenarios.py

Pre-defined market stress scenarios for hedge strategy simulation.
Each scenario applies a price shock and volatility multiplier to current market
conditions and reruns the optimizer to show recommended strategy response.

This does NOT write to the database — pure simulation, returns results only.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StressScenario:
    """A pre-defined stress scenario for simulation."""

    id: str
    name: str
    description: str
    price_shock_pct: float  # -0.67 = -67% price shock (COVID)
    vol_multiplier: float  # 4.2 = 4.2× normal volatility
    duration_days: int
    historical_reference: str
    color: str  # hex for UI card accent


SCENARIOS: list[StressScenario] = [
    StressScenario(
        id="covid_crash",
        name="COVID-19 Demand Collapse",
        description="Aviation demand collapsed 67% in 60 days. Tests hedge performance in extreme price decline where unhedged position benefits from lower costs.",
        price_shock_pct=-0.67,
        vol_multiplier=4.2,
        duration_days=60,
        historical_reference="March–May 2020",
        color="#ef4444",  # red — severe
    ),
    StressScenario(
        id="russia_ukraine",
        name="Russia-Ukraine Supply Shock",
        description="Brent crude surged 80% in 3 weeks following supply disruption. Tests hedge performance in rapid price spike.",
        price_shock_pct=0.80,
        vol_multiplier=2.8,
        duration_days=21,
        historical_reference="February–March 2022",
        color="#f97316",  # orange — severe
    ),
    StressScenario(
        id="gulf_disruption",
        name="Gulf Supply Disruption",
        description="Hypothetical 30-day disruption to Gulf crude supply routes. Elevated basis risk as crack spread widens.",
        price_shock_pct=0.45,
        vol_multiplier=2.2,
        duration_days=30,
        historical_reference="Hypothetical",
        color="#eab308",  # yellow — moderate
    ),
    StressScenario(
        id="contango_market",
        name="Deep Contango",
        description="Forward curve in deep contango — futures trade above spot. Tests cost of carry in hedging strategy.",
        price_shock_pct=0.12,
        vol_multiplier=0.8,
        duration_days=90,
        historical_reference="2023 Q1",
        color="#3b82f6",  # blue — low severity
    ),
    StressScenario(
        id="baseline",
        name="Normal Market",
        description="2023 baseline conditions — moderate volatility, normal backwardation. Reference scenario.",
        price_shock_pct=0.0,
        vol_multiplier=1.0,
        duration_days=30,
        historical_reference="2023 Average",
        color="#22c55e",  # green — baseline
    ),
]

SCENARIOS_BY_ID: dict[str, StressScenario] = {s.id: s for s in SCENARIOS}
