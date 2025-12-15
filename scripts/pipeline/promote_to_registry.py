#!/usr/bin/env python3
"""
Promote Models to Azure ML Registry

Promote registered models from workspace to central registry.

Usage:
    python scripts/pipeline/promote_to_registry.py \
        --registered-models registered_models.json \
        --subscription-id <sub_id> \
        --resource-group <rg> \
        --workspace-name <workspace> \
        --registry-name <registry> \
        --registry-resource-group <registry_rg>
"""

import argparse
import json
import subprocess
import sys


def promote_to_registry(
    models_file: str,
    subscription_id: str,
    resource_group: str,
    workspace_name: str,
    registry_name: str,
    registry_resource_group: str
) -> dict:
    """
    Promote models to registry.
    
    Returns:
        Dict with promoted and failed models
    """
    with open(models_file, 'r') as f:
        data = json.load(f)
    
    models = data.get('models', [])
    
    if not models:
        print("ℹ️  No models to promote")
        return {'promoted': [], 'failed': []}
    
    print(f"🚀 Promoting {len(models)} model(s) to Registry...\n")
    
    promoted = []
    failed = []
    
    for model in models:
        model_name = model['model_name']
        model_version = model['version']
        plant_id = model['plant_id']
        circuit_id = model['circuit_id']
        cutoff_date = model['cutoff_date']
        training_hash = model.get('training_hash', model.get('config_hash'))  # Backward compat
        
        print(f"📦 Promoting: {model_name}:v{model_version}")
        
        # Check if already exists in registry
        check_cmd = [
            'az', 'ml', 'model', 'show',
            '--name', model_name,
            '--version', model_version,
            '--registry-name', registry_name,
            '--resource-group', registry_resource_group
        ]
        
        check_result = subprocess.run(check_cmd, capture_output=True)
        
        if check_result.returncode == 0:
            print(f"   ℹ️  Already exists in registry, skipping")
            promoted.append({
                'model_name': model_name,
                'version': model_version,
                'status': 'already_exists'
            })
            continue
        
        # Build model URI from workspace
        model_uri = f"azureml://subscriptions/{subscription_id}/resourceGroups/{resource_group}/workspaces/{workspace_name}/models/{model_name}/versions/{model_version}"
        
        # Promote to registry using model URI
        promote_cmd = [
            'az', 'ml', 'model', 'create',
            '--name', model_name,
            '--version', model_version,
            '--path', model_uri,  # Reference from workspace
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
            
            # Verify model in registry
            verify_result = subprocess.run(check_cmd, capture_output=True)
            if verify_result.returncode == 0:
                print(f"   ✅ Verified in registry")
            else:
                print(f"   ⚠️  Promoted but verification failed")
            
            promoted.append({
                'model_name': model_name,
                'version': model_version,
                'training_hash': training_hash,
                'status': 'promoted'
            })
        else:
            print(f"   ❌ Failed: {result.stderr}")
            failed.append({
                'model_name': model_name,
                'version': model_version,
                'error': result.stderr
            })
    
    print(f"\n{'='*60}")
    print(f"Promotion Summary:")
    print(f"  ✅ Promoted: {len([p for p in promoted if p['status'] == 'promoted'])}")
    print(f"  ℹ️  Already existed: {len([p for p in promoted if p['status'] == 'already_exists'])}")
    print(f"  ❌ Failed: {len(failed)}")
    print(f"{'='*60}\n")
    
    return {'promoted': promoted, 'failed': failed}


def main():
    parser = argparse.ArgumentParser(
        description="Promote models to registry"
    )
    parser.add_argument(
        '--registered-models',
        required=True,
        help='Path to registered models JSON file'
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
        '--registry-name',
        required=True,
        help='Azure ML registry name'
    )
    parser.add_argument(
        '--registry-resource-group',
        required=True,
        help='Registry resource group name'
    )
    parser.add_argument(
        '--output',
        default='promotion_result.json',
        help='Output JSON file (default: promotion_result.json)'
    )
    
    args = parser.parse_args()
    
    try:
        result = promote_to_registry(
            models_file=args.registered_models,
            subscription_id=args.subscription_id,
            resource_group=args.resource_group,
            workspace_name=args.workspace_name,
            registry_name=args.registry_name,
            registry_resource_group=args.registry_resource_group
        )
        
        # Save result
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        
        if result['failed']:
            print(f"⚠️  {len(result['failed'])} model(s) failed to promote")
            return 1
        
        print(f"✅ Model promotion complete")
        print(f"Saved to {args.output}")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
