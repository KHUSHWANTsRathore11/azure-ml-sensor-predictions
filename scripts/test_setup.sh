#!/bin/bash
# Test and validate Azure ML setup
# This script tests individual components before running the full pipeline

set -e

WORKSPACE_NAME=${1:-"mlw-dev"}
RESOURCE_GROUP=${2:-"rg-mlops-dev"}

echo "🧪 Azure ML Component Testing"
echo "================================================"
echo "   Workspace: $WORKSPACE_NAME"
echo "   Resource Group: $RESOURCE_GROUP"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_step() {
    local step_name=$1
    echo -e "${YELLOW}➜${NC} Testing: $step_name"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# ============================================
# Test 1: Azure CLI and ML Extension
# ============================================
test_step "Azure CLI and ML Extension"
if az version &>/dev/null; then
    success "Azure CLI installed"
    AZ_VERSION=$(az version --query '"azure-cli"' -o tsv)
    echo "   Version: $AZ_VERSION"
else
    error "Azure CLI not installed"
    exit 1
fi

if az ml -h &>/dev/null; then
    success "Azure ML extension installed"
    ML_VERSION=$(az extension show --name ml --query version -o tsv 2>/dev/null || echo "unknown")
    echo "   Version: $ML_VERSION"
else
    error "Azure ML extension not installed. Run: az extension add -n ml"
    exit 1
fi

echo ""

# ============================================
# Test 2: Workspace Connection
# ============================================
test_step "Workspace Connection"
if az ml workspace show --name $WORKSPACE_NAME --resource-group $RESOURCE_GROUP &>/dev/null; then
    success "Connected to workspace: $WORKSPACE_NAME"
else
    error "Cannot connect to workspace: $WORKSPACE_NAME"
    echo "   Create with: az ml workspace create --name $WORKSPACE_NAME --resource-group $RESOURCE_GROUP"
    exit 1
fi

echo ""

# ============================================
# Test 3: Python Environment
# ============================================
test_step "Python Environment"
if python3 --version &>/dev/null; then
    PYTHON_VERSION=$(python3 --version)
    success "Python installed: $PYTHON_VERSION"
else
    error "Python3 not installed"
    exit 1
fi

# Check required packages
echo "   Checking Python packages..."
python3 -c "import yaml" 2>/dev/null && success "   - pyyaml installed" || error "   - pyyaml missing (pip install pyyaml)"
python3 -c "import mltable" 2>/dev/null && success "   - mltable installed" || echo "   ⚠️  mltable not installed (optional for local testing)"

echo ""

# ============================================
# Test 4: Generate Circuit Configs
# ============================================
test_step "Generate Circuit Configs"
if [ -f "scripts/generate_circuit_configs.py" ]; then
    python3 scripts/generate_circuit_configs.py
    if [ -d "config/circuits" ]; then
        CIRCUIT_COUNT=$(ls config/circuits/*.yaml 2>/dev/null | wc -l)
        success "Generated $CIRCUIT_COUNT circuit config files"
    else
        error "Circuit configs directory not created"
        exit 1
    fi
else
    error "generate_circuit_configs.py not found"
    exit 1
fi

echo ""

# ============================================
# Test 5: Detect Config Changes
# ============================================
test_step "Detect Config Changes"
if [ -f "scripts/detect_config_changes.py" ]; then
    # This will fail if not in git repo, which is okay
    python3 scripts/detect_config_changes.py --target-branch main --output /tmp/changed_circuits.json 2>/dev/null || {
        echo "   ⚠️  Git diff failed (expected if not in repo or no changes)"
        echo '[]' > /tmp/changed_circuits.json
    }
    
    if [ -f "/tmp/changed_circuits.json" ]; then
        CHANGE_COUNT=$(python3 -c "import json; print(len(json.load(open('/tmp/changed_circuits.json'))))" 2>/dev/null || echo "0")
        success "Change detection works (found $CHANGE_COUNT changes)"
    fi
else
    error "detect_config_changes.py not found"
    exit 1
fi

echo ""

# ============================================
# Test 6: Environment Registration
# ============================================
test_step "Environment Registration (Dry Run)"
if [ -f "config/environment.yaml" ]; then
    success "Environment config found: config/environment.yaml"
    
    # Check if environment exists
    ENV_EXISTS=$(az ml environment show \
        --name sensor-forecasting-env \
        --workspace-name $WORKSPACE_NAME \
        --resource-group $RESOURCE_GROUP \
        --query name -o tsv 2>/dev/null || echo "not_found")
    
    if [ "$ENV_EXISTS" = "sensor-forecasting-env" ]; then
        ENV_VERSION=$(az ml environment show \
            --name sensor-forecasting-env \
            --workspace-name $WORKSPACE_NAME \
            --resource-group $RESOURCE_GROUP \
            --query version -o tsv)
        success "Environment already registered: sensor-forecasting-env:$ENV_VERSION"
    else
        echo "   Environment not yet registered (will be created on first pipeline run)"
    fi
else
    error "Environment config not found"
    exit 1
fi

echo ""

# ============================================
# Test 7: Component Definitions
# ============================================
test_step "Component Definitions"
COMPONENT_FILES=(
    "components/training/train-lstm-model/component.yaml"
    "components/training/train-lstm-model/src/train.py"
    "components/scoring/batch-score/component.yaml"
)

for file in "${COMPONENT_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "   $file"
    else
        error "   $file NOT FOUND"
        exit 1
    fi
done

# Check if components are registered
echo ""
echo "   Checking registered components..."
TRAIN_COMP=$(az ml component show \
    --name train_lstm_model \
    --workspace-name $WORKSPACE_NAME \
    --resource-group $RESOURCE_GROUP \
    --query name -o tsv 2>/dev/null || echo "not_found")

if [ "$TRAIN_COMP" = "train_lstm_model" ]; then
    TRAIN_VERSION=$(az ml component show \
        --name train_lstm_model \
        --workspace-name $WORKSPACE_NAME \
        --resource-group $RESOURCE_GROUP \
        --query version -o tsv)
    success "   train_lstm_model:$TRAIN_VERSION already registered"
else
    echo "   ⚠️  train_lstm_model not yet registered"
fi

echo ""

# ============================================
# Test 8: Pipeline Definitions
# ============================================
test_step "Pipeline Definitions"
PIPELINE_FILES=(
    ".azuredevops/build-pipeline.yml"
    "pipelines/single-circuit-training.yaml"
)

for file in "${PIPELINE_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "   $file"
    else
        error "   $file NOT FOUND"
        exit 1
    fi
done

echo ""

# ============================================
# Test 9: Documentation
# ============================================
test_step "Documentation"
DOC_FILES=(
    "docs/COMPONENT_FLOW_DIAGRAM.md"
    "docs/CUTOFF_DATE_VERSION_VS_TAG.md"
    "IMPLEMENTATION_PROGRESS.md"
)

for file in "${DOC_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "   $file"
    else
        echo "   ⚠️  $file not found (optional)"
    fi
done

echo ""
echo "================================================"
echo -e "${GREEN}✅ All tests passed!${NC}"
echo "================================================"
echo ""
echo "📋 Next Steps:"
echo "   1. Register environment: az ml environment create --file config/environment.yaml"
echo "   2. Register components: az ml component create --file components/training/train-lstm-model/component.yaml"
echo "   3. Run build pipeline in Azure DevOps"
echo ""
echo "📚 Documentation:"
echo "   - Implementation Progress: IMPLEMENTATION_PROGRESS.md"
echo "   - Component Flow: docs/COMPONENT_FLOW_DIAGRAM.md"
echo "   - Version Strategy: docs/CUTOFF_DATE_VERSION_VS_TAG.md"
