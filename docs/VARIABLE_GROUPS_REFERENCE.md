# Azure DevOps Variable Groups - Complete Reference

## Overview

This is the **single source of truth** for all Variable Groups used across MLOps pipelines.

**All pipeline configuration is managed via Azure DevOps Variable Groups** - not in code or YAML files.

## Variable Groups Summary

| Group Name | Used By | Purpose |
|------------|---------|---------|
| `mlops-dev-variables` | training-pipeline, promote-single-model | Dev workspace connection & settings |
| `mlops-test-variables` | test-deployment, rollback | Test workspace connection & settings |
| `mlops-prod-variables` | prod-deployment, rollback | Prod workspace connection & settings |
| `mlops-registry-variables` | training, promote-single-model, test-deployment, prod-deployment | Registry connection & propagation settings |
| `mlops-pipeline-settings` | training, pr-validation, promote-single-model | Pipeline execution settings (monitoring, validation, Python version) |
| `mlops-shared-variables` | pr-validation | Storage account for PR validation |

---

## 1. mlops-dev-variables

**Used by:** `training-pipeline.yml`, `promote-single-model-pipeline.yml`

**Purpose:** Dev workspace Azure ML connection settings

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `azureServiceConnection` | Azure DevOps service connection name | `Azure-MLOps-Dev` |
| `subscriptionId` | Azure subscription ID | `12345678-1234-...` |
| `resourceGroup` | Resource group for Dev workspace | `mlops-dev-rg` |
| `workspaceName` | Dev workspace name | `mlops-dev-workspace` |
| `location` | Azure region | `eastus` |

---

## 2. mlops-test-variables

**Used by:** `test-deployment-pipeline.yml`, `rollback-pipeline.yml`

**Purpose:** Test workspace Azure ML connection settings

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `azureServiceConnection` | Azure DevOps service connection name | `Azure-MLOps-Test` |
| `subscriptionId` | Azure subscription ID | `12345678-1234-...` |
| `resourceGroup` | Resource group for Test workspace | `mlops-test-rg` |
| `workspaceName` | Test workspace name | `mlops-test-workspace` |
| `location` | Azure region | `eastus` |
| `testScoringCluster` | Scoring compute cluster name | `test-scoring-cluster` |

---

## 3. mlops-prod-variables

**Used by:** `prod-deployment-pipeline.yml`, `rollback-pipeline.yml`

**Purpose:** Prod workspace Azure ML connection settings

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `azureServiceConnection` | Azure DevOps service connection name | `Azure-MLOps-Prod` |
| `subscriptionId` | Azure subscription ID | `12345678-1234-...` |
| `resourceGroup` | Resource group for Prod workspace | `mlops-prod-rg` |
| `workspaceName` | Prod workspace name | `mlops-prod-workspace` |
| `location` | Azure region | `eastus` |
| `prodScoringCluster` | Scoring compute cluster name | `prod-scoring-cluster` |

---

## 4. mlops-registry-variables

**Used by:** `training-pipeline.yml`, `promote-single-model-pipeline.yml`, `test-deployment-pipeline.yml`, `prod-deployment-pipeline.yml`

**Purpose:** Azure ML Registry connection and model propagation settings

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `registryName` | Azure ML Registry name | `mlops-central-registry` |
| `registryResourceGroup` | Resource group for registry | `mlops-registry-rg` |
| `registryPropagationMaxWaitSeconds` | Max wait time for model to appear in registry after sharing | `120` |
| `registryPropagationInitialDelaySeconds` | Initial delay before first retry (exponential backoff) | `2` |
| `registryPropagationMaxDelaySeconds` | Maximum delay between retries (exponential backoff cap) | `30` |

**Propagation Settings Explanation:**
- Uses exponential backoff: 2s → 4s → 8s → 16s → 30s (capped) → 30s...
- Total max wait: 120 seconds
- Handles async nature of model sharing to registry

---

## 5. mlops-pipeline-settings

**Used by:** `training-pipeline.yml`, `pr-validation-pipeline.yml`, `promote-single-model-pipeline.yml`

**Purpose:** Pipeline execution settings (monitoring, validation, Python version, notifications)

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| **Python & Runtime** | | |
| `pythonVersion` | Python version for pipeline execution | `3.9` |
| `longRunningJobNotificationIntervalHours` | Notification interval for long jobs | `4` |
| `mlEngineersEmail` | Email for pipeline notifications (comma-separated) | `ml-team@company.com` |
| **Monitoring** | | |
| `monitoringMaxWaitHours` | Training job timeout (hours) | `3` |
| `monitoringPollIntervalSeconds` | How often to check job status | `30` |
| `monitoringLogLevel` | Log verbosity | `DEBUG` |
| **Validation** | | |
| `validationMinAccuracy` | Minimum model accuracy for PR validation | `0.70` |
| `validationMaxMae` | Maximum Mean Absolute Error | `10.0` |
| `validationMaxRmse` | Maximum Root Mean Square Error | `15.0` |
| **Retention** | | |
| `retentionModelsDays` | Model retention period (days) | `30` |
| `retentionLogsDays` | Pipeline log retention (days) | `14` |

---

## 6. mlops-shared-variables

**Used by:** `pr-validation-pipeline.yml`

