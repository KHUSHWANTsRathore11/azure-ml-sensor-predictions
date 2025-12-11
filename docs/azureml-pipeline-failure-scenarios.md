# Azure ML Pipeline Failure Scenarios

## Overview

This document catalogs all possible failure points in Azure ML pipelines, their causes, impacts, and mitigation strategies.

---

## 🏗️ Infrastructure & Configuration Failures

### 1. **Compute Cluster Issues**

#### 1.1 Compute Not Found
**Cause:**
- Cluster doesn't exist
- Cluster was deleted
- Wrong cluster name in pipeline YAML
- Cluster in different workspace

**Error Message:**
```
ComputeTargetNotFound: The compute target 'training-cluster' could not be found
```

**Impact:** Pipeline fails to start

**Mitigation:**
```python
# Pre-flight check in RegisterInfrastructure stage
check_cmd = [
    'az', 'ml', 'compute', 'show',
    '--name', cluster_name,
    '--workspace-name', workspace,
    '--resource-group', rg
]
result = subprocess.run(check_cmd, capture_output=True)
if result.returncode != 0:
    print(f"❌ Compute cluster '{cluster_name}' not found")
    sys.exit(1)
```

#### 1.2 Compute Quota Exceeded
**Cause:**
- Azure subscription quota limits reached
- Too many nodes requested
- Regional capacity constraints
- Concurrent pipelines consuming quota

**Error Message:**
```
QuotaExceeded: Operation could not be completed as it results in exceeding approved quota
Requested: 20 cores
Current usage: 95/100 cores
```

**Impact:** Jobs wait indefinitely or fail after timeout

**Detection:**
```python
# Jobs stuck in "Queued" state for > 30 minutes
if job.status == 'Queued' and time_elapsed > 1800:
    print(f"⚠️  Job {job_name} queued for >30min - possible quota issue")
```

**Mitigation:**
- Request quota increase via Azure Portal
- Use auto-scaling clusters with min_nodes=0
- Implement job prioritization
- Spread training across multiple regions

#### 1.3 Compute Provisioning Timeout
**Cause:**
- Azure backend issues
- Network connectivity problems
- Regional outages
- Node allocation failures

**Error Message:**
```
ComputeProvisioningTimeout: Failed to provision compute after 30 minutes
```

**Impact:** Job fails after 30-minute timeout

**Mitigation:**
- Implement automatic retry logic
- Use existing running clusters (min_nodes > 0)
- Monitor Azure Service Health
- Have backup regions configured

#### 1.4 Node Preemption (Low Priority VMs)
**Cause:**
- Using low-priority VMs
- Azure needs capacity for high-priority workloads
- Cost optimization settings

**Error Message:**
```
NodePreempted: Low priority VM was preempted due to capacity constraints
```

**Impact:** Job terminated mid-execution

**Mitigation:**
- Use dedicated VMs for critical workloads
- Enable automatic retry on preemption
- Implement checkpointing in training code
- Set appropriate priority levels

---

## 📦 Data & Asset Failures

### 2. **Data Asset Issues**

#### 2.1 MLTable Not Found
**Cause:**
- MLTable not registered
- Wrong data asset name/version
- Data asset in different workspace
- Typo in asset reference

**Error Message:**
```
DataAssetNotFound: Data asset 'PLANT001_CIRCUIT01:2025-12-11' not found
```

**Impact:** Pipeline fails at job submission

**Mitigation:**
```python
# Verify data asset exists before job submission
check_cmd = [
    'az', 'ml', 'data', 'show',
    '--name', data_name,
    '--version', data_version,
    '--workspace-name', workspace
]
result = subprocess.run(check_cmd, capture_output=True)
if result.returncode != 0:
    print(f"❌ Data asset not found: {data_name}:{data_version}")
    # Attempt to register it or fail gracefully
```

#### 2.2 Datastore Not Accessible
**Cause:**
- Datastore deleted
- Storage account moved/deleted
- Authentication issues
- Network/firewall rules blocking access

**Error Message:**
```
DatastoreNotAccessible: Cannot access datastore 'workspaceblobstore'
StorageAccountNotFound / AuthenticationFailed / NetworkAccessDenied
```

**Impact:** Pipeline cannot read/write data

**Mitigation:**
- Use managed identity authentication
- Verify datastore connectivity in pre-flight checks
- Monitor storage account health
- Implement retry logic with exponential backoff

#### 2.3 Data Path Not Found
**Cause:**
- Blob storage path doesn't exist
- MLTable YAML references wrong path
- Data deleted from storage
- Incorrect path format

