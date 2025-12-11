# Azure MLOps Architecture - Time Series Forecasting

**Project:** Multi-Model Time Series Forecasting with TensorFlow  
**Date:** December 9, 2025  
**Version:** 4.1

---

## 📋 Overview

Production-ready Azure Machine Learning MLOps architecture managing **75-200 independent models** (5-10 sensor circuits per plant × 15-20 plants) with automated training, testing, and deployment pipelines.

### Key Capabilities
- ✅ **Multi-Model Scale:** 75-200 models with per-circuit configuration
- ✅ **PR-Based Training:** Automated parallel training triggered by config changes
- ✅ **Multi-Stage Deployment:** Dev → Registry → Test → Production with approval gates
- ✅ **Config Hash Tracking:** Deterministic model lineage across pipeline runs
- ✅ **Environment Management:** Semantic versioning with breaking/non-breaking change workflows
- ✅ **Data Versioning:** Date-based MLTable Data Assets for reproducibility
- ✅ **Rollback:** 15-20 minute SLA via Azure DevOps Release history

---

## 📚 Documentation Structure

### 🏗️ Architecture Documentation
1. **[High-Level Architecture](docs/01-high-level-architecture.md)** - System overview, diagrams, design decisions
2. **[Data Architecture](docs/02-data-architecture.md)** - ETL, Delta Lake, MLTable strategy, versioning rules
3. **[Multi-Model Strategy](docs/03-multi-model-strategy.md)** - Config management, batch endpoints, scaling
4. **[Environment Management](docs/04-environment-management.md)** - Versioning, breaking/non-breaking changes, promotion
   - **[Config Hash Strategy](docs/config-hash-strategy.md)** - Model lineage tracking across pipeline runs

### 🔄 CI/CD & Deployment
5. **[Build Pipeline](docs/05-build-pipeline.md)** - PR-based training workflow, parallel execution
6. **[Release Pipeline](docs/06-release-pipeline.md)** - 3-stage deployment (Registry → Test → Prod)
7. **[Environment-Only Pipeline](docs/07-environment-only-pipeline.md)** - Non-breaking environment updates
8. **[Rollback Procedures](docs/08-rollback-procedures.md)** - Emergency rollback workflows

### 💻 Code & Scripts
9. **[Scripts Reference](docs/09-scripts-reference.md)** - All Python scripts with usage examples
10. **[Pipeline YAML Reference](docs/10-pipeline-yaml-reference.md)** - Complete pipeline definitions

### 📊 Operations
11. **[Monitoring Strategy](docs/11-monitoring-strategy.md)** - Azure Monitor, alerts, drift detection
12. **[Operational Runbooks](docs/12-operational-runbooks.md)** - Common scenarios and troubleshooting
13. **[Cost Estimation](docs/13-cost-estimation.md)** - Monthly costs and optimization tips
16. **[Model Monitoring & Data Drift](docs/16-model-monitoring-data-drift.md)** - Azure ML v2 monitoring, drift detection, App Insights

### 🚀 Implementation
14. **[Implementation Checklist](docs/14-implementation-checklist.md)** - 12-week phased rollout plan
15. **[Azure Well-Architected Assessment](docs/15-well-architected-assessment.md)** - Security, reliability, performance

---

## 🎯 Quick Start

### Prerequisites
- Azure Subscription with appropriate permissions
- Azure DevOps organization
- Azure ML Workspaces (Dev, Test, Prod) + Azure ML Registry
- Azure Synapse Analytics workspace
- ADLS Gen2 storage account

