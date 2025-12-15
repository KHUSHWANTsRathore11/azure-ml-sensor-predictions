# Per-Model Approval Setup Guide

## Overview

Each model gets its own pipeline run with individual approval using the child pipeline pattern.

## Setup Steps

### 1. Create the Child Pipeline in Azure DevOps

1. **Go to:** Azure DevOps → Pipelines → New Pipeline
2. **Select:** Azure Repos Git
3. **Choose:** Your repository
4. **Select:** Existing Azure Pipelines YAML file
5. **Path:** `.azuredevops/promote-single-model-pipeline.yml`
6. **Save** (don't run yet)
7. **Note the Pipeline ID:**
   - Go to pipeline settings → Edit
   - Look at URL: `https://dev.azure.com/{org}/{project}/_build?definitionId=**123**`
   - The number after `definitionId=` is your Pipeline ID

### 2. Update Parent Pipeline with Pipeline ID

Edit `.azuredevops/training-pipeline.yml`:

```yaml
# Line ~384: Replace with actual pipeline ID
PIPELINE_ID="<REPLACE_WITH_PIPELINE_ID>"
```

Change to:
```yaml
PIPELINE_ID="123"  # Your actual pipeline ID from step 1
```

### 3. Create Environment for Approvals

**Single environment (current):**
1. Azure DevOps → Pipelines → Environments
2. Click **New environment**
3. Name: `registry-promotion`
4. Click **Create**
5. Add approvers:
   - Click ⋯ → **Approvals and checks**
   - Click **Approvals**
   - Add: `ml-team@company.com`
   - Save

**Future: Plant-specific environments:**

When ready to use plant-specific approvals, update child pipeline:

```yaml
# Change line 47 in promote-single-model-pipeline.yml from:
environment: 'registry-promotion'

# To:
environment: 'registry-promotion-${{ parameters.plantId }}'
```

Then create environments:
- `registry-promotion-PLANT001` → Approver: plant001-engineer@
- `registry-promotion-PLANT002` → Approver: plant002-manager@
- etc.

### 4. Grant Pipeline Permissions

The parent pipeline needs permission to trigger child pipelines:

1. **Azure DevOps** → Project Settings → Pipelines → Settings
2. Enable: **"Disable creation of classic build pipelines"** = OFF
3. **OR** manually grant permissions:
   - Go to child pipeline → Edit → ⋯ → Security
   - Add parent pipeline's build service account
   - Grant: "Queue builds"

### 5. Enable System.AccessToken

Parent pipeline needs access token to trigger children:

```yaml
# Already configured in training-pipeline.yml:
env:
  SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

Ensure your pipeline has permission:
- Project Settings → Pipelines → Settings
- Enable: **"Limit job authorization scope"** = OFF (or grant specific access)

## How It Works

### Parent Pipeline (Training)

```
Stage 7: PromoteToRegistry
├─ Downloads registered_models.json
├─ For each model:
│  └─ Triggers child pipeline with model parameters
└─ Outputs triggered_promotions.json
```

### Child Pipeline (Per Model)

```
Pipeline: promote-single-model-pipeline
├─ Parameters: modelName, modelVersion, plantId, etc.
├─ Stage: ApprovePromotion
│  ├─ Deployment job (PAUSES for approval)
│  ├─ Environment: registry-promotion
│  ├─ Shows model details
│  └─ After approval: Promotes to registry
└─ Verifies promotion
```

### Approval Flow

```
Training Pipeline Completes
   ↓
3 models registered
   ↓
Stage 7 triggers 3 child pipelines
   ↓
Child Pipeline #1 (PLANT001-model:v5)
├─ Status: Waiting for approval ⏸️
└─ Approver sees: PLANT001/CIRCUIT01 details

Child Pipeline #2 (PLANT002-model:v3)
├─ Status: Waiting for approval ⏸️
└─ Approver sees: PLANT002/CIRCUIT05 details

Child Pipeline #3 (PLANT003-model:v2)
├─ Status: Waiting for approval ⏸️
└─ Approver sees: PLANT003/CIRCUIT10 details
```

**Approve independently:**
- Day 1: Approve PLANT001 → Promoted ✅
- Day 3: Approve PLANT002 → Promoted ✅
- Day 7: Approve PLANT003 → Promoted ✅

## Benefits

✅ **True per-model approvals** - Each model = separate pipeline run  
✅ **Independent timelines** - Approve whenever ready  
✅ **Native Azure DevOps** - No external systems needed  
✅ **Full audit trail** - Each promotion tracked separately  
✅ **Scalable** - Works for 3 models or 300 models  
✅ **Future-ready** - Easy to add plant-specific environments

## Verification

After setup, test with a single model:

```bash
# Manually trigger child pipeline
az pipelines run \
  --name "promote-single-model-pipeline" \
  --parameters modelName=test-model \
               modelVersion=1 \
               plantId=TEST \
               circuitId=CIRCUIT01 \
               trainingHash=abc123 \
               cutoffDate=2024-01-01
```

Check:
1. Pipeline runs
2. Pauses at environment approval
3. Shows model details
4. After approval, promotes to registry
5. Verifies model in registry

## Troubleshooting

**Child pipelines not triggering:**
- Check PIPELINE_ID is correct
- Verify System.AccessToken is enabled
- Check pipeline permissions

**Approval not appearing:**
- Verify environment exists
- Check approvers are configured
- Ensure environment name matches pipeline

**Promotion fails:**
- Check Azure subscription connection
- Verify registry exists
- Check model exists in Dev workspace
