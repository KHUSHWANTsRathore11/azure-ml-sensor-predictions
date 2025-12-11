"""
LSTM Training Component - Pure Python implementation.
No Azure ML SDK dependencies for training logic.
"""
import argparse
import json
import yaml
import mlflow
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib


class TimeSeriesForecaster:
    """LSTM-based time series forecasting model."""
    
    def __init__(self, lstm_units=64, learning_rate=0.001, sequence_length=24, forecast_horizon=7):
        self.lstm_units = lstm_units
        self.learning_rate = learning_rate
        self.sequence_length = sequence_length
        self.forecast_horizon = forecast_horizon
        self.model = None
        self.scaler = StandardScaler()
    
    def build_model(self, n_features):
        """Build LSTM architecture."""
        model = keras.Sequential([
            keras.layers.LSTM(
                self.lstm_units,
                activation='relu',
                return_sequences=True,
                input_shape=(self.sequence_length, n_features)
            ),
            keras.layers.Dropout(0.2),
            keras.layers.LSTM(self.lstm_units // 2, activation='relu'),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(self.forecast_horizon)
        ])
        
        optimizer = keras.optimizers.Adam(learning_rate=self.learning_rate)
        model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])
        
        self.model = model
        return model
    
    def prepare_sequences(self, data):
        """Prepare sequences for LSTM."""
        X, y = [], []
        for i in range(len(data) - self.sequence_length - self.forecast_horizon):
            X.append(data[i:i + self.sequence_length])
            y.append(data[i + self.sequence_length:i + self.sequence_length + self.forecast_horizon, 0])
        return np.array(X), np.array(y)
    
    def train(self, train_data, val_data, epochs=50, batch_size=32):
        """Train the model."""
        train_scaled = self.scaler.fit_transform(train_data)
        val_scaled = self.scaler.transform(val_data)
        
        X_train, y_train = self.prepare_sequences(train_scaled)
        X_val, y_val = self.prepare_sequences(val_scaled)
        
        self.build_model(train_data.shape[1])
        
        early_stop = keras.callbacks.EarlyStopping(
            monitor='val_loss', patience=10, restore_best_weights=True
        )
        
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stop],
            verbose=1
        )
        
        return history


def load_config(config_path):
    """Load circuit configuration."""
    with open(config_path, 'r') as f:
        if config_path.endswith('.yaml') or config_path.endswith('.yml'):
            return yaml.safe_load(f)
        else:
            return json.load(f)


def load_training_data(data_path):
    """Load data from MLTable."""
    import mltable
    tbl = mltable.load(data_path)
    df = tbl.to_pandas_dataframe()
    return df


