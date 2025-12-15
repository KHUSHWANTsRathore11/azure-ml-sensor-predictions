#!/usr/bin/env python3
"""
Detect Changed Circuits and Register MLTable Data Assets

This script:
1. Detects which circuits have changed (based on git diff or manual selection)
2. Generates MLTable YAML files for each circuit
3. Registers MLTable data assets in Azure ML workspace with tags

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


def detect_changed_circuits(
    config_path: str,
    manual_circuits: str = None
) -> List[Dict]:
    """
    Detect which circuits need MLTable registration.
    
    Args:
        config_path: Path to circuits.yaml
        manual_circuits: Comma-separated list of circuits (plant_circuit format)
    
    Returns:
        List of circuit configurations
    """
    print("🔍 Detecting changed circuits...\n")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    circuits = config.get('circuits', [])
    
    if not circuits:
        print("❌ No circuits found in config")
        return []
    
    # Check for manual circuit specification
    if manual_circuits and manual_circuits.strip():
        print(f"📋 Manual circuit specification: {manual_circuits}")
        manual_list = [c.strip() for c in manual_circuits.split(',')]
        circuits = [
            c for c in circuits
            if f"{c['plant_id']}_{c['circuit_id']}" in manual_list
        ]
        print(f"   Selected {len(circuits)} circuit(s)\n")
    else:
        # TODO: Implement git diff-based change detection
        print("📋 Using all circuits from config\n")
    
    return circuits


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
        
        features = circuit_cfg.get('features', [])
        feature_str = ','.join(sorted(features))
        feature_hash = hashlib.md5(feature_str.encode()).hexdigest()[:8]
        
        print(f"Feature hash: {feature_hash} ({len(features)} features)")
        
        data_name = f"{plant_id}_{circuit_id}"
        
        # Check if MLTable with same tags already exists
        check_cmd = [
            'az', 'ml', 'data', 'list',
            '--name', data_name,
            '--query',
            f"[?tags.cutoff_date=='{cutoff_date}' && tags.feature_hash=='{feature_hash}'].{{version:version,cutoff_date:tags.cutoff_date,feature_hash:tags.feature_hash}}",
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
                    print(f"✅ MLTable {data_name}:v{existing_version} already exists with same cutoff_date and features. Skipping.\n")
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
            '--set', f'tags.feature_hash={feature_hash}',
            '--set', f'tags.plant_id={plant_id}',
            '--set', f'tags.circuit_id={circuit_id}'
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
        print(f'   Tags: cutoff_date={cutoff_date}, delta_version={delta_version}, feature_hash={feature_hash}, num_features={len(features)}\n')
        
        changed_circuits.append(circuit)
    
    print("=" * 60)
    print(f"Summary:")
    print(f"  📊 Processed: {len(circuits)}")
    print(f"  ✅ Registered/Reused: {len(changed_circuits)}")
    print("=" * 60)
    
    if failed:
        raise RuntimeError("Some MLTable registrations failed")
    
    return changed_circuits


def main():
    parser = argparse.ArgumentParser(
        description="Detect changed circuits and register MLTables"
    )
    parser.add_argument(
        '--config',
        default='config/circuits.yaml',
        help='Path to circuits configuration (default: config/circuits.yaml)'
    )
    parser.add_argument(
        '--output',
        default='changed_circuits.json',
        help='Output JSON file (default: changed_circuits.json)'
    )
    parser.add_argument(
        '--manual-circuits',
        help='Comma-separated list of circuits (format: PLANT_CIRCUIT)'
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
        # Detect circuits
        circuits = detect_changed_circuits(
            config_path=args.config,
            manual_circuits=args.manual_circuits
        )
        
        # Register MLTables
        changed_circuits = register_mltables(
            circuits=circuits,
            workspace_name=args.workspace_name,
            resource_group=args.resource_group
        )
        
        # Save to file
        output_data = {'circuits': changed_circuits}
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        if changed_circuits:
            print(f"\n✅ MLTable registration complete")
            print(f"Saved to {args.output}")
        else:
            print(f"\nℹ️  No new MLTables to register")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
