#!/bin/bash
# ============================================================================
# Container Apps Deployment Script
# ============================================================================
# This script deploys or updates Container Apps and Container Apps Jobs after
# infrastructure is provisioned and container images are pushed to ACR.
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
#     --indexer-image-tag <indexer-tag> \
#     --indexer-identity-resource-id <indexer-uami-resource-id> \
#     --indexer-identity-client-id <indexer-uami-client-id> \
#     --bff-env-vars "KEY1=val1 KEY2=val2 ..." \
#     --frontend-env-vars "KEY1=val1 KEY2=val2 ..." \
#     --indexer-env-vars "KEY1=val1 KEY2=val2 ..." \
#     --governance-image-tag <governance-tag> \
#     --governance-identity-resource-id <governance-uami-resource-id> \
#     --governance-identity-client-id <governance-uami-client-id> \
#     --governance-env-vars "KEY1=val1 KEY2=val2 ..."
#
# Each Container App uses its own User-Assigned Managed Identity (UAMI) for
# ACR image pull and Azure service access.  The --*-identity-resource-id flags
# accept full ARM resource IDs required by `az containerapp create`.
#
# The --*-env-vars flags accept space-separated lists of KEY=VALUE pairs that
# are passed as environment variables to the respective Container Apps / Jobs.
# This keeps the script generic — add new env vars in the workflow without
# modifying this script.
# ============================================================================

set -euo pipefail

BFF_ENV_VARS=""
FRONTEND_ENV_VARS=""
INDEXER_ENV_VARS=""
INDEXER_IMAGE_TAG=""
INDEXER_IDENTITY_RESOURCE_ID=""
INDEXER_IDENTITY_CLIENT_ID=""
GOVERNANCE_ENV_VARS=""
GOVERNANCE_IMAGE_TAG=""
GOVERNANCE_IDENTITY_RESOURCE_ID=""
GOVERNANCE_IDENTITY_CLIENT_ID=""

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
    --frontend-env-vars)
      FRONTEND_ENV_VARS="$2"
      shift 2
      ;;
    --indexer-image-tag)
      INDEXER_IMAGE_TAG="$2"
      shift 2
      ;;
    --indexer-identity-resource-id)
      INDEXER_IDENTITY_RESOURCE_ID="$2"
      shift 2
      ;;
    --indexer-identity-client-id)
      INDEXER_IDENTITY_CLIENT_ID="$2"
      shift 2
      ;;
    --indexer-env-vars)
      INDEXER_ENV_VARS="$2"
      shift 2
      ;;
    --governance-image-tag)
      GOVERNANCE_IMAGE_TAG="$2"
      shift 2
      ;;
    --governance-identity-resource-id)
      GOVERNANCE_IDENTITY_RESOURCE_ID="$2"
      shift 2
      ;;
    --governance-identity-client-id)
      GOVERNANCE_IDENTITY_CLIENT_ID="$2"
      shift 2
      ;;
    --governance-env-vars)
      GOVERNANCE_ENV_VARS="$2"
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
    echo "Usage: $0 --resource-group <rg> --environment-id <env-id>" \
         "--frontend-app <name> --bff-app <name> --acr-server <server>" \
         "--frontend-identity-resource-id <id> --bff-identity-resource-id <id>" \
         "--bff-identity-client-id <id> --frontend-image-tag <tag>" \
         "--bff-image-tag <tag> --redis-host <hostname>" \
         "[--bff-env-vars \"KEY=val ...\"]" \
         "[--indexer-image-tag <tag> --indexer-identity-resource-id <id>" \
         " --indexer-identity-client-id <id>]"
    exit 1
  fi
done

