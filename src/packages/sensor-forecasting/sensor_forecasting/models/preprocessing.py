"""
Time series preprocessing utilities
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from typing import Tuple, Optional


class TimeSeriesPreprocessor:
    """
    Preprocess time series data for LSTM training
    """
    
    def __init__(
        self,
        sequence_length: int = 168,  # 7 days hourly
        forecast_horizon: int = 24,  # 1 day ahead
        scale: bool = True
    ):
        """
        Initialize preprocessor
        
        Args:
            sequence_length: Number of timesteps to look back
            forecast_horizon: Number of timesteps to predict ahead
            scale: Whether to apply standard scaling
        """
        self.sequence_length = sequence_length
        self.forecast_horizon = forecast_horizon
        self.scale = scale
        self.scaler = StandardScaler() if scale else None
        
    def create_sequences(
        self,
        data: np.ndarray,
        target_col: int = 0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for LSTM training
        
        Args:
            data: Input data array (n_samples, n_features)
            target_col: Index of target column
            
        Returns:
            X: Input sequences (n_samples, sequence_length, n_features)
            y: Target values (n_samples,)
        """
        X, y = [], []
        
        for i in range(len(data) - self.sequence_length - self.forecast_horizon + 1):
            # Input sequence
            X.append(data[i:i + self.sequence_length])
            
            # Target value (forecast_horizon steps ahead)
            y.append(data[i + self.sequence_length + self.forecast_horizon - 1, target_col])
        
        return np.array(X), np.array(y)
    
    def fit_transform(
        self,
        df: pd.DataFrame,
        feature_cols: list,
        target_col: str
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fit scaler and create sequences
        
        Args:
            df: Input dataframe
            feature_cols: List of feature column names
            target_col: Target column name
            
        Returns:
            X, y: Preprocessed sequences
        """
        # Extract features
        data = df[feature_cols].values
        
        # Fit and transform scaler
        if self.scaler:
            data = self.scaler.fit_transform(data)
        
        # Get target column index
        target_idx = feature_cols.index(target_col)
        
        # Create sequences
        X, y = self.create_sequences(data, target_col=target_idx)
        
        return X, y
    
    def transform(
        self,
        df: pd.DataFrame,
        feature_cols: list,
        target_col: str
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Transform data (scaler already fitted)
        
        Args:
            df: Input dataframe
            feature_cols: List of feature column names
            target_col: Target column name
            
        Returns:
            X, y: Preprocessed sequences
        """
        # Extract features
        data = df[feature_cols].values
        
        # Transform with fitted scaler
        if self.scaler:
            data = self.scaler.transform(data)
        
        # Get target column index
        target_idx = feature_cols.index(target_col)
        
        # Create sequences
        X, y = self.create_sequences(data, target_col=target_idx)
        
        return X, y
    
    def inverse_transform_target(self, y: np.ndarray) -> np.ndarray:
        """Inverse transform target values"""
        if self.scaler is None:
            return y
        
        # Create dummy array with same shape as fitted data
        n_features = self.scaler.scale_.shape[0]
        dummy = np.zeros((len(y), n_features))
        dummy[:, 0] = y  # Assuming target is first column
        
        # Inverse transform and extract target column
        return self.scaler.inverse_transform(dummy)[:, 0]
