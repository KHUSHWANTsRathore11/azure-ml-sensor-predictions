# Data Architecture

[← Back to README](../README.md)

---

## Overview

This document details the data engineering strategy, including ETL pipelines, Delta Lake design, MLTable Data Assets, and versioning approach for reproducible training.

---

## 1. Delta Lake Design

### Single Table Architecture

**Path:** `/processed/sensor_data/` (Production ADLS Gen2)

**Design Principles:**
- **Single table** for all sensor data
- **No partitioning** (data size manageable, simplifies queries)
- **Merge/upsert mode** for idempotency
- **Date column** for filtering

**Schema:**
```python
{
    "timestamp": "timestamp",       # Sensor reading timestamp
    "date": "date",                 # Extracted date for filtering
    "sensor_id": "string",          # Unique sensor identifier (e.g., "SENSOR_P001_C001")
    "temperature": "double",        # Sensor readings
    "pressure": "double",
    "vibration": "double",
    # ... additional sensor features
}
```

### Data Immutability Guarantee

**Critical Assumption:** Historical data never changes once a date has passed.

```
Day 1 (2025-12-09):
  Delta contains: [2025-01-01 to 2025-12-09] = 100 rows

Day 5 (2025-12-13):
  Delta contains: [2025-01-01 to 2025-12-13] = 120 rows
  BUT data for [2025-01-01 to 2025-12-09] = STILL 100 rows (unchanged)
```

**Why This Matters:**
- MLTable with filter `date <= 2025-12-09` always returns same data
- No need to lock Delta table version
- Training reproducibility guaranteed by date filter
- Can always use `delta_table_version: latest` safely

### Write Operations

```python
# ETL merge logic (Synapse Spark)
from delta.tables import DeltaTable

delta_table = DeltaTable.forPath(spark, "/processed/sensor_data/")

# Merge new data (upsert based on sensor_id + timestamp)
delta_table.alias("target").merge(
    new_data.alias("source"),
    "target.sensor_id = source.sensor_id AND target.timestamp = source.timestamp"
).whenMatchedUpdateAll() \
 .whenNotMatchedInsertAll() \
 .execute()
```

---

## 2. Azure ML Asset Versioning Rules

**Important:** Different rules per asset type:

| Asset Type | Versioning Rule | Example Allowed | Example Failed |
|------------|----------------|-----------------|----------------|
| **Model** | Integer ONLY | `1`, `2`, `15` | `1.0.0`, `v1` |
| **Environment** | String | `1.5.0`, `ubuntu-20.04` | N/A |
| **Data** | String | `2025-12-09`, `initial_load` | N/A |
| **Component** | String | `1.0.0`, `beta` | N/A |

**This Architecture:**
- **Models:** Auto-increment integers (1, 2, 3...)
- **Environments:** Semantic versioning (`1.5.0`, `2.0.0`)
- **Data Assets:** Date-based strings (`2025-12-09`)

---

## 3. MLTable Data Assets

### Purpose

Logical pointers to Delta Lake data with date filters for reproducible training.

### Versioning Strategy

**Use cutoff_date as version string:**
```python
data_asset = Data(
    name="sensor_training_data_P001_C001",
    version="2025-12-09",  # Date-based version
    type="mltable",
    ...
)
```

**Benefits:**
- ✅ Self-documenting (version = data cutoff date)
- ✅ Easy querying by date
- ✅ No duplicate registrations
- ✅ Clear lineage

### MLTable Definition

```yaml
# MLTable file content
type: mltable
paths:
  - folder: azureml://datastores/workspaceblobstore/paths/processed/sensor_data/
transformations:
  - read_delta_lake:
      delta_table_version: latest  # Safe due to immutability
  - filter:
      expression: "date <= '2025-12-09' AND sensor_id == 'SENSOR_P001_C001'"
```

### Per-Circuit Data Assets

**Naming Convention:** `sensor_training_data_{plant_id}_{circuit_id}`

**Example Registry:**
```
sensor_training_data_P001_C001:2025-11-09
sensor_training_data_P001_C001:2025-12-09
sensor_training_data_P001_C002:2025-12-09
sensor_training_data_P002_C001:2025-12-09
```

**Tags:**
```python
{
    "plant_id": "P001",
    "circuit_id": "C001",
    "cutoff_date": "2025-12-09",
    "pr_number": "PR-1234",
    "pr_author": "john.doe@company.com",
    "git_commit_sha": "a1b2c3d4",
    "sensor_id": "SENSOR_P001_C001",
    "registered_at": "2025-12-09T10:30:00Z"
}
```

