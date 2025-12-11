"""
Sensor Forecasting Package
Custom TensorFlow models and utilities for time series forecasting
"""

import sys
import os

# Add version to package
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from version import __version__

__all__ = ['__version__']
