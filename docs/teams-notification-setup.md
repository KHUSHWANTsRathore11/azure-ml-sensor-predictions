# Teams Notification Setup Guide

## Overview

This guide explains how to enable Microsoft Teams notifications for long-running training jobs. The pipeline is already configured with logging-based monitoring. Teams notifications are **optional** and can be added later.

---

## Current Status

✅ **Implemented (Active):**
- Automatic job monitoring with progress logs
- Long-running job alerts (every 4 hours) in pipeline logs
- Azure DevOps warnings in pipeline UI
- Configurable notification interval

⏸️ **Available (Not Enabled):**
- Microsoft Teams channel notifications
- Rich card formatting with job details
- Direct links to Azure ML Studio

---

## Why Add Teams Notifications?

### Benefits:
- **Proactive alerts:** Team sees notifications without checking pipeline
- **Centralized visibility:** All team members notified in shared channel
- **Rich formatting:** Clickable links to pipeline and Azure ML Studio
- **Mobile support:** Notifications on Teams mobile app

### When to Enable:
- Team wants push notifications for long-running jobs
- Multiple people need to monitor training progress
- Jobs frequently take 4+ hours
- Team uses Teams as primary communication tool

---

## Setup Instructions (Future Implementation)

### Prerequisites
- Microsoft Teams with appropriate permissions
- Azure DevOps pipeline edit access
- 10 minutes for setup

### Step 1: Create Teams Workflow (5 minutes)

#### Option A: Using Teams Workflows (Recommended - New Teams)

1. **Open Microsoft Teams** → Navigate to your channel (e.g., `#ml-ops` or `#ml-engineering`)

2. **Click channel name** → Click `•••` (More options) → **"Workflows"**

3. **Search for:** "Post to a channel when a webhook request is received"
   - If you don't see Workflows, use Option B below

4. **Click "Add workflow"** → Configure:
   ```
   Name: Training Pipeline Alerts
   Team: [Your team name]
   Channel: [Your channel, e.g., #ml-ops]
   ```

5. **Click "Add workflow"** → **Copy the HTTP POST URL**
   - URL format: `https://prod-XX.eastus.logic.azure.com:443/workflows/...`
   - This is your webhook URL

