# Azure DevOps Native Notifications Guide

## Overview

Azure DevOps provides built-in notification capabilities that require **zero code changes** to the pipeline. This guide shows how to set up notifications for long-running training jobs using native features.

---

## 🎯 Option 1: Project-Level Notifications (Easiest)

### Complexity: ⭐ Very Simple (5 minutes setup)
### Requires: Organization admin or project admin permissions

### Setup Steps

#### 1. Navigate to Project Settings
```
Project → Settings (gear icon) → Notifications
```

#### 2. Create Custom Subscription

Click **"+ New subscription"** and select **"Build"**

#### 3. Configure Notification Rule

**Notification Settings:**
```yaml
Name: "Long-Running Training Jobs Alert"
Description: "Alert ML engineers when training jobs run longer than expected"

Delivery:
  - Email to: ml-engineers@company.com, ml-ops-team@company.com
  - OR Team: ML Engineering Team

Trigger:
  Event: "A build completes"
  
Filters:
  Build pipeline: "MLOps - Training Pipeline"
  Build status: "In Progress" (running)
  
Custom Conditions:
  Duration: Greater than 4 hours
```

**Configuration Example:**

| Field | Value |
|-------|-------|
| **Event** | A build is queued |
| **Pipeline** | MLOps - Training Pipeline |
| **Status** | In Progress |
| **Run time** | Greater than 4 hours |

**Email Template:**
Azure DevOps will send emails like:

```
Subject: [MLOps - Training Pipeline] Build in progress for 4+ hours

Build: #20251211.1
Status: In Progress
Duration: 4 hours 15 minutes
Requested by: john.doe@company.com

The build has been running for over 4 hours.

View build: https://dev.azure.com/org/project/_build/results?buildId=12345
```

### Limitations
- ⚠️ Cannot trigger at multiple intervals (only once per run)
- ⚠️ Cannot include job-specific details (circuit names)
- ⚠️ Applies to entire pipeline, not individual stages

---

## 🎯 Option 2: Personal Notifications (Individual Setup)

### Complexity: ⭐ Very Simple (2 minutes per user)
### Requires: Individual user account

### Setup Steps

#### 1. User Notification Settings
```
User Icon (top right) → User settings → Notifications
```

#### 2. Subscribe to Build Events

Navigate to **"Build" → "A build I'm associated with completes"**

#### 3. Configure Filters

```yaml
Filters:
  - Build pipeline: MLOps - Training Pipeline
  - Build status: Any (to get all updates)
  - Build reason: Continuous Integration
```

#### 4. Optional: Customize Delivery

```yaml
Delivery:
  - Email (default)
  - Optional: Mobile notifications (Azure DevOps mobile app)
```

### Use Cases
- Individual ML engineers tracking their own work
- Quick setup for temporary monitoring
- Personal preferences for notification style

---

## 🎯 Option 3: Service Hooks (Most Flexible)

### Complexity: ⭐⭐ Moderate (15-30 minutes setup)
### Requires: Project admin permissions

Service hooks allow integration with external services like Teams, Slack, or custom webhooks.

### Setup for Microsoft Teams

#### 1. Create Teams Incoming Webhook

In Microsoft Teams:
```
Channel → More options (•••) → Connectors
→ Search "Incoming Webhook" → Configure
→ Name: "Azure DevOps - Training Pipeline"
→ Copy webhook URL
```

#### 2. Configure Azure DevOps Service Hook

```
Project Settings → Service hooks → + Create subscription
→ Service: "Web Hooks"
```

**Configuration:**
```yaml
Trigger:
  Event: "Build completed"
  
Filters:
  Build pipeline: MLOps - Training Pipeline
  Build status: Any
  
Action:
  URL: <Teams webhook URL>
  HTTP headers:
    Content-Type: application/json
  
Message:
  {
    "text": "Build $(Build.BuildNumber) completed with status $(Build.Status) after $(Build.Duration)"
  }
```

