# Implementation Checklist

[← Back to README](../README.md)

## Overview

12-week implementation timeline for the Azure ML sensor predictions architecture, organized into 9 phases with detailed tasks and deliverables.

**Total Timeline:** ~12 weeks (3 months)

## Phase Overview

| Phase | Duration | Focus Area | Key Deliverables |
|-------|----------|------------|------------------|
| Phase 1 | Week 1-2 | Foundation Setup | Azure resources, workspaces, DevOps project |
| Phase 2 | Week 2-3 | Data Pipeline | ETL, Delta Lake, scheduled pipelines |
| Phase 3 | Week 3-4 | Config Management | Multi-model configs, change detection |
| Phase 4 | Week 4-6 | ML Development | Training, MLTable, models |
| Phase 5 | Week 6-7 | Batch Endpoints | Endpoints per plant, deployments per circuit |
| Phase 6 | Week 7-9 | Release Pipeline | 3-stage deployment, approvals |
| Phase 7 | Week 9-10 | Environment Pipeline | Environment-only updates |
| Phase 8 | Week 10-11 | Monitoring | Alerts, dashboards, drift detection |
| Phase 9 | Week 11-12 | Testing & Validation | End-to-end tests, load tests |

---

## Phase 1: Foundation Setup (Week 1-2)

### Azure Resources

- [ ] Create Azure Resource Group (`mlops-rg`)
- [ ] **Provision Azure ML Registry** (shared across environments)
- [ ] **Provision Dev ML Workspace** (training)
- [ ] **Provision Test ML Workspace** (integration testing)
- [ ] **Provision Production ML Workspace** (inference)
- [ ] Set up Production ADLS Gen2 storage account (shared input data)
- [ ] Set up workspace storage accounts (dev/test/prod outputs)
- [ ] Create Synapse Analytics workspace
- [ ] Configure Synapse Spark Pool (attach to AzureML)
- [ ] Set up Azure Key Vault
- [ ] Configure managed identities for services

### DevOps Setup

- [ ] Set up Azure DevOps project
- [ ] Create Git repository
- [ ] Create service connections (Azure DevOps → Azure)
- [ ] **Configure Azure DevOps Environments:**
  - [ ] azureml-registry (approval required)
  - [ ] test-workspace (no approval)
  - [ ] production-workspace (approval required)
- [ ] **Set up approval groups:**
  - [ ] ML-Engineers group
  - [ ] Engineering-Managers group (for env updates)
- [ ] Create variable groups

### Configuration

- [ ] **Create master config file** (`config/plants_circuits.yml`)
- [ ] Define initial plant/circuit structure
- [ ] Set up branch protection rules
- [ ] Configure PR templates

**Deliverables:**
- ✅ All Azure resources provisioned
- ✅ DevOps project configured
- ✅ Service connections tested

---

## Phase 2: Data Pipeline (Week 2-3)

### Delta Lake Setup

- [ ] Create single Delta Lake table in Production ADLS Gen2
  - Path: `/processed/sensor_data/`
- [ ] Define merge keys (e.g., sensor_id + timestamp)
- [ ] Ensure ETL includes `date` column for filtering
- [ ] **Ensure sensor_id column for per-circuit filtering**

### Synapse ETL

- [ ] Develop Synapse Spark ETL notebooks
  - [ ] Read from source (Parquet files / SQL tables)
  - [ ] Transform data
  - [ ] Merge/upsert to Delta table
- [ ] Test ETL pipeline end-to-end
- [ ] Verify Delta transaction log functionality
- [ ] **Configure all workspaces to read from production storage**

### Automation

- [ ] Create Azure DevOps pipeline for scheduled ETL (every 3 hours)
- [ ] Test ETL schedule
- [ ] Set up monitoring for ETL failures

**Deliverables:**
- ✅ Delta Lake table created and tested
- ✅ ETL pipeline runs successfully every 3 hours
- ✅ Data accessible from all workspaces

---

## Phase 3: Multi-Model Config Management (Week 3-4)

### Config Structure

- [ ] **Create config directory structure:** `config/plants/{plant_id}/{circuit_id}.yml`
- [ ] **Define config schema:**
  - plant_id, circuit_id
  - cutoff_date
  - environment_version
  - hyperparameters
  - sensor_id, feature_columns
- [ ] **Populate initial configs for all circuits** (target: 10-20 for pilot)

