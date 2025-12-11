# Testing and Validation Guide

This guide provides scripts and commands to test the Azure ML setup before running the full pipeline.

## Quick Start

### 1. Test Setup
```bash
./scripts/test_setup.sh <workspace-name> <resource-group>
```

This script validates:
- ✅ Azure CLI and ML extension installation
- ✅ Workspace connectivity
- ✅ Python environment
- ✅ Circuit config generation
- ✅ Change detection logic
- ✅ Environment configuration
- ✅ Component definitions
- ✅ Pipeline definitions
- ✅ Documentation completeness

### 2. Quick Reference
```bash
./scripts/quick_reference.sh
```

Displays common Azure ML CLI commands for:
- Environment operations
- Component operations
- Data asset (MLTable) operations
- Job submission and monitoring
- Model operations
- Batch endpoint operations

## Manual Testing Steps

### Step 1: Register Environment
```bash
az ml environment create \
  --file config/environment.yaml \
  --workspace-name mlw-dev \
  --resource-group rg-mlops-dev
```

**Expected Output:**
```
Name: sensor-forecasting-env
Version: 1.0.0
```

**Verify:**
```bash
az ml environment show \
  --name sensor-forecasting-env \
  --workspace-name mlw-dev \
  --resource-group rg-mlops-dev
```

### Step 2: Register Components
```bash
# Training component
az ml component create \
  --file components/training/train-lstm-model/component.yaml \
  --workspace-name mlw-dev \
  --resource-group rg-mlops-dev

# Scoring component
az ml component create \
  --file components/scoring/batch-score/component.yaml \
  --workspace-name mlw-dev \
  --resource-group rg-mlops-dev
```

**Expected Output:**
```
Name: train_lstm_model
Version: 1.0.0

Name: batch_score
Version: 1.0.0
```

**Verify:**
```bash
az ml component list \
  --workspace-name mlw-dev \
  --resource-group rg-mlops-dev \
  --output table
```

### Step 3: Register MLTable Data Asset
```bash
# Example for PLANT001_CIRCUIT01
az ml data create \
  --name PLANT001_CIRCUIT01 \
  --version 2025-11-01 \
  --type mltable \
  --path azureml://datastores/workspaceblobstore/paths/mltable/PLANT001_CIRCUIT01/ \
  --workspace-name mlw-dev \
  --resource-group rg-mlops-dev
```

**Expected Output:**
```
Name: PLANT001_CIRCUIT01
Version: 2025-11-01
Type: mltable
```

**Verify:**
```bash
az ml data show \
  --name PLANT001_CIRCUIT01 \
  --version 2025-11-01 \
  --workspace-name mlw-dev \
  --resource-group rg-mlops-dev
```

### Step 4: Submit Training Pipeline
```bash
az ml job create \
  --file pipelines/single-circuit-training.yaml \
  --workspace-name mlw-dev \
  --resource-group rg-mlops-dev \
  --set inputs.circuit_config.path="config/circuits/PLANT001_CIRCUIT01.yaml" \
  --set inputs.training_data.path="azureml:PLANT001_CIRCUIT01:2025-11-01" \
  --set tags.test=true
```

**Expected Output:**
```
Job submitted: <job-name>
```

**Monitor:**
```bash
# Stream logs
az ml job stream --name <job-name> --workspace-name mlw-dev --resource-group rg-mlops-dev

# Check status
az ml job show --name <job-name> --workspace-name mlw-dev --resource-group rg-mlops-dev
```

### Step 5: Verify Model Registration
```bash
# List models
az ml model list \
  --workspace-name mlw-dev \
  --resource-group rg-mlops-dev \
  --output table

# Show specific model
az ml model show \
  --name plant001-circuit01 \
  --workspace-name mlw-dev \
  --resource-group rg-mlops-dev
```

**Expected:**
- Model name: `plant001-circuit01`
- Version: `1` (auto-incremented)
- Type: MLflow

## Testing Change Detection

### Test 1: No Changes
```bash
python3 scripts/detect_config_changes.py --target-branch main --output test_output.json
cat test_output.json
```

**Expected Output:**
```json
[]
```

### Test 2: With Changes
```bash
# Make a change to circuits.yaml
# Then run detection
python3 scripts/detect_config_changes.py --target-branch main --output test_output.json
cat test_output.json
```

**Expected Output:**
```json
[
  {
    "plant_id": "PLANT001",
    "circuit_id": "CIRCUIT01",
    "cutoff_date": "2025-11-01",
    "model_name": "plant001-circuit01",
    "change_type": "modified"
  }
]
```

## Testing Circuit Config Generation

```bash
python3 scripts/generate_circuit_configs.py

# Verify files created
ls -l config/circuits/

# Check content
cat config/circuits/PLANT001_CIRCUIT01.yaml
```

