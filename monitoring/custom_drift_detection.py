"""
Custom drift detector with multiple statistical tests.

This module provides advanced drift detection capabilities beyond
Azure ML's built-in monitoring.
"""

import pandas as pd
import numpy as np
from scipy.stats import ks_2samp, wasserstein_distance
from azure.ai.ml import MLClient
from typing import Dict, Tuple


class DriftDetector:
    """
    Custom drift detector for time series features.
    
    Uses multiple statistical tests:
    - Kolmogorov-Smirnov test
    - Wasserstein distance
    - Population Stability Index (PSI)
    """
    
    def __init__(self, ml_client: MLClient):
        self.ml_client = ml_client
        self.drift_thresholds = {
            "ks_test_pvalue": 0.05,
            "wasserstein_distance": 0.15,
            "psi": 0.25
        }
    
    def calculate_psi(
        self,
        baseline: np.ndarray,
        current: np.ndarray,
        bins: int = 10
    ) -> float:
        """
        Calculate Population Stability Index (PSI).
        
        PSI = Σ (actual% - expected%) * ln(actual% / expected%)
        
        Interpretation:
        - PSI < 0.1: No significant change
        - 0.1 < PSI < 0.25: Some change
        - PSI > 0.25: Significant drift
        """
        breakpoints = np.percentile(baseline, np.linspace(0, 100, bins + 1))
        breakpoints[-1] = breakpoints[-1] + 0.001
        
        baseline_dist = np.histogram(baseline, bins=breakpoints)[0] / len(baseline)
        current_dist = np.histogram(current, bins=breakpoints)[0] / len(current)
        
        baseline_dist = np.where(baseline_dist == 0, 0.0001, baseline_dist)
        current_dist = np.where(current_dist == 0, 0.0001, current_dist)
        
        psi = np.sum((current_dist - baseline_dist) * np.log(current_dist / baseline_dist))
        
        return psi
    
    def detect_drift_for_feature(
        self,
        feature_name: str,
        baseline_data: pd.Series,
        current_data: pd.Series
    ) -> Dict:
        """Detect drift for a single feature using multiple tests."""
        results = {
            "feature": feature_name,
            "tests": {}
        }
        
        # Kolmogorov-Smirnov test
        ks_stat, ks_pvalue = ks_2samp(baseline_data, current_data)
        results["tests"]["ks_test"] = {
            "statistic": float(ks_stat),
            "pvalue": float(ks_pvalue),
            "drift_detected": ks_pvalue < self.drift_thresholds["ks_test_pvalue"]
        }
        
        # Wasserstein distance
        wasserstein_dist = wasserstein_distance(baseline_data, current_data)
        results["tests"]["wasserstein"] = {
            "distance": float(wasserstein_dist),
            "drift_detected": wasserstein_dist > self.drift_thresholds["wasserstein_distance"]
        }
        
        # Population Stability Index
        psi = self.calculate_psi(baseline_data.values, current_data.values)
        results["tests"]["psi"] = {
            "value": float(psi),
            "drift_detected": psi > self.drift_thresholds["psi"]
        }
        
        # Overall drift decision
        results["drift_detected"] = any(
            test["drift_detected"] for test in results["tests"].values()
        )
        
        return results
    
    def detect_drift_for_circuit(
        self,
        plant_id: str,
        circuit_id: str,
        baseline_start_date: str,
        baseline_end_date: str,
        current_start_date: str,
        current_end_date: str
    ) -> Dict:
        """Detect drift for all features of a specific circuit."""
        baseline_df = self.load_data(
            plant_id, circuit_id, baseline_start_date, baseline_end_date
        )
        
        current_df = self.load_data(
            plant_id, circuit_id, current_start_date, current_end_date
        )
        
        feature_columns = [
            "temperature", "pressure", "vibration",
            "current", "voltage", "flow_rate"
        ]
        
        drift_results = {
            "plant_id": plant_id,
            "circuit_id": circuit_id,
            "baseline_period": f"{baseline_start_date} to {baseline_end_date}",
            "current_period": f"{current_start_date} to {current_end_date}",
            "features": []
        }
        
        for feature in feature_columns:
            if feature in baseline_df.columns and feature in current_df.columns:
                feature_result = self.detect_drift_for_feature(
                    feature,
                    baseline_df[feature],
                    current_df[feature]
                )
                drift_results["features"].append(feature_result)
        
        drifted_features = [
            f["feature"] for f in drift_results["features"]
            if f["drift_detected"]
        ]
        
        drift_results["summary"] = {
            "total_features": len(feature_columns),
            "drifted_features_count": len(drifted_features),
            "drifted_features": drifted_features,
            "overall_drift": len(drifted_features) > 0
        }
        
        return drift_results
    
    def load_data(
        self,
        plant_id: str,
        circuit_id: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """Load data from Delta Lake (placeholder - implement actual loading)."""
        # TODO: Implement actual Delta Lake query
        from datetime import datetime, timedelta
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        dates = pd.date_range(start=start, end=end, freq='H')
        
        df = pd.DataFrame({
            'timestamp': dates,
            'plant_id': plant_id,
            'circuit_id': circuit_id,
            'temperature': np.random.randn(len(dates)) * 10 + 50,
            'pressure': np.random.randn(len(dates)) * 5 + 100,
            'vibration': np.random.randn(len(dates)) * 2 + 10,
            'current': np.random.randn(len(dates)) * 3 + 20,
            'voltage': np.random.randn(len(dates)) * 10 + 220,
            'flow_rate': np.random.randn(len(dates)) * 5 + 50
        })
        
        return df
