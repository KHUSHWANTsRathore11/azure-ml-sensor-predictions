"""
Training script using custom sensor-forecasting package
"""

import argparse
import os
import mlflow
import yaml
import pandas as pd
from pathlib import Path

# Import from custom package
from sensor_forecasting.models import LSTMForecaster, TimeSeriesPreprocessor
from sensor_forecasting import __version__ as package_version


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--circuit_config", type=str, help="Path to circuit config YAML")
    parser.add_argument("--training_data", type=str, help="Path to training data (MLTable)")
    parser.add_argument("--model_output", type=str, help="Path to save trained model")
    parser.add_argument("--metrics_output", type=str, help="Path to save metrics")
    return parser.parse_args()


def load_config(config_path: str) -> dict:
    """Load circuit configuration"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_training_data(data_path: str) -> pd.DataFrame:
    """Load training data from MLTable"""
    # MLTable should contain a parquet or CSV file
    data_file = None
    for ext in ['parquet', 'csv']:
        potential_file = Path(data_path) / f"data.{ext}"
        if potential_file.exists():
            data_file = potential_file
            break
    
    if data_file is None:
        raise FileNotFoundError(f"No data file found in {data_path}")
    
    if data_file.suffix == '.parquet':
        return pd.read_parquet(data_file)
    else:
        return pd.read_csv(data_file)


def main():
    args = parse_args()
    
    # Load configuration
    config = load_config(args.circuit_config)
    
    plant_id = config['plant_id']
    circuit_id = config['circuit_id']
    model_name = config['model_name']
    cutoff_date = config['cutoff_date']
    
    # Training parameters
    training_params = config.get('training_parameters', {})
    sequence_length = training_params.get('sequence_length', 168)
    forecast_horizon = training_params.get('forecast_horizon', 24)
    lstm_units = training_params.get('lstm_units', 64)
    dropout = training_params.get('dropout', 0.2)
    learning_rate = training_params.get('learning_rate', 0.001)
    epochs = training_params.get('epochs', 50)
    batch_size = training_params.get('batch_size', 32)
    
    # Feature configuration
    feature_cols = config.get('features', ['sensor_value', 'temperature', 'pressure'])
    target_col = config.get('target', 'sensor_value')
    
    print(f"🚀 Training Model: {model_name}")
    print(f"   Plant: {plant_id}")
    print(f"   Circuit: {circuit_id}")
    print(f"   Cutoff Date: {cutoff_date}")
    print(f"   Package Version: {package_version}")
    print(f"   Sequence Length: {sequence_length}")
    print(f"   Forecast Horizon: {forecast_horizon}")
    
    # Start MLflow run
    mlflow.set_experiment(f"circuit-training")
    with mlflow.start_run(run_name=f"{model_name}-{cutoff_date}") as run:
        
        # Log parameters
        mlflow.log_param("plant_id", plant_id)
        mlflow.log_param("circuit_id", circuit_id)
        mlflow.log_param("model_name", model_name)
        mlflow.log_param("cutoff_date", cutoff_date)
        mlflow.log_param("package_version", package_version)
        mlflow.log_param("sequence_length", sequence_length)
        mlflow.log_param("forecast_horizon", forecast_horizon)
        mlflow.log_param("lstm_units", lstm_units)
        mlflow.log_param("dropout", dropout)
        mlflow.log_param("learning_rate", learning_rate)
        mlflow.log_param("epochs", epochs)
        mlflow.log_param("batch_size", batch_size)
        
        # Load data
        print("\n📊 Loading training data...")
        df = load_training_data(args.training_data)
        print(f"   Data shape: {df.shape}")
        
        # Preprocess data
        print("\n🔧 Preprocessing data...")
        preprocessor = TimeSeriesPreprocessor(
            sequence_length=sequence_length,
            forecast_horizon=forecast_horizon,
            scale=True
        )
        
        X, y = preprocessor.fit_transform(df, feature_cols, target_col)
        print(f"   Sequences shape: X={X.shape}, y={y.shape}")
        
        # Train/validation split (80/20)
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        print(f"   Train: {X_train.shape}, Val: {X_val.shape}")
        
        # Build and train model
        print("\n🧠 Building LSTM model...")
        forecaster = LSTMForecaster(
            input_shape=(sequence_length, len(feature_cols)),
            lstm_units=lstm_units,
            dropout=dropout,
            learning_rate=learning_rate
        )
        
        model = forecaster.build_model()
        print(model.summary())
        
        print("\n🏋️  Training model...")
        history = forecaster.train(
            X_train, y_train,
            X_val, y_val,
            epochs=epochs,
            batch_size=batch_size
        )
        
        # Get final metrics
        final_train_loss = history.history['loss'][-1]
        final_val_loss = history.history['val_loss'][-1]
        final_train_mae = history.history['mae'][-1]
        final_val_mae = history.history['val_mae'][-1]
        
        print(f"\n📈 Training Results:")
        print(f"   Train Loss: {final_train_loss:.4f}")
        print(f"   Val Loss: {final_val_loss:.4f}")
        print(f"   Train MAE: {final_train_mae:.4f}")
        print(f"   Val MAE: {final_val_mae:.4f}")
        
        # Log metrics
        mlflow.log_metric("train_loss", final_train_loss)
        mlflow.log_metric("val_loss", final_val_loss)
        mlflow.log_metric("train_mae", final_train_mae)
        mlflow.log_metric("val_mae", final_val_mae)
        
        # Save model
        print(f"\n💾 Saving model to {args.model_output}...")
        os.makedirs(args.model_output, exist_ok=True)
        
        # Save as MLflow model
        mlflow.tensorflow.log_model(
            model=forecaster.model,
            artifact_path="model",
            registered_model_name=model_name
        )
        
        # Also save locally for pipeline output
        model_path = os.path.join(args.model_output, "model")
        forecaster.save(model_path)
        
        # Save metrics
        print(f"\n📊 Saving metrics to {args.metrics_output}...")
        os.makedirs(args.metrics_output, exist_ok=True)
        
        metrics = {
            "model_name": model_name,
            "plant_id": plant_id,
            "circuit_id": circuit_id,
            "cutoff_date": cutoff_date,
            "package_version": package_version,
            "train_loss": float(final_train_loss),
            "val_loss": float(final_val_loss),
            "train_mae": float(final_train_mae),
            "val_mae": float(final_val_mae),
            "run_id": run.info.run_id
        }
        
        metrics_file = os.path.join(args.metrics_output, "metrics.yaml")
        with open(metrics_file, 'w') as f:
            yaml.dump(metrics, f)
        
        print("\n✅ Training complete!")
        print(f"   Run ID: {run.info.run_id}")
        print(f"   Model: {model_name}")


if __name__ == "__main__":
    main()
