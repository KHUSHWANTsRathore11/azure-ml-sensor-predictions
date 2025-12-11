# Release Pipeline - Component-Based Multi-Stage Deployment

[← Back to README](../README.md)

## Overview

The Release Pipeline implements a three-stage deployment workflow with manual approval gates for promoting validated models from Development workspace through Registry to Test and Production environments.

**Flow:** Dev Workspace (validated models) → Registry → Test → Production

## Architecture Alignment

This pipeline is designed for the **corrected component-based architecture** where:
- Models are **auto-registered** in Dev workspace by training component
- MLTable data assets use **per-circuit naming**: `PLANT_CIRCUIT:cutoff_date`
- Multiple circuits can be promoted/deployed in a single release
- Batch endpoints are created **per circuit**: `be-plant001-circuit01`

## Pipeline Stages

### Stage 1: Promote to Registry
- **Trigger:** Artifact (`changed_circuits.json`) from Build Pipeline
- **Approval:** Manual (ML Engineers via `Registry-Approval` environment)
- **Evidence:** Models tagged with `validated=true` in Dev Workspace
- **Action:** 
  - Query Dev workspace for validated models
  - Download models from Dev workspace
  - Upload to Azure ML Registry
  - Tag with: `cutoff_date`, `plant_id`, `circuit_id`, `release_id`, `promoted_at`

### Stage 2: Deploy to Test
- **Trigger:** Auto (after Stage 1 success)
- **Approval:** None (automated)
- **Action:** 
  - Create/update batch endpoints per circuit (naming: `be-{plant}-{circuit}`)
  - Deploy models from Registry to Test workspace
  - Run smoke tests (batch inference with test data)
- **Validation:** 
  - All deployments must succeed
  - Smoke tests must complete within 15 minutes
  - Job status must be "Completed"

### Stage 3: Deploy to Production
- **Trigger:** Stage 2 success
- **Approval:** Manual (ML Engineers via `Production-Approval` environment)
- **Evidence:** Test smoke tests passed
- **Action:** 
  - Create/update batch endpoints per circuit
  - Deploy models from Registry to Production workspace
  - Track previous deployment for rollback capability
  - Higher compute capacity (instance_count=2, concurrency=4)
- **Verification:**
  - Check endpoint provisioning status
  - Verify default deployment set correctly
  - Display deployment summary

## Approval Gates Configuration

### Stage 1: Registry Promotion Approval

Configure in Azure DevOps → Environments → `Registry-Approval`:

```yaml
approvals:
  - approval: manual
    approvers:
      - group: 'ML-Engineers'
    instructions: |
      Review validated models before promoting to shared registry.
      
      Release ID: $(Build.BuildNumber)
      Build ID: $(Build.BuildId)
      
      ✅ Pre-Approval Checklist:
      1. Review model metrics in Dev Workspace (tag: validated=true)
      2. Check training logs for any warnings
      3. Verify cutoff_date is correct
      4. Review changed_circuits.json artifact
      
      Models will be copied from Dev Workspace to Azure ML Registry.
    timeoutInMinutes: 1440  # 24 hours
```

**What to Review:**
```bash
# Check validated models in Dev workspace
az ml model list \
  --workspace-name mlw-dev \
  --resource-group rg-mlops-dev \
  --tag validated=true \
  --output table

# Check training metrics for specific model
az ml model show \
  --name plant001-circuit01 \
  --workspace-name mlw-dev \
## Smoke Test Validation (Stage 2)

### Validation Criteria

| Check | Requirement | Action on Failure |
|-------|-------------|-------------------|
| Job Status | Must be "Completed" | Fail release, no Production deployment |
| Execution Time | < 15 minutes | Timeout, fail release |
| Errors in Logs | Zero errors | Fail release, investigate |
| Output Files | Generated successfully | Fail release |
| Schema | Matches expected format | Warning only (manual review) |

### Smoke Test Process

```bash
# For each circuit in changed_circuits.json:
1. Get endpoint name: be-{plant}-{circuit}
2. Invoke batch endpoint with test data
   Input: azureml://datastores/workspaceblobstore/paths/test-data/{plant}/{circuit}/
3. Poll job status every 30 seconds
4. Timeout after 15 minutes
5. Check final status:
   - "Completed" → ✅ Test passed, proceed
   - "Failed" → ❌ Fail release, stop pipeline
   - Timeout → ⚠️ Fail release, investigate
```

### Test Data Requirements

Each circuit must have test data available:
```
workspaceblobstore/
└── test-data/
    ├── PLANT001/
    │   ├── CIRCUIT01/
    │   │   └── test_input.csv
    │   └── CIRCUIT02/
    │       └── test_input.csv
    └── PLANT002/
        └── CIRCUIT01/
            └── test_input.csv
```

**Test Data Schema:**
- Must match training data schema
- Small subset (e.g., last 7 days)
- Known expected output (for future validation)

## Deployment Tracking

### Model Metadata Tags (Registry)

When models are promoted to Registry in Stage 1:

```yaml
tags:
  cutoff_date: "2025-11-01"           # VERSION for MLTable, TAG for model
  plant_id: "PLANT001"
  circuit_id: "CIRCUIT01"
  promoted_from: "dev"
  promoted_at: "2025-12-10T14:30:00Z"
  release_id: "20251210.1"
  build_id: "12345"
```

### Deployment Metadata Tags (Production)

When deployments are created in Stage 3:

```yaml
tags:
  cutoff_date: "2025-11-01"
  release_id: "20251210.1"
  deployed_at: "2025-12-10T16:45:00Z"
  previous_deployment: "deployment-20251203.5"  # For rollback
