# Model Artifacts

This directory stores trained ML model files used by the analytics pipeline.

## Files

| File | Description | Size |
|------|-------------|------|
| `lstm_model.h5` | Pre-trained LSTM forecaster (TensorFlow/Keras) | ~2MB |

## How models are generated

Models are trained by the GitHub Actions workflow `lstm-retrain.yml`,
which runs every Sunday at 02:00 UTC and commits the updated `.h5` file here.

To train manually:
```bash
cd python_engine
pip install "tensorflow-cpu>=2.13.0,<2.16.0"
python app/services/train_lstm.py
```

This saves `lstm_model.h5` to this directory.

## Inference

The running platform (`LSTMForecaster`) loads `lstm_model.h5` at inference time.
If the file does not exist, the ensemble forecaster silently falls back to
ARIMA + XGBoost only (no error, no crash, just 45% weight redistributed).
