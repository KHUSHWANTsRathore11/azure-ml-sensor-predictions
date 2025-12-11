"""
Test drift detection module.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "monitoring"))

from custom_drift_detection import DriftDetector


class TestDriftDetector:
    """Test DriftDetector class."""
    
    def test_psi_calculation_no_drift(self):
        """Test PSI calculation with no drift."""
        from unittest.mock import Mock
        
        detector = DriftDetector(Mock())
        
        # Same distribution
        baseline = np.random.normal(0, 1, 1000)
        current = np.random.normal(0, 1, 1000)
        
        psi = detector.calculate_psi(baseline, current)
        
        # PSI should be very small (< 0.1 indicates no drift)
        assert psi < 0.15
    
    def test_psi_calculation_with_drift(self):
        """Test PSI calculation with significant drift."""
        from unittest.mock import Mock
        
        detector = DriftDetector(Mock())
        
        # Different distributions
        baseline = np.random.normal(0, 1, 1000)
        current = np.random.normal(5, 1, 1000)  # Mean shifted by 5
        
        psi = detector.calculate_psi(baseline, current)
        
        # PSI should be large (> 0.25 indicates significant drift)
        assert psi > 0.25
    
    def test_feature_drift_detection(self):
        """Test feature drift detection."""
        from unittest.mock import Mock
        
        detector = DriftDetector(Mock())
        
        # Create data with drift
        baseline_data = pd.Series(np.random.normal(50, 5, 1000))
        current_data = pd.Series(np.random.normal(60, 5, 1000))
        
        result = detector.detect_drift_for_feature(
            "temperature",
            baseline_data,
            current_data
        )
        
        assert result['feature'] == "temperature"
        assert 'tests' in result
        assert 'ks_test' in result['tests']
        assert 'wasserstein' in result['tests']
        assert 'psi' in result['tests']
        assert result['drift_detected'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
