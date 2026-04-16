#!/bin/bash
# ============================================================================
# Container Apps Deployment Script
# ============================================================================
# This script deploys or updates Container Apps after infrastructure is
# provisioned and container images are pushed to ACR.
#
# Usage:
#   ./deploy-container-apps.sh \
#     --resource-group <rg-name> \
#     --environment-id <container-apps-env-id> \
#     --frontend-app <frontend-app-name> \
#     --bff-app <bff-app-name> \
#     --acr-server <acr-login-server> \
#     --frontend-identity-resource-id <frontend-uami-resource-id> \
#     --bff-identity-resource-id <bff-uami-resource-id> \
#     --bff-identity-client-id <bff-uami-client-id> \
#     --frontend-image-tag <frontend-tag> \
#     --bff-image-tag <bff-tag> \
#     --redis-host <redis-hostname> \
#     --bff-env-vars "KEY1=val1 KEY2=val2 ..."
#
# Each Container App uses its own User-Assigned Managed Identity (UAMI) for
# ACR image pull and Azure service access.  The --*-identity-resource-id flags
# accept full ARM resource IDs required by `az containerapp create`.
#
# The --bff-env-vars flag accepts a space-separated list of KEY=VALUE pairs
# that are passed as environment variables to the BFF Container App. This
# keeps the script generic — add new env vars in the workflow without
# modifying this script.
# ============================================================================

set -euo pipefail

BFF_ENV_VARS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --resource-group)
      RESOURCE_GROUP="$2"
      shift 2
      ;;
    --environment-id)
      ENVIRONMENT_ID="$2"
      shift 2
      ;;
    --frontend-app)
      FRONTEND_APP_NAME="$2"
      shift 2
      ;;
    --bff-app)
      BFF_APP_NAME="$2"
      shift 2
      ;;
    --acr-server)
      ACR_SERVER="$2"
      shift 2
      ;;
    --frontend-identity-resource-id)
      FRONTEND_IDENTITY_RESOURCE_ID="$2"
      shift 2
      ;;
    --bff-identity-resource-id)
      BFF_IDENTITY_RESOURCE_ID="$2"
      shift 2
      ;;
    --bff-identity-client-id)
      BFF_IDENTITY_CLIENT_ID="$2"
      shift 2
      ;;
    --frontend-image-tag)
      FRONTEND_IMAGE_TAG="$2"
      shift 2
      ;;
    --bff-image-tag)
      BFF_IMAGE_TAG="$2"
      shift 2
      ;;
    --redis-host)
      REDIS_HOST="$2"
      shift 2
      ;;
    --bff-env-vars)
      BFF_ENV_VARS="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

# Validate required arguments
required_args=(RESOURCE_GROUP ENVIRONMENT_ID FRONTEND_APP_NAME BFF_APP_NAME \
               ACR_SERVER FRONTEND_IDENTITY_RESOURCE_ID BFF_IDENTITY_RESOURCE_ID \
               BFF_IDENTITY_CLIENT_ID FRONTEND_IMAGE_TAG BFF_IMAGE_TAG REDIS_HOST)
for arg in "${required_args[@]}"; do
  if [[ -z "${!arg:-}" ]]; then
    echo "Error: Missing required argument: --$(echo "$arg" | tr '[:upper:]' '[:lower:]' | tr '_' '-')"
    echo "Usage: $0 --resource-group <rg> --environment-id <env-id> --frontend-app <name> --bff-app <name> --acr-server <server> --frontend-identity-resource-id <id> --bff-identity-resource-id <id> --bff-identity-client-id <id> --frontend-image-tag <tag> --bff-image-tag <tag> --redis-host <hostname> [--bff-env-vars \"KEY=val ...\"]"
    exit 1
  fi
done

# Build the array of BFF env vars (always includes core infra vars)
BFF_CORE_ENV_VARS=(
  "AZURE_CLIENT_ID=${BFF_IDENTITY_CLIENT_ID}"
  "REDIS_HOST=${REDIS_HOST}"
  "REDIS_PORT=6380"
)

