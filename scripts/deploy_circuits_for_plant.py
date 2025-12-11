"""
Deploy circuits for a specific plant to batch endpoint.

Usage:
    python scripts/deploy_circuits_for_plant.py \
        --workspace mlw-prod \
        --resource-group rg-mlops-prod \
        --plant-id PLANT001 \
        --endpoint-name batch-plant001
"""

import argparse
import yaml
from azure.ai.ml import MLClient
from azure.ai.ml.entities import BatchDeployment, Model, Environment, CodeConfiguration
from azure.identity import DefaultAzureCredential


def deploy_circuit(
    ml_client: MLClient,
    plant_id: str,
    circuit_id: str,
    model_name: str,
    endpoint_name: str,
    environment_version: str
):
    """Deploy a single circuit to batch endpoint."""
    
    deployment_name = circuit_id.lower()
    
    # Get latest model version
    model = ml_client.models.get(name=model_name, label="latest")
    
    # Create deployment
    deployment = BatchDeployment(
        name=deployment_name,
        endpoint_name=endpoint_name,
        model=model,
        environment=f"sensor-forecasting-env:{environment_version}",
        code_configuration=CodeConfiguration(
            code="scoring",
            scoring_script="score.py"
        ),
        compute="cpu-cluster",
        instance_count=1,
        max_concurrency_per_instance=2,
        mini_batch_size=10,
        output_action="append_row",
        output_file_name="predictions.csv",
        retry_settings={
            "max_retries": 3,
            "timeout": 300
        },
        logging_level="info"
    )
    
    print(f"  Deploying {plant_id}/{circuit_id} to {endpoint_name}/{deployment_name}")
    
    try:
        ml_client.batch_deployments.begin_create_or_update(deployment).result()
        print(f"  ✅ {deployment_name} deployed")
        return True
    except Exception as e:
        print(f"  ❌ {deployment_name} failed: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Deploy circuits for a plant")
    parser.add_argument("--subscription-id", help="Azure subscription ID")
    parser.add_argument("--resource-group", required=True, help="Resource group")
    parser.add_argument("--workspace", required=True, help="Workspace name")
    parser.add_argument("--plant-id", required=True, help="Plant ID")
    parser.add_argument("--endpoint-name", required=True, help="Batch endpoint name")
    parser.add_argument("--config-path", default="config/circuits.yaml", help="Config path")
    
    args = parser.parse_args()
    
    # Initialize ML Client
    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=args.subscription_id,
        resource_group_name=args.resource_group,
        workspace_name=args.workspace
    )
    
    # Load circuit config
    with open(args.config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Filter circuits for this plant
    plant_circuits = [
        c for c in config['circuits']
        if c['plant_id'] == args.plant_id
    ]
    
    print(f"🚀 Deploying {len(plant_circuits)} circuits for {args.plant_id}")
    
    # Deploy each circuit
    results = []
    for circuit in plant_circuits:
        success = deploy_circuit(
            ml_client,
            circuit['plant_id'],
            circuit['circuit_id'],
            circuit['model_name'],
            args.endpoint_name,
            circuit['environment_version']
        )
        results.append(success)
    
    # Summary
    successful = sum(results)
    print(f"\n📊 Summary: {successful}/{len(plant_circuits)} circuits deployed")
    
    return 0 if successful == len(plant_circuits) else 1


if __name__ == "__main__":
    exit(main())
