# Approval Workflows

All approval gates and workflows for environment and model promotion.

## Approval Environments

Configure in **Azure DevOps → Pipelines → Environments**:

| Environment | Pipeline | Purpose | Approvers |
|-------------|----------|---------|-----------|
| `registry-promotion` | Environment & Model promotion | Approve sharing to Registry | ML team leads |
| `test-deployment` | Test deployment | Approve Test deployment | QA team |
| `prod-deployment` | Prod deployment | Approve Prod deployment | Senior engineers + platform lead |

## Environment Promotion

**Trigger:** New environment registered (Stage 1)

**Flow:**
1. Stage 1 registers new environment version
2. Stage 2 waits for `registry-promotion` approval
3. After approval, shares environment to Registry
4. Test/Prod can use new environment

**Approval UI:**
```
Environment: custom-training-env
Version: 1.1.0

This environment will be promoted to the shared Azure ML Registry
for use in Test and Production deployments.

[Approve] [Reject]
```

## Model Promotion

**Trigger:** Model registered (Stage 7)

**Flow:**
1. Stage 7 registers models in Dev workspace
2. Stage 8 triggers child pipeline per model
3. Each child pipeline waits for `registry-promotion` approval
4. After approval, shares model to Registry with exponential backoff
5. Test/Prod can deploy from Registry

**Per-Model Approval:**
- Each model requires individual approval
- Parallel approvals possible
- Different approvers can handle different models

**Approval UI:**
```
Model: plant001-circuit01
Version: 5
Training Hash: a1b2c3d4e5f6

Metrics:
- Accuracy: 0.92
- MAE: 3.2
- RMSE: 4.5

[Approve] [Reject]
```

## Setup Instructions

### 1. Create Environments

```bash
# Azure DevOps → Pipelines → Environments → New environment
```

Create 3 environments:
- `registry-promotion`
- `test-deployment`
- `prod-deployment`

### 2. Add Approvers

For each environment:
1. Click environment → Approvals and checks
2. Add "Approvals"
3. Select approvers (users or groups)
4. Set timeout (e.g., 30 days)
5. Add instructions for approvers

### 3. Configure Approval Settings

**Recommended:**
- Minimum approvers: 1 (registry-promotion, test-deployment)
- Minimum approvers: 2 (prod-deployment)
- Timeout: 30 days
- Allow approver to approve their own runs: No (prod only)

## Best Practices

1. **Review metrics** before approving model promotion
2. **Check environment changes** before approving environment promotion
3. **Use approval instructions** to guide approvers
4. **Set reasonable timeouts** (30 days recommended)
5. **Require 2 approvers for prod** (separation of duties)
6. **Document approval decisions** in comments
7. **Reject if uncertain** - better safe than sorry