# Append any extra BFF env vars passed via --bff-env-vars
if [[ -n "$BFF_ENV_VARS" ]]; then
  read -ra EXTRA_ENV_VARS <<< "$BFF_ENV_VARS"
  BFF_CORE_ENV_VARS+=("${EXTRA_ENV_VARS[@]}")
fi

echo "============================================================================"
echo "Deploying Container Apps"
echo "============================================================================"
echo "Resource Group: $RESOURCE_GROUP"
echo "Environment ID: $ENVIRONMENT_ID"
echo "Frontend App: $FRONTEND_APP_NAME"
echo "BFF App: $BFF_APP_NAME"
echo "ACR Server: $ACR_SERVER"
echo "Frontend Identity: $FRONTEND_IDENTITY_RESOURCE_ID"
echo "BFF Identity: $BFF_IDENTITY_RESOURCE_ID"
echo "Frontend Image: ${ACR_SERVER}/frontend:${FRONTEND_IMAGE_TAG}"
echo "BFF Image: ${ACR_SERVER}/bff:${BFF_IMAGE_TAG}"
echo "Redis Host: $REDIS_HOST"
echo "BFF Env Vars: ${BFF_CORE_ENV_VARS[*]}"
echo "============================================================================"

# Deploy Frontend Container App
echo ""
echo "Deploying Frontend Container App..."
if az containerapp show --name "$FRONTEND_APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
  echo "Updating existing Frontend Container App..."
  az containerapp update \
    --name "$FRONTEND_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "${ACR_SERVER}/frontend:${FRONTEND_IMAGE_TAG}" \
    --cpu 1.0 \
    --memory 2Gi \
    --min-replicas 1 \
    --max-replicas 10 \
    --revision-suffix "$(date +%s)"
else
  echo "Creating new Frontend Container App..."
  az containerapp create \
    --name "$FRONTEND_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$ENVIRONMENT_ID" \
    --image "${ACR_SERVER}/frontend:${FRONTEND_IMAGE_TAG}" \
    --target-port 3000 \
    --ingress external \
    --cpu 1.0 \
    --memory 2Gi \
    --min-replicas 1 \
    --max-replicas 10 \
    --registry-server "$ACR_SERVER" \
    --user-assigned "$FRONTEND_IDENTITY_RESOURCE_ID" \
    --registry-identity "$FRONTEND_IDENTITY_RESOURCE_ID"
fi

# Get Frontend URL
FRONTEND_URL=$(az containerapp show \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)
echo "Frontend URL: https://${FRONTEND_URL}"

# Deploy BFF Container App
echo ""
echo "Deploying BFF Container App..."
if az containerapp show --name "$BFF_APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
  echo "Updating existing BFF Container App..."
  az containerapp update \
    --name "$BFF_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "${ACR_SERVER}/bff:${BFF_IMAGE_TAG}" \
    --cpu 0.5 \
    --memory 1Gi \
    --min-replicas 1 \
    --max-replicas 10 \
    --set-env-vars "${BFF_CORE_ENV_VARS[@]}" \
    --revision-suffix "$(date +%s)"
else
  echo "Creating new BFF Container App..."
  az containerapp create \
    --name "$BFF_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$ENVIRONMENT_ID" \
    --image "${ACR_SERVER}/bff:${BFF_IMAGE_TAG}" \
    --target-port 8000 \
    --ingress external \
    --cpu 0.5 \
    --memory 1Gi \
    --min-replicas 1 \
    --max-replicas 10 \
    --registry-server "$ACR_SERVER" \
    --user-assigned "$BFF_IDENTITY_RESOURCE_ID" \
    --registry-identity "$BFF_IDENTITY_RESOURCE_ID" \
    --env-vars "${BFF_CORE_ENV_VARS[@]}"
fi

# Get BFF URL
BFF_URL=$(az containerapp show \
  --name "$BFF_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)
echo "BFF URL: https://${BFF_URL}"

echo ""
echo "============================================================================"
echo "Deployment Complete"
echo "============================================================================"
echo "Frontend: https://${FRONTEND_URL}"
echo "BFF: https://${BFF_URL}"
echo "============================================================================"
