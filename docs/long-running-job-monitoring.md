# Long-Running Job Monitoring

## Overview

The pipeline automatically monitors training jobs and provides notifications when jobs run longer than expected. This helps ML engineers stay informed about long-running training without constantly checking the pipeline.

---

## Features

### 1. **Automatic Monitoring**

The `WaitForTrainingJobs` stage monitors all submitted training jobs and tracks:
- Job start time
- Current status (Queued, Running, Completed, Failed, Canceled)
- Elapsed time
- Last notification time

### 2. **Periodic Notifications**

When a job runs longer than the configured threshold (default: 4 hours), the pipeline logs:

```
======================================================================
⏳ LONG-RUNNING JOB ALERT
======================================================================
Job: PLANT001_CIRCUIT01_2025_12_11
Status: Running
Running for: 4.2 hours
Started at: 2025-12-11 09:00:00
View in Studio: https://ml.azure.com/runs/...

📧 Notification: ML Engineers should check job progress
   - Review logs in Azure ML Studio
   - Verify compute is running efficiently
   - Consider cancelling if stuck
======================================================================
```

The notification repeats every 4 hours (configurable) until the job completes.

### 3. **Azure DevOps Warnings**

Long-running jobs also create warnings in the Azure DevOps pipeline UI:
```
⚠️ Job PLANT001_CIRCUIT01_2025_12_11 running for 4.2h - Status: Running
```

These warnings are visible in:
- Pipeline run summary
- Timeline view
- Email notifications (if configured in Azure DevOps)

### 4. **Progress Updates**

Every 10 minutes, the pipeline logs progress for running jobs:
```
⏰ Status check #10 - 3 job(s) remaining...
   ⏳ PLANT001_CIRCUIT01_2025_12_11: Running (0.2h elapsed)
   ⏳ PLANT002_CIRCUIT05_2025_12_11: Running (0.3h elapsed)
   ⏳ PLANT003_CIRCUIT10_2025_12_11: Queued (0.1h elapsed)
```

---

## Configuration

### Notification Interval

Set the notification interval via pipeline variable:

```yaml
variables:
  - name: longRunningJobNotificationIntervalHours
    value: '4'  # Default: 4 hours
```

**Options:**
- `2` - Notify every 2 hours (more frequent)
- `4` - Notify every 4 hours (default, recommended)
- `6` - Notify every 6 hours (less frequent)
- `8` - Notify every 8 hours (minimal)

### Email Notifications (Optional)

To enable email notifications, you can extend the pipeline with Azure DevOps notification features:

#### Option 1: Azure DevOps Project Notifications

1. Go to Project Settings → Notifications
2. Create a subscription for "Build completes" with conditions
3. Set filters: `Status = In Progress` + `Duration > X hours`

#### Option 2: Custom Email Task (Future Enhancement)

Add an email task when long-running job detected:

```yaml
- task: SendEmail@1
  condition: eq(variables['LongRunningJobDetected'], 'true')
  inputs:
    To: '$(mlEngineersEmail)'
    Subject: '[ALERT] Long-Running Training Jobs - $(Build.BuildNumber)'
    Body: |
      Training jobs have been running for more than $(longRunningJobNotificationIntervalHours) hours.
      
      Pipeline: $(Build.DefinitionName)
      Build: $(Build.BuildNumber)
      
      View in Azure DevOps:
      $(System.TeamFoundationCollectionUri)$(System.TeamProject)/_build/results?buildId=$(Build.BuildId)
      
      Review job status in Azure ML Studio.
```

#### Option 3: Teams/Slack Integration

Use webhooks to send notifications to Teams or Slack:

```python
# Add to notification logic
import requests

def send_teams_notification(job_name, elapsed_hours, studio_url):
    """Send notification to Microsoft Teams."""
    webhook_url = os.getenv('TEAMS_WEBHOOK_URL')
    if not webhook_url:
        return
    
    message = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": "Long-Running Training Job Alert",
        "themeColor": "FF9800",  # Orange
        "title": "⏳ Long-Running Training Job",
        "sections": [{
            "activityTitle": f"Job: {job_name}",
            "facts": [
                {"name": "Status", "value": "Running"},
                {"name": "Elapsed Time", "value": f"{elapsed_hours:.1f} hours"},
                {"name": "Started", "value": job_start_time[job_name].isoformat()}
            ],
            "markdown": True
        }],
        "potentialAction": [{
            "@type": "OpenUri",
            "name": "View in Azure ML Studio",
            "targets": [{"os": "default", "uri": studio_url}]
        }]
    }
    
    requests.post(webhook_url, json=message)
```

---

## Expected Training Times

### Typical Training Durations

Based on our LSTM models:

| Scenario | Expected Duration | Alert Threshold | Action |
|----------|------------------|----------------|--------|
| Small circuit (< 10k samples) | 15-30 minutes | 2 hours | Review if > 2h |
| Medium circuit (10k-100k samples) | 30-90 minutes | 3 hours | Review if > 3h |
| Large circuit (> 100k samples) | 1-3 hours | 5 hours | Review if > 5h |
| Hyperparameter tuning | 2-6 hours | 8 hours | Expected |

### When to Investigate

**Investigate immediately if:**
- Job queued for > 30 minutes (possible quota issue)
- Job running for > 2x expected time
- All jobs stuck in same status

**Normal scenarios:**
- First run with cold compute (15-20 min startup)
- Large dataset processing (proportional to data size)
- Complex model architecture (longer training per epoch)

---

## Troubleshooting Long-Running Jobs

### 1. Check Job Status in Azure ML Studio