#### 3. Advanced: Long-Running Job Detection

**Challenge:** Azure DevOps service hooks don't support time-based triggers during build execution.

**Workaround:** Use pipeline task to send Teams notification:

```yaml
- task: PowerShell@2
  displayName: 'Send Teams Notification'
  condition: always()
  inputs:
    targetType: 'inline'
    script: |
      $teamsWebhook = "$(TeamsWebhookURL)"
      
      $body = @{
        "@type" = "MessageCard"
        "@context" = "https://schema.org/extensions"
        "summary" = "Training Pipeline Update"
        "themeColor" = "FF9800"
        "title" = "⏳ Training Jobs In Progress"
        "sections" = @(
          @{
            "activityTitle" = "Pipeline: $(Build.DefinitionName)"
            "activitySubtitle" = "Build: $(Build.BuildNumber)"
            "facts" = @(
              @{ "name" = "Status"; "value" = "Running" }
              @{ "name" = "Branch"; "value" = "$(Build.SourceBranchName)" }
              @{ "name" = "Started"; "value" = "$(System.JobStartedAt)" }
            )
          }
        )
        "potentialAction" = @(
          @{
            "@type" = "OpenUri"
            "name" = "View Pipeline"
            "targets" = @(
              @{ "os" = "default"; "uri" = "$(System.TeamFoundationCollectionUri)$(System.TeamProject)/_build/results?buildId=$(Build.BuildId)" }
            )
          }
        )
      }
      
      $json = $body | ConvertTo-Json -Depth 10
      Invoke-RestMethod -Method Post -Uri $teamsWebhook -Body $json -ContentType "application/json"
```

**Where to add this task:**
```yaml
- job: WaitForTrainingJobs
  steps:
    # ... existing steps ...
    
    # Add notification every 4 hours
    - task: PowerShell@2
      displayName: 'Send 4-Hour Progress Update'
      condition: and(succeeded(), eq(variables['SendProgressUpdate'], 'true'))
      # ... configuration above ...
```

### Complexity: ⭐⭐⭐ (Requires pipeline modification)

---

## 🎯 Option 4: Email Task (Built-in)

### Complexity: ⭐⭐ Moderate
### Requires: SMTP configuration or SendGrid

Azure DevOps supports direct email sending via tasks, but requires SMTP setup.

### Using SendGrid Email Task

#### 1. Install Extension
```
Organization Settings → Extensions → Browse Marketplace
→ Search "SendGrid Email" → Install
```

#### 2. Configure SendGrid Connection
```
Project Settings → Service connections
→ New service connection → SendGrid
→ API Key: <your-sendgrid-api-key>
```

#### 3. Add Email Task to Pipeline

```yaml
- task: SendGrid@1
  displayName: 'Send Long-Running Job Alert'
  condition: eq(variables['LongRunningJobDetected'], 'true')
  inputs:
    sendGridConnection: 'SendGrid-Connection'
    from: 'azuredevops@company.com'
    to: '$(mlEngineersEmail)'
    subject: '[ALERT] Training Jobs Running for 4+ Hours'
    emailBodyFormat: 'html'
    emailBody: |
      <h2>⏳ Long-Running Training Jobs Detected</h2>
      
      <p><strong>Pipeline:</strong> $(Build.DefinitionName)</p>
      <p><strong>Build:</strong> $(Build.BuildNumber)</p>
      <p><strong>Status:</strong> In Progress (4+ hours)</p>
      <p><strong>Started:</strong> $(System.JobStartedAt)</p>
      
      <p>Training jobs have been running for more than 4 hours. Please review job progress in Azure ML Studio.</p>
      
      <p><a href="$(System.TeamFoundationCollectionUri)$(System.TeamProject)/_build/results?buildId=$(Build.BuildId)">View Pipeline</a></p>
      
      <hr>
      <p style="color: gray; font-size: 12px;">
        Jobs running:<br>
        $(LongRunningJobs)
      </p>
```

