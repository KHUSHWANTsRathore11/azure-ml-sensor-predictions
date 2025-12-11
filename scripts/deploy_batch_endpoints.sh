#!/bin/bash
# Deploy batch endpoints for all circuits

set -e

WORKSPACE_NAME=$1
RESOURCE_GROUP=$2

if [ -z "$WORKSPACE_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
    echo "Usage: $0 <workspace-name> <resource-group>"
    exit 1
fi

echo "🚀 Deploying batch endpoints to workspace: $WORKSPACE_NAME"

# Load circuit configuration
CIRCUITS=$(python -c "
import yaml
with open('config/circuits.yaml', 'r') as f:
    config = yaml.safe_load(f)
    plants = {}
    for circuit in config['circuits']:
        plant_id = circuit['plant_id']
        if plant_id not in plants:
            plants[plant_id] = []
        plants[plant_id].append(circuit)
    
    for plant_id, circuits in plants.items():
        print(plant_id)
")

# Deploy batch endpoint per plant
for PLANT_ID in $CIRCUITS; do
    ENDPOINT_NAME="batch-$(echo $PLANT_ID | tr '[:upper:]' '[:lower:]')"
    
    echo "📦 Creating/updating batch endpoint: $ENDPOINT_NAME"
    
    # Create batch endpoint if not exists
    az ml batch-endpoint create \
        --name $ENDPOINT_NAME \
        --workspace-name $WORKSPACE_NAME \
        --resource-group $RESOURCE_GROUP \
        --description "Batch endpoint for $PLANT_ID" \
        || echo "Endpoint $ENDPOINT_NAME already exists"
    
    # Deploy circuits for this plant
    python scripts/deploy_circuits_for_plant.py \
        --workspace $WORKSPACE_NAME \
        --resource-group $RESOURCE_GROUP \
        --plant-id $PLANT_ID \
        --endpoint-name $ENDPOINT_NAME
done

echo "✅ All batch endpoints deployed successfully!"
