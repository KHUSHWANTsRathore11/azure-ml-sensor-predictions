#!/usr/bin/env python3
"""
Submit Training Jobs for Changed Circuits

Reads changed circuits and submits Azure ML pipeline jobs for training.

Usage:
    python scripts/pipeline/submit_training_jobs.py \
        --changed-circuits changed_circuits.json \
        --output training_jobs.json \
        --pipeline-file pipelines/single-circuit-training.yaml
"""

import argparse
import hashlib
import json
import subprocess
import sys
import yaml
from pathlib import Path
from datetime import datetime, timedelta, timezone


def calculate_training_hash(circuit_cfg: dict) -> str:
    """
    Calculate training hash from all parameters that affect training.
    
    Includes:
    - Features (data columns)
    - Cutoff date (data filtering)
    - Delta version (data snapshot)
    - Environment version (code/dependencies)
    - Hyperparameters (model config)
    """
    features = circuit_cfg.get('features', [])
    feature_str = ','.join(sorted(features))
    
    cutoff_date = circuit_cfg.get('cutoff_date', '')
    delta_version = circuit_cfg.get('delta_version', 0)
    environment_version = circuit_cfg.get('environment_version', '1.0.0')
    
    hyperparams = circuit_cfg.get('hyperparameters', {})
    hyperparam_str = ','.join(f"{k}={v}" for k, v in sorted(hyperparams.items()))
    
    hash_str = f"{feature_str}|{cutoff_date}|{delta_version}|{environment_version}|{hyperparam_str}"
    return hashlib.md5(hash_str.encode()).hexdigest()[:8]


