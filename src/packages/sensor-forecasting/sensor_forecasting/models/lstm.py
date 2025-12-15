"""
Custom LSTM model for sensor forecasting
"""

import tensorflow as tf
from tensorflow import keras
from typing import Tuple, Optional


class LSTMForecaster:
    """
    LSTM-based time series forecasting model
    """
    
    def __init__(
        self,
        input_shape: Tuple[int, int],
        lstm_units: int = 64,
        dropout: float = 0.2,
        learning_rate: float = 0.001,
    ):
        """
        Initialize LSTM forecaster
        
        Args:
            input_shape: (sequence_length, n_features)
            lstm_units: Number of LSTM units
            dropout: Dropout rate
            learning_rate: Learning rate for optimizer
        """
        self.input_shape = input_shape
        self.lstm_units = lstm_units
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.model = None
        
    def build_model(self) -> keras.Model:
        """Build LSTM model architecture"""
        
        model = keras.Sequential([
            keras.layers.LSTM(
                self.lstm_units,
                input_shape=self.input_shape,
                return_sequences=True
            ),
            keras.layers.Dropout(self.dropout),
            keras.layers.LSTM(self.lstm_units // 2),
            keras.layers.Dropout(self.dropout),
            keras.layers.Dense(32, activation='relu'),
            keras.layers.Dense(1)
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss='mse',
            metrics=['mae', 'mse']
        )
        
        self.model = model
        return model
    
    def train(
        self,
        X_train,
        y_train,
        X_val,
        y_val,
        epochs: int = 50,
        batch_size: int = 32,
        callbacks: Optional[list] = None
    ):
        """Train the model"""
        
        if self.model is None:
            self.build_model()
        
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks or [],
            verbose=1
        )
        
        return history
    
    def predict(self, X):
        """Make predictions"""
        if self.model is None:
            raise ValueError("Model not built or loaded")
        return self.model.predict(X)
    
    def save(self, path: str):
        """Save model"""
        if self.model is None:
            raise ValueError("Model not built")
        self.model.save(path)
    
    def load(self, path: str):
        """Load model"""
        self.model = keras.models.load_model(path)
