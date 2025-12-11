# AzureML Job Wait Configuration

## Overview

The pipeline uses the **AzureML Job Wait** extension to efficiently wait for training jobs without consuming expensive agent resources.

**Key Benefits:**
- ✅ **No agent cost**: Runs on `pool: server` (no compute charges)
- ✅ **Efficient**: Azure ML calls back when job completes
- ✅ **Status propagation**: Job status automatically reflects in pipeline
- ✅ **Long-running support**: Can wait up to 48 hours (Azure DevOps limit)

## Prerequisites

### 1. Install AzureML Extension

Install the extension in your Azure DevOps organization:

**Extension URL:** https://marketplace.visualstudio.com/items?itemName=ms-air-aiagility.azureml-v2

1. Navigate to Azure DevOps → Organization Settings → Extensions
2. Search for "Azure Machine Learning"
3. Click "Install" on the extension by **Microsoft Devlabs**

### 2. Service Connection

Ensure you have an Azure Resource Manager service connection configured with access to your Azure ML workspace.

The pipeline uses: `$(azureServiceConnection)`

## Configuration

### Current Implementation

The `WaitForTraining` job in Stage 2 is a **placeholder** that needs manual configuration.

**Location:** `.azuredevops/build-pipeline.yml` → Stage 2 → Job: `WaitForTraining`

### Task Syntax

The AzureML Job Wait task syntax:

```yaml
- task: AzureMLJobWait@1
  displayName: 'Wait for {job_name}'
  inputs:
    connectedServiceName: '$(azureServiceConnection)'
    resourceGroupName: '$(resourceGroup)'
    workspaceName: '$(workspaceName)'
    jobName: 'PLANT001_CIRCUIT01_2025_11_01'  # Specific job name
```

### Handling Multiple Jobs

Since the extension **only supports one job per task**, use one of these approaches:

---

#### **Option 1: Matrix Strategy (Static Jobs)**

Use if circuit list is known at design time.

```yaml
- job: WaitForTraining
  displayName: 'Wait for Training Jobs'
  dependsOn: ParallelTraining
  pool: server
  timeoutInMinutes: 2880
  strategy:
    matrix:
      Plant001_Circuit01:
        jobName: 'PLANT001_CIRCUIT01_2025_11_01'
      Plant001_Circuit02:
        jobName: 'PLANT001_CIRCUIT02_2025_11_01'
      Plant002_Circuit01:
        jobName: 'PLANT002_CIRCUIT01_2025_11_01'
  steps:
    - task: AzureMLJobWait@1
      displayName: 'Wait for $(jobName)'
      inputs:
        connectedServiceName: '$(azureServiceConnection)'
        resourceGroupName: '$(resourceGroup)'
        workspaceName: '$(workspaceName)'
        jobName: '$(jobName)'
```

**Pros:** Simple, explicit  
**Cons:** Requires updating pipeline for new circuits

---

#### **Option 2: Dynamic Job List from Artifact**

Use a custom script to read `training_jobs.json` and wait for all jobs.

```yaml
- job: WaitForTraining
  displayName: 'Wait for Training Jobs'
  dependsOn: ParallelTraining
  pool: server
  timeoutInMinutes: 2880
  steps:
    - task: DownloadPipelineArtifact@2
      inputs:
        artifact: 'training_jobs'
        path: $(Pipeline.Workspace)
    
    # Read jobs from artifact and create wait tasks
    - task: PowerShell@2
      displayName: 'Generate Wait Tasks'
      inputs:
        targetType: 'inline'
        script: |
          $jobs = Get-Content "$(Pipeline.Workspace)/training_jobs.json" | ConvertFrom-Json
          foreach ($jobName in $jobs.jobs) {
            Write-Host "##[section]Waiting for job: $jobName"
            # Note: Cannot dynamically create AzureMLJobWait tasks in YAML
            # Must use pre-defined tasks or API
          }
```

**Limitation:** Cannot dynamically create `AzureMLJobWait` tasks in YAML runtime.

---

#### **Option 3: REST API Approach (Recommended for Dynamic)**

Use Azure ML REST API to poll jobs efficiently in a server job.

