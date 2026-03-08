"""Basis risk analyzer for jet fuel hedging.

Analyzes correlation between jet fuel spot prices and proxy instruments
(heating oil futures, Brent crude, WTI crude). Used for:
1. Proxy selection (which instrument to hedge with)
2. IFRS 9 hedge effectiveness testing
3. Basis risk level assessment
"""

from typing import Literal

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

from app.analytics.domain import BasisRiskMetric
from app.constants import IFRS9_R2_MIN_PROSPECTIVE


class BasisRiskAnalyzer:
    """Analyzes basis risk between jet fuel and proxy instruments.
    
    Computes rolling R² correlations and crack spread statistics
    to assess hedge effectiveness and recommend optimal proxy.
    """

    def __init__(self, window_days: int = 90) -> None:
        """Initialize analyzer.
        
        Args:
            window_days: Rolling window for R² calculation (default 90 days)
        """
        self.window_days = window_days

    def analyze(self, df: pd.DataFrame) -> BasisRiskMetric:
        """Analyze basis risk and recommend best proxy.
        
        Args:
            df: Historical price data with columns:
                - Jet_Fuel_Spot_USD_bbl
                - Heating_Oil_Futures_USD_bbl
                - Brent_Crude_Futures_USD_bbl
                - WTI_Crude_Futures_USD_bbl
                - Crack_Spread_USD_bbl
        
        Returns:
            BasisRiskMetric with correlations and recommendations
        """
        # Ensure we have enough data
        if len(df) < self.window_days:
            raise ValueError(
                f"Insufficient data: need at least {self.window_days} observations, "
                f"got {len(df)}"
            )

        # Extract price series
        jet_fuel = df["Jet_Fuel_Spot_USD_bbl"].values
        heating_oil = df["Heating_Oil_Futures_USD_bbl"].values
        brent = df["Brent_Crude_Futures_USD_bbl"].values
        wti = df["WTI_Crude_Futures_USD_bbl"].values

        # Compute rolling R² for each proxy (last window_days)
        recent_data = df.tail(self.window_days)
        
        r2_heating_oil = self._compute_r2(
            recent_data["Jet_Fuel_Spot_USD_bbl"].values,
            recent_data["Heating_Oil_Futures_USD_bbl"].values,
        )
        
        r2_brent = self._compute_r2(
            recent_data["Jet_Fuel_Spot_USD_bbl"].values,
            recent_data["Brent_Crude_Futures_USD_bbl"].values,
        )
        
        r2_wti = self._compute_r2(
            recent_data["Jet_Fuel_Spot_USD_bbl"].values,
            recent_data["WTI_Crude_Futures_USD_bbl"].values,
        )

        # Crack spread analysis
        crack_spread = df["Crack_Spread_USD_bbl"].values
        crack_spread_current = float(crack_spread[-1])
        
        # Compute z-score of current crack spread
        crack_spread_mean = np.mean(crack_spread)
        crack_spread_std = np.std(crack_spread)
        crack_spread_zscore = (
            (crack_spread_current - crack_spread_mean) / crack_spread_std
            if crack_spread_std > 0 else 0.0
        )

        # Determine recommended proxy (highest R²)
        correlations = {
            "heating_oil": r2_heating_oil,
            "brent": r2_brent,
            "wti": r2_wti,
        }
        recommended_proxy = max(correlations, key=correlations.get)  # type: ignore

        # Assess risk level based on crack spread z-score
        abs_zscore = abs(crack_spread_zscore)
        if abs_zscore < 1.0:
            risk_level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"] = "LOW"
        elif abs_zscore < 2.0:
            risk_level = "MODERATE"
        elif abs_zscore < 3.0:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        # IFRS 9 eligibility (heating oil R² must meet threshold)
        ifrs9_eligible = r2_heating_oil >= IFRS9_R2_MIN_PROSPECTIVE

        return BasisRiskMetric(
            r2_heating_oil=round(r2_heating_oil, 4),
            r2_brent=round(r2_brent, 4),
            r2_wti=round(r2_wti, 4),
            crack_spread_current=round(crack_spread_current, 2),
            crack_spread_zscore=round(crack_spread_zscore, 2),
            risk_level=risk_level,
            recommended_proxy=recommended_proxy,  # type: ignore
            ifrs9_eligible=ifrs9_eligible,
        )

    def _compute_r2(self, y: np.ndarray, x: np.ndarray) -> float:
        """Compute R² between two price series.
        
        Args:
            y: Dependent variable (jet fuel)
            x: Independent variable (proxy)
        
        Returns:
            R² value (0.0 to 1.0)
        """
        # Reshape for sklearn
        X = x.reshape(-1, 1)
        Y = y.reshape(-1, 1)

        # Fit linear regression
        model = LinearRegression()
        model.fit(X, Y)

        # Predict and compute R²
        y_pred = model.predict(X)
        r2 = r2_score(Y, y_pred)

        return float(max(0.0, r2))  # Ensure non-negative
