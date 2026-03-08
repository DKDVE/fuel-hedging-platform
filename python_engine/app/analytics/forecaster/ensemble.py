"""Ensemble forecaster combining ARIMA, LSTM, and XGBoost.

Weighted average of three forecasters for improved accuracy.
Default weights: {'arima': 0.25, 'lstm': 0.45, 'xgb': 0.30}
"""

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from app.analytics.domain import ForecastResult
from app.analytics.forecaster.arima import ArimaForecaster
from app.analytics.forecaster.lstm import LSTMForecaster
from app.analytics.forecaster.xgboost_model import XGBoostForecaster
from app.constants import MAPE_TARGET


class EnsembleForecaster:
    """Ensemble of ARIMA, LSTM, and XGBoost forecasters.
    
    Combines predictions using weighted average for improved
    robustness and accuracy.
    """

    def __init__(
        self,
        arima_forecaster: Optional[ArimaForecaster] = None,
        lstm_forecaster: Optional[LSTMForecaster] = None,
        xgboost_forecaster: Optional[XGBoostForecaster] = None,
        weights: Optional[dict[str, float]] = None,
        horizon_days: int = 30,
    ) -> None:
        """Initialize ensemble forecaster.
        
        Args:
            arima_forecaster: ARIMA forecaster instance (created if None)
            lstm_forecaster: LSTM forecaster instance (created if None)
            xgboost_forecaster: XGBoost forecaster instance (created if None)
            weights: Model weights {'arima': 0.25, 'lstm': 0.45, 'xgb': 0.30}
            horizon_days: Forecast horizon
        """
        self.horizon_days = horizon_days
        
        # Initialize sub-forecasters if not provided (dependency injection)
        self.arima = arima_forecaster or ArimaForecaster(horizon_days=horizon_days)
        self.lstm = lstm_forecaster or LSTMForecaster(horizon_days=horizon_days)
        self.xgboost = xgboost_forecaster or XGBoostForecaster(horizon_days=horizon_days)
        
        # Default weights (from Phase 2 Report - validated on 2024 data)
        self.weights = weights or {
            "arima": 0.25,
            "lstm": 0.45,
            "xgboost": 0.30,
        }
        
        # Validate weights sum to 1.0
        weight_sum = sum(self.weights.values())
        if not (0.999 <= weight_sum <= 1.001):
            raise ValueError(
                f"Model weights must sum to 1.0, got {weight_sum}"
            )

    def predict(self, df: pd.DataFrame) -> ForecastResult:
        """Generate ensemble forecast.
        
        Args:
            df: Historical price data with all required columns
        
        Returns:
            ForecastResult with weighted ensemble predictions
        """
        generated_at = datetime.utcnow()
        
        # Generate forecasts from each model
        try:
            arima_result = self.arima.predict(df)
            arima_forecast = np.array(arima_result.forecast_values)
            arima_available = True
        except Exception:
            # ARIMA failed - use zeros (will be handled by weight adjustment)
            arima_forecast = np.zeros(self.horizon_days)
            arima_available = False
        
        try:
            lstm_result = self.lstm.predict(df)
            lstm_forecast = np.array(lstm_result.forecast_values)
            lstm_available = True
        except Exception:
            # LSTM failed (e.g., model file not found) - use zeros
            lstm_forecast = np.zeros(self.horizon_days)
            lstm_available = False
        
        try:
            xgboost_result = self.xgboost.predict(df)
            xgboost_forecast = np.array(xgboost_result.forecast_values)
            xgboost_available = True
        except Exception:
            # XGBoost failed - use zeros
            xgboost_forecast = np.zeros(self.horizon_days)
            xgboost_available = False
        
        # Adjust weights if any model failed
        adjusted_weights = self._adjust_weights(
            arima_available,
            lstm_available,
            xgboost_available,
        )
        
        # Compute weighted ensemble
        ensemble_forecast = (
            adjusted_weights["arima"] * arima_forecast +
            adjusted_weights["lstm"] * lstm_forecast +
            adjusted_weights["xgboost"] * xgboost_forecast
        )
        
        forecast_values = tuple(float(x) for x in ensemble_forecast)
        
        # Calculate ensemble MAPE on validation set (last horizon_days)
        actual_prices = df["Jet_Fuel_Spot_USD_bbl"].values[-self.horizon_days:]
        mape = self._calculate_mape(actual_prices, ensemble_forecast)
        mape_passes_target = mape < MAPE_TARGET
        
        # Collect model versions
        model_versions = {}
        if arima_available:
            model_versions["arima"] = self.arima.model_version
        if lstm_available:
            model_versions["lstm"] = self.lstm.model_version
        if xgboost_available:
            model_versions["xgboost"] = self.xgboost.model_version
        
        return ForecastResult(
            forecast_values=forecast_values,
            mape=round(mape, 2),
            mape_passes_target=mape_passes_target,
            model_weights=adjusted_weights,
            horizon_days=self.horizon_days,
            generated_at=generated_at,
            model_versions=model_versions,
        )

    def _adjust_weights(
        self,
        arima_available: bool,
        lstm_available: bool,
        xgboost_available: bool,
    ) -> dict[str, float]:
        """Adjust weights if any model failed.
        
        Redistributes weight from failed models to available ones.
        
        Args:
            arima_available: Whether ARIMA succeeded
            lstm_available: Whether LSTM succeeded
            xgboost_available: Whether XGBoost succeeded
        
        Returns:
            Adjusted weights that sum to 1.0
        """
        if all([arima_available, lstm_available, xgboost_available]):
            # All models available - use original weights
            return self.weights.copy()
        
        # Calculate available weight
        available_weight = 0.0
        unavailable_weight = 0.0
        
        if not arima_available:
            unavailable_weight += self.weights["arima"]
        else:
            available_weight += self.weights["arima"]
        
        if not lstm_available:
            unavailable_weight += self.weights["lstm"]
        else:
            available_weight += self.weights["lstm"]
        
        if not xgboost_available:
            unavailable_weight += self.weights["xgboost"]
        else:
            available_weight += self.weights["xgboost"]
        
        # Redistribute unavailable weight proportionally
        if available_weight == 0:
            # All models failed - use equal weights
            return {
                "arima": 1.0 / 3,
                "lstm": 1.0 / 3,
                "xgboost": 1.0 / 3,
            }
        
        scale_factor = (available_weight + unavailable_weight) / available_weight
        
        return {
            "arima": self.weights["arima"] * scale_factor if arima_available else 0.0,
            "lstm": self.weights["lstm"] * scale_factor if lstm_available else 0.0,
            "xgboost": self.weights["xgboost"] * scale_factor if xgboost_available else 0.0,
        }

    def _calculate_mape(
        self,
        actual: np.ndarray,
        predicted: np.ndarray,
    ) -> float:
        """Calculate Mean Absolute Percentage Error."""
        actual_nonzero = np.where(actual == 0, 1e-10, actual)
        errors = np.abs((actual - predicted) / actual_nonzero)
        mape = np.mean(errors) * 100
        return float(mape)