# Validate identity arguments are real ARM resource IDs, not the literal string "null"
for id_arg in FRONTEND_IDENTITY_RESOURCE_ID BFF_IDENTITY_RESOURCE_ID; do
  if [[ "${!id_arg}" == "null" ]]; then
    echo "Error: ${id_arg} is 'null'. This usually means the infrastructure deployment"
    echo "       outputs are stale. Re-run the deploy-infra workflow first, then retry."
    exit 1
  fi
  if [[ ! "${!id_arg}" =~ ^/subscriptions/ ]]; then
    echo "Error: ${id_arg} does not look like a valid ARM resource ID: '${!id_arg}'"
    echo "       Expected format: /subscriptions/{sub}/resourceGroups/{rg}/providers/..."
    exit 1
  fi
done
if [[ "$BFF_IDENTITY_CLIENT_ID" == "null" ]]; then
  echo "Error: BFF_IDENTITY_CLIENT_ID is 'null'. Re-run the deploy-infra workflow first."
  exit 1
fi

# Validate indexer identity arguments when indexer deployment is requested
if [[ -n "$INDEXER_IMAGE_TAG" ]]; then
  if [[ -z "$INDEXER_IDENTITY_RESOURCE_ID" || "$INDEXER_IDENTITY_RESOURCE_ID" == "null" ]]; then
    echo "Error: INDEXER_IDENTITY_RESOURCE_ID is missing or 'null'. Re-run the deploy-infra workflow first."
    exit 1
  fi
  if [[ ! "$INDEXER_IDENTITY_RESOURCE_ID" =~ ^/subscriptions/ ]]; then
    echo "Error: INDEXER_IDENTITY_RESOURCE_ID does not look like a valid ARM resource ID: '$INDEXER_IDENTITY_RESOURCE_ID'"
    exit 1
  fi
  if [[ -z "$INDEXER_IDENTITY_CLIENT_ID" || "$INDEXER_IDENTITY_CLIENT_ID" == "null" ]]; then
    echo "Error: INDEXER_IDENTITY_CLIENT_ID is missing or 'null'. Re-run the deploy-infra workflow first."
    exit 1
  fi
fi

# Validate governance identity arguments when governance deployment is requested
if [[ -n "$GOVERNANCE_IMAGE_TAG" ]]; then
  if [[ -z "$GOVERNANCE_IDENTITY_RESOURCE_ID" || "$GOVERNANCE_IDENTITY_RESOURCE_ID" == "null" ]]; then
    echo "Error: GOVERNANCE_IDENTITY_RESOURCE_ID is missing or 'null'. Re-run the deploy-infra workflow first."
    exit 1
  fi
  if [[ ! "$GOVERNANCE_IDENTITY_RESOURCE_ID" =~ ^/subscriptions/ ]]; then
    echo "Error: GOVERNANCE_IDENTITY_RESOURCE_ID does not look like a valid ARM resource ID: '$GOVERNANCE_IDENTITY_RESOURCE_ID'"
    exit 1
  fi
  if [[ -z "$GOVERNANCE_IDENTITY_CLIENT_ID" || "$GOVERNANCE_IDENTITY_CLIENT_ID" == "null" ]]; then
    echo "Error: GOVERNANCE_IDENTITY_CLIENT_ID is missing or 'null'. Re-run the deploy-infra workflow first."
    exit 1
  fi
fi

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
echo "Frontend Env Vars (pre-deploy): ${FRONTEND_ENV_VARS:-<none>}"
if [[ -n "$INDEXER_IMAGE_TAG" ]]; then
  echo "Indexer Image: ${ACR_SERVER}/indexer:${INDEXER_IMAGE_TAG}"
  echo "Indexer Identity: $INDEXER_IDENTITY_RESOURCE_ID"
  echo "Indexer Env Vars: ${INDEXER_ENV_VARS:-<none>}"
fi
if [[ -n "$GOVERNANCE_IMAGE_TAG" ]]; then
  echo "Governance Worker Image: ${ACR_SERVER}/governance-worker:${GOVERNANCE_IMAGE_TAG}"
  echo "Governance Worker Identity: $GOVERNANCE_IDENTITY_RESOURCE_ID"
  echo "Governance Worker Env Vars: ${GOVERNANCE_ENV_VARS:-<none>}"
