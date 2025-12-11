# Pipeline YAML Reference

[← Back to README](../README.md)

## Overview

This document provides complete YAML definitions for all pipelines in the architecture.

## Table of Contents

1. [Build Pipeline (5 Stages)](#build-pipeline-5-stages)
2. [Release Pipeline (3 Stages)](#release-pipeline-3-stages)
3. [Environment-Only Pipeline (4 Stages)](#environment-only-pipeline-4-stages)
4. [ETL Pipeline (Synapse)](#etl-pipeline-synapse)
5. [Manual Training Pipeline](#manual-training-pipeline)

---

## Build Pipeline (5 Stages)

```yaml
# azure-pipelines-build-training.yml
name: Build-Train-$(Date:yyyyMMdd)$(Rev:.r)

trigger:
  branches:
    include:
      - main
  paths:
    include:
      - config/plants/**/*.yml

variables:
  - name: maxParallelTraining
    value: 5
  - name: azuremlWorkspace
    value: 'dev-ml-workspace'
  - name: resourceGroup
    value: 'mlops-rg'
  - name: subscriptionId
    value: '$(AZURE_SUBSCRIPTION_ID)'

stages:
  - stage: DetectChanges
    displayName: 'Stage 1: Detect Changed Circuits'
    jobs:
      - job: GitDiff
        displayName: 'Parse Git Diff'
        steps:
          - checkout: self
            fetchDepth: 2
          
          - task: PythonScript@0
            name: detectChanges
            inputs:
              scriptSource: 'filePath'
              scriptPath: 'scripts/detect_config_changes.py'
              arguments: '--pr-number $(System.PullRequest.PullRequestNumber) --commit-sha $(Build.SourceVersion)'
          
          - script: |
              echo "##vso[task.setvariable variable=changedCircuits;isOutput=true]$(cat changed_circuits.json)"
            name: setChangedCircuits

  - stage: PrepareData
    displayName: 'Stage 2: Register MLTable Data Assets'
    dependsOn: DetectChanges
    variables:
      changedCircuits: $[ stageDependencies.DetectChanges.GitDiff.outputs['setChangedCircuits.changedCircuits'] ]
    jobs:
      - job: RegisterMLTables
        strategy:
          maxParallel: $(maxParallelTraining)
          matrix: $[ variables.changedCircuits ]
        steps:
          - task: AzureCLI@2
            name: registerMLTable
            inputs:
              azureSubscription: 'AzureML-ServiceConnection'
              scriptType: 'bash'
              scriptLocation: 'scriptPath'
              scriptPath: 'scripts/register_mltable.py'
              arguments: >-
                --plant-id "$(plant_id)"
                --circuit-id "$(circuit_id)"
                --cutoff-date "$(cutoff_date)"
                --pr-number "$(System.PullRequest.PullRequestNumber)"
                --pr-author "$(Build.RequestedFor)"
                --git-sha "$(Build.SourceVersion)"
                --workspace-name "$(azuremlWorkspace)"
                --resource-group "$(resourceGroup)"
                --subscription-id "$(subscriptionId)"
          
          - script: |
              echo "##vso[task.setvariable variable=dataAssetVersion_$(plant_id)_$(circuit_id);isOutput=true]$(cat data_asset_version.txt)"
            name: setVersion

  - stage: Build
    displayName: 'Stage 3: Build Environment'
    dependsOn: PrepareData
    jobs:
      - job: BuildEnvironment
        steps:
          - task: PythonScript@0
            name: checkEnvChange
            inputs:
              scriptSource: 'filePath'
              scriptPath: 'scripts/check_env_change.py'
              arguments: '--pr-number $(System.PullRequest.PullRequestNumber)'
          
          - task: AzureCLI@2
            condition: eq(variables['checkEnvChange.env_changed'], 'true')
            name: buildEnv
            inputs:
              azureSubscription: 'AzureML-ServiceConnection'
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                python setup.py sdist bdist_wheel
                
                ENV_VERSION=$(az ml environment create \
                  --file environment/custom_tf_env.yml \
                  --workspace-name "$(azuremlWorkspace)" \
                  --resource-group "$(resourceGroup)" \
                  --set tags.backward_compatible="$(checkEnvChange.backward_compatible)" \
                       tags.requires_retrain="$(checkEnvChange.requires_retrain)" \
                       tags.pr_number="$(System.PullRequest.PullRequestNumber)" \
                  --query version -o tsv)
                
                echo "##vso[task.setvariable variable=envVersion;isOutput=true]$ENV_VERSION"

  - stage: Train
    displayName: 'Stage 4: Train Models in Parallel'
    dependsOn: [PrepareData, Build]
    variables:
      changedCircuits: $[ stageDependencies.DetectChanges.GitDiff.outputs['setChangedCircuits.changedCircuits'] ]
      envVersion: $[ stageDependencies.Build.BuildEnvironment.outputs['buildEnv.envVersion'] ]
    jobs:
      - job: TrainModels
        strategy:
          maxParallel: $(maxParallelTraining)
          matrix: $[ variables.changedCircuits ]
        steps:
          - task: AzureCLI@2
            name: submitJob
            inputs:
              azureSubscription: 'AzureML-ServiceConnection'
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                JOB_NAME=$(az ml job create \
                  --file pipelines/training_pipeline.yml \
                  --set inputs.training_data.path="azureml:sensor_training_data_$(plant_id)_$(circuit_id):$(dataAssetVersion)" \
                       inputs.plant_id="$(plant_id)" \
                       inputs.circuit_id="$(circuit_id)" \
                       environment="azureml:custom-tf-env:$(envVersion)" \
                  --workspace-name "$(azuremlWorkspace)" \
                  --query name -o tsv)
                
                echo "##vso[task.setvariable variable=jobName;isOutput=true]$JOB_NAME"
          
          - task: AzureCLI@2
            name: registerModel
            inputs:
              azureSubscription: 'AzureML-ServiceConnection'
              scriptType: 'bash'
              scriptLocation: 'scriptPath'
              scriptPath: 'scripts/register_model.sh'
              arguments: >-
                --plant-id "$(plant_id)"
                --circuit-id "$(circuit_id)"
                --job-name "$(submitJob.jobName)"

  - stage: PublishArtifact
    displayName: 'Stage 5: Publish Artifacts for Release'
    dependsOn: Train
    jobs:
      - job: CreateArtifacts
        strategy:
          matrix: $[ variables.changedCircuits ]
        steps:
          - script: |
              cat > model_artifact_$(plant_id)_$(circuit_id).json <<EOF
              {
                "plant_id": "$(plant_id)",
                "circuit_id": "$(circuit_id)",
                "model_name": "sensor_model",
                "model_version": "$(registerModel.modelVersion)",
                "environment_version": "$(envVersion)",
                "dev_workspace": "$(azuremlWorkspace)",
                "pr_number": "$(System.PullRequest.PullRequestNumber)",
                "build_id": "$(Build.BuildId)",
                "commit_sha": "$(Build.SourceVersion)",
                "trained_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
              }
              EOF
          
          - task: PublishBuildArtifacts@1
            inputs:
              PathtoPublish: 'model_artifact_$(plant_id)_$(circuit_id).json'
              ArtifactName: 'model-$(plant_id)-$(circuit_id)'
```

---

## Release Pipeline (3 Stages)

```yaml
# azure-release-pipeline.yml
name: Release-$(plant_id)-$(circuit_id)-$(Date:yyyyMMdd)$(Rev:.r)

resources:
  pipelines:
    - pipeline: BuildPipeline
      source: 'Build-Train-Pipeline'
      trigger:
        enabled: true

variables:
  - group: azureml-variables
  - name: azureMLRegistry
    value: 'mlregistry-shared'
  - name: testWorkspace
    value: 'test-ml-workspace'
  - name: prodWorkspace
    value: 'prod-ml-workspace'
  - name: resourceGroup
    value: 'mlops-rg'

stages:
  - stage: PromoteToRegistry
    displayName: 'Stage 1: Promote to Registry'
    
    approvals:
      - approval: manual
        approvers:
          - group: 'ML-Engineers'
        instructions: |
          Review model metrics before promoting.
          
          Plant: $(plant_id)
          Circuit: $(circuit_id)
          Model Version: $(model_version)
        timeoutInMinutes: 1440
    
    jobs:
      - deployment: PromoteModel
        environment: 'azureml-registry'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: DownloadBuildArtifacts@0
                  inputs:
                    artifactName: 'model-$(plant_id)-$(circuit_id)'
                
                - task: AzureCLI@2
                  inputs:
                    azureSubscription: 'AzureML-ServiceConnection'
                    scriptType: 'bash'
                    scriptLocation: 'scriptPath'
                    scriptPath: 'scripts/promote_to_registry.sh'
                    arguments: >-
                      --artifact-file "$(System.ArtifactsDirectory)/model_artifact.json"
                      --registry-name "$(azureMLRegistry)"

  - stage: DeployToTest
    displayName: 'Stage 2: Deploy to Test'
    dependsOn: PromoteToRegistry
    
    jobs:
      - deployment: DeployTest
        environment: 'test-workspace'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureCLI@2
                  inputs:
                    scriptPath: 'scripts/deploy_batch_endpoint.sh'
                    arguments: >-
                      --workspace-name "$(testWorkspace)"
                      --environment "test"
                
                - task: AzureCLI@2
                  name: testInference
                  inputs:
                    inlineScript: |
                      JOB_NAME=$(az ml batch-endpoint invoke \
                        --name "batch-endpoint-plant-$(plant_id)" \
                        --deployment-name "deployment-circuit-$(circuit_id)" \
                        --workspace-name "$(testWorkspace)" \
                        --query name -o tsv)
                      
                      # Wait for completion
                      az ml job stream --name "$JOB_NAME" --workspace-name "$(testWorkspace)"
                      
                      STATUS=$(az ml job show --name "$JOB_NAME" --query status -o tsv)
                      if [ "$STATUS" != "Completed" ]; then
                        exit 1
                      fi

  - stage: DeployToProduction
    displayName: 'Stage 3: Deploy to Production'
    dependsOn: DeployToTest
    
    approvals:
      - approval: manual
        approvers:
          - group: 'ML-Engineers'
        instructions: |
          Test passed. Approve for production deployment.
        timeoutInMinutes: 1440
    
    jobs:
      - deployment: DeployProduction
        environment: 'production-workspace'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureCLI@2
                  inputs:
                    scriptPath: 'scripts/deploy_batch_endpoint.sh'
                    arguments: >-
                      --workspace-name "$(prodWorkspace)"
                      --environment "production"
```

---

## Environment-Only Pipeline (4 Stages)

```yaml
# azure-pipelines-environment-release.yml
name: Environment-Release-$(Date:yyyyMMdd)$(Rev:.r)

trigger: none

variables:
  - group: azureml-variables
  - name: environmentVersion
    value: '1.5.1'

stages:
  - stage: PromoteEnvironment
    displayName: 'Stage 1: Promote Environment to Registry'
    
    approvals:
      - approval: manual
        approvers:
          - group: 'ML-Engineers'
        instructions: |
          Evidence: Interactive notebook showing successful scoring
          Environment Version: $(environmentVersion)
        timeoutInMinutes: 1440
    
    jobs:
      - job: Promote
        steps:
          - task: AzureCLI@2
            inputs:
              inlineScript: |
                az ml environment share \
                  --name "custom-tf-env" \
                  --version "$(environmentVersion)" \
                  --workspace-name "dev-ml-workspace" \
                  --registry-name "mlregistry-shared"

  - stage: TestAllModels
    displayName: 'Stage 2: Integration Test ALL Models'
    dependsOn: PromoteEnvironment
    
    jobs:
      - job: IntegrationTests
        steps:
          - task: PythonScript@0
            name: getAllModels
            inputs:
              scriptPath: 'scripts/get_all_deployments.py'
          
          - task: AzureCLI@2
            inputs:
              inlineScript: |
                cat deployments.json | jq -c '.[]' | while read deployment; do
                  MODEL_NAME=$(echo $deployment | jq -r '.model_name')
                  MODEL_VERSION=$(echo $deployment | jq -r '.model_version')
                  
                  az ml job create \
                    --file pipelines/environment_compatibility_test.yml \
                    --set inputs.model_name="$MODEL_NAME" \
                         inputs.model_version="$MODEL_VERSION" \
                         environment="azureml:custom-tf-env:$(environmentVersion)"
                done

  - stage: UpdateAllDeployments
    displayName: 'Stage 3: Update ALL Deployments'
    dependsOn: TestAllModels
    
    approvals:
      - approval: manual
        approvers:
          - group: 'ML-Engineers'
          - group: 'Engineering-Managers'
        instructions: |
          All tests passed. Update ALL deployments.
        timeoutInMinutes: 1440
    
    jobs:
      - job: UpdateDeployments
        steps:
          - task: AzureCLI@2
            inputs:
              inlineScript: |
                cat deployments.json | jq -c '.[]' | while read deployment; do
                  ENDPOINT_NAME=$(echo $deployment | jq -r '.endpoint_name')
                  DEPLOYMENT_NAME=$(echo $deployment | jq -r '.deployment_name')
                  
                  az ml batch-deployment update \
                    --name "$DEPLOYMENT_NAME" \
                    --endpoint-name "$ENDPOINT_NAME" \
                    --workspace-name "prod-ml-workspace" \
                    --set environment="azureml:custom-tf-env:$(environmentVersion)"
                done

  - stage: MonitorProduction
    displayName: 'Stage 4: Monitor Production'
    dependsOn: UpdateAllDeployments
    
    jobs:
      - job: PostDeployment
        steps:
          - script: |
              echo "Monitor for 24 hours"
              echo "Use rollback pipeline if issues detected"
```

---

## ETL Pipeline (Synapse)

```yaml
# azure-pipelines-etl.yml
name: ETL-$(Date:yyyyMMdd)$(Rev:.r)

schedules:
  - cron: "0 */3 * * *"  # Every 3 hours
    displayName: 'ETL Every 3 Hours'
    branches:
      include:
        - main

stages:
  - stage: RunETL
    jobs:
      - job: SynapseETL
        steps:
          - task: AzureSynapseWorkspace.synapsecicd-deploy.synapse-deploy.Synapse workspace deployment@2
            inputs:
              TemplateFile: 'synapse/notebooks/etl_pipeline.json'
              ParametersFile: 'synapse/parameters.json'
              azureSubscription: 'Synapse-ServiceConnection'
              ResourceGroupName: 'mlops-rg'
              WorkspaceName: 'synapse-workspace'
          
          - task: AzureCLI@2
            displayName: 'Verify Delta Table'
            inputs:
              scriptType: 'bash'
              inlineScript: |
                python -c "
                from deltalake import DeltaTable
                delta = DeltaTable('abfss://container@storage.dfs.core.windows.net/processed/sensor_data/')
                print(f'Version: {delta.version()}')
                print(f'Row count: {len(delta.to_pandas())}')
                "
```

---

## Manual Training Pipeline

```yaml
# azure-pipelines-manual-training.yml
name: ManualTrain-$(Date:yyyyMMdd)$(Rev:.r)

trigger: none

parameters:
  - name: plantId
    displayName: 'Plant ID'
    type: string
  - name: circuitId
    displayName: 'Circuit ID'
    type: string
  - name: cutoffDate
    displayName: 'Cutoff Date (optional)'
    type: string
    default: ''

stages:
  - stage: PrepareData
    jobs:
      - job: RegisterMLTable
        steps:
          - script: |
              if [ -z "${{ parameters.cutoffDate }}" ]; then
                CUTOFF_DATE=$(python scripts/read_config.py \
                  --plant-id "${{ parameters.plantId }}" \
                  --circuit-id "${{ parameters.circuitId }}" \
                  --field cutoff_date)
              else
                CUTOFF_DATE="${{ parameters.cutoffDate }}"
              fi
              echo "##vso[task.setvariable variable=cutoffDate;isOutput=true]$CUTOFF_DATE"
            name: setCutoffDate
          
          - task: AzureCLI@2
            name: registerMLTable
            inputs:
              scriptPath: 'scripts/register_mltable.py'
              arguments: >-
                --plant-id "${{ parameters.plantId }}"
                --circuit-id "${{ parameters.circuitId }}"
                --cutoff-date "$(cutoffDate)"
                --pr-number "MANUAL"

  - stage: Train
    dependsOn: PrepareData
    jobs:
      - job: TrainModel
        steps:
          - task: AzureCLI@2
            inputs:
              inlineScript: |
                az ml job create \
                  --file pipelines/training_pipeline.yml \
                  --set inputs.training_data.path="azureml:sensor_training_data_${{ parameters.plantId }}_${{ parameters.circuitId }}:$(dataAssetVersion)" \
                       inputs.plant_id="${{ parameters.plantId }}" \
                       inputs.circuit_id="${{ parameters.circuitId }}"
```

---

## Related Documents

- [05-build-pipeline.md](05-build-pipeline.md) - Build pipeline details
- [06-release-pipeline.md](06-release-pipeline.md) - Release pipeline details
- [07-environment-only-pipeline.md](07-environment-only-pipeline.md) - Environment pipeline details
- [09-scripts-reference.md](09-scripts-reference.md) - Python/shell scripts

---

**Document Version:** 1.0  
**Last Updated:** December 9, 2025
