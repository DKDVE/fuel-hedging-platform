"""Analytics package - Complete quantitative engine for fuel hedging.

This package contains all analytics modules:
- Forecasting (ARIMA, LSTM, XGBoost, Ensemble)
- Risk management (VaR, CVaR, stress testing)
- Optimization (SLSQP solver with constraints)
- Basis risk analysis (R², crack spreads, proxy selection)

All modules are pure functions with no I/O dependencies.
"""

# Domain objects
from app.analytics.domain import (
    BasisRiskMetric,
    ForecastResult,
    HypothesisValidation,
    OptimizationResult,
    VaRResult,
)

# Protocols
from app.analytics.protocols import BasisAnalyzer, Forecaster, Optimizer, RiskEngine

# Basis risk
from app.analytics.basis import BasisRiskAnalyzer

# Risk analytics
from app.analytics.risk import (
    STRESS_SCENARIOS,
    HistoricalSimVaR,
    StressScenario,
    StressTestEngine,
    StressTestResult,
)

# Optimization
from app.analytics.optimizer import (
    HedgeOptimizer,
    build_optimizer_constraints,
    validate_solution_constraints,
)

# Forecasting
from app.analytics.forecaster import (
    ArimaForecaster,
    EnsembleForecaster,
    LSTMForecaster,
    XGBoostForecaster,
)

__all__ = [
    # Domain objects
    "ForecastResult",
    "VaRResult",
    "OptimizationResult",
    "BasisRiskMetric",
    "HypothesisValidation",
    # Protocols
    "Forecaster",
    "RiskEngine",
    "Optimizer",
    "BasisAnalyzer",
    # Forecasters
    "ArimaForecaster",
    "LSTMForecaster",
    "XGBoostForecaster",
    "EnsembleForecaster",
    # Risk
    "HistoricalSimVaR",
    "StressTestEngine",
    "StressScenario",
    "StressTestResult",
    "STRESS_SCENARIOS",
    # Optimizer
    "HedgeOptimizer",
    "build_optimizer_constraints",
    "validate_solution_constraints",
    # Basis
    "BasisRiskAnalyzer",
]
