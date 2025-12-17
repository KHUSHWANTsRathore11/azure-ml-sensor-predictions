# MLOps Pipeline Architecture

Complete guide to the Azure ML training and deployment pipelines.

## Overview

**8-Stage Training Pipeline:**
1. Register Environment
2. Promote Environment (conditional)
3. Register Components
4. Register ML Tables
5. Submit Training Jobs
6. Monitor Training
7. Register Models
8. Promote Models (with approval)

**Deployment Pipelines:**
- Test Deployment (from Registry)
- Prod Deployment (from Registry)

---

## Training Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Stage 1: RegisterEnvironment                                    │
│ - Check components/environments/sensor-forecasting-env.yaml version                         │
│ - Register if new version                                       │
│ - Output: newEnvRegistered (true/false)                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 2: PromoteEnvironment (conditional)                       │
│ - Only runs if newEnvRegistered = true                          │
│ - Requires approval (registry-promotion environment)            │
│ - Shares environment to Azure ML Registry                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 3: RegisterComponents                                     │
│ - Register training-pipeline-component.yaml                     │
│ - Check version, skip if exists                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 4: RegisterMLTables                                       │
│ - Register MLTable definitions for each circuit                 │
│ - Points to Delta Lake tables with version                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 5: SubmitTraining                                         │
│ - Detect changed circuits (git or manual)                       │
│ - Calculate training hash for each circuit                      │
│ - Submit training jobs for circuits with hash changes           │
│ - Output: training_jobs.json                                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 6: MonitorTraining                                        │
│ - Poll submitted jobs every N seconds                           │
│ - Wait up to M hours for completion                             │
│ - Exponential backoff for polling                               │
│ - Output: completed_jobs.json                                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 7: RegisterModels                                         │
│ - Register models from completed jobs                           │
│ - Tag with training_hash for lineage                            │
│ - Output: registered_models.json                                │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 8: PromoteModels                                          │
│ - Trigger child pipeline for each model                         │
│ - Each child requires approval (registry-promotion)             │
│ - Share model to Registry with exponential backoff              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stage Details

### Stage 1: RegisterEnvironment

**Purpose:** Register custom training environment in Dev workspace

**Logic:**
```bash
# Read version from components/environments/sensor-forecasting-env.yaml
ENV_NAME=$(grep "^name:" components/environments/sensor-forecasting-env.yaml | awk '{print $2}')
ENV_VERSION=$(grep "^version:" components/environments/sensor-forecasting-env.yaml | awk '{print $2}')

# Check if exists
if ! az ml environment show --name "$ENV_NAME" --version "$ENV_VERSION"; then
  # Register new version
  az ml environment create --file components/environments/sensor-forecasting-env.yaml
  echo "##vso[task.setvariable variable=newEnvRegistered;isOutput=true]true"
else
  echo "##vso[task.setvariable variable=newEnvRegistered;isOutput=true]false"
fi
```

**Outputs:** `newEnvRegistered` (true/false)

### Stage 2: PromoteEnvironment

**Purpose:** Share environment to Registry for Test/Prod use

**Condition:** Only runs if `newEnvRegistered = true`

**Approval:** Requires `registry-promotion` environment approval

**Logic:**
```bash
# Promote to registry
az ml environment create \
  --file components/environments/sensor-forecasting-env.yaml \
  --registry-name "$(registryName)" \
  --resource-group "$(registryResourceGroup)"
```

### Stage 3: RegisterComponents

**Purpose:** Register pipeline component in Dev workspace

**Logic:**
```bash
# Read from component file
COMP_NAME=$(grep "^name:" components/training-pipeline-component.yaml | awk '{print $2}')
COMP_VERSION=$(grep "^version:" components/training-pipeline-component.yaml | awk '{print $2}')

# Register if not exists
if ! az ml component show --name "$COMP_NAME" --version "$COMP_VERSION"; then
  az ml component create --file components/training-pipeline-component.yaml
fi
```

### Stage 4: RegisterMLTables

**Purpose:** Register MLTable data assets for each circuit

**Logic:**
```python
for circuit in circuits:
    mltable_path = f"data/mltables/{circuit['plant_id']}/{circuit['circuit_id']}"
    
    # MLTable points to Delta table with version
    az ml data create \
        --name f"{circuit['plant_id']}-{circuit['circuit_id']}-data" \
        --version circuit['delta_version'] \
        --path mltable_path
```