**Purpose:** Shared resources for PR validation (storage account, workspace references for validation)

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `azureServiceConnection` | Azure service connection for PR validation | `Azure-MLOps-Shared` |
| `storageAccountName` | Storage account for validation data | `mlopsstorage` |
| `dataContainer` | Container name for validation datasets | `validation-data` |
| `mlopsDevWorkspace` | Dev workspace name (for validation checks) | `mlops-dev-workspace` |
| `mlopsDevResourceGroup` | Dev resource group (for validation checks) | `mlops-dev-rg` |
| `mlopsTestWorkspace` | Test workspace name (for validation checks) | `mlops-test-workspace` |
| `mlopsTestResourceGroup` | Test resource group (for validation checks) | `mlops-test-rg` |
| `mlopsProdWorkspace` | Prod workspace name (for validation checks) | `mlops-prod-workspace` |
| `mlopsProdResourceGroup` | Prod resource group (for validation checks) | `mlops-prod-rg` |

**Note:** These workspace references are used by PR validation to check for conflicts across environments, not for actual deployments.

---

## Setup Instructions

### 1. Create Variable Groups

1. Go to **Azure DevOps** → **Pipelines** → **Library**
2. Click **+ Variable group**
3. Create each group listed above with exact names

### 2. Add Variables

For each Variable Group, add all variables listed in its section above.

**Tips:**
- Copy-paste variable names exactly (case-sensitive)
- Use example values as templates
- Mark sensitive values as "Keep this value secret"

### 3. Set Permissions

**Recommended:**
- **Dev groups:** All developers (read/write)
- **Test groups:** QA team + leads (read), leads only (write)
- **Prod groups:** Senior engineers only (read/write)
- **Registry/Shared:** Platform team only (write)

### 4. Link to Key Vault (Optional)

For service connections and secrets:
1. Variable → ⋯ → Link to Azure Key Vault
2. Select subscription and Key Vault
3. Choose secret name

---

## Pipeline Usage

### Training Pipeline

```yaml
variables:
  - group: mlops-dev-variables
  - group: mlops-registry-variables
  - group: mlops-pipeline-settings
```

Uses: Dev workspace, Registry, Pipeline settings

### Promote Single Model Pipeline

```yaml
variables:
  - group: mlops-dev-variables
  - group: mlops-registry-variables
  - group: mlops-pipeline-settings
```

Uses: Dev workspace (source), Registry (target), Pipeline settings

### Test Deployment Pipeline

```yaml
variables:
  - group: mlops-test-variables
  - group: mlops-registry-variables
```

Uses: Test workspace, Registry (source)

### Prod Deployment Pipeline

```yaml
variables:
  - group: mlops-prod-variables
  - group: mlops-registry-variables
```

Uses: Prod workspace, Registry (source)

### PR Validation Pipeline

```yaml
variables:
  - group: mlops-pipeline-settings
  - group: mlops-shared-variables
```

Uses: Pipeline settings, Shared storage

### Rollback Pipeline

```yaml
variables:
  - group: mlops-test-variables
  - group: mlops-prod-variables
```

Uses: Test and Prod workspaces

---

## Approval Environments

**Separate from Variable Groups** - configured in Azure DevOps Environments:

| Environment | Used By | Approvers |
|-------------|---------|-----------|
| `registry-promotion` | promote-single-model-pipeline | ML team leads |
| `test-deployment` | test-deployment-pipeline | QA team |
| `prod-deployment` | prod-deployment-pipeline | Senior engineers + platform lead |

**Setup:**
1. Azure DevOps → Pipelines → Environments
2. Create environment
3. Add approvers via Approvals and checks

---

## Updating Configuration

**To change a setting:**

1. Azure DevOps → Pipelines → Library
2. Select Variable Group
3. Click variable → Edit
4. Update value → Save

**Next pipeline run uses new value** - no code commit needed!

---

## Reference Documentation

The following files are **reference only** (not loaded by pipelines):

- `config/environments/dev.yaml` - Dev settings reference
- `config/environments/test.yaml` - Test settings reference
- `config/environments/prod.yaml` - Prod settings reference

**Use these files to:**
- Document what should be in Variable Groups
- Template for new environments
- Reference when updating Variable Groups

**Do NOT:**
- Expect pipelines to load these files
- Put actual secrets in these files
- Use these instead of Variable Groups

---

## Troubleshooting

### Variable not found in pipeline

**Check:**
1. Variable Group name matches exactly
2. Variable name matches exactly (case-sensitive)
3. Pipeline YAML includes correct `- group:` reference
4. Build service has permissions to Variable Group

### Wrong value being used

**Check:**
1. Correct Variable Group for environment
2. No hardcoded values in pipeline YAML overriding
3. Variable Group change was saved
4. Pipeline run is after the change

### Service connection not working

**Check:**
1. Service connection exists in Azure DevOps
2. Service connection name matches `azureServiceConnection` variable
3. Service connection has permissions to subscription/resource group
4. Service connection is not expired

---

## Best Practices

1. ✅ **Use Variable Groups for all config** - Never hardcode in YAML
2. ✅ **Keep reference docs updated** - Update `config/environments/*.yaml` when changing Variable Groups
3. ✅ **Test in Dev first** - Validate changes before updating Test/Prod
4. ✅ **Use secrets for sensitive data** - Mark as secret or link to Key Vault
5. ✅ **Document changes** - Add comments in Variable Group descriptions
6. ✅ **Restrict prod access** - Limit who can modify production Variable Groups
7. ✅ **Track changes** - Variable Groups have change history in Azure DevOps

---

## Migration Checklist

If setting up from scratch:

- [ ] Create all 6 Variable Groups
- [ ] Add all required variables to each group
- [ ] Set permissions on each group
- [ ] Create 3 approval environments
- [ ] Add approvers to environments
- [ ] Test with dummy pipelines first
- [ ] Run training pipeline end-to-end
- [ ] Verify model promotion with approval
- [ ] Test deployment pipelines
- [ ] Document any custom variables added