**Error Message:**
```
PathNotFound: Path 'azureml://datastores/workspaceblobstore/paths/mltable/PLANT001_CIRCUIT01/' not found
```

**Impact:** Job fails when trying to read data

**Mitigation:**
```python
# Verify blob exists before registration
from azure.storage.blob import BlobServiceClient

blob_path = f"mltable/{plant_id}_{circuit_id}/MLTable"
if not blob_client.exists():
    print(f"❌ MLTable file not found at {blob_path}")
    print("   Ensure ETL pipeline has completed successfully")
    sys.exit(1)
```

#### 2.4 Data Format/Schema Mismatch
**Cause:**
- MLTable schema changed
- Data preprocessing modified
- Corrupt data files
- Type mismatches

**Error Message:**
```
DataValidationError: Column 'timestamp' expected type datetime64, got object
SchemaValidationError: Required column 'sensor_value' not found
```

**Impact:** Job fails during data loading

**Mitigation:**
- Implement data validation in component code
- Use schema versioning
- Add data quality checks before training
- Test with sample data in PR validation

#### 2.5 Data Too Large (OOM)
**Cause:**
- Dataset exceeds available memory
- Inefficient data loading
- Wrong compute SKU (too small)

**Error Message:**
```
OutOfMemoryError: Cannot allocate memory for array
MemoryError: Unable to load dataset
```

**Impact:** Job crashes during data loading

**Mitigation:**
- Use streaming data loading
- Implement batch processing
- Use larger compute SKU
- Optimize data loading logic

---

## 🐳 Environment & Dependency Failures

### 3. **Docker Environment Issues**

#### 3.1 Environment Build Failure
**Cause:**
- Invalid Dockerfile syntax
- Package installation fails
- Conda/pip dependency conflicts
- Base image not found

**Error Message:**
```
EnvironmentBuildError: Failed to build environment 'lstm-training-env:1.0.0'
ERROR: Could not find a version that satisfies the requirement tensorflow==2.15.0
ERROR: No matching distribution found for tensorflow==2.15.0
```

**Impact:** All jobs using this environment fail

**Mitigation:**
```yaml
# Pin all dependency versions in environment.yaml
dependencies:
  - python=3.9.18  # Exact version
  - pip=23.3.1
  - pip:
    - tensorflow==2.14.0  # Known working version
    - numpy==1.24.3
    - pandas==2.0.3
```

**Pre-build validation:**
```python
# Test environment build in PR validation
- script: |
    az ml environment create \
      --file config/environment.yaml \
      --workspace-name $(workspaceName)
  displayName: 'Validate Environment Build'
```

#### 3.2 Environment Pull Failure
**Cause:**
- Container registry unavailable
- Network issues
- Registry authentication failure
- Image corrupted

**Error Message:**
```
ImagePullError: Failed to pull image from registry
AuthenticationFailed: Unable to authenticate to container registry
NetworkError: Timeout pulling image
```

**Impact:** Job fails to start

**Mitigation:**
- Use Azure Container Registry with managed identity
- Implement retry logic for image pulls
- Cache images on compute nodes
- Monitor ACR health

#### 3.3 Package Import Failures (Runtime)
**Cause:**
- Package not installed despite being in requirements
- Version conflicts discovered at runtime
- Platform-specific dependencies (Linux vs Windows)
- Missing system libraries

**Error Message:**
```
ModuleNotFoundError: No module named 'tensorflow'
ImportError: libcudnn.so.8: cannot open shared object file
ImportError: DLL load failed while importing _sqlite3
```

**Impact:** Job fails immediately after starting

**Mitigation:**
```python
# Add import validation in component code
import sys

def validate_environment():
    """Validate all required packages are importable."""
    required_packages = [
        'tensorflow',
        'numpy',
        'pandas',
        'mlflow',
        'azureml.core'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import {package}: {e}")
            sys.exit(1)

# Call at start of component
validate_environment()
```

#### 3.4 CUDA/GPU Issues
**Cause:**
- GPU compute requested but not available
- CUDA version mismatch
- GPU drivers not installed
- GPU memory exhausted

**Error Message:**
```
CudaError: CUDA out of memory
CudaError: CUDA driver version is insufficient for CUDA runtime version
RuntimeError: No CUDA GPUs are available
```

**Impact:** Job fails if GPU required, or runs slowly on CPU