6. **Save the URL** securely (you'll need it in Step 2)

#### Option B: Using Power Automate (Alternative)

If Workflows are not available in your Teams:

1. **Go to https://make.powerautomate.com**

2. **Sign in** with your organization account

3. **Create** → "Instant cloud flow"

4. **Flow name:** "Training Pipeline Alerts"

5. **Trigger:** "When a HTTP request is received" → Click "Create"

6. **Click "New step"** → Search: "Post message in a chat or channel"

7. **Configure the action:**
   ```
   Post as: Flow bot
   Post in: Channel
   Team: [Select your team]
   Channel: [Select channel, e.g., ml-ops]
   Message: Use this expression:
   ```

8. **In the Message field**, click "Add dynamic content" → "Body"
   - This will insert: `@{triggerBody()}`

9. **Optional:** Format the message nicely:
   ```
   @{triggerBody()?['title']}
   
   @{triggerBody()?['text']}
   
   @{triggerBody()?['buildUrl']}
   ```

10. **Save the flow** → Go back to the first step ("When a HTTP request is received")

11. **Copy the HTTP POST URL** that appears after saving
    - URL format: `https://prod-XX.eastus.logic.azure.com:443/workflows/...`

12. **Save this URL** securely

#### Testing Your Webhook

Test that the webhook works before proceeding:

**PowerShell Test:**
```powershell
$webhook = "YOUR_WEBHOOK_URL_HERE"

$body = @{
    title = "Test Message"
    text = "If you see this in Teams, the webhook is working!"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri $webhook -Body $body -ContentType "application/json"
```

**Expected Result:** You should see a message appear in your Teams channel within seconds.

### Step 2: Add Webhook URL to Azure DevOps (2 minutes)

1. **Open Azure DevOps** → Navigate to your pipeline

2. **Click "Edit"** (top right)

3. **Click "Variables"** button (top right)

4. **Click "+ Add"** to create new variable:
   ```
   Name: TeamsWebhookURL
   Value: [Paste the webhook URL from Step 1]
   Secret: ✓ (IMPORTANT - Check this box!)
   Let users override: ☐ (Leave unchecked)
   Scope: Pipeline
   ```

5. **Click "OK"** → **Save**

### Step 3: Enable Teams Notification in Pipeline (3 minutes)

1. **Edit the pipeline YAML** (`.azuredevops/build-pipeline.yml`)

2. **Find the WaitForTrainingJobs stage** (around line 900)

3. **Update the monitoring task** to include output name:
   ```yaml
   - task: AzureCLI@2
     displayName: 'Wait for All Training Jobs'
     name: monitorJobs  # ← Add this line
     inputs:
       # ... existing configuration ...
   ```

4. **Find the Teams notification section** (around line 1150) and **uncomment it**:

   Change from:
   ```yaml
   # - task: PowerShell@2
   #   displayName: 'Send Teams Notification (Optional)'
   ```

   To:
   ```yaml
   - task: PowerShell@2
     displayName: 'Send Teams Notification'
   ```

5. **Replace the commented script** with the full implementation:
   ```yaml
   - task: PowerShell@2
     displayName: 'Send Teams Notification'
     condition: and(succeeded(), ne(variables['TeamsWebhookURL'], ''))
     inputs:
       targetType: 'inline'
       script: |
         $webhook = "$(TeamsWebhookURL)"
         
         if (-not $webhook) {
           Write-Host "⚠️  TeamsWebhookURL not configured - skipping notification"
           exit 0
         }
         
         # Build the notification message
         $buildUrl = "$(System.CollectionUri)$(System.TeamProject)/_build/results?buildId=$(Build.BuildId)"
         $studioUrl = "https://ml.azure.com/runs?wsid=/subscriptions/$(subscriptionId)/resourceGroups/$(resourceGroup)/providers/Microsoft.MachineLearningServices/workspaces/$(workspaceName)"
         
         # For Power Automate flow
         $body = @{
           title = "⏳ Long-Running Training Jobs Alert"
           text = "Training jobs in pipeline $(Build.DefinitionName) #$(Build.BuildNumber) have been running for 4+ hours. Please review job progress."
           buildUrl = "View Pipeline: $buildUrl"
           studioUrl = "Azure ML Studio: $studioUrl"
           branch = "Branch: $(Build.SourceBranchName)"
           status = "Status: In Progress"
         } | ConvertTo-Json -Depth 10
         
         try {
           Invoke-RestMethod -Method Post -Uri $webhook -Body $body -ContentType "application/json"
           Write-Host "✅ Teams notification sent successfully"
         }
         catch {
           Write-Host "⚠️  Failed to send Teams notification: $_"
           Write-Host "   Pipeline will continue - notification failure is non-critical"
           exit 0  # Don't fail pipeline if notification fails
         }
   ```

6. **Save and commit** the changes

### Step 4: Test the Integration (1 minute)

1. **Trigger the pipeline** (can be a test run)

2. **Wait for a job to run > 4 hours** OR temporarily change the notification interval:
   ```yaml
   variables:
     - name: longRunningJobNotificationIntervalHours
       value: '0.05'  # 3 minutes for testing
   ```

3. **Check Teams channel** for the notification

4. **Verify the message** includes:
   - Pipeline name and build number
   - Links to view the pipeline
   - Status information

5. **Restore the notification interval** to normal (4 hours) after testing

---

## Notification Message Format

### What the Teams Message Will Look Like:

```
⏳ Long-Running Training Jobs Alert

Training jobs in pipeline MLOps - Training Pipeline #20251211.1 
have been running for 4+ hours. Please review job progress.

View Pipeline: https://dev.azure.com/.../_build/results?buildId=12345
Azure ML Studio: https://ml.azure.com/runs?wsid=/subscriptions/...
Branch: develop
Status: In Progress
```

### Future Enhancement: Rich Cards

For a more visually appealing message with buttons, you can modify the body to use Microsoft Teams card format:

```powershell
$body = @{
  "@type" = "MessageCard"
  "@context" = "https://schema.org/extensions"
  "summary" = "Long-Running Training Jobs"
  "themeColor" = "FF9800"
  "title" = "⏳ Long-Running Training Jobs Alert"
  "sections" = @(
    @{
      "activityTitle" = "Pipeline: $(Build.DefinitionName)"
      "activitySubtitle" = "Build #$(Build.BuildNumber)"
      "facts" = @(
        @{ "name" = "Status"; "value" = "In Progress (4+ hours)" }
        @{ "name" = "Branch"; "value" = "$(Build.SourceBranchName)" }
        @{ "name" = "Triggered by"; "value" = "$(Build.RequestedFor)" }
      )
      "text" = "Training jobs have been running for more than 4 hours. Please review progress in Azure ML Studio."
    }
  )
  "potentialAction" = @(
    @{
      "@type" = "OpenUri"
      "name" = "View Pipeline"
      "targets" = @(@{ "os" = "default"; "uri" = $buildUrl })
    },
    @{
      "@type" = "OpenUri"
      "name" = "Azure ML Studio"
      "targets" = @(@{ "os" = "default"; "uri" = $studioUrl })
    }
  )
} | ConvertTo-Json -Depth 10
```

---

## Configuration Options

### Notification Interval

Adjust how often notifications are sent:

```yaml
variables:
  - name: longRunningJobNotificationIntervalHours
    value: '4'  # Options: 2, 3, 4, 6, 8 hours
```

**Recommended values:**
- `2` - For shorter training jobs or critical monitoring
- `4` - Default, good balance (recommended)
- `6` - For jobs that normally take 4-8 hours
- `8` - Minimal notifications, only for very long jobs

### Notification Recipients

**Option 1: Public Channel**
- All team members in channel receive notifications
- Good for: General awareness, team coordination

**Option 2: Private Channel**
- Only specific team members see notifications
- Good for: ML Ops team, on-call engineers

**Option 3: Direct Messages (Advanced)**
- Modify Power Automate flow to send DMs
- Good for: Individual notification preferences

---

## Troubleshooting

### Issue: No notification received

**Check:**
1. Is `TeamsWebhookURL` variable set in Azure DevOps?
2. Is the variable marked as "Secret"?
3. Did the pipeline run for 4+ hours (or your configured interval)?
4. Check pipeline logs for "Teams notification sent successfully"

**Debug:**
```yaml
# Add debug logging
script: |
  $webhook = "$(TeamsWebhookURL)"
  Write-Host "Webhook configured: $($webhook.Length -gt 0)"
  Write-Host "First 20 chars: $($webhook.Substring(0, [Math]::Min(20, $webhook.Length)))..."
```

### Issue: "Failed to send Teams notification"

**Common causes:**
- Webhook URL expired or was deleted
- Network/firewall blocking requests
- Malformed JSON in request body

**Solution:**
1. Test webhook manually (use PowerShell test script above)
2. Regenerate webhook in Teams/Power Automate
3. Update `TeamsWebhookURL` variable in Azure DevOps

### Issue: Notification sent but message is empty

**Cause:** Power Automate flow not configured correctly

**Solution:**
- Verify flow action uses `@{triggerBody()}` or specific fields
- Test the flow in Power Automate with sample data
- Check flow run history for errors

### Issue: Too many notifications

**Solution:**
- Increase `longRunningJobNotificationIntervalHours` value
- Add condition to only notify during business hours:
  ```powershell
  $hour = (Get-Date).Hour
  if ($hour -lt 8 -or $hour -gt 18) {
    Write-Host "Outside business hours - skipping notification"
    exit 0
  }
  ```

---

## Security Considerations

### Webhook URL Security

✅ **Do:**
- Mark `TeamsWebhookURL` as secret in Azure DevOps
- Regenerate webhook periodically (every 6-12 months)
- Use restricted Teams channels for sensitive information
- Document who has access to the webhook

❌ **Don't:**
- Commit webhook URL to git repository
- Share webhook URL via email or chat
- Use the same webhook for multiple pipelines
- Leave webhooks active when not needed

### Access Control

**Teams Channel Access:**
- Use private channels for production notifications
- Restrict channel membership to ML Ops team
- Review channel members periodically

**Pipeline Variables:**
- Only pipeline administrators can edit variables
- Secret variables are encrypted at rest
- Variables are masked in logs

---

## Maintenance

### Regular Tasks

**Monthly:**
- Verify notifications are being received
- Review notification frequency (adjust interval if needed)
- Check Teams channel membership

**Quarterly:**
- Test webhook functionality
- Review and update notification message format
- Verify links in notifications are correct

**Annually:**
- Regenerate webhook URL for security
- Review who has access to Teams channel
- Assess if notifications are still useful

### Webhook Rotation

To rotate the webhook URL:

1. Create new webhook in Teams (Step 1 above)
2. Update `TeamsWebhookURL` in Azure DevOps
3. Test with a pipeline run
4. Delete old webhook in Teams
5. Document the change

---

## Cost Analysis

**Setup Cost:** Free
- Teams: Included in Microsoft 365
- Power Automate: Free tier sufficient (2,500 runs/month)
- Azure DevOps: No additional cost

**Ongoing Cost:** Free
- No per-notification charges
- No API limits for webhook calls
- No additional licensing required

**Time Investment:**
- Initial setup: 10 minutes
- Maintenance: 5 minutes/month
- Total annual: ~1 hour

---

## Alternative Notification Methods

If Teams notifications don't work for your organization, consider:

### 1. Email Notifications
- Use Azure DevOps built-in email notifications
- Configure in Project Settings → Notifications
- Free, but less flexible

### 2. Slack Integration
- Similar to Teams workflow
- Use Slack incoming webhooks
- Replace Teams webhook URL with Slack webhook URL

### 3. Azure Monitor Alerts
- Create alert rules for pipeline duration
- Send notifications via email, SMS, or webhook
- More complex setup but enterprise-grade

### 4. PagerDuty/OpsGenie
- For on-call escalation scenarios
- Integrate via webhooks
- Requires paid subscription

---

## Summary

**Current Status:**
- ✅ Logging-based monitoring: **Active and working**
- ⏸️ Teams notifications: **Ready to enable (optional)**

**To Enable Teams Notifications:**
1. Create Teams webhook (5 min)
2. Add variable to Azure DevOps (2 min)
3. Uncomment pipeline task (3 min)
4. Test and verify (1 min)

**Total Time:** 10 minutes

**Decision Point:**
- If team wants push notifications → Enable now
- If logging is sufficient → Enable later when needed
- No pressure to enable immediately

The pipeline works perfectly without Teams notifications. They're purely a "nice-to-have" feature for proactive alerting.
