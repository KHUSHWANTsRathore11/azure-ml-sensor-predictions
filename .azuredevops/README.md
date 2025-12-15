# Pipeline Architecture

This project uses **3 separated pipelines** for better maintainability and independent execution.

## Directory Structure

```
.azuredevops/               # Azure DevOps CI/CD Pipelines
├── pr-validation-pipeline.yml      # ⭐ PR validation (all branches)
├── training-pipeline.yml           # ⭐ Train models in Dev (develop branch)
├── test-deployment-pipeline.yml    # ⭐ Deploy to Test (release/* branches)
├── prod-deployment-pipeline.yml    # ⭐ Deploy to Production (main branch)
├── templates/                      # Shared reusable templates
│   ├── install-ml-extension.yml
│   ├── configure-ml-defaults.yml
│   └── generate-circuit-configs.yml
├── build-pipeline.yml              # 🗄️ Old monolithic pipeline (archived)
└── PIPELINES.md                    # Quick reference guide

pipelines/                  # Azure ML Training Pipelines
├── single-circuit-training.yaml   # Single circuit training job
└── training-pipeline-components.yaml  # Multi-circuit alternative
```

## Azure DevOps Pipelines (`.azuredevops/`)

These are **CI/CD orchestration pipelines** that run in Azure DevOps:

### ✅ `pr-validation-pipeline.yml` (All PRs)
**Purpose:** Validate configuration files and check ML asset versions

**Trigger:** PRs to `develop`, `release/*`, `main` branches

**Stages:**
1. **Validate Configs** - YAML syntax, required fields, formats
2. **Check ML Assets** - Warn if versions already exist in target workspace
3. **Lint and Format** - Python code quality checks (flake8, black)
4. **Summary** - Display validation results

**Benefits:**
- Fast feedback on PRs (~2-3 minutes)
- Prevents invalid configs from being merged
- No training or deployment - pure validation
- Runs independently for each PR

### 🚀 `training-pipeline.yml` (Develop Branch)
**Purpose:** Train ML models in Dev workspace and promote to Registry

**Trigger:** Auto on merge to `develop` branch or manual

**Stages:**
1. **Register Infrastructure** - Environment, components, MLTables
2. **Train Models** - Submit jobs, monitor, register models
3. **Promote to Registry** - Share models to Registry (with approval)

**Parameters:**
- `manualCircuits` - Specific circuits to train
- `skipPromotion` - Skip Registry promotion

### 🧪 `test-deployment-pipeline.yml` (Release Branches)
**Purpose:** Deploy models from Registry to Test workspace

**Trigger:** Auto on `release/*` branches or manual

**Stages:**
1. **Verify Registry** - Query models by config_hash
2. **Deploy to Test** - Create batch endpoints (with approval)
3. **Integration Tests** - Run smoke tests
4. **QA Sign-Off** - Tag as production_ready (with approval)

### 🚨 `prod-deployment-pipeline.yml` (Main Branch)
**Purpose:** Deploy production-ready models to Production

**Trigger:** Auto on `main` branch or manual

**Stages:**
1. **Verify Registry** - Query production_ready models
2. **Deploy to Production** - Production endpoints (with dual approval)
3. **Production Validation** - Health checks

### 📦 Shared Templates
**Purpose:** Reusable steps across all pipelines

- `install-ml-extension.yml` - Install Azure ML CLI (stable only)
- `configure-ml-defaults.yml` - Set workspace defaults
- `generate-circuit-configs.yml` - Generate circuit configs

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
