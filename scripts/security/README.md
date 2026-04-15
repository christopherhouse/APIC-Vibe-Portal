# Security Scripts

This directory contains scripts for managing secrets and security operations for the APIC Vibe Portal.

## Scripts

### `rotate-service-principal.sh`

Rotates the client secret for an Azure AD service principal and stores the new secret in Azure Key Vault.

```bash
./rotate-service-principal.sh \
  --app-id <azure-ad-app-id> \
  --key-vault <vault-name> \
  --validity-days 90 \
  --secret-name sp-client-secret
```

**Prerequisites:**

- Azure CLI authenticated (`az login`)
- `Application.ReadWrite.All` permission on the service principal
- Key Vault `Secrets Officer` role on the target vault

### `rotate-api-keys.sh`

Rotates API keys for Azure services (OpenAI, AI Search, Cosmos DB) and stores them in Key Vault.

```bash
# Rotate a specific service
./rotate-api-keys.sh \
  --key-vault <vault-name> \
  --service openai \
  --resource-group <rg-name>

# Rotate all services
./rotate-api-keys.sh \
  --key-vault <vault-name> \
  --service all \
  --resource-group <rg-name>
```

**Supported services:** `openai`, `ai-search`, `cosmos-db`, `all`

## Rotation Policy

| Secret Type                      | Rotation Frequency | Automated       |
| -------------------------------- | ------------------ | --------------- |
| Service principal client secrets | 90 days            | Script-assisted |
| Azure OpenAI API keys            | 90 days            | Script-assisted |
| AI Search admin keys             | 90 days            | Script-assisted |
| Cosmos DB keys                   | 90 days            | Script-assisted |
| TLS certificates                 | 1 year             | Azure-managed   |

## Best Practices

1. **Use Managed Identity when possible** — eliminates the need for key rotation entirely.
2. **Store all secrets in Key Vault** — never in code, environment variables, or config files.
3. **Use Key Vault references** in Container Apps — secrets auto-refresh without restarts.
4. **Run rotation during low-traffic periods** to minimize impact.
5. **Verify service connectivity** after rotation completes.
6. **Keep at least one previous credential** active during rotation for zero-downtime.

## Manual Rotation (When Scripts Can't Be Used)

For secrets that cannot be rotated automatically:

1. Generate the new secret/key in the appropriate Azure portal.
2. Store the new value in Key Vault: `az keyvault secret set --vault-name <name> --name <secret-name> --value <value>`
3. Verify the application works with the new secret.
4. Revoke/delete the old secret after confirming.
5. Document the rotation in the team's operations log.