---

## 4. Hybrid Data Access Strategy

### Training (Infrequent)

**Use MLTable Data Assets:**
```python
# In training pipeline
inputs:
  training_data:
    type: mltable
    path: azureml:sensor_training_data_P001_C001:2025-12-09
```

**Benefits:**
- Reproducible training
- Graphical lineage in AzureML Studio
- Version tracking
- No daily overhead

### Inference (Daily)

**Direct Delta Lake reads:**
```python
# In score.py
from deltalake import DeltaTable

delta_table = DeltaTable("/mnt/batch/processed/sensor_data/")
df = delta_table.to_pandas()

# Filter for specific circuit
df_circuit = df[df['sensor_id'] == sensor_id]
latest_date = df_circuit['date'].max()
df_latest = df_circuit[df_circuit['date'] == latest_date]
```

**Benefits:**
- Always reads freshest data
- No registration overhead
- Simple and performant

---

## 5. ETL Pipeline

### Schedule

**Frequency:** Every 3 hours  
**Tool:** Azure Synapse Spark Pool

### Workflow

```
Source Data (Parquet/SQL)
  → Synapse Spark Pool (transformation)
  → Delta Lake (merge/upsert)
  → Verify (check latest date)
  → Optional: Trigger batch inference
```

### Synapse Notebook Pseudocode

```python
# Read from sources
raw_df = spark.read.parquet("/raw/sensor_data/")

# Transform
processed_df = raw_df \
    .withColumn("date", F.to_date("timestamp")) \
    .select("timestamp", "date", "sensor_id", ...)

# Merge to Delta
delta_table = DeltaTable.forPath(spark, "/processed/sensor_data/")
delta_table.alias("target").merge(
    processed_df.alias("source"),
    "target.sensor_id = source.sensor_id AND target.timestamp = source.timestamp"
).whenMatchedUpdateAll() \
 .whenNotMatchedInsertAll() \
 .execute()

# Verify
latest_date = spark.read.format("delta").load("/processed/sensor_data/") \
    .selectExpr("max(date) as latest").collect()[0]["latest"]
print(f"Latest date in Delta: {latest_date}")
```

---

## 6. Storage Layout

### Production ADLS Gen2 (Shared)

```
/production-datalake
├── /raw                    # Source parquet files
├── /processed
│   └── /sensor_data        # Delta Lake table
│       ├── *.parquet       # Data files
│       └── _delta_log/     # Transaction log
└── /monitoring             # Drift detection per circuit
    ├── /plant_1_circuit_1/
    └── /plant_N_circuit_X/
```

### Workspace Storage (Per Environment)

**Dev:**
```
/dev-workspace-storage
├── /mltables               # MLTable definitions
├── /models                 # Trained artifacts
└── /experiments            # MLflow data
```

**Test:**
```
/test-workspace-storage
├── /predictions            # Test inference outputs
└── /test_results           # Validation results
```

**Production:**
```
/prod-workspace-storage
└── /predictions            # Production outputs
    ├── /plant_1/
    │   ├── /circuit_1/YYYY-MM-DD.parquet
    │   └── /circuit_2/YYYY-MM-DD.parquet
    └── /plant_N/
```

---

## 7. Data Lineage

| Component | Tracking Method |
|-----------|----------------|
| **ETL Runs** | Synapse pipeline run ID + Delta commit timestamp |
| **Training Data** | MLTable Data Asset version (date string) |
| **Model Lineage** | Model metadata links to Data Asset version |
| **Inference Data** | Delta version logged in Application Insights |

**Example Lineage:**
```
ETL Run (2025-12-09 10:00) 
  → Delta commit #125 
  → MLTable Data Asset:2025-12-09 
  → Model v12 (plant P001, circuit C001)
  → Production deployment (2025-12-10)
```

---

## 8. Data Governance

### Retention Policy
- **Historical data:** Keep indefinitely (Delta supports time travel)
- **Predictions:** 90 days in hot tier, then move to cool tier
- **Monitoring data:** 1 year retention

### Access Control
- **Production Delta Lake:** Read-only for all workspaces
- **Dev/Test/Prod Storage:** Workspace-specific write access
- **Managed Identity:** Used for all data access

---

## Related Documents

- [← High-Level Architecture](01-high-level-architecture.md)
- [→ Multi-Model Strategy](03-multi-model-strategy.md)
- [→ Scripts Reference (register_mltable.py)](09-scripts-reference.md)
