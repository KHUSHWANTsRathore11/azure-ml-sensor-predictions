#!/usr/bin/env python3
"""
Validate component YAML files.

Usage:
    python scripts/validation/validate_components.py --components-dir components/
"""

import argparse
import sys
import yaml
from pathlib import Path


def validate_components(components_dir: str) -> int:
    """
    Validate component configuration files.
    
    Args:
        components_dir: Path to components directory
    
    Returns:
        0 if all valid, 1 if any invalid
    """
    print("📦 Validating component files...")
    
    components_path = Path(components_dir)
    
    if not components_path.exists():
        print(f"⚠️  Components directory not found: {components_dir}")
        return 0  # Not an error, just skip
    
    failed = False
    validated_count = 0
    
    # Validate component subdirectories
    for comp_file in components_path.glob("*/component.yaml"):
        print(f"Checking: {comp_file}")
        
        try:
            with open(comp_file, 'r') as f:
                comp = yaml.safe_load(f)
            
            required = ['name', 'version', 'type']
            for field in required:
                if field not in comp:
                    print(f"❌ Missing field: {field}")
                    failed = True
                    break
            else:
                print(f"✅ Valid: {comp['name']}:{comp['version']}")
                validated_count += 1
        
        except Exception as e:
            print(f"❌ Error: {e}")
            failed = True
    
    # Validate pipeline component
    pipeline_comp = components_path / "training-pipeline-component.yaml"
    if pipeline_comp.exists():
        print(f"Checking: {pipeline_comp}")
        
        try:
            with open(pipeline_comp, 'r') as f:
                comp = yaml.safe_load(f)
            
            if comp.get('type') != 'pipeline':
                print("❌ Pipeline component must have type: pipeline")
                failed = True
            else:
                print(f"✅ Valid: {comp['name']}:{comp['version']}")
                validated_count += 1
        
        except Exception as e:
            print(f"❌ Error: {e}")
            failed = True
    
    if failed:
        print("\n❌ Component validation failed")
        return 1
    
    print(f"\n✅ All {validated_count} component file(s) valid")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate component configuration files"
    )
    parser.add_argument(
        '--components-dir',
        default='components',
        help='Path to components directory (default: components)'
    )
    
    args = parser.parse_args()
    return validate_components(args.components_dir)


if __name__ == "__main__":
    sys.exit(main())
