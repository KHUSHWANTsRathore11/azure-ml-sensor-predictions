# Monitoring & Notifications

Job monitoring, failure handling, and notification setup.

## Training Job Monitoring

**Stage 6:** Monitor submitted training jobs

**Polling Strategy:**
```python
# Exponential backoff
initial_delay = monitoringPollIntervalSeconds  # 30s
max_delay = 300s  # 5 min
max_wait = monitoringMaxWaitHours * 3600  # 3 hours

while elapsed < max_wait:
    status = check_all_jobs()
    if all_complete:
        break
    sleep(min(current_delay, max_delay))
    current_delay *= 2
```

**Configuration:**
```yaml
# mlops-pipeline-settings Variable Group
monitoringMaxWaitHours: 3
monitoringPollIntervalSeconds: 30
monitoringLogLevel: "DEBUG"
```

## Failure Scenarios

### Training Job Failures

**Automatic Retry:**
- Max retries: 2
- Timeout: 3600s
- Configured in pipeline component

**Manual Retry:**
```bash
# Specify failed circuits manually
manualCircuits: "PLANT001/CIRCUIT01,PLANT002/CIRCUIT02"
```

### Deployment Failures

**Auto-Rollback (Prod):**
```yaml
auto_rollback:
  enabled: true
  error_threshold: 5%
  latency_threshold: 2000ms
```

**Manual Rollback:**
```bash
az pipelines run --name "rollback-pipeline"
```

## Notifications

### Azure DevOps Native

**Built-in notifications:**
- Pipeline completion
- Pipeline failure
- Approval required

**Setup:**
1. Azure DevOps → User Settings → Notifications
2. Enable desired notifications
3. Configure email preferences

### Teams Integration

**Setup:**
1. Create Teams webhook
2. Add to Variable Group:
   ```yaml
   teamsWebhookUrl: "https://outlook.office.com/webhook/..."
   ```
3. Pipeline sends notifications automatically

**Notification Events:**
- Training started
- Training completed
- Training failed
- Approval required
- Deployment completed

### Long-Running Job Alerts

**Configuration:**
```yaml
longRunningJobNotificationIntervalHours: 4
mlEngineersEmail: "ml-team@company.com"
```

**Behavior:**
- Send email every 4 hours for running jobs
- Include job status and elapsed time
- Stop when job completes

## Monitoring Best Practices

1. **Set reasonable timeouts** - 3 hours for training
2. **Use exponential backoff** - Reduce API calls
3. **Monitor in Azure ML Studio** - Visual job tracking
4. **Enable Teams notifications** - Real-time alerts
5. **Check logs regularly** - Identify issues early
6. **Set up dashboards** - Track metrics over time
7. **Configure auto-rollback** - Prod safety net
