# Branching Strategy & CI/CD Flow

## Branch Structure

```
develop (Dev Workspace)
    ↓
  Registry (Shared Model Store)
    ↓
release/* (Test Endpoints)
    ↓
main (Production Endpoints)
```

## Branch-to-Environment Mapping

| Branch | Action | Workspace/Registry | Purpose |
|--------|--------|-------------------|---------|
| `develop` | **Train & Promote** | Dev Workspace → Registry | Train models, validate, promote to Registry |
| `release/*` | **Deploy Only** | Registry → Test Endpoints | Pull from Registry, deploy to Test, QA validation |
| `main` | **Deploy Only** | Registry → Prod Endpoints | Pull from Registry, deploy to Production |

## Key Principles

✅ **Train Once, Deploy Everywhere** - Models trained in Dev, deployed from Registry to Test/Prod  
✅ **Registry as Single Source of Truth** - All environments use same validated model artifacts  
✅ **No Retraining in Test/Prod** - Ensures consistency and faster deployments  
✅ **Immutable Artifacts** - Once in Registry, models are versioned and immutable  

## CI/CD Pipeline Flow

### 1. Build Pipeline - `develop` Branch (Train & Promote)

**Purpose:** Train models in Dev workspace, validate, and promote to Registry

```yaml
develop branch:
  Stage 1: Register Infrastructure (Auto)
    - Register environment (Dockerfile-based)
    - Register components
    - Detect changed circuits
    - Register MLTable per circuit
    - No approval needed - Dev experimentation
  
  Stage 2: Train Models in Dev Workspace (Auto)
    - Parallel training for changed circuits
    - Models use cutoff_date tag
    - Validate against dev thresholds (relaxed)
    - No approval needed - Dev validation
  
  Stage 3: Validate & Promote to Registry (⚠️ APPROVAL REQUIRED)
    - Check model metrics
    - Tag models as "registry-ready"
    
    🛡️ MANUAL APPROVAL:
      - Approvers: ML Engineers, Data Scientists
      - Review: Model metrics, training logs, validation results
      - Decision: Approve to promote to Registry
    
    - Copy models to Shared Registry
    - Copy environment to Registry (if changed)
    - Copy components to Registry (if changed)
    - Models available for Test/Prod
```

**Output:** Approved models in Registry, ready for deployment  
**Approval:** Required before Registry promotion

### 2. Build Pipeline - `release/*` Branch (Deploy from Registry)

**Purpose:** Deploy Registry models to Test endpoints for QA validation

```yaml
release/* branch:
  Stage 1: Verify Registry Models (Auto)
    - Query Registry for latest approved models
    - Check model versions match expected
    - Verify model tags and metadata
    - Pull environment and components from Registry
  
  Stage 2: Deploy to Test Batch Endpoints (⚠️ APPROVAL REQUIRED)
    🛡️ MANUAL APPROVAL:
      - Approvers: QA Lead, ML Engineering Lead
      - Review: Registry model versions, deployment plan
      - Decision: Approve to deploy to Test
    
    - Create/update Test batch endpoints
    - Pull models FROM Registry
    - Configure endpoint settings (test thresholds)
    - Deploy new model version
  
  Stage 3: Integration Testing (Auto)
    - Run smoke tests on Test endpoints
    - Validate predictions
### 3. Build Pipeline - `main` Branch (Deploy to Production)

**Purpose:** Deploy Registry models to Production batch endpoints

```yaml
main branch:
  Stage 1: Verify Registry Models (Auto)
    - Query Registry for "production-ready" models
    - Check models passed QA sign-off in Test
    - Verify production readiness tags
    - Pull environment and components from Registry
  
  Stage 2: Production Deployment (⚠️ APPROVAL REQUIRED)
    🛡️ MANUAL APPROVAL:
      - Approvers: Senior ML Engineer, Platform Lead
      - Review: QA test results, deployment plan, rollback plan
      - Decision: Approve for Production deployment
      - Change Management: Require change ticket/JIRA number
      - Note: Single approval for batch endpoints (no traffic ramp needed)
    
    - Create/update Prod batch endpoints
    - Pull models FROM Registry
    - Configure endpoint settings (strict thresholds)
    - Deploy new model version
    - Track previous deployment for rollback
  
  Stage 3: Production Validation (Auto)
    - Run smoke tests on Prod batch endpoints
    - Submit test batch job
    - Validate predictions quality
    - Check job completion time
    - Verify SLAs met
    - Send deployment notification
