# Multi-Model Strategy

[← Back to README](../README.md)

---

## Overview

Architecture for managing **75-200 independent time series forecasting models** with per-circuit configuration, batch endpoints, and parallel training.

---

## 1. Scale & Organization

### Model Count
- **Total Models:** 75-200
- **Distribution:** 5-10 circuits per plant × 15-20 plants
- **Deployment:** One batch endpoint per plant, one deployment per circuit

### Organization Structure

| Component | Structure | Count | Example |
|-----------|-----------|-------|---------|
| **Plants** | Physical facilities | 15-20 | P001, P002, ... |
| **Circuits** | Sensors per plant | 5-10 per plant | C001, C002, ... |
| **Models** | One per circuit | 75-200 total | Model for P001/C001 |
| **Batch Endpoints** | One per plant | 15-20 | `batch-endpoint-plant-P001` |
| **Deployments** | One per circuit | 5-10 per endpoint | `deployment-circuit-C001` |
| **MLflow Experiments** | One per circuit | 75-200 | `plant_P001_circuit_C001` |
| **Config Files** | One per circuit | 75-200 | `config/plants/P001/C001.yml` |

---

## 2. Configuration Management

### Master Config

**File:** `config/plants_circuits.yml`

```yaml
plants:
  - plant_id: "P001"
    plant_name: "Manufacturing Plant 1"
    circuits:
      - circuit_id: "C001"
        circuit_name: "Assembly Line A Sensor"
      - circuit_id: "C002"
        circuit_name: "Packaging Line B Sensor"
  
  - plant_id: "P002"
    plant_name: "Distribution Center 2"
    circuits:
      - circuit_id: "C001"
        circuit_name: "Conveyor Belt Sensor"
```

### Per-Circuit Config

**File:** `config/plants/{plant_id}/{circuit_id}.yml`

```yaml
plant_id: "P001"
circuit_id: "C001"

training:
  cutoff_date: "2025-12-09"        # Drives training data
  environment_version: "1.5.0"     # Fixed environment version
  hyperparameters:
    sequence_length: 24
    lstm_units: 128
    dropout: 0.2
    learning_rate: 0.001
    batch_size: 32
    epochs: 50
  data_filters:
    sensor_id: "SENSOR_P001_C001"
    feature_columns: ["temperature", "pressure", "vibration"]

deployment:
  compute_instance_type: "Standard_DS3_v2"
  mini_batch_size: 100
  timeout_minutes: 60
```

### Config Change Detection

**Script:** `scripts/detect_config_changes.py`

```python
# Git diff to detect changed circuit configs
changed_files = subprocess.run(
    ["git", "diff", "--name-only", f"origin/main...{pr_branch}"],
    capture_output=True, text=True
).stdout.strip().split("\n")

changed_circuits = []
for file_path in changed_files:
    if file_path.startswith("config/plants/") and file_path.endswith(".yml"):
        # Extract plant_id and circuit_id
        parts = file_path.split("/")
        plant_id = parts[2]
        circuit_id = parts[3].replace(".yml", "")
        
        # Load cutoff_date from config
        with open(file_path) as f:
            config = yaml.safe_load(f)
        
        changed_circuits.append({
            "plant_id": plant_id,
            "circuit_id": circuit_id,
            "cutoff_date": config["training"]["cutoff_date"]
        })

# Output as JSON for pipeline matrix
print(json.dumps(changed_circuits))
```

---

## 3. Batch Endpoints Architecture

### Per-Plant Endpoints

**Endpoint Naming:** `batch-endpoint-plant-{plant_id}`

**Example:**
```
batch-endpoint-plant-P001  (Plant 1)
  ├── deployment-circuit-C001  (Circuit 1)
  ├── deployment-circuit-C002  (Circuit 2)
  └── deployment-circuit-C003  (Circuit 3)

batch-endpoint-plant-P002  (Plant 2)
  ├── deployment-circuit-C001
  └── deployment-circuit-C002
```

### Deployment Properties

```yaml
deployment-circuit-C001:
  model: azureml://registries/shared-registry/models/sensor-model/versions/12
  environment: azureml://registries/shared-registry/environments/custom-tf-env/versions/1.5.0
  compute: batch-compute-cluster
  instance_count: 1
  mini_batch_size: 100
  max_concurrency_per_instance: 1
  timeout: 3600  # 1 hour
  environment_variables:
    PLANT_ID: "P001"
    CIRCUIT_ID: "C001"
  tags:
    plant_id: "P001"
    circuit_id: "C001"
    model_version: "12"
    environment_version: "1.5.0"
    deployed_at: "2025-12-09T14:30:00Z"
```

### Invocation Strategy

**Daily inference requires 75-200 separate invocations:**