```yaml
- job: WaitForTraining
  displayName: 'Wait for Training Jobs'
  dependsOn: ParallelTraining
  pool: server
  timeoutInMinutes: 2880
  steps:
    - task: DownloadPipelineArtifact@2
      inputs:
        artifact: 'training_jobs'
        path: $(Pipeline.Workspace)
    
    - task: AzureCLI@2
      displayName: 'Wait for All Jobs via REST API'
      inputs:
        azureSubscription: '$(azureServiceConnection)'
        scriptType: 'bash'
        scriptLocation: 'inlineScript'
        inlineScript: |
          python3 << 'EOF'
          import json
          import time
          import sys
          from azure.identity import DefaultAzureCredential
          from azure.ai.ml import MLClient
          
          # Load job names
          with open('$(Pipeline.Workspace)/training_jobs.json', 'r') as f:
              data = json.load(f)
          
          job_names = data.get('jobs', [])
          
          if not job_names:
              print("No jobs to wait for")
              sys.exit(0)
          
          print(f"Waiting for {len(job_names)} jobs...")
          
          # Initialize ML Client
          credential = DefaultAzureCredential()
          ml_client = MLClient(
              credential=credential,
              subscription_id='$(subscriptionId)',
              resource_group_name='$(resourceGroup)',
              workspace_name='$(workspaceName)'
          )
          
          # Wait for all jobs
          pending = set(job_names)
          failed = []
          
          while pending:
              time.sleep(60)  # Check every minute
              
              for job_name in list(pending):
                  job = ml_client.jobs.get(job_name)
                  
                  if job.status in ['Completed', 'Failed', 'Canceled']:
                      pending.remove(job_name)
                      
                      if job.status == 'Completed':
                          print(f"✅ {job_name}: Completed")
                      else:
                          print(f"❌ {job_name}: {job.status}")
                          failed.append(job_name)
          
          if failed:
              print(f"\n❌ {len(failed)} job(s) failed")
              sys.exit(1)
          
          print(f"\n✅ All {len(job_names)} jobs completed successfully")
          EOF
```

**Pros:** Dynamic, handles any number of jobs  
**Cons:** Uses agent job (not server job), but still more efficient than old approach

---

#### **Option 4: Template-Based Approach (Balanced)**

Create a reusable template for known circuits.

**File: `templates/wait-for-jobs.yml`**
```yaml
parameters:
  - name: jobs
    type: object
    default: []

jobs:
  - ${{ each job in parameters.jobs }}:
    - job: Wait_${{ replace(job.name, '-', '_') }}
      displayName: 'Wait for ${{ job.name }}'
      pool: server
      timeoutInMinutes: 2880
      steps:
        - task: AzureMLJobWait@1
          inputs:
            connectedServiceName: '$(azureServiceConnection)'
            resourceGroupName: '$(resourceGroup)'
            workspaceName: '$(workspaceName)'
            jobName: '${{ job.name }}'
```

**Usage in main pipeline:**
```yaml
- template: templates/wait-for-jobs.yml
  parameters:
    jobs:
      - name: 'PLANT001_CIRCUIT01_2025_11_01'
      - name: 'PLANT001_CIRCUIT02_2025_11_01'
      - name: 'PLANT002_CIRCUIT01_2025_11_01'
```

**Pros:** Reusable, uses server jobs  
**Cons:** Static list, requires pipeline update for new circuits

---

## Recommended Implementation

For **dynamic circuit training** with **minimal agent cost**:

1. **Use Option 3** (REST API) with a **server job pool** if possible
2. Install `azure-ai-ml` in the server job environment
3. This provides the best balance of cost and flexibility

For **static/known circuits**:

1. **Use Option 4** (Template) with AzureML Job Wait tasks
2. Generates one server job per training job
3. Zero agent cost, maximum efficiency

## Current Status

⚠️ **Action Required:** The placeholder in `WaitForTraining` job must be replaced with one of the above options.

**Current Implementation:**
```yaml
- job: WaitForTraining
  pool: server
  steps:
    - task: Bash@3  # Placeholder - exits with error
```

**Next Steps:**
1. Choose implementation option (3 or 4 recommended)
2. Update `.azuredevops/build-pipeline.yml` → Stage 2 → Job: `WaitForTraining`
3. Test with a single circuit first
4. Verify job status propagates correctly

## Resources

- **Extension:** https://marketplace.visualstudio.com/items?itemName=ms-air-aiagility.azureml-v2
- **Documentation:** https://learn.microsoft.com/en-us/azure/machine-learning/how-to-devops-machine-learning
- **Server Jobs:** https://learn.microsoft.com/en-us/azure/devops/pipelines/process/phases?view=azure-devops&tabs=yaml#server-jobs
- **Azure ML Python SDK:** https://learn.microsoft.com/en-us/python/api/overview/azure/ml

## FAQ

**Q: Why not use the old polling approach?**  
A: The old approach used an agent job that polled every 60 seconds. For long-running training (hours), this ties up an expensive agent unnecessarily.

**Q: How much does a server job cost?**  
A: **$0** - Server jobs don't consume pipeline minutes or agent resources.

**Q: Can server jobs run Python scripts?**  
A: Limited. Server jobs can run certain tasks (AzureMLJobWait, Invoke REST API, etc.) but not arbitrary scripts. Use Option 3 with AzureCLI@2 as a workaround.

**Q: What happens if a training job fails?**  
A: The AzureML Job Wait task automatically fails with the same status, and the pipeline stops (unless `continueOnError: true`).

**Q: Can I wait for jobs across different workspaces?**  
A: Yes, but you need separate wait tasks with different service connections/workspace names.
