"""Protocol interfaces for analytics modules.

These define the contracts that all analytics implementations must follow.
Using Protocol allows for interchangeable implementations (ARIMA vs LSTM, etc.).
"""

from typing import Protocol, runtime_checkable

import pandas as pd

from app.analytics.domain import BasisRiskMetric, ForecastResult, OptimizationResult, VaRResult


@runtime_checkable
class Forecaster(Protocol):
    """Protocol for price forecasting models.
    
    Any forecaster (ARIMA, LSTM, XGBoost, or ensemble) must implement this.
    """

    def predict(self, df: pd.DataFrame) -> ForecastResult:
        """Generate price forecast from historical data.
        
        Args:
            df: Historical price data with columns:
                ['Date', 'Jet_Fuel_Spot_USD_bbl', 'Heating_Oil_Futures_USD_bbl',
                 'Brent_Crude_Futures_USD_bbl', 'WTI_Crude_Futures_USD_bbl',
                 'Crack_Spread_USD_bbl', 'Volatility_Index_pct']
        
        Returns:
            ForecastResult with predictions and accuracy metrics
        """
        ...


@runtime_checkable
class RiskEngine(Protocol):
    """Protocol for Value at Risk computation.
    
    Implementations can use historical simulation, parametric, or Monte Carlo methods.
    """

    def compute_var(
        self, 
        df: pd.DataFrame, 
        hedge_ratio: float, 
        notional: float
    ) -> VaRResult:
        """Compute VaR for a specific hedge ratio.
        
        Args:
            df: Historical price data
            hedge_ratio: Hedge ratio to compute VaR for (0.0 - 1.0)
            notional: Notional exposure in USD
        
        Returns:
            VaRResult with VaR, CVaR, and metadata
        """
        ...

    def var_curve(
        self, 
        df: pd.DataFrame, 
        notional: float
    ) -> list[VaRResult]:
        """Compute VaR at multiple hedge ratios for curve plotting.
        
        Computes VaR at 0%, 20%, 40%, 60%, 70%, 80%, 100% hedge ratios.
        Used for H1 hypothesis validation (diminishing returns above 70%).
        
        Args:
            df: Historical price data
            notional: Notional exposure in USD
        
        Returns:
            List of VaRResults for each hedge ratio
        """
        ...


@runtime_checkable
class Optimizer(Protocol):
    """Protocol for hedge optimization.
    
    Implementations can use SLSQP, genetic algorithms, or other solvers.
    """

    def optimize(
        self, 
        var_metrics: dict[str, float], 
        constraints: dict[str, float]
    ) -> OptimizationResult:
        """Optimize hedge ratio and instrument mix.
        
        Args:
            var_metrics: VaR values at different hedge ratios
                {'hr_0': var_usd, 'hr_20': var_usd, ...}
            constraints: Runtime constraints from ConfigRepository
                {'hr_cap': 0.80, 'collateral_limit': 0.15, ...}
        
        Returns:
            OptimizationResult with optimal decisions and constraint satisfaction
        """
        ...


@runtime_checkable
class BasisAnalyzer(Protocol):
    """Protocol for basis risk analysis.
    
    Analyzes correlation between jet fuel and proxy instruments.
    """

    def analyze(self, df: pd.DataFrame) -> BasisRiskMetric:
        """Analyze basis risk and recommend best proxy.
        
        Computes rolling R² correlations, crack spread z-scores,
        and determines IFRS 9 hedge accounting eligibility.
        
        Args:
            df: Historical price data with all proxies
        
        Returns:
            BasisRiskMetric with correlations and recommendations
        """
        ...