```

**Output:** Models deployed to Production batch endpoints  
**Approval:** Single gate (simpler for batch processing, no traffic ramp)
### 4. Rollback Pipeline (Manual)

Manual trigger for quick endpoint rollback:

```yaml
Rollback Pipeline:
  Parameters:
    - Circuit IDs
    - Environment (Test/Production only)
    - Rollback type (previous/specific)
    - Model version from Registry
  
  Stage 1: Rollback Request (Auto)
    - Identify target endpoint
    - Query Registry for rollback version
    - Generate rollback plan
    - Show diff (current vs rollback version)
  
  Stage 2: Rollback Approval (⚠️ APPROVAL REQUIRED)
    🛡️ MANUAL APPROVAL:
      Test Environment:
        - Approvers: QA Lead
        - Review: Rollback reason, target version
      
      Production Environment:
        - Approvers: Senior ML Engineer, Platform Lead, Incident Commander
        - Review: Incident details, rollback version, impact assessment
        - Priority: Expedited for P0/P1 incidents
  
  Stage 3: Execute Rollback (Auto after approval)
    - Update endpoint to previous Registry model version
    - 100% traffic to rollback version immediately
    - Disable problematic version
  
  Stage 4: Validate Rollback (Auto)
    - Run smoke tests
    - Verify issue resolved
    - Send notification
    - Create incident post-mortem ticket
```

**Note:** Rollback changes endpoint configuration, doesn't modify Registry  
**Approval:** Required, but expedited for production incidents
    - Run smoke tests on Prod endpoints
    - Monitor predictions and latency
    - Verify SLAs met
    - Send deployment notification
    - Update status page
```



**Output:** Models deployed to Production, serving live traffic

### 4. Rollback Pipeline (Manual)

Manual trigger for quick endpoint rollback:

```yaml
Parameters:
  - Circuit IDs
  - Environment (Test/Production only - Dev doesn't need rollback)
  - Rollback type (previous/specific)
  - Model version from Registry
```

**Note:** Rollback changes endpoint configuration, doesn't modify Registry

## Development Workflow

### Feature Development

```bash
# 1. Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/sensor-preprocessing

# 2. Make changes, commit
git add .
git commit -m "feat: improve sensor preprocessing"

# 3. Push and create PR to develop
git push origin feature/sensor-preprocessing
# Create PR: feature/sensor-preprocessing → develop

# 4. PR triggers build pipeline
# - Train models in Dev workspace
# - Validate models
# - NO promotion to Registry (only on merge)

# 5. Merge to develop
git checkout develop
git merge feature/sensor-preprocessing
git push origin develop

# 6. Build pipeline on develop branch
# - Train models in Dev workspace
# - Validate against dev thresholds
# - Promote validated models to Registry
# - Models now available for Test/Prod deployment
```

### Release Preparation

```bash
# 1. Ensure develop has promoted models to Registry
git checkout develop
git pull origin develop
# Verify: Build pipeline completed and models in Registry

# 2. Create release branch from develop
git checkout -b release/v1.1.0

# 3. Push release branch
git push origin release/v1.1.0

# 4. Build pipeline deploys from Registry to Test
# - Pulls models FROM Registry (no training)
# - Deploys to Test batch endpoints
# - Runs integration tests
# - QA validates functionality

# 5. If issues found in Test (code/config issues, NOT model issues):
git checkout release/v1.1.0
# ... fix deployment/endpoint config ...
git commit -m "fix: correct endpoint configuration"
git push origin release/v1.1.0
# Re-deploys to Test (still same Registry models)

# 6. If model issues found - go back to develop:
### Production Deployment

```bash
# 1. Ensure Test validation passed
# - QA sign-off received
# - Integration tests passed
# - Models in Registry are production-ready

# 2. Merge release to main
git checkout main
git pull origin main
git merge --no-ff release/v1.1.0 -m "release: v1.1.0"
git push origin main

# 3. Build pipeline runs on main branch
# - Verifies Registry models
# - Pulls SAME models from Registry (no retraining)
# - Deploys to Production batch endpoints
# - Blue-green deployment with traffic ramp
# - Tracks previous deployment for rollback

# 4. Production validation
# - Smoke tests run automatically
# - Monitor initial predictions
# - Requires manual approval to proceed

# 5. Tag the release
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0

# 6. Merge back to develop
git checkout develop
git merge main
git push origin develop

