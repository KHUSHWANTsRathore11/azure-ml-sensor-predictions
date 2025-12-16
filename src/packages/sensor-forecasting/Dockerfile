# Azure ML base image with OpenMPI 4.1.0 for distributed training
# This image is optimized for Azure ML and includes MPI support
FROM mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04:latest

# Ensure we're running as root for installations
# (Azure ML compute will switch to non-root user at runtime)
USER root

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Azure ML runtime dependencies (lightweight, installed first)
RUN pip install --no-cache-dir \
    azureml-core \
    azureml-mlflow \
    azureml-dataset-runtime \
    mlflow

# Install TensorFlow GPU (required for training)
RUN pip install --no-cache-dir tensorflow[and-cuda]==2.13.0

# Copy and install the package with pyproject.toml (includes all dependencies)
COPY . /tmp/sensor-forecasting
RUN pip install --no-cache-dir /tmp/sensor-forecasting

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TF_CPP_MIN_LOG_LEVEL=2

# Verify installation
RUN python -c "import sensor_forecasting; print(f'✅ sensor-forecasting: {sensor_forecasting.__version__}')" && \
    python -c "import tensorflow as tf; print(f'✅ TensorFlow: {tf.__version__}')" && \
    python -c "import azureml.core; print(f'✅ Azure ML: {azureml.core.VERSION}')"

# Default command
CMD ["/bin/bash"]
