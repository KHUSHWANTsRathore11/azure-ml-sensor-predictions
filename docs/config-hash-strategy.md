# Config Hash Strategy

## Overview

The config hash is a deterministic fingerprint of a circuit's training configuration that enables precise model lineage tracking across the entire MLOps pipeline lifecycle.

## Problem Statement

**Original Issue:**
- Release pipelines query ALL circuits from `circuits.yaml` (e.g., 100 circuits)
- Only a subset of circuits are trained in develop branch (e.g., 2 models)
- Release pipeline fails with "no models found" because it looks for all 100 circuits
- No mechanism to link models to the exact configuration that created them

**Root Cause:**
- Lack of deterministic identifier linking models to their training configuration
- Disconnection between develop branch (training) and release branch (deployment) artifacts
- No way to detect when configuration changes require retraining

## Solution: Configuration Hash

### What is the Config Hash?

A **12-character MD5 hash** generated from a circuit's complete training configuration, including:
- Model hyperparameters
- Feature selection
- Data preprocessing settings
- Training parameters
- Cutoff date
- Any other configuration that affects model training

### How It Works

#### 1. Hash Generation (Build Stage)

```python
def generate_config_hash(config_dict: dict) -> str:
    """Generate deterministic hash from circuit config."""
    # Remove metadata to avoid circular dependency
    config_copy = config_dict.copy()
    config_copy.pop('metadata', None)
    
    # Convert to sorted YAML for deterministic output
    yaml_str = yaml.dump(config_copy, sort_keys=True, default_flow_style=False)
    
    # Generate MD5 hash and truncate to 12 characters
    hash_md5 = hashlib.md5(yaml_str.encode('utf-8'))
    return hash_md5.hexdigest()[:12]
```

**Location:** `scripts/generate_circuit_configs.py`

**When:** During the `RegisterInfrastructure` stage, before training begins

**Output:** Each circuit config file gets a `metadata` section:
```yaml
metadata:
  config_hash: "a1b2c3d4e5f6"
  generated_at: "2025-12-11T14:30:00Z"
  description: "Deterministic hash of circuit configuration for model tracking"
```

#### 2. Model Tagging (Training Stage)

When models are registered in the Dev workspace, they are tagged with:
- `plant_id`
- `circuit_id`
- `cutoff_date`
- **`config_hash`** ← Key addition
- `training_job`

**Example:**
```bash
az ml model create \
  --name plant001-circuit01 \
  --type custom_model \
  --set tags.config_hash=a1b2c3d4e5f6 \
  --set tags.cutoff_date=2025-12-11 \
  ...
```

#### 3. Registry Promotion (Develop Branch)

Models are promoted from Dev workspace to Registry using `az ml model share`, which **preserves all tags** including `config_hash`.

The promotion stage checks for existing models by config_hash + version:
```python
check_cmd = [
    'az', 'ml', 'model', 'list',
    '--name', model_name,
    '--registry-name', registry_name,
    '--query', f"[?tags.config_hash=='{config_hash}' && version=='{version}']"
]
```

#### 4. Model Discovery (Release Branch)

**This is where the magic happens:**

Instead of querying for ALL circuits in `circuits.yaml`, the release pipeline:

1. Generates circuit configs (with current config hashes)
2. Loads each individual config file to get the config_hash
3. Queries Registry **ONLY** for models matching the current config_hash
4. Deploys only those models

```python
# Load circuit config to get config_hash
with open(f'config/circuits/{plant_id}_{circuit_id}.yaml', 'r') as f:
    circuit = yaml.safe_load(f)

config_hash = circuit['metadata']['config_hash']

# Query Registry by config_hash (not by all circuits!)
check_cmd = [
    'az', 'ml', 'model', 'list',
    '--name', model_name,
    '--registry-name', registry_name,
    '--query', f"[?tags.config_hash=='{config_hash}'] | [0]"
]
```

**Result:**
- ✅ Only finds models that match the CURRENT configuration
- ✅ Ignores circuits that haven't been trained
- ✅ Handles partial training runs gracefully
- ✅ Detects configuration changes automatically

