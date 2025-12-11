# Cutoff Date: Version vs Tag Usage

## Overview
The `cutoff_date` from circuit configuration serves different purposes depending on the Azure ML resource type.

---

## 📊 MLTable Data Assets: cutoff_date as VERSION

### Usage
```bash
# Register MLTable with cutoff_date as VERSION
az ml data create \
  --name PLANT1_CIRC1 \
  --version 2025-12-09 \
  --type mltable \
  --path azureml://datastores/workspaceblobstore/paths/mltable/PLANT1_CIRC1/
```

### Reference
```yaml
inputs:
  training_data:
    type: mltable
    path: azureml:PLANT1_CIRC1:2025-12-09  # Version = cutoff_date
```

### Why VERSION?
- ✅ **Semantic Meaning**: Each version represents data filtered up to that cutoff date
- ✅ **Version History**: Easy to see all cutoff dates used: `az ml data list --name PLANT1_CIRC1`
- ✅ **Direct Reference**: Pipeline can reference exact data snapshot
- ✅ **Immutable**: Each version is immutable and traceable

---

## 🏋️ Training Pipelines: cutoff_date as TAG

### Usage
```bash
# Submit pipeline with cutoff_date as TAG
az ml job create \
  --file pipelines/single-circuit-training.yaml \
  --set name="train-PLANT1-CIRC1-123" \
  --set inputs.training_data.path="azureml:PLANT1_CIRC1:2025-12-09" \
  --set tags.cutoff_date=2025-12-09 \
  --set tags.plant_id=PLANT1 \
  --set tags.circuit_id=CIRC1 \
  --set tags.build_id=12345
```

### Why TAG?
- ✅ **Metadata**: Training job version is auto-incremented; cutoff_date is metadata
- ✅ **Filtering**: Query all jobs trained with specific cutoff_date
- ✅ **Traceability**: Links job back to data asset version
- ✅ **Search**: `az ml job list --tag cutoff_date=2025-12-09`

---

## 🤖 Models: cutoff_date as TAG

### Usage
```bash
# Update model with cutoff_date as TAG
az ml model update \
  --name PLANT1_CIRC1_model \
  --version 1 \
  --add-tag cutoff_date=2025-12-09 \
  --add-tag data_asset_name=PLANT1_CIRC1 \
  --add-tag data_asset_version=2025-12-09 \
  --add-tag component_version=1.0.0 \
  --add-tag build_id=12345 \
  --add-tag validated=true
```

### Why TAG?
- ✅ **Model Version**: Semantic versioning (1, 2, 3) for model iterations
- ✅ **Data Lineage**: Tag points to which data version (cutoff_date) was used
- ✅ **Filtering**: Find all models trained with specific cutoff_date
- ✅ **Governance**: Track data provenance without coupling to version number

---

## 🚀 Deployments: cutoff_date as TAG

### Usage
```bash
# Deploy with cutoff_date as TAG
az ml batch-deployment create \
  --endpoint-name be-plant1-circ1-prod \
  --name deployment-v1 \
  --model azureml:PLANT1_CIRC1_model:1 \
  --set-tag cutoff_date=2025-12-09 \
  --set-tag model_version=1 \
  --set-tag deployed_by=mlops-pipeline \
  --set-tag environment=production
```

### Why TAG?
- ✅ **Deployment Version**: Independent versioning for deployment configurations
- ✅ **Traceability**: Which data cutoff_date did the deployed model use?
- ✅ **Monitoring**: Alert if deployed model's data is too old
- ✅ **Audit**: Track deployment metadata separate from version

---

## 📋 Summary Table

| Resource Type | cutoff_date Usage | Example | Query |
|--------------|-------------------|---------|-------|
| **MLTable Data Asset** | **VERSION** | `azureml:PLANT1_CIRC1:2025-12-09` | `az ml data list --name PLANT1_CIRC1` |
| **Training Pipeline** | **TAG** | `--set tags.cutoff_date=2025-12-09` | `az ml job list --tag cutoff_date=2025-12-09` |
| **Model** | **TAG** | `--add-tag cutoff_date=2025-12-09` | `az ml model list --tag cutoff_date=2025-12-09` |
| **Deployment** | **TAG** | `--set-tag cutoff_date=2025-12-09` | `az ml batch-deployment list --tag cutoff_date=2025-12-09` |

