# Security Policy — APIC Vibe Portal AI

## Overview

This document defines the security policies and standards for the APIC Vibe Portal AI project. All contributors and maintainers must follow these policies.

## Authentication & Authorization

### Authentication

- All user authentication is handled via **Azure Entra ID** (Azure AD).
- The frontend uses **MSAL.js** for authentication flows.
- The BFF validates **JWT bearer tokens** from Entra ID.
- Service-to-service authentication uses **Managed Identity**.

### Authorization

- **RBAC** (Role-Based Access Control) is enforced at the BFF layer.
- **Security trimming** ensures users only see data they are authorized to access.
- API Center data access is filtered by user roles and group memberships.

## Secrets Management

### Requirements

- All secrets **must** be stored in Azure Key Vault.
- Application code **must never** contain hardcoded secrets.
- Environment variables for secrets are only permitted in local development (`.env.local`).
- Production applications access secrets via Managed Identity → Key Vault references.

### Rotation

- Service principal secrets: Rotate every **90 days**.
- API keys: Rotate every **90 days**.
- TLS certificates: Rotate every **1 year** (Azure-managed).
- See `scripts/security/` for rotation automation.

## Data Protection

### Classification

| Level        | Description                         | Examples                                          |
| ------------ | ----------------------------------- | ------------------------------------------------- |
| Critical     | System credentials, encryption keys | Managed Identity tokens, Key Vault secrets        |
| Confidential | User identity, PII                  | Email addresses, display names, auth tokens       |
| Internal     | Business data                       | API metadata, governance snapshots, chat sessions |
| Public       | Non-sensitive data                  | Public API documentation                          |

### Handling Rules

- **Critical**: Key Vault only; never logged; encrypted at rest and in transit.
- **Confidential**: Minimize storage; never in logs; encrypt at rest.
- **Internal**: Standard Azure encryption; access controlled via RBAC.
- **Public**: No special handling required.

## Logging & Monitoring

- **Never log**: Tokens, passwords, API keys, PII (email, names).
- **Always log**: Authentication events, authorization failures, rate limit triggers.
- All logs are sent to **Azure Application Insights** and **Log Analytics**.
- Security events trigger alerts via Azure Monitor.

## Dependency Management

- Dependencies are audited weekly via **Dependabot** and CI scans.
- **Critical/High** vulnerabilities must be addressed within **7 days**.
- **Medium** vulnerabilities must be addressed within **30 days**.
- All dependency updates require CI pipeline approval.

## Network Security

- All communications use **TLS 1.2+**.
- Azure services communicate over **private endpoints** where possible.
- **CORS** is managed at the Azure Container Apps level (not in application code).
- Rate limiting is enforced at the BFF layer.

## Incident Response

See [incident-response.md](incident-response.md) for the full incident response plan.
