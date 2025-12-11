# Cost Estimation

[← Back to README](../README.md)

## Overview

Detailed monthly cost estimation for the Azure ML sensor predictions architecture at full scale (75-200 models across dev, test, and production environments).

## Monthly Cost Summary

**Total Estimated Monthly Cost: ~$1,483**

| Category | Cost | Percentage |
|----------|------|------------|
| Compute (Training + Inference) | $950 | 64% |
| Storage (ADLS + Workspaces) | $40 | 3% |
| Data Engineering (Synapse) | $100 | 7% |
| Batch Endpoints | $300 | 20% |
| Monitoring & Other | $93 | 6% |

## Detailed Cost Breakdown

### Core Resources (Multi-Environment)

| Resource | SKU/Configuration | Monthly Cost | Notes |
|----------|------------------|--------------|-------|
| **Azure ML Registry** | Enterprise | $0 | No separate charge |
| **Dev ML Workspace** | Enterprise | $0 | Training workspace |
| **Test ML Workspace** | Enterprise | $0 | Integration testing |
| **Production ML Workspace** | Enterprise | $0 | Inference workspace |
| **Production ADLS Gen2** | 1TB data (shared) | $20 | All workspaces read from here |
| **Workspace Storage** | 500GB × 3 workspaces | $15 | Dev/Test/Prod outputs |
| **Synapse Spark Pool** | Small, 8hrs/day | $100 | ETL every 3 hours |
| **Dev Compute Cluster** | DS3_v2, 4 nodes × 10hrs/month | $300 | Training (maxParallel=5) |
| **Test Compute Cluster** | DS2_v2, 2 nodes × 5hrs/month | $50 | Test inference |
| **Prod Compute Cluster** | DS3_v2, 4 nodes × 20hrs/month | $600 | Daily inference (75-200 invocations) |
| **Batch Endpoints** | 15-20 endpoints × 2 envs | $300 | Test + Prod (per-plant) |
| **Application Insights** | 30GB logs/month × 3 | $60 | Multi-workspace logging |
| **Azure DevOps** | Basic plan (5 users) | Free | Build + Release pipelines |
| **Azure Monitor Alerts** | 75 alert rules | $15 | Per circuit + environment |
| **Data Assets Storage** | 75-200 MLTable defs | $5 | Metadata only |
| **Environment Testing** | Integration tests | $10 | 2-3 updates/year |
| **Azure Container Registry** | Basic tier | $5 | Shared Docker images |
| **Azure Key Vault** | Standard | $3 | Secrets management |
| **TOTAL** | | **$1,483** | Full scale |

## Cost Breakdown by Environment

### Dev Workspace (~$400/month)

| Resource | Cost | Usage Pattern |
|----------|------|---------------|
| Compute Cluster | $300 | Training jobs (maxParallel=5) |
| Storage | $10 | MLTable definitions, models |
| Application Insights | $20 | Training logs |
| Environment builds | $5 | 2-3 builds/month |
| Data Assets | $5 | MLTable registrations |
| Container Registry | $5 | Docker images |
| **Subtotal** | **$345** | |

### Test Workspace (~$200/month)

| Resource | Cost | Usage Pattern |
|----------|------|---------------|
| Compute Cluster | $50 | Test inference |
| Batch Endpoints | $100 | 15-20 test endpoints |
| Storage | $5 | Test outputs |
| Application Insights | $20 | Test logs |
| Integration Testing | $10 | Environment compatibility |
| **Subtotal** | **$185** | |

### Production Workspace (~$700/month)

| Resource | Cost | Usage Pattern |
|----------|------|---------------|
| Compute Cluster | $600 | Daily inference (75-200 invocations) |
| Batch Endpoints | $200 | 15-20 production endpoints |
| Storage | $10 | Prediction outputs |
| Application Insights | $20 | Inference logs |
| **Subtotal** | **$830** | |

### Shared Infrastructure (~$183/month)

| Resource | Cost | Usage Pattern |
|----------|------|---------------|
| Production ADLS Gen2 | $20 | Shared input data |
| Synapse Spark Pool | $100 | ETL every 3 hours |
| Azure Monitor | $15 | Alert rules |
| Key Vault | $3 | Secrets |
| **Subtotal** | **$138** | |

## Cost Scaling by Model Count

### 10 Models (Initial Pilot)

| Category | Cost | Notes |
|----------|------|-------|
| Compute (Training) | $100 | 2 nodes, 5 hrs/month |
| Compute (Inference) | $150 | 2 nodes, 10 hrs/month |
| Batch Endpoints | $50 | 2-3 endpoints |
| Storage | $20 | Minimal outputs |
| Monitoring | $10 | 10 alert rules |
| Shared Infrastructure | $138 | Same as full scale |
| **Total** | **~$468/month** | |

### 75 Models (Mid Scale)

| Category | Cost | Notes |
|----------|------|-------|
| Compute (Training) | $250 | 4 nodes, 8 hrs/month |
| Compute (Inference) | $500 | 4 nodes, 18 hrs/month |
| Batch Endpoints | $250 | 12-15 endpoints |
| Storage | $35 | Moderate outputs |
| Monitoring | $15 | 75 alert rules |
| Shared Infrastructure | $138 | Same as full scale |
| **Total** | **~$1,188/month** | |

