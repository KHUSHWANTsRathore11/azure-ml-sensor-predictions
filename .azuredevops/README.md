# Pipeline Organization

This project separates Azure DevOps pipelines from Azure ML pipelines for clarity.

## Directory Structure

```
.azuredevops/               # Azure DevOps CI/CD Pipelines
├── build-pipeline.yml      # Main build pipeline (corrected architecture)
├── release-pipeline.yml    # Release/deployment pipeline
└── environment-only-pipeline.yml  # Environment update pipeline

pipelines/                  # Azure ML Training Pipelines
├── single-circuit-training.yaml   # Single circuit training (used by matrix jobs)
└── training-pipeline-components.yaml  # Multi-circuit training (alternative)
```

## Azure DevOps Pipelines (`.azuredevops/`)

These are **CI/CD orchestration pipelines** that run in Azure DevOps:

### `build-pipeline.yml` (Primary)
- Triggers on PR/commit to circuits.yaml, components, environment
- **Stage 1**: Register environment, components, MLTable assets (per circuit)
- **Stage 2**: Parallel training using matrix strategy (DevOps-level parallelism)
- **Stage 3**: Validate and tag trained models

### `release-pipeline.yml`
- Promotes components to shared registry
- Deploys to Test → Prod environments
- Manual approval gates

### `environment-only-pipeline.yml`
- Updates only the Python environment
- Useful for dependency updates without retraining

## Azure ML Pipelines (`pipelines/`)

These are **Azure ML pipeline definitions** (YAML) submitted to Azure ML workspace:

### `single-circuit-training.yaml` ⭐ (Used in matrix jobs)
- Trains a **single circuit's model**
- Called by each DevOps matrix job
- Inputs:
  - `circuit_config` - Circuit YAML config
  - `training_data` - Pre-registered MLTable (azureml:PLANT_CIRC:cutoff_date)
- Outputs: Trained MLflow model

### `training-pipeline-components.yaml` (Alternative)
- Multi-circuit training in single Azure ML pipeline
- Uses parallel component (Azure ML-level parallelism)
- Alternative approach to DevOps matrix

## Usage

### Triggering Build Pipeline
```bash
# Make changes to circuits
git add config/circuits.yaml
git commit -m "Update PLANT001_CIRCUIT01 hyperparameters"
git push

# Azure DevOps automatically triggers build-pipeline.yml
# 1. Registers infrastructure
# 2. Detects changed circuits
# 3. Trains in parallel (up to 5 concurrent)
# 4. Tags models with metadata
```

### Manually Submitting Azure ML Pipeline
```bash
# Submit single circuit training
az ml job create \
  --file pipelines/single-circuit-training.yaml \
  --workspace-name mlw-dev \
  --set inputs.circuit_config.path="config/circuits/PLANT001_CIRCUIT01.yaml" \
  --set inputs.training_data.path="azureml:PLANT001_CIRCUIT01:2025-11-01"
```

## Key Differences

| Aspect | Azure DevOps Pipelines | Azure ML Pipelines |
|--------|------------------------|-------------------|
| **Location** | `.azuredevops/` | `pipelines/` |
| **Extension** | `.yml` | `.yaml` |
| **Purpose** | CI/CD orchestration | ML training execution |
| **Triggers** | Git commits, PRs, schedules | Submitted by DevOps or manual |
| **Parallelism** | Matrix strategy | Parallel component (optional) |
| **Runs in** | Azure DevOps agents | Azure ML compute clusters |
| **Manages** | Infrastructure, testing, deployment | Model training, experimentation |

## Best Practices

1. **Azure DevOps pipelines** (`.azuredevops/`) control:
   - Infrastructure registration
   - Change detection
   - Parallel orchestration
   - Model validation
   - Deployment approvals

2. **Azure ML pipelines** (`pipelines/`) focus on:
   - Model training logic
   - Component composition
   - ML experimentation
   - Training orchestration

3. **Naming Convention**:
   - Azure DevOps: `*-pipeline.yml` (e.g., `build-pipeline.yml`)
   - Azure ML: `*-training.yaml` or descriptive names (e.g., `single-circuit-training.yaml`)
