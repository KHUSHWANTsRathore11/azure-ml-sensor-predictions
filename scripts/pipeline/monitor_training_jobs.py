#!/usr/bin/env python3
"""
Monitor Training Jobs

Waits for training jobs to complete and reports status.

Usage:
    python scripts/pipeline/monitor_training_jobs.py \
        --training-jobs training_jobs.json \
        --subscription-id <sub_id> \
        --resource-group <rg> \
        --workspace-name <workspace>
"""

import argparse
import json
import sys
import time
from azure.identity import DefaultAzureCredential
from azure.ai.ml import MLClient


def monitor_training_jobs(
    jobs_file: str,
    subscription_id: str,
    resource_group: str,
    workspace_name: str,
    poll_interval: int = 30
) -> dict:
    """
    Monitor training jobs until completion.
    
    Returns:
        Dict with completed, failed, and pending job lists
    """
    with open(jobs_file, 'r') as f:
        data = json.load(f)
    
    submitted_jobs = data.get('submitted_jobs', [])
    
    if not submitted_jobs:
        print("ℹ️  No jobs to wait for")
        return {'completed': [], 'failed': [], 'pending': []}
    
    job_names = [job['job_name'] for job in submitted_jobs]
    
    print(f"📊 Waiting for {len(job_names)} training job(s)...\n")
    
    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name
    )
    
    pending = set(job_names)
    completed = []
    failed = []
    
    poll_count = 0
    while pending:
        poll_count += 1
        
        for job_name in list(pending):
            try:
                job = ml_client.jobs.get(job_name)
                status = job.status
                
                if status in ['Completed']:
                    print(f"✅ {job_name}: {status}")
                    completed.append(job_name)
                    pending.remove(job_name)
                elif status in ['Failed', 'Canceled']:
                    print(f"❌ {job_name}: {status}")
                    failed.append(job_name)
                    pending.remove(job_name)
                elif poll_count % 10 == 0:
                    print(f"⏳ {job_name}: {status}")
            
            except Exception as e:
                print(f"⚠️  Error checking {job_name}: {e}")
        
        if pending:
            time.sleep(poll_interval)
    
    print(f"\n{'='*60}")
    print(f"Training Summary:")
    print(f"  ✅ Completed: {len(completed)}")
    print(f"  ❌ Failed: {len(failed)}")
    print(f"{'='*60}\n")
    
    return {
        'completed': completed,
        'failed': failed,
        'submitted_jobs': submitted_jobs
    }


def main():
    parser = argparse.ArgumentParser(
        description="Monitor training jobs until completion"
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
        '--poll-interval',
        type=int,
        default=30,
        help='Poll interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--output',
        default='monitoring_result.json',
        help='Output JSON file (default: monitoring_result.json)'
    )
    
    args = parser.parse_args()
    
    try:
        result = monitor_training_jobs(
            jobs_file=args.training_jobs,
            subscription_id=args.subscription_id,
            resource_group=args.resource_group,
            workspace_name=args.workspace_name,
            poll_interval=args.poll_interval
        )
        
        # Save result
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        
        if not result['completed']:
            print("❌ No jobs completed successfully")
            return 1
        
        if result['failed']:
            print(f"⚠️  {len(result['failed'])} job(s) failed")
        
        print(f"✅ Training monitoring complete")
        print(f"Saved to {args.output}")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
