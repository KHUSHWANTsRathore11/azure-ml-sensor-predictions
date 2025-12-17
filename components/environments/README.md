# AzureML Environments

This directory contains AzureML environment definitions for the sensor forecasting MLOps pipeline.

## sensor-forecasting-env.yaml

Custom Docker environment with embedded sensor-forecasting package.

### Features

- **Base Framework**: TensorFlow 2.13.0
- **Build Type**: Dockerfile-based
- **Package**: sensor-forecasting v1.0.0 (embedded)
- **Purpose**: Time series forecasting for sensor data

### Registration

Environments are automatically registered via the Azure DevOps training pipeline:
- **Stage 1**: RegisterEnvironment - Registers to Dev workspace
- **Stage 2**: PromoteEnvironment - Promotes to Registry (with approval)

### Manual Registration

To manually register this environment:

```bash
# Register to workspace
az ml environment create \
  --file components/environments/sensor-forecasting-env.yaml \
  --workspace-name <workspace> \
  --resource-group <resource-group>

# Promote to registry
az ml environment create \
  --file components/environments/sensor-forecasting-env.yaml \
  --registry-name <registry> \
  --resource-group <registry-resource-group>
```

### Version Updates

When updating the environment version:

1. Update version in `src/packages/sensor-forecasting/version.py`
2. Update version and `package_version` tag in this file
3. Commit both files together
4. Push to trigger pipeline - all circuits will retrain

See [docs/VERSIONING.md](../../docs/VERSIONING.md) for details.
