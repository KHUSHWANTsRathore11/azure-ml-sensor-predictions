# Model Type Configuration for Circuits

## Overview

Models can now be registered as **`custom_model`** or **`mlflow_model`** type.

**Default:** `custom_model`

## Configuration

Add `model_type` field to any circuit in `config/circuits.yaml`:

```yaml
circuits:
  - plant_id: PLANT001
    circuit_id: CIRCUIT01
    model_name: plant001-circuit01-model
    model_type: custom_model  # ← Add this field
    cutoff_date: "2024-01-15"
    features:
      - temperature
      - pressure
```

## Model Types

### custom_model (Default)
```yaml
model_type: custom_model
```

**Use when:**
- Using custom scoring/inference logic
- Model format is not MLflow
- Need full control over model artifacts

### mlflow_model
```yaml
model_type: mlflow_model
```

**Use when:**
- Model is saved using MLflow
- Want MLflow's automatic serving
- Using MLflow tracking/experiments

## How It Works

**Training Pipeline Flow:**

```
1. submit_training_jobs.py
   ├─ Reads model_type from circuits.yaml
   ├─ Includes in job submission
   └─ Stores in training_jobs.json

2. monitor_training_jobs.py
   └─ Passes through to monitoring_result.json

3. register_models.py
   ├─ Reads model_type from job info
   ├─ Registers with specified type
   └─ Adds model_type tag

4. promote_to_registry.py
   └─ Model type preserved in registry
```

## Example Configurations

### Custom Model (Recommended)
```yaml
circuits:
  - plant_id: PLANT001
    circuit_id: CIRCUIT01
    model_name: plant001-sensor-predictor
    model_type: custom_model
    features:
      - sensor_reading
      - timestamp
```

### MLflow Model
```yaml
circuits:
  - plant_id: PLANT002
    circuit_id: CIRCUIT05
    model_name: plant002-anomaly-detector
    model_type: mlflow_model
    features:
      - vibration
      - temperature
```

### Mixed (Default if not specified)
```yaml
circuits:
  # This will use custom_model (default)
  - plant_id: PLANT003
    circuit_id: CIRCUIT10
    model_name: plant003-forecaster
    # model_type not specified → defaults to custom_model
```

## Verification

After model registration, check the tags:

```bash
az ml model show \
  --name plant001-sensor-predictor \
  --version 1 \
  --workspace-name mlops-dev-workspace
```

Output will include:
```json
{
  "type": "custom_model",
  "tags": {
    "model_type": "custom_model",
    "plant_id": "PLANT001",
    "circuit_id": "CIRCUIT01"
  }
}
```

## Benefits

✅ **Flexibility** - Choose model type per circuit  
✅ **Default** - Defaults to custom_model (most common use case)  
✅ **Backward Compatible** - Existing configs work (use default)  
✅ **Traceable** - Model type stored in tags
