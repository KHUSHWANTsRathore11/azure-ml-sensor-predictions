# Operational Runbooks

[← Back to README](../README.md)

## Overview

Operational runbooks for common scenarios in the Azure ML sensor predictions architecture, providing step-by-step procedures for ML Engineers and DevOps teams.

## Common Scenarios

### 1. New Model Deployment

**Trigger:** PR merged with config changes

**Steps:**
1. ✅ Verify Build Pipeline triggered automatically
2. ✅ Monitor parallel training jobs (maxParallel=5)
3. ✅ Check training metrics in Dev Workspace
4. ✅ Verify model registered to Dev Workspace
5. ✅ Wait for artifact publication
6. ✅ Release Pipeline auto-triggers
7. ✅ **Stage 1 Approval:**
   - Review model metrics (MAE, RMSE, R²)
   - Check training logs for anomalies
   - Approve or reject registry promotion
8. ✅ **Stage 2 Auto-Test:**
   - Monitor test inference execution
   - Verify no errors in logs
   - Check test output files
9. ✅ **Stage 3 Approval:**
   - Review test results
   - Approve or reject production deployment
10. ✅ Verify deployment tags in production
11. ✅ Monitor alerts for 24 hours

**Estimated Time:** 2-4 hours (depends on approval response time)

---

### 2. Emergency Rollback

**Trigger:** Performance degradation or errors in production

**Steps:**
1. ✅ **Identify Issue:**
   - Check Azure Monitor alerts
   - Review batch job logs
   - Identify affected plant_id/circuit_id
2. ✅ **Get Previous Version:**
   ```bash
   az ml batch-deployment show \
     --name "deployment-circuit-C001" \
     --endpoint-name "batch-endpoint-plant-P001" \
     --workspace-name "prod-ml-workspace" \
     --query 'tags.previous_version' -o tsv
   ```
3. ✅ **Execute Rollback:**
   - Option A: Azure DevOps Release redeploy (recommended)
   - Option B: Run `scripts/rollback_model.sh`
4. ✅ **Verify Rollback:**
   - Check deployment status
   - Run test inference
   - Monitor alerts for 1 hour
5. ✅ **Root Cause Analysis:**
   - Document issue in incident report
   - Identify root cause
   - Plan fix

**Estimated Time:** 15-20 minutes

---

### 3. Config Update (Hyperparameters)

**Trigger:** Need to tune model for specific circuit

**Steps:**
1. ✅ **Update Config File:**
   ```yaml
   # config/plants/P001/C001.yml
   training:
     cutoff_date: "2025-12-09"  # Keep same
     hyperparameters:
       learning_rate: 0.0005  # Changed from 0.001
       lstm_units: 256        # Changed from 128
   ```
2. ✅ **Create PR:**
   - Branch: `feature/tune-P001-C001`
   - Title: "Tune hyperparameters for P001/C001"
   - Description: Rationale for changes
3. ✅ **PR Review:**
   - Data scientist review
   - Approval
4. ✅ **Merge PR:**
   - Build Pipeline auto-triggers
   - Only P001/C001 retrains
5. ✅ **Follow "New Model Deployment" runbook**

**Estimated Time:** 1-3 hours (training + approval)

---

### 4. Environment Update (Non-Breaking)

**Trigger:** Bug fix or logging improvement in scoring script

**Steps:**
1. ✅ **Update Source Code:**
   - Modify `src/score.py`
   - Increment version in `environment/custom_tf_env.yml`
     - 1.5.0 → 1.5.1 (PATCH)
   - Update tags:
     ```yaml
     tags:
       backward_compatible: "true"
       requires_retrain: "false"
       change_summary: "Fixed logging bug"
     ```
2. ✅ **Test in Dev Workspace:**
   - Create interactive notebook
   - Load test model
   - Execute scoring
   - Verify no errors
3. ✅ **Trigger Environment-Only Pipeline:**
   - Manual trigger in Azure DevOps
4. ✅ **Stage 1 Approval:**
   - Provide notebook evidence
   - Approve registry promotion
5. ✅ **Stage 2 Integration Tests:**
   - Monitor tests for all 75-200 models
   - Verify all pass
6. ✅ **Stage 3 Approval:**
   - Review test results
   - Approve update-all deployment
7. ✅ **Stage 4 Monitor:**
   - Monitor for 24 hours
   - Check alert rates
   - Verify batch job success rates
8. ✅ **Rollback if Needed:**
   - Use Environment Rollback Pipeline

**Estimated Time:** 4-8 hours (testing all models takes time)

---

### 5. Model Performance Degradation

**Trigger:** Monthly monitoring alert for specific circuit

**Steps:**
1. ✅ **Investigate Alert:**
   - Check which metrics degraded (MAE, RMSE, MAPE)
   - Review recent predictions vs actuals
   - Identify plant_id/circuit_id
2. ✅ **Analyze Data Quality:**
   - Check Delta Lake for data issues
   - Verify ETL pipeline health
   - Look for data gaps or anomalies
3. ✅ **Check for Drift:**
   - Run ad-hoc drift detection
   - Compare current vs baseline distributions
4. ✅ **Decision:**
   - If data quality issue → Fix ETL, wait
   - If drift detected → Retrain with new cutoff_date
   - If model issue → Rollback to previous version
