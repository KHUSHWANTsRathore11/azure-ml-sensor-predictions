# Training Retry and Manual Circuit Specification

This document explains how to use the automatic retry mechanism and manual circuit specification features in the Azure ML training pipeline.

## Features Overview

### 1. Automatic Retry for Failed Training Jobs

The pipeline includes an intelligent retry mechanism that automatically detects training failures and provides a streamlined way to retry only the failed circuits without affecting successful ones.

### 2. Manual Circuit Specification

You can manually specify which circuits to train, bypassing automatic change detection. This is useful for:
- Retrying specific circuits after fixing issues
- Training a single circuit for testing
- Re-training circuits without making config changes

## How Automatic Retry Works

### Failure Detection

1. The `WaitForTrainingJobs` stage monitors all training jobs
2. When jobs complete, it separates them into:
   - **Successful jobs** → Saved to `completed_jobs.json`
   - **Failed jobs** → Saved to `failed_jobs.json`
3. A pipeline variable `hasTrainingFailures` is set to indicate if there were failures

### Retry Stage Activation

The `RetryFailedTraining` stage only runs when:
- It's NOT a pull request build
- AND there are training failures (`hasTrainingFailures == 'true'`)

**If there are no failures, this stage is completely skipped** — no impact on normal flow!

### Retry Workflow

When failures are detected:

1. **Show Failed Circuits** (informational)
   - Lists all failed circuits with their job names
   - Provides context for approval decision

2. **Approval Gate** (manual intervention)
   - Environment: `training-retry`
   - Review the failed circuits
   - Check job logs in Azure ML Studio
   - Approve to proceed with retry

3. **Retry Failed Training Jobs**
   - Submits new training jobs for failed circuits only
   - Jobs are named with `_retry_<timestamp>` suffix
   - Uses the same config and data as original jobs

4. **Monitor Retry Jobs**
   - Waits for retry jobs to complete
   - Tracks success/failure rates

5. **Register Retry Models**
   - Registers successful retry models
   - Tags them with `retry=true`
   - **Merges with original models** → Single unified list

### Integration with Registry Promotion

The `PromoteToRegistry` stage intelligently handles retry scenarios:

```yaml
depends On:
  - TrainModels
  - RetryFailedTraining

condition:
  - TrainModels succeeded
  - RetryFailedTraining succeeded OR skipped
```

This means:
- ✅ Proceeds if no failures occurred (retry skipped)
- ✅ Proceeds if failures were retried and succeeded
- ❌ Blocks if retry was attempted but failed

## Manual Circuit Specification

### Pipeline Parameter

When running the pipeline manually, you can specify circuits to train:

```yaml
manualCircuits: 'flottec_2110,flottec_2130'
```

**Format:** `plant1_circuit1,plant2_circuit2` (comma-separated, no spaces)

### How to Use

#### Option 1: Azure DevOps UI

1. Navigate to your pipeline
2. Click "Run pipeline"
3. Expand "Advanced options"
4. Find "Manual Circuit Specification (Optional)"
5. Enter circuit names: `flottec_2110,flottec_2130`
6. Click "Run"

#### Option 2: Azure CLI

```bash
az pipelines run \
  --name "Azure-ML-Sensor-Training-Pipeline" \
  --variables manualCircuits="flottec_2110,flottec_2130"
```

### Behavior

When `manualCircuits` is specified:
- ✅ **Bypasses automatic change detection** (git diff ignored)
- ✅ Creates `changed_circuits.json` from manual specification
- ✅ Validates circuits exist in `config/circuits.yaml`
- ✅ Trains only the specified circuits
- ❌ Fails if any specified circuit is not found

When `manualCircuits` is empty (default):
- Uses automatic git diff-based change detection
- Trains circuits that have configuration changes

## Common Scenarios

### Scenario 1: Transient Failure - Retry All Failed Circuits

**Situation:** 4 circuits trained, 3 succeeded, 1 failed due to temporary compute issue

