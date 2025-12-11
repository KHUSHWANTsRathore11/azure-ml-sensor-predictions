# Approval Gates in Azure MLOps Pipeline

## Overview

This document explains how approval gates work in our Azure DevOps MLOps pipeline and how to configure them for governance and control over model deployments.

---

## What Are Approval Gates?

Approval gates are **manual checkpoints** in the CI/CD pipeline where execution **pauses** and waits for human approval before proceeding to the next stage. This ensures that critical operations (like promoting models to production) are reviewed and approved by designated personnel.

---

## How Approval Gates Work

### Mechanism: Azure DevOps Environments

Approval gates are implemented using **Azure DevOps Environments** with **Approvals and Checks** configured.

```yaml
- stage: PromoteToRegistry
  jobs:
    - deployment: ApprovalGate
      environment: 'registry-promotion'  # ← Environment with approval configured
      strategy:
        runOnce:
          deploy:
            steps:
              - script: echo "Approval received, promoting models..."
```

When the pipeline reaches this stage:
1. **Pipeline pauses** at the deployment job
2. **Notifications sent** to configured approvers (email + Azure DevOps portal)
3. **Approvers review** logs, metrics, and training results
4. **Approve or Reject** the stage
5. **Pipeline continues** (if approved) or **fails** (if rejected)

---

## Pipeline Execution Flow with Approvals

```
┌─────────────────────────────────────────┐
│ Stage 1: RegisterInfrastructure         │
│ Status: ✅ Completed                     │
│ Duration: 5 minutes                     │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Stage 2: TrainModels                    │
│ Status: ✅ Completed                     │
│ Duration: 45 minutes                    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Stage 3: PromoteToRegistry              │
│ Status: ⏸️  WAITING FOR APPROVAL         │
│                                         │
│ 🔔 Notifications sent to:               │
│    - ML Engineering Lead                │
│    - Data Science Manager               │
│                                         │
│ ⏰ Timeout: 30 days                     │
│ 📋 Instructions: Review models          │
└─────────────────────────────────────────┘
              ↓ (After approval)
┌─────────────────────────────────────────┐
│ Stage 3: PromoteToRegistry              │
│ Status: ▶️  Running                      │
│ Action: Promoting models to Registry    │
│ Duration: 3 minutes                     │
└─────────────────────────────────────────┘
```

---

## Approval Gates in Our Pipeline

We have **4 approval gates** strategically placed for governance:

### Gate 1: Registry Promotion Approval
- **Location**: Stage 3 (PromoteToRegistry) on `develop` branch
- **Environment**: `registry-promotion`
- **Purpose**: Review trained models before promoting to shared Registry
- **Approvers**: ML Engineers, Data Science Lead
- **Review Criteria**:
  - Training metrics (accuracy, loss, etc.)
  - Number of circuits trained
  - Training job success rate
  - Model performance compared to baseline

### Gate 2: Test Deployment Approval
- **Location**: Stage 5 (DeployToTest) on `release/*` branch
- **Environment**: `test-deployment`
- **Purpose**: Approve deployment of Registry models to Test environment
- **Approvers**: ML Engineers, QA Lead
- **Review Criteria**:
  - Registry models available
  - Test environment readiness
  - Deployment configuration review

### Gate 3: QA Sign-Off Approval
- **Location**: Stage 7 (QASignOff) on `release/*` branch
- **Environment**: `qa-signoff`
- **Purpose**: QA team signs off on Test environment results
- **Approvers**: QA Team, Product Owner
- **Review Criteria**:
  - Integration test results
  - Batch scoring validation
  - Data quality checks
  - Performance benchmarks

### Gate 4: Production Deployment Approval
- **Location**: Stage 9 (DeployToProduction) on `main` branch
- **Environment**: `production-deployment`
- **Purpose**: Final approval before production deployment
- **Approvers**: Engineering Manager, Product Owner, Security Team
- **Review Criteria**:
  - Test environment validation complete
  - QA sign-off received
  - Security review passed
  - Production deployment plan reviewed

---

## Setting Up Approval Gates

### One-Time Setup in Azure DevOps

#### Step 1: Create Environment