### Scripts

- [ ] **Create `scripts/detect_config_changes.py`** (git diff parser)
- [ ] **Create `scripts/read_config.py`** (config file reader)
- [ ] **Create `scripts/load_all_circuits.py`** (for monitoring matrix)
- [ ] **Create `scripts/promote_to_registry.sh`** (model promotion)
- [ ] **Create `scripts/deploy_batch_endpoint.sh`** (deployment script)
- [ ] **Create `scripts/rollback_model.sh`** (emergency rollback)

### Testing

- [ ] Test config change detection with sample PR
- [ ] Validate config schema
- [ ] Test scripts in isolation

**Deliverables:**
- ✅ Config structure validated
- ✅ 10-20 circuit configs created
- ✅ All scripts tested

---

## Phase 4: ML Development (Week 4-6)

### Environment Setup

- [ ] Structure Python package (setup.py, src/, tests/)
- [ ] Create custom Docker environment
  - [ ] Dockerfile
  - [ ] requirements.txt
  - [ ] conda.yml
- [ ] Build and register environment in Dev Workspace
  - [ ] Version: 1.0.0
  - [ ] Tags: backward_compatible, requires_retrain

### MLTable Registration

- [ ] **Develop `scripts/register_mltable.py`**
  - [ ] Per-circuit Data Asset naming
  - [ ] Check-or-create logic with tags
  - [ ] Sensor-specific filtering
  - [ ] Use cutoff_date as version string
- [ ] Test MLTable registration for sample circuits
- [ ] Verify Data Asset versioning

### Training Pipeline

- [ ] Create AzureML training pipeline YAML
- [ ] **Develop training script (`src/train.py`):**
  - [ ] Load hyperparameters from config YAML
  - [ ] Filter data by sensor_id
  - [ ] Tag experiments by plant_id/circuit_id
  - [ ] MLflow logging
- [ ] Test training on AzureML compute cluster
- [ ] **Test parallel training (maxParallel=5)**

### Model Registration

- [ ] Implement model registration with tags:
  - [ ] plant_id, circuit_id
  - [ ] pr_number, cutoff_date
  - [ ] data_asset_version
  - [ ] hyperparameters_hash
  - [ ] pr_author, git_commit_sha
- [ ] Test model registration
- [ ] Verify graphical lineage in AzureML Studio

**Deliverables:**
- ✅ Environment v1.0.0 registered
- ✅ Training pipeline functional
- ✅ Models registered with full metadata
- ✅ Graphical lineage verified

---

## Phase 5: Multi-Model Batch Endpoints (Week 6-7)

### Endpoint Creation

- [ ] **Create batch endpoints (one per plant):**
  - [ ] Example: `batch-endpoint-plant-P001`
  - [ ] Target: 3-5 endpoints for pilot
- [ ] **Create deployments per circuit:**
  - [ ] Example: `deployment-circuit-C001`
  - [ ] 2-4 deployments per endpoint

### Scoring Script

- [ ] **Develop `src/score.py`:**
  - [ ] Read plant_id/circuit_id from environment
  - [ ] Filter Delta data by sensor_id
  - [ ] Read latest data only (no MLTable)
  - [ ] Return predictions
- [ ] Test scoring locally
- [ ] Test batch scoring on Test Workspace

### Invocation

- [ ] **Create `scripts/invoke_all_batch_endpoints.py`:**
  - [ ] Loop through all plant/circuit combinations
  - [ ] Invoke each deployment
  - [ ] Log results
- [ ] Test batch inference for sample circuits
- [ ] Verify prediction output to ADLS Gen2

### Scheduling

- [ ] Set up scheduled batch inference (daily, post-ETL)
- [ ] Test daily schedule
- [ ] Monitor execution

**Deliverables:**
- ✅ 3-5 batch endpoints created
- ✅ 10-20 deployments functional
- ✅ Daily inference running successfully

---

## Phase 6: Release Pipeline & Deployment (Week 7-9)

### Build Pipeline

- [ ] **Create Azure DevOps Build Pipeline:**
  - [ ] **Stage 1: DetectChanges** (git diff)
  - [ ] **Stage 2: PrepareData** (register MLTables, maxParallel=5)
  - [ ] **Stage 3: Build** (check env changes, build/register)
  - [ ] **Stage 4: Train** (parallel training, maxParallel=5)
  - [ ] **Stage 5: PublishArtifact** (model metadata)
