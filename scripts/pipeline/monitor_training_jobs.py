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
    poll_interval: int = 30,
    max_wait_hours: int = 3
) -> dict:
    """
    Monitor training jobs until completion.
    
    Args:
        max_wait_hours: Maximum time to wait before timeout (default: 3 hours)
    
    Returns:
        Dict with completed, failed, timeout, and pending job lists
    """
    with open(jobs_file, 'r') as f:
        data = json.load(f)
    
    submitted_jobs = data.get('submitted_jobs', [])
    
    if not submitted_jobs:
        print("ℹ️  No jobs to monitor")
        return {'completed': [], 'failed': [], 'timeout': [], 'submitted_jobs': []}
    
    print(f"📊 Monitoring {len(submitted_jobs)} training job(s)...\n")
    print(f"⏱️  Max wait time: {max_wait_hours} hours")
    print(f"� Poll interval: {poll_interval} seconds\n")
    
    # Create job lookup map to preserve metadata
    job_map = {job['job_name']: job for job in submitted_jobs}
    
    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name
    )
    
    pending_job_names = set(job['job_name'] for job in submitted_jobs)
    completed = []
    failed = []
    timeout_jobs = []
    
    start_time = time.time()
    max_wait_seconds = max_wait_hours * 3600
    poll_count = 0
    
    while pending_job_names:
        poll_count += 1
        elapsed_seconds = time.time() - start_time
        
        # Check timeout
        if elapsed_seconds > max_wait_seconds:
            print(f"\n⏳ TIMEOUT after {max_wait_hours} hours")
            print(f"   {len(pending_job_names)} job(s) still pending\n")
            
            # Mark pending jobs as timeout
            for job_name in pending_job_names:
                timeout_jobs.append(job_map[job_name])
            
            break
        
        # Poll each pending job
        for job_name in list(pending_job_names):
            try:
                job = ml_client.jobs.get(job_name)
                status = job.status
                
                if status in ['Completed']:
                    print(f"✅ {job_name}: {status}")
                    completed.append(job_map[job_name])
                    pending_job_names.remove(job_name)
                    
                elif status in ['Failed', 'Canceled']:
                    print(f"❌ {job_name}: {status}")
                    failed.append(job_map[job_name])
                    pending_job_names.remove(job_name)
                    
                elif poll_count % 10 == 0:
                    # Show status for running jobs every 10 polls
                    print(f"⏳ {job_name}: {status}")
            
            except Exception as e:
                print(f"⚠️  Error checking {job_name}: {e}")
        
        # Progress summary every 10 polls
        if poll_count % 10 == 0:
            elapsed_min = elapsed_seconds / 60
            remaining_min = (max_wait_seconds - elapsed_seconds) / 60
            
            print(f"\n{'='*60}")
            print(f"Progress Update (Poll #{poll_count})")
            print(f"  ⏱️  Elapsed: {elapsed_min:.1f} minutes")
            print(f"  ⏳ Remaining: {remaining_min:.1f} minutes")
            print(f"  ✅ Completed: {len(completed)}")
            print(f"  ❌ Failed: {len(failed)}")
            print(f"  🔄 Pending: {len(pending_job_names)}")
            print(f"{'='*60}\n")
        
        # Early exit if all jobs finished (success or failure)
        if not pending_job_names:
            print("✅ All jobs finished\n")
            break
        
        # Early exit if everything failed and nothing pending
        if failed and not completed and len(pending_job_names) == len(submitted_jobs):
            print("❌ All jobs have failed or are failing, but will continue monitoring...\n")
        
        # Sleep before next poll
        if pending_job_names:
            time.sleep(poll_interval)
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"Training Monitoring Summary:")
    print(f"  Total jobs: {len(submitted_jobs)}")
    print(f"  ✅ Completed: {len(completed)}")
    print(f"  ❌ Failed: {len(failed)}")
    print(f"  ⏳ Timeout: {len(timeout_jobs)}")
    print(f"  ⏱️  Total time: {(time.time() - start_time) / 60:.1f} minutes")
    print(f"{'='*60}\n")
    
    return {
        'completed': completed,
        'failed': failed,
        'timeout': timeout_jobs,
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
        '--max-wait-hours',
        type=int,
        default=3,
        help='Maximum hours to wait before timeout (default: 3)'
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
            poll_interval=args.poll_interval,
            max_wait_hours=args.max_wait_hours
        )
        
        # Save result
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"✅ Monitoring complete")
        print(f"Saved to {args.output}\n")
        
        # Success if any jobs completed
        if result['completed']:
            if result['failed'] or result['timeout']:
                print(f"⚠️  Partial success: {len(result['failed'])} failed, {len(result['timeout'])} timeout")
            return 0
        
        # All failed or timeout
        if result['failed'] or result['timeout']:
            print(f"❌ No jobs completed successfully")
            return 1
        
        # No jobs submitted
        print(f"ℹ️  No jobs to monitor")
        return 0

        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