# 7. Delete release branch
git branch -d release/v1.1.0
git push origin --delete release/v1.1.0
```. Release pipeline auto-triggers
# - Stage 1: Promote to Registry (requires approval)
# - Stage 2: Update Test endpoints
# - Stage 3: Update Production endpoints (requires approval)

# 4. Tag the release
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0

# 5. Merge back to develop
git checkout develop
git merge main
git push origin develop

# 6. Delete release branch
git branch -d release/v1.1.0
git push origin --delete release/v1.1.0
```

## Hotfix Workflow

### Case 1: Deployment/Endpoint Issue (No Model Change)

For endpoint configuration or deployment issues:

```bash
# 1. Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/endpoint-config

# 2. Fix deployment/endpoint configuration
git add .
git commit -m "fix: correct batch endpoint timeout"
git push origin hotfix/endpoint-config

# 3. PR triggers build pipeline
# - Pulls existing models from Registry
# - Deploys to Prod with fixed configuration
# - No training, just redeployment

# 4. Merge to main
git checkout main
git merge --no-ff hotfix/endpoint-config
git push origin main

# 5. Tag hotfix
git tag -a v1.0.1 -m "Hotfix v1.0.1"
git push origin v1.0.1

# 6. Merge back to develop
git checkout develop
git merge main
git push origin develop

# 7. Delete hotfix branch
git branch -d hotfix/endpoint-config
git push origin --delete hotfix/endpoint-config
```

### Case 2: Model Issue (Requires Retraining)

For actual model or training issues:

```bash
# 1. Create hotfix branch from develop (NOT main)
git checkout develop
git pull origin develop
git checkout -b hotfix/model-critical-bug

# 2. Fix model training code
git add .
git commit -m "fix: resolve critical model scoring issue"
git push origin hotfix/model-critical-bug

# 3. PR triggers build pipeline on develop
# - Trains models in Dev workspace
# - Validates fixes
# - Promotes to Registry with new version

# 4. Merge to develop
git checkout develop
git merge --no-ff hotfix/model-critical-bug
git push origin develop

# 5. Create emergency release branch
git checkout -b release/v1.0.1-hotfix
git push origin release/v1.0.1-hotfix
# - Deploys new models from Registry to Test
# - Fast-track QA validation

# 6. Merge to main (expedited)
git checkout main
git merge --no-ff release/v1.0.1-hotfix
git push origin main
# - Deploys new models from Registry to Prod

# 7. Tag hotfix
git tag -a v1.0.1 -m "Hotfix v1.0.1"
git push origin v1.0.1

# 8. Cleanup
git branch -d hotfix/model-critical-bug
git branch -d release/v1.0.1-hotfix
git push origin --delete release/v1.0.1-hotfix
```

## Version Bump Workflow

When updating the custom package:

```bash
# 1. On develop branch
git checkout develop

# 2. Update package version
vim src/packages/sensor-forecasting/version.py
# Change: __version__ = "1.1.0"

# 3. Update environment version
vim config/environment.yaml
# Change: version: "1.1.0"
# Change: package_version: "1.1.0"

# 4. Commit both together
git add src/packages/sensor-forecasting/version.py config/environment.yaml
git commit -m "bump: sensor-forecasting to v1.1.0"
git push origin develop

# 5. Build pipeline on develop branch
# - Detects environment.yaml change
# - Retrains ALL circuits with new package version in Dev workspace
# - Validates models
# - Promotes to Registry with new package version tag

# 6. Follow release process to deploy to Test → Prod
# - release/* branch: Deploy new models from Registry to Test
# - main branch: Deploy new models from Registry to Prod
```

## PR Strategy

### Pull Request to `develop`

- **Triggers:** Build pipeline (Dev environment)
- **Required Checks:**
  - Build passes
  - Unit tests pass
  - Changed circuits train successfully
- **Reviewers:** 1+ team member
- **Auto-merge:** Not recommended

### Pull Request to `release/*`

- **Triggers:** Build pipeline (Test environment)
- **Required Checks:**
  - Build passes
  - Integration tests pass
  - All circuits validate
- **Reviewers:** 1+ team member + QA
- **Auto-merge:** Not recommended

### Pull Request to `main`

- **Triggers:** Build pipeline (Prod environment) + Release pipeline
- **Required Checks:**
  - Build passes
  - All validation tests pass
  - Release notes included
- **Reviewers:** 2+ senior team members
- **Approval:** Required
- **Auto-merge:** Never

## Branch Protection Rules

### `develop` Branch

