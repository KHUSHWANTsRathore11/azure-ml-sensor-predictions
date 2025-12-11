# Environment-Only Pipeline

[← Back to README](../README.md)

## Overview

The Environment-Only Pipeline enables updating custom environments across all production deployments WITHOUT model retraining for non-breaking changes.

## When to Use

**Use this pipeline for:**
- Bug fixes in scoring script (no model interface changes)
- Logging improvements
- Performance optimizations
- Security patches
- Non-breaking dependency updates

**Do NOT use for:**
- TensorFlow version upgrades (breaking)
- Feature engineering changes (breaking)
- Preprocessing logic changes (breaking)

## Four-Stage Pipeline

### Stage 1: Promote Environment to Registry
- **Approval:** Manual (ML Engineers)
- **Evidence:** Interactive notebook showing scoring in Dev
- **Action:** Promote environment to shared registry

### Stage 2: Test ALL Models
- **Trigger:** Auto
- **Action:** Integration test all 75-200 models
- **Validation:** All tests must pass

### Stage 3: Update All Deployments
- **Approval:** Manual (ML Engineers + Managers)
- **Action:** Update ALL deployments with new environment
- **Tracking:** Store previous environment versions for rollback

### Stage 4: Monitor Production
- **Duration:** 24 hours
- **Action:** Monitor alerts, batch job success rates
- **Rollback:** Use rollback pipeline if issues detected

## Integration Test Strategy

### Test Process

1. Copy environment to Test Workspace
2. Get list of all production models (75-200)
3. For each model:
   - Submit compatibility test job
   - Test with new environment version
4. Wait for all tests to complete
5. Check if any tests failed
6. If all pass → Proceed to Stage 3
7. If any fail → Fail release

### Test Job YAML

```yaml
# pipelines/environment_compatibility_test.yml
$schema: https://azuremlschemas.azureedge.net/latest/pipelineJob.schema.json
type: pipeline

inputs:
  model_name: 
    type: string
  model_version: 
    type: string
  environment_version:
    type: string

jobs:
  compatibility_test:
    type: command
    environment: azureml:custom-tf-env:${{inputs.environment_version}}
    command: >-
      python scripts/test_model_compatibility.py
      --model-name ${{inputs.model_name}}
      --model-version ${{inputs.model_version}}
    compute: azureml:test-compute-cluster
```

## Rollback Pipeline

### When to Rollback

| Trigger | Severity | Action |
|---------|----------|--------|
| Multiple batch failures | Critical | Immediate rollback |
| Performance degradation >20% | High | Rollback |
| Scoring errors | Critical | Immediate rollback |
| Alert spike >10/hour | High | Rollback |

### Rollback Process

1. Download rollback metadata artifact
2. Parse previous environment versions JSON
3. For each deployment (75-200):
   - Update to previous environment
   - Tag with rollback metadata
4. Verify all rollbacks successful

### Rollback Metadata Format

```json
[
  {
    "plant_id": "P001",
    "circuit_id": "C001",
    "previous_environment": "azureml:custom-tf-env:1.5.0"
  },
  {
    "plant_id": "P001",
    "circuit_id": "C002",
    "previous_environment": "azureml:custom-tf-env:1.5.0"
  }
]
```

## Update-All Rollout Strategy

### Benefits

- **Fast:** All deployments updated simultaneously
- **Consistent:** Single environment version across all deployments
- **Simple:** One operation vs. 75-200 individual deployments

### Trade-offs

- **Risk:** All deployments affected if issue occurs
- **Mitigation:** Comprehensive integration testing + rollback pipeline

## Related Documents

- [04-environment-management.md](04-environment-management.md) - Environment strategy
- [08-rollback-procedures.md](08-rollback-procedures.md) - Rollback details
- [10-pipeline-yaml-reference.md](10-pipeline-yaml-reference.md) - Full YAML

---

**Document Version:** 1.0  
**Last Updated:** December 9, 2025
