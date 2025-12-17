# MLOps Setup Guide

Complete guide for setting up the Azure ML MLOps pipeline infrastructure.

## Quick Start

1. **Azure DevOps Variable Groups** - Configure 6 variable groups
2. **Environment Configuration** - Set up Dev/Test/Prod environments
3. **Approval Environments** - Configure approval gates
4. **Service Connections** - Connect Azure DevOps to Azure ML

---

## Variable Groups

All pipeline configuration is managed via **Azure DevOps Variable Groups** (not in code).

### Required Variable Groups (6)

| Group | Purpose | Used By |
|-------|---------|---------|
| `mlops-dev-variables` | Dev workspace connection | Training, Promotion |
| `mlops-test-variables` | Test workspace connection | Test Deployment |
| `mlops-prod-variables` | Prod workspace connection | Prod Deployment |
| `mlops-registry-variables` | Registry connection & propagation | All pipelines |
| `mlops-pipeline-settings` | Pipeline execution settings | Training, PR Validation |
| `mlops-shared-variables` | Shared resources (PR validation) | PR Validation |

### 1. mlops-dev-variables

Dev workspace Azure ML connection:

```yaml
azureServiceConnection: "Azure-MLOps-Dev"
subscriptionId: "12345678-1234-..."
resourceGroup: "mlops-dev-rg"
workspaceName: "mlops-dev-workspace"
location: "eastus"
```

### 2. mlops-test-variables

Test workspace connection:

```yaml
azureServiceConnection: "Azure-MLOps-Test"
subscriptionId: "12345678-1234-..."
resourceGroup: "mlops-test-rg"
workspaceName: "mlops-test-workspace"
location: "eastus"
testScoringCluster: "test-scoring-cluster"
```

### 3. mlops-prod-variables

Prod workspace connection:

```yaml
azureServiceConnection: "Azure-MLOps-Prod"
subscriptionId: "12345678-1234-..."
resourceGroup: "mlops-prod-rg"
workspaceName: "mlops-prod-workspace"
location: "eastus"
prodScoringCluster: "prod-scoring-cluster"
```

### 4. mlops-registry-variables

Registry connection and model propagation settings:

```yaml
registryName: "mlops-central-registry"
registryResourceGroup: "mlops-registry-rg"

# Model propagation (exponential backoff)
registryPropagationMaxWaitSeconds: 120
registryPropagationInitialDelaySeconds: 2
registryPropagationMaxDelaySeconds: 30
```

### 5. mlops-pipeline-settings

Pipeline execution settings:

```yaml
# Python & Runtime
pythonVersion: "3.9"
longRunningJobNotificationIntervalHours: 4
mlEngineersEmail: "ml-team@company.com"

# Monitoring
monitoringMaxWaitHours: 3
monitoringPollIntervalSeconds: 30
monitoringLogLevel: "DEBUG"

# Validation
validationMinAccuracy: 0.70
validationMaxMae: 10.0
validationMaxRmse: 15.0

# Retention
retentionModelsDays: 30
retentionLogsDays: 14
```

### 6. mlops-shared-variables

Shared resources for PR validation:

```yaml
azureServiceConnection: "Azure-MLOps-Shared"
storageAccountName: "mlopsstorage"
dataContainer: "validation-data"

# Workspace references (for validation checks)
mlopsDevWorkspace: "mlops-dev-workspace"
mlopsDevResourceGroup: "mlops-dev-rg"
mlopsTestWorkspace: "mlops-test-workspace"
mlopsTestResourceGroup: "mlops-test-rg"
mlopsProdWorkspace: "mlops-prod-workspace"
mlopsProdResourceGroup: "mlops-prod-rg"
```

---

## Environment Configuration

### Environment Roles

| Environment | Training | Deployment | Branch | Variable Group |
|-------------|----------|------------|--------|----------------|
| **Dev** | ✅ Yes | ✅ Yes | `develop` | `mlops-dev-variables` |
| **Test** | ❌ No | ✅ Yes | `release/*` | `mlops-test-variables` |
| **Prod** | ❌ No | ✅ Yes | `main` | `mlops-prod-variables` |

### Dev Environment

**Purpose:** Active development and model training

**Configuration:**
```yaml
# Compute
training_cluster: "Standard_DS3_v2" (0-4 nodes)
scoring_cluster: "Standard_DS2_v2" (0-2 nodes)

# Training Schedule
frequency: "Daily at 2 AM"
lookback_days: 90
forecast_horizon: 7

# Validation (relaxed)
min_accuracy: 0.70
max_mae: 10.0
max_rmse: 15.0

# Deployment
auto_deploy: Yes
approval_required: No
traffic: 100%

# Monitoring
log_level: DEBUG
alerts: Disabled

# Retention
models: 30 days
logs: 14 days
datasets: 60 days
```

