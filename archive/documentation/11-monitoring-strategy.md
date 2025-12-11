# Monitoring Strategy

[← Back to README](../README.md)

## Overview

Comprehensive monitoring strategy for the multi-model sensor prediction architecture, covering model performance, data drift, infrastructure health, and operational metrics.

## Monitoring Components

### Azure Monitor
- Log Analytics workspace
- Alert rules per circuit
- Action groups for notifications

### Application Insights
- 3 instances (Dev, Test, Prod workspaces)
- 5GB free tier per month per workspace
- Batch job execution logs

### Metrics Tracked

| Metric Category | Frequency | Dimensions |
|----------------|-----------|------------|
| Model Performance | Monthly | plant_id, circuit_id |
| Data Drift | Quarterly | plant_id, circuit_id |
| Batch Job Status | Real-time | plant_id, circuit_id, endpoint_name |
| Compute Costs | Monthly | workspace, compute_cluster |
| Training Failures | Real-time | plant_id, circuit_id |

## Model Performance Monitoring (Per Circuit)

### Monthly Performance Check

**Metrics Calculated:**
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- MAPE (Mean Absolute Percentage Error)
- R² Score

**Alert Thresholds (Configurable per Circuit):**

```python
alert_thresholds = {
    "mae": {"warning": 0.15, "critical": 0.25},
    "rmse": {"warning": 0.20, "critical": 0.35},
    "mape": {"warning": 0.10, "critical": 0.20}
}
```

### Python Script

```python
# monitoring/check_model_performance.sh
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def check_circuit_performance(plant_id, circuit_id):
    """Check model performance for specific circuit."""
    predictions_path = f"/predictions/{plant_id}/{circuit_id}/"
    
    # Load predictions and actuals
    predictions = pd.read_parquet(predictions_path)
    
    metrics = {
        "plant_id": plant_id,
        "circuit_id": circuit_id,
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": sqrt(mean_squared_error(y_true, y_pred)),
        "mape": mean_absolute_percentage_error(y_true, y_pred),
        "r2_score": r2_score(y_true, y_pred),
        "checked_at": datetime.now().isoformat()
    }
    
    # Check thresholds
    if metrics["mae"] > 0.25:
        send_alert(f"Plant {plant_id} Circuit {circuit_id}: MAE critically degraded")
    
    return metrics
```

## Data Drift Detection (Per Circuit)

### Quarterly Drift Check

**Process:**
1. Compare baseline dataset (from training) with current production data
2. Calculate drift magnitude per feature
3. Alert if drift exceeds thresholds

**Drift Thresholds:**

```python
drift_thresholds = {
    "low": 0.05,      # <5% drift: No action
    "medium": 0.15,   # 5-15% drift: Warning
    "high": 0.25      # >25% drift: Critical + suggest retrain
}
```

**Azure ML Data Drift Monitor:**

```python
from azureml.datadrift import DataDriftDetector

drift_detector = DataDriftDetector.create(
    workspace=ws,
    name=f"drift-detector-{plant_id}-{circuit_id}",
    baseline_data_set=get_baseline_dataset(plant_id, circuit_id),
    target_data_set=get_current_dataset(plant_id, circuit_id),
    feature_list=["temperature", "pressure", "vibration"],
    frequency="Quarter"
)
```

## Alert Rules Configuration

### Azure Monitor Alert Rules