1. Navigate to **Pipelines** → **Environments** in Azure DevOps
2. Click **New environment**
3. Enter environment name (e.g., `registry-promotion`)
4. Select **None** for resources (we don't need specific Kubernetes/VMs)
5. Click **Create**

#### Step 2: Configure Approvals

1. Open the created environment
2. Click **⋮** (More actions) → **Approvals and checks**
3. Click **+ Add check** → **Approvals**
4. Configure approval settings:

**Approval Configuration:**
```
Approvers: 
  - User: john.doe@company.com (ML Engineering Lead)
  - User: jane.smith@company.com (Data Science Manager)
  - Or use Azure AD groups: ML-Approvers

Minimum number of approvers required: 1

Timeout: 30 days
(Pipeline will wait this long before timing out)

Approval order: Any (first approval proceeds)
OR
Approval order: Sequential (all must approve in order)

Instructions for approvers:
"Review training metrics and model performance before approving 
promotion to Registry. Check logs from Stage 2 for details."
```

5. Click **Create**

#### Step 3: Optional Advanced Checks

You can add additional checks:

**Business Hours Restriction:**
- Only allow approvals during 9 AM - 5 PM EST
- Prevents deployments during off-hours

**Branch Control:**
- Only allow from `develop` or `release/*` branches
- Prevents accidental promotions from feature branches

**Required Template:**
- Enforce specific pipeline template usage
- Ensures consistency across deployments

**Invoke REST API:**
- Call external validation service before approval
- Example: Check model registry for conflicts

**Invoke Azure Function:**
- Custom approval logic
- Example: Auto-approve if metrics exceed threshold

---

## Approver Experience

### 1. Receiving Notification

**Email Notification:**
```
Subject: Approval required for Pipeline Run #12345

Pipeline: azure-ml-sensor-predictions CI/CD
Stage: PromoteToRegistry
Requested by: DevOps Service
Environment: registry-promotion

Action Required: Review and approve to continue

[View Pipeline Run] [Approve] [Reject]
```

**Azure DevOps Portal:**
- Notification icon shows pending approval
- Environment page shows "Waiting for approval"

### 2. Reviewing Information

Approvers should review:
- **Stage 1 & 2 logs**: Verify all tasks completed successfully
- **Training metrics**: Check model performance
- **Changed circuits**: Review which circuits were retrained
- **Artifact outputs**: Validate `changed_circuits.json`

### 3. Making Decision

**To Approve:**
1. Click **Review** → **Approve**
2. Optional: Add comment (e.g., "Metrics look good, proceeding")
3. Click **Approve** to continue pipeline

**To Reject:**
1. Click **Review** → **Reject**
2. Required: Add comment explaining rejection
3. Click **Reject** to fail the stage

**Approval Dialog:**
```
┌────────────────────────────────────────┐
│ Approve deployment to registry-promotion│
│                                        │
│ Comment:                               │
│ ┌────────────────────────────────────┐ │
│ │ Reviewed training metrics for all  │ │
│ │ 5 circuits. Performance meets      │ │
│ │ thresholds. Approving promotion.   │ │
│ └────────────────────────────────────┘ │
│                                        │
│ [Approve]  [Reject]  [Cancel]         │
└────────────────────────────────────────┘
```

### 4. After Approval/Rejection

**If Approved:**
- Stage 3 resumes execution
- Models promoted to Registry
- Pipeline continues to completion
- Audit log records approval (who, when, comment)

**If Rejected:**
- Stage 3 is skipped
- Pipeline run fails
- Models remain in Dev workspace only
- Team receives notification of rejection
- Audit log records rejection (who, when, reason)

---

## Approval Matrix

| Gate | Stage | Branch | Approvers | Criteria | SLA |
|------|-------|--------|-----------|----------|-----|
| **1. Registry Promotion** | PromoteToRegistry | `develop` | ML Engineers, DS Lead | Training metrics, job success | 24 hours |
| **2. Test Deployment** | DeployToTest | `release/*` | ML Engineers, QA Lead | Registry verification, config | 4 hours |
| **3. QA Sign-Off** | QASignOff | `release/*` | QA Team, Product Owner | Integration tests, validation | 24 hours |
| **4. Prod Deployment** | DeployToProduction | `main` | Engineering Manager, PO, Security | All checks passed | 48 hours |

---

## Key Features

### 1. Pipeline Pauses (Non-Blocking)
- Pipeline execution **stops** at approval gate
- Does **not block** other pipelines from running
- Can wait for **days or weeks** for approval
- Configurable timeout (default: 30 days)

### 2. Audit Trail
- All approvals logged with:
  - Approver name
  - Timestamp
  - Comments/reason
  - Pipeline run ID
  - Environment name
- Compliance and audit requirements met
- Searchable history in Azure DevOps

### 3. Multiple Approvers
- Require **1 or more** approvers
- **Any order**: First approval proceeds
- **Sequential**: All must approve in order
- **Unanimous**: All must approve (any reject fails)

### 4. Flexible Conditions
- Time-based (business hours only)
- Branch-based (only from specific branches)
- API-based (custom validation logic)
- User-based (specific roles/groups)

---

## Best Practices

### 1. Clear Instructions
Provide detailed instructions in environment configuration:
```
"Review the following before approving:
1. Check Stage 2 logs for training job status
2. Verify all circuits trained successfully
3. Review training metrics in MLflow
4. Confirm no anomalies in logs
5. Check changed_circuits.json artifact"
```

### 2. Reasonable Timeouts
- **Development environments**: Shorter (1-7 days)
- **Production environments**: Longer (7-30 days)
- Balance urgency with thorough review

### 3. Appropriate Approvers
- Match approver expertise to gate purpose
- ML Engineers for model quality
- QA for testing validation
- Security for production deployments
- Management for business impact

### 4. Document Approval Criteria
Create checklists for each gate:
- What metrics to check
- What logs to review
- What thresholds to verify
- When to reject vs approve

### 5. Set SLAs
Define expected approval turnaround times:
- Critical production fixes: < 4 hours
- Regular deployments: < 24 hours
- Major releases: < 48 hours

---

## Handling Rejections

### What Happens on Rejection?

1. **Pipeline fails** at the approval stage
2. **No rollback needed** (changes not yet applied)
3. **Team notified** of rejection
4. **Developer investigates** based on rejection comments

### Common Rejection Reasons

**Gate 1 (Registry Promotion):**
- Training metrics below threshold
- Training job failures
- Model performance regression
- Missing validation checks

**Gate 2 (Test Deployment):**
- Incorrect configuration
- Environment not ready
- Registry models missing
- Resource capacity issues

**Gate 3 (QA Sign-Off):**
- Integration tests failed
- Data quality issues
- Performance benchmarks not met
- Known bugs discovered

**Gate 4 (Production Deployment):**
- Security vulnerabilities found
- Insufficient testing in Test environment
- Business not ready for change
- Regulatory compliance issues

### Recovery Process

After rejection:
1. **Review rejection comments** from approver
2. **Fix identified issues** in code/config
3. **Commit changes** to appropriate branch
4. **New pipeline run triggered** automatically
5. **Re-submit for approval** (new approval request)

---

## Troubleshooting

### Pipeline Stuck at Approval?
- Check approver notifications (email, Azure DevOps)
- Verify approvers are configured correctly
- Check if approvers are available
- Review timeout settings

### Approval Not Triggering?
- Verify environment name matches YAML exactly
- Check if environment has approvals configured
- Ensure deployment job type is used (not regular job)
- Review pipeline permissions

### Multiple Unnecessary Approvals?
- Check if approvals configured on multiple environments
- Review if multiple approval checks added
- Verify branch conditions are correct

### Approval Bypassed?
- Check if user has "Administrator" role on environment
- Review "Exempt from approval" settings
- Verify security permissions

---

## Security Considerations

### 1. Approver Permissions
- Use **Azure AD groups** for approvers (not individual users)
- Follow **least privilege** principle
- Regularly **review approver lists**
- **Rotate approvers** to prevent single points of failure

### 2. Environment Permissions
- Restrict **Creator** role (who can modify environment)
- Limit **Administrator** role (can bypass approvals)
- Use **Reader** role for visibility only
- Audit environment changes regularly

### 3. Audit Compliance
- All approvals logged automatically
- Export logs for compliance reporting
- Retain approval history (Azure DevOps default: indefinite)
- Monitor for suspicious approval patterns

---

## Related Documentation

- [Branching Strategy](./BRANCHING_STRATEGY.md) - Overall workflow and branch structure
- [Pipeline Implementation](./PIPELINE_IMPLEMENTATION.md) - Technical pipeline details
- [Azure DevOps Environments](https://docs.microsoft.com/en-us/azure/devops/pipelines/process/environments) - Official documentation

---

## Summary

Approval gates provide **governance and control** over critical ML deployment operations:

✅ **4 Strategic Gates**: Registry, Test Deploy, QA, Prod Deploy  
✅ **Manual Review**: Human approval required before proceeding  
✅ **Audit Trail**: All approvals logged for compliance  
✅ **Flexible**: Configurable approvers, timeouts, conditions  
✅ **Non-Blocking**: Pipeline pauses but doesn't block others  
✅ **Secure**: Role-based access control and permissions  

This ensures that model deployments are **reviewed, validated, and approved** by the right people at the right time.
