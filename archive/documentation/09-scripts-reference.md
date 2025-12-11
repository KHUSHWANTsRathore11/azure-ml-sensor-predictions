# Scripts Reference

[← Back to README](../README.md)

## Overview

This document provides complete Python and shell scripts referenced throughout the architecture documentation.

## Table of Contents

1. [register_mltable.py](#register_mltablepy)
2. [detect_config_changes.py](#detect_config_changespy)
3. [check_env_change.py](#check_env_changepy)
4. [get_env_from_config.py](#get_env_from_configpy)
5. [promote_to_registry.sh](#promote_to_registrysh)
6. [deploy_batch_endpoint.sh](#deploy_batch_endpointsh)
7. [get_all_deployments.py](#get_all_deploymentspy)
8. [invoke_all_batch_endpoints.py](#invoke_all_batch_endpointspy)
9. [rollback_model.sh](#rollback_modelsh)

---

## register_mltable.py

```python
#!/usr/bin/env python3
"""
Register MLTable Data Asset for training (per circuit).
Checks if cutoff_date already exists for this circuit, skips if found.
Returns Data Asset version number for pipeline consumption.
"""

import argparse
import os
import yaml
from datetime import datetime
from azure.ai.ml import MLClient
from azure.ai.ml.entities import Data
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError


def register_mltable(
    plant_id: str,
    circuit_id: str,
    cutoff_date: str,
    pr_number: str,
    pr_author: str,
    git_sha: str,
    workspace_name: str,
    resource_group: str,
    subscription_id: str
):
    """
    Register or find existing MLTable Data Asset for specific circuit.
    
    Returns:
        str: Data Asset version string (e.g., "2025-12-09")
    """
    # Initialize MLClient
    ml_client = MLClient(
        DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name
    )
    
    # Unique Data Asset name per circuit
    data_asset_name = f"sensor_training_data_{plant_id}_{circuit_id}"
    
    # Check if Data Asset with this cutoff_date already exists
    print(f"Checking for existing Data Asset: {data_asset_name} version {cutoff_date}")
    try:
        existing_asset = ml_client.data.get(name=data_asset_name, version=cutoff_date)
        print(f"✓ Found existing Data Asset version {cutoff_date}")
        print(f"Skipping registration. Reusing version {cutoff_date}")
        return cutoff_date
    except ResourceNotFoundError:
        print(f"No existing Data Asset found for version {cutoff_date}")
    
    # Not found, create new MLTable
    print(f"Creating new MLTable for {plant_id}/{circuit_id} with cutoff_date={cutoff_date}")
    
    # Load circuit config
    config_path = f"config/plants/{plant_id}/{circuit_id}.yml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    sensor_id = config['training']['data_filters']['sensor_id']
    
    # Create MLTable content with circuit-specific filter
    mltable_content = f"""type: mltable
paths:
  - folder: azureml://datastores/workspaceblobstore/paths/processed/sensor_data/
transformations:
  - read_delta_lake:
      delta_table_version: latest
  - filter:
      expression: "date <= '{cutoff_date}' AND sensor_id == '{sensor_id}'"
"""
    
    # Create local directory and save MLTable file
    mltable_dir = f"mltables/plant_{plant_id}_circuit_{circuit_id}_cutoff_{cutoff_date.replace('-', '')}"
    os.makedirs(mltable_dir, exist_ok=True)
    
    with open(os.path.join(mltable_dir, "MLTable"), "w") as f:
        f.write(mltable_content)
    
    print(f"MLTable file created at {mltable_dir}/MLTable")
    
    # Calculate hyperparameters hash
    import hashlib
    hyperparam_str = str(sorted(config['training']['hyperparameters'].items()))
    hyperparam_hash = hashlib.md5(hyperparam_str.encode()).hexdigest()[:8]
    
    # Register as Data Asset with cutoff_date as version string
    data_asset = Data(
        name=data_asset_name,
        version=cutoff_date,  # Use cutoff_date as version
        type="mltable",
        path=mltable_dir,
        tags={
            "plant_id": plant_id,
            "circuit_id": circuit_id,
            "cutoff_date": cutoff_date,
            "pr_number": pr_number,
            "pr_author": pr_author,
            "git_commit_sha": git_sha,
            "sensor_id": sensor_id,
            "hyperparameters_hash": hyperparam_hash,
            "delta_path": "/processed/sensor_data/",
            "registered_at": datetime.now().isoformat(),
            "registered_by": "azure-devops-pipeline"
        },
        description=f"Training data for Plant {plant_id} Circuit {circuit_id} up to {cutoff_date}"
    )
    
    registered = ml_client.data.create_or_update(data_asset)
    print(f"✓ Successfully registered Data Asset version {cutoff_date}")
    print(f"  Name: {registered.name}")
    print(f"  Version: {registered.version}")
    
    # Write version to file for pipeline consumption
    with open("data_asset_version.txt", "w") as f:
        f.write(cutoff_date)
    
    return cutoff_date


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plant-id", required=True)
    parser.add_argument("--circuit-id", required=True)
    parser.add_argument("--cutoff-date", required=True)
    parser.add_argument("--pr-number", required=True)
    parser.add_argument("--pr-author", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--workspace-name", required=True)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--subscription-id", required=True)
    
    args = parser.parse_args()
    
    version = register_mltable(
        plant_id=args.plant_id,
        circuit_id=args.circuit_id,
        cutoff_date=args.cutoff_date,
        pr_number=args.pr_number,
        pr_author=args.pr_author,
        git_sha=args.git_sha,
        workspace_name=args.workspace_name,
        resource_group=args.resource_group,
        subscription_id=args.subscription_id
    )
```

---

## detect_config_changes.py

```python
#!/usr/bin/env python3
"""
Detect which circuit config files changed in a PR.
"""

import argparse
import json
import yaml
import subprocess
from pathlib import Path


def detect_changed_configs(pr_number, commit_sha):
    """
    Parse git diff to find changed config files.
    """
    # Get changed files
    result = subprocess.run(
        ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
        capture_output=True,
        text=True
    )
    
    changed_files = result.stdout.strip().split('\n')
    
    # Filter for config files
    config_pattern = 'config/plants/'
    changed_configs = [
        f for f in changed_files 
        if f.startswith(config_pattern) and f.endswith('.yml')
    ]
    
    print(f"Found {len(changed_configs)} changed config files")
    
    # Parse each config
    circuits = []
    for config_path in changed_configs:
        if not Path(config_path).exists():
            continue
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        circuit_info = {
            'plant_id': config['plant_id'],
            'circuit_id': config['circuit_id'],
            'cutoff_date': config['training']['cutoff_date'],
            'environment_version': config['training']['environment_version'],
            'config_path': config_path,
            'pr_number': pr_number,
            'commit_sha': commit_sha
        }
        
        circuits.append(circuit_info)
    
    # Write JSON
    with open('changed_circuits.json', 'w') as f:
        json.dump(circuits, f, indent=2)
    
    return circuits


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--pr-number', required=True)
    parser.add_argument('--commit-sha', required=True)
    args = parser.parse_args()
    
    detect_changed_configs(args.pr_number, args.commit_sha)
```

---

## check_env_change.py

```python
#!/usr/bin/env python3
"""
Check if environment files changed in PR.
"""

import argparse
import subprocess
import yaml


def check_environment_change(pr_number):
    """Check if environment-related files changed."""
    result = subprocess.run(
        ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
        capture_output=True,
        text=True
    )
    
    changed_files = result.stdout.strip().split('\n')
    
    env_files = [
        'environment/custom_tf_env.yml',
        'environment/conda.yml',
        'environment/requirements.txt',
        'src/',
        'setup.py'
    ]
    
    env_changed = any(
        any(f.startswith(pattern) for pattern in env_files)
        for f in changed_files
    )
    
    if env_changed:
        with open('environment/custom_tf_env.yml', 'r') as f:
            env_config = yaml.safe_load(f)
        
        env_version = env_config['version']
        backward_compatible = env_config.get('tags', {}).get('backward_compatible', 'true')
        requires_retrain = env_config.get('tags', {}).get('requires_retrain', 'false')
        
        print(f"##vso[task.setvariable variable=env_changed;isOutput=true]true")
        print(f"##vso[task.setvariable variable=env_version;isOutput=true]{env_version}")
        print(f"##vso[task.setvariable variable=backward_compatible;isOutput=true]{backward_compatible}")
        print(f"##vso[task.setvariable variable=requires_retrain;isOutput=true]{requires_retrain}")
    else:
        print(f"##vso[task.setvariable variable=env_changed;isOutput=true]false")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--pr-number', required=True)
    args = parser.parse_args()
    
    check_environment_change(args.pr_number)
```

---

## get_env_from_config.py

```python
#!/usr/bin/env python3
"""
Extract environment version from circuit config file.
"""

import argparse
import yaml


def get_environment_version(config_file):
    """Read environment version from config."""
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    env_version = config['training']['environment_version']
    print(env_version)
    return env_version


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-file', required=True)
    args = parser.parse_args()
    
    get_environment_version(args.config_file)
```

---

## promote_to_registry.sh

```bash
#!/bin/bash
# Promote model from Dev Workspace to Azure ML Registry

set -e

ARTIFACT_FILE="$1"
REGISTRY_NAME="$2"
RESOURCE_GROUP="$3"

# Parse artifact metadata
PLANT_ID=$(jq -r '.plant_id' "$ARTIFACT_FILE")
CIRCUIT_ID=$(jq -r '.circuit_id' "$ARTIFACT_FILE")
MODEL_NAME=$(jq -r '.model_name' "$ARTIFACT_FILE")
MODEL_VERSION=$(jq -r '.model_version' "$ARTIFACT_FILE")
DEV_WORKSPACE=$(jq -r '.dev_workspace' "$ARTIFACT_FILE")

echo "Promoting model $MODEL_NAME:$MODEL_VERSION to registry..."

# Share model from workspace to registry
az ml model share \
  --name "$MODEL_NAME" \
  --version "$MODEL_VERSION" \
  --workspace-name "$DEV_WORKSPACE" \
  --resource-group "$RESOURCE_GROUP" \
  --registry-name "$REGISTRY_NAME" \
  --share-with-name "${MODEL_NAME}_${PLANT_ID}_${CIRCUIT_ID}" \
  --share-with-version "$MODEL_VERSION"

echo "✅ Model promoted to registry: $REGISTRY_NAME"
```

---

## deploy_batch_endpoint.sh

```bash
#!/bin/bash
# Deploy model to batch endpoint

set -e

ARTIFACT_FILE="$1"
ENDPOINT_NAME="$2"
DEPLOYMENT_NAME="$3"
WORKSPACE_NAME="$4"
RESOURCE_GROUP="$5"
REGISTRY_NAME="$6"
ENVIRONMENT="$7"

# Parse artifact
PLANT_ID=$(jq -r '.plant_id' "$ARTIFACT_FILE")
CIRCUIT_ID=$(jq -r '.circuit_id' "$ARTIFACT_FILE")
MODEL_VERSION=$(jq -r '.model_version' "$ARTIFACT_FILE")
ENV_VERSION=$(jq -r '.environment_version' "$ARTIFACT_FILE")

REGISTRY_MODEL="azureml://registries/${REGISTRY_NAME}/models/sensor_model_${PLANT_ID}_${CIRCUIT_ID}/versions/${MODEL_VERSION}"
REGISTRY_ENV="azureml://registries/${REGISTRY_NAME}/environments/custom-tf-env/versions/${ENV_VERSION}"

# Create or update deployment
az ml batch-deployment create-or-update \
  --name "$DEPLOYMENT_NAME" \
  --endpoint-name "$ENDPOINT_NAME" \
  --workspace-name "$WORKSPACE_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --model "$REGISTRY_MODEL" \
  --environment "$REGISTRY_ENV" \
  --compute azureml:batch-compute-cluster \
  --mini-batch-size 100 \
  --max-concurrency-per-instance 1

echo "✅ Deployment complete: $DEPLOYMENT_NAME"
```

---

## get_all_deployments.py

```python
#!/usr/bin/env python3
"""
Get all production batch deployments.
"""

import argparse
import json
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential


def get_all_deployments(workspace_name, resource_group, subscription_id):
    """List all batch deployments."""
    ml_client = MLClient(
        DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name
    )
    
    deployments = []
    
    # List all batch endpoints
    endpoints = ml_client.batch_endpoints.list()
    
    for endpoint in endpoints:
        # List deployments for this endpoint
        deps = ml_client.batch_deployments.list(endpoint_name=endpoint.name)
        
        for dep in deps:
            deployment_info = {
                'plant_id': dep.tags.get('plant_id'),
                'circuit_id': dep.tags.get('circuit_id'),
                'endpoint_name': endpoint.name,
                'deployment_name': dep.name,
                'model_version': dep.tags.get('model_version'),
                'environment': dep.environment
            }
            deployments.append(deployment_info)
    
    # Write to JSON
    with open('deployments.json', 'w') as f:
        json.dump(deployments, f, indent=2)
    
    print(f"Found {len(deployments)} deployments")
    return deployments


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace-name', required=True)
    parser.add_argument('--resource-group', required=True)
    parser.add_argument('--subscription-id', required=True)
    args = parser.parse_args()
    
    get_all_deployments(args.workspace_name, args.resource_group, args.subscription_id)
```

---

## invoke_all_batch_endpoints.py

```python
#!/usr/bin/env python3
"""
Invoke all batch endpoints for daily inference.
"""

import argparse
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential


def invoke_all_endpoints(workspace_name, resource_group, subscription_id):
    """Invoke all batch deployments."""
    ml_client = MLClient(
        DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name
    )
    
    endpoints = ml_client.batch_endpoints.list()
    
    for endpoint in endpoints:
        deployments = ml_client.batch_deployments.list(endpoint_name=endpoint.name)
        
        for deployment in deployments:
            plant_id = deployment.tags.get('plant_id')
            circuit_id = deployment.tags.get('circuit_id')
            
            print(f"Invoking {plant_id}/{circuit_id}...")
            
            job = ml_client.batch_endpoints.invoke(
                endpoint_name=endpoint.name,
                deployment_name=deployment.name
            )
            
            print(f"  Job started: {job.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace-name', required=True)
    parser.add_argument('--resource-group', required=True)
    parser.add_argument('--subscription-id', required=True)
    args = parser.parse_args()
    
    invoke_all_endpoints(args.workspace_name, args.resource_group, args.subscription_id)
```

---

## rollback_model.sh

```bash
#!/bin/bash
# Rollback model deployment to previous version

set -e

PLANT_ID="$1"
CIRCUIT_ID="$2"
PREVIOUS_VERSION="$3"

ENDPOINT_NAME="batch-endpoint-plant-$PLANT_ID"
DEPLOYMENT_NAME="deployment-circuit-$CIRCUIT_ID"

echo "Rolling back $PLANT_ID/$CIRCUIT_ID to version $PREVIOUS_VERSION"

REGISTRY_MODEL="azureml://registries/mlregistry-shared/models/sensor_model_${PLANT_ID}_${CIRCUIT_ID}/versions/${PREVIOUS_VERSION}"

az ml batch-deployment update \
  --name "$DEPLOYMENT_NAME" \
  --endpoint-name "$ENDPOINT_NAME" \
  --workspace-name "prod-ml-workspace" \
  --resource-group "mlops-rg" \
  --set model="$REGISTRY_MODEL"

echo "✅ Rollback complete"
```

---

## Related Documents

- [05-build-pipeline.md](05-build-pipeline.md) - Pipeline context
- [10-pipeline-yaml-reference.md](10-pipeline-yaml-reference.md) - YAML definitions

---

**Document Version:** 1.0  
**Last Updated:** December 9, 2025
