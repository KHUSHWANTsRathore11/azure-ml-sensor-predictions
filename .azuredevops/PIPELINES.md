# Pipeline Architecture Guide

This guide explains the separated pipeline structure for the Azure ML sensor predictions project.

See `.azuredevops/README.md` for comprehensive documentation.

## Quick Reference

### 4 Focused Pipelines

1. **PR Validation** (`pr-validation-pipeline.yml`)
   - Trigger: PRs to `develop`, `release/*`, `main`
   - Purpose: Validate configs, check versions, lint code
   - Fast feedback: ~2-3 minutes

2. **Training Pipeline** (`training-pipeline.yml`)
   - Branch: `develop`
   - Purpose: Train models in Dev, promote to Registry
   - Trigger: Auto on merge to develop

3. **Test Deployment** (`test-deployment-pipeline.yml`)
   - Branch: `release/*`
   - Purpose: Deploy from Registry to Test
   - Trigger: Auto on release branches or manual

4. **Production Deployment** (`prod-deployment-pipeline.yml`)
   - Branch: `main`
   - Purpose: Deploy production-ready models
   - Trigger: Auto on main or manual

### Shared Templates

- `templates/install-ml-extension.yml` - Install Azure ML CLI
- `templates/configure-ml-defaults.yml` - Configure workspace defaults
- `templates/generate-circuit-configs.yml` - Generate circuit configs

## Setup Checklist

- [ ] Create 4 pipelines in Azure DevOps
  - [ ] PR Validation Pipeline
  - [ ] Training Pipeline
  - [ ] Test Deployment Pipeline
  - [ ] Production Deployment Pipeline
- [ ] Configure 4 environment approval gates
- [ ] Set up 4 variable groups
- [ ] Test each pipeline independently
- [ ] Archive old `build-pipeline.yml`

## Benefits

✅ **Fast PR Feedback** - Validation in 2-3 minutes  
✅ **Independent** - Run deployments without retraining  
✅ **Faster** - No skipped stages  
✅ **Cleaner** - 350-800 lines vs 2,700 lines  
✅ **Safer** - Approval gates at each stage  
✅ **Quality** - Automated linting and formatting checks

Read `.azuredevops/README.md` for detailed documentation.
