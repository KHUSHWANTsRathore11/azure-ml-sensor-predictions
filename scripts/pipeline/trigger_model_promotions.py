#!/usr/bin/env python3
"""
Trigger Child Pipelines for Model Promotions

This script triggers a separate pipeline run for each registered model,
allowing independent approvals and timelines.

Usage:
    python scripts/pipeline/trigger_model_promotions.py \
        --registered-models registered_models.json \
        --organization <org> \
        --project <project> \
        --pipeline-id <id> \
        --pat-token <token>
"""

import argparse
import json
import sys
import requests
import base64


def trigger_pipeline(
    organization: str,
    project: str,
    pipeline_id: int,
    pat_token: str,
    parameters: dict
) -> dict:
    """
    Trigger Azure DevOps pipeline with parameters.
    
    Returns:
        Pipeline run details
    """
    url = f"https://dev.azure.com/{organization}/{project}/_apis/pipelines/{pipeline_id}/runs?api-version=7.0"
    
    # Encode PAT token
    auth = base64.b64encode(f":{pat_token}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    
    body = {
        "templateParameters": parameters
    }
    
    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    
    return response.json()


def main():
    parser = argparse.ArgumentParser(
        description="Trigger child pipelines for model promotions"
    )
    parser.add_argument('--registered-models', required=True,
                        help='Path to registered_models.json')
    parser.add_argument('--organization', required=True,
                        help='Azure DevOps organization name')
    parser.add_argument('--project', required=True,
                        help='Azure DevOps project name')
    parser.add_argument('--pipeline-id', required=True, type=int,
                        help='Pipeline ID for promote-single-model-pipeline')
    parser.add_argument('--pat-token', required=False,
                        help='Personal Access Token (or use AZURE_DEVOPS_PAT env var)')
    parser.add_argument('--output', default='triggered_promotions.json',
                        help='Output file for triggered pipeline runs')
    
    args = parser.parse_args()
    
    # Get PAT token
    import os
    pat_token = args.pat_token or os.getenv('AZURE_DEVOPS_PAT') or os.getenv('SYSTEM_ACCESSTOKEN')
    
    if not pat_token:
        print("❌ Error: PAT token required (use --pat-token or AZURE_DEVOPS_PAT env var)")
        return 1
    
    # Load models
    with open(args.registered_models) as f:
        data = json.load(f)
    
    models = data.get('models', [])
    
    if not models:
        print("ℹ️  No models to promote")
        return 0
    
    print(f"🚀 Triggering promotion pipelines for {len(models)} model(s)...")
    print()
    
    triggered = []
    failed = []
    
    for model in models:
        model_name = model['model_name']
        model_version = model['version']
        plant_id = model['plant_id']
        circuit_id = model['circuit_id']
        
        print(f"📦 Triggering: {plant_id}/{circuit_id} - {model_name}:v{model_version}")
        
        # Prepare parameters
        parameters = {
            'modelName': model_name,
            'modelVersion': str(model_version),
            'plantId': plant_id,
            'circuitId': circuit_id,
            'trainingHash': model.get('training_hash', ''),
            'cutoffDate': model.get('cutoff_date', '')
        }
        
        try:
            result = trigger_pipeline(
                organization=args.organization,
                project=args.project,
                pipeline_id=args.pipeline_id,
                pat_token=pat_token,
                parameters=parameters
            )
            
            run_id = result.get('id')
            run_url = result.get('_links', {}).get('web', {}).get('href', '')
            
            print(f"   ✅ Triggered: Run #{run_id}")
            print(f"   🔗 {run_url}")
            
            triggered.append({
                'model_name': model_name,
                'version': model_version,
                'plant_id': plant_id,
                'circuit_id': circuit_id,
                'pipeline_run_id': run_id,
                'pipeline_run_url': run_url
            })
        
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            failed.append({
                'model_name': model_name,
                'version': model_version,
                'plant_id': plant_id,
                'error': str(e)
            })
        
        print()
    
    # Summary
    print(f"{'='*60}")
    print(f"Summary:")
    print(f"  ✅ Triggered: {len(triggered)} pipeline(s)")
    print(f"  ❌ Failed: {len(failed)}")
    print(f"{'='*60}")
    
    # Save results
    output = {
        'triggered': triggered,
        'failed': failed
    }
    
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Results saved to {args.output}")
    
    if failed:
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
