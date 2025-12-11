# Training Trigger Logic and Error Handling Analysis

## Overview

This document analyzes the training trigger mechanisms and error handling strategies in the MLOps pipeline, identifying potential issues and recommending improvements.

---

## 🚀 Training Trigger Logic

### Current Implementation

#### 1. **Pipeline Triggers** (`.azuredevops/build-pipeline.yml`)

```yaml
trigger:
  branches:
    include:
      - develop
      - release/*
      - main
  paths:
    include:
      - config/circuits.yaml          # Circuit configs
      - config/environment.yaml       # Environment definition
      - components/**                 # Component definitions
      - src/packages/**               # Source code
```

**What triggers training:**
- ✅ Push to `develop` branch
- ✅ Changes to `config/circuits.yaml`
- ✅ Changes to `config/environment.yaml`
- ✅ Changes to `components/**`
- ✅ Changes to `src/packages/**`

**What does NOT trigger training:**
- ❌ Push to `release/*` or `main` (these only deploy from Registry)
- ❌ Changes to documentation files
- ❌ Changes to scripts (unless in `src/packages/`)
- ❌ Pull requests (PRs only validate, don't train)

#### 2. **Change Detection** (`scripts/detect_config_changes.py`)

The script uses **git diff** to detect which circuits have changed:

```python
# Compare current branch with target branch (default: main)
git diff --unified=0 origin/main...HEAD config/circuits.yaml
```

**Logic:**
1. Compare current `circuits.yaml` with the version in `origin/main`
2. Parse diff output to extract changed circuit IDs
3. Return full circuit configs for changed circuits
4. If target branch doesn't exist (first run), return **ALL circuits**
5. If diff parsing fails, return **ALL circuits** (safety fallback)

**What counts as a "change":**
- ✅ New circuit added
- ✅ Existing circuit modified (any field: cutoff_date, hyperparameters, etc.)
- ✅ Circuit removed (won't be in changed list, but old models remain)

**Example changed circuit detection:**
```python
# Circuit PLANT001/CIRCUIT01 changed:
{
  "plant_id": "PLANT001",
  "circuit_id": "CIRCUIT01",
  "cutoff_date": "2025-12-11",  # Changed from "2025-12-04"
  "model_name": "plant001-circuit01",
  "change_type": "modified"
}
```

---

## ⚠️ Potential Issues with Current Trigger Logic

### Issue 1: **Overly Broad Triggers**

**Problem:**
- Changing `config/environment.yaml` triggers training for **all detected circuits**
- Changing any component in `components/**` triggers training
- Changing any source code in `src/packages/**` triggers training

**Impact:**
- Environment version bump → Retrains all changed circuits (may be unnecessary)
- Component version bump → Retrains all changed circuits (may be unnecessary)
- Code refactoring → Triggers training (may be unintended)

**Scenario:**
```yaml
# Day 1: Update cutoff_date for CIRCUIT01
cutoff_date: "2025-12-11"  # Changed from "2025-12-04"
# Triggers: Training for CIRCUIT01 ✅

# Day 2: Bump environment version (unrelated change)
version: "2.1.0"  # Changed from "2.0.0"
# Triggers: Training for CIRCUIT01 AGAIN ❌ (unnecessary retrain)
```

**Recommendation:**
Consider separating triggers:
```yaml
# Option A: Separate pipelines
# build-pipeline-training.yml - Triggered by circuits.yaml only
# build-pipeline-env.yml - Triggered by environment.yaml only

# Option B: Conditional stages
- stage: TrainModels
  condition: |
    or(
      eq(variables['Build.Reason'], 'Manual'),
      contains(variables['Build.SourceVersionMessage'], '[train]'),
      contains(variables['System.PullRequest.SourceBranch'], 'feature/training')
    )
```

### Issue 2: **Git Diff Parsing Fragility**

**Problem:**
The diff parsing logic in `detect_config_changes.py` is fragile:

```python
# This pattern matching can fail:
if 'plant_id:' in line and (line.startswith('+') or line.startswith('-')):
    parts = line.split('"')
    if len(parts) >= 2:
        current_plant = parts[1]
```

**Failure scenarios:**
1. **YAML formatting changes:** If someone reformats the YAML (quotes → no quotes), the parsing breaks
2. **Multiline values:** If a field spans multiple lines, the parser misses it
3. **Indentation changes:** Pure indentation changes trigger the "train all" fallback

**Example failure:**
```yaml
# Before (double quotes)
plant_id: "PLANT001"

# After (single quotes or no quotes)
plant_id: 'PLANT001'
plant_id: PLANT001

# Parser may fail to extract plant_id correctly
```

**Safety fallback (too aggressive):**
```python
# If we can't parse specific circuits, train all (safety fallback)
if not changed_circuits and "circuits:" in diff_output:
    print("⚠️  Could not parse specific changes, returning all circuits")
    return current_config.get("circuits", [])
```

**Impact:**
- YAML formatting PR → Retrains ALL circuits (100+ models)
- Cost: Potentially thousands of dollars
- Duration: Hours of training time

**Recommendation:**
Use **config hash comparison** instead of git diff parsing:

```python
def get_changed_circuits_by_hash() -> List[Dict]:
    """
    Compare current config hashes with previously trained models.
    Much more robust than git diff parsing.
    """
    with open("config/circuits.yaml", "r") as f:
        current_circuits = yaml.safe_load(f)["circuits"]
    
    changed = []
    for circuit in current_circuits:
        # Generate config file to get hash
        generate_circuit_config(circuit)
        config_file = f"config/circuits/{circuit['plant_id']}_{circuit['circuit_id']}.yaml"
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        current_hash = config['metadata']['config_hash']
        model_name = circuit['model_name']
        
        # Query Dev workspace for model with this hash
        result = subprocess.run([
            'az', 'ml', 'model', 'list',
            '--name', model_name,
            '--query', f"[?tags.config_hash=='{current_hash}']",
            '--workspace-name', WORKSPACE
        ], capture_output=True, text=True)
        
        # If no model with this hash exists, circuit has changed
        if not result.stdout.strip() or result.stdout.strip() == '[]':
            changed.append(circuit)
    
    return changed
```

### Issue 3: **First Run Behavior**

**Problem:**
On first pipeline run (when `origin/main` doesn't exist), the script returns **ALL circuits**:

```python
if branch_check.returncode != 0:
    print(f"ℹ️  Branch origin/{target_branch} not found. This appears to be the first run.")
    print("   Returning all circuits for training.")
    return current_config.get("circuits", [])
```

**Impact:**
- Initial setup → Trains 100+ models
- Could cost thousands of dollars
- Takes hours to complete
- May overwhelm Azure ML quotas

**Scenario:**
- New repository setup
- Forked repository
- Branch renamed from `master` to `main`

**Recommendation:**
Add explicit flag for initial training:
```python
# Add command-line flag
parser.add_argument(
    "--initial-run",
    action="store_true",
    help="Explicitly train all circuits (use for first run)"
)

# Require explicit opt-in for training all
if branch_check.returncode != 0:
    if args.initial_run:
        print("🚀 Initial run mode: Training all circuits")
        return current_config.get("circuits", [])
    else:
        print("❌ Target branch not found and --initial-run not specified")
        print("   If this is the first run, use: --initial-run")
        sys.exit(1)
```

---

## ❌ Error Handling Analysis

### Current Error Handling Strategy

#### 1. **Job Submission Failures** (All-or-Nothing with Retry)

**Strategy:** If ANY job submission fails after 3 retries, **cancel ALL submitted jobs** and fail the pipeline.

```python
# Retry logic: 3 attempts (1 initial + 2 retries)
max_retries = 2
retry_count = 0
success = False

while retry_count <= max_retries and not success:
    if retry_count > 0:
        wait_time = 30 * retry_count  # 30s, 60s
        time.sleep(wait_time)
    
    result = subprocess.run(cmd, ...)
    
    if result.returncode == 0:
        success = True
    else:
        retry_count += 1

# If all retries failed, cancel everything
if not success:
    for job_info in submitted_jobs:
        az ml job cancel --name {job_name}
    
    sys.exit(1)  # Fail pipeline
```

**Pros:**
- ✅ Prevents partial training runs
- ✅ Ensures consistency (either all circuits trained or none)
- ✅ Avoids wasted compute on circuits that won't be promoted together

**Cons:**
- ❌ One flaky circuit blocks all others
- ❌ If circuit #50 fails, circuits #1-49 are cancelled (wasted work)
- ❌ No way to partially recover

**Recommendation:** This is actually a **good strategy** for the use case. Rationale:
- Models are deployed together as a batch
- Partial training creates inconsistent model sets
- Better to fail fast and fix the issue than have partial deployments

**Alternative (if partial training is acceptable):**
```python
# Continue on failure, track failed submissions
if not success:
    failed_submissions.append({
        'plant_id': plant_id,
        'circuit_id': circuit_id,
        'error': last_error
    })
    print(f"⚠️  Failed to submit {plant_id}/{circuit_id}, continuing...")
    # Don't cancel others
```

#### 2. **Training Job Failures** (Continue with Successful Jobs)

**Strategy:** Wait for all jobs, skip failed jobs during registration.

```python
while pending:
    time.sleep(60)  # Poll every minute
    
    for job_name in list(pending):
        job = ml_client.jobs.get(job_name)
        status = job.status
        
        if status == 'Completed':
            completed.append(job_name)
        elif status in ['Failed', 'Canceled']:
            failed.append(job_name)  # Track but don't fail pipeline
        
        pending.remove(job_name)

# Continue with successful jobs only
if not completed:
    print("⚠️  WARNING: No jobs completed successfully")
    print("   Pipeline will continue but no models will be registered")
```

**Pros:**
- ✅ Gracefully handles partial failures
- ✅ Registers successful models
- ✅ Doesn't waste completed training work

**Cons:**
- ❌ Silent failures (pipeline succeeds even if all training fails)
- ❌ No notification of failed circuits
- ❌ Deployment may proceed with incomplete model set

**Issue:** The pipeline continues even if **all training jobs fail**:

```python
if not completed:
    print("⚠️  WARNING: No jobs completed successfully")
    # Don't fail - just proceed with empty completed list
```

**Impact:**
- RegisterModels stage creates empty `registered_models.json`
- PromoteToRegistry stage skips promotion (no models)
- **Pipeline shows as "successful"** even though nothing trained
- User may not notice the failure until deployment

**Recommendation:** Add threshold-based failure:

```python
# Calculate success rate
total_jobs = len(submitted_jobs)
success_rate = len(completed) / total_jobs if total_jobs > 0 else 0

# Define acceptable threshold (e.g., 80%)
REQUIRED_SUCCESS_RATE = 0.80

if success_rate < REQUIRED_SUCCESS_RATE:
    print(f"❌ CRITICAL: Only {success_rate:.1%} of jobs completed successfully")
    print(f"   Required: {REQUIRED_SUCCESS_RATE:.1%}")
    print(f"   Completed: {len(completed)}/{total_jobs}")
    print("\nFailed jobs:")
    for job in failed:
        print(f"   - {job}")
    sys.exit(1)  # Fail pipeline

if failed:
    print(f"⚠️  WARNING: {len(failed)} job(s) failed but success rate acceptable")
    print(f"   Success rate: {success_rate:.1%} (threshold: {REQUIRED_SUCCESS_RATE:.1%})")
```

#### 3. **Model Registration Failures** (Continue on Failure)

**Strategy:** Try to register all completed jobs, track failures, but **don't fail pipeline**.

```python
for key, job_info in completed_job_map.items():
    # ... registration logic ...
    
    if result.returncode != 0:
        print(f"❌ Failed to register {model_name}")
        failed.append(f"{plant_id}/{circuit_id}")
        # Continue to next circuit (don't exit)

# At the end, no sys.exit(1) even if some failed
if not registered_models:
    print("⚠️  WARNING: No models were successfully registered")
    # Don't fail - just proceed
```

**Issue:** Same as training failures - pipeline succeeds even if registration completely fails.

**Recommendation:** Same threshold-based approach:

```python
# Registration success rate
total_to_register = len(completed_job_map)
registration_success_rate = len(registered_models) / total_to_register if total_to_register > 0 else 0

REQUIRED_REGISTRATION_RATE = 0.90  # 90% must register successfully

if registration_success_rate < REQUIRED_REGISTRATION_RATE:
    print(f"❌ CRITICAL: Only {registration_success_rate:.1%} of models registered")
    print(f"   Required: {REQUIRED_REGISTRATION_RATE:.1%}")
    sys.exit(1)
```

---

## 🔧 Recommended Improvements

### 1. **Replace Git Diff with Config Hash Comparison**

**Current:**
```python
# Fragile git diff parsing
diff_output = git diff origin/main...HEAD config/circuits.yaml
changed_circuits = parse_diff(diff_output)
```

**Proposed:**
```python
# Robust config hash comparison
for circuit in circuits:
    current_hash = generate_config_hash(circuit)
    
    # Check if model with this hash exists in workspace
    existing = query_workspace_by_hash(current_hash, model_name)
    
    if not existing:
        changed_circuits.append(circuit)  # Needs training
```

**Benefits:**
- ✅ Immune to YAML formatting changes
- ✅ Deterministic detection (hash-based)
- ✅ Detects actual config changes, not formatting
- ✅ Works across branches and forks

### 2. **Add Failure Thresholds**

**Training stage:**
```python
REQUIRED_SUCCESS_RATE = float(os.getenv('TRAINING_SUCCESS_THRESHOLD', '0.80'))

if success_rate < REQUIRED_SUCCESS_RATE:
    sys.exit(1)
```

**Registration stage:**
```python
REQUIRED_REGISTRATION_RATE = float(os.getenv('REGISTRATION_SUCCESS_THRESHOLD', '0.90'))

if registration_success_rate < REQUIRED_REGISTRATION_RATE:
    sys.exit(1)
```

**Make thresholds configurable via pipeline variables:**
```yaml
variables:
  - name: trainingSuccessThreshold
    value: '0.80'  # 80% of training jobs must succeed
  - name: registrationSuccessThreshold
    value: '0.90'  # 90% of registrations must succeed
```

### 3. **Add Explicit Training Control**

**Option A: Manual approval before training**
```yaml
- stage: TrainModels
  dependsOn: RegisterInfrastructure
  jobs:
    - deployment: TrainingApproval
      environment: 'training-approval'  # Requires manual approval
      strategy:
        runOnce:
          deploy:
            steps:
              - script: echo "Training approved"
    
    - job: ParallelTraining
      dependsOn: TrainingApproval
      # ... existing training logic ...
```

**Option B: Commit message flag**
```yaml
- stage: TrainModels
  condition: |
    and(
      ne(variables['Build.Reason'], 'PullRequest'),
      or(
        eq(variables['Build.Reason'], 'Manual'),
        contains(variables['Build.SourceVersionMessage'], '[train]')
      )
    )
```

Usage:
```bash
git commit -m "Update cutoff dates [train]"  # Triggers training
git commit -m "Update cutoff dates"          # No training
```

### 4. **Add Detailed Error Notifications**

**Send notifications on failures:**
```yaml
- task: SendEmail@1
  condition: failed()
  inputs:
    to: 'ml-ops-team@company.com'
    subject: '[ALERT] Training Pipeline Failed - $(Build.DefinitionName)'
    body: |
      Pipeline: $(Build.DefinitionName)
      Build: $(Build.BuildNumber)
      Branch: $(Build.SourceBranchName)
      
      Failed jobs: $(FailedJobCount)
      Success rate: $(SuccessRate)
      
      View logs: $(System.TeamFoundationCollectionUri)$(System.TeamProject)/_build/results?buildId=$(Build.BuildId)
```

### 5. **Add Retry Logic for Individual Job Failures**

**Currently:** Retry only submission failures, not job failures.

**Proposed:** Add automatic retry for failed training jobs:

```python
# After initial training run
failed_jobs = []  # Jobs that failed or were cancelled

# Retry failed jobs (up to 2 times)
for retry_attempt in range(2):
    if not failed_jobs:
        break
    
    print(f"\n🔄 Retry attempt {retry_attempt + 1} for {len(failed_jobs)} failed job(s)")
    
    retry_results = []
    for job_info in failed_jobs:
        # Resubmit with new job name
        new_job_name = f"{job_info['job_name']}_retry{retry_attempt + 1}"
        # ... submit job ...
        retry_results.append((job_info, new_job_name))
    
    # Wait for retry jobs
    # ... polling logic ...
    
    # Update failed_jobs list with still-failed jobs
    failed_jobs = [j for j in retry_results if status == 'Failed']
```

---

## 📊 Summary of Recommendations

### High Priority (Implement First)

1. **✅ Keep all-or-nothing job submission strategy** (already good)
2. **🔧 Add failure thresholds** for training and registration (80% / 90%)
3. **🔧 Add config hash-based change detection** (replace git diff)
4. **📧 Add failure notifications** (email/Teams/Slack)

### Medium Priority

5. **🎯 Add explicit training control** (commit message flag or manual approval)
6. **🔁 Add automatic retry for failed training jobs**
7. **📝 Improve logging** (structured logs with timestamps)

### Low Priority

8. **🎛️ Make thresholds configurable** (pipeline variables)
9. **📊 Add training metrics dashboard** (success rates over time)
10. **🔔 Add Slack/Teams integration** for real-time alerts

---

## 🎯 Recommended Configuration

```yaml
# Pipeline variables
variables:
  - name: trainingSuccessThreshold
    value: '0.80'  # 80% of circuits must train successfully
  
  - name: registrationSuccessThreshold
    value: '0.90'  # 90% of models must register successfully
  
  - name: enableAutoRetry
    value: 'true'  # Automatically retry failed training jobs
  
  - name: maxRetryAttempts
    value: '2'  # Max retry attempts per job
  
  - name: changeDetectionMethod
    value: 'config_hash'  # 'git_diff' or 'config_hash'
```

This configuration provides a good balance of reliability, cost-efficiency, and operational safety.