**Mitigation:**
```python
# Add GPU detection and fallback
import tensorflow as tf

gpus = tf.config.list_physical_devices('GPU')
if not gpus:
    print("⚠️  No GPUs detected, falling back to CPU")
    print("   Training will be slower")
else:
    print(f"✅ Using {len(gpus)} GPU(s)")
    # Enable memory growth to prevent OOM
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)
```

---

## 📝 Component & Pipeline Configuration Failures

### 4. **Pipeline Definition Issues**

#### 4.1 Component Not Found
**Cause:**
- Component not registered
- Wrong component name/version
- Component in different workspace
- Typo in component reference

**Error Message:**
```
ComponentNotFound: Component 'train_lstm_model:1.0.0' not found
```

**Impact:** Pipeline fails at submission

**Mitigation:**
```python
# Verify component exists before pipeline submission
check_cmd = [
    'az', 'ml', 'component', 'show',
    '--name', component_name,
    '--version', component_version,
    '--workspace-name', workspace
]
result = subprocess.run(check_cmd, capture_output=True)
if result.returncode != 0:
    print(f"❌ Component not found: {component_name}:{component_version}")
    sys.exit(1)
```

#### 4.2 Invalid Pipeline YAML
**Cause:**
- YAML syntax errors
- Invalid schema
- Missing required fields
- Type mismatches

**Error Message:**
```
PipelineDefinitionError: Invalid pipeline definition
YAMLError: mapping values are not allowed here
ValidationError: Missing required field 'type' in input 'training_data'
```

**Impact:** Pipeline submission fails

**Mitigation:**
```python
# Validate YAML syntax in PR validation
import yaml
import jsonschema

with open('pipelines/single-circuit-training.yaml', 'r') as f:
    pipeline = yaml.safe_load(f)

# Validate against schema
validate_pipeline_schema(pipeline)
```

#### 4.3 Input/Output Mismatch
**Cause:**
- Component output doesn't match pipeline input
- Type mismatch (uri_file vs uri_folder)
- Missing required inputs
- Wrong parameter names

**Error Message:**
```
InputTypeMismatch: Component expects type 'uri_folder' but received 'uri_file'
RequiredInputNotProvided: Required input 'circuit_config' not provided
OutputNotFound: Component output 'trained_model' not found
```

**Impact:** Pipeline validation fails or runtime error

**Mitigation:**
```yaml
# Ensure type consistency
# Component definition
outputs:
  trained_model:
    type: custom_model  # Must match

# Pipeline job
outputs:
  trained_model:
    type: custom_model  # Must match
```

#### 4.4 Invalid Parameter Values
**Cause:**
- Parameter out of valid range
- Wrong data type
- Invalid enum value
- Null/empty required parameter

**Error Message:**
```
ParameterValidationError: Parameter 'learning_rate' must be between 0.0 and 1.0, got -0.1
TypeError: Parameter 'epochs' expected int, got str
```

**Impact:** Pipeline validation fails

**Mitigation:**
```python
# Add parameter validation in component code
def validate_parameters(config):
    """Validate training parameters."""
    lr = config.get('learning_rate', 0.001)
    if not 0.0 < lr < 1.0:
        raise ValueError(f"learning_rate must be in (0, 1), got {lr}")
    
    epochs = config.get('epochs', 100)
    if not isinstance(epochs, int) or epochs <= 0:
        raise ValueError(f"epochs must be positive int, got {epochs}")
    
    batch_size = config.get('batch_size', 32)
    if batch_size not in [16, 32, 64, 128, 256]:
        raise ValueError(f"batch_size must be power of 2, got {batch_size}")
```

---

## 💻 Training Code Failures

### 5. **Model Training Issues**

#### 5.1 Insufficient Data
**Cause:**
- Empty dataset
- Too few samples after filtering
- Data quality issues
- Wrong date range

**Error Message:**
```
ValueError: Cannot train with empty dataset
InsufficientDataError: Need at least 100 samples, got 5
```

**Impact:** Training fails immediately

**Mitigation:**
```python
# Validate data before training
def validate_dataset(df, min_samples=100):
    """Validate dataset has sufficient data."""
    if df.empty:
        raise ValueError("Dataset is empty")
    
    if len(df) < min_samples:
        raise ValueError(f"Insufficient data: {len(df)} < {min_samples}")
    
    # Check for null values
    null_pct = df.isnull().sum().sum() / (len(df) * len(df.columns))
    if null_pct > 0.1:  # >10% null
        raise ValueError(f"Too many null values: {null_pct:.1%}")
    
    print(f"✅ Dataset validated: {len(df)} samples, {null_pct:.2%} null")
```

