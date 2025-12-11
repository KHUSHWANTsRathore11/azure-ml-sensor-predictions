"""
Train time series forecasting model for a single circuit.

This script trains an LSTM model for sensor predictions and logs
metrics to MLflow.

Usage:
    python scripts/train_model.py \
        --plant-id PLANT001 \
        --circuit-id CIRCUIT01 \
        --config-path config/circuits.yaml \
        --data-path azureml://datastores/workspaceblobstore/paths/mltable/
"""

import argparse
import yaml
import mlflow
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


class TimeSeriesForecaster:
    """LSTM-based time series forecasting model."""
    
    def __init__(
        self,
        lstm_units: int = 64,
        learning_rate: float = 0.001,
        sequence_length: int = 24,
        forecast_horizon: int = 7
    ):
        self.lstm_units = lstm_units
        self.learning_rate = learning_rate
        self.sequence_length = sequence_length
        self.forecast_horizon = forecast_horizon
        self.model = None
        self.scaler = StandardScaler()
    
    def build_model(self, n_features: int):
        """Build LSTM model architecture."""
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
    
    def prepare_sequences(self, data: np.ndarray):
        """Prepare sequences for LSTM training."""
        X, y = [], []
        
        for i in range(len(data) - self.sequence_length - self.forecast_horizon):
            X.append(data[i:i + self.sequence_length])
            y.append(data[i + self.sequence_length:i + self.sequence_length + self.forecast_horizon, 0])
        
        return np.array(X), np.array(y)
    
    def train(
        self,
        train_data: pd.DataFrame,
        val_data: pd.DataFrame,
        epochs: int = 50,
        batch_size: int = 32
    ):
        """Train the model."""
        # Scale data
        train_scaled = self.scaler.fit_transform(train_data)
        val_scaled = self.scaler.transform(val_data)
        
        # Prepare sequences
        X_train, y_train = self.prepare_sequences(train_scaled)
        X_val, y_val = self.prepare_sequences(val_scaled)
        
        # Build model
        self.build_model(train_data.shape[1])
        
        # Early stopping
        early_stop = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        # Train
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stop],
            verbose=1
        )
        
        return history
    
    def predict(self, data: pd.DataFrame):
        """Make predictions."""
        scaled_data = self.scaler.transform(data)
        X, _ = self.prepare_sequences(scaled_data)
        predictions = self.model.predict(X)
        return predictions


def load_circuit_config(config_path: str, plant_id: str, circuit_id: str) -> dict:
    """Load configuration for specific circuit."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    for circuit in config['circuits']:
        if circuit['plant_id'] == plant_id and circuit['circuit_id'] == circuit_id:
            return circuit
    
    raise ValueError(f"Circuit {plant_id}/{circuit_id} not found in config")


def load_data(data_path: str, plant_id: str, circuit_id: str, cutoff_date: str, training_days: int) -> tuple:
    """Load and prepare training data from Delta Lake."""
    # Calculate date range
    cutoff = datetime.strptime(cutoff_date, "%Y-%m-%d")
    start_date = cutoff - timedelta(days=training_days)
    
    # TODO: Replace with actual Delta Lake query
    # This is a placeholder - in production, load from Delta Lake via MLTable
    print(f"Loading data from {start_date.strftime('%Y-%m-%d')} to {cutoff_date}")
    
    # For now, generate synthetic data for demonstration
    dates = pd.date_range(start=start_date, end=cutoff, freq='H')
    n_samples = len(dates)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'plant_id': plant_id,
        'circuit_id': circuit_id,
        'temperature': np.random.randn(n_samples) * 10 + 50,
        'pressure': np.random.randn(n_samples) * 5 + 100,
        'vibration': np.random.randn(n_samples) * 2 + 10,
        'current': np.random.randn(n_samples) * 3 + 20,
        'voltage': np.random.randn(n_samples) * 10 + 220,
        'flow_rate': np.random.randn(n_samples) * 5 + 50
    })
    
    # Split into train/val (80/20)
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]
    
    return train_df, val_df


def main():
    parser = argparse.ArgumentParser(description="Train time series forecasting model")
    parser.add_argument("--plant-id", required=True, help="Plant ID")
    parser.add_argument("--circuit-id", required=True, help="Circuit ID")
    parser.add_argument("--config-path", default="config/circuits.yaml", help="Path to circuits config")
    parser.add_argument("--data-path", required=True, help="Path to data (MLTable)")
    parser.add_argument("--output-dir", default="outputs", help="Output directory for model")
    
    args = parser.parse_args()
    
    print(f"🚀 Starting training for {args.plant_id}/{args.circuit_id}")
    
    # Load circuit configuration
    circuit_config = load_circuit_config(args.config_path, args.plant_id, args.circuit_id)
    print(f"📋 Configuration loaded: {circuit_config['description']}")
    
    # Start MLflow run
    mlflow.start_run()
    
    # Log parameters
    mlflow.log_params({
        "plant_id": args.plant_id,
        "circuit_id": args.circuit_id,
        "lstm_units": circuit_config['hyperparameters']['lstm_units'],
        "learning_rate": circuit_config['hyperparameters']['learning_rate'],
        "epochs": circuit_config['hyperparameters']['epochs'],
        "batch_size": circuit_config['hyperparameters']['batch_size'],
        "forecast_horizon": circuit_config['forecast_horizon'],
        "cutoff_date": circuit_config['cutoff_date']
    })
    
    # Load data
    print("📊 Loading training data...")
    train_df, val_df = load_data(
        args.data_path,
        args.plant_id,
        args.circuit_id,
        circuit_config['cutoff_date'],
        circuit_config['training_days']
    )
    
    # Select features
    feature_cols = circuit_config['features']
    train_features = train_df[feature_cols]
    val_features = val_df[feature_cols]
    
    # Initialize model
    forecaster = TimeSeriesForecaster(
        lstm_units=circuit_config['hyperparameters']['lstm_units'],
        learning_rate=circuit_config['hyperparameters']['learning_rate'],
        forecast_horizon=circuit_config['forecast_horizon']
    )
    
    # Train model
    print("🏋️ Training model...")
    history = forecaster.train(
        train_features,
        val_features,
        epochs=circuit_config['hyperparameters']['epochs'],
        batch_size=circuit_config['hyperparameters']['batch_size']
    )
    
    # Evaluate
    print("📈 Evaluating model...")
    val_predictions = forecaster.predict(val_features)
    
    # Calculate metrics (using first forecast horizon value)
    y_true = val_features.values[forecaster.sequence_length:, 0][:len(val_predictions)]
    y_pred = val_predictions[:, 0]  # First horizon prediction
    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    
    # Log metrics
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
    
    # Save model
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    model_path = output_path / "model"
    forecaster.model.save(model_path)
    mlflow.keras.log_model(forecaster.model, "model")
    
    print(f"💾 Model saved to {model_path}")
    
    mlflow.end_run()
    
    return 0


if __name__ == "__main__":
    exit(main())
