"""
Hyperparameter Tuning Helper Functions

Utilities for running hyperparameter tuning experiments on sensor circuits.
"""
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from azure.ai.ml import MLClient, load_component
from azure.ai.ml.entities import Job
from azure.identity import DefaultAzureCredential


def load_tuning_component(component_path: str = "../components/training/hyperparameter-tuning-pipeline/component.yaml"):
    """
    Load the hyperparameter tuning component from local file.
    
    Args:
        component_path: Path to component.yaml file
        
    Returns:
        Loaded component object
    """
    return load_component(source=component_path)


def submit_tuning_job(
    ml_client: MLClient,
    plant_id: str,
    circuit_id: str,
    circuit_config_path: str,
    training_data_asset: str,
    max_trials: int = 20,
    sampling_algorithm: str = "random",
    component_path: str = "../components/training/hyperparameter-tuning-pipeline/component.yaml"
) -> Job:
    """
    Submit a hyperparameter tuning job for a specific circuit.
    
    Args:
        ml_client: Azure ML client
        plant_id: Plant identifier (e.g., "PLANT001")
        circuit_id: Circuit identifier (e.g., "CIRCUIT01")
        circuit_config_path: Path to circuit config YAML
        training_data_asset: MLTable data asset reference (e.g., "azureml:sensor_training_data_P001_C001:1")
        max_trials: Maximum number of trials to run
        sampling_algorithm: "random" or "bayesian"
        component_path: Path to tuning component
        
    Returns:
        Submitted job object
    """
    # Load component
    tuning_component = load_component(source=component_path)
    
    # Create job
    job = tuning_component(
        circuit_config=circuit_config_path,
        training_data=training_data_asset,
        max_trials=max_trials,
        sampling_algorithm=sampling_algorithm
    )
    
    # Set display name
    job.display_name = f"HPO_{plant_id}_{circuit_id}"
    job.experiment_name = f"hyperparameter-tuning-{plant_id.lower()}-{circuit_id.lower()}"
    
    # Submit job
    submitted_job = ml_client.jobs.create_or_update(job)
    
    print(f"✅ Submitted hyperparameter tuning job: {submitted_job.name}")
    print(f"   Plant: {plant_id}, Circuit: {circuit_id}")
    print(f"   Max Trials: {max_trials}, Sampling: {sampling_algorithm}")
    print(f"   View in Studio: {submitted_job.studio_url}")
    
    return submitted_job


def get_best_trial_results(ml_client: MLClient, job_name: str) -> Dict[str, Any]:
    """
    Get the best trial results from a completed hyperparameter tuning job.
    
    Args:
        ml_client: Azure ML client
        job_name: Name of the completed tuning job
        
    Returns:
        Dictionary with best hyperparameters and metrics
    """
    # Get the parent sweep job
    job = ml_client.jobs.get(job_name)
    
    if job.status != "Completed":
        print(f"⚠️  Job status: {job.status}")
        print("   Job must be completed to retrieve best results")
        return {}
    
    # Get all child runs
    child_runs = ml_client.jobs.list(parent_job_name=job_name)
    
    # Find best run based on primary metric
    best_run = None
    best_metric_value = float('inf')  # Assuming we're minimizing
    
    for run in child_runs:
        if hasattr(run, 'properties') and 'primary_metric' in run.properties:
            metric_value = float(run.properties['primary_metric'])
            if metric_value < best_metric_value:
                best_metric_value = metric_value
                best_run = run
    
    if not best_run:
        print("⚠️  Could not find best run")
        return {}
    
    # Extract hyperparameters and metrics
    best_params = best_run.properties.get('hyperparameters', {})
    
    result = {
        "best_run_id": best_run.name,
        "best_metric_value": best_metric_value,
        "hyperparameters": best_params,
        "metrics": {
            "val_loss": best_run.properties.get('val_loss'),
            "mae": best_run.properties.get('mae'),
            "rmse": best_run.properties.get('rmse'),
            "r2_score": best_run.properties.get('r2_score')
        }
    }
    
    print(f"✅ Best trial: {best_run.name}")
    print(f"   Val Loss: {best_metric_value:.4f}")
    print(f"   Hyperparameters: {best_params}")
    
    return result


def generate_circuits_yaml_snippet(
    plant_id: str,
    circuit_id: str,
    best_params: Dict[str, Any]
) -> str:
    """
    Generate a YAML snippet to update circuits.yaml with best hyperparameters.
    
    Args:
        plant_id: Plant identifier
        circuit_id: Circuit identifier
        best_params: Best hyperparameters from tuning
        
    Returns:
        YAML snippet as string
    """
    snippet = f"""
# Updated hyperparameters for {plant_id}/{circuit_id}
# Based on hyperparameter tuning results

hyperparameters:
  lstm_units: {best_params.get('lstm_units', 64)}
  learning_rate: {best_params.get('learning_rate', 0.001)}
  epochs: {best_params.get('epochs', 50)}
  batch_size: {best_params.get('batch_size', 32)}
"""
    
    print("📋 Copy this snippet to update circuits.yaml:")
    print("=" * 60)
    print(snippet)
    print("=" * 60)
    
    return snippet


def compare_tuning_runs(
    ml_client: MLClient,
    job_names: List[str]
) -> None:
    """
    Compare results from multiple hyperparameter tuning runs.
    
    Args:
        ml_client: Azure ML client
        job_names: List of job names to compare
    """
    print(f"Comparing {len(job_names)} tuning runs...\n")
    
    results = []
    for job_name in job_names:
        result = get_best_trial_results(ml_client, job_name)
        if result:
            results.append({
                "job_name": job_name,
                **result
            })
    
    if not results:
        print("⚠️  No completed jobs found")
        return
    
    # Sort by best metric
    results.sort(key=lambda x: x['best_metric_value'])
    
    print("\n📊 Comparison Results (sorted by val_loss):")
    print("=" * 80)
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Job: {result['job_name']}")
        print(f"   Val Loss: {result['best_metric_value']:.4f}")
        print(f"   Hyperparameters: {result['hyperparameters']}")
    print("=" * 80)


def save_tuning_results(
    job_name: str,
    best_results: Dict[str, Any],
    output_path: str = "tuning_results.json"
) -> None:
    """
    Save tuning results to a JSON file.
    
    Args:
        job_name: Name of the tuning job
        best_results: Best trial results
        output_path: Path to save results
    """
    results = {
        "job_name": job_name,
        "timestamp": str(Path(output_path).stat().st_mtime),
        **best_results
    }
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ Results saved to: {output_path}")


if __name__ == "__main__":
    print("Hyperparameter Tuning Helper Functions")
    print("Import this module in your notebook or scripts")
    print("\nExample usage:")
    print("""
    from scripts.hyperparameter_helper import submit_tuning_job, get_best_trial_results
    
    # Submit tuning job
    job = submit_tuning_job(
        ml_client=ml_client,
        plant_id="PLANT001",
        circuit_id="CIRCUIT01",
        circuit_config_path="config/circuits/PLANT001_CIRCUIT01.yaml",
        training_data_asset="azureml:sensor_training_data_P001_C001:1",
        max_trials=20,
        sampling_algorithm="random"
    )
    
    # Get best results (after job completes)
    best_results = get_best_trial_results(ml_client, job.name)
    
    # Generate config snippet
    generate_circuits_yaml_snippet("PLANT001", "CIRCUIT01", best_results['hyperparameters'])
    """)
