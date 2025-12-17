# Testing Guide

Testing strategies for pipelines and models.

## Dummy Pipelines

**Purpose:** Test workflow logic without Azure ML resources

**Available:**
- `dummy-training-pipeline.yml` - Full 8-stage simulation
- `dummy-promote-single-model-pipeline.yml` - Model promotion simulation

### Dummy Training Pipeline

**Parameters:**
```yaml
simulateNewEnvironment: true/false
simulateCircuitChanges: "PLANT001/CIRCUIT01,..."
simulateJobFailures: "PLANT001/CIRCUIT02"
skipPromotion: true/false
simulatePropagationDelay: 5  # seconds
```

**Features:**
- Simulates all 8 stages
- No Azure ML connection required
- Configurable scenarios
- Outputs simulated artifacts
- Tests approval flow

**Usage:**
```bash
# Test full workflow
az pipelines run --name "dummy-training-pipeline"

# Test specific scenario
az pipelines run --name "dummy-training-pipeline" \
  --parameters simulateJobFailures="PLANT001/CIRCUIT01"
```

### Dummy Model Promotion

**Purpose:** Test per-model approval workflow

**Features:**
- Simulates propagation delay
- Tests exponential backoff
- Requires approval (dummy-approval environment)

## PR Validation

**Trigger:** Pull request to develop/release/main

**Checks:**
1. **Python Linting** - flake8, black
2. **YAML Validation** - Pipeline syntax
3. **Environment Validation** - Version consistency
4. **Component Validation** - Version consistency
5. **Circuit Validation** - Config syntax

**Configuration:**
```yaml
# mlops-pipeline-settings
validationMinAccuracy: 0.70
validationMaxMae: 10.0
validationMaxRmse: 15.0
```

## Manual Testing

### Test Environment Registration

```bash
# Update environment version
# components/environments/sensor-forecasting-env.yaml: version "1.0.0" → "1.1.0"

# Run pipeline
az pipelines run --name "training-pipeline"

# Verify in Azure ML Studio
az ml environment show --name custom-training-env --version 1.1.0
```

### Test Component Registration

```bash
# Update component version
# components/training-pipeline-component.yaml: version "1.0.0" → "1.1.0"

# Run pipeline
az pipelines run --name "training-pipeline"

# Verify
az ml component show --name training-pipeline-component --version 1.1.0
```

### Test Training

```bash
# Manual circuit specification
az pipelines run --name "training-pipeline" \
  --parameters manualCircuits="PLANT001/CIRCUIT01"

# Monitor in Azure ML Studio
az ml job list --workspace-name mlops-dev-workspace
```

### Test Model Promotion

```bash
# Run full pipeline
az pipelines run --name "training-pipeline"

# Approve model promotion when prompted
# Verify in Registry
az ml model list --registry-name mlops-central-registry
```

## Testing Checklist

### Before Merge

- [ ] PR validation passes
- [ ] Dummy pipeline runs successfully
- [ ] Manual testing in Dev completed
- [ ] Documentation updated
- [ ] Code reviewed

### Before Release

- [ ] Full training pipeline tested in Dev
- [ ] Model promotion tested with approval
- [ ] Test deployment verified
- [ ] Rollback procedure tested
- [ ] Monitoring alerts verified

### Before Production

- [ ] Test environment validated
- [ ] Prod deployment tested in Test
- [ ] Auto-rollback tested
- [ ] Performance benchmarks met
- [ ] Security review completed