### 200 Models (Max Scale)

| Category | Cost | Notes |
|----------|------|-------|
| Compute (Training) | $400 | 4 nodes, 15 hrs/month |
| Compute (Inference) | $800 | 4 nodes, 25 hrs/month |
| Batch Endpoints | $400 | 20+ endpoints |
| Storage | $60 | Large outputs |
| Monitoring | $20 | 200 alert rules |
| Shared Infrastructure | $138 | Same as full scale |
| **Total** | **~$1,818/month** | |

## Cost Optimization Strategies

### Immediate Savings (20-40% reduction)

1. **Use Low-Priority VMs for Training**
   - Savings: ~$240/month (80% off training compute)
   - Risk: Jobs may be preempted
   - Best for: Non-urgent retraining

2. **Auto-Pause Synapse Spark Pool**
   - Savings: ~$30/month
   - Configuration: Auto-pause after 5 minutes idle
   - No downside

3. **ADLS Gen2 Lifecycle Management**
   - Savings: ~$10/month
   - Move old predictions to Cool tier after 90 days
   - Archive after 1 year

4. **Right-Size Compute Clusters**
   - Savings: ~$100/month
   - Monitor actual utilization
   - Reduce node count if underutilized

5. **Optimize Test Workspace**
   - Savings: ~$50/month
   - Use smaller compute
   - Run only when needed (not daily)

**Total Immediate Savings: ~$430/month (29%)**
**Optimized Cost: ~$1,053/month**

### Long-Term Optimizations

1. **Azure Reserved Instances**
   - Savings: 30-50% on compute
   - Commitment: 1-3 years
   - Best for: Stable production workload

2. **Spot Instances for Non-Critical Workloads**
   - Savings: Up to 90%
   - Use for: Dev workspace training

3. **Batch Multiple Circuits**
   - Reduce batch endpoint count
   - Deploy multiple circuits per endpoint
   - Savings: ~$100/month

4. **Optimize Alert Rules**
   - Consolidate similar alerts
   - Reduce noise
   - Savings: ~$5/month

5. **Dev Workspace in Separate Subscription**
   - Better cost tracking
   - Independent billing
   - Potential cost center allocation

## Cost Comparison by Phase

### Phase 1: Development Only (Months 1-3)

| Resource | Cost |
|----------|------|
| Dev Workspace | $400 |
| Shared Infrastructure | $138 |
| **Total** | **~$538/month** |

### Phase 2: Dev + Test (Months 4-6)

| Resource | Cost |
|----------|------|
| Dev Workspace | $400 |
| Test Workspace | $200 |
| Shared Infrastructure | $138 |
| **Total** | **~$738/month** |

### Phase 3: Full Production (Months 7+)

| Resource | Cost |
|----------|------|
| Dev Workspace | $400 |
| Test Workspace | $200 |
| Production Workspace | $700 |
| Shared Infrastructure | $183 |
| **Total** | **~$1,483/month** |

## Cost Monitoring & Alerts

### Budget Configuration

```json
{
  "budgets": [
    {
      "name": "Dev-Workspace-Budget",
      "amount": 450,
      "timeGrain": "Monthly",
      "alertThreshold": 90,
      "contactEmails": ["mlops-team@company.com"]
    },
    {
      "name": "Test-Workspace-Budget",
      "amount": 225,
      "timeGrain": "Monthly",
      "alertThreshold": 90,
      "contactEmails": ["mlops-team@company.com"]
    },
    {
      "name": "Prod-Workspace-Budget",
      "amount": 800,
      "timeGrain": "Monthly",
      "alertThreshold": 90,
      "contactEmails": ["mlops-team@company.com", "finance@company.com"]
    },
    {
      "name": "Total-Monthly-Budget",
      "amount": 1675,
      "timeGrain": "Monthly",
      "alertThreshold": 80,
      "contactEmails": ["engineering-manager@company.com"]
    }
  ]
}
```

### Cost Analysis Recommendations

1. **Weekly Reviews:**
   - Check compute utilization
   - Review storage growth
   - Identify anomalies

2. **Monthly Reports:**
   - Cost breakdown by workspace
   - Trend analysis
   - Optimization opportunities

3. **Quarterly Planning:**
   - Forecast based on model count
   - Plan for scale changes
   - Budget adjustments

## ROI Considerations

### Cost Avoidance

| Factor | Annual Savings |
|--------|---------------|
| Automated deployment (vs manual) | ~$50,000 |
| Early issue detection (monitoring) | ~$100,000 |
| Rollback capability (reduced downtime) | ~$200,000 |
| **Total Annual ROI** | **~$350,000** |

### Break-Even Analysis

- **Monthly MLOps Cost:** $1,483
- **Annual MLOps Cost:** $17,796
- **Cost Avoidance:** $350,000/year
- **Net Benefit:** $332,204/year
- **ROI:** 1,866%

## Related Documents

- [02-data-architecture.md](02-data-architecture.md) - Storage strategy
- [11-monitoring-strategy.md](11-monitoring-strategy.md) - Cost monitoring

---

**Document Version:** 1.0  
**Last Updated:** December 9, 2025  
**Note:** Costs are estimates based on Azure pricing as of December 2025 and may vary by region.
