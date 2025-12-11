# Component-Based Architecture Summary

## Quick Reference

### 📁 Component Structure
```
components/
├── training/train-lstm-model/      ✅ v1.0.0 - LSTM training
└── scoring/batch-score/            ✅ v1.0.0 - Batch inference

Note: MLTable registration is NOT a component - done via direct Azure CLI
```

### 🔄 Flow Summary

**Developer → PR → Build Pipeline → Training Pipeline → Model Registration → Release Pipeline → Production**

### 🎯 Key Files Created

| File | Purpose | Technology |
|------|---------|------------|
| `components/*/component.yaml` | Component definitions | Azure ML YAML |
| `components/*/src/*.py` | Pure Python logic | TensorFlow, Pandas, MLflow |
| `pipelines/training-pipeline-components.yaml` | Component orchestration | Azure ML Pipeline YAML |
| `pipelines/build-pipeline-components.yml` | CI/CD automation | Azure DevOps YAML |
| `scripts/register_all_components.sh` | Bulk component registration | Azure CLI |

### 🚀 Component Registration

**Workspace (Dev):**
```bash
./scripts/register_all_components.sh mlw-dev rg-mlops-dev
```

**Registry (Shared):**
```bash
./scripts/register_all_components.sh "" "" shared-registry
```

### 📊 Data Versioning
- **Strategy**: Name=Circuit ID, Version=Cutoff Date
- **Example**: `azureml:PLANT1_CIRC1:2025-12-09`
- **Registration**: Direct Azure CLI in Stage 1 (per changed circuit)

### 🔧 Build Pipeline Stages
1. **RegisterComponents** - Register environment, components & MLTable assets (per circuit+cutoff_date)
2. **DetectChanges** - Git diff on circuits.yaml
3. **ParallelTraining** - Matrix strategy: Submit one pipeline per changed circuit (max 5 parallel)
4. **ValidateModels** - Validate metrics and tag trained models

### 🎯 Training Pipeline (Single Circuit)
1. **train** - Train LSTM model using pre-registered MLTable data
   - Input: Pre-registered azureml:PLANT1_CIRC1:2025-12-09
   - Output: MLflow model (auto-registered by training component)

### 🏭 Deployment Strategy
- **Test**: Automatic deployment after successful training
- **Prod**: Manual approval gate + monitoring setup
- **Components**: Promoted from workspace to shared registry

### ✅ Advantages Over Script-Based
1. ✅ Reusable components across environments
2. ✅ Independent versioning (1.0.0, 1.1.0, 2.0.0)
3. ✅ CLI/YAML approach (DevOps-friendly)
4. ✅ MLTable registration before training (Name=PLANT_CIRC, Version=Date)
5. ✅ Shared component registry
6. ✅ Parallel orchestration at DevOps level (not Azure ML)
7. ✅ Clear lineage tracking
8. ✅ Custom environment with TensorFlow 2.13

---

**See `docs/COMPONENT_FLOW_DIAGRAM.md` for detailed visual flow**