```yaml
Required:
  - Pull request before merge
  - 1 approval
  - Passing build
  - Up-to-date with base branch

Allowed:
  - Direct commits from CI/CD (merge from main)
```

### `release/*` Branches

```yaml
Required:
  - Pull request before merge
  - 1 approval (with QA)
  - Passing build + tests
  - Up-to-date with base branch

Allowed:
  - Hotfix commits
  - Merge from main (hotfixes)
```

### `main` Branch

```yaml
Required:
  - Pull request before merge
  - 2 approvals
  - Passing build + all tests
  - Up-to-date with base branch
  - Release notes

Restricted:
  - No direct commits
  - No force push
  - No deletion
```

## Pipeline Variables

Each environment has its own variable group:

### `mlops-dev-variables`

```yaml
azureServiceConnection: 'Azure-MLOps-Dev'
workspaceName: 'mlops-dev-workspace'
resourceGroup: 'mlops-dev-rg'
location: 'eastus'
```
## Model Lifecycle Flow with Approval Gates

```
┌─────────────────────────────────────────────────────────────────┐
│ develop branch                                                   │
│ ┌──────────────┐     ┌──────────────┐     🛡️     ┌───────────┐ │
│ │ Train Models │ --> │   Validate   │ --> │ A │ ->│ Promote   │ │
│ │ (Dev WS)     │     │   (dev)      │     │ P │   │ Registry  │ │
│ │              │     │              │     │ P │   │           │ │
│ └──────────────┘     └──────────────┘     └───┘   └───────────┘ │
│                                            ML Engineers           │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                      ┌──────────────────────┐
                      │  Shared Registry     │ ◄── Single Source of Truth
                      │  (Immutable)         │     Approved artifacts only
                      │  - Models            │
                      │  - Environments      │
                      │  - Components        │
                      └──────────────────────┘
                            │           │
               ┌────────────┘           └────────────┐
               ▼                                     ▼
┌───────────────────────────────┐      ┌────────────────────────────────┐
│ release/* branch              │      │ main branch                    │
│                               │      │                                │
│ ┌──────────────┐              │      │ ┌──────────────┐               │
│ │ Pull from    │              │      │ │ Pull from    │               │
│ │ Registry     │              │      │ │ Registry     │               │
│ └──────────────┘              │      │ └──────────────┘               │
│        │                      │      │        │                       │
│        ▼                      │      │        ▼                       │
│   🛡️                          │      │   🛡️                           │
│  │ A │  QA Lead               │      │  │ A │  Sr ML Eng + VP        │
│  │ P │                        │      │  │ P │                        │
│  │ P │                        │      │  │ P │                        │
│  └───┘                        │      │  └───┘                        │
│        │                      │      │        │                       │
│        ▼                      │      │        ▼                       │
│ ┌──────────────┐              │      │ ┌──────────────┐               │
## Approval Matrix

| Stage | Environment | Approvers | SLA | Can Skip? |
|-------|-------------|-----------|-----|-----------|
| **Promote to Registry** | Dev → Registry | ML Engineer or Data Scientist | 24 hours | No |
| **Deploy to Test** | Registry → Test | QA Lead + ML Engineering Lead | 4 hours | No |
| **QA Sign-Off** | Test validation | QA Team + Product Owner | 48 hours | No |
| **Deploy to Production** | Registry → Prod | Sr ML Engineer + Platform Lead | 24 hours | No |
| **Rollback (Test)** | Test | QA Lead | Immediate | No |
| **Rollback (Prod)** | Production | Sr ML Engineer + Incident Commander | Expedited | No |

**Approval SLAs:**
- **Standard:** Approvers have X hours to approve/reject
- **Expedited:** High-priority incidents, approvers notified immediately
- **Immediate:** No wait time, approve in real-time during deployment

**Notification Channels:**
- Email to approvers
- Slack channel (#mlops-approvals)
- PagerDuty for Production approvals
- Teams/webhook for audit trail

## Best Practices

1. **Never commit directly to `main`** - Always use PR workflow
2. **Keep `develop` stable** - Don't merge broken features
3. **Train only in `develop`** - Test/Prod pull from Registry
4. **Registry is immutable** - Never delete or modify models in Registry
5. **Version everything** - Models, packages, deployments all versioned
6. **Approval gates are mandatory** - No bypassing without incident
7. **Document approval decisions** - Require comments when approving/rejecting
8. **Short-lived feature branches** - Merge within 2-3 days
9. **Release branches for QA** - Dedicated validation before production
10. **Tag all releases** - Use semantic versioning
11. **Document breaking changes** - Update CHANGELOG.md
12. **Merge `main` back to `develop`** - Keep branches synchronized
13. **Delete merged branches** - Keep repository clean
14. **Monitor Registry storage** - Archive old models periodically
15. **Test from Registry** - Always test what will go to production
16. **Rollback from Registry** - Use previous versions for quick recovery
17. **Audit all approvals** - Log who approved what and when
18. **Escalation path** - Define who to contact if approvers unavailable
│  └───┘                        │      │                                │
└───────────────────────────────┘      └────────────────────────────────┘

Legend:
🛡️ - Manual Approval Required
APP - Approval Gate
```
```bash
# During release branch validation, revert to previous Registry version
# Manual trigger of rollback pipeline:
Environment: Test
Circuits: ALL or specific circuits
Rollback Type: previous
Model Version: Pull previous version from Registry
```

