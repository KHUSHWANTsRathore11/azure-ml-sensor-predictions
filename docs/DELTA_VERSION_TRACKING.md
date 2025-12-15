# Delta Version Tracking for MLTable Reproducibility

## Overview

This implementation adds Delta Lake version tracking to your MLTable Data Assets for perfect reproducibility. The approach is simple: you manually specify which Delta version to use in your circuit configs.

## How It Works

### 1. Configuration

Each circuit now has a `delta_version` field:

```yaml
circuits:
  - plant_id: "PLANT001"
    circuit_id: "CIRCUIT01"
    cutoff_date: "2025-12-09"  # Date filter for training
    delta_version: 50          # Delta Lake version to use
    # ... other fields
```

**Two key parameters:**
- `cutoff_date`: Filters data (`date <= '2025-12-09'`)
- `delta_version`: Specific Delta snapshot to read from

### 2. MLTable Generation

When you generate MLTable files, they now use the specific Delta version:

```yaml
type: mltable
paths:
  - pattern: abfss://...
transformations:
  - read_delta_lake:
      delta_table_version: 50  # From config
  - filter: "date <= '2025-12-09'"  # From config
```

### 3. Reproducibility Guarantee

**Training on Dec 20, 2025:**
- Delta table is at version 50
- You set `delta_version: 50` in config
- MLTable reads Delta v50 + applies date filter
- Gets 50,000 rows

**6 months later (Jun 2026):**
- Delta table is now at version 100
- **Your MLTable still reads Delta v50** (unchanged)
- Still gets exact same 50,000 rows ✅

**Even if historical data was corrected:**
- Someone fixed 2025-12-05 data in Delta v60
- **Your MLTable uses v50** (before correction)
- Perfect reproducibility ✅

## Workflow

### Step 1: Check Current Delta Version

Before updating configs, check what version Delta is at:

```bash
python scripts/check_delta_version.py \
    --path /processed/sensor_data \
    --storage mystorageaccount \
    --container data
```

**Output:**
```
✅ Current Delta version: 50

📜 Recent history (last 5 versions):
   v50: 2025-12-20 08:00:00 - WRITE
   v49: 2025-12-20 05:00:00 - WRITE
   v48: 2025-12-20 02:00:00 - WRITE
   ...

💡 Recommendation:
   Use delta_version: 50 in your circuit configs
```

### Step 2: Update Circuit Configs

Edit `config/circuits.yaml`:

```yaml
circuits:
  - plant_id: "PLANT001"
    circuit_id: "CIRCUIT01"
    cutoff_date: "2025-12-09"
    delta_version: 50  # ← Set this
```

### Step 3: Generate MLTable Files

```bash
python scripts/generate_mltable.py \
    --config config/circuits.yaml \
    --output-dir mltables \
    --adls-account mystorageaccount
```

**Output:**
```
✅ Generated MLTable: mltables/PLANT001_CIRCUIT01/MLTable
   Path: abfss://data@...
   Cutoff date: 2025-12-09
   Delta version: 50  # ← Verified!
```

### Step 4: Register MLTable

```bash
az ml data create \
    --name PLANT001_CIRCUIT01 \
    --version 2025-12-20 \
    --type mltable \
    --path mltables/PLANT001_CIRCUIT01
```

**Tags stored:**
```json
{
  "plant_id": "PLANT001",
  "circuit_id": "CIRCUIT01",
  "cutoff_date": "2025-12-09",
  "delta_version": "50",
  "registered_at": "2025-12-20T10:00:00Z"
}
```

## When to Update delta_version

### Scenario 1: New Training Run with More Data

**Situation:** A month has passed, you want to retrain with updated cutoff

```yaml
# Before
cutoff_date: "2025-11-01"
delta_version: 40

# After (1 month later)
cutoff_date: "2025-12-01"  # ← New cutoff
delta_version: 48          # ← Current Delta version
```

### Scenario 2: Same Cutoff, Just Rerunning

**Situation:** Retrain same model, no data changes