**Set Variable in Python Script:**
```python
# In WaitForTrainingJobs monitoring loop
if time_since_notification >= NOTIFICATION_INTERVAL:
    # Set pipeline variable
    long_running_jobs_list = "\n".join([f"- {job}" for job in pending])
    print(f"##vso[task.setvariable variable=LongRunningJobDetected]true")
    print(f"##vso[task.setvariable variable=LongRunningJobs]{long_running_jobs_list}")
```

### Complexity: ⭐⭐⭐ (Requires extension + configuration)

---

## 🎯 Option 5: Logic Apps Integration (Enterprise)

### Complexity: ⭐⭐⭐⭐ Advanced
### Requires: Azure subscription with Logic Apps

For sophisticated scenarios, use Azure Logic Apps triggered by Azure DevOps events.

### Architecture
```
Azure DevOps Pipeline
  → Service Hook (HTTP POST)
    → Azure Logic App
      → Condition: Check duration > 4 hours
        → Send Email / Teams / Slack / SMS
        → Create Azure Monitor Alert
        → Update Tracking Database
```

### Benefits
- Complex routing logic
- Multiple notification channels
- Escalation workflows
- Integration with monitoring systems

### Setup (High-Level)
1. Create Logic App in Azure Portal
2. Add HTTP trigger
3. Add condition blocks (duration check)
4. Add notification actions (Email, Teams, etc.)
5. Configure Azure DevOps service hook to Logic App URL

**Not recommended for simple use cases** - overkill for just time-based notifications.

---

## 📊 Comparison Matrix

| Option | Complexity | Setup Time | Code Changes | Flexibility | Cost | Best For |
|--------|-----------|------------|--------------|-------------|------|----------|
| **1. Project Notifications** | ⭐ | 5 min | None | Low | Free | Simple alerts, entire team |
| **2. Personal Notifications** | ⭐ | 2 min | None | Low | Free | Individual tracking |
| **3. Service Hooks (Teams)** | ⭐⭐ | 15 min | Minimal | Medium | Free | Team collaboration |
| **4. Email Task** | ⭐⭐⭐ | 30 min | Medium | High | $$ | Custom emails |
| **5. Logic Apps** | ⭐⭐⭐⭐ | 2 hours | None | Very High | $$$ | Enterprise workflows |

---

## 🎯 Recommended Approach: Hybrid Solution

### For Your Use Case (Training Monitoring):

**Tier 1: Built-in Logging (Already Implemented)** ✅
- Log alerts every 4 hours in pipeline output
- Azure DevOps warnings visible in UI
- **No additional setup needed**
- **Cost:** Free
- **Effort:** Already done

**Tier 2: Teams Notification (Recommended)**
```yaml
# Add this task after the monitoring loop
- task: PowerShell@2
  displayName: 'Send Teams Notification for Long-Running Jobs'
  condition: eq(variables['LongRunningJobsDetected'], 'true')
  inputs:
    targetType: 'inline'
    script: |
      # Read long-running jobs from variable
      $jobs = "$(LongRunningJobsList)"
      
      $body = @{
        "@type" = "MessageCard"
        "summary" = "Training Jobs Running 4+ Hours"
        "themeColor" = "FF9800"
        "title" = "⏳ Long-Running Training Jobs"
        "text" = "The following training jobs have been running for over 4 hours:`n`n$jobs"
        "potentialAction" = @(
          @{
            "@type" = "OpenUri"
            "name" = "View Pipeline"
            "targets" = @(@{ "uri" = "$(System.CollectionUri)$(System.TeamProject)/_build/results?buildId=$(Build.BuildId)" })
          }
        )
      }
      
      Invoke-RestMethod -Method Post -Uri "$(TeamsWebhookURL)" -Body ($body | ConvertTo-Json -Depth 10) -ContentType "application/json"
```