### Setup Overview
1. **Week 1-2:** Provision Azure resources (see [Implementation Checklist](docs/14-implementation-checklist.md#phase-1))
2. **Week 3-4:** Configure multi-model structure and ETL pipeline
3. **Week 5-6:** Develop ML training pipeline and batch endpoints
4. **Week 7-9:** Implement Build + Release pipelines with approval gates
5. **Week 9-10:** Add environment-only release pipeline
6. **Week 10-11:** Configure monitoring and alerts
7. **Week 11-12:** End-to-end testing and validation

---

## 🏛️ Architecture Highlights

### Data Flow
```
Synapse ETL (every 3 hours) 
  → Delta Lake (single table, merge mode) 
  → MLTable Data Assets (date-based versions) 
  → Training (parallel, maxParallel=5)
  → Models (integer versions)
  → Registry → Test → Production
```

### Deployment Strategy
```
PR with Config Change 
  → Build Pipeline (training + artifact) 
  → Release Stage 1: Promote to Registry (manual approval)
  → Release Stage 2: Deploy to Test (auto, with validation)
  → Release Stage 3: Deploy to Production (manual approval)
```

### Environment Updates
```
Breaking Change (e.g., TensorFlow upgrade)
  → Update configs → Full retrain → Normal Release Pipeline

Non-Breaking Change (e.g., bug fix)
  → Environment-Only Release Pipeline 
  → Test ALL 75-200 models 
  → Update all deployments at once
```

---

## 📊 Architecture at a Glance

| Component | Configuration | Details |
|-----------|--------------|---------|
| **Models** | 75-200 models | One per sensor circuit |
| **Batch Endpoints** | 15-20 endpoints | One per plant |
| **Deployments** | 5-10 per endpoint | One per circuit within plant |
| **Training Frequency** | On-demand (PR-based) | Parallel execution (maxParallel=5) |
| **Inference Frequency** | Daily | 75-200 separate invocations |
| **ETL Frequency** | Every 3 hours | Synapse Spark Pool |
| **Monthly Cost** | ~$1,483 | Full scale (75-200 models, 3 workspaces) |
| **Rollback SLA** | 15-20 minutes | Via Azure DevOps Releases |

---

## 🔑 Key Design Decisions

### Versioning Strategy
- **Models:** Integer-only (Azure ML auto-increment: `1`, `2`, `3`)
- **Environments:** Semantic versioning strings (`1.5.0`, `2.0.0`)
- **Data Assets:** Date-based strings (`2025-12-09`)
- **Fixed Versions:** Configs specify exact env version for reproducibility

### Multi-Model Organization
- **Per-Plant Endpoints:** Logical grouping by facility
- **Per-Circuit Deployments:** Independent scaling and updates
- **Shared Registry:** Single source of truth across Dev/Test/Prod
- **Config-Driven:** YAML files control cutoff dates and hyperparameters

### Approval Gates
- **Registry Promotion:** Manual approval + interactive notebook evidence
- **Production Deployment:** Manual approval + successful test validation
- **Environment Updates:** Integration testing ALL models before production

---

## 🛠️ Technology Stack

- **ML Platform:** Azure Machine Learning (Dev/Test/Prod Workspaces + Registry)
- **Data Engineering:** Azure Synapse Analytics (Spark Pool)
- **Storage:** ADLS Gen2 with Delta Lake
- **ML Framework:** TensorFlow 2.13+
- **CI/CD:** Azure DevOps (Build + Release Pipelines)
- **Monitoring:** Azure Monitor + Application Insights
- **IaC:** Azure CLI + Python SDK

---

## 📖 Additional Resources

- [Azure ML Documentation](https://learn.microsoft.com/en-us/azure/machine-learning/)
- [Delta Lake Documentation](https://docs.delta.io/)
- [Azure DevOps Pipelines](https://learn.microsoft.com/en-us/azure/devops/pipelines/)
- [Azure Synapse Analytics](https://learn.microsoft.com/en-us/azure/synapse-analytics/)

---

## 📝 Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| 4.1 | 2025-12-09 | Corrected Azure ML versioning rules (Models: int, Envs/Data: string) |
| 4.0 | 2025-12-09 | Added environment management strategy with breaking/non-breaking workflows |
| 3.0 | 2025-12-09 | Multi-workspace deployment with Azure DevOps Releases |
| 2.0 | 2025-12-09 | Multi-model architecture (75-200 models) with PR-based training |
| 1.0 | 2025-12-08 | Initial architecture design |

---

**For detailed implementation guidance, start with the [Implementation Checklist](docs/14-implementation-checklist.md).**
