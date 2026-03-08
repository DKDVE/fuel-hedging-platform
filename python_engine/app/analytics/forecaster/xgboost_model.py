"""XGBoost forecaster for jet fuel prices.

Gradient boosting model using XGBoost with engineered features.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import StandardScaler

from app.analytics.domain import ForecastResult
from app.constants import MAPE_TARGET


class XGBoostForecaster:
    """XGBoost-based price forecaster.
    
    Uses lagged prices, crack spreads, and volatility as features.
    """

    def __init__(
        self,
        n_lags: int = 7,
        horizon_days: int = 30,
        n_estimators: int = 100,
        max_depth: int = 5,
        learning_rate: float = 0.1,
    ) -> None:
        """Initialize XGBoost forecaster.
        
        Args:
            n_lags: Number of lagged price features
            horizon_days: Forecast horizon
            n_estimators: Number of boosting rounds
            max_depth: Maximum tree depth
            learning_rate: Learning rate
        """
        self.n_lags = n_lags
        self.horizon_days = horizon_days
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.model_version = f"xgboost_v1.0_lags{n_lags}"
        self.scaler = StandardScaler()

    def predict(self, df: pd.DataFrame) -> ForecastResult:
        """Generate XGBoost forecast.
        
        Args:
            df: Historical price data with all columns
        
        Returns:
            ForecastResult with predictions and accuracy
        """
        # Prepare features
        features_df = self._create_features(df)

        # Split into train/validation
        train_df = features_df.iloc[:-self.horizon_days]
        val_df = features_df.iloc[-self.horizon_days:]

        X_train = train_df.drop(columns=["target"])
        y_train = train_df["target"]
        X_val = val_df.drop(columns=["target"])
        y_val = val_df["target"]

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        # Train XGBoost model
        model = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            random_state=42,
            objective="reg:squarederror",
        )
        model.fit(X_train_scaled, y_train)

        # Generate forecast
        predictions = model.predict(X_val_scaled)
        forecast_values = tuple(float(x) for x in predictions)

        # Calculate MAPE
        mape = self._calculate_mape(y_val.values, predictions)
        mape_passes_target = mape < MAPE_TARGET

        return ForecastResult(
            forecast_values=forecast_values,
            mape=round(mape, 2),
            mape_passes_target=mape_passes_target,
            model_weights={"xgboost": 1.0},
            horizon_days=self.horizon_days,
            generated_at=datetime.utcnow(),
            model_versions={"xgboost": self.model_version},
        )

    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create lagged features and technical indicators.
        
        Args:
            df: Historical price data
        
        Returns:
            DataFrame with features and target
        """
        features = pd.DataFrame()

        # Target: next day's jet fuel price
        features["target"] = df["Jet_Fuel_Spot_USD_bbl"].shift(-1)

        # Lagged jet fuel prices
        for lag in range(1, self.n_lags + 1):
            features[f"jet_fuel_lag_{lag}"] = df["Jet_Fuel_Spot_USD_bbl"].shift(lag)

        # Lagged crack spread
        for lag in range(1, min(self.n_lags, 3) + 1):
            features[f"crack_spread_lag_{lag}"] = df["Crack_Spread_USD_bbl"].shift(lag)

        # Lagged volatility
        features["volatility_lag_1"] = df["Volatility_Index_pct"].shift(1)

        # Rolling statistics
        features["jet_fuel_ma_7"] = (
            df["Jet_Fuel_Spot_USD_bbl"].rolling(window=7).mean()
        )
        features["jet_fuel_std_7"] = (
            df["Jet_Fuel_Spot_USD_bbl"].rolling(window=7).std()
        )

        # Drop rows with NaN (due to lagging and rolling)
        features = features.dropna()

        return features

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
