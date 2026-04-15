#!/usr/bin/env bash
# ==============================================================================
# Rotate API Keys for External Services
# ==============================================================================
# This script rotates API keys stored in Azure Key Vault for external services
# used by the APIC Vibe Portal (e.g., Azure OpenAI, AI Search).
#
# Prerequisites:
#   - Azure CLI installed and authenticated (az login)
#   - Permissions to manage the relevant Azure services
#   - Permissions to write secrets in the target Key Vault
#
# Usage:
#   ./rotate-api-keys.sh --key-vault <vault-name> --service <service-name>
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    echo "Usage: $0 --key-vault <vault-name> --service <service-name> [options]"
    echo ""
    echo "Services:"
    echo "  openai          Rotate Azure OpenAI API key"
    echo "  ai-search       Rotate Azure AI Search admin key"
    echo "  cosmos-db       Rotate Cosmos DB primary key"
    echo "  all             Rotate all service keys"
    echo ""
    echo "Options:"
    echo "  --key-vault          Azure Key Vault name"
    echo "  --service            Service to rotate (see above)"
    echo "  --resource-group     Azure resource group name"
    echo "  --help               Show this help message"
    exit 1
}

KEY_VAULT=""
SERVICE=""
RESOURCE_GROUP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --key-vault) KEY_VAULT="$2"; shift 2 ;;
        --service) SERVICE="$2"; shift 2 ;;
        --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
        --help) usage ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; usage ;;
    esac
done

if [[ -z "$KEY_VAULT" || -z "$SERVICE" ]]; then
    echo -e "${RED}Error: --key-vault and --service are required.${NC}"
    usage
fi

store_in_keyvault() {
    local name="$1"
    local value="$2"
    local tags="$3"

    az keyvault secret set \
        --vault-name "$KEY_VAULT" \
        --name "$name" \
        --value "$value" \
        --tags "rotated-on=$(date -u '+%Y-%m-%dT%H:%M:%SZ')" $tags \
        --output none

    echo -e "${GREEN}  ✅ Stored as '$name' in Key Vault${NC}"
}

rotate_openai() {
    echo -e "${YELLOW}Rotating Azure OpenAI API key...${NC}"
    local account_name
    account_name=$(az cognitiveservices account list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?kind=='OpenAI'].name | [0]" -o tsv)

    if [[ -z "$account_name" ]]; then
        echo -e "${RED}Error: No OpenAI account found in resource group $RESOURCE_GROUP${NC}"
        return 1
    fi

    az cognitiveservices account keys regenerate \
        --name "$account_name" \
        --resource-group "$RESOURCE_GROUP" \
        --key-name key1 \
        --output none

    local new_key
    new_key=$(az cognitiveservices account keys list \
        --name "$account_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "key1" -o tsv)

    store_in_keyvault "openai-api-key" "$new_key" "service=openai"
    echo -e "${GREEN}✅ Azure OpenAI key rotated${NC}"
}

rotate_ai_search() {
    echo -e "${YELLOW}Rotating Azure AI Search admin key...${NC}"
    local search_name
    search_name=$(az search service list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[0].name" -o tsv)

    if [[ -z "$search_name" ]]; then
        echo -e "${RED}Error: No AI Search service found in resource group $RESOURCE_GROUP${NC}"
        return 1
    fi

    az search admin-key renew \
        --service-name "$search_name" \
        --resource-group "$RESOURCE_GROUP" \
        --key-type primary \
        --output none

    local new_key
    new_key=$(az search admin-key show \
        --service-name "$search_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "primaryKey" -o tsv)

    store_in_keyvault "ai-search-admin-key" "$new_key" "service=ai-search"
    echo -e "${GREEN}✅ AI Search admin key rotated${NC}"
}

rotate_cosmos_db() {
    echo -e "${YELLOW}Rotating Cosmos DB primary key...${NC}"
    local account_name
    account_name=$(az cosmosdb list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[0].name" -o tsv)

    if [[ -z "$account_name" ]]; then
        echo -e "${RED}Error: No Cosmos DB account found in resource group $RESOURCE_GROUP${NC}"
        return 1
    fi

    az cosmosdb keys regenerate \
        --name "$account_name" \
        --resource-group "$RESOURCE_GROUP" \
        --key-kind primary \
        --output none

    local new_key
    new_key=$(az cosmosdb keys list \
        --name "$account_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "primaryMasterKey" -o tsv)

    store_in_keyvault "cosmos-db-primary-key" "$new_key" "service=cosmos-db"
    echo -e "${GREEN}✅ Cosmos DB primary key rotated${NC}"
}

echo -e "${YELLOW}=== API Key Rotation ===${NC}"
echo "Key Vault:       $KEY_VAULT"
echo "Service:         $SERVICE"
echo "Resource Group:  $RESOURCE_GROUP"
echo ""

case "$SERVICE" in
    openai)     rotate_openai ;;
    ai-search)  rotate_ai_search ;;
    cosmos-db)  rotate_cosmos_db ;;
    all)
        rotate_openai
        rotate_ai_search
        rotate_cosmos_db
        ;;
    *)
        echo -e "${RED}Unknown service: $SERVICE${NC}"
        usage
        ;;
esac

echo ""
echo -e "${GREEN}=== Key Rotation Complete ===${NC}"
echo "NOTE: Services using Managed Identity are not affected by key rotation."
echo "      Key Vault references in Container Apps will auto-refresh."
