#!/usr/bin/env python3
"""
Delta Lake Data Validation Script

Validates Delta Lake tables for schema compliance and data quality.
Used in PR validation pipeline to catch data issues early.

Usage:
    python scripts/validate_delta_data.py \
        --table-path /processed/sensor_data \
        --storage-account mystorageaccount \
        --container data
"""

import argparse
import sys
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

try:
    from deltalake import DeltaTable
    import pandas as pd
except ImportError:
    print("❌ Required packages not installed")
    print("   Run: pip install deltalake pandas")
    sys.exit(1)


class DeltaValidator:
    """Validates Delta Lake table schema and data quality."""
    
    def __init__(self, table_path: str, storage_account: str, container: str = "data"):
        self.table_path = table_path
        self.storage_account = storage_account
        self.container = container
        self.abfs_path = f"abfs://{container}@{storage_account}.dfs.core.windows.net{table_path}"
        self.errors = []
        self.warnings = []
    
    def validate_schema(self, expected_schema: Dict[str, str]) -> bool:
        """
        Validate table schema matches expected schema.
        
        Args:
            expected_schema: Dict of {column_name: expected_type}
        
        Returns:
            True if valid, False otherwise
        """
        print("📋 Validating schema...")
        
        try:
            dt = DeltaTable(self.abfs_path)
            schema = dt.schema()
            
            actual_columns = {field.name: str(field.type) for field in schema.fields}
            
            # Check for missing columns
            for col_name, expected_type in expected_schema.items():
                if col_name not in actual_columns:
                    self.errors.append(f"Missing column: {col_name}")
                elif expected_type not in str(actual_columns[col_name]):
                    self.errors.append(
                        f"Column {col_name}: expected {expected_type}, "
                        f"got {actual_columns[col_name]}"
                    )
            
            # Check for unexpected columns (warning only)
            for col_name in actual_columns:
                if col_name not in expected_schema:
                    self.warnings.append(f"Unexpected column: {col_name}")
            
            if not self.errors:
                print(f"   ✅ Schema valid ({len(actual_columns)} columns)")
                return True
            else:
                print(f"   ❌ Schema validation failed")
                for error in self.errors:
                    print(f"      - {error}")
                return False
                
        except Exception as e:
            self.errors.append(f"Schema validation error: {e}")
            print(f"   ❌ Error: {e}")
            return False
    
    def validate_data_quality(
        self,
        null_checks: List[str] = None,
        range_checks: Dict[str, Tuple[float, float]] = None,
        freshness_hours: int = None
    ) -> bool:
        """
        Validate data quality.
        
        Args:
            null_checks: Columns that should not have nulls
            range_checks: Dict of {column: (min, max)} for range validation
            freshness_hours: Max age of most recent data in hours
        
        Returns:
            True if all checks pass, False otherwise
        """
        print("\n🔍 Validating data quality...")
        
        try:
            dt = DeltaTable(self.abfs_path)
            df = dt.to_pandas()
            
            if df.empty:
                self.errors.append("Table is empty")
                print("   ❌ Table is empty")
                return False
            
            print(f"   Total rows: {len(df):,}")
            
            # Null checks
            if null_checks:
                print(f"\n   Checking nulls in {len(null_checks)} column(s)...")
                for col in null_checks:
                    if col not in df.columns:
                        self.errors.append(f"Column not found: {col}")
                        continue
                    
                    null_count = df[col].isnull().sum()
                    null_pct = (null_count / len(df)) * 100
                    
                    if null_count > 0:
                        self.errors.append(
                            f"Column {col}: {null_count:,} nulls ({null_pct:.2f}%)"
                        )
                        print(f"      ❌ {col}: {null_count:,} nulls")
                    else:
                        print(f"      ✅ {col}: no nulls")
            
            # Range checks
            if range_checks:
                print(f"\n   Checking ranges for {len(range_checks)} column(s)...")
                for col, (min_val, max_val) in range_checks.items():
                    if col not in df.columns:
                        self.errors.append(f"Column not found: {col}")
                        continue
                    
                    out_of_range = df[
                        (df[col] < min_val) | (df[col] > max_val)
                    ].shape[0]
                    
                    if out_of_range > 0:
                        out_of_range_pct = (out_of_range / len(df)) * 100
                        self.errors.append(
                            f"Column {col}: {out_of_range:,} values out of range "
                            f"[{min_val}, {max_val}] ({out_of_range_pct:.2f}%)"
                        )
                        print(f"      ❌ {col}: {out_of_range:,} out of range")
                    else:
                        print(f"      ✅ {col}: all values in range [{min_val}, {max_val}]")
            
            # Freshness check
            if freshness_hours and 'timestamp' in df.columns:
                print(f"\n   Checking data freshness (max age: {freshness_hours}h)...")
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                max_timestamp = df['timestamp'].max()
                age_hours = (datetime.now() - max_timestamp).total_seconds() / 3600
                
                if age_hours > freshness_hours:
                    self.warnings.append(
                        f"Data is {age_hours:.1f} hours old (threshold: {freshness_hours}h)"
                    )
                    print(f"      ⚠️  Most recent data: {age_hours:.1f}h old")
                else:
                    print(f"      ✅ Most recent data: {age_hours:.1f}h old")
            
            return len(self.errors) == 0
            
        except Exception as e:
            self.errors.append(f"Data quality validation error: {e}")
            print(f"   ❌ Error: {e}")
            return False
    
    def validate_row_count(self, min_rows: int = None, max_rows: int = None) -> bool:
        """Validate row count is within expected range."""
        print("\n📊 Validating row count...")
        
        try:
            dt = DeltaTable(self.abfs_path)
            df = dt.to_pandas()
            row_count = len(df)
            
            print(f"   Total rows: {row_count:,}")
            
            if min_rows and row_count < min_rows:
                self.errors.append(f"Row count {row_count:,} below minimum {min_rows:,}")
                print(f"   ❌ Below minimum ({min_rows:,})")
                return False
            
            if max_rows and row_count > max_rows:
                self.warnings.append(f"Row count {row_count:,} above maximum {max_rows:,}")
                print(f"   ⚠️  Above maximum ({max_rows:,})")
            
            print(f"   ✅ Row count within expected range")
            return True
            
        except Exception as e:
            self.errors.append(f"Row count validation error: {e}")
            print(f"   ❌ Error: {e}")
            return False
    
    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 70)
        print("Validation Summary")
        print("=" * 70)
        
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"   - {error}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All validation checks passed!")
        elif not self.errors:
            print(f"\n✅ Validation passed with {len(self.warnings)} warning(s)")
        else:
            print(f"\n❌ Validation failed with {len(self.errors)} error(s)")
        
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Validate Delta Lake table schema and data quality"
    )
    parser.add_argument(
        "--table-path",
        required=True,
        help="Path to Delta table (e.g., /processed/sensor_data)"
    )
    parser.add_argument(
        "--storage-account",
        required=True,
        help="Azure storage account name"
    )
    parser.add_argument(
        "--container",
        default="data",
        help="Container name (default: data)"
    )
    parser.add_argument(
        "--min-rows",
        type=int,
        help="Minimum expected row count"
    )
    parser.add_argument(
        "--freshness-hours",
        type=int,
        default=24,
        help="Maximum age of most recent data in hours (default: 24)"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔍 Delta Lake Data Validation")
    print("=" * 70)
    print(f"\nTable: {args.table_path}")
    print(f"Storage: {args.storage_account}/{args.container}")
    print()
    
    # Initialize validator
    validator = DeltaValidator(
        table_path=args.table_path,
        storage_account=args.storage_account,
        container=args.container
    )
    
    # Define expected schema for sensor data
    expected_schema = {
        'plant_id': 'string',
        'circuit_id': 'string',
        'timestamp': 'timestamp',
        'temperature': 'double',
        'pressure': 'double',
        'vibration': 'double',
        'current': 'double',
        'voltage': 'double',
        'flow_rate': 'double',
    }
    
    # Define critical columns (no nulls allowed)
    null_checks = [
        'plant_id',
        'circuit_id',
        'timestamp',
        'temperature',
        'pressure'
    ]
    
    # Define range checks
    range_checks = {
        'temperature': (-50.0, 200.0),
        'pressure': (0.0, 1000.0),
        'vibration': (0.0, 100.0),
        'current': (0.0, 500.0),
        'voltage': (0.0, 600.0),
        'flow_rate': (0.0, 1000.0),
    }
    
    # Run validations
    schema_valid = validator.validate_schema(expected_schema)
    quality_valid = validator.validate_data_quality(
        null_checks=null_checks,
        range_checks=range_checks,
        freshness_hours=args.freshness_hours
    )
    row_count_valid = validator.validate_row_count(min_rows=args.min_rows)
    
    # Print summary
    validator.print_summary()
    
    # Exit with appropriate code
    if validator.errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
