# Rollback Procedures

[← Back to README](../README.md)

## Overview

This document outlines comprehensive rollback procedures for both model deployments and environment updates in the Azure ML sensor predictions architecture.

## Model Rollback (Per Circuit)

### Rollback Methods

#### Method 1: Azure DevOps Release Redeploy (Recommended)

**Process:**
1. Navigate to Azure DevOps → Releases
2. Find last successful release for plant/circuit
3. Click "Redeploy" button
4. Fast-track approval gates (emergency)
5. Verify rollback success

**Time:** 15-20 minutes

#### Method 2: Manual Script

```bash
# scripts/rollback_model.sh
#!/bin/bash

PLANT_ID="$1"
CIRCUIT_ID="$2"
PREVIOUS_VERSION="$3"  # From deployment tags

ENDPOINT_NAME="batch-endpoint-plant-$PLANT_ID"
DEPLOYMENT_NAME="deployment-circuit-$CIRCUIT_ID"

echo "Rolling back $PLANT_ID/$CIRCUIT_ID to model version $PREVIOUS_VERSION"

# Get previous model from registry
REGISTRY_MODEL="azureml://registries/mlregistry-shared/models/sensor_model_${PLANT_ID}_${CIRCUIT_ID}/versions/${PREVIOUS_VERSION}"

# Update deployment with previous model
az ml batch-deployment update \
  --name "$DEPLOYMENT_NAME" \
  --endpoint-name "$ENDPOINT_NAME" \
  --workspace-name "prod-ml-workspace" \
  --resource-group "mlops-rg" \
  --set model="$REGISTRY_MODEL"

echo "Rollback complete"
```

### Rollback Verification Steps

1. ✅ Check deployment status
2. ✅ Run test batch inference
3. ✅ Compare predictions with expected baseline
4. ✅ Check alert rules (should decrease)
5. ✅ Monitor for 1 hour
6. ✅ Document rollback reason

### Rollback SLA

| Phase | Time |
|-------|------|
| Identify issue | 5-10 minutes |
| Execute rollback | 5-10 minutes |
| Verification | 5 minutes |
| **Total** | **15-20 minutes** |

## Environment Rollback (All Circuits)

### When to Rollback Environment

**Trigger Conditions:**
- Multiple batch job failures across circuits
- Performance degradation >20% across multiple circuits
- Scoring errors in production
- Alert spike (>10 alerts/hour)

### Rollback Process

#### Step 1: Identify Previous Environment

```bash
# Check deployment for previous environment version
az ml batch-deployment show \
  --name "deployment-circuit-C001" \
  --endpoint-name "batch-endpoint-plant-P001" \
  --workspace-name "prod-ml-workspace" \
  --query 'tags.previous_environment' -o tsv
```

#### Step 2: Execute Rollback Pipeline

```bash
# Trigger rollback pipeline with release ID
az pipelines run \
  --name "Environment-Rollback" \
  --parameters releaseId=Release-123
```

#### Step 3: Verify Rollback

**Verification Checklist:**
1. ✅ All 75-200 deployments updated
2. ✅ Environment versions match expected
3. ✅ Run sample batch inference
4. ✅ Check error logs
5. ✅ Monitor alerts for 2-4 hours
6. ✅ Document root cause

### Rollback Metadata

**Stored in artifact during environment update:**

```json
{
  "release_id": "Release-123",
  "environment_version": "1.5.1",
  "previous_environment_version": "1.5.0",
  "updated_at": "2025-12-09T14:30:00Z",
  "deployments": [
    {
      "plant_id": "P001",
      "circuit_id": "C001",
      "previous_environment": "azureml:custom-tf-env:1.5.0"
    }
  ]
}
```

## Rollback Decision Matrix

| Scenario | Model Rollback | Environment Rollback | Both |
|----------|---------------|---------------------|------|
| Single circuit performance degraded | ✓ | | |
| Multiple circuits same issue | | ✓ | |
| New model + new environment both failing | | | ✓ |
| Scoring errors across all circuits | | ✓ | |
| Single model prediction errors | ✓ | | |

## Emergency Rollback Contacts

| Role | Responsibility | Contact |
|------|---------------|---------|
| **On-Call ML Engineer** | Execute rollback | TBD |
| **ML Engineering Manager** | Approve emergency rollback | TBD |
| **DevOps Engineer** | Pipeline support | TBD |

## Post-Rollback Actions

### Immediate (0-1 hour)
1. Verify system stability
2. Check alert rates
3. Monitor batch job success rates
4. Document initial findings

### Short-term (1-24 hours)
1. Root cause analysis
2. Document lessons learned
3. Update runbooks if needed
4. Plan fix and redeployment

### Long-term (1-7 days)
1. Implement permanent fix
2. Test thoroughly in dev/test
3. Create new release
4. Post-mortem meeting

## Related Documents

- [06-release-pipeline.md](06-release-pipeline.md) - Release process
- [07-environment-only-pipeline.md](07-environment-only-pipeline.md) - Environment updates
- [12-operational-runbooks.md](12-operational-runbooks.md) - Operational procedures

---

**Document Version:** 1.0  
**Last Updated:** December 9, 2025