### Stage 5: SubmitTraining

**Purpose:** Submit training jobs for changed circuits

**Circuit Detection:**
```python
# Option 1: Git-based (default)
changed_circuits = detect_changed_circuits_from_git()

# Option 2: Manual override
if manualCircuits != 'AUTO':
    changed_circuits = parse_manual_circuits(manualCircuits)
```

**Training Hash:**
```python
hash_components = {
    'cutoff_date': circuit['cutoff_date'],
    'delta_version': circuit['delta_version'],
    'pipeline_component_version': circuit['pipeline_component_version'],
    'training_days': circuit['training_days'],
    'hyperparameters': circuit['hyperparameters']
}
training_hash = md5(json.dumps(hash_components, sort_keys=True))[:12]
```

**Retraining Decision:**
```python
current_hash = calculate_training_hash(circuit)
last_hash = get_last_model_training_hash(circuit['model_name'])

if current_hash != last_hash:
    submit_training_job(circuit, current_hash)
```

**Output:** `training_jobs.json`

### Stage 6: MonitorTraining

**Purpose:** Wait for training jobs to complete

**Polling Strategy:**
```python
# Exponential backoff
initial_delay = 30s
max_delay = 300s (5 min)
max_wait = monitoringMaxWaitHours * 3600

while elapsed < max_wait:
    check_job_status()
    if all_complete:
        break
    sleep(min(current_delay, max_delay))
    current_delay *= 2
```

**Output:** `completed_jobs.json`

### Stage 7: RegisterModels

**Purpose:** Register models from completed jobs

**Logic:**
```python
for job in completed_jobs:
    if job['status'] == 'Completed':
        model_path = f"azureml://jobs/{job['name']}/outputs/model"
        
        az ml model create \
            --name job['model_name'] \
            --version auto \
            --path model_path \
            --set tags.training_hash=job['training_hash']
```

**Output:** `registered_models.json`

### Stage 8: PromoteModels

**Purpose:** Trigger per-model promotion with approval

**Logic:**
```bash
for model in registered_models:
    # Trigger child pipeline
    az pipelines run \
        --name "promote-single-model-pipeline" \
        --parameters \
            modelName=$model_name \
            modelVersion=$model_version \
            trainingHash=$training_hash
```

**Child Pipeline (promote-single-model-pipeline.yml):**
1. Requires approval (`registry-promotion` environment)
2. Shares model to Registry
3. Polls with exponential backoff for propagation

---

## Deployment Pipelines

### Test Deployment

**Trigger:** Manual or release branch

**Source:** Azure ML Registry

**Flow:**
```
1. List models in Registry
2. For each model:
   - Check if deployed in Test workspace
   - Deploy if not exists or version changed
3. Configure canary deployment (50% traffic)
4. Monitor deployment health
```

**Approval:** `test-deployment` environment

### Prod Deployment

**Trigger:** Manual from main branch

**Source:** Azure ML Registry

**Flow:**
```
1. List models in Registry
2. For each model:
   - Check if deployed in Prod workspace
   - Deploy with blue-green strategy
3. Traffic ramp: 0% → 10% → 25% → 50% → 100%
4. Auto-rollback if error threshold exceeded
```

**Approval:** `prod-deployment` environment (2 approvers)

---

## Error Handling

### Training Job Failures

**Automatic Retry:**
```yaml
# In pipeline component
retry:
  max_retries: 2
  timeout: 3600
```

**Manual Retry:**
```bash
# Specify circuits manually
manualCircuits: "PLANT001/CIRCUIT01,PLANT002/CIRCUIT02"
```

### Deployment Failures

**Auto-Rollback (Prod only):**
```yaml
auto_rollback:
  enabled: true
  error_threshold: 5%
  latency_threshold: 2000ms
```

**Manual Rollback:**
```bash
# Run rollback pipeline
az pipelines run --name "rollback-pipeline"
```

---

## Best Practices

1. **Environment Changes** - Bump version in `components/environments/sensor-forecasting-env.yaml`
2. **Component Changes** - Bump version in `components/training-pipeline-component.yaml`
3. **Circuit Changes** - Update `config/circuits.yaml` (triggers retraining)
4. **Manual Training** - Use `manualCircuits` parameter
5. **Approval** - Always review model metrics before approving promotion
6. **Monitoring** - Check Azure ML Studio for job details
7. **Rollback** - Test rollback procedure in Test environment first