## Benefits

### 1. Deterministic Model Tracking
- Same configuration → Same hash
- Different configuration → Different hash
- Enables precise lineage tracking

### 2. Partial Training Support
- Scenario: 100 circuits in config, only 2 trained
- Old behavior: Fails looking for all 100
- **New behavior: Succeeds deploying only the 2 with matching config hashes**

### 3. Configuration Change Detection
- If cutoff_date changes: New hash → Requires retraining
- If hyperparameters change: New hash → Requires retraining
- If only metadata changes: Same hash → No retraining needed

### 4. Retraining Flexibility
- Same config can be retrained multiple times
- Each training gets a new version (1, 2, 3...)
- All versions share the same config_hash
- Latest version is always retrieved

### 5. Cross-Pipeline Artifact Linking
- Develop branch: Tags models with config_hash
- Release branch: Queries models by config_hash from current configs
- **No need to pass artifact files between branches**
- Works even if release pipeline runs weeks later

## Example Scenarios

### Scenario 1: Normal Training Flow

1. **Develop Branch:** Train PLANT001_CIRCUIT01 with cutoff_date=2025-12-11
   - Config hash: `a1b2c3d4e5f6`
   - Model registered: `plant001-circuit01:v1` (tagged with hash)
   - Model promoted to Registry

2. **Release Branch (same day):**
   - Generate configs → Hash: `a1b2c3d4e5f6`
   - Query Registry by hash → Finds `v1`
   - Deploy to Test ✅

3. **Main Branch:**
   - Query Registry by hash + `production_ready=true`
   - Deploy to Production ✅

### Scenario 2: Partial Training

1. **Config:** 100 circuits defined
2. **Develop Branch:** Only train 2 circuits
   - PLANT001_CIRCUIT01: hash `a1b2c3d4e5f6` → v1
   - PLANT002_CIRCUIT05: hash `x9y8z7w6v5u4` → v1
   
3. **Release Branch:**
   - Generate 100 configs (100 hashes)
   - Query Registry for each hash
   - **Find only 2 models** (matching hashes)
   - Deploy only those 2 ✅
   - No failure! The other 98 simply aren't ready yet

### Scenario 3: Configuration Update

1. **Week 1:** Train with cutoff_date=2025-12-11
   - Hash: `a1b2c3d4e5f6`
   - Model: v1

2. **Week 2:** Update cutoff_date=2025-12-18 (new data)
   - Hash: `b2c3d4e5f6a7` (different!)
   - Model: v2 (new version)

3. **Release Branch:**
   - Current config has hash `b2c3d4e5f6a7`
   - Query finds v2 (not v1)
   - Deploys the model trained with current config ✅

### Scenario 4: Retraining with Same Config

1. **First training:**
   - Config hash: `a1b2c3d4e5f6`
   - Model: v1

2. **Retraining (same config):**
   - Config hash: `a1b2c3d4e5f6` (unchanged)
   - Model: v2 (new version)

3. **Query behavior:**
   - `[?tags.config_hash=='a1b2c3d4e5f6'] | [0]`
   - Returns the **first match** (v2 if sorted by version desc)
   - Deploys the latest training ✅

## Implementation Details

### Files Modified

1. **`scripts/generate_circuit_configs.py`**
   - Added `generate_config_hash()` function
   - Generates hash for each circuit
   - Adds metadata section to config files

2. **`.azuredevops/build-pipeline.yml`**
   - **RegisterModels:** Reads config_hash, tags models
   - **PromoteToRegistry:** Preserves config_hash during promotion
   - **VerifyRegistry (release):** Queries by config_hash instead of all circuits
   - **QASignOff:** Tags models with production_ready flag
   - **VerifyRegistryProd (main):** Queries by config_hash + production_ready

3. **Artifacts:**
   - `registered_models.json`: Now includes config_hash field
   - `config/circuits/*.yaml`: Now includes metadata.config_hash

### Key Design Decisions

