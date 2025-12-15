#!/usr/bin/env python3
"""
Generate circuit-specific MLTable YAML files for Delta table data sources.
This script creates MLTable definitions that point to Delta tables on ADLS Gen2
with circuit-specific column selections.
"""

import yaml
import sys
import argparse
from pathlib import Path


def generate_mltable(
    circuit_config: dict,
    delta_table_path: str,
    output_path: str,
    adls_account: str = "datalake",
    container: str = "bronze"
) -> None:
    """
    Generate an MLTable YAML file for a specific circuit.
    
    Args:
        circuit_config: Circuit configuration dictionary
        delta_table_path: Path to Delta table (e.g., 'sensors/flottec_2110')
        output_path: Where to save the MLTable file
        adls_account: ADLS Gen2 account name
        container: ADLS Gen2 container name
    """
    plant_id = circuit_config['plant_id']
    circuit_id = circuit_config['circuit_id']
    cutoff_date = circuit_config.get('cutoff_date', '')
    delta_version = circuit_config.get('delta_version')  # Get Delta version from config
    
    # Get circuit-specific features/columns
    # Option 1: Columns defined in circuit config
    columns = circuit_config.get('features', [])
    
    # Option 2: If not specified, use default columns
    if not columns:
        columns = [
            'plant_id',
            'circuit_id', 
            'timestamp',
            'temperature',
            'pressure',
            'vibration',
            'current',
            'voltage',
            'flow_rate',
            'target'
        ]
    
    # Ensure required columns are present
    required_cols = ['plant_id', 'circuit_id', 'timestamp']
    for col in required_cols:
        if col not in columns:
            columns.insert(0, col)
    
    # Build ADLS Gen2 path for Delta table
    # Format: abfss://container@account.dfs.core.windows.net/path
    if delta_table_path.startswith('abfss://'):
        # Already a full path
        full_path = delta_table_path
    else:
        full_path = f"abfss://{container}@{adls_account}.dfs.core.windows.net/{delta_table_path}"
    
    # Create MLTable definition
    mltable_def = {
        'type': 'mltable',
        'paths': [
            {'pattern': full_path}
        ],
        'transformations': [
            # Read from Delta table with specific version for reproducibility
            {'read_delta_lake': {
                'delta_table_version': delta_version  # Use specific version from config
            }},
            # Filter by plant and circuit
            {'filter': f"plant_id == '{plant_id}' and circuit_id == '{circuit_id}'"},
        ]
    }
    
    # Add date filter if cutoff_date is specified
    if cutoff_date:
        mltable_def['transformations'].append({
            'filter': f"timestamp <= '{cutoff_date}'"
        })
    
    # Add column selection
    mltable_def['transformations'].append({
        'keep_columns': columns
    })
    
    # Write MLTable file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        # Add header comment
        f.write(f"# MLTable for {plant_id}_{circuit_id}\n")
        f.write(f"# Generated from circuit configuration\n")
        f.write(f"# Cutoff date: {cutoff_date}\n")
        f.write(f"# Delta version: {delta_version}\n\n")
        
        # Write YAML
        yaml.dump(mltable_def, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Generated MLTable: {output_file}")
    print(f"   Path: {full_path}")
    print(f"   Columns: {len(columns)}")
    print(f"   Cutoff date: {cutoff_date or 'None (all data)'}")
    print(f"   Delta version: {delta_version}")


def main():
    parser = argparse.ArgumentParser(description='Generate circuit-specific MLTable files')
    parser.add_argument('--config', required=True, help='Path to circuits.yaml')
    parser.add_argument('--output-dir', default='mltables', help='Output directory for MLTable files')
    parser.add_argument('--delta-table-base', default='sensors', help='Base path to Delta tables')
    parser.add_argument('--adls-account', default='datalake', help='ADLS Gen2 account name')
    parser.add_argument('--container', default='bronze', help='ADLS Gen2 container')
    parser.add_argument('--circuit', help='Generate for specific circuit only (format: plant_circuit)')
    
    args = parser.parse_args()
    
    # Load circuits config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    circuits = config.get('circuits', [])
    
    if not circuits:
        print("❌ No circuits found in configuration")
        sys.exit(1)
    
    # Filter for specific circuit if requested
    if args.circuit:
        plant_id, circuit_id = args.circuit.split('_')
        circuits = [c for c in circuits 
                   if c.get('plant_id') == plant_id and c.get('circuit_id') == circuit_id]
        
        if not circuits:
            print(f"❌ Circuit not found: {args.circuit}")
            sys.exit(1)
    
    print(f"🔨 Generating MLTable files for {len(circuits)} circuit(s)...\n")
    
    for circuit in circuits:
        plant_id = circuit['plant_id']
        circuit_id = circuit['circuit_id']
        
        # Delta table path - can be customized per circuit
        delta_path = circuit.get('delta_table_path', 
                                f"{args.delta_table_base}/{plant_id}_{circuit_id}")
        
        # Or single Delta table for all circuits
        # delta_path = args.delta_table_base
        
        output_file = f"{args.output_dir}/{plant_id}_{circuit_id}/MLTable"
        
        try:
            generate_mltable(
                circuit_config=circuit,
                delta_table_path=delta_path,
                output_path=output_file,
                adls_account=args.adls_account,
                container=args.container
            )
        except Exception as e:
            print(f"❌ Failed to generate MLTable for {plant_id}_{circuit_id}: {e}")
            sys.exit(1)
    
    print(f"\n✅ Generated {len(circuits)} MLTable file(s)")


if __name__ == '__main__':
    main()
