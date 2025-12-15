#!/usr/bin/env python3
"""
Load Circuits and Register MLTable Data Assets

This script:
1. Loads circuits from config (all or manual selection)
2. Generates MLTable YAML files for each circuit
3. Registers MLTable data assets in Azure ML workspace with hash-based change detection
4. Outputs list of circuits that were registered (have new config hash)

The hash includes: features + cutoff_date + delta_version
If hash matches existing MLTable → Skip registration
If hash is new → Register new MLTable version

Usage:
    python scripts/pipeline/detect_changed_circuits.py \
        --config config/circuits.yaml \
        --output changed_circuits.json \
        --manual-circuits "PLANT001_CIRCUIT01,PLANT001_CIRCUIT02"
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import yaml
from pathlib import Path
from typing import List, Dict


def load_circuits_to_process(
    config_path: str,
    manual_circuits: str = None
) -> List[Dict]:
    """
    Load circuits to process from config.
    
    Note: This doesn't detect "changes" - that happens in register_mltables()
    via hash comparison. This just loads which circuits to consider.
    
    Strategy:
    - Manual override: Use specified circuits (highest priority)
    - Default: Load all circuits from config
    - Hash-based check in register_mltables() determines what actually changed
    
    Args:
        config_path: Path to circuits.yaml
        manual_circuits: Comma-separated list (format: PLANT_CIRCUIT)
    
    Returns:
        List of circuit configurations to process
    """
    print("� Loading circuits to process...\n")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    all_circuits = config.get('circuits', [])
    
    if not all_circuits:
        print("❌ No circuits found in config")
        return []
    
    # Priority 1: Manual circuit specification (explicit override)
    if manual_circuits and manual_circuits.strip():
        print(f"📋 Manual circuit specification: {manual_circuits}")
        print(f"   (Overriding default)")
        manual_list = [c.strip() for c in manual_circuits.split(',')]
        circuits = [
            c for c in all_circuits
            if f"{c['plant_id']}_{c['circuit_id']}" in manual_list
        ]
        print(f"   Selected {len(circuits)} circuit(s)\n")
        return circuits
    
    # Priority 2: Load all circuits (hash check will determine what changed)
    print(f"📋 Loading all {len(all_circuits)} circuits from config")
    print(f"   Hash comparison will identify which need new MLTable versions\n")
    
    return all_circuits


def register_mltables(
    circuits: List[Dict],
    workspace_name: str = None,
    resource_group: str = None
) -> List[Dict]:
    """
    Register MLTable data assets for circuits.
    
    Args:
        circuits: List of circuit configurations
        workspace_name: Azure ML workspace name
        resource_group: Resource group name
    
    Returns:
        List of successfully registered circuits
    """
    if not circuits:
        print("ℹ️  No circuits to process")
        return []
    
    print(f"📊 Processing {len(circuits)} circuit(s)...\n")
    
    changed_circuits = []
    failed = False
    
    for circuit in circuits:
        plant_id = circuit['plant_id']
        circuit_id = circuit['circuit_id']
        cutoff_date = circuit.get('cutoff_date', '')
        delta_version = circuit.get('delta_version')
        
        print("=" * 60)
        print(f"Circuit: {plant_id}_{circuit_id}")
        print(f"Cutoff Date: {cutoff_date}")
        print(f"Delta Version: {delta_version}")
        
        # Load circuit-specific config for features
        circuit_config_path = f'config/circuits/{plant_id}_{circuit_id}.yaml'
        if not os.path.exists(circuit_config_path):
            print(f"❌ Circuit config not found: {circuit_config_path}")
            failed = True
            continue
        
        with open(circuit_config_path, 'r') as cf:
            circuit_cfg = yaml.safe_load(cf)
        
        # Get all configuration elements that should trigger retraining
        features = circuit_cfg.get('features', [])
        feature_str = ','.join(sorted(features))
        
        # Calculate MLTable configuration hash
        # Only includes DATA-related parameters:
        # - Features (what data columns)
        # - Cutoff date (data filtering)  
        # - Delta version (data snapshot)
        # 
        # Does NOT include:
        # - Environment version (code, not data)
        # - Hyperparameters (training config, not data)
        config_str = f"{feature_str}|{cutoff_date}|{delta_version}"
        config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]
        
        print(f"Config hash: {config_hash}")
        print(f"  - Features: {len(features)}")
        print(f"  - Cutoff date: {cutoff_date}")
        print(f"  - Delta version: {delta_version}")

        
        data_name = f"{plant_id}_{circuit_id}"
        
        # Check if MLTable with same config hash already exists
        check_cmd = [
            'az', 'ml', 'data', 'list',
            '--name', data_name,
            '--query',
            f"[?tags.config_hash=='{config_hash}'].{{version:version,config_hash:tags.config_hash,cutoff_date:tags.cutoff_date,delta_version:tags.delta_version}}",
            '-o', 'json'
        ]
        
        if workspace_name:
            check_cmd.extend(['--workspace-name', workspace_name])
        if resource_group:
            check_cmd.extend(['--resource-group', resource_group])
        
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if check_result.returncode == 0 and check_result.stdout.strip() not in ['[]', '']:
            try:
                existing = json.loads(check_result.stdout.strip())
                if existing:
                    existing_version = existing[0]['version']
                    print(f"✅ MLTable {data_name}:v{existing_version} already exists with same config. Skipping.\n")
                    # Don't append to changed_circuits - no change detected!
                    continue
            except json.JSONDecodeError:
                pass
        
        # Check generated MLTable file exists locally
        mltable_local_dir = f"mltables/{plant_id}_{circuit_id}"
        
        if not os.path.exists(f"{mltable_local_dir}/MLTable"):
            print(f"❌ MLTable file not found: {mltable_local_dir}/MLTable")
            failed = True
            continue
        
        # Register ML Table data asset with tags
        print(f"📊 Registering new MLTable version with tags...")
        
        tag_args = [
            '--set', f'tags.cutoff_date={cutoff_date}',
            '--set', f'tags.config_hash={config_hash}',
            '--set', f'tags.plant_id={plant_id}',
            '--set', f'tags.circuit_id={circuit_id}',
            '--set', f'tags.features={feature_str}'  # Add features list
        ]
        
        if delta_version is not None:
            tag_args.extend(['--set', f'tags.delta_version={delta_version}'])
        
        if features:
            tag_args.extend(['--set', f'tags.num_features={len(features)}'])
        
        create_cmd = [
            'az', 'ml', 'data', 'create',
            '--name', data_name,
            '--type', 'mltable',
            '--path', mltable_local_dir,
            '-o', 'json'
        ] + tag_args
        
        if workspace_name:
            create_cmd.extend(['--workspace-name', workspace_name])
        if resource_group:
            create_cmd.extend(['--resource-group', resource_group])
        
        result = subprocess.run(create_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f'❌ Failed to register {data_name}')
            print(f'   Error: {result.stderr}')
            failed = True
            continue
        
        # Parse version from response
        data_info = json.loads(result.stdout)
        data_version = data_info.get('version', 'unknown')
        
        print(f'✅ Registered: {data_name}:v{data_version}')
        print(f'   Tags: config_hash={config_hash}, cutoff_date={cutoff_date}, delta_version={delta_version}')
        print(f'   Features ({len(features)}): {feature_str[:100]}{"..." if len(feature_str) > 100 else ""}\n')
        
        # Only append circuits where we REGISTERED a new MLTable (config changed)
        # Minimal output - just what's needed for training submission
        changed_circuits.append({
            'plant_id': plant_id,
            'circuit_id': circuit_id,
            'mltable_name': data_name,
            'mltable_version': data_version,
            'mltable_uri': f"azureml:{data_name}:{data_version}"
        })
    
    print("=" * 60)
    print(f"Summary:")
    print(f"  📊 Processed: {len(circuits)}")
    print(f"  ✅ New MLTables registered: {len(changed_circuits)}")
    print(f"  ⏭️  Skipped (no config change): {len(circuits) - len(changed_circuits)}")
    print("=" * 60)
    
    if failed:
        raise RuntimeError("Some MLTable registrations failed")
    
    return changed_circuits


def main():
    parser = argparse.ArgumentParser(
        description="Load circuits and register MLTables with hash-based change detection"
    )
    parser.add_argument(
        '--config',
        default='config/circuits.yaml',
        help='Path to circuits configuration (default: config/circuits.yaml)'
    )
    parser.add_argument(
        '--workspace-name',
        help='Azure ML workspace name'
    )
    parser.add_argument(
        '--resource-group',
        help='Resource group name'
    )
    parser.add_argument(
        '--manual-circuits',
        help='Comma-separated list of circuits (format: PLANT_CIRCUIT)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load circuits to process
        circuits = load_circuits_to_process(
            config_path=args.config,
            manual_circuits=args.manual_circuits
        )
        
        # Register MLTables (with hash-based change detection)
        # Returns list of circuits where new MLTable was registered
        registered_circuits = register_mltables(
            circuits=circuits,
            workspace_name=args.workspace_name,
            resource_group=args.resource_group
        )
        
        if registered_circuits:
            print(f"\n✅ MLTable registration complete")
            print(f"   {len(registered_circuits)} circuit(s) registered with new config")
            print(f"\n💡 Next stage will query Azure ML for these MLTables")
            return 0
        else:
            print(f"\nℹ️  No new MLTables registered (all configs unchanged)")
            return 0
            
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
