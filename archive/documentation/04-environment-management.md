# Environment Management Strategy

[← Back to README](../README.md)

## Overview

This document outlines the comprehensive environment management strategy for the Azure ML sensor predictions architecture, covering versioning, change classification, promotion paths, and deployment workflows.

## Table of Contents

1. [Environment Versioning Strategy](#environment-versioning-strategy)
2. [Breaking vs Non-Breaking Changes](#breaking-vs-non-breaking-changes)
3. [Environment Tags and Metadata](#environment-tags-and-metadata)
4. [Change Classification Scenarios](#change-classification-scenarios)
5. [Environment Promotion Path](#environment-promotion-path)
6. [Fixed Environment Versions in Production](#fixed-environment-versions-in-production)
7. [Environment-Only Release Pipeline](#environment-only-release-pipeline)
8. [Environment Rollback Strategy](#environment-rollback-strategy)
9. [Approval Evidence Requirements](#approval-evidence-requirements)
10. [Best Practices](#best-practices)

---

## Environment Versioning Strategy

### Azure ML Environment Versioning Rules

Azure ML has different versioning rules per asset type:

| Asset Type | Versioning Rule | Example Allowed | Example Failed |
|------------|----------------|-----------------|----------------|
| **Model** | Integer ONLY | `1`, `2`, `15` | `1.0.0`, `v1` |
| **Environment** | String | `1.0.0`, `ubuntu-20.04` | N/A (all strings accepted) |
| **Data** | String | `initial_load`, `2025-01-01` | N/A (all strings accepted) |
| **Component** | String | `1.0.0`, `beta` | N/A (all strings accepted) |

### Semantic Versioning for Environments

**Strategy:** Use semantic versioning (MAJOR.MINOR.PATCH) for custom environments

```
Format: MAJOR.MINOR.PATCH

Examples:
- 1.5.0 (current stable)
- 1.5.1 (patch/bug fix)
- 1.6.0 (new non-breaking feature)
- 2.0.0 (breaking change)
```

**Version Bump Guidelines:**

| Version Component | When to Bump | Impact |
|------------------|--------------|--------|
| **MAJOR** (e.g., 1.5.0 → 2.0.0) | Breaking changes: TensorFlow upgrade, feature engineering change, preprocessing change | Requires model retraining |
| **MINOR** (e.g., 1.5.0 → 1.6.0) | Non-breaking features: New utility functions, optional parameters | No retraining needed |
| **PATCH** (e.g., 1.5.0 → 1.5.1) | Bug fixes: Logging improvements, performance optimizations | No retraining needed |

### Environment Registration

```python
# Environment registration with semantic versioning
from azure.ai.ml.entities import Environment

env = Environment(
    name="custom-tf-env",
    version="1.5.0",  # String version - semantic versioning
    image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04",
    conda_file="environment/conda.yml",
    tags={
        "backward_compatible": "true",    # or "false" for breaking changes
        "requires_retrain": "false",      # or "true" if models need retraining
        "tensorflow_version": "2.13.0",
        "registered_at": "2025-12-09T10:30:00Z",
        "git_commit_sha": "a1b2c3d4",
        "breaking_changes": "",           # Description if breaking
        "change_summary": "Bug fix in scoring script logging"
    },
    description="Custom TensorFlow environment for sensor predictions"
)
```

---

## Breaking vs Non-Breaking Changes

### Classification Matrix

| Change Type | Examples | Requires Retraining? | Workflow |
|-------------|----------|---------------------|----------|
| **Breaking** | TensorFlow upgrade, feature engineering change, preprocessing change, schema changes | Yes | Update configs → PR → Full training → Normal Release Pipeline |
| **Non-Breaking** | Bug fix in scoring, logging improvement, performance optimization, security patches | No | Environment-Only Release Pipeline → Test all models → Update all deployments |

### Scenario 1: Breaking Changes (Requires Model Retraining)

**Examples:**
- TensorFlow version upgrade (2.13.0 → 2.14.0)
- Feature engineering logic change
- Preprocessing change (normalization method)
- Model input/output schema changes

**Version Update:**
```yaml
# Environment version: 1.5.0 → 2.0.0 (MAJOR bump)
# Tags: backward_compatible: false, requires_retrain: true
```

**Workflow:**
1. Update source code + environment definition (bump MAJOR version: 2.0.0)
2. Update all circuit configs (set `environment_version: "2.0.0"`)
3. Create PR (triggers training for all affected circuits)
4. Models trained with new environment
5. Follow normal Release Pipeline (model + environment promoted together)
6. Production updated gradually (one-by-one approvals per circuit)

**Example Config Update:**
```yaml
# config/plants/P001/C001.yml (and all other circuits)
plant_id: "P001"
circuit_id: "C001"
training:
  cutoff_date: "2025-12-09"
  environment_version: "2.0.0"  # Updated from 1.5.0
  hyperparameters:
    sequence_length: 24
    lstm_units: 128
```

### Scenario 2: Non-Breaking Changes (No Model Retraining)

**Examples:**
- Bug fix in scoring script (logging, error handling)
- Performance optimization (code refactoring)
- Security patch (dependency update without API changes)
- Documentation improvements in code

**Version Update:**
```yaml
# Environment version: 1.5.0 → 1.5.1 (PATCH bump)
# or 1.5.0 → 1.6.0 (MINOR bump for features)
# Tags: backward_compatible: true, requires_retrain: false
```

**Workflow:**
1. Update source code + environment definition
2. Build new environment version
3. Use separate Environment-Only Release Pipeline
4. Test against ALL 75-200 existing models
5. Update all deployments at once (if tests pass)
6. Rollback all if issues occur

---

## Environment Tags and Metadata

### Required Tags

```python
tags = {
    # Classification tags (REQUIRED)
    "backward_compatible": "true",      # true/false
    "requires_retrain": "false",        # true/false
    
    # Version information
    "tensorflow_version": "2.13.0",
    "python_version": "3.9",
    "source_code_version": "1.5.0",     # Matches environment version
    
    # Change tracking
    "change_summary": "Bug fix in scoring script logging",
    "breaking_changes": "",             # Description if applicable
    "git_commit_sha": "a1b2c3d4e5f6",
    
    # Metadata
    "registered_at": "2025-12-09T10:30:00Z",
    "registered_by": "john.doe@company.com",
    "pr_number": "PR-1234",
    
    # Dependencies
    "cuda_version": "",                 # If GPU
    "openmpi_version": "4.1.0"
}
```

### Tag Usage

**Query environments by compatibility:**
```python
# Find all backward-compatible environments
environments = ml_client.environments.list(name="custom-tf-env")
compatible_envs = [
    env for env in environments 
    if env.tags.get("backward_compatible") == "true"
]
```

**Check if retraining is required:**
```python
env = ml_client.environments.get(name="custom-tf-env", version="2.0.0")
if env.tags.get("requires_retrain") == "true":
    print("⚠️ Models need retraining with this environment")
```

---

## Change Classification Scenarios

### Example 1: Logging Improvement (Non-Breaking)

**Change:**
```python
# Before (v1.5.0)
print(f"Prediction: {result}")

# After (v1.5.1)
import logging
logger.info(f"Prediction for sensor {sensor_id}: {result}, confidence: {confidence}")
```

**Classification:**
- **Backward Compatible:** Yes (no interface changes)
- **Requires Retrain:** No (scoring logic unchanged)
- **Version:** 1.5.0 → 1.5.1 (PATCH)
- **Workflow:** Environment-Only Release Pipeline

### Example 2: TensorFlow Upgrade (Breaking)

**Change:**
```yaml
# Before (v1.5.0)
tensorflow==2.13.0

# After (v2.0.0)
tensorflow==2.14.0  # New TF version may have API changes
```

**Classification:**
- **Backward Compatible:** No (TF API changes may affect models)
- **Requires Retrain:** Yes (models need recompilation)
- **Version:** 1.5.0 → 2.0.0 (MAJOR)
- **Workflow:** Full retrain + Normal Release Pipeline

### Example 3: New Utility Function (Non-Breaking)

**Change:**
```python
# Added to scoring script (v1.6.0)
def calculate_confidence_interval(predictions):
    """New optional utility for confidence bounds"""
    return np.percentile(predictions, [2.5, 97.5])

# Existing score() function unchanged
def score(data):
    # Original logic intact
    predictions = model.predict(data)
    return predictions
```

**Classification:**
- **Backward Compatible:** Yes (new optional function)
- **Requires Retrain:** No (scoring logic unchanged)
- **Version:** 1.5.0 → 1.6.0 (MINOR)
- **Workflow:** Environment-Only Release Pipeline

### Example 4: Feature Preprocessing Change (Breaking)

**Change:**
```python
# Before (v1.5.0)
X_scaled = (X - X.mean()) / X.std()

# After (v2.0.0)
X_scaled = (X - X.min()) / (X.max() - X.min())  # Changed to min-max scaling
```

**Classification:**
- **Backward Compatible:** No (feature values will differ)
- **Requires Retrain:** Yes (models trained on different data distribution)
- **Version:** 1.5.0 → 2.0.0 (MAJOR)
- **Workflow:** Full retrain + Normal Release Pipeline

---

## Environment Promotion Path

### Promotion Flow

```
Dev Workspace (Build) 
  ↓
  [Manual Approval + Evidence]
  ↓
Azure ML Registry (Shared)
  ↓
  [Auto-deploy for Integration Tests]
  ↓
Test Workspace
  ↓
  [Test ALL 75-200 Models]
  ↓
  [Manual Approval]
  ↓
Production Workspace
```

### Stage Details

| Stage | Environment | Approval Required | Evidence Required | Purpose |
|-------|-------------|------------------|-------------------|---------|
| **Build** | Dev Workspace | No | N/A | Environment creation and registration |
| **Registry Promotion** | Azure ML Registry | Yes (ML Engineers) | Interactive notebook showing scoring execution | Shared environment registry |
| **Test Deployment** | Test Workspace | No (auto-trigger) | N/A | Integration testing environment |
| **Integration Tests** | Test Workspace | No (automated) | All 75-200 models must pass | Compatibility validation |
| **Production Deployment** | Production Workspace | Yes (ML Engineers) | Test results | Production environment |

### Promotion Script

```bash
# scripts/promote_environment_to_registry.sh
#!/bin/bash

ENV_NAME="$1"
ENV_VERSION="$2"
DEV_WORKSPACE="$3"
REGISTRY_NAME="$4"

echo "Promoting environment $ENV_NAME:$ENV_VERSION to registry..."

# Copy environment from Dev to Registry
az ml environment share \
  --name "$ENV_NAME" \
  --version "$ENV_VERSION" \
  --workspace-name "$DEV_WORKSPACE" \
  --resource-group "mlops-rg" \
  --registry-name "$REGISTRY_NAME" \
  --share-with-name "$ENV_NAME" \
  --share-with-version "$ENV_VERSION"

echo "✅ Environment promoted to registry"
```

---

## Fixed Environment Versions in Production

### Configuration Strategy

**Model configs include `environment_version`:**

```yaml
# config/plants/P001/C001.yml
plant_id: "P001"
circuit_id: "C001"
training:
  cutoff_date: "2025-12-09"
  environment_version: "1.5.0"  # Fixed environment version
  hyperparameters:
    sequence_length: 24
    lstm_units: 128
```

### Benefits

| Benefit | Description |
|---------|-------------|
| **Reproducibility** | Models always use same environment they were trained with |
| **Stability** | No unexpected changes from "latest" environment |
| **Rollback** | Can redeploy exact model + environment combination |
| **Auditability** | Clear lineage from training to production |
| **Testing** | Can test specific environment versions |

### Trade-offs

**Trade-off:** Must explicitly update configs for environment changes

**Mitigation:**
- Automation scripts to bulk-update configs
- PR-based workflow ensures review
- Environment-Only pipeline for non-breaking changes

---

## Environment-Only Release Pipeline

### Overview

**Purpose:** Update custom environment across all production deployments WITHOUT model retraining

**When to Use:**
- Bug fixes in scoring script (no model interface changes)
- Logging improvements
- Performance optimizations
- Security patches
- Non-breaking dependency updates

### Workflow Diagram

```
Environment Code Change
  ↓
Build New Environment
  ↓
Register in Dev
  ↓
[Manual Approval + Evidence]
  ↓
Promote to Registry
  ↓
Copy to Test Workspace
  ↓
Test ALL 75-200 Models (Integration)
  ↓
All Tests Pass?
  ├─ Yes → [Manual Approval] → Update ALL Deployments → Monitor 24h
  └─ No → Fail Release → Alert Team
```

### Pipeline Stages

#### Stage 1: Promote Environment to Registry

**Approval Gate:**
- **Approvers:** ML Engineers group
- **Evidence Required:** Interactive notebook showing scoring execution in Dev workspace
- **Timeout:** 24 hours

**Instructions:**
```
Review environment changes before promoting to shared registry.

Environment Version: $(environment_version)
Changes: $(change_summary)
Backward Compatible: $(backward_compatible)

Verify evidence of successful scoring in Dev workspace notebook.
```

#### Stage 2: Integration Test ALL Models

**Process:**
1. Copy environment from Registry to Test Workspace
2. Get list of all 75-200 production model deployments
3. Submit integration test job for each model
4. Wait for all tests to complete
5. Check if all tests passed

**Test Job:**
```yaml
# pipelines/environment_compatibility_test.yml
$schema: https://azuremlschemas.azureedge.net/latest/pipelineJob.schema.json
type: pipeline

inputs:
  model_name: 
    type: string
  model_version: 
    type: string
  environment_version:
    type: string

jobs:
  compatibility_test:
    type: command
    environment: azureml:custom-tf-env:${{inputs.environment_version}}
    command: >-
      python scripts/test_model_compatibility.py
      --model-name ${{inputs.model_name}}
      --model-version ${{inputs.model_version}}
    compute: azureml:test-compute-cluster
```

**Integration Test Script:**
```python
# scripts/test_model_compatibility.py
import argparse
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

def test_compatibility(model_name, model_version):
    """Test if model works with current environment"""
    ml_client = MLClient(DefaultAzureCredential(), ...)
    
    # Load model
    model = ml_client.models.get(name=model_name, version=model_version)
    
    # Load test data
    test_data = load_test_data()
    
    # Try scoring
    try:
        predictions = model.predict(test_data)
        assert predictions is not None
        assert len(predictions) > 0
        print("✅ Compatibility test passed")
        return True
    except Exception as e:
        print(f"❌ Compatibility test failed: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-version", required=True)
    args = parser.parse_args()
    
    test_compatibility(args.model_name, args.model_version)
```

#### Stage 3: Update ALL Production Deployments

**Approval Gate:**
- **Approvers:** ML Engineers + Engineering Managers
- **Evidence Required:** All integration test results
- **Timeout:** 24 hours

**Instructions:**
```
All integration tests passed. Ready to update ALL production deployments.

Environment Version: $(environment_version)
Models Tested: 75-200
Test Results: All Passed

This will update ALL deployments at once.
```

**Update Process:**
1. Copy environment from Registry to Production Workspace
2. Get all production deployments
3. Track current environment versions (for rollback)
4. Update each deployment with new environment
5. Publish rollback metadata as artifact

#### Stage 4: Monitor Production

**Post-Deployment:**
- Monitor for 24 hours
- Check alert rules for anomalies
- Review batch job success rates
- Use rollback pipeline if issues detected

---

## Environment Rollback Strategy

### Rollback Trigger Conditions

| Condition | Severity | Action |
|-----------|----------|--------|
| Multiple batch job failures | Critical | Immediate rollback |
| Performance degradation (>20%) | High | Investigate, consider rollback |
| Scoring errors in production | Critical | Immediate rollback |
| Alert spike (>10 alerts/hour) | High | Investigate, consider rollback |

### Rollback Pipeline

```yaml
# azure-pipelines-environment-rollback.yml
name: Environment-Rollback-$(Date:yyyyMMdd)$(Rev:.r)

trigger: none

parameters:
  - name: releaseId
    displayName: 'Release ID to Rollback From'
    type: string

stages:
  - stage: RollbackAll
    displayName: 'Rollback All Deployments to Previous Environment'
    
    approvals:
      - approval: manual
        approvers:
          - group: 'ML-Engineers'
        instructions: |
          Confirm rollback of ALL production deployments to previous environment.
          Release ID: ${{ parameters.releaseId }}
        timeoutInMinutes: 60
    
    jobs:
      - job: ExecuteRollback
        steps:
          - task: DownloadBuildArtifacts@0
            displayName: 'Download Rollback Metadata'
            inputs:
              buildType: 'specific'
              project: '$(System.TeamProject)'
              pipeline: 'Environment-Only-Release'
              buildVersionToDownload: 'specific'
              buildId: '${{ parameters.releaseId }}'
              artifactName: 'RollbackMetadata'
          
          - task: AzureCLI@2
            displayName: 'Rollback All Deployments'
            inputs:
              azureSubscription: 'AzureML-ServiceConnection'
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                ROLLBACK_DATA=$(cat $(System.ArtifactsDirectory)/RollbackMetadata/previous_env_versions.json)
                
                echo "$ROLLBACK_DATA" | jq -c '.[]' | while read item; do
                  PLANT_ID=$(echo $item | jq -r '.plant_id')
                  CIRCUIT_ID=$(echo $item | jq -r '.circuit_id')
                  PREV_ENV=$(echo $item | jq -r '.previous_environment')
                  
                  ENDPOINT_NAME="batch-endpoint-plant-$PLANT_ID"
                  DEPLOYMENT_NAME="deployment-circuit-$CIRCUIT_ID"
                  
                  echo "Rolling back $ENDPOINT_NAME/$DEPLOYMENT_NAME → $PREV_ENV"
                  
                  az ml batch-deployment update \
                    --name "$DEPLOYMENT_NAME" \
                    --endpoint-name "$ENDPOINT_NAME" \
                    --workspace-name "$(prodWorkspace)" \
                    --resource-group "$(resourceGroup)" \
                    --set environment="$PREV_ENV" \
                         tags.rolled_back_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
                         tags.rollback_reason="Environment issue in release ${{ parameters.releaseId }}"
                  
                  echo "✅ Rolled back $ENDPOINT_NAME/$DEPLOYMENT_NAME"
                done
                
                echo "✅ All deployments rolled back successfully"
```

### Rollback Verification

**Post-Rollback Checklist:**
1. ✅ Verify all deployments updated to previous environment
2. ✅ Run test batch inference for sample circuits
3. ✅ Check alert rules (should decrease)
4. ✅ Monitor for 1 hour post-rollback
5. ✅ Document root cause and prevention

---

## Approval Evidence Requirements

### Why Evidence is Required

**Problem:** Interactive notebook can execute code that would fail in production environment
**Solution:** Require evidence of successful scoring in Dev workspace before Registry promotion

### Evidence Format

**Required Notebook Content:**
1. Load environment version
2. Load test model
3. Load sample data
4. Execute scoring
5. Display predictions
6. Show no errors

**Example Notebook:**
```python
# Environment Evidence Notebook
# Version: 1.5.1

# 1. Load environment
import os
print(f"Environment: {os.environ.get('AZUREML_ARM_ENVIRONMENT')}")

# 2. Load test model
from azure.ai.ml import MLClient
ml_client = MLClient(...)
model = ml_client.models.get(name="sensor_model_P001_C001", version="5")

# 3. Load sample data
import pandas as pd
test_data = pd.read_csv("/mnt/data/test_sample.csv")

# 4. Execute scoring
predictions = model.predict(test_data)

# 5. Display predictions
print(f"Predictions: {predictions[:10]}")
print(f"Shape: {predictions.shape}")

# 6. Assert no errors
assert predictions is not None
assert len(predictions) > 0
print("✅ Scoring successful")
```

### Approval Decision Matrix

| Evidence Quality | Test Results | Decision |
|-----------------|--------------|----------|
| Complete notebook with successful scoring | All models pass | Approve |
| Complete notebook with successful scoring | Some models fail | Investigate, likely Reject |
| Incomplete notebook | N/A | Reject |
| No notebook provided | N/A | Reject |
| Notebook with errors | N/A | Reject |

---

## Best Practices

### Environment Development

1. **Use semantic versioning consistently**
   - MAJOR for breaking changes
   - MINOR for new features
   - PATCH for bug fixes

2. **Tag environments thoroughly**
   - Always include backward_compatible tag
   - Always include requires_retrain tag
   - Include git commit SHA
   - Document change summary

3. **Test environments in Dev workspace**
   - Run interactive notebook
   - Test with sample models
   - Verify all dependencies

4. **Document changes**
   - Update CHANGELOG.md
   - Include rationale for changes
   - List affected components

### Change Management

1. **Classify changes correctly**
   - Err on the side of "breaking" if uncertain
   - Consult with team for borderline cases
   - Document classification rationale

2. **Coordinate environment updates**
   - Batch multiple changes when possible
   - Avoid frequent environment-only releases
   - Schedule during low-usage windows

3. **Monitor post-deployment**
   - Check alerts for 24-48 hours
   - Review batch job success rates
   - Compare metrics to baseline

### Rollback Planning

1. **Always maintain rollback metadata**
   - Store previous environment versions
   - Track deployment mappings
   - Document rollback procedures

2. **Test rollback procedures**
   - Practice rollback in test environment
   - Time rollback execution
   - Verify rollback verification steps

3. **Automate rollback decisions**
   - Define clear rollback triggers
   - Implement automated alerts
   - Document escalation paths

---

## Related Documents

- [02-data-architecture.md](02-data-architecture.md) - Data strategy and MLTable usage
- [05-build-pipeline.md](05-build-pipeline.md) - Environment build process
- [07-environment-only-pipeline.md](07-environment-only-pipeline.md) - Detailed pipeline configuration
- [08-rollback-procedures.md](08-rollback-procedures.md) - Comprehensive rollback documentation
- [12-operational-runbooks.md](12-operational-runbooks.md) - Operational procedures

---

**Document Version:** 1.0  
**Last Updated:** December 9, 2025  
**Maintained By:** ML Engineering Team