```python
# scripts/invoke_all_batch_endpoints.py
import yaml
from azure.ai.ml import MLClient

ml_client = MLClient(...)

# Load all plant-circuit combinations
with open("config/plants_circuits.yml") as f:
    config = yaml.safe_load(f)

for plant in config["plants"]:
    plant_id = plant["plant_id"]
    endpoint_name = f"batch-endpoint-plant-{plant_id}"
    
    for circuit in plant["circuits"]:
        circuit_id = circuit["circuit_id"]
        deployment_name = f"deployment-circuit-{circuit_id}"
        
        # Invoke specific deployment
        job = ml_client.batch_endpoints.invoke(
            endpoint_name=endpoint_name,
            deployment_name=deployment_name,  # Target specific circuit
            input=input_data
        )
        
        print(f"Started job {job.name} for {plant_id}/{circuit_id}")
```

---

## 4. Model Registry Strategy

### Naming Convention

**Model Name:** `sensor-model` (shared name)  
**Differentiation:** Via tags

### Model Tags

```python
{
    "plant_id": "P001",
    "circuit_id": "C001",
    "cutoff_date": "2025-12-09",
    "environment_version": "1.5.0",
    "data_asset_version": "2025-12-09",
    "pr_number": "PR-1234",
    "pr_author": "john.doe@company.com",
    "git_commit_sha": "a1b2c3d4",
    "hyperparameters_hash": "abc12345",
    "mae": "0.15",
    "rmse": "0.23",
    "r2": "0.89",
    "trained_at": "2025-12-09T12:00:00Z"
}
```

### Querying Models

```python
# Find latest model for specific circuit
models = ml_client.models.list(name="sensor-model")
circuit_models = [
    m for m in models 
    if m.tags.get("plant_id") == "P001" 
    and m.tags.get("circuit_id") == "C001"
]
latest_model = max(circuit_models, key=lambda m: m.version)
```

---

## 5. Parallel Training

### Strategy

**Azure DevOps matrix strategy** with controlled parallelism:

```yaml
jobs:
  - job: TrainModels
    strategy:
      maxParallel: 5  # Train 5 circuits at once
      matrix: $[ variables.changedCircuits ]  # Dynamic from git diff
    steps:
      - script: |
          # Train model for $(plant_id)/$(circuit_id)
```

### Rationale

- **maxParallel: 5** prevents resource exhaustion
- **Dynamic matrix** only trains changed circuits
- **Independent jobs** per circuit for fault tolerance
- **Parallel execution** reduces total pipeline time

### Example Execution

```
PR changes 8 circuit configs → 8 training jobs

Wave 1 (parallel):
  - P001/C001 ✓
  - P001/C002 ✓
  - P001/C003 ✓
  - P002/C001 ✓
  - P002/C002 ✓

Wave 2 (parallel):
  - P003/C001 ✓
  - P003/C002 ✓
  - P004/C001 ✓
```

---

## 6. MLflow Experiment Tracking

### Per-Circuit Experiments

**Experiment Name:** `plant_{plant_id}_circuit_{circuit_id}`

```python
import mlflow

mlflow.set_experiment(f"plant_{plant_id}_circuit_{circuit_id}")

with mlflow.start_run(run_name=f"PR-{pr_number}_{cutoff_date}"):
    mlflow.log_param("cutoff_date", cutoff_date)
    mlflow.log_param("lstm_units", 128)
    mlflow.log_param("dropout", 0.2)
    
    # Training...
    
    mlflow.log_metric("mae", mae)
    mlflow.log_metric("rmse", rmse)
    mlflow.log_metric("r2", r2)
    
    mlflow.log_artifact("model.pkl")
```

### Benefits

- **Isolated experiments** per circuit
- **Historical tracking** of all training runs
- **Compare hyperparameters** across runs
- **Track metrics over time**

---

## 7. Scaling Considerations

### Current Scale (75-200 models)

| Metric | Value |
|--------|-------|
| Training jobs per PR | 1-20 (only changed circuits) |
| Parallel training | 5 at once |
| Training time per model | ~15-30 min |
| Total training time (worst case) | ~120 min for 20 models |
| Daily inference invocations | 75-200 |
| Inference time per circuit | ~5-10 min |

### Future Scaling (500+ models)

**Optimizations needed:**
- Increase `maxParallel` to 10-15
- Use low-priority VMs for cost savings
- Implement model caching strategies
- Consider dedicated compute per plant

---

## 8. Config-Driven Workflow

### Training Trigger

```
1. Update config file (change cutoff_date or hyperparameters)
2. Create PR
3. Git diff detects changed configs
4. Build Pipeline triggers
5. Register MLTable for changed circuits
6. Train models in parallel
7. Publish artifacts for Release Pipeline
```

### No Manual Intervention

- **Config changes** drive all training
- **Same config** used for PR and manual training
- **Reproducible** via git history
- **Auditable** via PR reviews

---

## Related Documents

- [← Data Architecture](02-data-architecture.md)
- [→ Environment Management](04-environment-management.md)
- [→ Build Pipeline](05-build-pipeline.md)