```yaml
# Can keep same values!
cutoff_date: "2025-12-01"
delta_version: 48  # Still valid if data hasn't changed
```

### Scenario 3: Historical Data Was Corrected

**Situation:** Someone fixed errors in historical data

```yaml
# You have two choices:

# Option A: Use old version (original data)
cutoff_date: "2025-12-01"
delta_version: 48  # Before correction

# Option B: Use new version (corrected data)
cutoff_date: "2025-12-01"
delta_version: 52  # After correction
```

## Important: VACUUM Policy

### The ONE Risk

If someone runs:
```sql
VACUUM delta_table RETAIN 168 HOURS;  -- 7 days
```

And deletes Delta v50's files, your MLTable breaks!

### Solution: Long Retention

Set Delta retention to 5+ years:

```sql
ALTER TABLE sensor_data 
SET TBLPROPERTIES (
  'delta.deletedFileRetentionDuration' = 'interval 1825 days'  -- 5 years
);
```

Or in Synapse notebook:
```python
spark.conf.set(
    "spark.databricks.delta.deletedFileRetentionDuration",
    "interval 1825 days"
)
```

### Document the Policy

Create `VACUUM_POLICY.md`:

```markdown
# Delta VACUUM Policy

⚠️ DO NOT run VACUUM on sensor_data table

**Reason:** MLTable Data Assets reference specific Delta versions.
Running VACUUM will break training reproducibility.

**Retention:** 5 years (1825 days)

**If storage cleanup needed:**
1. Check oldest MLTable reference
2. Only VACUUM versions older than that
3. Update this document with date
```

## Files Modified

```
config/
├── circuits.yaml  (✅ Added delta_version to all circuits)

scripts/
├── generate_mltable.py  (✅ Uses delta_version from config)
├── register_mltable.py  (✅ Stores delta_version in tags)
└── check_delta_version.py  (✅ New utility)

requirements.txt  (✅ Added deltalake==0.10.0)
```

## Quick Reference Commands

```bash
# Check current Delta version
python scripts/check_delta_version.py \
    --path /processed/sensor_data \
    --storage mystorageaccount

# Generate MLTables with Delta version
python scripts/generate_mltable.py \
    --config config/circuits.yaml \
    --output-dir mltables

# Register with tags
az ml data create \
    --name PLANT001_CIRCUIT01 \
    --version $(date +%Y-%m-%d) \
    --type mltable \
    --path mltables/PLANT001_CIRCUIT01
```

## Benefits

✅ **Simple**: Just add one field to configs  
✅ **Explicit**: You control which version  
✅ **Reproducible**: Always read same data  
✅ **Trackable**: Git tracks version changes  
✅ **Flexible**: Different circuits can use different versions  

## Example: End-to-End Flow

**Day 1: Initial Training**
```yaml
# config/circuits.yaml
cutoff_date: "2025-12-09"
delta_version: 42
```
→ MLTable v1 reads Delta v42 with date filter  
→ Model v1 trained on 50,000 rows

**Day 30: Retrain with More Data**
```yaml
# config/circuits.yaml (updated)
cutoff_date: "2026-01-09"  # New month
delta_version: 52          # Current Delta version
```
→ MLTable v2 reads Delta v52 with new date filter  
→ Model v2 trained on 55,000 rows

**Day 180: Verify Old Model**
→ MLTable v1 **still reads Delta v42**  
→ Still gets 50,000 rows (reproducible!) ✅

## FAQ

**Q: Do all circuits need the same delta_version?**  
A: No! Each circuit can have different versions.

**Q: What if I forget to update delta_version?**  
A: Old version still works, you just won't have latest data.

**Q: Can I change cutoff_date without changing delta_version?**  
A: Yes, but only if that date range exists in that Delta version.

**Q: How do I know which Delta version has my cutoff date?**  
A: Run `check_delta_version.py` to see date ranges per version.

---

**Implementation Date:** December 14, 2025  
**Approach:** Manual Delta version specification  
**Status:** ✅ Production ready