**Where to set variables in Python:**
```python
# In the long-running job detection block
if time_since_notification >= NOTIFICATION_INTERVAL:
    print(f"##vso[task.setvariable variable=LongRunningJobsDetected;isOutput=true]true")
    jobs_list = "\n".join([f"• {job_name} ({elapsed_hours:.1f}h)" for job_name in pending])
    print(f"##vso[task.setvariable variable=LongRunningJobsList;isOutput=true]{jobs_list}")
```

**Setup Required:**
1. Create Teams incoming webhook (2 minutes)
2. Add webhook URL as pipeline variable `TeamsWebhookURL` (1 minute)
3. Add PowerShell task to pipeline (5 minutes)

**Total Setup Time:** ~10 minutes
**Complexity:** ⭐⭐ (Low-Medium)
**Cost:** Free

---

## 🚀 Quick Start: Minimal Implementation

### Step 1: Create Teams Webhook (2 minutes)

1. Open Microsoft Teams
2. Go to the channel: `#ml-ops` or `#ml-engineering`
3. Click `•••` → Connectors → Configure "Incoming Webhook"
4. Name: "Training Pipeline Alerts"
5. Copy webhook URL

### Step 2: Add Pipeline Variable (1 minute)

In Azure DevOps:
```
Pipeline → Edit → Variables → + Add
Name: TeamsWebhookURL
Value: <paste webhook URL>
Secret: ✓ (check this box)
```

### Step 3: Update Python Script (5 minutes)

Add to the monitoring loop:
```python
# After notification logging
if time_since_notification >= NOTIFICATION_INTERVAL:
    # ... existing logging ...
    
    # Set variable for Teams notification
    jobs_list = "\\n".join([f"• {job} ({(datetime.now() - job_start_time[job]).total_seconds()/3600:.1f}h)" 
                            for job in pending])
    print(f"##vso[task.setvariable variable=LongRunningJobsDetected;isOutput=true]true")
    print(f"##vso[task.setvariable variable=LongRunningJobsList;isOutput=true]{jobs_list}")
```

### Step 4: Add Teams Notification Task

```yaml
- job: WaitForTrainingJobs
  # ... existing configuration ...
  steps:
    # ... existing steps ...
    
    - task: AzureCLI@2
      displayName: 'Wait for All Training Jobs'
      name: monitorJobs  # Add this name
      # ... existing monitoring script ...
    
    # Add new task for Teams notification
    - task: PowerShell@2
      displayName: 'Send Teams Alert'
      condition: eq(variables['monitorJobs.LongRunningJobsDetected'], 'true')
      inputs:
        targetType: 'inline'
        script: |
          $webhook = "$(TeamsWebhookURL)"
          if (-not $webhook) {
            Write-Host "⚠️  TeamsWebhookURL not configured, skipping notification"
            exit 0
          }
          
          $jobs = "$(monitorJobs.LongRunningJobsList)"
          
          $body = @{
            "@type" = "MessageCard"
            "summary" = "Training Jobs Alert"
            "themeColor" = "FF9800"
            "title" = "⏳ Long-Running Training Jobs"
            "text" = "Jobs running 4+ hours:`n`n$jobs"
          } | ConvertTo-Json -Depth 10
          
          Invoke-RestMethod -Method Post -Uri $webhook -Body $body -ContentType "application/json"
```

**Done!** Now you'll get Teams notifications when jobs run > 4 hours.

---

## Summary

**Easiest Solution (Zero Code):**
- Use **Project Notifications** for basic alerts
- Setup: 5 minutes
- Limitation: Only one alert per build

**Best Solution (Minimal Code):**
- Use **Teams Webhook + Pipeline Task**
- Setup: 10 minutes
- Provides: Multiple alerts, job-specific details, team visibility
- **This is what I recommend for your use case**

**Most Flexible (Advanced):**
- Use **Logic Apps** for complex routing
- Setup: 2+ hours
- Only needed for enterprise scenarios with multiple escalation paths

For monitoring long-running training jobs, the **Teams webhook approach** is the sweet spot: simple enough to implement quickly, powerful enough to provide useful notifications, and free.