#### 5.2 Training Divergence / NaN Loss
**Cause:**
- Learning rate too high
- Exploding gradients
- Numerical instability
- Bad initialization

**Error Message:**
```
RuntimeError: Loss became NaN during training
ValueError: NaN or Inf found in gradients
```

**Impact:** Training produces unusable model

**Mitigation:**
```python
# Add gradient clipping and NaN checks
import tensorflow as tf

# Gradient clipping
optimizer = tf.keras.optimizers.Adam(
    learning_rate=0.001,
    clipnorm=1.0,  # Clip gradients
    clipvalue=0.5
)

# NaN callback
class NanTerminator(tf.keras.callbacks.Callback):
    def on_batch_end(self, batch, logs=None):
        loss = logs.get('loss')
        if loss is None or np.isnan(loss) or np.isinf(loss):
            print(f"❌ NaN/Inf loss detected at batch {batch}")
            self.model.stop_training = True

model.fit(X_train, y_train, callbacks=[NanTerminator()])
```

#### 5.3 Out of Memory (Training)
**Cause:**
- Batch size too large
- Model too large
- Gradient accumulation without clearing
- Memory leaks

**Error Message:**
```
ResourceExhaustedError: OOM when allocating tensor
OutOfMemoryError: CUDA out of memory. Tried to allocate 2.00 GiB
```

**Impact:** Training crashes mid-execution

**Mitigation:**
```python
# Dynamic batch size adjustment
def find_optimal_batch_size(model, X_train, y_train):
    """Find largest batch size that fits in memory."""
    batch_sizes = [256, 128, 64, 32, 16, 8]
    
    for batch_size in batch_sizes:
        try:
            print(f"Testing batch_size={batch_size}...")
            model.fit(X_train, y_train, 
                     batch_size=batch_size,
                     epochs=1,
                     verbose=0)
            print(f"✅ Using batch_size={batch_size}")
            return batch_size
        except Exception as e:
            if "OOM" in str(e) or "ResourceExhausted" in str(e):
                print(f"⚠️  batch_size={batch_size} too large")
                continue
            raise
    
    raise RuntimeError("Cannot find working batch size")
```

#### 5.4 Training Timeout
**Cause:**
- Training takes longer than job timeout
- Compute too slow (wrong SKU)
- Too many epochs
- Inefficient code

**Error Message:**
```
JobTimeoutError: Job exceeded maximum runtime of 4 hours
```

**Impact:** Job killed mid-training

**Mitigation:**
```python
# Implement checkpointing
checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
    filepath='./outputs/checkpoints/model_{epoch:02d}.h5',
    save_freq='epoch',
    save_best_only=False
)

# Early stopping
early_stopping = tf.keras.callbacks.EarlyStopping(
    monitor='val_loss',
    patience=10,
    restore_best_weights=True
)

model.fit(X_train, y_train,
         callbacks=[checkpoint_callback, early_stopping],
         epochs=1000)  # Early stopping will prevent full 1000 epochs
```

#### 5.5 Poor Model Performance
**Cause:**
- Hyperparameters not tuned
- Data quality issues
- Wrong model architecture
- Overfitting/underfitting

**Error Message:**
```
# No error, but metrics are bad
ValidationAccuracy: 0.52  # Near random
TrainLoss: 0.001, ValLoss: 10.5  # Severe overfitting
```

**Impact:** Model registers but performs poorly

**Mitigation:**
```python
# Add performance validation before registration
def validate_model_performance(metrics, thresholds):
    """Validate model meets minimum performance criteria."""
    val_loss = metrics.get('val_loss')
    if val_loss > thresholds['max_val_loss']:
        raise ValueError(f"Validation loss too high: {val_loss:.4f}")
    
    train_loss = metrics.get('train_loss')
    if val_loss > train_loss * 2.0:
        raise ValueError(f"Severe overfitting detected: train={train_loss:.4f}, val={val_loss:.4f}")
    
    # Check if model is better than baseline
    baseline_loss = thresholds.get('baseline_loss', float('inf'))
    if val_loss > baseline_loss * 0.95:  # Must be 5% better
        raise ValueError(f"Model not better than baseline: {val_loss:.4f} vs {baseline_loss:.4f}")
    
    print("✅ Model performance validated")
```

---

## 💾 Output & Artifact Failures

### 6. **Model Output Issues**

#### 6.1 Output Path Not Found
**Cause:**
- Component didn't write to expected path
- Wrong output directory
- Permission issues
- Disk full

