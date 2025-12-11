#!/usr/bin/env python3
"""
Generate individual circuit configuration files from circuits.yaml.

This script reads the master circuits.yaml and creates individual
config files for each circuit in config/circuits/ directory.
Each config includes a deterministic hash for tracking model lineage.

Usage:
    python scripts/generate_circuit_configs.py
"""

import yaml
import os
import hashlib
from datetime import datetime
from pathlib import Path


def generate_config_hash(config_dict: dict) -> str:
    """
    Generate deterministic hash from configuration dictionary.
    
    This hash captures all configuration parameters that affect model training,
    including cutoff_date, hyperparameters, features, etc.
    
    Args:
        config_dict: Circuit configuration dictionary
    
    Returns:
        12-character hexadecimal hash string
    """
    # Create a copy without metadata (to avoid circular dependency)
    config_copy = {k: v for k, v in config_dict.items() if k != 'metadata'}
    
    # Convert to deterministic YAML string (sorted keys)
    config_str = yaml.dump(config_copy, sort_keys=True, default_flow_style=False)
    
    # Generate MD5 hash and truncate to 12 characters
    hash_obj = hashlib.md5(config_str.encode('utf-8'))
    return hash_obj.hexdigest()[:12]


def generate_circuit_configs(circuits_yaml_path: str, output_dir: str):
    """
    Generate individual circuit config files.
    
    Args:
        circuits_yaml_path: Path to master circuits.yaml
        output_dir: Directory to output individual configs
    """
    # Load master config
    with open(circuits_yaml_path, 'r') as f:
        master_config = yaml.safe_load(f)
    
    circuits = master_config.get('circuits', [])
    
    if not circuits:
        print("⚠️  No circuits found in circuits.yaml")
        return
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Creating circuit configs in: {output_dir}\n")
    
    # Generate individual files
    for circuit in circuits:
        plant_id = circuit['plant_id']
        circuit_id = circuit['circuit_id']
        
        # Generate config hash before adding metadata
        config_hash = generate_config_hash(circuit)
        
        # Add metadata section with hash and generation timestamp
        circuit['metadata'] = {
            'config_hash': config_hash,
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'description': 'Deterministic hash of circuit configuration for model tracking'
        }
        
        # Filename: PLANT001_CIRCUIT01.yaml
        filename = f"{plant_id}_{circuit_id}.yaml"
        filepath = output_path / filename
        
        # Write individual config
        with open(filepath, 'w') as f:
            yaml.dump(circuit, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Created: {filename} (hash: {config_hash})")
    
    print(f"\n✅ Generated {len(circuits)} circuit configuration files")
    print(f"📂 Location: {output_dir}")


def main():
    # Paths
    circuits_yaml = "config/circuits.yaml"
    output_directory = "config/circuits"
    
    if not os.path.exists(circuits_yaml):
        print(f"❌ File not found: {circuits_yaml}")
        return 1
    
    generate_circuit_configs(circuits_yaml, output_directory)
    return 0


if __name__ == "__main__":
    exit(main())
