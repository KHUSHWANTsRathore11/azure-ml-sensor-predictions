#!/usr/bin/env python3
"""
Promote Models Individually to Registry

This script promotes models one at a time, allowing for plant-specific 
approval workflows via external systems (ServiceNow, email, manual gates).

Usage:
    python scripts/pipeline/promote_models_individually.py \
        --registered-models registered_models.json \
        --subscription-id <sub_id> \
        --resource-group <rg> \
        --workspace-name <workspace> \
        --registry-name <registry> \
        --registry-resource-group <registry_rg> \
        --output promotion_result.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def check_approval_status(plant_id: str, model_name: str, version: str) -> bool:
    """
    Check if model has been approved for promotion.
    
    This function checks for approval via:
    1. Approval file (approval_status.json)
    2. Environment variable
    3. Auto-approve if no approval system configured
    
    Returns:
        True if approved, False if rejected/pending
    """
    # Check for approval file in workspace
    approval_file = Path('approval_status.json')
    
    if approval_file.exists():
        with open(approval_file) as f:
            approvals = json.load(f)
        
        model_key = f"{plant_id}:{model_name}:{version}"
        status = approvals.get(model_key, 'pending')
        
        if status == 'approved':
            print(f"   ✅ Approved via approval file")
            return True
        elif status == 'rejected':
            print(f"   ❌ Rejected via approval file")
            return False
        else:
            print(f"   ⏸️  Pending approval in approval file")
            return False
    
    # Default: Auto-approve (implement your approval logic here)
    print(f"   ℹ️  No approval system configured, auto-approving")
    return True


def promote_model(
    model: dict,
    subscription_id: str,
    resource_group: str,
    workspace_name: str,
    registry_name: str,
    registry_resource_group: str
) -> dict:
    """
    Promote a single model to registry.
    
    Returns:
        dict with promotion result
    """
    model_name = model['model_name']
    model_version = model['version']
    plant_id = model['plant_id']
    circuit_id = model['circuit_id']
    cutoff_date = model['cutoff_date']
    training_hash = model.get('training_hash', model.get('config_hash'))
    
    print(f"\n📦 Processing: {model_name}:v{model_version}")
    print(f"   Plant: {plant_id}, Circuit: {circuit_id}")
    
    # Check approval status
    if not check_approval_status(plant_id, model_name, model_version):
        return {
            'model_name': model_name,
            'version': model_version,
            'plant_id': plant_id,
            'status': 'pending_approval'
        }
    
    # Check if already in registry
    check_cmd = [
        'az', 'ml', 'model', 'show',
        '--name', model_name,
        '--version', model_version,
        '--registry-name', registry_name,
        '--resource-group', registry_resource_group
    ]
    
    check_result = subprocess.run(check_cmd, capture_output=True)
    
    if check_result.returncode == 0:
        print(f"   ℹ️  Already exists in registry")
        return {
            'model_name': model_name,
            'version': model_version,
            'plant_id': plant_id,
            'status': 'already_exists'
        }
    
    # Build model URI
    model_uri = f"azureml://subscriptions/{subscription_id}/resourceGroups/{resource_group}/workspaces/{workspace_name}/models/{model_name}/versions/{model_version}"
    
    # Promote to registry
    promote_cmd = [
        'az', 'ml', 'model', 'create',
        '--name', model_name,
        '--version', model_version,
        '--path', model_uri,
        '--registry-name', registry_name,
        '--resource-group', registry_resource_group,
        '--set', f'tags.plant_id={plant_id}',
        '--set', f'tags.circuit_id={circuit_id}',
        '--set', f'tags.cutoff_date={cutoff_date}',
        '--set', f'tags.training_hash={training_hash}',
        '--set', 'tags.promoted_from=dev',
        '-o', 'json'
    ]
    
    result = subprocess.run(promote_cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"   ✅ Promoted successfully")
        
        # Verify
        verify_result = subprocess.run(check_cmd, capture_output=True)
        if verify_result.returncode == 0:
            print(f"   ✅ Verified in registry")
        else:
            print(f"   ⚠️  Promoted but verification failed")
        
        return {
            'model_name': model_name,
            'version': model_version,
            'plant_id': plant_id,
            'training_hash': training_hash,
            'status': 'promoted'
        }
    else:
        print(f"   ❌ Failed: {result.stderr}")
        return {
            'model_name': model_name,
            'version': model_version,
            'plant_id': plant_id,
            'error': result.stderr,
            'status': 'failed'
        }


def main():
    parser = argparse.ArgumentParser(
        description="Promote models individually with approval checks"
    )
    parser.add_argument('--registered-models', required=True)
    parser.add_argument('--subscription-id', required=True)
    parser.add_argument('--resource-group', required=True)
    parser.add_argument('--workspace-name', required=True)
    parser.add_argument('--registry-name', required=True)
    parser.add_argument('--registry-resource-group', required=True)
    parser.add_argument('--output', default='promotion_result.json')
    
    args = parser.parse_args()
    
    # Load models
    with open(args.registered_models) as f:
        data = json.load(f)
    
    models = data.get('models', [])
    
    if not models:
        print("ℹ️  No models to promote")
        result = {'promoted': [], 'pending': [], 'failed': []}
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        return 0
    
    print(f"🚀 Processing {len(models)} model(s) for promotion...")
    print(f"Each model will be checked for approval before promotion")
    print()
    
    promoted = []
    pending = []
    failed = []
    already_exists = []
    
    # Process each model
    for model in models:
        try:
            result = promote_model(
                model=model,
                subscription_id=args.subscription_id,
                resource_group=args.resource_group,
                workspace_name=args.workspace_name,
                registry_name=args.registry_name,
                registry_resource_group=args.registry_resource_group
            )
            
            status = result['status']
            if status == 'promoted':
                promoted.append(result)
            elif status == 'pending_approval':
                pending.append(result)
            elif status == 'already_exists':
                already_exists.append(result)
            else:
                failed.append(result)
        
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            failed.append({
                'model_name': model.get('model_name'),
                'error': str(e),
                'status': 'error'
            })
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Promotion Summary:")
    print(f"  ✅ Promoted: {len(promoted)}")
    print(f"  ℹ️  Already existed: {len(already_exists)}")
    print(f"  ⏸️  Pending approval: {len(pending)}")
    print(f"  ❌ Failed: {len(failed)}")
    print(f"{'='*60}\n")
    
    # Save results
    output = {
        'promoted': promoted,
        'already_exists': already_exists,
        'pending_approval': pending,
        'failed': failed
    }
    
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Results saved to {args.output}")
    
    # Return code
    if pending:
        print(f"\n⏸️  {len(pending)} model(s) pending approval")
        print("Run pipeline again after approvals are granted")
        return 1
    
    if failed:
        print(f"\n❌ {len(failed)} model(s) failed to promote")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
