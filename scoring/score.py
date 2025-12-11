"""
Scoring script for batch endpoint deployment.

This script is executed by Azure ML batch endpoints to generate predictions.
"""

import os
import json
import joblib
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from opencensus.ext.azure.log_exporter import AzureLogHandler

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add Azure Log Handler if connection string available
connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if connection_string:
    logger.addHandler(AzureLogHandler(connection_string=connection_string))


def init():
    """
    Initialize scoring script.
    Called once when the deployment is created or updated.
    """
    global model, scaler
    
    try:
        # Get model path
        model_path = os.path.join(os.getenv("AZUREML_MODEL_DIR", ""), "model")
        
        # Load model
        import tensorflow as tf
        model = tf.keras.models.load_model(model_path)
        
        # Load scaler if exists
        scaler_path = Path(model_path).parent / "scaler.pkl"
        if scaler_path.exists():
            scaler = joblib.load(scaler_path)
        else:
            scaler = None
        
        logger.info("Model loaded successfully", extra={
            "custom_dimensions": {
                "model_path": model_path,
                "model_version": os.getenv("MODEL_VERSION", "unknown"),
                "scaler_loaded": scaler is not None
            }
        })
        
        print(f"✅ Model initialized from {model_path}")
        
    except Exception as e:
        logger.error(f"Model initialization failed: {str(e)}", extra={
            "custom_dimensions": {
                "error_type": type(e).__name__,
                "model_path": os.getenv("AZUREML_MODEL_DIR", "")
            }
        })
        raise


def run(mini_batch):
    """
    Score a mini batch of files.
    
    Args:
        mini_batch: List of file paths to score
        
    Returns:
        List of predictions
    """
    import time
    
    results = []
    
    for file_path in mini_batch:
        start_time = time.time()
        
        try:
            # Load data
            if file_path.endswith('.parquet'):
                df = pd.read_parquet(file_path)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            # Extract metadata
            plant_id = df['plant_id'].iloc[0] if 'plant_id' in df.columns else "unknown"
            circuit_id = df['circuit_id'].iloc[0] if 'circuit_id' in df.columns else "unknown"
            
            # Select features (exclude metadata columns)
            feature_cols = [col for col in df.columns if col not in ['plant_id', 'circuit_id', 'timestamp']]
            features = df[feature_cols].values
            
            # Scale if scaler available
            if scaler is not None:
                features = scaler.transform(features)
            
            # Reshape for LSTM (add sequence dimension if needed)
            if len(features.shape) == 2:
                features = np.expand_dims(features, axis=0)
            
            # Make predictions
            predictions = model.predict(features, verbose=0)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Log successful prediction
            logger.info("Prediction completed", extra={
                "custom_dimensions": {
                    "plant_id": plant_id,
                    "circuit_id": circuit_id,
                    "num_records": len(df),
                    "latency_ms": latency_ms,
                    "prediction_shape": str(predictions.shape),
                    "prediction_mean": float(np.mean(predictions)),
                    "prediction_std": float(np.std(predictions))
                }
            })
            
            # Prepare result
            result = {
                "file": os.path.basename(file_path),
                "plant_id": plant_id,
                "circuit_id": circuit_id,
                "predictions": predictions.tolist(),
                "latency_ms": latency_ms,
                "status": "success"
            }
            
            results.append(result)
            
            print(f"✅ Scored {file_path} - {len(df)} records in {latency_ms:.2f}ms")
            
        except Exception as e:
            # Log error
            logger.error(f"Prediction failed: {str(e)}", extra={
                "custom_dimensions": {
                    "file_path": file_path,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            })
            
            result = {
                "file": os.path.basename(file_path),
                "error": str(e),
                "error_type": type(e).__name__,
                "status": "failed"
            }
            
            results.append(result)
            
            print(f"❌ Failed to score {file_path}: {str(e)}")
    
    return results


def shutdown():
    """
    Cleanup when deployment is deleted.
    """
    logger.info("Scoring script shutdown", extra={
        "custom_dimensions": {
            "timestamp": pd.Timestamp.now().isoformat()
        }
    })
    print("🛑 Scoring script shutdown")