**Solution:**
1. Check pipeline logs to confirm transient nature
2. Wait for `RetryFailedTraining` stage to appear
3. Approve the retry gate
4. Failed circuit automatically retrains
5. Successful retry model merges with original 3 models
6. All 4 models proceed to Registry promotion

**No manual intervention needed beyond approval!**

### Scenario 2: Retry Single Circuit Manually

**Situation:** 1 circuit failed, you want to re-run it independently

**Solution:**
1. Run pipeline with manual circuit specification:
   ```
   manualCircuits: 'flottec_2110'
   ```
2. Only that circuit trains
3. Successful model registers normally

**When to use:** Testing fixes, one-off retraining, data quality issues fixed

### Scenario 3: Code Bug - Fix and Retry

**Situation:** Multiple circuits failed due to a code bug in training logic

**Solution:**
1. **Don't approve** the retry gate (cancel or reject)
2. Fix the code bug in your feature branch
3. Merge fix to `develop`
4. Pipeline runs automatically
5. Retry stage appears again for previous failures
6. Approve retry with fix in place

**Alternative:** Use manual circuit specification after fix is merged

### Scenario 4: Training subset for testing

**Situation:** Testing config changes on 2 circuits before full rollout

**Solution:**
1. Make config changes
2. Run pipeline manually:
   ```
   manualCircuits: 'flottec_2110,flottec_2130'
   ```
3. Only specified circuits train
4. Review results before deploying to all circuits

## Model Metadata

### Retry Models

Models registered from retry jobs have an additional tag:

```yaml
tags:
  plant_id: flottec
  circuit_id: 2110
  cutoff_date: 2024-01-15
  config_hash: a3b5c7d9e1f2
  training_job: flottec_2110_2024_01_15_retry_20250211_143022
  retry: true  # ← Identifies this as a retry model
```

This allows you to:
- Track which models came from retry operations
- Audit retry history
- Filter models by retry status if needed

## Pipeline Flow Diagrams

### Normal Flow (No Failures)

```
RegisterInfrastructure
  ↓
TrainModels
  → All jobs succeed
  ↓
RegisterModels
  ↓
[RetryFailedTraining] ← SKIPPED (no failures)
  ↓
PromoteToRegistry (uses original models)
```

### Flow with Failures and Retry

```
RegisterInfrastructure
  ↓
TrainModels
  → 3 succeed, 1 fails
  ↓
RegisterModels (registers 3 models)
  ↓
RetryFailedTraining ← RUNS (failures detected)
  1. Show failed circuit
  2. Wait for approval ⏸️
  3. Retry failed job
  4. Monitor retry
  5. Register retry model
  6. Merge: 3 original + 1 retry = 4 total
  ↓
PromoteToRegistry (uses merged list of 4 models)
```

### Manual Circuit Flow

```
RegisterInfrastructure
  ↓ (manual circuits specified)
DetectChangedCircuits
  → Uses manualCircuits parameter
  → Creates changed_circuits.json from parameter
  ↓
TrainModels (trains only specified circuits)
  ↓
RegisterModels
  ↓
[RetryFailedTraining] ← SKIPPED or RUNS based on failures
  ↓
PromoteToRegistry
```

## Best Practices

### When to Use Automatic Retry

✅ **Use automatic retry for:**
- Transient infrastructure failures (compute not available, network issues)
- Timeout issues that may resolve on retry
- Occasional Azure ML service hiccups
- When you want to retry immediately without code changes

❌ **Don't use automatic retry for:**
- Code bugs (fix the code first)
- Data quality issues (fix data first)
- Configuration errors (fix config first)
- Consistent failures across multiple circuits

### When to Use Manual Specification

✅ **Use manual specification for:**
- Testing specific circuits after fixes
- Re-training after data corrections
- Selective training for validation
- Debugging individual circuit issues

❌ **Don't use manual specification for:**
- Regular training runs (use automatic detection)
- Full retraining of all circuits (modify configs instead)

