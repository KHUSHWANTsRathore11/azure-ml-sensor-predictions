# Environment Configuration Guide

This directory contains **reference documentation** for environment-specific settings. 

## ⚠️ Important: Reference Documentation Only

**These YAML files are NOT loaded by pipelines.** They serve as:
- 📋 Documentation of what should be configured in Variable Groups
- 📝 Templates for setting up new environments  
- 🔍 Reference when creating/updating Variable Groups

**Actual configuration** is managed in **Azure DevOps Library → Variable Groups**.

## Files (Reference Only)

- **`dev.yaml`** - Development environment reference
- **`test.yaml`** - Test environment reference  
- **`prod.yaml`** - Production environment reference
- **`README.md`** - This file

## Quick Start

1. **View** the YAML file for your environment (e.g., `dev.yaml`)
2. **Copy** values from `variable_groups` section
3. **Create** Variable Group in Azure DevOps Library
4. **Paste** values into the Variable Group


## Structure

Each configuration file contains:

### Azure Settings
- Subscription, resource group, workspace details
- Compute cluster settings (training & scoring)
- Batch endpoint configuration
- Registry settings (prod only)

### Training Settings
- Retrain schedule
- Data settings (lookback, forecast horizon)
- Model hyperparameters
- Validation settings

### Validation Thresholds
- Model performance metrics (accuracy, MAE, RMSE, R²)
- Business metrics (precision, recall, FPR)

### Deployment Settings
- Auto-deployment rules
- Approval requirements
- Canary/blue-green deployment
- Traffic ramping
- Rollback settings

### Monitoring & Alerts
- Log levels
- Alert channels (Slack, email, PagerDuty)
- Alert thresholds (drift, latency, errors)
- Dashboard links

### Data Retention
- Model retention periods
- Log retention
- Dataset retention

### Security & Compliance
- VNet settings
- Private endpoints
- RBAC roles
- Key vault references

### Cost Management
- Budget alerts
- Auto-shutdown schedules

## Setting Up Variable Groups

### 1. Create Variable Groups in Azure DevOps

Go to **Pipelines → Library → + Variable group**

Create three variable groups:
- `mlops-dev-variables`
- `mlops-test-variables`
- `mlops-prod-variables`

### 2. Add Variables to Each Group

Use the YAML files as a reference for what variables to create.

**Example for `mlops-dev-variables`:**

| Variable Name | Value | Secret? |
|--------------|-------|---------|
| `azureServiceConnection` | `Azure-MLOps-Dev` | No |
| `subscriptionId` | `00000000-0000-...` | No |
| `resourceGroup` | `mlops-dev-rg` | No |
| `workspaceName` | `mlops-dev-workspace` | No |
| `location` | `eastus` | No |
| `trainingCluster` | `dev-training-cluster` | No |
| `trainingVmSize` | `Standard_DS3_v2` | No |
| `trainingMinNodes` | `0` | No |
| `trainingMaxNodes` | `4` | No |
| `scoringCluster` | `dev-scoring-cluster` | No |
| `scoringVmSize` | `Standard_DS2_v2` | No |
| `lstmUnits` | `64` | No |
| `dropoutRate` | `0.2` | No |
| `learningRate` | `0.001` | No |
| `epochs` | `50` | No |
| `batchSize` | `32` | No |
| `minAccuracy` | `0.70` | No |
| `maxMae` | `10.0` | No |
| `maxRmse` | `15.0` | No |
| `minR2Score` | `0.60` | No |
| `autoDeploy` | `true` | No |
| `approvalRequired` | `false` | No |
| `logLevel` | `DEBUG` | No |

Repeat for test and prod with values from `test.yaml` and `prod.yaml`.

### 3. Set Permissions

- **Dev:** Allow all developers
- **Test:** Restrict to QA team + leads
- **Prod:** Restrict to senior engineers only

### 4. Link Secrets from Key Vault (Optional)

For sensitive values, link to Azure Key Vault:

```
Variable: azureServiceConnection
Source: Azure Key Vault
Subscription: [Your subscription]
Key Vault: mlops-keyvault
Secret: service-connection-dev
```

## Usage

### In Pipeline

The configuration is automatically loaded based on the branch:

```yaml
# develop branch → loads mlops-dev-variables
# release/* branches → loads mlops-test-variables
# main branch → loads mlops-prod-variables
```

Variables are available throughout the pipeline:

```yaml
- script: |
    echo "Training on $(workspaceName)"
    echo "Using $(trainingCluster) with $(epochs) epochs"
```

### Updating Configuration

**To update a setting:**

1. Go to Azure DevOps → Pipelines → Library
2. Select the variable group (e.g., `mlops-prod-variables`)
3. Click on the variable to edit
4. Update the value
5. Save