```json
{
  "alertRules": [
    {
      "name": "Model Performance Degradation",
      "condition": "mae > 0.25 OR rmse > 0.35",
      "severity": "2",
      "frequency": "Monthly",
      "actionGroup": "ml-ops-team",
      "dimensions": ["plant_id", "circuit_id"]
    },
    {
      "name": "Data Drift Detected",
      "condition": "drift_magnitude > 0.25",
      "severity": "3",
      "frequency": "Quarterly",
      "actionGroup": "ml-ops-team",
      "dimensions": ["plant_id", "circuit_id"]
    },
    {
      "name": "Batch Job Failure",
      "condition": "batch_endpoint_status == 'Failed'",
      "severity": "1",
      "frequency": "Real-time",
      "actionGroup": "ml-ops-team",
      "dimensions": ["plant_id", "circuit_id", "endpoint_name"]
    },
    {
      "name": "Compute Cluster Cost Alert",
      "condition": "monthly_compute_cost > $1000",
      "severity": "3",
      "frequency": "Monthly",
      "actionGroup": "finance-team"
    },
    {
      "name": "High Training Failure Rate",
      "condition": "training_failure_count > 5 in last 24 hours",
      "severity": "2",
      "frequency": "Real-time",
      "actionGroup": "ml-ops-team"
    }
  ]
}
```

### Action Groups

```json
{
  "actionGroups": [
    {
      "name": "ml-ops-team",
      "emailReceivers": [
        "mlops-team@company.com"
      ],
      "smsReceivers": [],
      "webhookReceivers": []
    },
    {
      "name": "finance-team",
      "emailReceivers": [
        "finance@company.com"
      ]
    }
  ]
}
```

## Monitoring Pipeline (Scheduled)

### Monthly Performance Monitoring

```yaml
# azure-pipelines-monitoring.yml
schedules:
  - cron: "0 6 1 * *"
    displayName: 'Monthly Performance Check'
    branches:
      include:
        - main

stages:
  - stage: ModelMonitoring
    jobs:
      - job: CheckPerformance
        strategy:
          maxParallel: 10
          matrix: $[ scripts/load_all_circuits.py ]
        steps:
          - task: AzureCLI@2
            inputs:
              scriptPath: 'monitoring/check_model_performance.sh'
              arguments: '--plant-id $(plant_id) --circuit-id $(circuit_id)'
```

### Quarterly Drift Monitoring

```yaml
schedules:
  - cron: "0 6 1 */3 *"
    displayName: 'Quarterly Drift Check'
    branches:
      include:
        - main

stages:
  - stage: DriftMonitoring
    jobs:
      - job: CheckDrift
        strategy:
          maxParallel: 10
          matrix: $[ scripts/load_all_circuits.py ]
        steps:
          - task: AzureCLI@2
            inputs:
              scriptPath: 'monitoring/check_data_drift.sh'
              arguments: '--plant-id $(plant_id) --circuit-id $(circuit_id)'
```

## Infrastructure Monitoring

### Compute Cluster Metrics

- **CPU utilization** (target: 60-80%)
- **Memory utilization** (target: <85%)
- **Node count** (auto-scale 0-4)
- **Queue depth** (training jobs waiting)

### Batch Endpoint Metrics

- **Invocation count** (75-200 daily)
- **Success rate** (target: >99%)
- **Execution time** (track per circuit)
- **Error rate** (alert if >1%)

### Storage Metrics

- **ADLS Gen2 capacity** (track growth)
- **Transaction count**
- **Egress** (data transfer out)
- **Hot vs Cool storage split**

## Cost Monitoring

### Monthly Cost Breakdown

| Resource | Budget | Alert Threshold |
|----------|--------|----------------|
| Dev Workspace | $400 | $450 |
| Test Workspace | $200 | $225 |
| Prod Workspace | $700 | $800 |
| Shared Infrastructure | $183 | $200 |
| **Total** | **$1,483** | **$1,675** |

### Cost Optimization Alerts

- Alert when compute costs exceed budget by 10%
- Weekly cost report to engineering managers
- Monthly cost breakdown by circuit (if possible)

## Related Documents

- [16-model-monitoring-data-drift.md](16-model-monitoring-data-drift.md) - **Comprehensive Azure ML v2 monitoring & drift detection**
- [02-data-architecture.md](02-data-architecture.md) - Data monitoring
- [12-operational-runbooks.md](12-operational-runbooks.md) - Response procedures

---

**Document Version:** 1.0  
**Last Updated:** December 9, 2025
