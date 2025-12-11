# Azure ML Sensor Predictions - MLOps Project

Production-ready Azure Machine Learning MLOps architecture for time series forecasting.

## Project Structure

```
.
├── config/                          # Configuration files
│   ├── circuits.yaml               # Circuit definitions (75-200 models)
│   └── environment.yaml            # Conda environment specification
│
├── scripts/                         # Python scripts
│   ├── register_mltable.py        # Register MLTable Data Assets
│   ├── detect_config_changes.py   # Detect changed circuits via git diff
│   ├── train_model.py             # Train individual model
│   ├── deploy_batch_endpoints.sh  # Deploy batch endpoints
│   └── deploy_circuits_for_plant.py # Deploy circuits to endpoints
│
├── scoring/                         # Batch scoring
│   └── score.py                   # Scoring script for batch endpoints
│
├── monitoring/                      # Monitoring scripts
│   ├── setup_all_monitors.py      # Setup Azure ML v2 monitors
│   └── custom_drift_detection.py  # Custom drift detector
│
├── pipelines/                       # Azure DevOps pipelines
│   ├── build-pipeline.yml         # PR-based training pipeline
│   ├── release-pipeline.yml       # 3-stage deployment pipeline
│   └── environment-only-pipeline.yml # Environment update pipeline
│
├── tests/                           # Unit tests
│   ├── test_training.py           # Training tests
│   └── test_drift_detection.py    # Drift detection tests
│
├── notebooks/                       # Jupyter notebooks
│   └── (interactive analysis)
│
├── docs/                            # Documentation (16 documents)
│   ├── 01-high-level-architecture.md
│   ├── 02-data-architecture.md
│   ├── 03-multi-model-strategy.md
│   └── ... (13 more)
│
└── requirements.txt                 # Python dependencies
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Circuits

Edit `config/circuits.yaml` to define your sensor circuits:

```yaml
circuits:
  - plant_id: "PLANT001"
    circuit_id: "CIRCUIT01"
    model_name: "plant001-circuit01"
    features: [temperature, pressure, vibration]
    cutoff_date: "2025-11-01"
    hyperparameters:
      lstm_units: 64
      learning_rate: 0.001
```

### 3. Register Data

```bash
python scripts/register_mltable.py \
  --subscription-id <sub-id> \
  --resource-group rg-mlops-dev \
  --workspace mlw-dev \
  --version 2025-12-09 \
  --path azureml://datastores/workspaceblobstore/paths/mltable/
```

### 4. Train Model

```bash
python scripts/train_model.py \
  --plant-id PLANT001 \
  --circuit-id CIRCUIT01 \
  --config-path config/circuits.yaml \
  --data-path <mltable-path>
```

### 5. Deploy to Batch Endpoint

```bash
./scripts/deploy_batch_endpoints.sh mlw-dev rg-mlops-dev
```

## CI/CD Pipelines

### Build Pipeline (PR-Based Training)
- Triggered by changes to `config/circuits.yaml`
- Detects changed circuits using git diff
- Trains models in parallel (maxParallel=5)
- Registers models to Dev workspace

### Release Pipeline (3-Stage Deployment)
- **Stage 1:** Promote to Registry (manual approval)
- **Stage 2:** Deploy to Test (automated)
- **Stage 3:** Deploy to Production (manual approval)

### Environment-Only Pipeline
- For non-breaking environment changes
- Tests all 75-200 models
- Updates all deployments at once

## Monitoring

### Setup Model Monitors

```bash
python monitoring/setup_all_monitors.py \
  --subscription-id <sub-id> \
  --resource-group rg-mlops-prod \
  --workspace mlw-prod
```

### Run Drift Detection

```bash
python monitoring/run_drift_detection.py
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=scripts --cov=monitoring --cov-report=html
```

## Documentation

Comprehensive documentation available in `docs/`:

- **Architecture:** System design, data flow, multi-model strategy
- **CI/CD:** Build and release pipelines, rollback procedures
- **Operations:** Monitoring, runbooks, cost estimation
- **Implementation:** 12-week implementation checklist

Start with [README.md](README.md) for navigation.

## Key Features

✅ **Multi-Model Scale:** Support for 75-200 independent models
✅ **PR-Based Training:** Automated training triggered by config changes
✅ **Parallel Execution:** Train multiple models simultaneously
✅ **Multi-Stage Deployment:** Dev → Registry → Test → Production
✅ **Environment Management:** Semantic versioning with breaking/non-breaking workflows
✅ **Data Versioning:** Date-based MLTable versions for reproducibility
✅ **Comprehensive Monitoring:** Azure ML v2 + custom drift detection
✅ **Fast Rollback:** 15-20 minute SLA via Azure DevOps
✅ **Cost Optimized:** ~$1,483/month for full scale

## Azure Resources Required

- 3 Azure ML Workspaces (Dev, Test, Prod)
- 1 Azure ML Registry (Shared)
- Azure Synapse Analytics (ETL)
- ADLS Gen2 Storage (Delta Lake)
- Azure DevOps (CI/CD)
- Azure Monitor + Application Insights

## Cost Estimate

- **Dev Workspace:** ~$400/month
- **Test Workspace:** ~$200/month
- **Prod Workspace:** ~$700/month
- **Shared Resources:** ~$183/month
- **Monitoring:** ~$210/month
- **Total:** ~$1,693/month

See [docs/13-cost-estimation.md](docs/13-cost-estimation.md) for details.

## License

[Your License Here]

## Support

For questions or issues, contact: mlops-team@company.com
