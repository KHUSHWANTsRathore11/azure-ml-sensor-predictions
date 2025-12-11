# Custom Docker image for sensor forecasting
# Based on official TensorFlow image
# Built by Azure ML - context is this package directory

ARG TENSORFLOW_VERSION=2.13.0
FROM tensorflow/tensorflow:${TENSORFLOW_VERSION}-gpu

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from package directory
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy and install the package itself (context is package root)
COPY . /tmp/sensor-forecasting
RUN pip install /tmp/sensor-forecasting

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TF_CPP_MIN_LOG_LEVEL=2

# Verify installation
RUN python -c "import sensor_forecasting; print(f'✅ sensor-forecasting: {sensor_forecasting.__version__}')" && \
    python -c "import tensorflow as tf; print(f'✅ TensorFlow: {tf.__version__}')"

# Default command
CMD ["/bin/bash"]
