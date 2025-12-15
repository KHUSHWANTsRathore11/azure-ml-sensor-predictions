#!/usr/bin/env python3
"""
Validate circuits.yaml configuration file.

Validates that all circuits have required fields and proper formats.

Usage:
    python scripts/validation/validate_circuits.py --config config/circuits.yaml
"""

import argparse
import sys
import yaml
from typing import List, Dict


def validate_circuits(config_path: str) -> int:
    """
    Validate circuits configuration.
    
    Args:
        config_path: Path to circuits.yaml file
    
    Returns:
        0 if valid, 1 if invalid
    """
    print(f"📋 Validating circuits.yaml...")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        circuits = config.get('circuits', [])
        
        if not circuits:
            print("❌ No circuits found in config")
            return 1
        
        required_fields = [
            'plant_id',
            'circuit_id',
            'cutoff_date',
            'model_name',
            'delta_version'
        ]
        
        for i, circuit in enumerate(circuits):
            plant_id = circuit.get('plant_id', f'circuit_{i+1}')
            circuit_id = circuit.get('circuit_id', '')
            
            # Check required fields
            for field in required_fields:
                if field not in circuit:
                    print(f"❌ Circuit {plant_id}/{circuit_id}: missing required field '{field}'")
                    return 1
            
            # Validate cutoff_date format (YYYY-MM-DD)
            cutoff = circuit.get('cutoff_date', '')
            if len(cutoff) != 10 or cutoff[4] != '-' or cutoff[7] != '-':
                print(f"❌ Circuit {plant_id}/{circuit_id}: Invalid cutoff_date format. Expected YYYY-MM-DD")
                return 1
            
            # Validate delta_version is a non-negative integer
            delta_version = circuit.get('delta_version')
            if not isinstance(delta_version, int):
                print(f"❌ Circuit {plant_id}/{circuit_id}: delta_version must be an integer, got {type(delta_version).__name__}")
                return 1
            
            if delta_version < 0:
                print(f"❌ Circuit {plant_id}/{circuit_id}: delta_version must be >= 0, got {delta_version}")
                return 1
            
            print(f"   ✅ {plant_id}/{circuit_id}: cutoff_date={cutoff}, delta_version={delta_version}")
        
        print(f"\n✅ Validated {len(circuits)} circuits (all have valid delta_version)")
        return 0
    
    except yaml.YAMLError as e:
        print(f"❌ YAML syntax error: {e}")
        return 1
    except FileNotFoundError:
        print(f"❌ File not found: {config_path}")
        return 1
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Validate circuits configuration"
    )
    parser.add_argument(
        '--config',
        default='config/circuits.yaml',
        help='Path to circuits.yaml (default: config/circuits.yaml)'
    )
    
    args = parser.parse_args()
    return validate_circuits(args.config)


if __name__ == "__main__":
    sys.exit(main())
