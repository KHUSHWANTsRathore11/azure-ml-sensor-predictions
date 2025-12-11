# Component-Based MLOps Flow

## Overview
This document describes the complete end-to-end flow using **Azure ML Components** with CLI/YAML approach for DevOps-friendly infrastructure.

---

## 🏗️ Component Architecture

### Component Catalog

```
components/
├── training/
│   ├── train-lstm-model/          # v1.0.0 - LSTM training with TensorFlow
│   │   ├── component.yaml
│   │   └── src/train.py
│   ├── evaluate-model/            # (Future) Model evaluation & metrics
│   └── register-model/            # (Future) Model registration
│
├── scoring/
│   ├── batch-score/               # v1.0.0 - Batch inference
│   │   ├── component.yaml
│   │   └── src/score.py
│   └── validate-predictions/      # (Future) Prediction validation
│
└── monitoring/
    ├── detect-drift/              # (Future) Data drift detection
    └── calculate-metrics/         # (Future) Model performance metrics

Note: MLTable registration is NOT a component - it's done via direct Azure CLI
```

---

## 🔄 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DEVELOPER WORKFLOW                                │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│ Developer    │
│ Updates      │──┐
│ circuits.yaml│  │
└──────────────┘  │
                  │
┌──────────────┐  │
│ Developer    │  │
│ Updates      │──┼──► Git Push to Feature Branch
│ Components   │  │
└──────────────┘  │
                  │
┌──────────────┐  │
│ Developer    │  │
│ Updates      │──┘
│ Pipeline     │
└──────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PULL REQUEST CREATED                             │
└─────────────────────────────────────────────────────────────────────────┘
        │
        ▼

┌═══════════════════════════════════════════════════════════════════════┐
║                    AZURE DEVOPS BUILD PIPELINE                         ║
║                   (build-pipeline-components.yml)                      ║
╚═══════════════════════════════════════════════════════════════════════╝

