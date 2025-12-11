#!/bin/bash
# Build and push custom Docker image with sensor-forecasting package
# This script:
# 1. Reads package version from packages/sensor-forecasting/version.py
# 2. Builds Docker image with that version
# 3. Pushes to Azure Container Registry
# 4. Updates config/environment.yaml with image reference

set -e

# Configuration
ACR_NAME=${1:-"your-acr-name"}  # Pass as argument or set default
IMAGE_NAME="sensor-forecasting"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🐳 Building Custom Docker Image for Sensor Forecasting"
echo "================================================"

# Step 1: Get package version
echo "📦 Reading package version..."
PACKAGE_VERSION=$(python3 -c "exec(open('packages/sensor-forecasting/version.py').read()); print(__version__)")

if [ -z "$PACKAGE_VERSION" ]; then
    echo "❌ Failed to read package version"
    exit 1
fi

echo -e "${GREEN}✅ Package version: $PACKAGE_VERSION${NC}"

# Step 2: Build Docker image
IMAGE_TAG="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${PACKAGE_VERSION}"
IMAGE_TAG_LATEST="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:latest"

echo ""
echo "🔨 Building Docker image..."
echo "   Tag: $IMAGE_TAG"

docker build \
    -t $IMAGE_TAG \
    -t $IMAGE_TAG_LATEST \
    -f docker/Dockerfile \
    --build-arg TENSORFLOW_VERSION=2.13.0 \
    .

echo -e "${GREEN}✅ Image built successfully${NC}"

# Step 3: Test image
echo ""
echo "🧪 Testing image..."
docker run --rm $IMAGE_TAG python -c "
import sensor_forecasting
import tensorflow as tf
print(f'✅ sensor-forecasting: {sensor_forecasting.__version__}')
print(f'✅ TensorFlow: {tf.__version__}')
"

# Step 4: Push to ACR
echo ""
echo "📤 Pushing to Azure Container Registry..."
echo "   Registry: $ACR_NAME"

# Login to ACR
az acr login --name $ACR_NAME

# Push versioned tag
docker push $IMAGE_TAG
echo -e "${GREEN}✅ Pushed: $IMAGE_TAG${NC}"

# Push latest tag
docker push $IMAGE_TAG_LATEST
echo -e "${GREEN}✅ Pushed: $IMAGE_TAG_LATEST${NC}"

# Step 5: Update environment.yaml
echo ""
echo "📝 Updating config/environment.yaml..."

# Create updated environment.yaml
cat > config/environment.yaml << EOF
\$schema: https://azuremlschemas.azureedge.net/latest/environment.schema.json
name: sensor-forecasting-env
version: "$PACKAGE_VERSION"
description: Custom Docker environment with embedded sensor-forecasting package v$PACKAGE_VERSION

# Docker image reference
image: $IMAGE_TAG

tags:
  framework: tensorflow
  tensorflow_version: "2.13.0"
  build_type: docker
  package_name: sensor-forecasting
  package_version: "$PACKAGE_VERSION"
  purpose: time-series-forecasting
  built_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EOF

echo -e "${GREEN}✅ Updated config/environment.yaml${NC}"

# Step 6: Summary
echo ""
echo "================================================"
echo -e "${GREEN}✅ Build Complete!${NC}"
echo "================================================"
echo "Package Version: $PACKAGE_VERSION"
echo "Image Tag: $IMAGE_TAG"
echo ""
echo "Next steps:"
echo "1. Register environment in Azure ML:"
echo "   az ml environment create --file config/environment.yaml"
echo ""
echo "2. Or run build pipeline (auto-registers)"
echo "================================================"
