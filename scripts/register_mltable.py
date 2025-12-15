"""
Register MLTable Data Asset with date-based versioning.

This script registers a new MLTable Data Asset in Azure ML workspace
using the current date as the version string (e.g., "2025-12-09").

Usage:
    python scripts/register_mltable.py --workspace mlw-dev --date 2025-12-09
"""

import argparse
from datetime import datetime
from azure.ai.ml import MLClient
from azure.ai.ml.entities import Data
from azure.ai.ml.constants import AssetTypes
from azure.identity import DefaultAzureCredential


def register_mltable(
    subscription_id: str,
    resource_group: str,
    workspace_name: str,
    data_asset_name: str,
    version: str,
    description: str,
    path: str,
    delta_version: int = None,
    cutoff_date: str = None,
    plant_id: str = None,
    circuit_id: str = None
):
    """
    Register MLTable Data Asset in Azure ML.
    
    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        workspace_name: Azure ML workspace name
        data_asset_name: Name of the data asset
        version: Version string (date format: YYYY-MM-DD)
        description: Description of the data asset
        path: Path to the MLTable definition
        delta_version: Delta Lake version used for reproducibility
        cutoff_date: Training cutoff date
        plant_id: Plant identifier
        circuit_id: Circuit identifier
    """
    # Initialize ML Client
    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name
    )
    
    # Prepare tags for tracking
    tags = {}
    if delta_version is not None:
        tags['delta_version'] = str(delta_version)
    if cutoff_date:
        tags['cutoff_date'] = cutoff_date
    if plant_id:
        tags['plant_id'] = plant_id
    if circuit_id:
        tags['circuit_id'] = circuit_id
    tags['registered_at'] = datetime.now().isoformat()
    
    # Create Data Asset
    data_asset = Data(
        name=data_asset_name,
        version=version,
        description=description,
        type=AssetTypes.MLTABLE,
        path=path,
        tags=tags
    )
    
    # Register Data Asset
    try:
        registered_asset = ml_client.data.create_or_update(data_asset)
        print(f"✅ Data Asset registered successfully:")
        print(f"   Name: {registered_asset.name}")
        print(f"   Version: {registered_asset.version}")
        print(f"   ID: {registered_asset.id}")
        if delta_version is not None:
            print(f"   Delta version: {delta_version}")
        if cutoff_date:
            print(f"   Cutoff date: {cutoff_date}")
        return registered_asset
    except Exception as e:
        print(f"❌ Failed to register data asset: {str(e)}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Register MLTable Data Asset in Azure ML"
    )
    parser.add_argument(
        "--subscription-id",
        required=True,
        help="Azure subscription ID"
    )
    parser.add_argument(
        "--resource-group",
        required=True,
        help="Resource group name"
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="Azure ML workspace name"
    )
    parser.add_argument(
        "--name",
        default="sensor-data",
        help="Data asset name (default: sensor-data)"
    )
    parser.add_argument(
        "--version",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Version string in YYYY-MM-DD format (default: today's date)"
    )
    parser.add_argument(
        "--description",
        default="Sensor data from Delta Lake",
        help="Description of the data asset"
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Path to MLTable definition (e.g., azureml://datastores/workspaceblobstore/paths/mltable/)"
    )
    
    args = parser.parse_args()
    
    # Validate version format
    try:
        datetime.strptime(args.version, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Invalid version format: {args.version}")
        print("   Version must be in YYYY-MM-DD format")
        return 1
    
    # Register data asset
    register_mltable(
        subscription_id=args.subscription_id,
        resource_group=args.resource_group,
        workspace_name=args.workspace,
        data_asset_name=args.name,
        version=args.version,
        description=args.description,
        path=args.path
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
