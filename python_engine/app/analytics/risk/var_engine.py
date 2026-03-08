"""Historical simulation Value at Risk engine.

Non-parametric VaR calculation using historical price changes.
More robust than parametric methods for non-normal distributions.
"""

from typing import Optional

import numpy as np
import pandas as pd

from app.analytics.domain import VaRResult
from app.exceptions import ModelError


class HistoricalSimVaR:
    """Historical simulation VaR calculator.
    
    Uses empirical distribution of historical returns to compute VaR
    without assuming a specific distribution (normal, t, etc.).
    """

    def __init__(
        self,
        confidence: float = 0.95,
        holding_period_days: int = 30,
        min_observations: int = 252,
    ) -> None:
        """Initialize VaR engine.
        
        Args:
            confidence: Confidence level (e.g., 0.95 for 95%)
            holding_period_days: Holding period for VaR calculation
            min_observations: Minimum required observations (default 1 year)
        """
        self.confidence = confidence
        self.holding_period_days = holding_period_days
        self.min_observations = min_observations

    def compute_var(
        self,
        df: pd.DataFrame,
        hedge_ratio: float,
        notional: float,
    ) -> VaRResult:
        """Compute VaR for a specific hedge ratio.
        
        Args:
            df: Historical price data with columns:
                - Jet_Fuel_Spot_USD_bbl
                - Heating_Oil_Futures_USD_bbl (primary proxy)
            hedge_ratio: Hedge ratio (0.0 = no hedge, 1.0 = fully hedged)
            notional: Notional exposure in USD
        
        Returns:
            VaRResult with VaR, CVaR, and metadata
        
        Raises:
            ModelError: If insufficient observations
        """
        n_obs = len(df)
        
        if n_obs < self.min_observations:
            raise ModelError(
                message=f"Insufficient data for VaR calculation: need {self.min_observations}, got {n_obs}",
                model_name="var_engine",
                context={"n_observations": n_obs, "min_required": self.min_observations},
            )

        # Extract price series
        jet_fuel_prices = df["Jet_Fuel_Spot_USD_bbl"].values
        proxy_prices = df["Heating_Oil_Futures_USD_bbl"].values

        # Compute daily returns
        jet_fuel_returns = np.diff(jet_fuel_prices) / jet_fuel_prices[:-1]
        proxy_returns = np.diff(proxy_prices) / proxy_prices[:-1]

        # Portfolio returns = unhedged exposure - hedged position
        # Negative return = loss
        portfolio_returns = jet_fuel_returns - (hedge_ratio * proxy_returns)

        # Scale to holding period (square root of time rule)
        scaling_factor = np.sqrt(self.holding_period_days)
        scaled_returns = portfolio_returns * scaling_factor

        # Compute VaR (quantile of loss distribution)
        # VaR is the (1 - confidence) percentile of losses
        var_percentile = (1 - self.confidence) * 100
        var_return = np.percentile(scaled_returns, var_percentile)
        var_usd = abs(var_return * notional)
        var_pct = abs(var_return * 100)

        # Compute CVaR (Expected Shortfall) - average of losses beyond VaR
        losses_beyond_var = scaled_returns[scaled_returns <= var_return]
        if len(losses_beyond_var) > 0:
            cvar_return = np.mean(losses_beyond_var)
            cvar_usd = abs(cvar_return * notional)
        else:
            # Edge case: no losses beyond VaR
            cvar_usd = var_usd

        return VaRResult(
            hedge_ratio=round(hedge_ratio, 4),
            var_pct=round(var_pct, 2),
            var_usd=round(var_usd, 2),
            cvar_usd=round(cvar_usd, 2),
            confidence=self.confidence,
            holding_period_days=self.holding_period_days,
            n_observations=n_obs - 1,  # -1 because we compute returns
        )

    def var_curve(
        self,
        df: pd.DataFrame,
        notional: float,
        hedge_ratios: Optional[list[float]] = None,
    ) -> list[VaRResult]:
        """Compute VaR at multiple hedge ratios for curve plotting.
        
        Used for H1 hypothesis validation (diminishing returns above 70%).
        
        Args:
            df: Historical price data
            notional: Notional exposure in USD
            hedge_ratios: Optional list of hedge ratios (default: 0%, 20%, 40%, 60%, 70%, 80%, 100%)
        
        Returns:
            List of VaRResults for each hedge ratio
        """
        if hedge_ratios is None:
            hedge_ratios = [0.0, 0.20, 0.40, 0.60, 0.70, 0.80, 1.0]
        results = []

        for hr in hedge_ratios:
            var_result = self.compute_var(df, hr, notional)
            results.append(var_result)

        return results

    def compute_marginal_var_reduction(
        self,
        df: pd.DataFrame,
        notional: float,
    ) -> dict[str, float]:
        """Compute marginal VaR reduction between consecutive hedge ratios.
        
        Used to validate H1 hypothesis: marginal VaR reduction decreases
        significantly above 70% hedge ratio.
        
        Args:
            df: Historical price data
            notional: Notional exposure in USD
        
        Returns:
            Dict of marginal reductions: {
                '0_to_20': 0.15,  # 15% reduction
                '20_to_40': 0.12,
                '40_to_60': 0.08,
                '60_to_70': 0.04,
                '70_to_80': 0.02,  # Diminishing returns
                '80_to_100': 0.01,
            }
        """
        var_curve = self.var_curve(df, notional)
        marginal_reductions = {}

        for i in range(1, len(var_curve)):
            prev_var = var_curve[i - 1].var_usd
            curr_var = var_curve[i].var_usd
            reduction_pct = ((prev_var - curr_var) / prev_var) * 100

            prev_hr = int(var_curve[i - 1].hedge_ratio * 100)
            curr_hr = int(var_curve[i].hedge_ratio * 100)
            key = f"{prev_hr}_to_{curr_hr}"

            marginal_reductions[key] = round(reduction_pct, 2)

        return marginal_reductions
