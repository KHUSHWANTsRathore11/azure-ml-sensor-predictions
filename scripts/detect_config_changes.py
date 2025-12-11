"""
Detect circuit configuration changes using git diff.

This script compares the current circuits.yaml with the previous version
to determine which circuits need retraining.

Usage:
    python scripts/detect_config_changes.py --target-branch main
"""

import argparse
import subprocess
import yaml
import json
from typing import List, Dict, Set


def get_changed_circuits(target_branch: str = "main") -> List[Dict]:
    """
    Detect which circuits have changed in circuits.yaml.
    
    Args:
        target_branch: Branch to compare against (default: main)
        
    Returns:
        List of circuit configurations that have changed
    """
    try:
        # Check if target branch exists
        branch_check = subprocess.run(
            ["git", "rev-parse", "--verify", f"origin/{target_branch}"],
            capture_output=True,
            text=True
        )
        
        # If target branch doesn't exist, train all circuits (first run)
        if branch_check.returncode != 0:
            print(f"ℹ️  Branch origin/{target_branch} not found. This appears to be the first run.")
            print("   Returning all circuits for training.")
            with open("config/circuits.yaml", "r") as f:
                current_config = yaml.safe_load(f)
            return current_config.get("circuits", [])
        
        # Get git diff for circuits.yaml
        diff_cmd = [
            "git", "diff", "--unified=0",
            f"origin/{target_branch}...HEAD",
            "config/circuits.yaml"
        ]
        
        result = subprocess.run(
            diff_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        diff_output = result.stdout
        
        # If no changes, return empty list
        if not diff_output.strip():
            print("ℹ️  No changes detected in config/circuits.yaml")
            return []
        
        print(f"📝 Git diff output:\n{diff_output}\n")
        
        # Load current circuits.yaml
        with open("config/circuits.yaml", "r") as f:
            current_config = yaml.safe_load(f)
        
        # Extract changed circuit IDs from diff
        changed_circuit_keys = extract_changed_circuits_from_diff(diff_output)
        
        # Get full configs for changed circuits
        changed_circuits = []
        for circuit in current_config.get("circuits", []):
            circuit_key = f"{circuit['plant_id']}-{circuit['circuit_id']}"
            if circuit_key in changed_circuit_keys:
                changed_circuits.append(circuit)
        
        # If we can't parse specific circuits, train all (safety fallback)
        if not changed_circuits and "circuits:" in diff_output:
            print("⚠️  Could not parse specific changes, returning all circuits")
            return current_config.get("circuits", [])
        
        return changed_circuits
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Git diff failed: {e}")
        print(f"   stderr: {e.stderr}")
        raise
    except Exception as e:
        print(f"❌ Error detecting changes: {e}")
        raise


def extract_changed_circuits_from_diff(diff_output: str) -> Set[str]:
    """
    Extract circuit IDs from git diff output.
    
    Args:
        diff_output: Git diff output string
        
    Returns:
        Set of circuit keys (plant_id-circuit_id)
    """
    changed_circuits = set()
    
    lines = diff_output.split("\n")
    current_plant = None
    current_circuit = None
    
    for line in lines:
        # Look for plant_id changes
        if 'plant_id:' in line and (line.startswith('+') or line.startswith('-')):
            parts = line.split('"')
            if len(parts) >= 2:
                current_plant = parts[1]
        
        # Look for circuit_id changes
        if 'circuit_id:' in line and (line.startswith('+') or line.startswith('-')):
            parts = line.split('"')
            if len(parts) >= 2:
                current_circuit = parts[1]
        
        # If we have both plant and circuit, add to set
        if current_plant and current_circuit:
            changed_circuits.add(f"{current_plant}-{current_circuit}")
            current_plant = None
            current_circuit = None
    
    return changed_circuits


def main():
    parser = argparse.ArgumentParser(
        description="Detect circuit configuration changes"
    )
    parser.add_argument(
        "--target-branch",
        default="main",
        help="Branch to compare against (default: main)"
    )
    parser.add_argument(
        "--output",
        default="changed_circuits.json",
        help="Output file for changed circuits (default: changed_circuits.json)"
    )
    
    args = parser.parse_args()
    
    # Detect changes
    changed_circuits = get_changed_circuits(args.target_branch)
    
    # Output results
    if changed_circuits:
        print(f"\n✅ Detected {len(changed_circuits)} changed circuit(s):")
        for circuit in changed_circuits:
            print(f"   - {circuit['plant_id']}/{circuit['circuit_id']} (cutoff: {circuit.get('cutoff_date', 'N/A')})")
        
        # Prepare output with essential metadata for pipeline
        output_data = {
            "circuits": []
        }
        
        for circuit in changed_circuits:
            output_data["circuits"].append({
                "plant_id": circuit["plant_id"],
                "circuit_id": circuit["circuit_id"],
                "cutoff_date": circuit.get("cutoff_date"),
                "model_name": circuit.get("model_name"),
                "change_type": "modified"  # Could be enhanced to detect new vs modified
            })
        
        # Save to file
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n💾 Saved to {args.output}")
    else:
        print("\nℹ️  No circuits need retraining")
        
        # Create empty file
        with open(args.output, "w") as f:
            json.dump({"circuits": []}, f)
    
    return 0


if __name__ == "__main__":
    exit(main())