```bash
# Get detailed job status
az ml job show \
  --name <job_name> \
  --workspace-name <workspace> \
  --resource-group <rg> \
  --query "{status: status, duration: duration, error: error}" \
  -o table
```

### 2. Review Job Logs

In Azure ML Studio:
1. Navigate to Jobs → Select job
2. Click "Outputs + logs"
3. Check `user_logs/std_log.txt` for training output
4. Check `system_logs/` for infrastructure issues

### 3. Common Issues

#### Job Stuck in "Queued"
**Cause:** Quota exceeded or no available compute nodes

**Solution:**
```bash
# Check cluster status
az ml compute show --name training-cluster --workspace-name <workspace>

# Check running jobs
az ml job list --workspace-name <workspace> --query "[?status=='Running']"
```

#### Job Running Very Slowly
**Cause:** Wrong compute SKU, inefficient code, or data loading bottleneck

**Solution:**
- Check CPU/GPU utilization in Studio metrics
- Review training logs for performance issues
- Consider larger compute SKU

#### Job Not Progressing
**Cause:** Hung process, deadlock, or infinite loop

**Solution:**
```bash
# Cancel the job
az ml job cancel --name <job_name> --workspace-name <workspace>

# Review logs to identify issue
# Fix code and resubmit
```

---

## Monitoring Dashboard (Optional)

Create an Azure Monitor workbook to track training job metrics:

```kusto
// Query: Average training duration by circuit
AzureMLJobCompleted
| where WorkspaceName == "mlops-dev-workspace"
| where JobType == "Pipeline"
| extend Duration = datetime_diff('hour', EndTime, StartTime)
| summarize 
    AvgDuration = avg(Duration),
    MinDuration = min(Duration),
    MaxDuration = max(Duration),
    Count = count()
    by CircuitId = tostring(parse_json(Tags).circuit_id)
| order by AvgDuration desc
```

---

## Best Practices

### 1. Set Realistic Expectations
- Document expected training times for different circuit sizes
- Update notification thresholds based on actual data
- Adjust intervals for different model types

### 2. Early Detection
- Monitor job queue time (should be < 5 minutes)
- Track first epoch completion time (indicator of final duration)
- Set alerts for jobs stuck > 2x expected time

### 3. Proactive Cancellation
- Cancel jobs that are clearly stuck
- Don't wait for timeout (can take hours)
- Investigate root cause before resubmitting

### 4. Capacity Planning
- Monitor concurrent job limits
- Track quota usage trends
- Request quota increases proactively

### 5. Regular Review
- Weekly review of training durations
- Identify optimization opportunities
- Update compute SKUs as needed

---

## Example Scenarios

### Scenario 1: Normal Training Run

```
⏰ Status check #1 - 5 job(s) remaining...
   ⏳ PLANT001_CIRCUIT01: Running (0.1h elapsed)
   ⏳ PLANT001_CIRCUIT02: Running (0.1h elapsed)
   ...

⏰ Status check #45 - 3 job(s) remaining...
   ✅ PLANT001_CIRCUIT01: Completed (took 0.8h)
   ✅ PLANT001_CIRCUIT02: Completed (took 0.9h)
   ⏳ PLANT002_CIRCUIT05: Running (1.2h elapsed)
   
... all jobs complete within 3 hours
✅ 5 job(s) completed successfully
```

### Scenario 2: Long-Running Job with Notifications

```
⏰ Status check #240 - 1 job(s) remaining...
   ⏳ PLANT005_CIRCUIT99: Running (4.0h elapsed)

======================================================================
⏳ LONG-RUNNING JOB ALERT
======================================================================
Job: PLANT005_CIRCUIT99_2025_12_11
Status: Running
Running for: 4.0 hours
...
======================================================================

⏰ Status check #480 - 1 job(s) remaining...
   ⏳ PLANT005_CIRCUIT99: Running (8.0h elapsed)

======================================================================
⏳ LONG-RUNNING JOB ALERT  [2nd notification]
======================================================================
...

⏰ Status check #520 - 0 job(s) remaining...
   ✅ PLANT005_CIRCUIT99: Completed (took 8.7h)
   
✅ 1 job(s) completed successfully
⚠️ Note: Job took longer than expected (8.7h)
```

### Scenario 3: Stuck Job Requiring Intervention

```
⏰ Status check #30 - 5 job(s) remaining...
   ⏳ PLANT001_CIRCUIT01: Queued (0.5h elapsed)  ⚠️ Stuck
   
⏰ Status check #60 - 5 job(s) remaining...
   ⏳ PLANT001_CIRCUIT01: Queued (1.0h elapsed)  ⚠️ Still stuck

Manual intervention required:
1. Check Azure ML quota
2. Verify compute cluster is healthy
3. Cancel and resubmit if needed
```

---

## Configuration Summary

| Setting | Default | Recommended | Notes |
|---------|---------|-------------|-------|
| Notification Interval | 4 hours | 3-6 hours | Adjust based on typical training duration |
| Poll Interval | 60 seconds | 60 seconds | Don't reduce (API throttling) |
| Progress Update Frequency | 10 minutes | 10-15 minutes | Balance between visibility and log clutter |
| Max Expected Duration | None | 12 hours | Consider adding timeout |

---

## Future Enhancements

1. **Adaptive Thresholds:** Automatically adjust notification interval based on circuit size
2. **Predictive Alerts:** Estimate completion time based on progress
3. **Auto-Cancellation:** Option to auto-cancel jobs stuck in queue > X minutes
4. **Rich Notifications:** Include metrics, progress bars, estimated completion
5. **Integration:** Teams/Slack/PagerDuty notifications
6. **Historical Analysis:** Track training duration trends over time