**Error Message:**
```
OutputNotFound: Expected output at './outputs/model/' but path does not exist
```

**Impact:** Pipeline fails when trying to register model

**Mitigation:**
```python
# Ensure output directory exists and model is saved
import os

output_dir = './outputs/model/'
os.makedirs(output_dir, exist_ok=True)

# Save model
model.save(os.path.join(output_dir, 'model.h5'))

# Verify save succeeded
if not os.path.exists(os.path.join(output_dir, 'model.h5')):
    raise RuntimeError("Model save failed")

print(f"✅ Model saved to {output_dir}")
```

#### 6.2 Model Serialization Failure
**Cause:**
- Custom objects not registered
- Incompatible TensorFlow versions
- Corrupt model state
- Unsupported layer types

**Error Message:**
```
SerializationError: Cannot serialize custom layer 'CustomLSTM'
TypeError: Object of type 'function' is not JSON serializable
```

**Impact:** Model trains but cannot be saved

**Mitigation:**
```python
# Register custom objects before saving
import tensorflow as tf
from custom_layers import CustomLSTM

# Option 1: Save with custom object scope
with tf.keras.utils.custom_object_scope({'CustomLSTM': CustomLSTM}):
    model.save('model.h5')

# Option 2: Use SavedModel format (more robust)
model.save('model', save_format='tf')  # Not HDF5

# Option 3: Save config separately
model_config = model.to_json()
with open('model_config.json', 'w') as f:
    f.write(model_config)
model.save_weights('model_weights.h5')
```

#### 6.3 Output Too Large
**Cause:**
- Model file exceeds size limits
- Too many checkpoints saved
- Large artifacts (plots, logs)
- Inefficient serialization

**Error Message:**
```
OutputSizeLimitExceeded: Output size 10GB exceeds limit of 5GB
```

**Impact:** Model cannot be registered

**Mitigation:**
```python
# Compress model and clean up artifacts
import gzip
import shutil

# Save only essential artifacts
model.save('model.h5')

# Compress if needed
with open('model.h5', 'rb') as f_in:
    with gzip.open('model.h5.gz', 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

# Clean up intermediate files
for checkpoint_file in glob.glob('./outputs/checkpoints/*.h5'):
    os.remove(checkpoint_file)

# Limit plot sizes
import matplotlib.pyplot as plt
plt.savefig('training_plot.png', dpi=100)  # Not 300
```

---

## 🔐 Authentication & Permissions Failures

### 7. **Access Control Issues**

#### 7.1 Service Principal Expired/Invalid
**Cause:**
- Service principal credentials expired
- Service principal deleted
- Wrong credentials in pipeline
- Client secret rotated

**Error Message:**
```
AuthenticationFailed: AADSTS7000215: Invalid client secret provided
AuthenticationFailed: Service principal not found
```

**Impact:** All Azure operations fail

**Mitigation:**
- Use managed identity instead of service principal
- Set up credential rotation alerts
- Monitor service principal expiration
- Use Azure Key Vault for credentials

#### 7.2 Insufficient RBAC Permissions
**Cause:**
- Service principal lacks required roles
- Workspace access revoked
- Resource group permissions changed
- Conditional access policies

**Error Message:**
```
AuthorizationFailed: The client does not have authorization to perform action 'Microsoft.MachineLearningServices/workspaces/jobs/write'
ForbiddenError: Access denied to resource 'workspaceblobstore'
```

**Impact:** Specific operations fail (create jobs, read data, etc.)

**Mitigation:**
```bash
# Required roles for MLOps service principal
az role assignment create \
  --assignee <service-principal-id> \
  --role "AzureML Data Scientist" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.MachineLearningServices/workspaces/<workspace>

az role assignment create \
  --assignee <service-principal-id> \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<storage>
```

#### 7.3 Network/Firewall Restrictions
**Cause:**
- Workspace behind private endpoint
- Firewall rules blocking pipeline agent
- VNet restrictions
- Conditional access policies

**Error Message:**
```
NetworkAccessDenied: This workspace is behind a private endpoint
ConnectionRefused: Cannot connect to workspace endpoint
```

**Impact:** Pipeline cannot access workspace

**Mitigation:**
- Use self-hosted agents in VNet
- Configure private endpoint properly
- Add pipeline agent IPs to firewall allowlist
- Use Azure DevOps service tags

---

## ⏱️ Timeout & Resource Failures

### 8. **Azure ML Service Limits**