- [ ] **Create environment detection scripts:**
  - [ ] `scripts/check_env_change.py`
  - [ ] `scripts/get_env_from_config.py`
- [ ] **Update configs to include environment_version**
- [ ] Test Build Pipeline end-to-end

### Release Pipeline

- [ ] **Create Azure DevOps Release Pipeline:**
  - [ ] **Stage 1: Promote to Registry**
    - [ ] Manual approval gate
    - [ ] Environment: azureml-registry
    - [ ] Instructions with model details
  - [ ] **Stage 2: Deploy to Test**
    - [ ] Auto-trigger
    - [ ] Deploy to test endpoint
    - [ ] Run test inference
    - [ ] Validate no errors
  - [ ] **Stage 3: Deploy to Production**
    - [ ] Manual approval gate
    - [ ] Environment: production-workspace
    - [ ] Instructions with test results
- [ ] **Configure approval gates:**
  - [ ] ML-Engineers as approvers
  - [ ] Evidence requirements
  - [ ] 24-hour timeout

### Testing

- [ ] **Test Release Pipeline:**
  - [ ] Single circuit: Full flow
  - [ ] Multiple circuits: Parallel releases
  - [ ] Rejection scenarios
  - [ ] Environment + model changes
- [ ] **Test rollback:**
  - [ ] Via Azure DevOps Release history
  - [ ] Via `scripts/rollback_model.sh`
- [ ] Test graphical lineage per circuit

### Documentation

- [ ] Create rollback procedures
- [ ] Document Release Pipeline workflow
- [ ] Create operational runbooks

**Deliverables:**
- ✅ Build Pipeline (5 stages) functional
- ✅ Release Pipeline (3 stages) functional
- ✅ Approval gates configured
- ✅ Rollback tested

---

## Phase 7: Environment-Only Release Pipeline (Week 9-10)

### Pipeline Creation

- [ ] **Create Environment-Only Release Pipeline:**
  - [ ] **Stage 1: Promote to Registry** (manual approval + evidence)
  - [ ] **Stage 2: Test ALL Models** (integration tests)
  - [ ] **Stage 3: Update ALL Deployments** (manual approval)
  - [ ] **Stage 4: Monitor Production** (24h observation)

### Integration Testing

- [ ] **Create `scripts/get_all_deployments.py`**
- [ ] **Create `pipelines/environment_compatibility_test.yml`**
- [ ] **Test integration testing:**
  - [ ] Test 10-20 models simultaneously
  - [ ] Verify all tests pass/fail correctly

### Rollback Pipeline

- [ ] **Create Environment Rollback Pipeline:**
  - [ ] Download rollback metadata
  - [ ] Rollback all deployments
  - [ ] Verify success

### Testing

- [ ] **Test environment-only workflow:**
  - [ ] Non-breaking change (bug fix)
  - [ ] Integration testing all models
  - [ ] Update all deployments
  - [ ] Monitor for issues
  - [ ] Test rollback

### Documentation

- [ ] **Document environment update procedures:**
  - [ ] Breaking vs Non-breaking classification
  - [ ] Evidence requirements
  - [ ] Integration test criteria
  - [ ] Rollback procedures
- [ ] **Update environment versioning strategy**

**Deliverables:**
- ✅ Environment-Only Pipeline functional
- ✅ Integration testing verified
- ✅ Rollback pipeline tested
- ✅ Documentation complete

---

## Phase 8: Multi-Model Monitoring (Week 10-11)

### Application Insights

- [ ] Set up Application Insights for all workspaces
- [ ] Configure logging in training scripts
- [ ] Configure logging in scoring scripts

### Alert Rules

- [ ] **Create Azure Monitor alert rules:**
  - [ ] Model performance degradation (per circuit)
  - [ ] Data drift detected (per circuit)
  - [ ] Batch job failure (any circuit)
  - [ ] Compute cluster cost alert
  - [ ] High training failure rate
- [ ] Configure alert action groups
- [ ] Test alert triggering

### Monitoring Scripts

- [ ] **Create monitoring scripts:**
  - [ ] `monitoring/check_model_performance.sh`
  - [ ] `monitoring/check_data_drift.sh`
  - [ ] `scripts/load_all_circuits.py`

### Monitoring Pipelines

