#!/usr/bin/env bash
# ==============================================================================
# Rotate Azure Service Principal Credentials
# ==============================================================================
# This script rotates the client secret for the APIC Vibe Portal service
# principal and updates the corresponding Azure Key Vault secret.
#
# Prerequisites:
#   - Azure CLI installed and authenticated (az login)
#   - Permissions to manage the service principal (Application.ReadWrite.All)
#   - Permissions to write secrets in the target Key Vault
#
# Usage:
#   ./rotate-service-principal.sh --app-id <app-id> --key-vault <vault-name>
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    echo "Usage: $0 --app-id <app-id> --key-vault <vault-name> [--validity-days <days>]"
    echo ""
    echo "Options:"
    echo "  --app-id          Azure AD Application (client) ID"
    echo "  --key-vault       Azure Key Vault name"
    echo "  --validity-days   Secret validity in days (default: 90)"
    echo "  --secret-name     Key Vault secret name (default: sp-client-secret)"
    echo "  --help            Show this help message"
    exit 1
}

APP_ID=""
KEY_VAULT=""
VALIDITY_DAYS=90
SECRET_NAME="sp-client-secret"

while [[ $# -gt 0 ]]; do
    case $1 in
        --app-id) APP_ID="$2"; shift 2 ;;
        --key-vault) KEY_VAULT="$2"; shift 2 ;;
        --validity-days) VALIDITY_DAYS="$2"; shift 2 ;;
        --secret-name) SECRET_NAME="$2"; shift 2 ;;
        --help) usage ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; usage ;;
    esac
done

if [[ -z "$APP_ID" || -z "$KEY_VAULT" ]]; then
    echo -e "${RED}Error: --app-id and --key-vault are required.${NC}"
    usage
fi

echo -e "${YELLOW}=== Service Principal Credential Rotation ===${NC}"
echo "App ID:        $APP_ID"
echo "Key Vault:     $KEY_VAULT"
echo "Validity:      $VALIDITY_DAYS days"
echo "Secret Name:   $SECRET_NAME"
echo ""

# Step 1: Create new credential
echo -e "${YELLOW}Step 1: Creating new client secret...${NC}"
END_DATE=$(date -u -d "+${VALIDITY_DAYS} days" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -v+${VALIDITY_DAYS}d '+%Y-%m-%dT%H:%M:%SZ')

NEW_SECRET=$(az ad app credential reset \
    --id "$APP_ID" \
    --end-date "$END_DATE" \
    --query password \
    --output tsv)

if [[ -z "$NEW_SECRET" ]]; then
    echo -e "${RED}Error: Failed to create new client secret.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ New client secret created (expires: $END_DATE)${NC}"

# Step 2: Store in Key Vault
echo -e "${YELLOW}Step 2: Storing new secret in Key Vault...${NC}"
az keyvault secret set \
    --vault-name "$KEY_VAULT" \
    --name "$SECRET_NAME" \
    --value "$NEW_SECRET" \
    --expires "$END_DATE" \
    --tags "rotated-on=$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "app-id=$APP_ID" \
    --output none

echo -e "${GREEN}✅ Secret stored in Key Vault as '$SECRET_NAME'${NC}"

# Step 3: Verify
echo -e "${YELLOW}Step 3: Verifying Key Vault secret...${NC}"
STORED=$(az keyvault secret show \
    --vault-name "$KEY_VAULT" \
    --name "$SECRET_NAME" \
    --query "attributes.expires" \
    --output tsv)

echo -e "${GREEN}✅ Verification complete. Secret expires: $STORED${NC}"

# Step 4: Clean up old credentials (keep current + 1 previous)
echo -e "${YELLOW}Step 4: Cleaning up old credentials...${NC}"
OLD_KEYS=$(az ad app credential list --id "$APP_ID" --query "[].keyId" -o tsv | tail -n +3)
for KEY_ID in $OLD_KEYS; do
    echo "  Removing old credential: $KEY_ID"
    az ad app credential delete --id "$APP_ID" --key-id "$KEY_ID" 2>/dev/null || true
done
echo -e "${GREEN}✅ Old credentials cleaned up${NC}"

echo ""
echo -e "${GREEN}=== Rotation Complete ===${NC}"
echo "NOTE: If Container Apps use this secret, they will pick up the new"
echo "value automatically via Key Vault reference on next restart."
echo "To force immediate update, restart the Container Apps."
