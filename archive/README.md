# Archived Files

This directory contains old implementations and documentation that have been superseded by the corrected component-based architecture.

## Archive Date
December 10, 2025

## Why Archived

These files represent earlier iterations of the MLOps architecture before the following corrections were made:

### Key Architecture Changes:
1. **Removed Data Component**: MLTable registration moved from component to direct Azure CLI per circuit
2. **Data Asset Naming**: Changed to per-circuit naming (`PLANT_CIRCUIT:cutoff_date`)
3. **Parallel Orchestration**: Moved from Azure ML parallel component to Azure DevOps matrix strategy
4. **Component Version Tracking**: Added proper version capture and dynamic references
5. **Environment Management**: Added custom environment registration in build pipeline
6. **Cutoff Date Usage**: Clarified as VERSION for MLTable, TAG for pipelines/models/deployments

## Current Implementation

See the main repository for:
- `.azuredevops/build-pipeline.yml` - Corrected build pipeline with 3 stages
- `.azuredevops/release-pipeline.yml` - Release pipeline (future: Step 7)
- `pipelines/single-circuit-training.yaml` - Single circuit training pipeline
- `docs/` - Current documentation
- `IMPLEMENTATION_PROGRESS.md` - Step-by-step progress tracker

## Archived Contents

### Pipelines (`/pipelines/`)
- **`build-pipeline-components.yml`** - Old component-based build pipeline
  - Had data component for MLTable registration (removed)
  - Missing environment registration
  - No component version tracking
  
- **`build-pipeline-old.yml`** - Original build pipeline
  - Early iteration before component architecture
  
- **`environment-only-pipeline.yml`** - Environment-only deployment
  - Standalone environment pipeline (no longer needed)
  
- **`training-pipeline-components.yaml`** - Multi-circuit training with parallel component
  - Used Azure ML parallel component (wrong orchestration level)
  - Changed to DevOps matrix strategy instead

### Documentation (`/documentation/`)

#### Architecture Documentation (Pre-Correction)
- `01-high-level-architecture.md` - Had 6 inconsistencies
- `02-data-architecture.md` - Generic data asset naming
- `03-multi-model-strategy.md` - Parallel component approach
- `04-environment-management.md` - Registry-based environment
- `05-build-pipeline.md` - Old build pipeline with data component

#### Pipeline Documentation
- `07-environment-only-pipeline.md` - Standalone environment deployment
- `08-rollback-procedures.md` - Old rollback procedures
- `09-scripts-reference.md` - Old script documentation
- `10-pipeline-yaml-reference.md` - Old YAML reference

#### Monitoring & Operations
- `11-monitoring-strategy.md` - Old monitoring approach
- `12-operational-runbooks.md` - Old runbooks
- `13-cost-estimation.md` - Old cost analysis
- `14-implementation-checklist.md` - Old checklist
- `15-well-architected-assessment.md` - Old assessment
- `16-model-monitoring-data-drift.md` - Old drift monitoring

#### Status Documents
- `MIGRATION_STATUS.md` - Migration tracking (obsolete)
- `DOCUMENTATION_COMPLETE.md` - Old completion status
- `MONITORING_DOCUMENTATION_ADDED.md` - Old monitoring status
- `MONITORING_QUICK_REFERENCE.md` - Old quick reference
- `README_COMPONENTS.md` - Old component README

## What Remains Active

### Azure DevOps Pipelines
- ✅ `.azuredevops/build-pipeline.yml` - **CORRECTED** build pipeline
- ✅ `.azuredevops/release-pipeline.yml` - Release pipeline (future implementation)

### Azure ML Pipelines
- ✅ `pipelines/single-circuit-training.yaml` - Per-circuit training

### Documentation
- ✅ `docs/06-release-pipeline.md` - Release pipeline documentation (future)
- ✅ `docs/COMPONENT_FLOW_DIAGRAM.md` - Corrected component flow
- ✅ `docs/CUTOFF_DATE_VERSION_VS_TAG.md` - Version vs tag strategy
- ✅ `docs/TESTING_GUIDE.md` - Testing procedures

### Progress Tracking
- ✅ `IMPLEMENTATION_PROGRESS.md` - Current implementation status

## Six Major Inconsistencies Fixed

1. ❌ **Data Component** → ✅ Direct Azure CLI per circuit
2. ❌ **Generic MLTable naming** → ✅ Per-circuit: `PLANT_CIRCUIT:cutoff_date`
3. ❌ **Azure ML parallel component** → ✅ DevOps matrix strategy
4. ❌ **No component version tracking** → ✅ Dynamic version capture
5. ❌ **Registry environment reference** → ✅ Workspace environment
6. ❌ **Unclear cutoff_date usage** → ✅ VERSION for MLTable, TAG for others

## Reference

For the corrected architecture, see:
- Main `README.md`
- `IMPLEMENTATION_PROGRESS.md`
- `.azuredevops/build-pipeline.yml`

## Notes

- **Release pipeline NOT archived** - It's a future implementation (Step 7)
- **06-release-pipeline.md NOT archived** - Documentation for future use
- **Testing documentation NOT archived** - Active testing procedures
- **Component flow diagrams NOT archived** - Current architecture diagrams
