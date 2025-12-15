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


def submit_training_jobs(
    circuits_file: str,
    pipeline_file: str,
    workspace_name: str = None,
    resource_group: str = None
) -> dict:
    """
    Submit training jobs for changed circuits.
    
    Returns:
        Dict with submitted_jobs and failed_submissions lists
    """
    with open(circuits_file, 'r') as f:
        changed = json.load(f)
    
    circuits = changed.get('circuits', [])
    
    if not circuits:
        print("ℹ️  No circuits to train")
        return {'submitted_jobs': [], 'failed_submissions': []}
    
    print(f"🚀 Submitting training jobs for {len(circuits)} circuit(s)...\n")
    
    submitted_jobs = []
    failed_submissions = []
    
    for circuit in circuits:
        plant_id = circuit['plant_id']
        circuit_id = circuit['circuit_id']
        cutoff_date = circuit.get('cutoff_date', '')
        
        print(f"\n📊 Submitting training job: {plant_id}_{circuit_id}")
        
        circuit_config = f'config/circuits/{plant_id}_{circuit_id}.yaml'
        
        # Query for latest MLTable version with matching tags
        data_name = f"{plant_id}_{circuit_id}"
        
        with open(circuit_config, 'r') as cf:
            circuit_cfg = yaml.safe_load(cf)
        
        features = circuit_cfg.get('features', [])
        feature_str = ','.join(sorted(features))
        feature_hash = hashlib.md5(feature_str.encode()).hexdigest()[:8]
        
        query_cmd = [
            'az', 'ml', 'data', 'list',
            '--name', data_name,
            '--query',
            f"[?tags.cutoff_date=='{cutoff_date}' && tags.feature_hash=='{feature_hash}'] | [-1].version",
            '-o', 'tsv'
        ]
        
        if workspace_name:
            query_cmd.extend(['--workspace-name', workspace_name])
        if resource_group:
            query_cmd.extend(['--resource-group', resource_group])
        
        query_result = subprocess.run(query_cmd, capture_output=True, text=True)
        
        if query_result.returncode != 0 or not query_result.stdout.strip():
            print(f"   ❌ ERROR: No MLTable found")
            failed_submissions.append({
                'plant_id': plant_id,
                'circuit_id': circuit_id,
                'error': 'MLTable not found'
            })
            continue
        
        data_version = query_result.stdout.strip()
        mltable_uri = f"azureml:{data_name}:{data_version}"
        
        print(f"   Found MLTable: {data_name}:v{data_version}")
        
        timestamp = cutoff_date.replace('-', '_').replace(':', '_')
        job_name = f"{plant_id}_{circuit_id}_{timestamp}_v{data_version}"
        
        print(f"   Job: {job_name}")
        
        cmd = [
            'az', 'ml', 'job', 'create',
            '--file', pipeline_file,
            '--name', job_name,
            '--set', f'inputs.circuit_config.path={circuit_config}',
            '--set', f'inputs.training_data.path={mltable_uri}',
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
                'model_name': circuit.get('model_name', f'{plant_id.lower()}-{circuit_id.lower()}')
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
        description="Submit training jobs for changed circuits"
    )
    parser.add_argument(
        '--changed-circuits',
        required=True,
        help='Path to changed circuits JSON file'
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
            circuits_file=args.changed_circuits,
            pipeline_file=args.pipeline_file,
            workspace_name=args.workspace_name,
            resource_group=args.resource_group
        )
        
        # Save job info
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        
        if result['submitted_jobs']:
            print(f"✅ Training jobs submitted successfully")
            print(f"Saved to {args.output}")
            return 0
        else:
            print(f"⚠️  No training jobs submitted")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
