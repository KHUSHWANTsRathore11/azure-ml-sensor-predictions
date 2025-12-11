#!/bin/bash
# Register all components to workspace or registry

set -e

WORKSPACE_NAME=${1:-"mlw-dev"}
RESOURCE_GROUP=${2:-"rg-mlops-dev"}
REGISTRY_NAME=${3:-""}

echo "🚀 Registering all Azure ML components..."
echo "================================================"
echo "   Workspace: $WORKSPACE_NAME"
echo "   Resource Group: $RESOURCE_GROUP"

# Determine target (workspace or registry)
if [ -z "$REGISTRY_NAME" ]; then
    TARGET="--workspace-name $WORKSPACE_NAME --resource-group $RESOURCE_GROUP"
    TARGET_TYPE="Workspace"
else
    TARGET="--registry-name $REGISTRY_NAME"
    TARGET_TYPE="Registry ($REGISTRY_NAME)"
fi

echo "   Target: $TARGET_TYPE"
echo "================================================"
echo ""

# Function to register component
register_component() {
    local component_file=$1
    local component_name=$(basename $(dirname $component_file))
    local component_category=$(basename $(dirname $(dirname $component_file)))
    
    echo "📦 [$component_category] Registering: $component_name"
    
    if az ml component create --file $component_file $TARGET 2>&1 | tee /tmp/component_output.txt; then
        # Extract version from output
        VERSION=$(grep -oP 'version: \K[^,]+' /tmp/component_output.txt | head -1 || echo "N/A")
        echo "   ✅ Success - Version: $VERSION"
    else
        echo "   ❌ Failed to register $component_name"
        return 1
    fi
    echo ""
}

# Register Data Components
echo "═══════════════════════════════════════════════"
echo "📂 DATA COMPONENTS"
echo "═══════════════════════════════════════════════"
for component_file in components/data/*/component.yaml; do
    if [ -f "$component_file" ]; then
        register_component "$component_file"
    fi
done

# Register Training Components
echo "═══════════════════════════════════════════════"
echo "🏋️  TRAINING COMPONENTS"
echo "═══════════════════════════════════════════════"
for component_file in components/training/*/component.yaml; do
    if [ -f "$component_file" ]; then
        register_component "$component_file"
    fi
done

# Register Scoring Components
echo "═══════════════════════════════════════════════"
echo "🎯 SCORING COMPONENTS"
echo "═══════════════════════════════════════════════"
for component_file in components/scoring/*/component.yaml; do
    if [ -f "$component_file" ]; then
        register_component "$component_file"
    fi
done

# Register Monitoring Components
echo "═══════════════════════════════════════════════"
echo "📊 MONITORING COMPONENTS"
echo "═══════════════════════════════════════════════"
for component_file in components/monitoring/*/component.yaml; do
    if [ -f "$component_file" ]; then
        register_component "$component_file"
    fi
done

echo "═══════════════════════════════════════════════"
echo "✅ All components registered!"
echo "═══════════════════════════════════════════════"
echo ""

# List registered components
echo "📋 Listing all registered components..."
echo ""
if [ -z "$REGISTRY_NAME" ]; then
    az ml component list \
        --workspace-name $WORKSPACE_NAME \
        --resource-group $RESOURCE_GROUP \
        --output table
else
    az ml component list \
        --registry-name $REGISTRY_NAME \
        --output table
fi

echo ""
echo "🎉 Component registration complete!"
