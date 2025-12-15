#!/usr/bin/env python3
"""
Simple utility to check the current Delta Lake version.

This helps you determine which delta_version value to put in your circuit configs.

Usage:
    python scripts/check_delta_version.py --path /processed/sensor_data --storage mystorageaccount

Requires delta lake package:
    pip install deltalake
"""

import argparse
from deltalake import DeltaTable


def check_delta_version(delta_path: str, storage_account: str, container: str = "data"):
    """Check current Delta Lake version and show recent history."""
    
    # Construct ABFS path
    abfs_path = f"abfs://{container}@{storage_account}.dfs.core.windows.net{delta_path}"
    
    print(f"🔍 Checking Delta table: {delta_path}")
    print(f"   Storage: {storage_account}/{container}")
    print(f"   Full path: {abfs_path}\n")
    
    try:
        # Load Delta table
        dt = DeltaTable(abfs_path)
        
        # Get current version
        current_version = dt.version()
        print(f"✅ Current Delta version: {current_version}")
        
        # Get history
        history = dt.history()
        
        # Show last 5 versions
        print(f"\n📜 Recent history (last 5 versions):")
        print("-" * 80)
        
        recent = history.sort_values('version', ascending=False).head(5)
        
        for _, entry in recent.iterrows():
            version = entry.get('version', 'N/A')
            timestamp = entry.get('timestamp', 'N/A')
            operation = entry.get('operation', 'N/A')
            print(f"   v{version}: {timestamp} - {operation}")
        
        print("-" * 80)
        
        # Get table stats
        print(f"\n📊 Table statistics:")
        detail = dt.metadata()
        print(f"   Total versions: {current_version + 1}")
        print(f"   Schema: {len(detail.schema.fields)} columns")
        
        # Show sample data
        df = dt.to_pandas()
        print(f"   Current rows: {len(df):,}")
        
        if 'date' in df.columns:
            import pandas as pd
            df['date'] = pd.to_datetime(df['date'])
            print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        
        print(f"\n💡 Recommendation:")
        print(f"   Use delta_version: {current_version} in your circuit configs")
        print(f"   This ensures reproducibility for training runs started now.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"\n💡 Troubleshooting:")
        print(f"   1. Verify storage account name and path")
        print(f"   2. Ensure Azure credentials are configured (az login)")
        print(f"   3. Check that Delta table exists at this path")
        return 1
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Check current Delta Lake version"
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Path to Delta table (e.g., /processed/sensor_data)"
    )
    parser.add_argument(
        "--storage",
        required=True,
        help="Storage account name (e.g., mystorageaccount)"
    )
    parser.add_argument(
        "--container",
        default="data",
        help="Container name (default: data)"
    )
    
    args = parser.parse_args()
    
    return check_delta_version(
        delta_path=args.path,
        storage_account=args.storage,
        container=args.container
    )


if __name__ == "__main__":
    import sys
    sys.exit(main())