#### 8.1 Job Queue Timeout
**Cause:**
- Too many concurrent jobs
- Cluster nodes not scaling fast enough
- Quota limitations
- Regional capacity issues

**Error Message:**
```
QueueTimeout: Job queued for over 2 hours without starting
```

**Impact:** Jobs never start

**Mitigation:**
```python
# Implement queue time monitoring
job_submitted_time = datetime.now()

while job.status == 'Queued':
    elapsed = (datetime.now() - job_submitted_time).total_seconds()
    if elapsed > 7200:  # 2 hours
        print(f"❌ Job queued for {elapsed/3600:.1f}h - cancelling")
        ml_client.jobs.cancel(job_name)
        raise TimeoutError("Job queue timeout")
    time.sleep(60)
```

#### 8.2 Workspace Throttling
**Cause:**
- Too many API calls
- Rate limit exceeded
- Concurrent operation limit hit

**Error Message:**
```
TooManyRequests: API rate limit exceeded. Retry after 60 seconds
ThrottlingError: Too many concurrent operations
```

**Impact:** API calls fail temporarily

**Mitigation:**
```python
# Implement retry with exponential backoff
from azure.core.exceptions import HttpResponseError
import time

def api_call_with_retry(func, max_retries=5):
    """Retry API calls with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except HttpResponseError as e:
            if e.status_code == 429:  # Too Many Requests
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"⚠️  Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    raise RuntimeError("Max retries exceeded")
```

#### 8.3 Pipeline Execution Timeout
**Cause:**
- Pipeline takes longer than max allowed time
- Long-running jobs in pipeline
- Default timeout too short

**Error Message:**
```
PipelineTimeoutError: Pipeline exceeded maximum runtime of 7 days
```

**Impact:** Entire pipeline killed

**Mitigation:**
```yaml
# Set appropriate timeouts in pipeline
jobs:
  train_model:
    timeout: 14400  # 4 hours per job
    
# Set overall pipeline timeout
settings:
  force_rerun: false
  continue_on_step_failure: false
  default_compute: azureml:training-cluster
  # No pipeline-level timeout in Azure ML (defaults to workspace limit)
```

---

## 🔧 Mitigation Summary

### Pre-Flight Checks (RegisterInfrastructure Stage)
```python
def pre_flight_checks():
    """Run comprehensive pre-flight checks."""
    checks = [
        check_compute_exists,
        check_compute_quota,
        check_datastore_accessible,
        check_environment_valid,
        check_component_exists,
        check_service_principal_valid,
        check_rbac_permissions
    ]
    
    for check in checks:
        try:
            check()
        except Exception as e:
            print(f"❌ Pre-flight check failed: {check.__name__}")
            print(f"   Error: {e}")
            sys.exit(1)
    
    print("✅ All pre-flight checks passed")
```

### Comprehensive Error Handling
```python
try:
    # Submit job
    job = ml_client.jobs.create_or_update(pipeline_job)
except Exception as e:
    error_type = type(e).__name__
    
    if "ComputeNotFound" in error_type:
        print("❌ Compute cluster not found")
        print("   Action: Verify cluster exists and name is correct")
    elif "QuotaExceeded" in error_type:
        print("❌ Quota exceeded")
        print("   Action: Request quota increase or reduce concurrent jobs")
    elif "AuthenticationFailed" in error_type:
        print("❌ Authentication failed")
        print("   Action: Verify service principal credentials")
    else:
        print(f"❌ Unexpected error: {error_type}")
        print(f"   Details: {str(e)}")
    
    raise
```

### Monitoring & Alerting
```python
# Set up alerts for common failure patterns
alerts = [
    {"pattern": "ComputeNotFound", "severity": "Critical", "action": "Page on-call"},
    {"pattern": "QuotaExceeded", "severity": "High", "action": "Request quota increase"},
    {"pattern": "OOM", "severity": "Medium", "action": "Increase compute SKU"},
    {"pattern": "DataNotFound", "severity": "High", "action": "Check ETL pipeline"},
    {"pattern": "AuthenticationFailed", "severity": "Critical", "action": "Rotate credentials"}
]
```

---

## 📊 Failure Rate SLOs

**Target SLOs:**
- Infrastructure failures: < 1%
- Data/asset failures: < 2%
- Training code failures: < 5% (acceptable for experimentation)
- Environment failures: < 0.5%
- Authentication failures: < 0.1%

**Monitoring:**
- Track failure rates by category
- Set up dashboards in Azure Monitor
- Alert when SLO breached
- Weekly failure review meetings