fi
echo "============================================================================"

# Deploy BFF Container App first (its URL is needed by the frontend)
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

# Get BFF URL (used to configure frontend proxy)
BFF_URL=$(az containerapp show \
  --name "$BFF_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)
echo "BFF URL: https://${BFF_URL}"

# Deploy Frontend Container App with BFF_URL so the server-side proxy
# can forward /api/* requests to the BFF at runtime, plus runtime MSAL config.
echo ""
echo "Deploying Frontend Container App..."

# Build the array of frontend env vars (always includes BFF_URL)
FRONTEND_CORE_ENV_VARS=(
  "BFF_URL=https://${BFF_URL}"
)

# Append any extra frontend env vars passed via --frontend-env-vars
if [[ -n "$FRONTEND_ENV_VARS" ]]; then
  read -ra EXTRA_FRONTEND_ENV_VARS <<< "$FRONTEND_ENV_VARS"
  FRONTEND_CORE_ENV_VARS+=("${EXTRA_FRONTEND_ENV_VARS[@]}")
fi

echo "Frontend Env Vars (${#FRONTEND_CORE_ENV_VARS[@]} vars): ${FRONTEND_CORE_ENV_VARS[*]}"

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
    --set-env-vars "${FRONTEND_CORE_ENV_VARS[@]}" \
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
    --registry-identity "$FRONTEND_IDENTITY_RESOURCE_ID" \
    --env-vars "${FRONTEND_CORE_ENV_VARS[@]}"
fi

# Get Frontend URL
FRONTEND_URL=$(az containerapp show \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)
echo "Frontend URL: https://${FRONTEND_URL}"

# ============================================================================
# Deploy Indexer Container Apps Job (cron-based, runs to completion)
# ============================================================================
if [[ -n "$INDEXER_IMAGE_TAG" ]]; then
  echo ""
  echo "Deploying Indexer Container Apps Job..."

  # Derive the job name from the BFF app name pattern (replace -bff- with -indexer-)
  INDEXER_JOB_NAME="${BFF_APP_NAME/bff/indexer}"

  # Build indexer env vars
  INDEXER_CORE_ENV_VARS=(
    "AZURE_CLIENT_ID=${INDEXER_IDENTITY_CLIENT_ID}"
  )

  if [[ -n "$INDEXER_ENV_VARS" ]]; then
    read -ra EXTRA_INDEXER_ENV_VARS <<< "$INDEXER_ENV_VARS"
    INDEXER_CORE_ENV_VARS+=("${EXTRA_INDEXER_ENV_VARS[@]}")
  fi

  echo "Indexer Job Name: $INDEXER_JOB_NAME"
  echo "Indexer Image: ${ACR_SERVER}/indexer:${INDEXER_IMAGE_TAG}"
  echo "Indexer Env Vars (${#INDEXER_CORE_ENV_VARS[@]} vars): ${INDEXER_CORE_ENV_VARS[*]}"

  if az containerapp job show --name "$INDEXER_JOB_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "Updating existing Indexer Container Apps Job..."
    az containerapp job update \
      --name "$INDEXER_JOB_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --image "${ACR_SERVER}/indexer:${INDEXER_IMAGE_TAG}" \
      --cpu 0.5 \
      --memory 1Gi \
      --set-env-vars "${INDEXER_CORE_ENV_VARS[@]}"
  else
    echo "Creating new Indexer Container Apps Job..."
    az containerapp job create \
      --name "$INDEXER_JOB_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --environment "$ENVIRONMENT_ID" \
      --image "${ACR_SERVER}/indexer:${INDEXER_IMAGE_TAG}" \
      --cpu 0.5 \
      --memory 1Gi \
      --trigger-type Schedule \
      --cron-expression "*/5 * * * *" \
      --replica-timeout 600 \
      --replica-retry-limit 1 \
      --parallelism 1 \
      --replica-completion-count 1 \
      --registry-server "$ACR_SERVER" \
      --mi-user-assigned "$INDEXER_IDENTITY_RESOURCE_ID" \
      --registry-identity "$INDEXER_IDENTITY_RESOURCE_ID" \
      --env-vars "${INDEXER_CORE_ENV_VARS[@]}"
  fi

  echo "Indexer Job: $INDEXER_JOB_NAME (cron: */5 * * * *)"
fi

# ============================================================================
# Deploy Governance Snapshot Worker Container Apps Job (daily cron)
# ============================================================================
if [[ -n "$GOVERNANCE_IMAGE_TAG" ]]; then
  echo ""
  echo "Deploying Governance Snapshot Worker Container Apps Job..."

  # Derive the job name from the BFF app name pattern (replace -bff- with -governance-)
  GOVERNANCE_JOB_NAME="${BFF_APP_NAME/bff/governance}"

  # Build governance worker env vars
  GOVERNANCE_CORE_ENV_VARS=(
    "AZURE_CLIENT_ID=${GOVERNANCE_IDENTITY_CLIENT_ID}"
  )

  if [[ -n "$GOVERNANCE_ENV_VARS" ]]; then
    read -ra EXTRA_GOVERNANCE_ENV_VARS <<< "$GOVERNANCE_ENV_VARS"
    GOVERNANCE_CORE_ENV_VARS+=("${EXTRA_GOVERNANCE_ENV_VARS[@]}")
  fi

  echo "Governance Worker Job Name: $GOVERNANCE_JOB_NAME"
  echo "Governance Worker Image: ${ACR_SERVER}/governance-worker:${GOVERNANCE_IMAGE_TAG}"
  echo "Governance Worker Env Vars (${#GOVERNANCE_CORE_ENV_VARS[@]} vars): ${GOVERNANCE_CORE_ENV_VARS[*]}"

  if az containerapp job show --name "$GOVERNANCE_JOB_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "Updating existing Governance Worker Container Apps Job..."
    az containerapp job update \
      --name "$GOVERNANCE_JOB_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --image "${ACR_SERVER}/governance-worker:${GOVERNANCE_IMAGE_TAG}" \
      --cpu 0.5 \
      --memory 1Gi \
      --set-env-vars "${GOVERNANCE_CORE_ENV_VARS[@]}"
  else
    echo "Creating new Governance Worker Container Apps Job..."
    az containerapp job create \
      --name "$GOVERNANCE_JOB_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --environment "$ENVIRONMENT_ID" \
      --image "${ACR_SERVER}/governance-worker:${GOVERNANCE_IMAGE_TAG}" \
      --cpu 0.5 \
      --memory 1Gi \
      --trigger-type Schedule \
      --cron-expression "0 */3 * * *" \
      --replica-timeout 1800 \
      --replica-retry-limit 1 \
      --parallelism 1 \
      --replica-completion-count 1 \
      --registry-server "$ACR_SERVER" \
      --mi-user-assigned "$GOVERNANCE_IDENTITY_RESOURCE_ID" \
      --registry-identity "$GOVERNANCE_IDENTITY_RESOURCE_ID" \
      --env-vars "${GOVERNANCE_CORE_ENV_VARS[@]}"
  fi

  echo "Governance Worker Job: $GOVERNANCE_JOB_NAME (cron: 0 */3 * * *)"
fi

echo ""
echo "============================================================================"
echo "Deployment Complete"
echo "============================================================================"
echo "Frontend: https://${FRONTEND_URL}"
echo "BFF: https://${BFF_URL}"
if [[ -n "$INDEXER_IMAGE_TAG" ]]; then
  echo "Indexer Job: ${INDEXER_JOB_NAME}"
fi
if [[ -n "$GOVERNANCE_IMAGE_TAG" ]]; then
  echo "Governance Worker Job: ${GOVERNANCE_JOB_NAME}"
fi
echo "============================================================================"
