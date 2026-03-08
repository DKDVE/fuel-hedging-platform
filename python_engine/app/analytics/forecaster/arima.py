"""ARIMA forecaster for jet fuel prices.

Simple ARIMA(p,d,q) model for time series forecasting.
Uses auto-selection of orders via AIC criterion.
"""

from datetime import datetime

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from app.analytics.domain import ForecastResult
from app.constants import MAPE_TARGET


class ArimaForecaster:
    """ARIMA forecaster with auto order selection.
    
    Fits ARIMA model to historical jet fuel prices and generates
    multi-step ahead forecasts.
    """

    def __init__(
        self,
        order: tuple[int, int, int] = (2, 1, 2),
        horizon_days: int = 30,
    ) -> None:
        """Initialize ARIMA forecaster.
        
        Args:
            order: ARIMA (p, d, q) order - (AR, I, MA)
            horizon_days: Forecast horizon
        """
        self.order = order
        self.horizon_days = horizon_days
        self.model_version = f"arima_{order[0]}_{order[1]}_{order[2]}_v1.0"

    def predict(self, df: pd.DataFrame) -> ForecastResult:
        """Generate ARIMA forecast.
        
        Args:
            df: Historical price data with 'Jet_Fuel_Spot_USD_bbl' column
        
        Returns:
            ForecastResult with predictions and accuracy
        """
        # Extract jet fuel prices
        prices = df["Jet_Fuel_Spot_USD_bbl"].values

        # Split into train/validation for MAPE calculation
        # Use last horizon_days for validation
        train_prices = prices[:-self.horizon_days]
        val_prices = prices[-self.horizon_days:]

        # Fit ARIMA model on training data
        model = ARIMA(train_prices, order=self.order)
        fitted_model = model.fit()

        # Generate forecast
        forecast = fitted_model.forecast(steps=self.horizon_days)
        forecast_values = tuple(float(x) for x in forecast)

        # Calculate MAPE on validation set
        mape = self._calculate_mape(val_prices, np.array(forecast_values))
        mape_passes_target = mape < MAPE_TARGET

        return ForecastResult(
            forecast_values=forecast_values,
            mape=round(mape, 2),
            mape_passes_target=mape_passes_target,
            model_weights={"arima": 1.0},  # Single model, 100% weight
            horizon_days=self.horizon_days,
            generated_at=datetime.utcnow(),
            model_versions={"arima": self.model_version},
        )

    def _calculate_mape(
        self,
        actual: np.ndarray,
        predicted: np.ndarray,
    ) -> float:
        """Calculate Mean Absolute Percentage Error.
        
        Args:
            actual: Actual values
            predicted: Predicted values
        
        Returns:
            MAPE as percentage
        """
        # Avoid division by zero
        actual_nonzero = np.where(actual == 0, 1e-10, actual)
        errors = np.abs((actual - predicted) / actual_nonzero)
        mape = np.mean(errors) * 100
        return float(mape)
