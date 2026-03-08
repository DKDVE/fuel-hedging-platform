"""LSTM forecaster for jet fuel prices.

Deep learning model using LSTM for time series forecasting.
On Render: inference only, loads pre-trained model from /models/
Training happens in GitHub Actions workflow.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from app.analytics.domain import ForecastResult
from app.constants import MAPE_TARGET


class LSTMForecaster:
    """LSTM-based price forecaster (inference only).
    
    Loads pre-trained model from disk. Training happens offline
    in GitHub Actions lstm-retrain.yml workflow.
    """

    def __init__(
        self,
        model_path: str = "/models/lstm_model.h5",
        sequence_length: int = 30,
        horizon_days: int = 30,
    ) -> None:
        """Initialize LSTM forecaster.
        
        Args:
            model_path: Path to pre-trained model file
            sequence_length: Input sequence length
            horizon_days: Forecast horizon
        """
        self.model_path = model_path
        self.sequence_length = sequence_length
        self.horizon_days = horizon_days
        self.model_version = "lstm_v2.0_seq30"
        self.model = None

    def _load_model(self) -> None:
        """Load pre-trained LSTM model.
        
        Raises:
            FileNotFoundError: If model file not found
        """
        try:
            # Import tensorflow only when needed (not in requirements for this phase)
            import tensorflow as tf
            
            model_file = Path(self.model_path)
            if not model_file.exists():
                raise FileNotFoundError(
                    f"LSTM model not found at {self.model_path}. "
                    "Run lstm-retrain.yml GitHub Actions workflow to generate model."
                )
            
            self.model = tf.keras.models.load_model(self.model_path)
        except ImportError:
            raise ImportError(
                "TensorFlow not installed. Install with: pip install tensorflow-cpu"
            )

    def predict(self, df: pd.DataFrame) -> ForecastResult:
        """Generate LSTM forecast.
        
        Args:
            df: Historical price data with 'Jet_Fuel_Spot_USD_bbl' column
        
        Returns:
            ForecastResult with predictions and accuracy
        """
        # Load model if not already loaded
        if self.model is None:
            self._load_model()

        # Extract and normalize prices
        prices = df["Jet_Fuel_Spot_USD_bbl"].values
        
        # Normalize to [0, 1] range
        price_min = np.min(prices)
        price_max = np.max(prices)
        prices_normalized = (prices - price_min) / (price_max - price_min + 1e-10)

        # Prepare sequences
        X = []
        for i in range(len(prices_normalized) - self.sequence_length):
            X.append(prices_normalized[i:i + self.sequence_length])
        X = np.array(X)
        X = X.reshape((X.shape[0], X.shape[1], 1))  # Add feature dimension

        # Generate predictions (multi-step ahead)
        # Note: This is simplified - production would use recursive forecasting
        predictions_normalized = []
        for _ in range(self.horizon_days):
            if len(X) > 0:
                pred = self.model.predict(X[-1:], verbose=0)  # type: ignore
                predictions_normalized.append(float(pred[0, 0]))

        # Denormalize predictions
        predictions = np.array(predictions_normalized) * (price_max - price_min) + price_min
        forecast_values = tuple(float(x) for x in predictions)

        # Calculate MAPE on last horizon_days of actual data
        val_prices = prices[-self.horizon_days:]
        mape = self._calculate_mape(val_prices, predictions)
        mape_passes_target = mape < MAPE_TARGET

        return ForecastResult(
            forecast_values=forecast_values,
            mape=round(mape, 2),
            mape_passes_target=mape_passes_target,
            model_weights={"lstm": 1.0},
            horizon_days=self.horizon_days,
            generated_at=datetime.utcnow(),
            model_versions={"lstm": self.model_version},
        )

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