┌───────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Register Environment & Components & MLTable Assets           │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  🐍 Register Custom Environment (if changed)                          │
│     └─ az ml environment create --file config/environment.yaml       │
│        Name: sensor-forecasting-env                                   │
│        Conda: TensorFlow 2.13, Pandas, Scikit-learn, MLflow          │
│        Version: Auto-incremented if changed                           │
│                                                                        │
│  📦 Register Training Components (if changed)                         │
│     └─ az ml component create --file train-lstm-model/component.yaml │
│        References: sensor-forecasting-env:latest                      │
│                                                                        │
│  📦 Register Scoring Components (if changed)                          │
│     └─ az ml component create --file batch-score/component.yaml      │
│                                                                        │
│  📊 Register MLTable Data Assets (per circuit + cutoff_date)          │
│     For each changed circuit:                                         │
│       DATA_NAME="PLANT1_CIRC1"                                        │
│       DATA_VERSION="2025-12-09"                                       │
│       └─ Check if exists:                                             │
│          az ml data show --name $DATA_NAME --version $DATA_VERSION   │
│       └─ If not exists, register:                                     │
│          az ml data create --name $DATA_NAME                         │
│             --version $DATA_VERSION                                   │
│             --type mltable                                            │
│             --path azureml://datastores/workspaceblobstore/          │
│                    paths/mltable/$PLANT_$CIRCUIT/                    │
│                                                                        │
│  ✅ Components + Environment + MLTable assets registered              │
│  ✅ Component versions captured for downstream use                    │
│     TRAIN_COMPONENT_VERSION=$(az ml component show ... -o tsv)       │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│ STAGE 2: Detect Changed Circuits                                      │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  🔍 Git Diff Analysis                                                 │
│     └─ python scripts/detect_config_changes.py                       │
│        --target-branch main                                           │
│        --output changed_circuits.json                                 │
│                                                                        │
│  📋 Output: List of changed circuits with metadata                    │
│     [                                                                 │
│       {"plant_id": "PLANT1", "circuit_id": "CIRC1",                 │
│        "cutoff_date": "2025-12-09", "change_type": "modified"},     │
│       {"plant_id": "PLANT1", "circuit_id": "CIRC2",                 │
│        "cutoff_date": "2025-12-08", "change_type": "new"}           │
│     ]                                                                 │
│                                                                        │
│  ⚖️  Decision: If circuitCount > 0 → Continue, else Skip Training    │
└───────────────────────────────────────────────────────────────────────┘
        │
        │ (If circuits changed)
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│ STAGE 3: Parallel Training Orchestration (Azure DevOps)               │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  🔄 Matrix Strategy - Train Each Circuit in Parallel                 │
│                                                                        │
│  strategy:                                                            │
│    matrix:                                                            │
│      PLANT1_CIRC1:                                                    │
│        plant_id: PLANT1                                               │
│        circuit_id: CIRC1                                              │
│        cutoff_date: 2025-12-09                                        │
│        data_name: PLANT1_CIRC1                                        │
│        data_version: 2025-12-09                                       │
│        component_version: $TRAIN_COMPONENT_VERSION                    │
│      PLANT1_CIRC2:                                                    │
│        plant_id: PLANT1                                               │
│        circuit_id: CIRC2                                              │
│        cutoff_date: 2025-12-08                                        │
│        data_name: PLANT1_CIRC2                                        │
│        data_version: 2025-12-08                                       │
│        component_version: $TRAIN_COMPONENT_VERSION                    │
│    maxParallel: 5                                                     │
│                                                                        │
│  For each circuit (running in parallel):                             │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────┐         │
│  │  JOB: Train PLANT1_CIRC1                                │         │
│  ├─────────────────────────────────────────────────────────┤         │
│  │                                                         │         │
│  │  🚀 Submit Single-Circuit Training Pipeline            │         │
│  │     └─ az ml job create                                │         │
│  │        --file pipelines/single-circuit-training.yaml   │         │
│  │        --set name="train-PLANT1-CIRC1-$(Build.Number)" │         │
│  │        --set jobs.train.component=                     │         │
│  │             "azureml:train_lstm_model:$VERSION"        │         │
│  │        --set inputs.circuit_config=                    │         │
│  │             "config/circuits/PLANT1_CIRC1.yaml"        │         │
│  │        --set inputs.training_data=                     │         │
│  │             "azureml:sensor-data:PLANT1_CIRC1_2025-12-09"│       │
│  │                                                         │         │
│  │  📺 Stream Pipeline Logs                               │         │
│  │     └─ az ml job stream --name $JOB_NAME              │         │
│  │                                                         │         │
│  │  ✅ Model trained: PLANT1_CIRC1_model:1               │         │
│  └─────────────────────────────────────────────────────────┘         │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────┐         │
│  │  JOB: Train PLANT1_CIRC2 (runs in parallel)            │         │
│  │  (Same structure as above)                             │         │
│  └─────────────────────────────────────────────────────────┘         │
│                                                                        │
│  ✅ All circuits trained in parallel (max 5 concurrent)              │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼

┌═══════════════════════════════════════════════════════════════════════┐
║         AZURE ML SINGLE-CIRCUIT TRAINING PIPELINE (Component)          ║
║                 (single-circuit-training.yaml)                         ║
╚═══════════════════════════════════════════════════════════════════════╝

┌───────────────────────────────────────────────────────────────────────┐
│ STEP 1: Train Model                                                    │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Component: train_lstm_model (version from Stage 1)                  │
│                                                                        │
│  Inputs:                                                              │
│    • circuit_config: config/circuits/PLANT1_CIRC1.yaml               │
│    • training_data: azureml:PLANT1_CIRC1:2025-12-09                 │
│                     (already registered in Stage 1)                  │
│                                                                        │
│  Outputs:                                                             │
│    • trained_model: MLflow model (auto-logged)                       │
│    • metrics: JSON (MAE, RMSE, R²)                                   │
│    • artifacts: Training plots, checkpoints                          │
│                                                                        │
│  Environment: sensor-forecasting-env (from Stage 1)                  │
│                                                                        │
│  ✅ Model trained and registered to workspace                        │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
        Back to Build Pipeline (all matrix jobs complete)
        │
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│ STAGE 4: Validate & Tag Trained Models                                │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  📊 Gather Training Metrics from All Jobs                             │
│     For each circuit:                                                 │
│       └─ az ml job show --name train-PLANT1-CIRC1-$(Build.Number)   │
│                                                                        │
│  ✅ Validate Metrics Meet Thresholds                                  │
│     • MAE < threshold                                                 │
│     • RMSE < threshold                                                │
│     • R² > threshold                                                  │
│                                                                        │
  🏷️  Tag Models with Metadata                                        │
  │     └─ az ml model update                                             │
  │        --name PLANT1_CIRC1_model --version 1                         │
  │        --add-tag build_id=$(Build.BuildId)                           │
  │        --add-tag cutoff_date=2025-12-09  (TAG, not version)         │
  │        --add-tag data_asset_name=PLANT1_CIRC1                        │
  │        --add-tag data_asset_version=2025-12-09  (MLTable version)   │
  │        --add-tag component_version=$TRAIN_COMPONENT_VERSION          │
  │        --add-tag validated=true                                      │
