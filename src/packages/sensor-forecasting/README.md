# Sensor Forecasting Package

Custom TensorFlow package for time series forecasting with Docker environment.

## Structure

```
src/packages/sensor-forecasting/
├── Dockerfile              # Docker image definition
├── requirements.txt        # Base dependencies
├── setup.py               # Package setup
├── version.py             # Package version (= Environment version)
└── sensor_forecasting/    # Python package
    ├── __init__.py
    └── models/
        ├── __init__.py
        ├── lstm.py               # LSTMForecaster class
        └── preprocessing.py      # TimeSeriesPreprocessor class
```

## Version Management

Package version and environment version are managed manually and kept in sync.

```python
# src/packages/sensor-forecasting/version.py
__version__ = "1.0.0"
```

```yaml
# components/environments/sensor-forecasting-env.yaml
name: sensor-forecasting-env
version: "1.0.0"
tags:
  package_version: "1.0.0"
```

**To release a new version:**

1. Update package version:
   ```python
   # src/packages/sensor-forecasting/version.py
   __version__ = "1.1.0"
   ```

2. Update environment version:
   ```yaml
   # components/environments/sensor-forecasting-env.yaml
   name: sensor-forecasting-env
   version: "1.1.0"
   tags:
     package_version: "1.1.0"
   ```

3. Commit both files together:
   ```bash
   git add src/packages/sensor-forecasting/version.py
   git add components/environments/sensor-forecasting-env.yaml
   git commit -m "bump: sensor-forecasting to v1.1.0"
   ```

4. Push to trigger pipeline:
   ```bash
   git push origin main
   ```

5. Pipeline automatically:
   - Detects environment.yaml changed (git diff)
   - Registers new environment version
   - Azure ML builds Docker image with new package
   - **Retrains ALL circuits** (infrastructure changed)

## Docker Image

The Docker image is built by Azure ML from the Dockerfile in this directory.

**Build context:** This package directory  
**Base image:** `tensorflow/tensorflow:2.13.0-gpu`  
**Contents:**
- TensorFlow 2.13.0
- Custom `sensor-forecasting` package
- All dependencies from `requirements.txt`

## Using the Package

### In Training Components

```python
# components/training/train-lstm-model/src/train_with_package.py
from sensor_forecasting.models import LSTMForecaster, TimeSeriesPreprocessor

# Create preprocessor
preprocessor = TimeSeriesPreprocessor(
    sequence_length=168,
    forecast_horizon=24
)

# Preprocess data
X, y = preprocessor.fit_transform(df, feature_cols, target_col)

# Create and train model
forecaster = LSTMForecaster(
    input_shape=(168, len(feature_cols)),
    lstm_units=64
)
model = forecaster.build_model()
history = forecaster.train(X_train, y_train, X_val, y_val)
```

### Package Classes

#### `LSTMForecaster`
LSTM-based time series forecasting model.

**Methods:**
- `build_model()` - Build model architecture
- `train(X_train, y_train, X_val, y_val, epochs, batch_size)` - Train model
- `predict(X)` - Make predictions
- `save(path)` - Save model
- `load(path)` - Load model

#### `TimeSeriesPreprocessor`
Time series preprocessing utilities.

**Methods:**
- `fit_transform(df, feature_cols, target_col)` - Fit scaler and create sequences
- `transform(df, feature_cols, target_col)` - Transform data with fitted scaler
- `inverse_transform_target(y)` - Inverse transform target values

## Local Development

### Install Package Locally

```bash
cd src/packages/sensor-forecasting
pip install -e .
```

### Test Package

```python
import sensor_forecasting
print(sensor_forecasting.__version__)

from sensor_forecasting.models import LSTMForecaster
forecaster = LSTMForecaster(input_shape=(168, 10))
model = forecaster.build_model()
print(model.summary())
```

### Build Docker Image Locally

```bash
cd src/packages/sensor-forecasting
docker build -t sensor-forecasting:local .
docker run -it sensor-forecasting:local
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-10 | Initial release with LSTM forecaster |

## Breaking Changes

When making breaking changes:
1. Bump MAJOR version (1.0.0 → 2.0.0)
2. Document changes in this README
3. All circuits will be retrained automatically

## Non-Breaking Changes

When adding features:
1. Bump MINOR version (1.0.0 → 1.1.0)
2. All circuits will be retrained for consistency

## Bug Fixes

For bug fixes:
1. Bump PATCH version (1.0.0 → 1.0.1)
2. All circuits will be retrained
