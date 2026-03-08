"""LSTM model training script for jet fuel price forecasting.

This script trains an LSTM neural network on historical price data.
The trained model is saved to /models/lstm_model.h5 for inference.
"""

import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import structlog
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
from tensorflow.keras import layers

logger = structlog.get_logger()


class LSTMTrainer:
    """Train LSTM model for time series forecasting."""

    def __init__(
        self,
        lookback_days: int = 60,
        forecast_horizon: int = 30,
        lstm_units: int = 64,
        dropout_rate: float = 0.2,
    ) -> None:
        """Initialize LSTM trainer.

        Args:
            lookback_days: Number of historical days for features
            forecast_horizon: Number of days to forecast
            lstm_units: Number of LSTM units in hidden layer
            dropout_rate: Dropout rate for regularization
        """
        self.lookback_days = lookback_days
        self.forecast_horizon = forecast_horizon
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate

        self.scaler = StandardScaler()
        self.model: Optional[keras.Model] = None

    def prepare_data(
        self,
        df: pd.DataFrame,
        train_split: float = 0.8,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Prepare training and validation data.

        Args:
            df: DataFrame with price history
            train_split: Fraction of data for training

        Returns:
            X_train, y_train, X_val, y_val arrays
        """
        # Extract jet fuel prices
        prices = df["Jet_Fuel_Spot_USD_bbl"].values.reshape(-1, 1)

        # Scale data
        prices_scaled = self.scaler.fit_transform(prices)

        # Create sequences
        X, y = [], []
        for i in range(len(prices_scaled) - self.lookback_days - self.forecast_horizon + 1):
            X.append(prices_scaled[i : i + self.lookback_days])
            y.append(prices_scaled[i + self.lookback_days : i + self.lookback_days + self.forecast_horizon])

        X = np.array(X)
        y = np.array(y)

        # Train/val split
        split_idx = int(len(X) * train_split)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        logger.info(
            "data_prepared",
            train_samples=len(X_train),
            val_samples=len(X_val),
            lookback=self.lookback_days,
            horizon=self.forecast_horizon,
        )

        return X_train, y_train, X_val, y_val

    def build_model(self, input_shape: tuple) -> keras.Model:
        """Build LSTM architecture.

        Args:
            input_shape: Shape of input sequences (lookback_days, 1)

        Returns:
            Compiled Keras model
        """
        model = keras.Sequential(
            [
                layers.Input(shape=input_shape),
                layers.LSTM(self.lstm_units, return_sequences=True),
                layers.Dropout(self.dropout_rate),
                layers.LSTM(self.lstm_units // 2, return_sequences=False),
                layers.Dropout(self.dropout_rate),
                layers.Dense(self.forecast_horizon),
                layers.Reshape((self.forecast_horizon, 1)),
            ],
            name="jet_fuel_lstm",
        )

        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss="mse",
            metrics=["mae"],
        )

        logger.info("model_built", params=model.count_params())
        return model

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        epochs: int = 50,
        batch_size: int = 32,
    ) -> keras.callbacks.History:
        """Train the LSTM model.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            epochs: Number of training epochs
            batch_size: Batch size

        Returns:
            Training history
        """
        self.model = self.build_model(input_shape=(self.lookback_days, 1))

        # Callbacks
        early_stop = keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=10,
            restore_best_weights=True,
        )

        reduce_lr = keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=5,
            min_lr=0.00001,
        )

        logger.info("training_start", epochs=epochs, batch_size=batch_size)

        history = self.model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stop, reduce_lr],
            verbose=1,
        )

        logger.info(
            "training_complete",
            final_train_loss=history.history["loss"][-1],
            final_val_loss=history.history["val_loss"][-1],
        )

        return history

    def save_model(self, model_path: Path) -> None:
        """Save trained model to disk.

        Args:
            model_path: Path to save model (.h5 file)
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        model_path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(model_path)

        logger.info("model_saved", path=str(model_path))

    def evaluate(self, X_val: np.ndarray, y_val: np.ndarray) -> dict[str, float]:
        """Evaluate model performance.

        Args:
            X_val: Validation features
            y_val: Validation labels

        Returns:
            Dictionary with evaluation metrics
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        loss, mae = self.model.evaluate(X_val, y_val, verbose=0)

        # Calculate MAPE
        y_pred = self.model.predict(X_val, verbose=0)

        # Inverse transform to original scale
        y_val_orig = self.scaler.inverse_transform(y_val.reshape(-1, 1)).reshape(y_val.shape)
        y_pred_orig = self.scaler.inverse_transform(y_pred.reshape(-1, 1)).reshape(y_pred.shape)

        # MAPE calculation
        mape = np.mean(np.abs((y_val_orig - y_pred_orig) / y_val_orig)) * 100

        metrics = {
            "mse": float(loss),
            "mae": float(mae),
            "mape": float(mape),
        }

        logger.info("model_evaluated", **metrics)
        return metrics


def train_lstm_model(
    csv_path: Optional[Path] = None,
    model_output_path: Optional[Path] = None,
    epochs: int = 50,
) -> dict[str, float]:
    """Train LSTM model on historical data.

    Args:
        csv_path: Path to historical CSV data
        model_output_path: Path to save trained model
        epochs: Number of training epochs

    Returns:
        Evaluation metrics
    """
    # Default paths
    if csv_path is None:
        csv_path = Path(__file__).parent.parent.parent.parent / "data" / "fuel_hedging_dataset.csv"

    if model_output_path is None:
        model_output_path = Path(__file__).parent.parent.parent.parent / "models" / "lstm_model.h5"

    # Load data
    logger.info("loading_data", path=str(csv_path))
    df = pd.read_csv(csv_path)

    # Initialize trainer
    trainer = LSTMTrainer(
        lookback_days=60,
        forecast_horizon=30,
        lstm_units=64,
        dropout_rate=0.2,
    )

    # Prepare data
    X_train, y_train, X_val, y_val = trainer.prepare_data(df, train_split=0.8)

    # Train model
    trainer.train(X_train, y_train, X_val, y_val, epochs=epochs)

    # Evaluate
    metrics = trainer.evaluate(X_val, y_val)

    # Save model
    trainer.save_model(model_output_path)

    logger.info(
        "lstm_training_complete",
        model_path=str(model_output_path),
        mape=metrics["mape"],
    )

    return metrics


if __name__ == "__main__":
    # Enable eager execution for debugging
    tf.config.run_functions_eagerly(True)

    # Configure logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )

    # Train model
    metrics = train_lstm_model(epochs=50)

    print("\n" + "=" * 70)
    print("LSTM TRAINING COMPLETE")
    print("=" * 70)
    print(f"MSE: {metrics['mse']:.4f}")
    print(f"MAE: {metrics['mae']:.4f}")
    print(f"MAPE: {metrics['mape']:.2f}%")
    print("=" * 70)

    sys.exit(0)