### Approval Guidelines

**When approving retry:**
- ✅ Verify failure is transient (check logs)
- ✅ Confirm no code/config changes needed
- ✅ Check Azure ML workspace has available compute
- ✅ Review estimated training duration

**When rejecting retry:**
- ❌ Failure indicates code bug → fix first
- ❌ Configuration is incorrect → update config first
- ❌ Data quality issues → resolve data issues first
- ❌ Multiple circuits failing with same error → systematic issue

## Monitoring and Troubleshooting

### Check Retry Status

**Azure DevOps Pipeline:**
1. Navigate to pipeline run
2. Find `RetryFailedTraining` stage
3. If not present: No failures occurred (normal!)
4. If present but pending: Waiting for approval
5. If present and running: Retry in progress

**Azure ML Studio:**
1. Go to Jobs section
2. Filter by job name containing `_retry_`
3. View retry job progress and logs

### Failed Retry Recovery

If retry fails again:

**Option 1: Manual Retry**
```
manualCircuits: '<failed_circuit>'
```

**Option 2: Fix and Re-run**
1. Fix underlying issue
2. Merge fix to develop
3. Run pipeline again
4. Original retry stage will appear for previous failures

**Option 3: Accept Partial Success**
1. Don't approve retry
2. Proceed with successful models only
3. Address failed circuits in next training cycle

### Artifacts for Debugging

The pipeline creates these artifacts:
- `training_jobs.json` - All submitted jobs
- `failed_jobs.json` - Failed job details (for retry)
- `completed_jobs.json` - Successful job details
- `retry_jobs.json` - Retry submission details
- `completed_retry_jobs.json` - Successful retry details
- `registered_models.json` - Original models
- `registered_models_with_retry.json` - Merged list (original + retry)

Download from Azure DevOps:
1. Go to pipeline run
2. Click "Artifacts" button
3. Download relevant JSON files
4. Inspect for debugging

## Configuration

### Environment Setup

The retry feature uses an Azure DevOps environment for approval gates:

**Environment Name:** `training-retry`

**To configure:**
1. Go to Azure DevOps → Environments
2. Create environment: `training-retry`
3. Add approvers (ML Engineers, Team Leads)
4. Set approval timeout (e.g., 4 hours)

### Pipeline Variables

No additional variables needed! The retry feature uses existing pipeline infrastructure:

```yaml
variables:
  longRunningJobNotificationIntervalHours: '4'  # Already exists
```

## FAQ

**Q: What happens if I don't approve the retry?**  
A: The pipeline continues with only the successful models. Failed circuits are not retrained.

**Q: Can I retry multiple times?**  
A: Yes! If a retry fails, the next pipeline run will detect those failures and offer retry again.

**Q: Does retry affect compute costs?**  
A: Yes, retry jobs consume compute resources like original jobs. Only retry what you need.

**Q: Can I cancel a retry in progress?**  
A: Yes, cancel the pipeline run or cancel individual jobs in Azure ML Studio.

**Q: How long do I have to approve?**  
A: Configurable in environment settings (default: 4 hours). After timeout, retry is skipped.

**Q: Will retry models overwrite original versions?**  
A: No! Retry models register as new versions (auto-incremented). No overwriting occurs.

**Q: Can I use manual specification AND retry?**  
A: Yes! Manual specification can trigger training, and if those jobs fail, retry stage will activate.

**Q: What if a circuit fails in both original and retry?**  
A: It remains in failed state. You'll need to investigate and either fix the issue or use manual specification.

## Summary

The retry and manual specification features provide:

1. **Zero-impact on normal flow** - Retry stage skips when not needed
2. **Intelligent failure handling** - Automatic detection and isolation
3. **Flexible retry options** - Automatic or manual approaches
4. **Full audit trail** - All retry models tagged
5. **Seamless integration** - Merged models flow to Registry

**Key principle:** Failed circuits don't block successful ones. The pipeline progresses with what succeeded while offering easy retry for what failed.