def train_model(circuit_config_path, training_data_path, hyperparameters_path, 
                model_output_path, metrics_output_path, artifacts_output_path):
    """Main training function."""
    
    # Load configuration
    config = load_config(circuit_config_path)
    print(f"🔧 Configuration loaded")
    print(f"   Plant: {config.get('plant_id', 'N/A')}")
    print(f"   Circuit: {config.get('circuit_id', 'N/A')}")
    print(f"   Model Name: {config.get('model_name', 'N/A')}")
    print(f"   Cutoff Date: {config.get('cutoff_date', 'N/A')}")
    
    # Load hyperparameters
    if hyperparameters_path:
        hyperparams = load_config(hyperparameters_path)
    else:
        hyperparams = config.get('hyperparameters', {})
    
    # Set MLflow experiment and run name
    experiment_name = "circuit-training"
    run_name = f"{config.get('plant_id', 'unknown')}-{config.get('circuit_id', 'unknown')}-{config.get('cutoff_date', 'unknown')}"
    
    mlflow.set_experiment(experiment_name)
    
    # Start MLflow run
    mlflow.start_run(run_name=run_name)
    mlflow.log_params({
        "plant_id": config.get('plant_id'),
        "circuit_id": config.get('circuit_id'),
        "model_name": config.get('model_name'),
        "cutoff_date": config.get('cutoff_date'),
        "training_days": config.get('training_days'),
        "forecast_horizon": config.get('forecast_horizon'),
        "lstm_units": hyperparams.get('lstm_units', 64),
        "learning_rate": hyperparams.get('learning_rate', 0.001),
        "epochs": hyperparams.get('epochs', 50),
        "batch_size": hyperparams.get('batch_size', 32)
    })
    
    # Load training data
    print("📊 Loading training data...")
    df = load_training_data(training_data_path)
    print(f"   Loaded {len(df)} records")
    
    # Filter by plant/circuit if needed
    if 'plant_id' in config and 'plant_id' in df.columns:
        df = df[df['plant_id'] == config['plant_id']]
    if 'circuit_id' in config and 'circuit_id' in df.columns:
        df = df[df['circuit_id'] == config['circuit_id']]
    
    # Split train/val
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]
    
    # Select features
    feature_cols = config.get('features', ['temperature', 'pressure', 'vibration'])
    train_features = train_df[feature_cols]
    val_features = val_df[feature_cols]
    
    # Initialize and train model
    print("🏋️ Training model...")
    forecaster = TimeSeriesForecaster(
        lstm_units=hyperparams.get('lstm_units', 64),
        learning_rate=hyperparams.get('learning_rate', 0.001),
        forecast_horizon=config.get('forecast_horizon', 7)
    )
    
    history = forecaster.train(
        train_features,
        val_features,
        epochs=hyperparams.get('epochs', 50),
        batch_size=hyperparams.get('batch_size', 32)
    )
    
    # Calculate final metrics
    val_scaled = forecaster.scaler.transform(val_features)
    X_val, y_val = forecaster.prepare_sequences(val_scaled)
    val_predictions = forecaster.model.predict(X_val)
    
    mae = mean_absolute_error(y_val[:, 0], val_predictions[:, 0])
    rmse = np.sqrt(mean_squared_error(y_val[:, 0], val_predictions[:, 0]))
    r2 = r2_score(y_val[:, 0], val_predictions[:, 0])
    
    # Log metrics to MLflow
    mlflow.log_metrics({
        "mae": mae,
        "rmse": rmse,
        "r2_score": r2,
        "final_train_loss": history.history['loss'][-1],
        "final_val_loss": history.history['val_loss'][-1]
    })
    
    print(f"✅ Training complete!")
    print(f"   MAE: {mae:.4f}")
    print(f"   RMSE: {rmse:.4f}")
    print(f"   R²: {r2:.4f}")
    
    # Save model with MLflow and register with model name from config
    print("💾 Saving model...")
    
    # Get model name from config
    model_name = config.get('model_name', f"{config.get('plant_id', 'unknown').lower()}-{config.get('circuit_id', 'unknown').lower()}")
    
    # Log model with auto-registration
    mlflow.tensorflow.log_model(
        forecaster.model, 
        "model",
        registered_model_name=model_name  # Auto-register with this name
    )
    
    print(f"✅ Model registered as: {model_name}")
    
    # Save scaler
    artifacts_path = Path(artifacts_output_path)
    artifacts_path.mkdir(parents=True, exist_ok=True)
    joblib.dump(forecaster.scaler, artifacts_path / "scaler.pkl")
    
    # Save metrics to file
    metrics = {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2_score": float(r2),
        "train_loss": float(history.history['loss'][-1]),
        "val_loss": float(history.history['val_loss'][-1]),
        "trained_at": datetime.now().isoformat(),
        "plant_id": config.get('plant_id'),
        "circuit_id": config.get('circuit_id'),
        "model_name": config.get('model_name'),
        "cutoff_date": config.get('cutoff_date')
    }
    
    metrics_file = Path(metrics_output_path)
    metrics_file.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    mlflow.end_run()
    
    print(f"✅ Model saved to: {model_output_path}")
    print(f"✅ Metrics saved to: {metrics_output_path}")


def main():
    parser = argparse.ArgumentParser(description="Train LSTM model")
    parser.add_argument("--circuit-config", required=True)
    parser.add_argument("--training-data", required=True)
    parser.add_argument("--hyperparameters", required=False)
    parser.add_argument("--model-output", required=True)
    parser.add_argument("--metrics-output", required=True)
    parser.add_argument("--artifacts-output", required=True)
    
    args = parser.parse_args()
    
    train_model(
        args.circuit_config,
        args.training_data,
        args.hyperparameters,
        args.model_output,
        args.metrics_output,
        args.artifacts_output
    )


if __name__ == "__main__":
    main()
