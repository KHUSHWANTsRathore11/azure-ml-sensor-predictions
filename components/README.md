# AzureML Components and Assets

This directory contains all AzureML components, data definitions, and environments used in the sensor forecasting MLOps pipeline.

## Directory Structure

### Compute Components

Components are organized by category:

- **`training/`**: Components for model training and hyperparameter tuning
  - `train-lstm-model`: Train LSTM model for time series forecasting
  - `hyperparameter-tuning-pipeline`: Hyperparameter optimization pipeline

- **`scoring/`**: Components for model inference and batch scoring
  - `batch-score`: Batch scoring with trained LSTM model

- **`monitoring/`**: Components for model monitoring and drift detection
  - `calculate-metrics`: Calculate model performance metrics (planned)
  - `detect-drift`: Detect data/model drift (planned)
  - `validate-predictions`: Validate prediction quality (planned)

- **`evaluation/`**: Components for model evaluation and registration
  - `evaluate-model`: Evaluate model performance (planned)
  - `register-model`: Register models to workspace (planned)

- **`pipelines/`**: Pipeline components that orchestrate other components
  - `training-pipeline-component.yaml`: Complete training pipeline

### Environments

- **`environments/`**: AzureML environment definitions
  - `sensor-forecasting-env.yaml`: TensorFlow 2.13 environment with sensor-forecasting package
  - Automatically registered and promoted via Azure DevOps pipeline

## Component Registration

**Registration Strategy**: Only **pipeline components** are registered to AzureML. Command components (training, scoring, monitoring, evaluation) are referenced via local file paths and are NOT registered separately.

### Why This Approach?

- **Atomic versioning**: Pipeline + all its command components version together
- **Simpler**: Only one version to track (the pipeline version)
- **No dependency conflicts**: Command components are bundled with the pipeline

### What Gets Registered

✅ **Pipeline components** (automatically via Azure DevOps Stage 3):
- `training-pipeline-component.yaml`

❌ **Command components** (NOT registered, referenced locally):
- `train-lstm-model`
- `batch-score`
- `hyperparameter-tuning-pipeline` (when used standalone)

### Manual Registration

To manually register a pipeline component:

```bash
az ml component create --file components/pipelines/training-pipeline-component.yaml \
  --workspace-name <workspace> \
  --resource-group <resource-group>
```

**Note**: Command components are included automatically via file references in the pipeline.

## Environment Registration

Environments are automatically registered via the Azure DevOps training pipeline (Stage 1: RegisterEnvironment).

To manually register an environment:

```bash
az ml environment create --file components/environments/sensor-forecasting-env.yaml \
  --workspace-name <workspace> \
  --resource-group <resource-group>
```

## Data Asset Registration

MLTable data assets are registered via the Azure DevOps training pipeline (Stage 4: RegisterMLTables).

MLTable definitions remain in `config/MLTable` and are used as templates by registration scripts.

## Component Versioning

All components follow semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes to component interface
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

See [Component Versioning Strategy](../docs/COMPONENT_VERSIONING.md) for details.