│                                                                        │
│  ✅ Models validated and tagged (auto-registered by MLflow):         │
│     • PLANT1_CIRC1_model:1 (from training pipeline)                 │
│     • PLANT1_CIRC2_model:1 (from training pipeline)                 │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PULL REQUEST COMPLETED                              │
│                    Merge to Main Branch                                  │
└─────────────────────────────────────────────────────────────────────────┘
        │
        ▼

┌═══════════════════════════════════════════════════════════════════════┐
║                   AZURE DEVOPS RELEASE PIPELINE                        ║
║                      (release-pipeline.yml)                            ║
╚═══════════════════════════════════════════════════════════════════════╝

┌───────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Promote Components to Shared Registry                        │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  📤 Promote to Registry                                               │
│     └─ az ml component create                                         │
│        --file register-mltable/component.yaml                        │
│        --registry-name shared-registry                               │
│                                                                        │
│  ✅ Components available in:                                          │
│     azureml://registries/shared-registry/components/                 │
│        • register_mltable:1.0.0                                      │
│        • train_lstm_model:1.0.0                                      │
│        • batch_score:1.0.0                                           │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│ STAGE 2: Deploy to Test Environment                                   │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  🎯 Create Batch Endpoints (Circuit-Specific)                         │
│     For each circuit:                                                 │
│       └─ az ml batch-endpoint create                                  │
│          --name be-plant1-circ1-test                                  │
│                                                                        │
│  🚀 Create Deployments using Registry Components                     │
│     └─ az ml batch-deployment create                                  │
│        --endpoint-name be-plant1-circ1-test                          │
│        --model azureml:PLANT1_CIRC1_model:1                          │
│        --scoring-component azureml://registries/.../batch_score:1.0.0│
│                                                                        │
│  🧪 Run Test Scoring                                                  │
│     └─ az ml batch-endpoint invoke                                    │
│        --name be-plant1-circ1-test                                   │
│        --input azureml:test-data:latest                              │
│                                                                        │
│  ✅ Test deployments validated                                        │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│ STAGE 3: Deploy to Production (Manual Approval)                       │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ⏸️  Manual Approval Gate                                             │
│     └─ Requires approval from Operations team                        │
│                                                                        │
  🎯 Create Production Endpoints                                       │
  │     └─ az ml batch-endpoint create --name be-plant1-circ1-prod       │
  │                                                                        │
  │  🚀 Deploy to Production                                              │
  │     └─ az ml batch-deployment create                                  │
  │        --endpoint-name be-plant1-circ1-prod                          │
  │        --model azureml:PLANT1_CIRC1_model:1                          │
  │        --set-tag cutoff_date=2025-12-09  (TAG for traceability)     │
│                                                                        │
│  🔔 Configure Monitoring (Model Monitors)                             │
│     └─ python monitoring/setup_all_monitors.py                       │
│        --environment prod                                             │
│                                                                        │
│  ✅ Production deployment complete with monitoring                    │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PRODUCTION INFERENCE                              │
└─────────────────────────────────────────────────────────────────────────┘

Daily Batch Scoring:
  └─ Scheduled Trigger (Azure Data Factory / Azure ML Pipeline)
     └─ az ml batch-endpoint invoke
        --name be-plant1-circ1-prod
        --input azureml:daily-sensor-data:latest

