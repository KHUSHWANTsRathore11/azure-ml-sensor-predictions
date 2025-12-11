# Model Monitoring & Data Drift Architecture

[← Back to README](../README.md)

## Overview

Comprehensive architecture for continuous model monitoring and data drift detection using **Azure ML v2 SDK**, **Azure Monitor**, and **Application Insights**. This document covers production-grade monitoring for 75-200 time series forecasting models.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Azure ML v2 Model Monitoring](#azure-ml-v2-model-monitoring)
3. [Data Drift Detection](#data-drift-detection)
4. [Azure Monitor Integration](#azure-monitor-integration)
5. [Application Insights Configuration](#application-insights-configuration)
6. [Monitoring Pipelines](#monitoring-pipelines)
7. [Alerting Strategy](#alerting-strategy)
8. [Dashboards & Visualization](#dashboards--visualization)
9. [Response Workflows](#response-workflows)
10. [Implementation Code](#implementation-code)

---

## Architecture Overview

### Monitoring Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    Monitoring Architecture                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │ Batch Endpoints │───→│ Prediction Logs  │                   │
│  │  (75-200 models)│    │ (App Insights)   │                   │
│  └─────────────────┘    └──────────────────┘                   │
│           │                       │                              │
│           ├───────────────────────┼──────────────────┐          │
│           ↓                       ↓                  ↓          │
│  ┌─────────────────┐    ┌──────────────────┐  ┌──────────────┐│
│  │ Azure ML v2     │    │ Azure Monitor    │  │ Log Analytics││
│  │ Model Monitor   │    │ Metrics          │  │ Workspace    ││
│  │ - Performance   │    │ - Alerts         │  │              ││
│  │ - Data Drift    │    │ - Action Groups  │  │              ││
│  │ - Data Quality  │    │ - Workbooks      │  │              ││
│  └─────────────────┘    └──────────────────┘  └──────────────┘│
│           │                       │                  │          │
│           └───────────────────────┴──────────────────┘          │
│                              ↓                                   │
│                   ┌──────────────────────┐                      │
│                   │  Notification Layer   │                      │
│                   │  - Email              │                      │
│                   │  - Teams/Slack        │                      │
│                   │  - Incident Tracking  │                      │
│                   └──────────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Model Monitor** | Track prediction quality, drift | Azure ML v2 SDK |
| **Data Collector** | Capture predictions & actuals | Custom logging |
| **Drift Detector** | Feature distribution analysis | Azure ML Data Drift |
| **Performance Tracker** | Model accuracy metrics | Custom metrics |
| **Alert Manager** | Threshold-based notifications | Azure Monitor |
| **Dashboard** | Visual monitoring | Azure Workbooks |

---

## Azure ML v2 Model Monitoring

### Model Monitor Configuration

Azure ML v2 provides built-in model monitoring capabilities for production deployments.

#### 1. Enable Model Monitoring

```python
# monitoring/setup_model_monitor.py
from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    ModelMonitor,
    MonitoringTarget,
    MonitorSchedule,
    AlertNotification
)
from azure.identity import DefaultAzureCredential

# Initialize ML Client
credential = DefaultAzureCredential()
ml_client = MLClient(
    credential=credential,
    subscription_id="<subscription-id>",
    resource_group_name="rg-mlops-prod",
    workspace_name="mlw-prod"
)

def create_model_monitor(plant_id: str, circuit_id: str, model_name: str):
    """
    Create Azure ML v2 Model Monitor for a specific circuit.
    
    Monitors:
    - Prediction drift
    - Data drift
    - Data quality
    - Model performance
    """
    
    monitor_name = f"monitor-{plant_id}-{circuit_id}"
    
    # Define monitoring target (batch endpoint deployment)
    monitoring_target = MonitoringTarget(
        endpoint_deployment_id=f"/subscriptions/<sub-id>/resourceGroups/rg-mlops-prod/providers/Microsoft.MachineLearningServices/workspaces/mlw-prod/batchEndpoints/batch-{plant_id}/deployments/{circuit_id}",
        model_id=f"azureml://registries/shared-registry/models/{model_name}"
    )
    
    # Create model monitor
    model_monitor = ModelMonitor(
        name=monitor_name,
        monitoring_target=monitoring_target,
        compute="cpu-cluster",
        
        # Monitoring signals
        monitoring_signals={
            # Prediction drift signal
            "prediction_drift": {
                "type": "PredictionDrift",
                "baseline_dataset": f"azureml://datastores/workspaceblobstore/paths/baseline/{plant_id}/{circuit_id}/",
                "target_dataset": f"azureml://datastores/workspaceblobstore/paths/production/{plant_id}/{circuit_id}/",
                "features": ["predicted_value"],
                "metric_thresholds": {
                    "numerical": {
                        "jensen_shannon_distance": 0.15
                    }
                }
            },
            
            # Data drift signal
            "data_drift": {
                "type": "DataDrift",
                "baseline_dataset": f"azureml://datastores/workspaceblobstore/paths/baseline/{plant_id}/{circuit_id}/",
                "target_dataset": f"azureml://datastores/workspaceblobstore/paths/production/{plant_id}/{circuit_id}/",
                "features": [
                    "temperature", "pressure", "vibration",
                    "current", "voltage", "flow_rate"
                ],
                "metric_thresholds": {
                    "numerical": {
                        "jensen_shannon_distance": 0.15,
                        "normalized_wasserstein_distance": 0.15,
                        "two_sample_kolmogorov_smirnov_test": 0.15
                    }
                }
            },
            
            # Data quality signal
            "data_quality": {
                "type": "DataQuality",
                "target_dataset": f"azureml://datastores/workspaceblobstore/paths/production/{plant_id}/{circuit_id}/",
                "features": ["all"],
                "metric_thresholds": {
                    "null_value_rate": 0.05,      # Max 5% nulls
                    "data_type_error_rate": 0.01,  # Max 1% type errors
                    "out_of_bounds_rate": 0.05     # Max 5% out of range
                }
            },
            
            # Model performance signal (requires ground truth)
            "model_performance": {
                "type": "ModelPerformance",
                "production_dataset": f"azureml://datastores/workspaceblobstore/paths/production/{plant_id}/{circuit_id}/",
                "model_type": "regression",
                "metric_thresholds": {
                    "mean_absolute_error": 0.25,
                    "root_mean_squared_error": 0.35,
                    "r2_score": 0.75  # Minimum R²
                }
            }
        },
        
        # Alert configuration
        alert_notification=AlertNotification(
            emails=["mlops-team@company.com"],
            custom_properties={
                "plant_id": plant_id,
                "circuit_id": circuit_id,
                "severity": "high"
            }
        )
    )
    
    # Create monitor
    created_monitor = ml_client.model_monitors.begin_create_or_update(
        model_monitor
    ).result()
    
    print(f"✅ Model monitor created: {monitor_name}")
    return created_monitor


def create_monitor_schedule(plant_id: str, circuit_id: str):
    """
    Create monitoring schedule.
    
    - Data drift: Daily
    - Performance: Weekly (when actuals available)
    - Data quality: Daily
    """
    
    monitor_name = f"monitor-{plant_id}-{circuit_id}"
    
    # Daily monitoring schedule
    schedule = MonitorSchedule(
        name=f"schedule-{monitor_name}",
        monitor_name=monitor_name,
        trigger={
            "type": "cron",
            "expression": "0 2 * * *",  # Daily at 2 AM
            "start_time": None,
            "end_time": None,
            "time_zone": "UTC"
        }
    )
    
    created_schedule = ml_client.schedules.begin_create_or_update(
        schedule
    ).result()
    
    print(f"✅ Monitor schedule created for {monitor_name}")
    return created_schedule
```

#### 2. Bulk Monitor Setup for All Circuits

```python
# monitoring/setup_all_monitors.py
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed

def load_circuit_config():
    """Load circuit configuration."""
    with open("config/circuits.yaml", "r") as f:
        return yaml.safe_load(f)

def setup_monitor_for_circuit(circuit_config):
    """Setup monitor for single circuit."""
    plant_id = circuit_config["plant_id"]
    circuit_id = circuit_config["circuit_id"]
    model_name = circuit_config["model_name"]
    
    try:
        # Create monitor
        monitor = create_model_monitor(plant_id, circuit_id, model_name)
        
        # Create schedule
        schedule = create_monitor_schedule(plant_id, circuit_id)
        
        return {
            "plant_id": plant_id,
            "circuit_id": circuit_id,
            "status": "success",
            "monitor": monitor.name
        }
    except Exception as e:
        return {
            "plant_id": plant_id,
            "circuit_id": circuit_id,
            "status": "failed",
            "error": str(e)
        }

def main():
    """Setup monitors for all circuits in parallel."""
    config = load_circuit_config()
    circuits = config["circuits"]
    
    print(f"Setting up monitors for {len(circuits)} circuits...")
    
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_circuit = {
            executor.submit(setup_monitor_for_circuit, circuit): circuit
            for circuit in circuits
        }
        
        for future in as_completed(future_to_circuit):
            result = future.result()
            results.append(result)
            
            if result["status"] == "success":
                print(f"✅ {result['plant_id']}/{result['circuit_id']}")
            else:
                print(f"❌ {result['plant_id']}/{result['circuit_id']}: {result['error']}")
    
    # Summary
    successful = sum(1 for r in results if r["status"] == "success")
    print(f"\n📊 Summary: {successful}/{len(circuits)} monitors created successfully")

if __name__ == "__main__":
    main()
```

---

## Data Drift Detection

### Drift Detection Strategy

| Drift Type | Method | Frequency | Threshold |
|------------|--------|-----------|-----------|
| **Feature Drift** | Jensen-Shannon Distance | Daily | 0.15 |
| **Prediction Drift** | Wasserstein Distance | Daily | 0.15 |
| **Concept Drift** | Model Performance | Weekly | MAE > 0.25 |
| **Data Quality Drift** | Null/Outlier Rate | Daily | 5% |

### Custom Drift Detection

For more control, implement custom drift detection:

```python
# monitoring/custom_drift_detection.py
import pandas as pd
import numpy as np
from scipy.stats import ks_2samp, wasserstein_distance
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

class DriftDetector:
    """
    Custom drift detector for time series features.
    
    Uses multiple statistical tests:
    - Kolmogorov-Smirnov test
    - Wasserstein distance
    - Population Stability Index (PSI)
    """
    
    def __init__(self, ml_client: MLClient):
        self.ml_client = ml_client
        self.drift_thresholds = {
            "ks_test_pvalue": 0.05,           # p-value < 0.05 = drift
            "wasserstein_distance": 0.15,     # Distance > 0.15 = drift
            "psi": 0.25                        # PSI > 0.25 = drift
        }
    
    def calculate_psi(self, baseline: np.ndarray, current: np.ndarray, bins=10):
        """
        Calculate Population Stability Index (PSI).
        
        PSI = Σ (actual% - expected%) * ln(actual% / expected%)
        
        Interpretation:
        - PSI < 0.1: No significant change
        - 0.1 < PSI < 0.25: Some change
        - PSI > 0.25: Significant drift
        """
        # Create bins from baseline
        breakpoints = np.percentile(baseline, np.linspace(0, 100, bins + 1))
        breakpoints[-1] = breakpoints[-1] + 0.001  # Ensure last value included
        
        # Calculate distributions
        baseline_dist = np.histogram(baseline, bins=breakpoints)[0] / len(baseline)
        current_dist = np.histogram(current, bins=breakpoints)[0] / len(current)
        
        # Avoid division by zero
        baseline_dist = np.where(baseline_dist == 0, 0.0001, baseline_dist)
        current_dist = np.where(current_dist == 0, 0.0001, current_dist)
        
        # Calculate PSI
        psi = np.sum((current_dist - baseline_dist) * np.log(current_dist / baseline_dist))
        
        return psi
    
    def detect_drift_for_feature(
        self,
        feature_name: str,
        baseline_data: pd.Series,
        current_data: pd.Series
    ):
        """
        Detect drift for a single feature using multiple tests.
        """
        results = {
            "feature": feature_name,
            "tests": {}
        }
        
        # 1. Kolmogorov-Smirnov test
        ks_stat, ks_pvalue = ks_2samp(baseline_data, current_data)
        results["tests"]["ks_test"] = {
            "statistic": float(ks_stat),
            "pvalue": float(ks_pvalue),
            "drift_detected": ks_pvalue < self.drift_thresholds["ks_test_pvalue"]
        }
        
        # 2. Wasserstein distance
        wasserstein_dist = wasserstein_distance(baseline_data, current_data)
        results["tests"]["wasserstein"] = {
            "distance": float(wasserstein_dist),
            "drift_detected": wasserstein_dist > self.drift_thresholds["wasserstein_distance"]
        }
        
        # 3. Population Stability Index (PSI)
        psi = self.calculate_psi(baseline_data.values, current_data.values)
        results["tests"]["psi"] = {
            "value": float(psi),
            "drift_detected": psi > self.drift_thresholds["psi"]
        }
        
        # Overall drift decision (if any test detects drift)
        results["drift_detected"] = any(
            test["drift_detected"] for test in results["tests"].values()
        )
        
        return results
    
    def detect_drift_for_circuit(
        self,
        plant_id: str,
        circuit_id: str,
        baseline_start_date: str,
        baseline_end_date: str,
        current_start_date: str,
        current_end_date: str
    ):
        """
        Detect drift for all features of a specific circuit.
        """
        # Load baseline data
        baseline_df = self.load_data(
            plant_id, circuit_id, baseline_start_date, baseline_end_date
        )
        
        # Load current data
        current_df = self.load_data(
            plant_id, circuit_id, current_start_date, current_end_date
        )
        
        # Feature columns
        feature_columns = [
            "temperature", "pressure", "vibration",
            "current", "voltage", "flow_rate"
        ]
        
        drift_results = {
            "plant_id": plant_id,
            "circuit_id": circuit_id,
            "baseline_period": f"{baseline_start_date} to {baseline_end_date}",
            "current_period": f"{current_start_date} to {current_end_date}",
            "features": []
        }
        
        # Check each feature
        for feature in feature_columns:
            if feature in baseline_df.columns and feature in current_df.columns:
                feature_result = self.detect_drift_for_feature(
                    feature,
                    baseline_df[feature],
                    current_df[feature]
                )
                drift_results["features"].append(feature_result)
        
        # Summary
        drifted_features = [
            f["feature"] for f in drift_results["features"]
            if f["drift_detected"]
        ]
        
        drift_results["summary"] = {
            "total_features": len(feature_columns),
            "drifted_features_count": len(drifted_features),
            "drifted_features": drifted_features,
            "overall_drift": len(drifted_features) > 0
        }
        
        return drift_results
    
    def load_data(
        self,
        plant_id: str,
        circuit_id: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """Load data from Delta Lake."""
        from pyspark.sql import SparkSession
        
        spark = SparkSession.builder.getOrCreate()
        
        df = spark.read.format("delta").load(
            f"abfss://bronze@datalake.dfs.core.windows.net/sensors/"
        ).filter(
            f"plant_id = '{plant_id}' AND circuit_id = '{circuit_id}' " +
            f"AND date >= '{start_date}' AND date <= '{end_date}'"
        ).toPandas()
        
        return df
```

### Scheduled Drift Detection

```python
# monitoring/run_drift_detection.py
from datetime import datetime, timedelta
import json

def run_daily_drift_check():
    """
    Run drift detection for all circuits.
    Compare last 7 days vs previous 30 days.
    """
    ml_client = MLClient(
        DefaultAzureCredential(),
        subscription_id="<sub-id>",
        resource_group_name="rg-mlops-prod",
        workspace_name="mlw-prod"
    )
    
    detector = DriftDetector(ml_client)
    
    # Date ranges
    today = datetime.now()
    current_end = today.strftime("%Y-%m-%d")
    current_start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    baseline_end = (today - timedelta(days=8)).strftime("%Y-%m-%d")
    baseline_start = (today - timedelta(days=38)).strftime("%Y-%m-%d")
    
    # Load circuits
    with open("config/circuits.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    all_results = []
    
    for circuit in config["circuits"]:
        plant_id = circuit["plant_id"]
        circuit_id = circuit["circuit_id"]
        
        print(f"Checking drift for {plant_id}/{circuit_id}...")
        
        result = detector.detect_drift_for_circuit(
            plant_id=plant_id,
            circuit_id=circuit_id,
            baseline_start_date=baseline_start,
            baseline_end_date=baseline_end,
            current_start_date=current_start,
            current_end_date=current_end
        )
        
        all_results.append(result)
        
        # Send alert if drift detected
        if result["summary"]["overall_drift"]:
            send_drift_alert(result)
    
    # Save results
    with open(f"drift_results_{today.strftime('%Y%m%d')}.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"✅ Drift detection complete. Checked {len(all_results)} circuits.")

def send_drift_alert(drift_result):
    """Send alert when drift is detected."""
    from azure.monitor.query import LogsQueryClient
    
    plant_id = drift_result["plant_id"]
    circuit_id = drift_result["circuit_id"]
    drifted_features = drift_result["summary"]["drifted_features"]
    
    message = f"""
    ⚠️ DATA DRIFT DETECTED
    
    Plant: {plant_id}
    Circuit: {circuit_id}
    
    Drifted Features ({len(drifted_features)}):
    {', '.join(drifted_features)}
    
    Action Required:
    1. Review feature distributions
    2. Investigate root cause
    3. Consider model retraining
    
    Dashboard: https://ml.azure.com/monitoring/{plant_id}-{circuit_id}
    """
    
    # Send to Azure Monitor (custom event)
    # Implementation depends on your notification setup
    print(message)
```

---

## Azure Monitor Integration

### Log Analytics Workspace Setup

```bash
# monitoring/setup_log_analytics.sh

# Create Log Analytics Workspace
az monitor log-analytics workspace create \
  --resource-group rg-mlops-prod \
  --workspace-name law-mlops-monitoring \
  --location eastus \
  --retention-time 90

# Get workspace ID
WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --resource-group rg-mlops-prod \
  --workspace-name law-mlops-monitoring \
  --query customerId -o tsv)

echo "Log Analytics Workspace ID: $WORKSPACE_ID"

# Link Azure ML workspace to Log Analytics
az ml workspace update \
  --resource-group rg-mlops-prod \
  --name mlw-prod \
  --application-insights /subscriptions/<sub-id>/resourceGroups/rg-mlops-prod/providers/Microsoft.Insights/components/appi-mlops-prod
```

### Custom Metrics

```python
# monitoring/custom_metrics.py
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider

# Configure Azure Monitor
configure_azure_monitor(
    connection_string="InstrumentationKey=<key>;IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/"
)

# Get meter
meter = metrics.get_meter(__name__)

# Create custom metrics
prediction_counter = meter.create_counter(
    name="model_predictions",
    description="Number of predictions made",
    unit="1"
)

prediction_latency = meter.create_histogram(
    name="prediction_latency_ms",
    description="Prediction latency in milliseconds",
    unit="ms"
)

model_accuracy_gauge = meter.create_gauge(
    name="model_accuracy_mae",
    description="Model Mean Absolute Error",
    unit="1"
)

drift_score_gauge = meter.create_gauge(
    name="data_drift_score",
    description="Data drift score (0-1)",
    unit="1"
)

def log_prediction_metrics(plant_id: str, circuit_id: str, latency_ms: float):
    """Log prediction metrics."""
    prediction_counter.add(
        1,
        {"plant_id": plant_id, "circuit_id": circuit_id}
    )
    
    prediction_latency.record(
        latency_ms,
        {"plant_id": plant_id, "circuit_id": circuit_id}
    )

def log_model_performance(plant_id: str, circuit_id: str, mae: float):
    """Log model performance metrics."""
    model_accuracy_gauge.set(
        mae,
        {"plant_id": plant_id, "circuit_id": circuit_id}
    )

def log_drift_score(plant_id: str, circuit_id: str, drift_score: float):
    """Log drift score."""
    drift_score_gauge.set(
        drift_score,
        {"plant_id": plant_id, "circuit_id": circuit_id}
    )
```

### KQL Queries for Monitoring

```kql
// monitoring/kql_queries.kql

// 1. Model Performance Over Time
customMetrics
| where name == "model_accuracy_mae"
| extend plant_id = tostring(customDimensions.plant_id)
| extend circuit_id = tostring(customDimensions.circuit_id)
| summarize avg_mae = avg(value), max_mae = max(value) by bin(timestamp, 1d), plant_id, circuit_id
| order by timestamp desc

// 2. Drift Detection Events
customEvents
| where name == "data_drift_detected"
| extend plant_id = tostring(customDimensions.plant_id)
| extend circuit_id = tostring(customDimensions.circuit_id)
| extend drifted_features = customDimensions.drifted_features
| project timestamp, plant_id, circuit_id, drifted_features
| order by timestamp desc

// 3. Prediction Volume by Circuit
customMetrics
| where name == "model_predictions"
| extend plant_id = tostring(customDimensions.plant_id)
| extend circuit_id = tostring(customDimensions.circuit_id)
| summarize prediction_count = sum(value) by bin(timestamp, 1h), plant_id, circuit_id
| render timechart

// 4. High Latency Predictions
customMetrics
| where name == "prediction_latency_ms"
| where value > 1000  // > 1 second
| extend plant_id = tostring(customDimensions.plant_id)
| extend circuit_id = tostring(customDimensions.circuit_id)
| project timestamp, plant_id, circuit_id, latency_ms = value
| order by latency_ms desc

// 5. Model Performance Degradation Alert
customMetrics
| where name == "model_accuracy_mae"
| extend plant_id = tostring(customDimensions.plant_id)
| extend circuit_id = tostring(customDimensions.circuit_id)
| where value > 0.25  // MAE threshold
| summarize count() by plant_id, circuit_id
| where count_ >= 3  // 3 consecutive degradations

// 6. Daily Monitoring Summary
let StartDate = ago(1d);
customMetrics
| where timestamp >= StartDate
| where name in ("model_accuracy_mae", "data_drift_score", "model_predictions")
| extend plant_id = tostring(customDimensions.plant_id)
| extend circuit_id = tostring(customDimensions.circuit_id)
| summarize 
    avg_mae = avgif(value, name == "model_accuracy_mae"),
    max_drift = maxif(value, name == "data_drift_score"),
    total_predictions = sumif(value, name == "model_predictions")
    by plant_id, circuit_id
| where avg_mae > 0.20 or max_drift > 0.15
```

---

## Application Insights Configuration

### Enable Application Insights for Batch Endpoints

```python
# monitoring/setup_app_insights.py
from azure.ai.ml import MLClient
from azure.ai.ml.entities import BatchEndpoint, BatchDeployment
from azure.identity import DefaultAzureCredential

def enable_app_insights_for_endpoint(
    plant_id: str,
    endpoint_name: str,
    app_insights_name: str
):
    """
    Enable Application Insights for batch endpoint.
    """
    ml_client = MLClient(
        DefaultAzureCredential(),
        subscription_id="<sub-id>",
        resource_group_name="rg-mlops-prod",
        workspace_name="mlw-prod"
    )
    
    # Get App Insights instrumentation key
    from azure.mgmt.applicationinsights import ApplicationInsightsManagementClient
    
    ai_client = ApplicationInsightsManagementClient(
        DefaultAzureCredential(),
        subscription_id="<sub-id>"
    )
    
    app_insights = ai_client.components.get(
        resource_group_name="rg-mlops-prod",
        resource_name=app_insights_name
    )
    
    instrumentation_key = app_insights.instrumentation_key
    connection_string = app_insights.connection_string
    
    # Update endpoint with App Insights
    endpoint = ml_client.batch_endpoints.get(endpoint_name)
    
    # Add App Insights to endpoint properties
    endpoint.properties = endpoint.properties or {}
    endpoint.properties["ApplicationInsights"] = connection_string
    
    ml_client.batch_endpoints.begin_create_or_update(endpoint).result()
    
    print(f"✅ App Insights enabled for {endpoint_name}")
    
    return connection_string
```

### Custom Logging in Scoring Script

```python
# scoring/score.py
import os
import json
import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler

# Setup Azure Application Insights logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add Azure Log Handler
connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if connection_string:
    logger.addHandler(
        AzureLogHandler(connection_string=connection_string)
    )

def init():
    """Initialize scoring script."""
    global model
    
    model_path = os.path.join(os.getenv("AZUREML_MODEL_DIR"), "model.pkl")
    model = joblib.load(model_path)
    
    logger.info("Model loaded successfully", extra={
        "custom_dimensions": {
            "model_path": model_path,
            "model_version": os.getenv("MODEL_VERSION", "unknown")
        }
    })

def run(mini_batch):
    """Score mini batch."""
    import pandas as pd
    import time
    
    results = []
    
    for file_path in mini_batch:
        start_time = time.time()
        
        try:
            # Load data
            df = pd.read_parquet(file_path)
            
            # Make predictions
            predictions = model.predict(df)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Log successful prediction
            logger.info("Prediction completed", extra={
                "custom_dimensions": {
                    "plant_id": df["plant_id"].iloc[0],
                    "circuit_id": df["circuit_id"].iloc[0],
                    "num_records": len(df),
                    "latency_ms": latency_ms,
                    "prediction_mean": float(predictions.mean()),
                    "prediction_std": float(predictions.std())
                }
            })
            
            results.append({
                "file": file_path,
                "predictions": predictions.tolist(),
                "status": "success"
            })
            
        except Exception as e:
            # Log error
            logger.error(f"Prediction failed: {str(e)}", extra={
                "custom_dimensions": {
                    "file_path": file_path,
                    "error_type": type(e).__name__
                }
            })
            
            results.append({
                "file": file_path,
                "error": str(e),
                "status": "failed"
            })
    
    return results
```

---

## Monitoring Pipelines

### Daily Monitoring Pipeline

```yaml
# pipelines/monitoring-pipeline.yml
trigger: none

schedules:
  - cron: "0 2 * * *"  # Daily at 2 AM UTC
    displayName: 'Daily Model Monitoring'
    branches:
      include:
        - main

variables:
  - group: mlops-prod-variables

stages:
  - stage: DataDriftCheck
    displayName: 'Data Drift Detection'
    jobs:
      - job: RunDriftDetection
        displayName: 'Run Drift Detection for All Circuits'
        pool:
          vmImage: 'ubuntu-latest'
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.9'
          
          - script: |
              pip install azure-ai-ml azure-identity pandas numpy scipy pyyaml
            displayName: 'Install dependencies'
          
          - task: AzureCLI@2
            displayName: 'Run Drift Detection'
            inputs:
              azureSubscription: 'azure-service-connection'
              scriptType: 'bash'
              scriptLocation: 'scriptPath'
              scriptPath: 'monitoring/run_drift_detection.py'
          
          - task: PublishBuildArtifacts@1
            inputs:
              pathToPublish: 'drift_results_*.json'
              artifactName: 'drift-results'

  - stage: PerformanceCheck
    displayName: 'Model Performance Check'
    dependsOn: DataDriftCheck
    jobs:
      - job: RunPerformanceCheck
        displayName: 'Calculate Performance Metrics'
        pool:
          vmImage: 'ubuntu-latest'
        steps:
          - task: AzureCLI@2
            displayName: 'Run Performance Check'
            inputs:
              azureSubscription: 'azure-service-connection'
              scriptType: 'bash'
              scriptLocation: 'scriptPath'
              scriptPath: 'monitoring/check_model_performance.py'
          
          - task: PublishBuildArtifacts@1
            inputs:
              pathToPublish: 'performance_results_*.json'
              artifactName: 'performance-results'

  - stage: GenerateReport
    displayName: 'Generate Monitoring Report'
    dependsOn: 
      - DataDriftCheck
      - PerformanceCheck
    jobs:
      - job: CreateReport
        displayName: 'Create Summary Report'
        pool:
          vmImage: 'ubuntu-latest'
        steps:
          - task: DownloadBuildArtifacts@0
            inputs:
              artifactName: 'drift-results'
              downloadPath: '$(System.ArtifactsDirectory)'
          
          - task: DownloadBuildArtifacts@0
            inputs:
              artifactName: 'performance-results'
              downloadPath: '$(System.ArtifactsDirectory)'
          
          - script: |
              python monitoring/generate_daily_report.py \
                --drift-results $(System.ArtifactsDirectory)/drift-results/ \
                --performance-results $(System.ArtifactsDirectory)/performance-results/ \
                --output daily_monitoring_report.html
            displayName: 'Generate HTML Report'
          
          - task: PublishBuildArtifacts@1
            inputs:
              pathToPublish: 'daily_monitoring_report.html'
              artifactName: 'monitoring-report'
          
          - task: SendEmail@1
            condition: always()
            inputs:
              to: 'mlops-team@company.com'
              subject: 'Daily ML Monitoring Report - $(Build.BuildNumber)'
              body: 'Daily monitoring report attached. Check Azure DevOps for details.'
              attachments: 'daily_monitoring_report.html'
```

---

## Alerting Strategy

### Alert Rules Configuration

```json
// monitoring/alert_rules.json
{
  "alert_rules": [
    {
      "name": "High MAE Alert",
      "description": "Alert when model MAE exceeds threshold",
      "severity": "2",
      "enabled": true,
      "query": "customMetrics | where name == 'model_accuracy_mae' | where value > 0.25",
      "frequency": "PT5M",
      "timeWindow": "PT15M",
      "actionGroups": ["ag-mlops-critical"],
      "throttling": "PT1H"
    },
    {
      "name": "Data Drift Detected",
      "description": "Alert when significant data drift is detected",
      "severity": "3",
      "enabled": true,
      "query": "customEvents | where name == 'data_drift_detected' | where customDimensions.severity == 'high'",
      "frequency": "PT15M",
      "timeWindow": "PT30M",
      "actionGroups": ["ag-mlops-warning"],
      "throttling": "PT6H"
    },
    {
      "name": "Batch Job Failure",
      "description": "Alert on batch endpoint failures",
      "severity": "1",
      "enabled": true,
      "query": "AzureDiagnostics | where Category == 'BatchScoring' | where Level == 'Error'",
      "frequency": "PT5M",
      "timeWindow": "PT10M",
      "actionGroups": ["ag-mlops-critical"],
      "throttling": "PT30M"
    },
    {
      "name": "Multiple Models Degraded",
      "description": "Alert when >10% of models show degraded performance",
      "severity": "2",
      "enabled": true,
      "query": "customMetrics | where name == 'model_accuracy_mae' | where value > 0.25 | summarize degraded_count = dcount(circuit_id) | where degraded_count > 15",
      "frequency": "PT1H",
      "timeWindow": "PT6H",
      "actionGroups": ["ag-mlops-critical", "ag-management"],
      "throttling": "PT12H"
    },
    {
      "name": "Data Quality Issues",
      "description": "Alert on high null rate or data quality problems",
      "severity": "2",
      "enabled": true,
      "query": "customMetrics | where name == 'data_quality_null_rate' | where value > 0.05",
      "frequency": "PT15M",
      "timeWindow": "PT30M",
      "actionGroups": ["ag-data-engineering"],
      "throttling": "PT2H"
    }
  ],
  
  "action_groups": [
    {
      "name": "ag-mlops-critical",
      "shortName": "MLOpsCrit",
      "emailReceivers": [
        {
          "name": "MLOps Team",
          "emailAddress": "mlops-team@company.com"
        }
      ],
      "smsReceivers": [
        {
          "name": "On-Call Engineer",
          "countryCode": "1",
          "phoneNumber": "555-0100"
        }
      ],
      "webhookReceivers": [
        {
          "name": "Teams Webhook",
          "serviceUri": "https://outlook.office.com/webhook/..."
        }
      ]
    },
    {
      "name": "ag-mlops-warning",
      "shortName": "MLOpsWarn",
      "emailReceivers": [
        {
          "name": "MLOps Team",
          "emailAddress": "mlops-team@company.com"
        }
      ]
    },
    {
      "name": "ag-data-engineering",
      "shortName": "DataEng",
      "emailReceivers": [
        {
          "name": "Data Engineering",
          "emailAddress": "data-eng@company.com"
        }
      ]
    },
    {
      "name": "ag-management",
      "shortName": "Mgmt",
      "emailReceivers": [
        {
          "name": "Engineering Manager",
          "emailAddress": "eng-manager@company.com"
        }
      ]
    }
  ]
}
```

### Deploy Alert Rules

```bash
# monitoring/deploy_alerts.sh
#!/bin/bash

set -e

RESOURCE_GROUP="rg-mlops-prod"
WORKSPACE_ID="/subscriptions/<sub-id>/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.OperationalInsights/workspaces/law-mlops-monitoring"

echo "Deploying alert rules..."

# Create Action Groups first
az monitor action-group create \
  --name ag-mlops-critical \
  --resource-group $RESOURCE_GROUP \
  --short-name MLOpsCrit \
  --email-receiver name=MLOpsTeam address=mlops-team@company.com

az monitor action-group create \
  --name ag-mlops-warning \
  --resource-group $RESOURCE_GROUP \
  --short-name MLOpsWarn \
  --email-receiver name=MLOpsTeam address=mlops-team@company.com

# Create Scheduled Query Alert Rules
az monitor scheduled-query create \
  --name "High MAE Alert" \
  --resource-group $RESOURCE_GROUP \
  --scopes $WORKSPACE_ID \
  --condition "count 'Heartbeat' > 0" \
  --condition-query "customMetrics | where name == 'model_accuracy_mae' | where value > 0.25" \
  --description "Alert when model MAE exceeds threshold" \
  --evaluation-frequency 5m \
  --window-size 15m \
  --severity 2 \
  --action-groups /subscriptions/<sub-id>/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/actionGroups/ag-mlops-critical

echo "✅ Alert rules deployed successfully"
```

---

## Dashboards & Visualization

### Azure Workbook for Monitoring

```json
// monitoring/monitoring_workbook.json
{
  "version": "Notebook/1.0",
  "items": [
    {
      "type": 1,
      "content": {
        "json": "## ML Model Monitoring Dashboard\n\n📊 Real-time monitoring for 75-200 sensor prediction models"
      }
    },
    {
      "type": 3,
      "content": {
        "version": "KqlItem/1.0",
        "query": "customMetrics\n| where name == 'model_accuracy_mae'\n| extend plant_id = tostring(customDimensions.plant_id)\n| extend circuit_id = tostring(customDimensions.circuit_id)\n| summarize avg_mae = avg(value) by bin(timestamp, 1d), plant_id\n| render timechart",
        "size": 0,
        "title": "Average MAE by Plant (Last 30 Days)",
        "timeContext": {
          "durationMs": 2592000000
        }
      }
    },
    {
      "type": 3,
      "content": {
        "version": "KqlItem/1.0",
        "query": "customEvents\n| where name == 'data_drift_detected'\n| extend plant_id = tostring(customDimensions.plant_id)\n| extend circuit_id = tostring(customDimensions.circuit_id)\n| summarize count() by bin(timestamp, 1d)\n| render columnchart",
        "size": 0,
        "title": "Data Drift Events (Last 30 Days)"
      }
    },
    {
      "type": 3,
      "content": {
        "version": "KqlItem/1.0",
        "query": "customMetrics\n| where name == 'model_accuracy_mae'\n| where value > 0.25\n| extend plant_id = tostring(customDimensions.plant_id)\n| extend circuit_id = tostring(customDimensions.circuit_id)\n| summarize count() by plant_id, circuit_id\n| top 10 by count_",
        "size": 0,
        "title": "Top 10 Degraded Models"
      }
    },
    {
      "type": 3,
      "content": {
        "version": "KqlItem/1.0",
        "query": "customMetrics\n| where name == 'prediction_latency_ms'\n| extend plant_id = tostring(customDimensions.plant_id)\n| summarize avg_latency = avg(value), p95_latency = percentile(value, 95) by bin(timestamp, 1h)\n| render timechart",
        "size": 0,
        "title": "Prediction Latency (Avg & P95)"
      }
    }
  ]
}
```

---

## Response Workflows

### Workflow: Data Drift Detected

```
1. Alert Received
   ↓
2. Review Drift Dashboard
   - Identify drifted features
   - Check magnitude (PSI, Wasserstein distance)
   ↓
3. Root Cause Analysis
   - Check data pipeline changes
   - Verify sensor calibration
   - Review recent maintenance
   ↓
4. Decision
   ├─→ Minor Drift (<0.15): Monitor
   ├─→ Moderate Drift (0.15-0.25): Schedule retrain
   └─→ Severe Drift (>0.25): Immediate retrain
   ↓
5. Action
   - Trigger manual training pipeline
   - Update baseline dataset
   - Document incident
```

### Workflow: Model Performance Degradation

```
1. Performance Alert (MAE > 0.25)
   ↓
2. Verify Alert
   - Check multiple metrics (RMSE, MAPE)
   - Compare to historical performance
   ↓
3. Check for Drift
   - Run ad-hoc drift detection
   - Review data quality
   ↓
4. If No Drift Detected
   - Review model deployment
   - Check for code changes
   - Verify environment version
   ↓
5. Retrain Model
   - Use latest data
   - Compare new vs old model
   ↓
6. Deploy if Improved
   - Register new model version
   - Deploy to Test
   - Promote to Prod
```

---

## Implementation Checklist

### Phase 1: Setup (Week 1-2)

- [ ] Create Log Analytics Workspace
- [ ] Setup Application Insights for all workspaces
- [ ] Deploy alert rules and action groups
- [ ] Create monitoring workbook dashboard
- [ ] Configure Azure ML v2 SDK environment

### Phase 2: Model Monitoring (Week 3-4)

- [ ] Implement model monitor creation script
- [ ] Setup monitors for all 75-200 circuits
- [ ] Configure monitoring schedules
- [ ] Test alert notifications
- [ ] Document monitoring thresholds

### Phase 3: Drift Detection (Week 5-6)

- [ ] Implement custom drift detector
- [ ] Create baseline datasets for all circuits
- [ ] Deploy daily drift detection pipeline
- [ ] Test drift alerts
- [ ] Create drift visualization dashboard

### Phase 4: Integration (Week 7-8)

- [ ] Update scoring scripts with App Insights logging
- [ ] Implement custom metrics collection
- [ ] Create KQL queries for common scenarios
- [ ] Setup scheduled monitoring pipeline
- [ ] Document response workflows

### Phase 5: Validation (Week 9-10)

- [ ] End-to-end testing of monitoring
- [ ] Validate alert workflows
- [ ] Test drift detection accuracy
- [ ] Performance test monitoring overhead
- [ ] User acceptance testing

### Phase 6: Production (Week 11-12)

- [ ] Deploy to production
- [ ] Train operations team
- [ ] Create runbooks
- [ ] Establish SLAs
- [ ] Conduct retrospective

---

## Cost Considerations

### Monthly Monitoring Costs

| Component | Details | Est. Cost |
|-----------|---------|-----------|
| **Log Analytics** | 90-day retention, ~50GB/month | $115 |
| **Application Insights** | 3 instances, 5GB free + 10GB extra | $23 |
| **Azure Monitor Alerts** | ~20 alert rules | $2 |
| **Model Monitoring Compute** | Daily runs, 2 hours/day on Standard_DS3_v2 | $60 |
| **Data Storage** | Baseline + monitoring data | $10 |
| **Total** | | **~$210/month** |

### Cost Optimization

- Use 90-day retention (vs 365 days)
- Archive old monitoring data to Cool storage
- Optimize query frequency
- Use sampling for high-volume metrics

---

## Related Documents

- [11-monitoring-strategy.md](11-monitoring-strategy.md) - High-level monitoring strategy
- [12-operational-runbooks.md](12-operational-runbooks.md) - Incident response procedures
- [03-multi-model-strategy.md](03-multi-model-strategy.md) - Multi-model architecture
- [02-data-architecture.md](02-data-architecture.md) - Data pipeline monitoring

---

**Document Version:** 1.0  
**Last Updated:** December 9, 2025  
**Author:** MLOps Team
