# Per-Model Approval System for Registry Promotion

## Overview

Models are promoted to the registry individually with **plant-specific approvals**. Each plant can have different approvers and approval timelines.

## How It Works

### 1. Create Approval File

Before or during the pipeline run, create `approval_status.json`:

```json
{
  "PLANT001:plant001-circuit01-model:5": "approved",
  "PLANT001:plant001-circuit02-model:3": "approved",
  "PLANT002:plant002-circuit05-model:2": "pending",
  "PLANT003:plant003-circuit10-model:4": "rejected"
}
```

**Format:** `"<PLANT_ID>:<MODEL_NAME>:<VERSION>": "<STATUS>"`

**Status values:**
- `approved` - Promote to registry
- `pending` - Skip promotion (wait for approval)
- `rejected` - Skip promotion (don't promote)

### 2. Pipeline Reads Approvals

The `promote_models_individually.py` script:
1. Reads `approval_status.json`
2. For each model:
   - If `approved` → Promote to registry ✅
   - If `pending` → Skip, log as pending ⏸️
   - If `rejected` → Skip, log as rejected ❌
   - If not in file → Auto-approve (configurable)

### 3. Results Published

Pipeline publishes `promotion_result.json`:

```json
{
  "promoted": [
    {
      "model_name": "plant001-circuit01-model",
      "version": "5",
      "plant_id": "PLANT001",
      "status": "promoted"
    }
  ],
  "pending_approval": [
    {
      "model_name": "plant002-circuit05-model",
      "version": "2",
      "plant_id": "PLANT002",
      "status": "pending_approval"
    }
  ],
  "failed": []
}
```

## Approval Workflows

### Option 1: Manual Approval File (Simple)

**Before pipeline:**
1. ML Engineer creates `approval_status.json`
2. Commits to repo or uploads as artifact
3. Pipeline runs and reads approvals

### Option 2: Pre-Pipeline Approval Job (Recommended)

Add approval job before promotion:

```yaml
- job: RequestApprovals
  steps:
    - script: |
        # Generate approval request file
        python scripts/generate_approval_request.py
    - task: PublishPipelineArtifact@1
      inputs:
        targetPath: 'approval_request.json'
        artifact: 'approval_request'
    
    # Send to approval system (ServiceNow, Jira, email)
    - script: |
        python scripts/send_approval_requests.py \
          --plant-approvers plant_approvers.yaml
```

### Option 3: External System Integration

**Integrate with:**
- ServiceNow change requests
- Jira approval workflows  
- Custom approval portal

## Plant-Specific Approvers

Configure approvers per plant in `config/plant_approvers.yaml`:

```yaml
approvers:
  PLANT001:
    - name: "John Doe"
      email: "john.doe@company.com"
      role: "Plant Engineer"
  
  PLANT002:
    - name: "Jane Smith"
      email: "jane.smith@company.com"
      role: "Operations Manager"
  
  PLANT003:
    - name: "Bob Johnson"
      email: "bob.johnson@company.com"
      role: "Site Lead"
    - name: "Alice Williams"
      email: "alice.williams@company.com"
      role: "ML Engineer"
    approval_policy: "all"  # Require all approvers
```

## Timeline Examples

### Scenario 1: All Approved
```
Pipeline Run 1:
├─ 3 models registered
├─ Approval file: all approved
└─ Result: All 3 promoted ✅

Total time: ~10 minutes
```

### Scenario 2: Partial Approval
```
Pipeline Run 1:
├─ 3 models registered
├─ Approval file: 2 approved, 1 pending
└─ Result: 2 promoted, 1 skipped ⏸️

(Wait for PLANT002 approval)

Pipeline Run 2 (manual trigger):
├─ Same 3 models
├─ Approval file: all approved
└─ Result: 1 promoted (PLANT002), 2 skipped (already in registry) ✅

Total time: Hours/days (depends on approval)
```

### Scenario 3: Staged Rollout
```
Day 1:
├─ Approve PLANT001 only
└─ Promote PLANT001 model

Day 3:
├─ Approve PLANT002
└─ Promote PLANT002 model

Day 7:
├─ Approve PLANT003
└─ Promote PLANT003 model
```

## Benefits

✅ **Plant-specific control** - Each plant has own approval  
✅ **Different timelines** - Approve models independently  
✅ **Flexible approvers** - Different people per plant  
✅ **Audit trail** - Approval file tracked in git  
✅ **Partial deployment** - Promote some models, wait on others

## Auto-Approval (Optional)

Set auto-approve for certain plants:

```json
{
  "auto_approve_plants": ["TEST_PLANT", "DEV_PLANT"],
  "PLANT001:model:v1": "approved",
  "TEST_PLANT:model:v2": "auto"
}
```

Models from `TEST_PLANT` auto-approve if not in file.

## Future Enhancements

- **API integration:** Call external approval API
- **Azure DevOps Environments:** Create per-plant environments
- **Notifications:** Slack/email when approval needed
- **Auto-approve based on metrics:** If accuracy > 0.9, auto-approve
