# Setting Up Pipeline Variable Groups

This guide explains how to configure the `mlops-pipeline-settings` Variable Group in Azure DevOps.

## Why Variable Groups?

- ✅ No commits required to change settings
- ✅ Cleaner git history (config not in repo)
- ✅ Per-environment configuration
- ✅ UI-based management
- ✅ Access control via permissions

## Setup Instructions

### 1. Create Variable Group

1. Go to **Azure DevOps** → **Pipelines** → **Library**
2. Click **+ Variable group**
3. Name: `mlops-pipeline-settings`
4. Description: "Pipeline execution settings for training pipeline"

### 2. Add Variables

Add the following variables to the group:

#### Python & Runtime Settings

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `pythonVersion` | `3.9` | Python version for pipeline execution |
| `longRunningJobNotificationIntervalHours` | `4` | Notification interval for long jobs (hours) |
| `mlEngineersEmail` | `ml-team@company.com` | Email for pipeline notifications (comma-separated) |

#### Monitoring Settings

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `monitoringMaxWaitHours` | `3` | Training job timeout (hours) |
| `monitoringPollIntervalSeconds` | `30` | How often to check job status |
| `registryName` | `mlops-central-registry` | Name of the Azure ML Registry |
| `registryResourceGroup` | `mlops-registry-rg` | Resource group for registry |
| `registryPropagationMaxWaitSeconds` | `120` | Max time to wait for model to appear in registry after sharing |
| `registryPropagationInitialDelaySeconds` | `2` | Initial delay before first retry (exponential backoff) |
| `registryPropagationMaxDelaySeconds` | `30` | Maximum delay between retries (exponential backoff cap) |
| `monitoringLogLevel` | `DEBUG` | Log verbosity (DEBUG/INFO/WARNING) |

**Note:** The propagation settings use exponential backoff:
- Attempt 1: Wait 2s
- Attempt 2: Wait 4s
- Attempt 3: Wait 8s
- Attempt 4: Wait 16s
- Attempt 5+: Wait 30s (capped)
- Total max wait: 120s

### mlops-pipeline-settings

Pipeline execution settings for Dev environment (training).

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `validationMinAccuracy` | `0.70` | Minimum model accuracy for PR validation |
| `validationMaxMae` | `10.0` | Maximum Mean Absolute Error |
| `validationMaxRmse` | `15.0` | Maximum Root Mean Square Error |

#### Retention Settings

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `retentionModelsDays` | `30` | Model retention period (days) |
| `retentionLogsDays` | `14` | Pipeline log retention (days) |

### 3. Set Permissions

**Recommended permissions:**
- **Administrators:** Full control
- **Contributors:** Read only (cannot edit)
- **Build Service:** User (can read)

To restrict who can modify production settings, create separate groups per environment.

### 4. Verify in Pipeline

The `training-pipeline.yml` already references this group:

```yaml
variables:
  - group: mlops-pipeline-settings
```

Variables are automatically available in the pipeline:

```yaml
steps:
  - script: |
      python monitor.py --max-wait-hours $(monitoringMaxWaitHours)
```

## Per-Environment Configuration

For different settings per environment, create multiple groups:

- `mlops-pipeline-settings-dev` (relaxed thresholds)
- `mlops-pipeline-settings-test` (moderate thresholds)
- `mlops-pipeline-settings-prod` (strict thresholds)

Update pipeline to load conditionally:

```yaml
variables:
  - ${{ if eq(variables['Build.SourceBranch'], 'refs/heads/develop') }}:
    - group: mlops-pipeline-settings-dev
  - ${{ if eq(variables['Build.SourceBranch'], 'refs/heads/main') }}:
    - group: mlops-pipeline-settings-prod
```

## Reference Values

Use `config/environments/dev.yaml` as the source of truth for what values should be set in the Variable Group. The YAML files are reference documentation.

**Workflow:**
1. Decide on a setting value
2. Document in `config/environments/dev.yaml`
3. Set in Variable Group `mlops-pipeline-settings`
4. Pipeline reads from Variable Group

## Updating Settings

**To change a setting:**

1. Go to **Pipelines** → **Library** → `mlops-pipeline-settings`
2. Click the variable to edit
3. Change the value
4. Save

**Next pipeline run** will use the new value automatically - no code commit needed!

## Best Practices

1. **Document in env configs** - Keep `config/environments/*.yaml` as reference
2. **Test in dev first** - Change dev group, validate, then update prod
3. **Track changes** - Variable groups have change history in Azure DevOps
4. **Use secrets** - For sensitive values, enable "Keep this value secret"
5. **Access control** - Restrict prod variable group modifications