5. ✅ **Retrain (if needed):**
   - Update cutoff_date in config
   - Create PR
   - Follow "New Model Deployment" runbook
6. ✅ **Document:**
   - Update incident log
   - Track metrics trend

**Estimated Time:** 2-4 hours (investigation) + retrain time if needed

---

### 6. Data Drift Detected

**Trigger:** Quarterly drift monitoring alert

**Steps:**
1. ✅ **Review Drift Report:**
   - Identify which features drifted
   - Check drift magnitude
   - Review plant_id/circuit_id
2. ✅ **Analyze Drift:**
   - Is drift expected (seasonal, operational changes)?
   - Is drift gradual or sudden?
3. ✅ **Update Baseline:**
   - If drift is expected and gradual
   - Update cutoff_date in config
   - Retrain model with recent data
4. ✅ **Create PR:**
   - Update `cutoff_date` to recent date
   - Title: "Update training data for P001/C001 (drift detected)"
   - Include drift analysis in description
5. ✅ **Follow "New Model Deployment" runbook**
6. ✅ **Update Drift Monitor:**
   - Update baseline dataset reference
   - Reset drift tracking

**Estimated Time:** 1-2 hours (analysis) + retrain time

---

### 7. Troubleshooting Batch Job Failures

**Trigger:** Real-time alert for batch job failure

**Steps:**
1. ✅ **Identify Failed Job:**
   - Check Azure Monitor alert
   - Note plant_id, circuit_id, job_name
2. ✅ **Review Logs:**
   ```bash
   az ml job show \
     --name "$JOB_NAME" \
     --workspace-name "prod-ml-workspace"
   ```
3. ✅ **Common Issues:**
   - **Data not found:** Check Delta Lake path
   - **Memory error:** Reduce mini_batch_size
   - **Timeout:** Increase job timeout
   - **Model load error:** Check environment compatibility
4. ✅ **Fix Issue:**
   - Update deployment config if needed
   - Retry job manually
5. ✅ **Monitor:**
   - Verify next scheduled job succeeds

**Estimated Time:** 30 minutes - 2 hours

---

### 8. Multiple Releases Pending

**Trigger:** Multiple circuits trained, awaiting approval

**Steps:**
1. ✅ **Prioritize Circuits:**
   - Critical plants first
   - Group similar circuits
2. ✅ **Batch Review:**
   - Review metrics for all circuits
   - Compare to historical baselines
3. ✅ **Approve Strategy:**
   - Approve high-priority first
   - Approve similar circuits together
   - Reject if metrics don't meet threshold
4. ✅ **Monitor Deployment Queue:**
   - Track deployment progress
   - Check for conflicts
5. ✅ **Post-Deployment:**
   - Monitor all deployed circuits
   - Check for patterns in alerts

**Estimated Time:** 1-3 hours (depends on count)

---

### 9. Release Pipeline Stuck in Approval

**Trigger:** Release pending approval >12 hours

**Steps:**
1. ✅ **Review Release Details:**
   - Check model metrics
   - Review test results
   - Identify any blockers
2. ✅ **Decision:**
   - Approve if metrics acceptable
   - Reject if issues found
   - Document rejection reason
3. ✅ **Follow-up:**
   - If rejected, create issue for data scientist
   - If approved, monitor deployment

**Estimated Time:** 15-30 minutes

---

### 10. High Training Failure Rate

**Trigger:** >5 training failures in 24 hours

**Steps:**
1. ✅ **Identify Pattern:**
   - Check which circuits failed
   - Review failure logs
2. ✅ **Common Causes:**
   - **Data Asset registration failed:** Check Delta Lake access
   - **Config syntax error:** Validate YAML
   - **Compute quota exceeded:** Check cluster capacity
   - **Environment issue:** Verify environment available
3. ✅ **Fix Root Cause:**
   - Update configs if syntax error
   - Request quota increase if needed
   - Rebuild environment if corrupted
4. ✅ **Retry Failed Jobs:**
   - Use Manual Training Pipeline
   - Monitor success

**Estimated Time:** 1-2 hours

---

## Escalation Paths

| Issue Severity | First Contact | Escalation (if unresolved) |
|---------------|---------------|---------------------------|
| **Critical** (Production down) | On-Call ML Engineer | ML Engineering Manager |
| **High** (Performance degraded) | ML Engineer | Data Science Lead |
| **Medium** (Training failures) | ML Engineer | DevOps Engineer |
| **Low** (Monitoring alerts) | ML Engineer | N/A |

## Contact Information

| Role | Responsibility | Contact |
|------|---------------|---------|
| **On-Call ML Engineer** | 24/7 incident response | TBD |
| **ML Engineering Manager** | Escalation, approvals | TBD |
| **Data Science Lead** | Model quality decisions | TBD |
| **DevOps Engineer** | Infrastructure support | TBD |

## Related Documents

- [06-release-pipeline.md](06-release-pipeline.md) - Deployment process
- [08-rollback-procedures.md](08-rollback-procedures.md) - Rollback details
- [11-monitoring-strategy.md](11-monitoring-strategy.md) - Monitoring setup

---

**Document Version:** 1.0  
**Last Updated:** December 9, 2025