Continuous Monitoring:
  └─ Azure ML Model Monitors
     ├─ Data Drift Detection (KS Test)
     ├─ Data Quality Monitoring
     └─ Prediction Drift Detection
  
  └─ Alert on significant drift
     └─ Trigger retraining pipeline if thresholds exceeded
```

---

## 🔑 Key Benefits of Component-Based Approach

### 1. **Reusability**
- Register once, use everywhere (Dev → Test → Prod)
- Components versioned independently
- Shared across teams via Registry

### 2. **Versioning & Lineage**
```yaml
# Component reference with version pinning
component: azureml://registries/shared-registry/components/train_lstm_model/versions/1.0.0
```

### 3. **DevOps-Friendly with CLI/YAML**
- No Python SDK in pipelines
- Pure YAML definitions
- Azure CLI for all operations
- Easy integration with Azure DevOps

### 4. **MLTable Registration Before Training**
- Data asset per circuit: Name=PLANT1_CIRC1, Version=cutoff_date (2025-12-09)
- Registered once in Stage 1, used by all pipeline runs
- Ensures consistent data across pipeline
- Traceable data lineage:
  - MLTable: cutoff_date as **VERSION**
  - Pipeline/Model/Deployment: cutoff_date as **TAG**

### 5. **Parallel Execution at DevOps Level**
- Azure DevOps matrix strategy (not Azure ML parallel component)
- Each circuit gets its own Azure ML pipeline job
- Max 5 concurrent Azure DevOps jobs
- Each pipeline: Simple, single-circuit training
- Scales to 75-200 models with controlled concurrency

---

## 📋 Component Registration Workflow

### Local/CI Registration
```bash
# Register all components to Dev workspace
./scripts/register_all_components.sh mlw-dev rg-mlops-dev

# Register to Shared Registry (for Prod promotion)
./scripts/register_all_components.sh "" "" shared-registry
```

### Pipeline Registration (Automated)
```yaml
# In build-pipeline-components.yml
- task: AzureCLI@2
  displayName: 'Register Data Components'
  inputs:
    scriptLocation: 'inlineScript'
    inlineScript: |
      az ml component create \
        --file components/data/register-mltable/component.yaml \
        --workspace-name $(workspaceName)
```

---

## 🔄 Data Versioning Strategy

### MLTable Circuit-Specific Versioning
```
azureml:PLANT1_CIRC1:2025-12-09  ← Name: Circuit ID, Version: Cutoff Date
azureml:PLANT1_CIRC2:2025-12-08
azureml:PLANT2_CIRC1:2025-12-07
```

### Naming Convention:
- **Asset Name**: `{PLANT_ID}_{CIRCUIT_ID}` (e.g., PLANT1_CIRC1)
- **Asset Version**: `{CUTOFF_DATE}` (e.g., 2025-12-09)
- **Full Reference**: `azureml:PLANT1_CIRC1:2025-12-09`

### Important: Cutoff Date Usage
- **MLTable Data Assets**: `cutoff_date` is the **VERSION** (azureml:PLANT1_CIRC1:2025-12-09)
- **Training Pipelines**: `cutoff_date` is a **TAG** (for tracking and filtering)
- **Models**: `cutoff_date` is a **TAG** (references which data version was used)
- **Deployments**: `cutoff_date` is a **TAG** (indicates model's training data cutoff)

### Benefits:
- **Circuit Isolation**: Each circuit has its own data asset with independent versions
- **Reproducibility**: Exact data snapshot per circuit per training date
- **Cutoff Date as Version (MLTable only)**: Data asset version = cutoff_date
- **Cutoff Date as Tag (everything else)**: Pipeline jobs, models, deployments tagged with cutoff_date
- **Comparison**: Compare model performance across different cutoff dates for same circuit
- **Rollback**: Retrain with historical data version (older cutoff_date) for specific circuit
- **Version History**: `az ml data list --name PLANT1_CIRC1` shows all cutoff dates used for training
- **Query by Tag**: `az ml model list --tag cutoff_date=2025-12-09` finds all models trained with that data

---

## 🎯 Component Usage Examples

### 1. Use in Training Pipeline (Single Circuit)
```yaml
jobs:
  train:
    type: command
    component: azureml:train_lstm_model:1.0.0  # Use specific version from Stage 1
    inputs:
      circuit_config:
        path: config/circuits/PLANT1_CIRC1.yaml
      training_data:
        type: mltable
        path: azureml:PLANT1_CIRC1:2025-12-09  # Pre-registered in Stage 1
    outputs:
      trained_model: # Auto-registered by MLflow
