# Azure ML Model Versioning Strategy

## Overview
Azure ML uses **auto-incrementing integer versions** (1, 2, 3, ...) for models, which are **immutable**. We cannot specify custom version strings like dates.

## Implementation

### Model Registration (Stage 2)

**Naming Convention:**
- **Model Name**: `{model_name}` from circuit config (e.g., `plant001-circuit01`)
- **Model Version**: Auto-incremented by Azure ML (1, 2, 3, ...)
- **Cutoff Date**: Stored as **tag** for tracking and querying

**Registration Process:**
```bash
# Azure ML auto-assigns version
az ml model create \
  --name plant001-circuit01 \
  --path azureml://jobs/{job_id}/outputs/trained_model \
  --type mlflow_model \
  --set tags.cutoff_date=2025-11-01 \
  --set tags.plant_id=PLANT001 \
  --set tags.circuit_id=CIRCUIT01 \
  --set tags.training_job={job_name}
```

**Result:**
- Model registered as: `plant001-circuit01:1` (or v2, v3, etc.)
- Tags allow filtering by cutoff_date

### Querying Models by Cutoff Date

**Find specific model version:**
```bash
az ml model list \
  --name plant001-circuit01 \
  --query "[?tags.cutoff_date=='2025-11-01'] | [0].{version:version, id:id}" \
  -o json
```

**Returns:**
```json
{
  "version": "3",
  "id": "/subscriptions/.../models/plant001-circuit01/versions/3"
}
```

### Promotion to Registry (Stage 3)

**Process:**
1. Query Dev workspace for model with specific `cutoff_date` tag
2. Get the auto-assigned version number
3. Copy model to Registry (Registry auto-assigns new version)
4. Preserve `cutoff_date` tag in Registry

**Check if already promoted:**
```bash
az ml model list \
  --name plant001-circuit01 \
  --registry-name shared-registry \
  --query "[?tags.cutoff_date=='2025-11-01'].version" \
  -o tsv
```

### Deployment (Stage 5)

**Model Reference:**
```bash
azureml://registries/shared-registry/models/{model_name}/versions/{version}
```

Where `version` is the integer version from Registry (e.g., `5`).

## Benefits

✅ **Compliance**: Follows Azure ML's immutable versioning model  
✅ **Traceability**: `cutoff_date` tag links model to training data  
✅ **Idempotency**: Can check if model with specific cutoff_date exists  
✅ **Flexibility**: Multiple models can be trained for same circuit with different dates  
✅ **Audit Trail**: Tags preserve metadata across workspaces and registry  

## Tag Schema

| Tag | Description | Example |
|-----|-------------|---------|
| `cutoff_date` | Training data cutoff date (YYYY-MM-DD) | `2025-11-01` |
| `plant_id` | Plant identifier | `PLANT001` |
| `circuit_id` | Circuit identifier | `CIRCUIT01` |
| `training_job` | Azure ML job name that trained the model | `circuit_job_1234` |
| `source_version` | Original version in Dev workspace (Registry only) | `3` |
| `promoted_from` | Source workspace (Registry only) | `dev` |

## Example Workflow

1. **Train model** (develop branch)
   - Job produces MLflow model
   - Stage 2 registers as: `plant001-circuit01:1` with `tags.cutoff_date=2025-11-01`

2. **Promote to Registry** (develop branch)
   - Query: Find model with `cutoff_date=2025-11-01` → returns version `1`
   - Promote: Copy to Registry → Registry assigns version `5`
   - Tags preserved: `cutoff_date=2025-11-01`, `source_version=1`

3. **Verify Registry** (release/* branch)
   - Query: Find model with `cutoff_date=2025-11-01` → returns version `5`
   - Store in artifact: `{"model_name": "plant001-circuit01", "version": "5"}`

4. **Deploy to Test** (release/* branch)
   - Deploy: `azureml://registries/shared-registry/models/plant001-circuit01/versions/5`

## Migration Notes

**Before:**
```bash
# ❌ INVALID - Cannot specify version as date
az ml model create --name model --version 2025-11-01
```

**After:**
```bash
# ✅ VALID - Let Azure ML auto-assign version, use tag for date
az ml model create --name model --set tags.cutoff_date=2025-11-01
```

## Troubleshooting

**Q: How do I find the latest model for a circuit?**
```bash
az ml model list --name plant001-circuit01 --query "[0].version" -o tsv
```

**Q: How do I find which version was trained on a specific date?**
```bash
az ml model list --name plant001-circuit01 \
  --query "[?tags.cutoff_date=='2025-11-01'].version" -o tsv
```

**Q: Can I have multiple models for the same circuit?**

Yes! Each training run creates a new version:
- `plant001-circuit01:1` (cutoff_date=2025-10-01)
- `plant001-circuit01:2` (cutoff_date=2025-11-01)
- `plant001-circuit01:3` (cutoff_date=2025-12-01)

Query by `cutoff_date` tag to get the right version.
