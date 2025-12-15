# Dummy Training Pipeline - Testing Guide

## Overview

The dummy training pipeline (`dummy-training-pipeline.yml`) is an exact replica of the real training pipeline but **simulates all Azure ML operations** without requiring actual connections. Perfect for testing workflow logic, conditions, and scenarios!

## Setup

### 1. Create Dummy Approval Environment

For testing approvals, create a dummy environment:

1. Azure DevOps → Pipelines → Environments
2. Create: `dummy-approval`
3. (Optional) Add yourself as approver to test approval flow

### 2. Create Pipeline in Azure DevOps

1. Pipelines → New Pipeline
2. Select: Azure Repos Git
3. Choose: Existing YAML file
4. Path: `.azuredevops/dummy-training-pipeline.yml`
5. Save

## Test Scenarios

### Scenario 1: New Environment Registration

**Parameters:**
- `simulateNewEnvironment`: `true`
- `simulateCircuitChanges`: `2`
- `simulateJobFailures`: `0`
- `skipPromotion`: `false`

**Expected Flow:**
```
Stage 1: RegisterEnvironment ✅
   ├─ Simulates new env registration
   └─ Sets newEnvRegistered=true
      ↓
Stage 2: PromoteEnvironment ✅ (RUNS - waits for approval)
   ↓
Stage 3: RegisterComponents ✅ (runs in parallel)
   ↓
Stage 4-8: Continue normally
```

### Scenario 2: Environment Already Exists

**Parameters:**
- `simulateNewEnvironment`: `false`
- `simulateCircuitChanges`: `2`
- `simulateJobFailures`: `0`

**Expected Flow:**
```
Stage 1: RegisterEnvironment ✅
   ├─ Simulates existing env
   └─ Sets newEnvRegistered=false
      ↓
Stage 2: PromoteEnvironment ⏭️ (SKIPPED!)
   ↓
Stage 3: RegisterComponents ✅ (runs immediately)
   ↓
Stage 4-8: Continue normally
```

### Scenario 3: Training Failures

**Parameters:**
- `simulateNewEnvironment`: `false`
- `simulateCircuitChanges`: `5`
- `simulateJobFailures`: `2`

**Expected Flow:**
```
Stage 4: RegisterMLTables
   └─ 5 circuits detected

Stage 5: SubmitTraining
   └─ 5 jobs submitted

Stage 6: MonitorTraining
   ├─ Completed: 3
   └─ Failed: 2

Stage 7: RegisterModels
   └─ 3 models registered (only successful)

Stage 8: PromoteToRegistry
   └─ 3 child pipelines triggered
```

### Scenario 4: Skip Promotion

**Parameters:**
- `simulateCircuitChanges`: `3`
- `skipPromotion`: `true`

**Expected Flow:**
```
Stages 1-7: Run normally
Stage 8: PromoteToRegistry ⏭️ (SKIPPED!)
```

## What Gets Simulated

### Stage 1: RegisterEnvironment
- ✅ Environment version check
- ✅ Registration decision
- ✅ Output variable (`newEnvRegistered`)

### Stage 2: PromoteEnvironment
- ✅ Conditional execution based on Stage 1
- ✅ Approval gate (if environment configured)
- ✅ Promotion simulation

### Stage 3: RegisterComponents
- ✅ Parallel execution with Stage 2
- ✅ Component registration

### Stage 4: RegisterMLTables
- ✅ Circuit detection
- ✅ MLTable registration
- ✅ Artifact output

### Stage 5: SubmitTraining
- ✅ Job submission
- ✅ Training jobs artifact

### Stage 6: MonitorTraining
- ✅ Job monitoring simulation
- ✅ Success/failure tracking
- ✅ Monitoring result artifact

### Stage 7: RegisterModels
- ✅ Model registration (only successful jobs)
- ✅ Registered models artifact

### Stage 8: PromoteToRegistry
- ✅ Child pipeline triggering simulation
- ✅ Per-model promotion display
- ✅ Skip promotion parameter

## Artifacts Created

All stages create realistic JSON artifacts:

- `mltable_result.json` - MLTable registration results
- `training_jobs.json` - Submitted training jobs
- `monitoring_result.json` - Training monitoring results
- `registered_models.json` - Registered models

## Benefits

✅ **No Azure ML required** - Test without workspace access  
✅ **Fast execution** - Completes in ~2 minutes  
✅ **Realistic flow** - Exact same stages and conditions  
✅ **Approval testing** - Test approval gates  
✅ **Scenario testing** - Test different failure scenarios  
✅ **Artifact validation** - Verify artifact structure  
✅ **Conditional logic** - Test all conditions and dependencies

## Comparison with Real Pipeline

| Feature | Real Pipeline | Dummy Pipeline |
|---------|--------------|----------------|
| Stages | 8 | 8 (identical) |
| Dependencies | ✅ Same | ✅ Same |
| Conditions | ✅ Same | ✅ Same |
| Artifacts | ✅ Real data | ✅ Simulated data |
| Approvals | ✅ Real | ✅ Simulated |
| Duration | ~30-60 min | ~2 min |
| Azure ML | Required | Not required |

## Use Cases

### 1. Test Workflow Changes
Before modifying the real pipeline, test changes in dummy pipeline:
```bash
# Make changes to dummy-training-pipeline.yml
# Run dummy pipeline
# Verify workflow behaves as expected
# Apply same changes to training-pipeline.yml
```

### 2. Test Conditional Logic
Verify conditions work correctly:
- New environment registration → Stage 2 runs
- Existing environment → Stage 2 skips
- Skip promotion parameter → Stage 8 skips

### 3. Test Approval Flow
Practice approval process:
- Configure `dummy-approval` environment with approvers
- Run pipeline
- Test approval/rejection
- Verify behavior

### 4. Training for Team
Onboard new team members:
- Show them the dummy pipeline
- Let them run it and see the flow
- Explain each stage
- No risk of affecting real resources

### 5. CI/CD Validation
Add dummy pipeline to PR validation:
```yaml
# pr-validation-pipeline.yml
- stage: TestWorkflow
  jobs:
    - job: RunDummyPipeline
      steps:
        - task: TriggerPipeline@1
          inputs:
            pipeline: 'dummy-training-pipeline'
```

## Next Steps

1. **Run dummy pipeline** with default parameters
2. **Test each scenario** listed above
3. **Verify artifacts** are created correctly
4. **Test approvals** if environment configured
5. **Use for training** and documentation

**Ready to test your workflow without touching Azure ML!** 🎯