### Production Rollback

```bash
# Critical production issue - immediate rollback
# Manual trigger of rollback pipeline:
Environment: Production
Circuits: PLANT001_CIRCUIT01,PLANT001_CIRCUIT02
Rollback Type: previous or specific
Model Version: Specify Registry model version (e.g., v1.0.0)

# Rollback updates endpoint to use previous model from Registry
# Does NOT modify Registry itself
# Previous model is still available in Registry
```rce Branch: main
Circuits: PLANT001_CIRCUIT01,PLANT001_CIRCUIT02
Rollback Type: specific
Specific Deployment: lstm-model-v1-0-0
```
## Model Lifecycle Flow

```
┌─────────────────────────────────────────────────────────────┐
│ develop branch                                               │
│ ┌──────────────┐     ┌──────────────┐     ┌──────────────┐ │
│ │ Train Models │ --> │   Validate   │ --> │  Promote to  │ │
│ │ (Dev WS)     │     │   (dev)      │     │   Registry   │ │
│ └──────────────┘     └──────────────┘     └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Shared Registry │ ◄── Single Source of Truth
                    │  (Immutable)    │     All environments use same models
                    └─────────────────┘
                         │         │
            ┌────────────┘         └────────────┐
            ▼                                   ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│ release/* branch        │         │ main branch             │
│ ┌──────────────┐        │         │ ┌──────────────┐        │
│ │ Pull from    │        │         │ │ Pull from    │        │
│ │ Registry     │        │         │ │ Registry     │        │
│ └──────────────┘        │         │ └──────────────┘        │
│        │                │         │        │                │
│        ▼                │         │        ▼                │
│ ┌──────────────┐        │         │ ┌──────────────┐        │
│ │ Deploy to    │        │         │ │ Deploy to    │        │
│ │ Test         │        │         │ │ Production   │        │
│ │ Endpoints    │        │         │ │ Endpoints    │        │
│ └──────────────┘        │         │ └──────────────┘        │
│        │                │         │        │                │
│        ▼                │         │        ▼                │
│ ┌──────────────┐        │         │ ┌──────────────┐        │
│ │ Integration  │        │         │ │ Production   │        │
│ │ Tests        │        │         │ │ Validation   │        │
│ └──────────────┘        │         │ └──────────────┘        │
└─────────────────────────┘         └─────────────────────────┘
```

## Best Practices

1. **Never commit directly to `main`** - Always use PR workflow
2. **Keep `develop` stable** - Don't merge broken features
3. **Train only in `develop`** - Test/Prod pull from Registry
4. **Registry is immutable** - Never delete or modify models in Registry
5. **Version everything** - Models, packages, deployments all versioned
6. **Short-lived feature branches** - Merge within 2-3 days
7. **Release branches for QA** - Dedicated validation before production
8. **Tag all releases** - Use semantic versioning
9. **Document breaking changes** - Update CHANGELOG.md
10. **Merge `main` back to `develop`** - Keep branches synchronized
11. **Delete merged branches** - Keep repository clean
12. **Monitor Registry storage** - Archive old models periodically
13. **Test from Registry** - Always test what will go to production
14. **Rollback from Registry** - Use previous versions for quick recovery
4. **Version bumps on `develop`** - Test thoroughly before releasing
5. **Release branches for QA** - Dedicated branch for testing
6. **Tag all releases** - Use semantic versioning
7. **Document breaking changes** - Update CHANGELOG.md
8. **Merge `main` back to `develop`** - Keep branches synchronized
9. **Delete merged branches** - Keep repository clean
10. **Monitor pipeline failures** - Address CI/CD issues immediately