def get_last_model_training_hash(
    model_name: str,
    workspace_name: str = None,
    resource_group: str = None
) -> str:
    """
    Get training hash from the last registered model.
    This is the source of truth for what's in production.
    
    Returns:
        Training hash from last model, or None if no model exists
    """
    cmd = [
        'az', 'ml', 'model', 'list',
        '--name', model_name,
        '--query', '[0].tags.training_hash',
        '-o', 'tsv'
    ]
    
    if workspace_name:
        cmd.extend(['--workspace-name', workspace_name])
    if resource_group:
        cmd.extend(['--resource-group', resource_group])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def determine_circuits_to_train(
    workspace_name: str = None,
    resource_group: str = None
) -> list:
    """
    Determine which circuits need training by comparing current config hash
    with the hash stored in the last registered model.
    
    Returns:
        List of circuits that need training
    """
    print("🔍 Determining which circuits need training...\n")
    
    # Load all circuits from config
    with open('config/circuits.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    all_circuits = config.get('circuits', [])
    circuits_to_train = []
    
    for circuit in all_circuits:
        plant_id = circuit['plant_id']
        circuit_id = circuit['circuit_id']
        model_name = circuit.get('model_name', f'{plant_id.lower()}-{circuit_id.lower()}')
        
        print(f"📊 Checking: {plant_id}_{circuit_id}")
        
        # Calculate current training hash
        current_hash = calculate_training_hash(circuit)
        print(f"   Current training hash: {current_hash}")
        
        # Get hash from last registered model
        last_hash = get_last_model_training_hash(
            model_name=model_name,
            workspace_name=workspace_name,
            resource_group=resource_group
        )
        
        if last_hash:
            print(f"   Last model hash: {last_hash}")
            
            if current_hash != last_hash:
                print(f"   ✅ Config changed → Needs training\n")
                circuits_to_train.append({
                    'plant_id': plant_id,
                    'circuit_id': circuit_id,
                    'model_name': model_name,
                    'training_hash': current_hash
                })
            else:
                print(f"   ⏭️  No change → Skip training\n")
        else:
            print(f"   ✅ No model registered → First training\n")
            circuits_to_train.append({
                'plant_id': plant_id,
                'circuit_id': circuit_id,
                'model_name': model_name,
                'training_hash': current_hash
            })
    
    print(f"{'='*60}")
    print(f"Training determination:")
    print(f"  Total circuits: {len(all_circuits)}")
    print(f"  Need training: {len(circuits_to_train)}")
    print(f"  Skip (no change): {len(all_circuits) - len(circuits_to_train)}")
    print(f"{'='*60}\n")
    
    return circuits_to_train


def submit_training_jobs(
    workspace_name: str = None,
    resource_group: str = None,
    pipeline_file: str = 'pipelines/single-circuit-training.yaml'
) -> dict:
    """
    Submit training jobs for circuits that need training.
    
    Returns:
        Dict with submitted_jobs and failed_submissions lists
    """
    # Determine which circuits need training (hash comparison)
    circuits = determine_circuits_to_train(
        workspace_name=workspace_name,
        resource_group=resource_group
    )
    
    if not circuits:
        print("ℹ️  No circuits need training (all configs unchanged)")
        return {'submitted_jobs': [], 'failed_submissions': []}
    
    print(f"🚀 Submitting training jobs for {len(circuits)} circuit(s)...\n")

    
    submitted_jobs = []
    failed_submissions = []
    
    for circuit in circuits:
        plant_id = circuit['plant_id']
        circuit_id = circuit['circuit_id']
        model_name = circuit['model_name']
        training_hash = circuit['training_hash']
        
        print(f"\n📊 Submitting training job: {plant_id}_{circuit_id}")
        print(f"   Training hash: {training_hash}")
        
        # Load circuit config to get full details
        with open('config/circuits.yaml', 'r') as f:
            main_config = yaml.safe_load(f)
        
        # Find this circuit in config
        circuit_cfg = None
        for cfg in main_config.get('circuits', []):
            if cfg['plant_id'] == plant_id and cfg['circuit_id'] == circuit_id:
                circuit_cfg = cfg
                break
        
        if not circuit_cfg:
            print(f"   ❌ ERROR: Circuit not found in circuits.yaml")
            failed_submissions.append({
                'plant_id': plant_id,
                'circuit_id': circuit_id,
                'error': 'Circuit not found in config'
            })
            continue
        
        cutoff_date = circuit_cfg.get('cutoff_date', '')
        delta_version = circuit_cfg.get('delta_version', 0)
        
        # Query for latest MLTable with matching config
        data_name = f"{plant_id}_{circuit_id}"
        
        query_cmd = [
            'az', 'ml', 'data', 'list',
            '--name', data_name,
            '--query', '[0].version',
            '-o', 'tsv'
        ]
        
        if workspace_name:
            query_cmd.extend(['--workspace-name', workspace_name])
        if resource_group:
            query_cmd.extend(['--resource-group', resource_group])
        
        query_result = subprocess.run(query_cmd, capture_output=True, text=True)
        
        if query_result.returncode != 0 or not query_result.stdout.strip():
            print(f"   ❌ ERROR: No MLTable found for {data_name}")
            failed_submissions.append({
                'plant_id': plant_id,
                'circuit_id': circuit_id,
                'error': 'MLTable not found'
            })
            continue
        
        mltable_version = query_result.stdout.strip()
        mltable_uri = f"azureml:{data_name}:{mltable_version}"
        
        print(f"   MLTable: {mltable_uri}")
        print(f"   Model: {model_name}")
        
        circuit_config_path = f'config/circuits/{plant_id}_{circuit_id}.yaml'
        
        timestamp = cutoff_date.replace('-', '_').replace(':', '_')
        job_name = f"{plant_id}_{circuit_id}_{timestamp}_v{mltable_version}"
        
        print(f"   Job: {job_name}")
        
        cmd = [
            'az', 'ml', 'job', 'create',
            '--file', pipeline_file,
            '--name', job_name,
            '--set', f'inputs.circuit_config.path={circuit_config_path}',
            '--set', f'inputs.training_data.path={mltable_uri}',
            '--set', f'tags.training_hash={training_hash}',  # Store hash in job tags
            '--set', f'tags.plant_id={plant_id}',
            '--set', f'tags.circuit_id={circuit_id}',
            '--query', 'name',
            '-o', 'tsv'
        ]
        
        if workspace_name:
            cmd.extend(['--workspace-name', workspace_name])
        if resource_group:
            cmd.extend(['--resource-group', resource_group])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            job_name = result.stdout.strip()
            submitted_jobs.append({
                'job_name': job_name,
                'plant_id': plant_id,
                'circuit_id': circuit_id,
                'cutoff_date': cutoff_date,
                'mltable_version': mltable_version,
                'training_hash': training_hash,
                'model_name': model_name,
                'model_type': circuit_cfg.get('model_type', 'custom_model')  # Default to custom_model
            })
            print(f"   ✅ Submitted: {job_name}")
        else:
            print(f"   ❌ Failed: {result.stderr}")
            failed_submissions.append({
                'plant_id': plant_id,
                'circuit_id': circuit_id,
                'error': result.stderr
            })
    
    print(f"\n{'='*60}")
    print(f"Submission Summary:")
    print(f"  ✅ Submitted: {len(submitted_jobs)}")
    print(f"  ❌ Failed: {len(failed_submissions)}")
    print(f"{'='*60}\n")
    
    return {
        'submitted_jobs': submitted_jobs,
        'failed_submissions': failed_submissions
    }


def main():
    parser = argparse.ArgumentParser(
        description="Submit training jobs for circuits with new MLTable registrations"
    )
    parser.add_argument(
        '--output',
        default='training_jobs.json',
        help='Output JSON file (default: training_jobs.json)'
    )
    parser.add_argument(
        '--pipeline-file',
        default='pipelines/single-circuit-training.yaml',
        help='Training pipeline YAML file'
    )
    parser.add_argument(
        '--workspace-name',
        help='Azure ML workspace name'
    )
    parser.add_argument(
        '--resource-group',
        help='Resource group name'
    )
    
    args = parser.parse_args()
    
    try:
        result = submit_training_jobs(
            workspace_name=args.workspace_name,
            resource_group=args.resource_group,
            pipeline_file=args.pipeline_file
        )
        
        # Save job info
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        
        if result['submitted_jobs']:
            print(f"✅ Training jobs submitted successfully")
            print(f"Saved to {args.output}")
            return 0
        else:
            print(f"ℹ️  No training jobs submitted")
            return 0
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
