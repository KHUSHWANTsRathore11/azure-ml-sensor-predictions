# Environment Configuration - Reference Only

⚠️ **IMPORTANT:** These files are **reference documentation only**.

**Pipelines do NOT load these files.** All configuration is managed via **Azure DevOps Variable Groups**.

## Purpose

These YAML files serve as:
- 📋 Documentation of Variable Group contents
- 📝 Templates for creating new environments
- 🔍 Quick reference when updating Variable Groups

## Files

- **`dev.yaml`** - Dev environment reference (training workspace)
- **`test.yaml`** - Test environment reference (deployment only)
- **`prod.yaml`** - Prod environment reference (deployment only)

## How to Use

1. **View** the YAML file for your environment
2. **Copy** values from the `variable_groups` section
3. **Go to** Azure DevOps → Pipelines → Library
4. **Create/Update** the corresponding Variable Group
5. **Paste** values into the Variable Group

## Complete Setup Guide

See **`docs/VARIABLE_GROUPS_REFERENCE.md`** for:
- Complete list of all 6 Variable Groups
- All required variables for each group
- Setup instructions
- Pipeline usage
- Approval environments
- Troubleshooting

## Environment Roles

### Dev Environment
- **Training:** ✅ Yes (only environment that trains)
- **Deployment:** ✅ Yes (for testing)
- **Branch:** `develop`
- **Variable Groups:** `mlops-dev-variables`, `mlops-registry-variables`, `mlops-pipeline-settings`

### Test Environment
- **Training:** ❌ No (deploys from Registry)
- **Deployment:** ✅ Yes
- **Branch:** `release/*`
- **Variable Groups:** `mlops-test-variables`, `mlops-registry-variables`

### Prod Environment
- **Training:** ❌ No (deploys from Registry)
- **Deployment:** ✅ Yes
- **Branch:** `main`
- **Variable Groups:** `mlops-prod-variables`, `mlops-registry-variables`

## Workflow

```
Dev (develop branch)
├─ Train models
├─ Register in Dev workspace
└─ Promote to Registry (with approval)
   ↓
Registry (shared)
├─ Stores approved models
└─ Source for Test/Prod deployments
   ↓
Test/Prod (release/main branches)
└─ Deploy from Registry
```

## Quick Reference

| What | Where | How |
|------|-------|-----|
| **Actual config** | Azure DevOps Variable Groups | Pipelines → Library |
| **Reference docs** | This directory (`config/environments/`) | View YAML files |
| **Complete guide** | `docs/VARIABLE_GROUPS_REFERENCE.md` | Full setup instructions |
| **Approvals** | Azure DevOps Environments | Pipelines → Environments |

## Updating Configuration

**To change a setting:**

1. ✅ Update Variable Group in Azure DevOps
2. ✅ Update reference YAML file (for documentation)
3. ❌ Do NOT commit secrets to YAML files

**Next pipeline run** uses the new Variable Group value automatically!