### Test Environment

**Purpose:** QA validation and pre-production testing

**Configuration:**
```yaml
# Compute
scoring_cluster: "Standard_DS3_v2" (0-4 nodes)

# Deployment
auto_deploy: No
approval_required: Yes
canary_deployment: Yes (50% traffic)

# Validation (stricter)
min_accuracy: 0.80
max_mae: 7.0
max_rmse: 10.0

# Monitoring
log_level: INFO
alerts: Enabled (email + Slack)

# Alert Thresholds
model_drift: 0.15
data_drift: 0.20
prediction_latency_ms: 1000
error_rate_percent: 5

# Retention
models: 90 days
logs: 30 days
datasets: 180 days
```

### Prod Environment

**Purpose:** Production model serving

**Configuration:**
```yaml
# Compute
scoring_cluster: "Standard_DS4_v2" (2-8 nodes, 2 warm for HA)

# Deployment
auto_deploy: No (never auto-deploy to prod)
approval_required: Yes (2 approvers)
blue_green_deployment: Yes
traffic_ramp: 0% → 10% → 25% → 50% → 100%

# Validation (strictest)
min_accuracy: 0.85
max_mae: 5.0
max_rmse: 7.0
min_precision: 0.85
min_recall: 0.80

# Monitoring
log_level: WARNING
alerts: Enabled (PagerDuty + email + Slack)
application_insights: Enabled (10% sampling)

# Alert Thresholds (strict)
model_drift: 0.10
data_drift: 0.15
prediction_latency_ms: 500
error_rate_percent: 2
endpoint_availability_percent: 99.5

# Auto-Rollback
enabled: Yes
error_threshold: 5%
latency_threshold: 2000ms

# Retention
models: 365 days
logs: 90 days
datasets: 730 days
predictions: 180 days

# Backup
frequency: Daily
retention: 30 days
geo_redundant: Yes

# Security
vnet: Enabled
private_endpoints: Yes
managed_identity: Yes
key_vault: "mlops-prod-keyvault"
```

---

## Approval Environments

Configure in **Azure DevOps → Pipelines → Environments**:

| Environment | Used By | Approvers |
|-------------|---------|-----------|
| `registry-promotion` | Model promotion to registry | ML team leads |
| `test-deployment` | Test deployment | QA team |
| `prod-deployment` | Prod deployment | Senior engineers + platform lead |

**Setup Steps:**
1. Go to Azure DevOps → Pipelines → Environments
2. Create environment
3. Add approvers via "Approvals and checks"
4. Configure approval timeout and instructions

---

## Setup Instructions

### 1. Create Variable Groups

```bash
# Azure DevOps → Pipelines → Library → + Variable group
```

Create all 6 variable groups with exact names and add variables from tables above.

### 2. Set Permissions

**Recommended:**
- Dev groups: All developers (read/write)
- Test groups: QA team + leads (read), leads only (write)
- Prod groups: Senior engineers only (read/write)
- Registry/Shared: Platform team only (write)

### 3. Create Approval Environments

```bash
# Azure DevOps → Pipelines → Environments → New environment
```

Create 3 environments and configure approvers.

### 4. Create Service Connections

```bash
# Azure DevOps → Project Settings → Service connections → New service connection
```

Create Azure Resource Manager connections for Dev, Test, Prod, and Shared.

### 5. Link to Key Vault (Optional)

For secrets:
1. Variable → ⋯ → Link to Azure Key Vault
2. Select subscription and Key Vault
3. Choose secret name

---

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

---

## Updating Configuration

**To change a setting:**

1. Azure DevOps → Pipelines → Library
2. Select Variable Group
3. Click variable → Edit
4. Update value → Save

**Next pipeline run uses new value** - no code commit needed!

---

## Troubleshooting

### Variable not found

- Check Variable Group name matches exactly
- Check variable name (case-sensitive)
- Verify pipeline YAML includes `- group:` reference
- Check build service has permissions

### Wrong value being used

- Verify correct Variable Group for environment
- Check for hardcoded values in YAML
- Confirm Variable Group change was saved
- Ensure pipeline run is after the change

### Service connection not working

- Verify service connection exists
- Check name matches `azureServiceConnection` variable
- Verify permissions to subscription/resource group
- Check service connection is not expired