---

## 🔍 Query Examples

### Find all resources for a specific cutoff_date

```bash
# All data assets for circuit PLANT1_CIRC1
az ml data list --name PLANT1_CIRC1 --output table

# All training jobs with cutoff_date=2025-12-09
az ml job list --workspace-name mlw-dev --tag cutoff_date=2025-12-09 --output table

# All models trained with cutoff_date=2025-12-09
az ml model list --workspace-name mlw-dev --tag cutoff_date=2025-12-09 --output table

# All deployments using models from cutoff_date=2025-12-09
az ml batch-deployment list --workspace-name mlw-prod --tag cutoff_date=2025-12-09 --output table
```

### Find full lineage for a circuit

```bash
# 1. Find data asset versions (cutoff dates)
az ml data list --name PLANT1_CIRC1

# 2. Find jobs that used specific data version
az ml job list --tag data_asset_version=2025-12-09 --tag circuit_id=CIRC1

# 3. Find models from those jobs
az ml model list --tag cutoff_date=2025-12-09 --tag circuit_id=CIRC1

# 4. Find deployments of those models
az ml batch-deployment list --tag cutoff_date=2025-12-09
```

---

## 💡 Best Practices

### 1. Always Tag Related Resources
When training:
```bash
# Pipeline tags reference the data
--set tags.cutoff_date=2025-12-09
--set tags.data_asset_name=PLANT1_CIRC1
--set tags.data_asset_version=2025-12-09
```

When registering models:
```bash
# Model tags reference the data and pipeline
--add-tag cutoff_date=2025-12-09
--add-tag data_asset_name=PLANT1_CIRC1
--add-tag data_asset_version=2025-12-09
--add-tag training_job_id=<job_id>
```

### 2. Use Consistent Tag Names
- `cutoff_date` - The data cutoff date (YYYY-MM-DD)
- `data_asset_name` - The MLTable asset name (PLANT1_CIRC1)
- `data_asset_version` - The MLTable asset version (same as cutoff_date)
- `plant_id` - Plant identifier
- `circuit_id` - Circuit identifier

### 3. Version vs Tag Decision Tree
```
Is it an MLTable data asset?
├─ YES → Use cutoff_date as VERSION
└─ NO → Use cutoff_date as TAG
```

### 4. Querying Strategy
- **Data Assets**: Query by name, list versions
- **Everything Else**: Query by tags

---

## 🔗 Complete Example

### Stage 1: Register Data (VERSION)
```bash
az ml data create \
  --name PLANT1_CIRC1 \
  --version 2025-12-09 \
  --type mltable
```

### Stage 3: Submit Training (TAG)
```bash
az ml job create \
  --file single-circuit-training.yaml \
  --set inputs.training_data.path="azureml:PLANT1_CIRC1:2025-12-09" \
  --set tags.cutoff_date=2025-12-09 \
  --set tags.data_asset_name=PLANT1_CIRC1
```

### Stage 4: Tag Model (TAG)
```bash
az ml model update \
  --name PLANT1_CIRC1_model --version 1 \
  --add-tag cutoff_date=2025-12-09 \
  --add-tag data_asset_name=PLANT1_CIRC1 \
  --add-tag data_asset_version=2025-12-09
```

### Release: Deploy (TAG)
```bash
az ml batch-deployment create \
  --endpoint-name be-plant1-circ1-prod \
  --model azureml:PLANT1_CIRC1_model:1 \
  --set-tag cutoff_date=2025-12-09
```

### Query Full Lineage
```bash
# Start with data version
az ml data show --name PLANT1_CIRC1 --version 2025-12-09

# Find jobs that used it
az ml job list --tag cutoff_date=2025-12-09 --tag circuit_id=CIRC1

# Find models from those jobs
az ml model list --tag cutoff_date=2025-12-09

# Find deployments
az ml batch-deployment list --tag cutoff_date=2025-12-09
```

---

## ✅ Key Takeaways

1. **MLTable Only**: `cutoff_date` is a **VERSION** for MLTable data assets
2. **Everything Else**: `cutoff_date` is a **TAG** for pipelines, models, deployments
3. **Traceability**: Tags link back to the data asset version used
4. **Querying**: Use tags to filter and find related resources
5. **Governance**: Clear separation between versioning and metadata
