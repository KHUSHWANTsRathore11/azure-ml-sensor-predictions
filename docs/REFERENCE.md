# Quick Reference

Common commands, troubleshooting, and quick links.

## Common Commands

### Azure ML

```bash
# List environments
az ml environment list --workspace-name mlops-dev-workspace

# Show environment
az ml environment show --name custom-training-env --version 1.0.0

# List components
az ml component list --workspace-name mlops-dev-workspace

# List jobs
az ml job list --workspace-name mlops-dev-workspace

# Show job
az ml job show --name <job-name> --workspace-name mlops-dev-workspace

# List models
az ml model list --workspace-name mlops-dev-workspace

# List models in Registry
az ml model list --registry-name mlops-central-registry
```

### Azure DevOps

```bash
# Run pipeline
az pipelines run --name training-pipeline

# Run with parameters
az pipelines run --name training-pipeline \
  --parameters manualCircuits="PLANT001/CIRCUIT01"

# List runs
az pipelines runs list --pipeline-name training-pipeline

# Show run
az pipelines runs show --id <run-id>
```

## Troubleshooting

### Pipeline Fails at Stage 1

**Issue:** Environment registration fails

**Check:**
- `config/environment.yaml` exists
- `name` and `version` fields present
- Azure ML workspace accessible

### Pipeline Fails at Stage 5

**Issue:** No circuits detected for training

**Check:**
- `config/circuits.yaml` has circuits
- Git changes detected or `manualCircuits` specified
- Training hash changed

### Model Not in Registry

**Issue:** Model promoted but not visible

**Check:**
- Approval was granted
- Propagation delay (wait 2 minutes)
- Check Registry directly in Azure ML Studio

### Variable Not Found

**Issue:** Pipeline can't find variable

**Check:**
- Variable Group name matches exactly
- Variable name correct (case-sensitive)
- Pipeline YAML includes `- group:` reference
- Build service has permissions

## File Locations

```
├── .azuredevops/
│   ├── training-pipeline.yml           # Main training pipeline
│   ├── promote-single-model-pipeline.yml  # Model promotion child
│   ├── test-deployment-pipeline.yml    # Test deployment
│   ├── prod-deployment-pipeline.yml    # Prod deployment
│   └── pr-validation-pipeline.yml      # PR validation
├── config/
│   ├── circuits.yaml                   # Circuit configuration
│   └── environment.yaml                # Environment definition
├── components/
│   └── training-pipeline-component.yaml  # Pipeline component
├── scripts/pipeline/
│   ├── detect_changed_circuits.py      # Circuit detection
│   ├── submit_training_jobs.py         # Job submission
│   ├── monitor_training_jobs.py        # Job monitoring
│   ├── register_models.py              # Model registration
│   └── promote_to_registry.py          # Model promotion
└── docs/
    ├── SETUP.md                        # Setup guide
    ├── PIPELINES.md                    # Pipeline architecture
    ├── VERSIONING.md                   # Versioning strategy
    ├── APPROVALS.md                    # Approval workflows
    ├── MONITORING.md                   # Monitoring & notifications
    ├── TESTING.md                      # Testing guide
    ├── BRANCHING.md                    # Git workflow
    └── REFERENCE.md                    # This file
```

## Variable Groups

| Group | Variables |
|-------|-----------|
| `mlops-dev-variables` | 5 vars (workspace connection) |
| `mlops-test-variables` | 6 vars (workspace + cluster) |
| `mlops-prod-variables` | 6 vars (workspace + cluster) |
| `mlops-registry-variables` | 5 vars (registry + propagation) |
| `mlops-pipeline-settings` | 12 vars (monitoring, validation) |
| `mlops-shared-variables` | 9 vars (PR validation) |

**Total:** 43 variables across 6 groups

## Quick Links

- [Azure ML Studio](https://ml.azure.com)
- [Azure DevOps Pipelines](https://dev.azure.com)
- [Variable Groups](https://dev.azure.com → Pipelines → Library)
- [Environments](https://dev.azure.com → Pipelines → Environments)

## Support

**For issues:**
1. Check this reference
2. Review relevant doc (SETUP, PIPELINES, etc.)
3. Check Azure ML Studio logs
4. Contact ML platform team