#### Why MD5?
- Fast and deterministic
- 12 characters provide sufficient uniqueness
- Collision risk negligible for this use case
- Alternative: SHA256 (overkill for our needs)

#### Why 12 Characters?
- Balances uniqueness vs. readability
- Full MD5 (32 chars) is too long for tags
- 12 chars = 16^12 = 2.8 × 10^14 possible values
- Collision probability: ~1 in a trillion for 100 circuits

#### Why Not Include Environment/Code Version?
- Config hash represents **training configuration only**
- Environment version tracked separately in tags
- Code version tracked via Git commit/pipeline ID
- Separation of concerns enables independent updates

#### Why Remove Metadata from Hash?
- Prevents circular dependency (metadata contains the hash)
- Generated_at timestamp would change hash every time
- Only configuration affecting model training should be included

## Limitations and Considerations

### Limitations

1. **YAML Serialization Consistency**
   - Requires `sort_keys=True` for deterministic output
   - Python dict ordering must be consistent

2. **Hash Collisions**
   - Theoretical but extremely unlikely with 12-char MD5
   - If collision occurs, use full 32-char hash

3. **Manual Config Changes**
   - Config hash only reflects what's in the file
   - Manual Registry operations bypass hash tracking

### Best Practices

1. **Never manually edit metadata.config_hash**
   - Always regenerate configs using the script

2. **Version control circuit configs**
   - Git history provides audit trail of config changes

3. **Monitor hash generation**
   - Log shows hash for each circuit during generation
   - Verify expected circuits have expected hashes

4. **Test hash consistency**
   - Same config should always generate same hash
   - Add unit test to verify deterministic behavior

## Monitoring and Debugging

### Logs to Check

1. **RegisterInfrastructure Stage:**
   ```
   ✅ Created: PLANT001_CIRCUIT01.yaml (hash: a1b2c3d4e5f6)
   ```

2. **RegisterModels Stage:**
   ```
   📊 Registering model: plant001-circuit01
      Config hash: a1b2c3d4e5f6
   ✅ Registered: plant001-circuit01:v1 (config_hash=a1b2c3d4e5f6)
   ```

3. **VerifyRegistry Stage (Release):**
   ```
   🔍 Checking: plant001-circuit01 (config_hash: a1b2c3d4e5f6)
   ✅ Found: plant001-circuit01:v1 (config_hash=a1b2c3d4e5f6)
   ```

### Common Issues

**Issue:** "Not found in Registry: model_name (config_hash=...)"

**Causes:**
- Model not yet trained in develop branch
- Configuration changed since training
- Model failed to promote to Registry

**Resolution:**
- Check develop branch pipeline logs
- Verify model exists in Dev workspace
- Compare config_hash in workspace vs. Registry

## Future Enhancements

1. **Hash Collision Detection**
   - Add validation to detect duplicate hashes
   - Alert on collision (extremely rare)

2. **Config Drift Detection**
   - Compare Registry model hash vs. current config hash
   - Alert when deployed model config differs from current

3. **Hash-Based Retraining**
   - Automatically trigger retraining when hash changes
   - Skip training if model with current hash already exists

4. **Multi-Version Deployment**
   - Deploy multiple versions with same config_hash
   - Enable A/B testing or canary deployments

5. **Config Hash API**
   - Expose hash calculation as reusable function
   - Enable external tools to compute hashes

## Summary

The config hash strategy solves the critical problem of artifact tracking across pipeline runs by creating a deterministic fingerprint of each circuit's training configuration. This enables:

- **Precise model lineage tracking** across dev/test/prod
- **Graceful handling of partial training runs** (deploy only what's ready)
- **Automatic configuration change detection** (retrain when config changes)
- **Independent pipeline runs** (release doesn't depend on develop artifacts)

The implementation is simple, efficient, and maintainable, requiring only:
- 12-character hash stored in config metadata
- Model tag during registration
- Query by hash during deployment

This architecture pattern can be extended to other MLOps scenarios requiring deterministic tracking across distributed systems.
