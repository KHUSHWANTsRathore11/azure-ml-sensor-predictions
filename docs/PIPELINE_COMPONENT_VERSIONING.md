# Pipeline Component Versioning Strategy

## Motivation

### Two Distinct Version Fields

**`environment_version`** - Environment Registration Only
- Used in **Stage 1 & 2** (RegisterEnvironment, PromoteEnvironment)
- Purpose: Check if environment needs registration/promotion
- Scope: Azure ML environment management
- **NOT used in training or model lineage**

**`pipeline_component_version`** - Training & Model Lineage
- Used in **Stage 5-7** (SubmitTraining, MonitorTraining, RegisterModels)
- Purpose: Track which component version was used for training
- Scope: Model reproducibility and lineage
- **Included in training hash**

### Why Separate Them?

**Problem with Single Version:**
- Environment changes don't always require retraining
- Component logic can change without environment changes
- Mixing concerns makes it unclear what triggers retraining

**Solution: Two Independent Versions:**
```yaml
circuits:
  - pipeline_component_version: "1.0.0"  # Training execution
    environment_version: "1.0.0"          # Environment registration
```

## Use Cases

### Scenario 1: Environment Update (No Retraining)
```yaml
# Update Python package in environment
environment_version: "1.0.0" → "1.1.0"  # Triggers env registration
pipeline_component_version: "1.0.0"      # No change → No retraining
```

### Scenario 2: Component Logic Change (Retraining)
```yaml
# Add new preprocessing step to component
environment_version: "1.0.0"             # No change
pipeline_component_version: "1.0.0" → "1.1.0"  # Triggers retraining
```

### Scenario 3: Both Change
```yaml
# New component needs new environment
environment_version: "1.0.0" → "2.0.0"   # Triggers env registration
pipeline_component_version: "1.0.0" → "2.0.0"  # Triggers retraining
```

## Architecture

```
Circuit Configuration (circuits.yaml)
├─ pipeline_component_version: "1.0.0"  ← Single version reference
   ↓
Pipeline Component (training-pipeline-component.yaml)
├─ version: "1.0.0"
├─ Job 1: Data Preparation
│  └─ environment: data-prep-env:2.0.0
├─ Job 2: Feature Engineering  
│  └─ environment: feature-eng-env:1.5.0
├─ Job 3: Model Training
│  └─ environment: training-env:3.0.0
└─ Job 4: Model Evaluation
   └─ environment: eval-env:1.0.0
```

## Benefits

### 1. **Scalability**
- Add new jobs without changing circuit config
- Each job can evolve its environment independently
- Component manages internal complexity

### 2. **Reproducibility**
- Component version in training hash ensures exact pipeline reproduction
- All jobs, environments, and logic versioned together
- No ambiguity about which environment versions were used

### 3. **Flexibility**
- Support nested pipelines (pipeline calling pipeline)
- Each nested pipeline has its own environments
- Component version tracks the entire execution graph

### 4. **Simplicity**
- Circuit config only needs one version field
- Component handles all internal versioning
- Clear separation of concerns

## Example: Multi-Job Pipeline

### Current (Simple)
```yaml
# Component: training-pipeline-component.yaml v1.0.0
jobs:
  train:
    type: command
    environment: azureml:custom-training-env:1.0.0
    command: python train.py
```

### Future (Complex)
```yaml
# Component: training-pipeline-component.yaml v2.0.0
jobs:
  prepare_data:
    type: command
    environment: azureml:data-prep-env:2.0.0
    command: python prepare.py
    
  feature_engineering:
    type: command
    environment: azureml:feature-eng-env:1.5.0
    command: python features.py
    
  train_model:
    type: command
    environment: azureml:training-env:3.0.0
    command: python train.py
    
  evaluate:
    type: command
    environment: azureml:eval-env:1.0.0
    command: python evaluate.py
```

**Circuit config stays the same:**
```yaml
pipeline_component_version: "2.0.0"  # Just update this
```

## Training Hash Calculation

**Only `pipeline_component_version` is included in the hash:**

```python
def calculate_training_hash(circuit_cfg: dict) -> str:
    """
    Calculate training configuration hash for model lineage.
    
    IMPORTANT: environment_version is NOT included.
    Environment changes don't trigger retraining.
    """
    hash_components = {
        'cutoff_date': circuit_cfg.get('cutoff_date'),
        'delta_version': circuit_cfg.get('delta_version'),
        'pipeline_component_version': circuit_cfg.get('pipeline_component_version'),  # ← Included
        'training_days': circuit_cfg.get('training_days'),
        'hyperparameters': circuit_cfg.get('hyperparameters', {}),
        # environment_version: NOT included - only for registration
    }
    return hashlib.md5(json.dumps(hash_components, sort_keys=True).encode()).hexdigest()[:12]
```

