#!/usr/bin/env python3
"""
Validate environment.yaml configuration file.

Usage:
    python scripts/validation/validate_environment.py --config components/environments/sensor-forecasting-env.yaml
"""

import argparse
import sys
import yaml


def validate_environment(config_path: str) -> int:
    """
    Validate environment configuration.
    
    Args:
        config_path: Path to environment.yaml file
    
    Returns:
        0 if valid, 1 if invalid
    """
    print("🐳 Validating environment.yaml...")
    
    try:
        with open(config_path, 'r') as f:
            env_config = yaml.safe_load(f)
        
        # Check required fields
        if 'name' not in env_config:
            print("❌ Missing 'name' field in environment.yaml")
            return 1
        
        if 'version' not in env_config:
            print("❌ Missing 'version' field in environment.yaml")
            return 1
        
        print(f"✅ Environment config valid: {env_config['name']}:{env_config['version']}")
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
        description="Validate environment configuration"
    )
    parser.add_argument(
        '--config',
        default='components/environments/sensor-forecasting-env.yaml',
        help='Path to environment.yaml (default: components/environments/sensor-forecasting-env.yaml)'
    )
    
    args = parser.parse_args()
    return validate_environment(args.config)


if __name__ == "__main__":
    sys.exit(main())
