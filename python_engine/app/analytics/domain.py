"""Domain objects for analytics modules.

All domain objects are frozen dataclasses (immutable after creation).
They have no knowledge of HTTP, databases, or I/O operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class ForecastResult:
    """Result from ensemble forecaster.
    
    Contains 30-day ahead price predictions and accuracy metrics.
    """

    forecast_values: tuple[float, ...]
    """30-day ahead jet fuel price forecasts (USD/bbl)"""

    mape: float
    """Mean Absolute Percentage Error on validation set (%)"""

    mape_passes_target: bool
    """Whether MAPE is below MAPE_TARGET threshold"""

    model_weights: dict[str, float]
    """Ensemble weights: {'arima': 0.25, 'lstm': 0.45, 'xgb': 0.30}"""

    horizon_days: int
    """Forecast horizon in days (typically 30)"""

    generated_at: datetime
    """Timestamp when forecast was generated"""

    model_versions: dict[str, str]
    """Model version identifiers for reproducibility"""


@dataclass(frozen=True)
class VaRResult:
    """Value at Risk calculation result.
    
    Non-parametric historical simulation VaR.
    """

    hedge_ratio: float
    """Hedge ratio for this VaR calculation (0.0 - 1.0)"""

    var_pct: float
    """VaR as percentage of notional (%)"""

    var_usd: float
    """VaR in absolute USD terms"""

    cvar_usd: float
    """Conditional VaR / Expected Shortfall (USD)"""

    confidence: float
    """Confidence level (e.g., 0.95 for 95%)"""

    holding_period_days: int
    """Holding period for VaR calculation"""

    n_observations: int
    """Number of historical observations used"""


@dataclass(frozen=True)
class OptimizationResult:
    """Result from hedge optimizer.
    
    Contains optimal hedge ratio, instrument mix, and constraint satisfaction.
    """

    optimal_hr: float
    """Optimal hedge ratio (0.0 - 0.80)"""

    instrument_mix: dict[str, float]
    """Mix of instruments: {'futures': 0.60, 'options': 0.30, 'collars': 0.10, 'swaps': 0.0}"""

    proxy_weights: dict[str, float]
    """Proxy weights: {'heating_oil': 0.70, 'brent': 0.20, 'wti': 0.10}"""

    objective_value: float
    """Optimizer objective function value (typically VaR reduction)"""

    solver_converged: bool
    """Whether optimizer converged to a solution"""

    collateral_usd: float
    """Required collateral in USD"""

    collateral_pct_of_reserves: float
    """Collateral as percentage of cash reserves (%)"""

    solve_time_seconds: float
    """Time taken to solve optimization problem"""

    constraint_violations: list[str]
    """List of violated constraints (empty if all satisfied)"""


@dataclass(frozen=True)
class BasisRiskMetric:
    """Basis risk analysis between jet fuel and proxy instruments.
    
    Used for proxy selection and IFRS 9 hedge effectiveness.
    """

    r2_heating_oil: float
    """R² correlation between jet fuel and heating oil futures"""

    r2_brent: float
    """R² correlation between jet fuel and Brent crude"""

    r2_wti: float
    """R² correlation between jet fuel and WTI crude"""

    crack_spread_current: float
    """Current crack spread (jet fuel - heating oil) in USD/bbl"""

    crack_spread_zscore: float
    """Z-score of current crack spread vs historical mean"""

    risk_level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    """Basis risk assessment level"""

    recommended_proxy: Literal["heating_oil", "brent", "wti"]
    """Recommended proxy instrument based on highest R²"""

    ifrs9_eligible: bool
    """Whether heating oil R² meets IFRS 9 prospective effectiveness threshold"""


@dataclass(frozen=True)
class HypothesisValidation:
    """Result of hypothesis validation (H1-H4).
    
    Used for hypothesis status tracking in the dashboard.
    """

    hypothesis_id: Literal["H1", "H2", "H3", "H4"]
    """Hypothesis identifier"""

    hypothesis_name: str
    """Human-readable hypothesis description"""

    passed: bool
    """Whether hypothesis validation passed"""

    metric_name: str
    """Name of the metric being tested"""

    metric_value: float
    """Actual metric value"""

    threshold: str
    """Threshold description (e.g., '< 70%' or '> 35%')"""

    last_tested: datetime
    """Timestamp of last validation"""
