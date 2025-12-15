#!/usr/bin/env python3
"""
Register Trained Models in ML Workspace

Register models from completed training jobs with proper tags.

Usage:
    python scripts/pipeline/register_models.py \
        --training-jobs training_jobs.json \
        --subscription-id <sub_id> \
        --resource-group <rg> \
        --workspace-name <workspace> \
        --output registered_models.json
"""

import argparse
import json
import sys
from azure.identity import DefaultAzureCredential
from azure.ai.ml import MLClient
from azure.ai.ml.entities import Model


def register_models(
    jobs_file: str,
    subscription_id: str,
    resource_group: str,
    workspace_name: str
) -> dict:
    """
    Register models from completed training jobs.
    
    Returns:
        Dict with registered models and failures
    """
    with open(jobs_file, 'r') as f:
        data = json.load(f)
    
    submitted_jobs = data.get('submitted_jobs', [])
    
    if not submitted_jobs:
        print("ℹ️  No jobs to register models for")
        return {'models': [], 'failed': []}
    
    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name
    )
    
    registered_models = []
    failed = []
    
    for job_info in submitted_jobs:
        job_name = job_info['job_name']
        model_name = job_info['model_name']
        plant_id = job_info['plant_id']
        circuit_id = job_info['circuit_id']
        cutoff_date = job_info['cutoff_date']
        training_hash = job_info.get('training_hash')  # Use from job info!
        
        print(f"\n📊 Registering model from job: {job_name}")
        
        if not training_hash:
            print(f"   ⚠️  No training_hash in job info, skipping")
            failed.append(f"{plant_id}_{circuit_id}")
            continue
        
        try:
            job = ml_client.jobs.get(job_name)
            
            if job.status != 'Completed':
                print(f"   ⚠️  Job not completed: {job.status}")
                failed.append(f"{plant_id}_{circuit_id}")
                continue
            
            # Register model from job output
            model_path = f"azureml://jobs/{job_name}/outputs/model"
            
            # Get model type from job info (default to custom_model)
            model_type = job_info.get('model_type', 'custom_model')
            
            model = Model(
                name=model_name,
                path=model_path,
                type=model_type,  # Configurable: custom_model or mlflow_model
                description=f"Model for {plant_id}/{circuit_id}",
                tags={
                    "plant_id": plant_id,
                    "circuit_id": circuit_id,
                    "cutoff_date": cutoff_date,
                    "training_hash": training_hash,  # Consistent with job submission!
                    "training_job": job_name,
                    "model_type": model_type
                }
            )
            
            registered_model = ml_client.models.create_or_update(model)
            version = registered_model.version
            
            print(f"   ✅ Registered: {model_name}:v{version}")
            print(f"   📝 Training hash: {training_hash}")
            print(f"   🏷️  Model type: {model_type}")
            
            registered_models.append({
                'model_name': model_name,
                'version': str(version),
                'plant_id': plant_id,
                'circuit_id': circuit_id,
                'cutoff_date': cutoff_date,
                'training_hash': training_hash,  # Pass to next stage
                'training_job': job_name
            })
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed.append(f"{plant_id}_{circuit_id}")
    
    print(f"\n{'='*60}")
    print(f"Registration Summary:")
    print(f"  ✅ Registered: {len(registered_models)}")
    print(f"  ❌ Failed: {len(failed)}")
    print(f"{'='*60}\n")
    
    return {'models': registered_models, 'failed': failed}


def main():
    parser = argparse.ArgumentParser(
        description="Register trained models"
    )
    parser.add_argument(
        '--training-jobs',
        required=True,
        help='Path to training jobs JSON file'
    )
    parser.add_argument(
        '--subscription-id',
        required=True,
        help='Azure subscription ID'
    )
    parser.add_argument(
        '--resource-group',
        required=True,
        help='Resource group name'
    )
    parser.add_argument(
        '--workspace-name',
        required=True,
        help='Azure ML workspace name'
    )
    parser.add_argument(
        '--output',
        default='registered_models.json',
        help='Output JSON file (default: registered_models.json)'
    )
    
    args = parser.parse_args()
    
    try:
        result = register_models(
            jobs_file=args.training_jobs,
            subscription_id=args.subscription_id,
            resource_group=args.resource_group,
            workspace_name=args.workspace_name
        )
        
        # Save registered models
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        
        if not result['models']:
            print("⚠️  No models were successfully registered")
            return 1
        
        print(f"✅ Model registration complete")
        print(f"Saved to {args.output}")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