**Why this works:**
- Component version changes → hash changes → triggers retraining
- Environment version changes → hash unchanged → no retraining
- Clear separation: environment management vs training execution

## Pipeline Stages Usage

### Stage 1-2: Environment Management
```yaml
# Uses: environment_version
- Stage 1: RegisterEnvironment
  - Reads: config/environment.yaml (has version field)
  - Checks: Does this environment version exist?
  - Action: Register if not found
  
- Stage 2: PromoteEnvironment
  - Condition: Only if new environment registered
  - Action: Share environment to registry
```

### Stage 3: Component Registration
```yaml
# Uses: component version from component file
- Stage 3: RegisterComponents
  - Reads: components/training-pipeline-component.yaml (has version field)
  - Checks: Does this component version exist?
  - Action: Register if not found
```

### Stage 5-7: Training & Model Registration
```yaml
# Uses: pipeline_component_version from circuits.yaml
- Stage 5: SubmitTraining
  - Reads: pipeline_component_version from circuits.yaml
  - Calculates: training_hash (includes component version)
  - Action: Submit training job with hash tag
  
- Stage 6: MonitorTraining
  - Monitors: Jobs submitted in Stage 5
  
- Stage 7: RegisterModels
  - Tags: Model with training_hash
  - Lineage: Hash includes component version → reproducible
```

## Migration Path

### Phase 1: Single Environment (Current)
```yaml
circuits:
  - pipeline_component_version: "1.0.0"
    environment_version: "1.0.0"  # Still here for backward compat
```

### Phase 2: Remove Environment Version (Future)
```yaml
circuits:
  - pipeline_component_version: "2.0.0"  # Only this needed
```

Component manages all environments internally.

## Best Practices

### When to Bump `environment_version`

**Bump when:**
- Python package versions change
- System dependencies change
- Docker base image changes
- Environment configuration changes

**Don't bump when:**
- Only component logic changes
- Only hyperparameters change
- Only data settings change

**Effect:**
- Triggers environment registration (Stage 1)
- May trigger environment promotion (Stage 2)
- **Does NOT trigger retraining**

### When to Bump `pipeline_component_version`

**Bump when:**
- Pipeline logic changes
- New jobs added/removed
- Component inputs/outputs change
- Job orchestration changes

**Don't bump when:**
- Only environment changes
- Only circuit-specific settings change (hyperparameters, cutoff_date)

**Effect:**
- Triggers component registration (Stage 3)
- **Triggers retraining** (hash changes)
- Updates model lineage

### Version Naming

Both use semantic versioning: `major.minor.patch`

**Environment Version:**
- Major: Breaking changes (Python version, major package upgrades)
- Minor: New packages, minor upgrades
- Patch: Bug fixes, patch updates

**Component Version:**
- Major: Breaking changes (schema, outputs)
- Minor: New features (new jobs, new logic)
- Patch: Bug fixes (same functionality)

### Example Workflow

**1. Update Environment:**
```bash
# Update config/environment.yaml
version: "1.0.0" → "1.1.0"

# Update circuits.yaml
environment_version: "1.0.0" → "1.1.0"

# Pipeline runs:
# - Stage 1: Registers new environment
# - Stage 2: Promotes to registry
# - Stage 5-7: Uses OLD component version → No retraining
```

**2. Update Component:**
```bash
# Update components/training-pipeline-component.yaml
version: "1.0.0" → "1.1.0"

# Update circuits.yaml
pipeline_component_version: "1.0.0" → "1.1.0"

# Pipeline runs:
# - Stage 1-2: Skips (environment unchanged)
# - Stage 3: Registers new component
# - Stage 5-7: Uses NEW component → Triggers retraining
```

**3. Update Both:**
```bash
# Update both files
environment.yaml: version "1.0.0" → "2.0.0"
component.yaml: version "1.0.0" → "2.0.0"

# Update circuits.yaml
environment_version: "1.0.0" → "2.0.0"
pipeline_component_version: "1.0.0" → "2.0.0"

# Pipeline runs all stages with new versions
```

## Related Files

- `config/circuits.yaml` - Circuit configs with `pipeline_component_version`
- `components/training-pipeline-component.yaml` - Component definition with `version`
- `scripts/pipeline/submit_training_jobs.py` - Hash calculation including component version
- `.azuredevops/training-pipeline.yml` - Component registration (Stage 3)
