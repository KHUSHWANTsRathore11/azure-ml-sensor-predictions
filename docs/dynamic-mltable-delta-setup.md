# Dynamic MLTable Configuration for Delta Tables

This guide explains how to use dynamically generated MLTable definitions that point to Delta tables on ADLS Gen2.

## Overview

Instead of using a rigid MLTable file, the pipeline now:
1. **Generates circuit-specific MLTable files** with custom column selections
2. **Points to Delta tables** on ADLS Gen2 (not parquet files)
3. **Filters data** by circuit and cutoff date
4. **Supports different feature sets** per circuit

## Configuration

### 1. Update circuits.yaml

Add Delta table paths and feature columns for each circuit:

```yaml
circuits:
  - plant_id: flottec
    circuit_id: 2110
    cutoff_date: "2024-01-15"
    model_name: flottec-2110
    
    # Delta table configuration
    delta_table_path: "sensors/flottec_2110"  # Path on ADLS Gen2
    
    # Feature columns (optional - if not specified, uses defaults)
    features:
      - plant_id
      - circuit_id
      - timestamp
      - temperature
      - pressure
      - vibration
      - current
      - voltage
      - flow_rate
      - rpm          # Circuit-specific feature
      - target
```

### 2. Set Pipeline Variables

Add these variables to your Azure DevOps pipeline:

```yaml
variables:
  # ADLS Gen2 Configuration
  - name: adlsAccountName
    value: 'yourdatalake'  # Your ADLS Gen2 account name
  
  - name: adlsContainer
    value: 'bronze'  # Container with Delta tables
  
  - name: storageAccountName
    value: 'yourmlstorage'  # Workspace storage account
```

## How It Works

### Step 1: Generate MLTable Files

The pipeline runs `generate_mltable.py` which:
- Reads your circuit configuration
- Creates an MLTable YAML file for each circuit
- Configures it to read from the Delta table on ADLS Gen2

Generated MLTable example:
```yaml
# MLTable for flottec_2110
# Generated from circuit configuration
# Cutoff date: 2024-01-15

type: mltable
paths:
- pattern: abfss://bronze@yourdatalake.dfs.core.windows.net/sensors/flottec_2110
transformations:
- read_delta_lake:
    timestamp_as_of: null
- filter: plant_id == 'flottec' and circuit_id == '2110'
- filter: timestamp <= '2024-01-15'
- keep_columns:
  - plant_id
  - circuit_id
  - timestamp
  - temperature
  - pressure
  - vibration
  - current
  - voltage
  - flow_rate
  - rpm
  - target
```

### Step 2: Upload to Blob Storage

The generated MLTable file is uploaded to:
```
workspaceblobstore/mltable/{plant_id}_{circuit_id}/MLTable
```

### Step 3: Register as Data Asset

The MLTable is registered in Azure ML as a data asset:
```bash
az ml data create \
  --name flottec_2110 \
  --version 2024-01-15 \
  --type mltable \
  --path azureml://datastores/workspaceblobstore/paths/mltable/flottec_2110/
```

### Step 4: Training Uses Delta Data

When training runs, it:
1. Loads the MLTable definition from blob storage
2. Reads data directly from Delta table on ADLS Gen2
3. Applies filters and column selection
4. Gets circuit-specific features

## Benefits

✅ **Dynamic Column Selection**: Each circuit can have different features  
✅ **Delta Table Support**: Direct reading from Delta tables (ACID transactions, time travel)  
✅ **No Data Duplication**: Data stays in Delta format on ADLS Gen2  
✅ **Version Control**: MLTable definition tracks what columns were used  
✅ **Efficient Filtering**: Delta table predicate pushdown for fast queries  
✅ **Feature Evolution**: Easy to add/remove features per circuit  

## Delta Table Structure

Your Delta tables on ADLS Gen2 should follow this structure:

```
abfss://bronze@yourdatalake.dfs.core.windows.net/
├── sensors/
│   ├── flottec_2110/          # Per-circuit Delta table
│   │   ├── _delta_log/
│   │   ├── part-00000.parquet
│   │   └── ...
│   ├── flottec_2130/
│   │   ├── _delta_log/
│   │   ├── part-00000.parquet
│   │   └── ...
│   └── all_circuits/          # OR single shared Delta table
│       ├── _delta_log/
│       └── ...
```

### Option 1: Per-Circuit Delta Tables
```yaml
circuits:
  - plant_id: flottec
    circuit_id: 2110
    delta_table_path: "sensors/flottec_2110"  # Separate table
```

### Option 2: Shared Delta Table
```yaml
circuits:
  - plant_id: flottec
    circuit_id: 2110
    delta_table_path: "sensors/all_circuits"  # Filter by plant_id/circuit_id
```

## Feature Changes

When you add/remove features:

1. **Update circuits.yaml**:
```yaml
features:
  - temperature
  - pressure
  - new_feature  # Add this
```

2. **Pipeline automatically**:
   - Generates new MLTable with updated columns
   - Registers with same version (or bump cutoff_date)
   - Training uses new features

3. **Config hash changes** → Triggers retraining

## Troubleshooting

### MLTable file not found
- Check that `scripts/generate_mltable.py` ran successfully
- Verify circuit exists in `circuits.yaml`

### Access denied to Delta table
- Ensure service principal has "Storage Blob Data Reader" on ADLS Gen2
- Check that `adlsAccountName` and `adlsContainer` are correct

### Column not found in Delta table
- Verify column exists in your Delta table schema
- Check spelling in `features` list

### Delta table not found
- Verify `delta_table_path` in circuits.yaml
- Check ADLS Gen2 path: `abfss://{container}@{account}.dfs.core.windows.net/{path}`

## Manual Testing

Generate MLTable locally:
```bash
python3 scripts/generate_mltable.py \
  --config config/circuits.yaml \
  --output-dir mltables \
  --adls-account yourdatalake \
  --container bronze \
  --circuit flottec_2110
```

View generated file:
```bash
cat mltables/flottec_2110/MLTable
```

## Next Steps

1. Update your `circuits.yaml` with Delta table paths
2. Add pipeline variables for ADLS
3. Ensure Delta tables exist on ADLS Gen2
4. Grant service principal access to ADLS Gen2
5. Run pipeline to test

The pipeline will automatically generate and register the appropriate MLTable definitions for each circuit.
