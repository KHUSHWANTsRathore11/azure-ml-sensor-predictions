# Hyperparameter Tuning Pipeline Component

## Overview

This component enables data scientists to run hyperparameter tuning experiments on individual sensor circuits. It wraps the existing `train-lstm-model` component in an Azure ML sweep job.

**Important:** This is for exploratory tuning only. Results must be manually applied to `circuits.yaml` and committed via PR to trigger production training.

## Files

- **`component.yaml`** - Pipeline component definition with sweep job configuration
- **`search-space-template.yaml`** - Example hyperparameter search space with recommendations

## Usage

### Quick Start

1. Open the helper notebook:
   ```bash
   jupyter notebook notebooks/hyperparameter_tuning.ipynb
   ```

2. Configure your Azure ML workspace connection

3. Select a circuit to tune (e.g., PLANT001/CIRCUIT01)

4. Submit the tuning job (starts with 10-20 trials)

5. Monitor progress in Azure ML Studio

6. Retrieve best hyperparameters and update `circuits.yaml`

### Programmatic Usage

```python
from azure.ai.ml import MLClient, load_component
from azure.identity import DefaultAzureCredential

# Connect to workspace
ml_client = MLClient(
    DefaultAzureCredential(),
    subscription_id="...",
    resource_group_name="...",
    workspace_name="dev-ml-workspace"
)

# Load component
tuning_component = load_component(
    source="components/hyperparameter-tuning-pipeline/component.yaml"
)

# Submit job
job = tuning_component(
    circuit_config="config/circuits/PLANT001_CIRCUIT01.yaml",
    training_data="azureml:sensor_training_data_PLANT001_CIRCUIT01:1",
    max_trials=20,
    sampling_algorithm="random"
)

submitted_job = ml_client.jobs.create_or_update(job)
print(f"View in Studio: {submitted_job.studio_url}")
```

## Search Space Configuration

The default search space is defined in `component.yaml`:

```yaml
search_space:
  hyperparameters:
    lstm_units:
      type: choice
      values: [32, 64, 128, 256]
    learning_rate:
      type: loguniform
      min_value: 0.0001
      max_value: 0.01
    epochs:
      type: choice
      values: [30, 50, 100]
    batch_size:
      type: choice
      values: [16, 32, 64]
```

To customize the search space, edit `component.yaml` and update the version number.

## Sampling Algorithms

### Random Sampling (Default)
- Good for initial exploration
- Parallelizes well (runs multiple trials concurrently)
- Recommended for first experiments

### Bayesian Sampling
- Better convergence with fewer trials
- Sequential (learns from previous trials)
- Use when you have a good understanding of the search space

## Early Termination

The component uses a **Bandit policy** to stop poor-performing trials early:

```yaml
early_termination:
  type: bandit
  evaluation_interval: 5
  slack_factor: 0.1
  delay_evaluation: 10
```

This saves compute time by terminating trials that are unlikely to outperform the best trial.

## Workflow

```
1. Data Scientist runs tuning experiment
   ↓
2. Sweep job runs 10-20 trials
   ↓
3. Best hyperparameters identified
   ↓
4. Data Scientist updates circuits.yaml
   ↓
5. Create PR with changes
   ↓
6. PR triggers production training pipeline
   ↓
7. Model deployed via Release Pipeline
```

## Best Practices

### Starting Small
- Begin with 5-10 trials to test the setup
- Use fewer epochs (30-50) for faster tuning
- Tune 5-10 representative circuits, then apply learnings to all

### Cost Optimization
- Limit `max_trials` to 10-20 for initial experiments
- Set `max_concurrent_trials: 3` to avoid resource exhaustion
- Use early termination to stop poor trials

### Search Space Design
- Start with 2-3 values per parameter
- Use `choice` for discrete values
- Use `loguniform` for learning rates (better distribution)
- Expand search space based on initial results

### Applying Results
1. Run tuning on representative circuits
2. Identify common optimal ranges
3. Update default hyperparameters in `circuits.yaml`
4. Selectively tune underperforming circuits

## Helper Functions

The `scripts/hyperparameter_helper.py` module provides utility functions:

```python
from scripts.hyperparameter_helper import (
    submit_tuning_job,           # Submit tuning job
    get_best_trial_results,      # Get best hyperparameters
    generate_circuits_yaml_snippet,  # Generate config snippet
    compare_tuning_runs          # Compare multiple runs
)
```

## Troubleshooting

### Job Fails Immediately
- Check that training data asset exists and is accessible
- Verify circuit config path is correct
- Ensure compute cluster is available

### All Trials Fail
- Check training component logs for errors
- Verify hyperparameter ranges are valid
- Test with a single training run first

### No Improvement Over Baseline
- Expand search space
- Increase `max_trials`
- Try Bayesian sampling
- Check if data quality is the limiting factor

## Version History

| Version | Changes |
|---------|---------|
| 1.0.0   | Initial release with random/Bayesian sampling |

## Related Documentation

- [Training Pipeline Component](../training-pipeline-component.yaml)
- [Train LSTM Model Component](../train-lstm-model/component.yaml)
- [Helper Notebook](../../notebooks/hyperparameter_tuning.ipynb)
- [Helper Script](../../scripts/hyperparameter_helper.py)