```

### 2. Use in Batch Deployment
```bash
az ml batch-deployment create \
  --name deployment-v1 \
  --endpoint-name be-plant1-circ1 \
  --model azureml:PLANT1_CIRC1_model:1 \
  --component azureml://registries/shared-registry/components/batch_score:1.0.0
```

### 3. Promote Component Version
```bash
# Copy from Dev to Registry
az ml component create \
  --file components/training/train-lstm-model/component.yaml \
  --registry-name shared-registry
```

---

## 📊 Monitoring & Drift Detection

### Continuous Monitoring (Post-Production)
- **Data Drift**: Kolmogorov-Smirnov test on input distributions
- **Prediction Drift**: Monitor output distribution changes
- **Data Quality**: Missing values, outliers, schema validation

### Alert & Retrain Workflow
```
Drift Detected → Alert Sent → Manual Review → Approve Retrain → 
  → Trigger Build Pipeline → New Version Trained → Deploy to Test → Validate → Promote to Prod
```

---

## 🛠️ Quick Start Commands

### 1. Register Components
```bash
cd /home/ksr11/workspace/repos/MLOPS/azure-ml-sensor-predictions
./scripts/register_all_components.sh mlw-dev rg-mlops-dev
```

### 2. Submit Training Pipeline (Single Circuit)
```bash
# After Stage 1 registers components and MLTable assets
az ml job create \
  --file pipelines/single-circuit-training.yaml \
  --workspace-name mlw-dev \
  --resource-group rg-mlops-dev \
  --set jobs.train.component="azureml:train_lstm_model:1.0.0" \
  --set inputs.circuit_config="config/circuits/PLANT1_CIRC1.yaml" \
  --set inputs.training_data.path="azureml:PLANT1_CIRC1:2025-12-09"
```

### 3. Monitor Pipeline
```bash
az ml job stream --name <job_name> --workspace-name mlw-dev
```

### 4. Deploy to Batch Endpoint
```bash
az ml batch-endpoint create --name be-plant1-circ1 --workspace-name mlw-test
az ml batch-deployment create \
  --endpoint-name be-plant1-circ1 \
  --model azureml:PLANT1_CIRC1_model:1 \
  --component azureml://registries/shared-registry/components/batch_score:1.0.0
```

---

## 🔐 Governance & Security

### Component Versioning Policy
- **Semantic Versioning**: Major.Minor.Patch (1.0.0)
- **Breaking Changes**: Increment major version
- **New Features**: Increment minor version
- **Bug Fixes**: Increment patch version

### Registry Access Control
- Dev Workspace: Contributor access for data scientists
- Shared Registry: Read-only for Test/Prod, Admin access for CI/CD
- Production Workspace: Restricted deployment permissions

---

## 📝 Next Steps

1. ✅ **Components Created**: train-lstm-model, batch-score
2. ⏳ **Update Build Pipeline**: 
   - Add environment registration
   - Add MLTable registration per circuit in Stage 1
   - Add matrix strategy for parallel training in Stage 3
   - Use registered component versions
3. ⏳ **Create Single-Circuit Pipeline**: single-circuit-training.yaml
4. ⏳ **Update detect_config_changes.py**: Include cutoff_date in output
5. ⏳ **Remaining Components**: evaluate-model, detect-drift, validate-predictions
6. ⏳ **Testing**: End-to-end flow validation
7. ⏳ **Documentation**: Update team onboarding guide

---

## 📚 References

- [Azure ML Components Documentation](https://learn.microsoft.com/azure/machine-learning/concept-component)
- [Azure ML CLI v2](https://learn.microsoft.com/azure/machine-learning/how-to-configure-cli)
- [Component Versioning Best Practices](https://learn.microsoft.com/azure/machine-learning/how-to-manage-component-version)
- [MLTable Data Asset](https://learn.microsoft.com/azure/machine-learning/how-to-mltable)