No code commit needed - next pipeline run will use the new value!

## Variable Mapping

The following variables are automatically set in Azure DevOps:

| Variable | Config Path | Example |
|----------|-------------|---------|
| `resourceGroup` | `azure.resource_group` | `mlops-dev-rg` |
| `workspaceName` | `azure.workspace_name` | `mlops-dev-workspace` |
| `location` | `azure.location` | `eastus` |
| `trainingCluster` | `azure.compute.training_cluster` | `dev-training-cluster` |
| `trainingVmSize` | `azure.compute.training_vm_size` | `Standard_DS3_v2` |
| `lookbackDays` | `training.lookback_days` | `90` |
| `forecastHorizon` | `training.forecast_horizon` | `7` |
| `lstmUnits` | `training.hyperparameters.lstm_units` | `64` |
| `minAccuracy` | `validation.min_accuracy` | `0.70` |
| `autoDeploy` | `deployment.auto_deploy` | `true` |
| `logLevel` | `monitoring.log_level` | `DEBUG` |
| `environment` | `environment.name` | `dev` |

## Environment Differences

### Dev Environment

- **Purpose:** Active development, frequent deployments
- **Compute:** Smaller VMs (DS3_v2), auto-scale 0-4 nodes
- **Training:** Daily retraining, relaxed thresholds
- **Validation:** min_accuracy=0.70, max_mae=10.0
- **Deployment:** Auto-deploy, no approvals
- **Monitoring:** DEBUG logs, Slack alerts
- **Retention:** 30 days models, 14 days logs

### Test Environment

- **Purpose:** QA validation, pre-production testing
- **Compute:** Medium VMs (DS4_v2), auto-scale 0-6 nodes
- **Training:** Weekly retraining, stricter thresholds
- **Validation:** min_accuracy=0.80, max_mae=7.0
- **Deployment:** Manual approval, canary (50%)
- **Monitoring:** INFO logs, email + Slack alerts
- **Retention:** 90 days models, 30 days logs

### Production Environment

- **Purpose:** Live production serving
- **Compute:** Large VMs (DS5_v2), auto-scale 1-10 nodes (1 warm)
- **Training:** Weekly retraining, strict thresholds
- **Validation:** min_accuracy=0.85, max_mae=5.0, cross-validation
- **Deployment:** Manual approval (2 reviewers), blue-green with traffic ramp
- **Monitoring:** WARNING logs, PagerDuty alerts, Application Insights
- **Retention:** 365 days models, 90 days logs
- **Security:** VNet, private endpoints, managed identity
- **HA:** 2 warm scoring nodes, geo-redundant backup

## Customization

### Adding New Settings

1. Add the setting to all three environment files:

```yaml
# config/environments/dev.yaml
my_new_setting:
  key: "value"
```

2. Update the variable mapping in `scripts/load_environment_config.py`:

```python
variables = {
    # ... existing variables ...
    'myNewKey': config['my_new_setting']['key'],
}
```

3. Use in pipeline:

```yaml
- script: |
    echo "My setting: $(myNewKey)"
```

### Overriding for Specific Circuits

If you need circuit-specific overrides, add them to `config/circuits.yaml`:

```yaml
circuits:
  - plant_id: PLANT001
    circuit_id: CIRCUIT01
    override_settings:
      training:
        epochs: 200  # Override for this circuit
```

## Best Practices

1. **Never commit secrets** - Use Azure Key Vault references
2. **Keep configs synchronized** - Maintain same structure across environments
3. **Document changes** - Add comments for non-obvious settings
4. **Test in dev first** - Validate config changes in dev before promoting
5. **Use variable groups** - For service connections and sensitive data
6. **Version control** - Track all config changes in git
7. **Review prod changes** - Require PR approval for prod.yaml changes

## Troubleshooting

### Config not loading

```bash
# Check branch detection
git rev-parse --abbrev-ref HEAD

# Verify config file exists
ls -la config/environments/

# Test config loading
python scripts/load_environment_config.py --print
```

### Wrong environment selected

```bash
# Force specific environment
python scripts/load_environment_config.py --environment prod --print
```

### Variable not set in pipeline

```bash
# Check variable mapping
python scripts/load_environment_config.py --environment dev --set-pipeline-vars

# Verify variable in Azure DevOps
# Pipeline → Edit → Variables → Check if variable exists
```

## Related Files

- `.azuredevops/build-pipeline.yml` - Uses environment configs
- `.azuredevops/release-pipeline.yml` - Uses prod/test configs
- `scripts/load_environment_config.py` - Config loader script
- `docs/BRANCHING_STRATEGY.md` - Branch-to-environment mapping
