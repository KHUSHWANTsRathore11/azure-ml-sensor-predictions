"""
Unit tests for training pipeline.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from train_model import TimeSeriesForecaster


class TestTimeSeriesForecaster:
    """Test TimeSeriesForecaster class."""
    
    def test_model_initialization(self):
        """Test model initialization."""
        forecaster = TimeSeriesForecaster(
            lstm_units=64,
            learning_rate=0.001,
            sequence_length=24,
            forecast_horizon=7
        )
        
        assert forecaster.lstm_units == 64
        assert forecaster.learning_rate == 0.001
        assert forecaster.sequence_length == 24
        assert forecaster.forecast_horizon == 7
    
    def test_prepare_sequences(self):
        """Test sequence preparation."""
        forecaster = TimeSeriesForecaster(
            sequence_length=10,
            forecast_horizon=3
        )
        
        # Create test data
        data = np.random.randn(100, 5)
        X, y = forecaster.prepare_sequences(data)
        
        # Check shapes
        assert X.shape == (87, 10, 5)  # 100 - 10 - 3 = 87 sequences
        assert y.shape == (87, 3)  # forecast_horizon = 3
    
    def test_model_building(self):
        """Test model architecture building."""
        forecaster = TimeSeriesForecaster(
            lstm_units=32,
            sequence_length=10,
            forecast_horizon=5
        )
        
        model = forecaster.build_model(n_features=6)
        
        assert model is not None
        assert len(model.layers) == 5  # LSTM, Dropout, LSTM, Dropout, Dense
        assert model.input_shape == (None, 10, 6)
        assert model.output_shape == (None, 5)


class TestDataLoading:
    """Test data loading functions."""
    
    def test_circuit_config_loading(self):
        """Test loading circuit configuration."""
        from train_model import load_circuit_config
        
        # This test requires the config file to exist
        config_path = Path(__file__).parent.parent / "config" / "circuits.yaml"
        
        if config_path.exists():
            config = load_circuit_config(
                str(config_path),
                "PLANT001",
                "CIRCUIT01"
            )
            
            assert config['plant_id'] == "PLANT001"
            assert config['circuit_id'] == "CIRCUIT01"
            assert 'features' in config
            assert 'hyperparameters' in config


def test_imports():
    """Test that all required packages can be imported."""
    try:
        import tensorflow
        import sklearn
        import pandas
        import numpy
        import mlflow
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import required package: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