```

### Querying by Tags

```bash
# Find all models for a specific cutoff_date
az ml model list \
  --registry-name mlr-shared \
  --tag cutoff_date=2025-11-01 \
  --output table

# Find all models in a release
az ml model list \
  --registry-name mlr-shared \
  --tag release_id=20251210.1 \
  --output table

# Find deployments for a circuit
az ml batch-endpoint show \
  --name be-plant001-circuit01 \
  --workspace-name mlw-prod \
  --resource-group rg-mlops-prod
```

## Batch Endpoint Naming Convention

### Endpoint Names
Format: `be-{plant_id}-{circuit_id}` (lowercase)

Examples:
- `be-plant001-circuit01`
- `be-plant001-circuit02`
- `be-plant002-circuit01`

### Deployment Names
Format: `deployment-{build_number}`

Examples:
- `deployment-20251210.1`
- `deployment-20251210.2`

### Rationale
- **Per-circuit endpoints**: Each circuit has dedicated endpoint for independent scaling
- **Build-based deployments**: Multiple deployments per endpoint, default rotates
- **Rollback ready**: Previous deployment tracked in tags

## Rollback Support

### Automatic Rollback Tracking

Each Production deployment records the previous default deployment:

```bash
# During deployment
PREVIOUS_DEPLOYMENT=$(az ml batch-endpoint show \
  --name $ENDPOINT_NAME \
  --workspace-name mlw-prod \
  --query defaults.deployment_name -o tsv)

# Tag new deployment with previous
az ml batch-deployment create \
  --name deployment-20251210.1 \
  --endpoint-name be-plant001-circuit01 \
  --set tags.previous_deployment=$PREVIOUS_DEPLOYMENT
```

### Rollback Procedure

```bash
# 1. Identify current deployment
CURRENT=$(az ml batch-endpoint show \
  --name be-plant001-circuit01 \
  --workspace-name mlw-prod \
  --query defaults.deployment_name -o tsv)

# 2. Get previous deployment from tags
PREVIOUS=$(az ml batch-deployment show \
  --name $CURRENT \
  --endpoint-name be-plant001-circuit01 \
  --workspace-name mlw-prod \
  --query tags.previous_deployment -o tsv)

# 3. Set previous as default
az ml batch-endpoint update \
  --name be-plant001-circuit01 \
  --workspace-name mlw-prod \
  --set defaults.deployment_name=$PREVIOUS

# 4. Verify
az ml batch-endpoint show \
  --name be-plant001-circuit01 \
  --workspace-name mlw-prod \
  --query defaults.deployment_name
```

### Rollback Time
- **Identification:** 2-5 minutes (check logs, verify issue)
- **Execution:** 1-2 minutes (update default deployment)
- **Total SLA:** 5-10 minutes (significantly faster than redeployment)

## Pipeline Variables Required

### Variable Groups

**mlops-dev-variables:**
```yaml
devWorkspaceName: mlw-dev
devResourceGroup: rg-mlops-dev
azureServiceConnection: azure-ml-connection
```

**mlops-test-variables:**
```yaml
testWorkspaceName: mlw-test
testResourceGroup: rg-mlops-test
```

**mlops-prod-variables:**
```yaml
prodWorkspaceName: mlw-prod
prodResourceGroup: rg-mlops-prod
```

**mlops-registry-variables:**
```yaml
registryName: mlr-shared
```

## Deployment Summary Output

After successful Production deployment:

```
================================================
✅ Production Deployment Complete!
================================================
Release ID: 20251210.1
Build ID: 12345
Deployed At: 2025-12-10T16:45:00Z

📋 Deployed Circuits:
   - PLANT001 / CIRCUIT01 → plant001-circuit01
   - PLANT001 / CIRCUIT02 → plant001-circuit02
   - PLANT002 / CIRCUIT01 → plant002-circuit01

🔗 Workspace: mlw-prod
================================================
```

## Related Documents

- [../IMPLEMENTATION_PROGRESS.md](../IMPLEMENTATION_PROGRESS.md) - Implementation status
- [COMPONENT_FLOW_DIAGRAM.md](COMPONENT_FLOW_DIAGRAM.md) - Architecture flow
- [CUTOFF_DATE_VERSION_VS_TAG.md](CUTOFF_DATE_VERSION_VS_TAG.md) - Versioning strategy
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Testing procedures

## Troubleshooting

### Issue: Model not found in Registry
```bash
# Check if model was promoted in Stage 1
az ml model list \
  --registry-name mlr-shared \
  --tag release_id=<release-id> \
  --output table

# If missing, check Dev workspace for validated models
az ml model list \
  --workspace-name mlw-dev \
  --tag validated=true \
  --output table
```

### Issue: Smoke test timeout in Test
```bash
# Check job status
az ml job show --name <job-name> --workspace-name mlw-test

# Check compute availability
az ml compute show --name batch-cluster --workspace-name mlw-test

# Check test data exists
az storage blob list \
  --account-name <storage-account> \
  --container-name workspaceblobstore \
  --prefix test-data/
```

### Issue: Deployment fails in Production
```bash
# Check endpoint provisioning
az ml batch-endpoint show \
  --name be-plant001-circuit01 \
  --workspace-name mlw-prod

# Check compute capacity
az ml compute show --name batch-cluster --workspace-name mlw-prod

# Check model exists in Registry
az ml model show \
  --registry-name mlr-shared \
  --name plant001-circuit01 \
  --version <version>
```

---

**Document Version:** 2.0 (Component-Based Architecture)  
**Last Updated:** December 10, 2025
