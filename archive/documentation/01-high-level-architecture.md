# High-Level Architecture

[← Back to README](../README.md)

---

## Architecture Overview

Production-ready Azure Machine Learning MLOps architecture for **75-200 time series forecasting models** with multi-stage deployment and approval gates.

### System Diagram

```mermaid
graph TB
    subgraph "Data Layer - ETL Every 3 Hours"
        A[Production ADLS Gen2<br/>Parquet Files] --> B[Synapse Spark Pool<br/>ETL Processing]
        C[Synapse Dedicated Pool<br/>SQL Tables] --> B
        B -->|Merge/Upsert Mode| D[Production ADLS Gen2<br/>Delta Lake<br/>Single Table]
    end

    subgraph "Config Management"
        R[Git Repository<br/>Azure DevOps] --> S[config/plants_circuits.yml<br/>Master Config]
        R --> T[config/plants/P1/C1.yml<br/>Per-Circuit Configs]
        T -->|Contains| U[cutoff_date<br/>hyperparameters]
    end

    subgraph "PR-Based Training - Dev Workspace"
        V[Pull Request<br/>Config Change] --> W[Build Pipeline<br/>Git Diff Detection]
        W --> X[Parallel Training<br/>maxParallel=5]
        
        X --> Y[Register MLTable<br/>per Circuit]
        Y --> Z[Train Models<br/>with Data Asset]
        
        Z --> AA[Dev Workspace<br/>Model Registry]
        AA --> AB[Build Artifact<br/>Model Metadata]
    end

    subgraph "Release Pipeline - Multi-Stage Deployment"
        AB --> AC[Stage 1: Promote to Registry]
        AC -->|Manual Approval| AD[Azure ML Registry<br/>Shared]
        
        AD --> AE[Stage 2: Deploy to Test]
        AE --> AF[Test Workspace<br/>Batch Endpoints]
        AF --> AG[Test Inference<br/>Latest Data]
        AG -->|Success: No Errors| AH{Test Passed?}
        
        AH -->|Yes| AI[Stage 3: Deploy to Prod]
        AI -->|Manual Approval| AJ[Production Workspace<br/>Batch Endpoints]
        AH -->|No| AK[Fail Release<br/>Alert Team]
    end

    subgraph "Production Inference - Daily"
        D -->|Direct Read| AL[75-200 Batch<br/>Invocations Daily]
        AL --> AJ
        AJ --> AM[Predictions Output<br/>per Plant/Circuit]
    end

    subgraph "Monitoring & Rollback"
        AN[Azure Monitor<br/>Per-Circuit Metrics] --> AO[Performance Degraded?]
        AO -->|Yes| AP[Rollback via<br/>Azure DevOps Release]
        AP --> AI
    end

    D --> Y

    style D fill:#4CAF50
    style AD fill:#9C27B0
    style AF fill:#FF9800
    style AJ fill:#2196F3
    style AC fill:#FFC107
    style AI fill:#FFC107
```

---

## Key Architectural Decisions

### 1. Multi-Workspace Strategy
- **Dev Workspace:** Training and experimentation
- **Shared Azure ML Registry:** Central model and environment store
- **Test Workspace:** Integration testing and validation
- **Production Workspace:** Production inference only

**Rationale:** Isolation between environments, shared registry for consistency, approval gates between stages.

### 2. Multi-Model Organization
- **Scale:** 75-200 models (5-10 circuits per plant × 15-20 plants)
- **Batch Endpoints:** One per plant (15-20 total)
- **Deployments:** One per circuit within plant (5-10 per endpoint)

**Rationale:** Logical grouping by plant, independent updates per circuit, simplified endpoint management.

### 3. Hybrid Data Strategy
- **Training:** MLTable Data Assets with date-based versions for reproducibility
- **Inference:** Direct Delta Lake reads for performance

**Rationale:** Training requires reproducibility (Data Assets), inference needs latest data (direct reads).

### 4. PR-Based Training Workflow
- **Trigger:** Git config file changes
- **Execution:** Parallel training (maxParallel=5)
- **Output:** Build artifact with model metadata

**Rationale:** Config-driven changes, automated training, controlled parallelism.

### 5. Three-Stage Release Pipeline
- **Stage 1:** Promote to Registry (manual approval + evidence)
- **Stage 2:** Deploy to Test (automated validation)
- **Stage 3:** Deploy to Production (manual approval)

**Rationale:** Approval gates, automated testing, audit trail, rollback capability.

---

## Azure Resources

### Core Services

| Service | Purpose | SKU |
|---------|---------|-----|
| Azure ML Registry | Shared model/environment registry | Enterprise |
| Azure ML Workspaces (3) | Dev, Test, Production | Enterprise Edition |
| ADLS Gen2 | Delta Lake storage | Standard LRS |
| Synapse Analytics | ETL processing (every 3 hours) | Spark Pool (Small) |
| Azure DevOps | CI/CD pipelines | Free tier |
| Azure Monitor | Alerting and metrics | Standard |

### Compute Resources

| Resource | Configuration | Purpose |
|----------|--------------|---------|
| Dev Compute Cluster | DS3_v2, 0-4 nodes | Training (parallel) |
| Test Compute Cluster | DS2_v2, 0-2 nodes | Test inference |
| Prod Compute Cluster | DS3_v2, 0-4 nodes | Production inference |

---

## Data Flow

### Training Flow
```
Config Change (PR) 
  → Git Diff Detection 
  → Register MLTable (per circuit, date-based version)
  → Parallel Training (maxParallel=5)
  → Model Registration (Dev Workspace)
  → Build Artifact Creation
```

### Deployment Flow
```
Build Artifact
  → Stage 1: Promote to Registry (manual approval)
  → Stage 2: Deploy to Test + Validate
  → Stage 3: Deploy to Production (manual approval)
```

### Inference Flow
```
ETL (every 3 hours) 
  → Delta Lake Update
  → Daily Batch Inference (75-200 invocations)
  → Predictions per Plant/Circuit
```

---

## Approval Gates

### Registry Promotion
- **Approvers:** ML Engineers
- **Evidence Required:**
  - PR review
  - Interactive notebook showing scoring execution in Dev
  - Training logs and metrics
  - Data lineage confirmation
- **Timeout:** 24 hours

### Production Deployment
- **Approvers:** ML Engineers or Engineering Managers
- **Evidence Required:**
  - Successful test validation
  - No errors in test inference
  - Rollback plan documented
- **Timeout:** 24 hours

---

## Versioning Strategy

| Asset Type | Versioning Rule | Example | Notes |
|------------|----------------|---------|-------|
| **Models** | Integer (auto-increment) | `1`, `2`, `15` | Azure ML enforced |
| **Environments** | Semantic versioning | `1.5.0`, `2.0.0` | String versions supported |
| **Data Assets** | Date-based strings | `2025-12-09` | Self-documenting |
| **Configs** | Git SHA | `a1b2c3d4` | Source control |

---

## Rollback Strategy

- **Method:** Redeploy previous successful Azure DevOps Release
- **SLA:** 15-20 minutes
- **Scope:** Per-circuit or all deployments
- **Tracking:** Previous version tagged in deployment metadata

---

## Next Steps

- [Data Architecture Details →](02-data-architecture.md)
- [Multi-Model Strategy →](03-multi-model-strategy.md)
- [Implementation Checklist →](14-implementation-checklist.md)
