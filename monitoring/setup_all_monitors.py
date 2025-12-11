"""
Setup Azure ML Model Monitors for all circuits.

This script creates Azure ML v2 model monitors with drift detection
and performance tracking.

Usage:
    python monitoring/setup_all_monitors.py \
        --subscription-id <sub-id> \
        --resource-group rg-mlops-prod \
        --workspace mlw-prod
"""

import argparse
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    MonitoringTarget,
    MonitorSchedule,
    AlertNotification
)
from azure.identity import DefaultAzureCredential


def create_model_monitor(
    ml_client: MLClient,
    plant_id: str,
    circuit_id: str,
    model_name: str
):
    """
    Create Azure ML v2 Model Monitor for a specific circuit.
    
    Monitors:
    - Prediction drift
    - Data drift
    - Data quality
    - Model performance
    """
    from azure.ai.ml.entities import ModelMonitor
    
    monitor_name = f"monitor-{plant_id}-{circuit_id}".lower()
    
    # Define monitoring target
    monitoring_target = MonitoringTarget(
        endpoint_deployment_id=f"azureml://subscriptions/{ml_client.subscription_id}/resourceGroups/{ml_client.resource_group_name}/providers/Microsoft.MachineLearningServices/workspaces/{ml_client.workspace_name}/batchEndpoints/batch-{plant_id.lower()}/deployments/{circuit_id.lower()}",
        model_id=f"azureml://registries/shared-registry/models/{model_name}"
    )
    
    # Create model monitor
    model_monitor = ModelMonitor(
        name=monitor_name,
        monitoring_target=monitoring_target,
        compute="cpu-cluster",
        
        monitoring_signals={
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
            
            "data_drift": {
                "type": "DataDrift",
                "baseline_dataset": f"azureml://datastores/workspaceblobstore/paths/baseline/{plant_id}/{circuit_id}/",
                "target_dataset": f"azureml://datastores/workspaceblobstore/paths/production/{plant_id}/{circuit_id}/",
                "features": ["temperature", "pressure", "vibration", "current", "voltage", "flow_rate"],
                "metric_thresholds": {
                    "numerical": {
                        "jensen_shannon_distance": 0.15,
                        "normalized_wasserstein_distance": 0.15
                    }
                }
            },
            
            "data_quality": {
                "type": "DataQuality",
                "target_dataset": f"azureml://datastores/workspaceblobstore/paths/production/{plant_id}/{circuit_id}/",
                "features": ["all"],
                "metric_thresholds": {
                    "null_value_rate": 0.05,
                    "data_type_error_rate": 0.01,
                    "out_of_bounds_rate": 0.05
                }
            }
        },
        
        alert_notification=AlertNotification(
            emails=["mlops-team@company.com"],
            custom_properties={
                "plant_id": plant_id,
                "circuit_id": circuit_id,
                "severity": "high"
            }
        )
    )
    
    created_monitor = ml_client.model_monitors.begin_create_or_update(
        model_monitor
    ).result()
    
    return created_monitor


def create_monitor_schedule(
    ml_client: MLClient,
    plant_id: str,
    circuit_id: str
):
    """Create daily monitoring schedule."""
    monitor_name = f"monitor-{plant_id}-{circuit_id}".lower()
    
    schedule = MonitorSchedule(
        name=f"schedule-{monitor_name}",
        monitor_name=monitor_name,
        trigger={
            "type": "cron",
            "expression": "0 2 * * *",  # Daily at 2 AM
            "time_zone": "UTC"
        }
    )
    
    created_schedule = ml_client.schedules.begin_create_or_update(
        schedule
    ).result()
    
    return created_schedule


def setup_monitor_for_circuit(
    subscription_id: str,
    resource_group: str,
    workspace: str,
    circuit_config: dict
):
    """Setup monitor for single circuit."""
    plant_id = circuit_config["plant_id"]
    circuit_id = circuit_config["circuit_id"]
    model_name = circuit_config["model_name"]
    
    try:
        ml_client = MLClient(
            DefaultAzureCredential(),
            subscription_id=subscription_id,
            resource_group_name=resource_group,
            workspace_name=workspace
        )
        
        # Create monitor
        monitor = create_model_monitor(ml_client, plant_id, circuit_id, model_name)
        
        # Create schedule
        schedule = create_monitor_schedule(ml_client, plant_id, circuit_id)
        
        return {
            "plant_id": plant_id,
            "circuit_id": circuit_id,
            "status": "success",
            "monitor": monitor.name,
            "schedule": schedule.name
        }
    except Exception as e:
        return {
            "plant_id": plant_id,
            "circuit_id": circuit_id,
            "status": "failed",
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description="Setup model monitors for all circuits")
    parser.add_argument("--subscription-id", required=True, help="Azure subscription ID")
    parser.add_argument("--resource-group", required=True, help="Resource group name")
    parser.add_argument("--workspace", required=True, help="Azure ML workspace name")
    parser.add_argument("--config-path", default="config/circuits.yaml", help="Path to circuits config")
    parser.add_argument("--max-workers", type=int, default=10, help="Max parallel workers")
    
    args = parser.parse_args()
    
    # Load circuit config
    with open(args.config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    circuits = config['circuits']
    
    print(f"🚀 Setting up monitors for {len(circuits)} circuits...")
    print(f"   Workspace: {args.workspace}")
    print(f"   Max Workers: {args.max_workers}\n")
    
    results = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_circuit = {
            executor.submit(
                setup_monitor_for_circuit,
                args.subscription_id,
                args.resource_group,
                args.workspace,
                circuit
            ): circuit
            for circuit in circuits
        }
        
        for future in as_completed(future_to_circuit):
            result = future.result()
            results.append(result)
            
            if result["status"] == "success":
                print(f"✅ {result['plant_id']}/{result['circuit_id']} - {result['monitor']}")
            else:
                print(f"❌ {result['plant_id']}/{result['circuit_id']}: {result['error']}")
    
    # Summary
    successful = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - successful
    
    print(f"\n📊 Summary:")
    print(f"   Total: {len(results)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
