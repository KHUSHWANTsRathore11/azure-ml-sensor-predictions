#!/usr/bin/env python3
"""
Validate pipeline compute references.

Checks that pipeline YAML files have valid compute references.

Usage:
    python scripts/validation/validate_pipeline_compute.py --pipelines-dir pipelines/
"""

import argparse
import sys
import yaml
from pathlib import Path


def validate_pipeline_compute(pipelines_dir: str) -> int:
    """
    Validate pipeline compute references.
    
    Args:
        pipelines_dir: Path to pipelines directory
    
    Returns:
        0 if valid, 1 if invalid
    """
    print("🔧 Validating pipeline compute references...")
    
    pipelines_path = Path(pipelines_dir)
    
    if not pipelines_path.exists():
        print(f"ℹ️  No pipeline files found in {pipelines_dir}")
        return 0
    
    pipeline_files = list(pipelines_path.glob("*.yaml")) + list(pipelines_path.glob("*.yml"))
    
    if not pipeline_files:
        print(f"ℹ️  No pipeline files found in {pipelines_dir}")
        return 0
    
    for pipeline_file in pipeline_files:
        try:
            with open(pipeline_file, 'r') as f:
                pipeline = yaml.safe_load(f)
            
            # Check if compute is specified
            if 'settings' in pipeline and 'default_compute' in pipeline['settings']:
                compute = pipeline['settings']['default_compute']
                
                # Check if it's a valid format (azureml:cluster-name)
                if compute.startswith('azureml:'):
                    cluster_name = compute.replace('azureml:', '')
                    print(f"✅ {pipeline_file.name}: References compute '{cluster_name}'")
                else:
                    print(f"⚠️  {pipeline_file.name}: Compute reference should start with 'azureml:'")
            else:
                print(f"⚠️  {pipeline_file.name}: No default_compute specified")
        
        except Exception as e:
            print(f"❌ Error processing {pipeline_file.name}: {e}")
            return 1
    
    print(f"\n✅ Validated {len(pipeline_files)} pipeline file(s)")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate pipeline compute references"
    )
    parser.add_argument(
        '--pipelines-dir',
        default='pipelines',
        help='Path to pipelines directory (default: pipelines)'
    )
    
    args = parser.parse_args()
    return validate_pipeline_compute(args.pipelines_dir)


if __name__ == "__main__":
    sys.exit(main())