- [ ] **Create monthly performance monitoring pipeline:**
  - [ ] Parallel execution across circuits
  - [ ] Circuit-specific alerting
- [ ] **Create quarterly drift monitoring pipeline:**
  - [ ] Parallel execution
  - [ ] Drift reports per circuit
- [ ] Test monitoring pipelines

### Dashboards

- [ ] Create Azure Monitor dashboard
- [ ] Create cost analysis dashboard
- [ ] Plan Power BI dashboard (future)

**Deliverables:**
- ✅ Application Insights configured
- ✅ Alert rules active
- ✅ Monitoring pipelines scheduled
- ✅ Dashboards created

---

## Phase 9: Testing & Validation (Week 11-12)

### End-to-End Testing

- [ ] **Full workflow test:**
  - [ ] ETL → Config change PR → Training → Artifact
  - [ ] Release: Registry → Test → Production
  - [ ] Daily batch inference
- [ ] **Release Pipeline testing:**
  - [ ] Approval workflows
  - [ ] Test validation
  - [ ] Rollback procedures
  - [ ] Multiple concurrent releases
- [ ] **Environment-Only Pipeline testing:**
  - [ ] Non-breaking change
  - [ ] Integration test all models
  - [ ] Update all deployments
  - [ ] Rollback

### Load Testing

- [ ] **Parallel training:**
  - [ ] 10 circuits simultaneously
  - [ ] Verify maxParallel=5 enforced
  - [ ] Check compute utilization
- [ ] **Batch inference:**
  - [ ] 20-50 invocations
  - [ ] Check success rate
  - [ ] Monitor execution time
- [ ] **Test/Prod concurrent deployments:**
  - [ ] Deploy to both environments
  - [ ] Verify no conflicts

### Validation

- [ ] Validate graphical lineage per circuit
- [ ] Test monitoring alerts
- [ ] Security review (RBAC, secrets, firewall)
- [ ] **Cost optimization review**

### Documentation

- [ ] **Document deployment procedures:**
  - [ ] Registry promotion criteria
  - [ ] Test validation criteria
  - [ ] Production approval criteria
  - [ ] Rollback procedures
  - [ ] Environment update procedures
- [ ] Knowledge transfer to operations team
- [ ] Create training materials

### Sign-Off

- [ ] ML Engineers sign-off
- [ ] Data Science Lead sign-off
- [ ] DevOps sign-off
- [ ] Security sign-off
- [ ] Management sign-off

**Deliverables:**
- ✅ All tests passed
- ✅ Documentation complete
- ✅ Team trained
- ✅ Production-ready

---

## Success Criteria

### Technical

- [ ] All 5 pipelines functional (Build, Release, Env-Only, ETL, Monitoring)
- [ ] 10-20 models trained and deployed successfully
- [ ] Approval gates working correctly
- [ ] Rollback tested and documented
- [ ] Monitoring alerts active
- [ ] Cost within budget

### Operational

- [ ] Team trained on pipelines
- [ ] Runbooks documented
- [ ] Incident response procedures defined
- [ ] On-call rotation established

### Business

- [ ] Predictions generated daily
- [ ] Model metrics meeting thresholds
- [ ] Deployment time <4 hours (PR to prod)
- [ ] Rollback time <20 minutes

## Post-Implementation

### Week 13-16: Stabilization

- [ ] Monitor production closely
- [ ] Address any issues
- [ ] Optimize based on usage patterns
- [ ] Fine-tune alert thresholds

### Month 4-6: Scaling

- [ ] Scale to 50-75 models
- [ ] Optimize costs
- [ ] Automate additional workflows
- [ ] Implement additional features

### Month 7-12: Full Scale

- [ ] Scale to 75-200 models
- [ ] Full production deployment
- [ ] Continuous optimization
- [ ] Plan future enhancements

## Related Documents

- [02-data-architecture.md](02-data-architecture.md) - Data setup
- [05-build-pipeline.md](05-build-pipeline.md) - Build pipeline
- [06-release-pipeline.md](06-release-pipeline.md) - Release pipeline
- [07-environment-only-pipeline.md](07-environment-only-pipeline.md) - Environment pipeline
- [11-monitoring-strategy.md](11-monitoring-strategy.md) - Monitoring setup

---

**Document Version:** 1.0  
**Last Updated:** December 9, 2025  
**Maintained By:** ML Engineering Team
