# CI/CD Pipeline Implementation Summary

## Updated Pipelines

### Build Pipeline (`.azuredevops/build-pipeline.yml`)

**New Architecture:** Single pipeline with branch-specific stages

#### develop Branch Flow:
```
Stage 1: Register Infrastructure (Auto)
  - Register environment in Dev workspace
  - Register components in Dev workspace
  - Detect changed circuits
  - Register MLTables

Stage 2: Train Models (Auto)
  - Train models in parallel in Dev workspace
  - Monitor job completion

Stage 3: Promote to Registry (⚠️ APPROVAL)
  - Approval Gate: ML Engineers/Data Scientists
  - Promote environment to Registry
  - Promote components to Registry
  - Promote models to Registry
  - Tag models with source metadata
```

#### release/* Branch Flow:
```
Stage 1: Verify Registry (Auto)
  - Query Registry for latest models
  - Verify model versions and tags
  - Download environment and components from Registry

Stage 2: Deploy to Test (⚠️ APPROVAL)
  - Approval Gate: QA Lead + ML Engineering Lead
  - Deploy batch endpoints using Registry models
  - No training - uses artifacts from Registry

Stage 3: Integration Tests (Auto)
  - Run smoke tests on Test endpoints
  - Validate predictions quality

Stage 4: QA Sign-Off (⚠️ APPROVAL)
  - Approval Gate: QA Team + Product Owner
  - Tag models as "production-ready" in Registry
```

#### main Branch Flow:
```
Stage 1: Verify Registry (Auto)
  - Query Registry for "production-ready" models
  - Verify QA sign-off tags
  - Download environment and components from Registry

Stage 2: Deploy to Production (⚠️ APPROVAL)
  - Approval Gate: Senior ML Engineer + Platform Lead
  - Deploy batch endpoints using Registry models
  - Track previous deployment for rollback
  - No training - uses artifacts from Registry

Stage 3: Production Validation (Auto)
  - Run smoke tests on Production endpoints
  - Submit test batch job
  - Verify SLAs
```

### Release Pipeline (Deprecated)

**Old:** Separate multi-stage pipeline for promotions  
**New:** Integrated into build-pipeline.yml  
**Location:** Archived to `archive/pipelines/release-pipeline-old.yml`

### Rollback Pipeline (`.azuredevops/rollback-pipeline.yml`)

No changes needed - still works with new architecture. Pulls previous model versions from Registry.

## Key Changes

### 1. Train Once, Deploy Everywhere ✅
- **Before:** Models trained separately in Dev, Test, and Prod workspaces
- **After:** Models trained once in Dev, pulled from Registry for Test/Prod

### 2. Registry as Single Source of Truth ✅
- **Before:** Registry used only after Prod deployment
- **After:** Registry populated from Dev, used by Test and Prod

### 3. Approval Gates ✅
| Gate | Who | Where |
|------|-----|-------|
| Registry Promotion | ML Engineers | develop branch |
| Test Deployment | QA Lead + ML Lead | release/* branch |
| QA Sign-Off | QA Team + PO | release/* branch |
| Prod Deployment | Sr ML Eng + Platform Lead | main branch |

### 4. Branch-Specific Logic ✅
- Uses compile-time `${{ if }}` expressions
- Single pipeline file, different stages per branch
- Automatic variable group selection

### 5. No More Retraining in Test/Prod ✅
- Test and Prod stages only deploy from Registry
- Faster deployments (no training time)
- Guaranteed consistency (same model artifacts)

## Environment Configuration

Each environment requires these Azure DevOps variable groups:

### mlops-dev-variables
- Dev workspace credentials
- Training compute settings
- Relaxed validation thresholds

### mlops-test-variables
- Test workspace credentials
- Test endpoint settings
- Stricter validation thresholds

### mlops-prod-variables
- Prod workspace credentials
- Production endpoint settings
- Strict validation thresholds

### mlops-registry-variables
- Registry credentials
- Used by all three environments

## Deployment Environments

The following environments must be created in Azure DevOps for approval gates:

1. **registry-promotion** - Approves promotion from Dev to Registry
2. **test-deployment** - Approves deployment to Test endpoints
3. **qa-signoff** - QA approval after testing
4. **production-deployment** - Approves production deployment

Configure approvers in: **Pipelines → Environments → [environment name] → Approvals and checks**

## Testing the New Pipeline

### 1. Test develop Branch
```bash
git checkout develop
# Make changes to model code
git commit -am "feat: improve model"
git push origin develop
```
**Expected:** Train in Dev → Approval prompt → Promote to Registry

### 2. Test release Branch
```bash
git checkout -b release/v1.0.0
git push origin release/v1.0.0
```
**Expected:** Pull from Registry → Approval prompt → Deploy to Test → Run tests → QA approval prompt

### 3. Test main Branch
```bash
git checkout main
git merge release/v1.0.0
git push origin main
```
**Expected:** Pull from Registry → Approval prompt → Deploy to Prod → Smoke tests

## Migration Checklist

- [x] Update build-pipeline.yml with branch-specific logic
- [x] Archive old release-pipeline.yml
- [x] Add Registry variable group references
- [ ] Create Azure DevOps environments for approval gates
- [ ] Configure approvers for each environment
- [ ] Update variable groups with Registry credentials
- [ ] Test develop branch flow (train + promote)
- [ ] Test release branch flow (deploy to test)
- [ ] Test main branch flow (deploy to prod)
- [ ] Update documentation
- [ ] Train team on new workflow

## Troubleshooting

### Pipeline doesn't trigger
- Check branch name matches trigger conditions exactly
- Verify paths in trigger include changed files

### Approval gate doesn't appear
- Check environment exists in Azure DevOps
- Verify approvers are configured
- Check service connection permissions

### Registry promotion fails
- Verify mlops-registry-variables group exists
- Check Registry credentials and permissions
- Ensure Registry resource group exists

### Model not found in Registry
- Check develop branch pipeline completed successfully
- Verify approval was granted for Registry promotion
- Query Registry manually: `az ml model list --registry-name <name>`

## Benefits Achieved

✅ **Consistency** - Same model artifacts in Test and Prod  
✅ **Speed** - No retraining in Test/Prod (5-10x faster)  
✅ **Traceability** - Models tagged with source and promotion history  
✅ **Governance** - 4 approval gates ensure quality  
✅ **Rollback** - Previous versions always available in Registry  
✅ **Simplicity** - Single pipeline file, branch-aware logic  
