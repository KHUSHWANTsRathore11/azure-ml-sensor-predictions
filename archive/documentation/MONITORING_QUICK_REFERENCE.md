# Model Monitoring Quick Reference

## 🎯 Monitoring Capabilities at a Glance

### Azure ML v2 Model Monitoring
```python
# Create monitor for a circuit
from monitoring.setup_model_monitor import create_model_monitor, create_monitor_schedule

monitor = create_model_monitor(
    plant_id="PLANT001",
    circuit_id="CIRCUIT05",
    model_name="plant001-circuit05"
)

schedule = create_monitor_schedule("PLANT001", "CIRCUIT05")
```

**Monitors:**
- ✅ Prediction Drift (Jensen-Shannon distance < 0.15)
- ✅ Data Drift (Wasserstein distance < 0.15)
- ✅ Data Quality (null rate < 5%, type errors < 1%)
- ✅ Model Performance (MAE < 0.25, RMSE < 0.35)

---

### Custom Drift Detection
```python
# Run drift detection
from monitoring.custom_drift_detection import DriftDetector

detector = DriftDetector(ml_client)
result = detector.detect_drift_for_circuit(
    plant_id="PLANT001",
    circuit_id="CIRCUIT05",
    baseline_start_date="2025-11-01",
    baseline_end_date="2025-11-30",
    current_start_date="2025-12-01",
    current_end_date="2025-12-08"
)

if result["summary"]["overall_drift"]:
    print(f"⚠️ Drift detected in: {result['summary']['drifted_features']}")
```

**Tests:**
- Kolmogorov-Smirnov (p-value < 0.05)
- Wasserstein Distance (< 0.15)
- Population Stability Index (< 0.25)

---

### Azure Monitor Queries

#### Check Model Performance
```kql
customMetrics
| where name == "model_accuracy_mae"
| extend plant_id = tostring(customDimensions.plant_id)
| extend circuit_id = tostring(customDimensions.circuit_id)
| where value > 0.25
| summarize count() by plant_id, circuit_id
| order by count_ desc
```

#### Find Drift Events
```kql
customEvents
| where name == "data_drift_detected"
| extend plant_id = tostring(customDimensions.plant_id)
| extend drifted_features = customDimensions.drifted_features
| project timestamp, plant_id, circuit_id, drifted_features
| order by timestamp desc
```

#### Track Prediction Volume
```kql
customMetrics
| where name == "model_predictions"
| summarize total_predictions = sum(value) by bin(timestamp, 1h)
| render timechart
```

---

### Alert Rules

| Alert | Threshold | Severity | Action |
|-------|-----------|----------|--------|
| High MAE | > 0.25 | 2 | Email + SMS |
| Data Drift | > 0.15 | 3 | Email |
| Batch Failure | Any error | 1 | Email + SMS + Teams |
| Multiple Models Degraded | > 15 circuits | 2 | Email + Management |
| Data Quality | Null rate > 5% | 2 | Email Data Eng |

---

### Application Insights Logging

```python
# In scoring script (scoring/score.py)
import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler

logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")))

# Log predictions
logger.info("Prediction completed", extra={
    "custom_dimensions": {
        "plant_id": plant_id,
        "circuit_id": circuit_id,
        "latency_ms": latency_ms,
        "prediction_mean": predictions.mean()
    }
})
```

---

### Daily Monitoring Pipeline

```yaml
# Runs at 2 AM daily
schedules:
  - cron: "0 2 * * *"
    
stages:
  - DataDriftCheck      # Run drift detection
  - PerformanceCheck    # Calculate metrics
  - GenerateReport      # Create HTML report
```

**Output:**
- `drift_results_YYYYMMDD.json`
- `performance_results_YYYYMMDD.json`
- `daily_monitoring_report.html`

---

### Response Workflows

#### Drift Detected
1. Review drift dashboard
2. Check magnitude (PSI, Wasserstein)
3. Investigate root cause
4. Decision:
   - Minor (<0.15): Monitor
   - Moderate (0.15-0.25): Schedule retrain
   - Severe (>0.25): Immediate retrain

#### Performance Degradation
1. Verify alert (multiple metrics)
2. Check for drift
3. Review recent changes
4. Retrain if needed
5. Compare new vs old
6. Deploy if improved

---

### Setup Commands

```bash
# 1. Create monitors for all circuits
python monitoring/setup_all_monitors.py

# 2. Setup Azure Monitor
./monitoring/setup_log_analytics.sh
./monitoring/deploy_alerts.sh

# 3. Enable App Insights
python monitoring/setup_app_insights.py

# 4. Deploy monitoring pipeline
az pipelines create \
  --name "Daily-Model-Monitoring" \
  --yml-path pipelines/monitoring-pipeline.yml

# 5. Test drift detection
python monitoring/run_drift_detection.py
```

---

### Cost Summary

| Component | Monthly Cost |
|-----------|--------------|
| Log Analytics (50GB) | $115 |
| Application Insights | $23 |
| Alert Rules | $2 |
| Monitoring Compute | $60 |
| Storage | $10 |
| **Total** | **$210** |

---

### Key Files

| File | Purpose |
|------|---------|
| `monitoring/setup_model_monitor.py` | Azure ML v2 monitor creation |
| `monitoring/custom_drift_detection.py` | Custom drift detector class |
| `monitoring/run_drift_detection.py` | Daily drift check script |
| `monitoring/setup_log_analytics.sh` | Azure Monitor setup |
| `monitoring/deploy_alerts.sh` | Alert rule deployment |
| `monitoring/kql_queries.kql` | Common KQL queries |
| `pipelines/monitoring-pipeline.yml` | Daily monitoring pipeline |

---

### Dashboard Access

- **Azure Workbook:** Portal → Azure ML → Workspaces → Monitoring
- **Log Analytics:** Portal → Log Analytics → Logs
- **App Insights:** Portal → Application Insights → Search

---

### Thresholds (Configurable)

```python
# monitoring/config.py
THRESHOLDS = {
    "mae": {"warning": 0.15, "critical": 0.25},
    "rmse": {"warning": 0.20, "critical": 0.35},
    "mape": {"warning": 0.10, "critical": 0.20},
    "r2_score": {"minimum": 0.75},
    "drift": {
        "ks_test_pvalue": 0.05,
        "wasserstein_distance": 0.15,
        "psi": 0.25
    },
    "data_quality": {
        "null_rate": 0.05,
        "type_error_rate": 0.01,
        "outlier_rate": 0.05
    }
}
```

---

### Support Contacts

- **MLOps Team:** mlops-team@company.com
- **Data Engineering:** data-eng@company.com
- **On-Call:** 555-0100

---

**Quick Reference Version:** 1.0  
**Last Updated:** December 9, 2025  
**Full Documentation:** [docs/16-model-monitoring-data-drift.md](docs/16-model-monitoring-data-drift.md)