**Expected:**
- Files created: `PLANT001_CIRCUIT01.yaml`, `PLANT001_CIRCUIT02.yaml`, etc.
- Each file contains complete circuit configuration

## Integration Testing with Azure DevOps

### Test Build Pipeline

1. **Push changes to branch:**
```bash
git add .
git commit -m "Test component-based architecture"
git push origin feature/test-pipeline
```

2. **Create PR to main:**
- Pipeline should trigger automatically
- Watch pipeline execution in Azure DevOps

3. **Monitor stages:**
- Stage 1: Register Infrastructure (should complete in ~2-3 min)
- Stage 2: Parallel Training (depends on circuit count)
- Stage 3: Validate Models (should complete in ~1 min)

### Verify Pipeline Outputs

**After Stage 1:**
```bash
# Check environment
az ml environment show --name sensor-forecasting-env --workspace-name mlw-dev --resource-group rg-mlops-dev

# Check components
az ml component list --workspace-name mlw-dev --resource-group rg-mlops-dev -o table

# Check MLTable assets
az ml data list --workspace-name mlw-dev --resource-group rg-mlops-dev -o table
```

**After Stage 2:**
```bash
# Check training jobs
az ml job list --workspace-name mlw-dev --resource-group rg-mlops-dev --tag build_id=<build-id> -o table
```

**After Stage 3:**
```bash
# Check models with tags
az ml model list --workspace-name mlw-dev --resource-group rg-mlops-dev --tag validated=true -o table
```

## Troubleshooting

### Common Issues

**1. Environment registration fails**
```bash
# Check conda syntax
conda env create -f config/environment.yaml --dry-run

# Check Azure ML quota
az ml compute list --workspace-name mlw-dev --resource-group rg-mlops-dev
```

**2. Component registration fails**
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('components/training/train-lstm-model/component.yaml'))"

# Check environment reference
az ml environment show --name sensor-forecasting-env --workspace-name mlw-dev --resource-group rg-mlops-dev
```

**3. Training job fails**
```bash
# Get detailed logs
az ml job stream --name <job-name> --workspace-name mlw-dev --resource-group rg-mlops-dev

# Download outputs
az ml job download --name <job-name> --workspace-name mlw-dev --resource-group rg-mlops-dev

# Check data asset
az ml data show --name PLANT001_CIRCUIT01 --version 2025-11-01 --workspace-name mlw-dev --resource-group rg-mlops-dev
```

**4. Model not found**
```bash
# Check if training completed
az ml job show --name <job-name> --workspace-name mlw-dev --resource-group rg-mlops-dev --query status

# Check MLflow experiment
# Go to Azure ML Studio → Experiments → circuit-training
```

## Success Criteria

### ✅ Environment Setup
- [ ] Azure CLI installed and logged in
- [ ] Azure ML extension installed
- [ ] Workspace accessible
- [ ] Python 3.9+ with required packages

### ✅ Infrastructure Registration
- [ ] Environment registered: `sensor-forecasting-env:1.0.0`
- [ ] Training component registered: `train_lstm_model:1.0.0`
- [ ] Scoring component registered: `batch_score:1.0.0`

### ✅ Data Assets
- [ ] MLTable registered per circuit
- [ ] Naming: `PLANT_CIRCUIT`
- [ ] Version: `cutoff_date`

### ✅ Training
- [ ] Pipeline job submitted successfully
- [ ] Training completes without errors
- [ ] Model auto-registered with correct name
- [ ] Metrics logged to MLflow

### ✅ Model Registry
- [ ] Model registered with name from circuit config
- [ ] Tags applied: cutoff_date, plant_id, circuit_id
- [ ] Version auto-incremented

### ✅ End-to-End
- [ ] Build pipeline executes all stages
- [ ] Multiple circuits trained in parallel
- [ ] Models validated and tagged
- [ ] No errors in pipeline logs

## Next Steps After Testing

1. **Review Results:**
   - Check training metrics
   - Validate model quality
   - Review pipeline execution times

2. **Optimize:**
   - Adjust parallel concurrency
   - Tune hyperparameters
   - Optimize compute resources

3. **Deploy:**
   - Run release pipeline
   - Deploy to test environment
   - Validate batch endpoints

4. **Monitor:**
   - Set up data drift monitoring
   - Configure alerts
   - Track model performance

## Additional Resources

- **Implementation Progress:** `IMPLEMENTATION_PROGRESS.md`
- **Component Flow Diagram:** `docs/COMPONENT_FLOW_DIAGRAM.md`
- **Version Strategy:** `docs/CUTOFF_DATE_VERSION_VS_TAG.md`
- **Azure DevOps Pipelines:** `.azuredevops/`
- **Azure ML Pipelines:** `pipelines/`
