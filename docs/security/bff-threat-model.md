# BFF Threat Model — APIC Vibe Portal AI

## Component Overview
The Backend-for-Frontend (BFF) is a Python 3.14 FastAPI application that acts as an orchestration layer between the frontend SPA and Azure backend services (API Center, AI Search, OpenAI, Foundry Agent Service, Cosmos DB). It authenticates users via Entra ID token validation and accesses Azure services via Managed Identity.

## Assets
| Asset | Description | Sensitivity |
|-------|-------------|-------------|
| Entra ID tokens | User access tokens validated by BFF | High |
| Azure service credentials | Managed Identity credentials | Critical |
| API catalog data | Data from Azure API Center | Medium |
| Search index data | AI Search query results | Medium |
| Chat session data | Stored in Cosmos DB | Medium |
| Key Vault secrets | Application secrets | Critical |
| User PII | Names, email from token claims | High |

## Threat Analysis

### T-BFF-01: API Abuse / Denial of Service
- **Attack vector**: Attacker floods the BFF with requests to exhaust resources or increase Azure costs.
- **Impact**: Service degradation, increased costs, resource exhaustion.
- **Likelihood**: High
- **Mitigations**:
  - Rate limiting middleware (per-user and per-IP).
  - Bot detection middleware.
  - Azure Container Apps scaling limits.
  - Request timeout configuration.
  - Return 429 Too Many Requests with Retry-After header.
- **Residual risk**: Medium — Sophisticated distributed attacks may bypass per-IP limits.

### T-BFF-02: Injection Attacks (SQL, NoSQL, Command)
- **Attack vector**: Malicious input in query parameters, request bodies, or headers that gets passed to backend services.
- **Impact**: Data exfiltration, unauthorized data modification, command execution.
- **Likelihood**: Medium
- **Mitigations**:
  - Pydantic models for all request validation.
  - Parameterized queries for Cosmos DB.
  - Input sanitization middleware.
  - Never construct queries from raw user input.
  - Use Azure SDK methods (not raw REST) for service calls.
- **Residual risk**: Low — Pydantic validation and parameterized queries are effective.

### T-BFF-03: Token Validation Bypass
- **Attack vector**: Attacker presents a forged, expired, or stolen token to access BFF endpoints.
- **Impact**: Unauthorized access to user data and API operations.
- **Likelihood**: Medium
- **Mitigations**:
  - Validate token signature against Entra ID JWKS endpoint.
  - Check token expiration, issuer, audience claims.
  - Reject tokens with unexpected scopes or roles.
  - Implement token revocation checking.
- **Residual risk**: Low — Standard OIDC token validation is robust.

### T-BFF-04: Unauthorized Data Access
- **Attack vector**: Authenticated user accesses data belonging to other users or exceeds their authorization level.
- **Impact**: Data breach, privacy violation.
- **Likelihood**: Medium
- **Mitigations**:
  - Security trimming on all data queries (Task 020).
  - RBAC enforcement at the BFF layer.
  - Audit logging of data access.
  - Never trust client-provided user IDs for authorization decisions.
- **Residual risk**: Low — With proper security trimming implementation.

### T-BFF-05: Information Leakage via Error Responses
- **Attack vector**: Detailed error messages or stack traces reveal internal implementation details.
- **Impact**: Reconnaissance for further attacks.
- **Likelihood**: Medium
- **Mitigations**:
  - Generic error responses in production (no stack traces).
  - Structured logging with sensitive data redaction.
  - Different error detail levels for dev vs. production.
  - Never log tokens, passwords, or PII.
- **Residual risk**: Low

### T-BFF-06: Server-Side Request Forgery (SSRF)
- **Attack vector**: Attacker manipulates BFF to make requests to internal or unintended services.
- **Impact**: Access to internal services, metadata endpoints, or other Azure resources.
- **Likelihood**: Low
- **Mitigations**:
  - Hardcode all Azure service endpoints (no user-controlled URLs).
  - Use Azure SDK with managed identity (not raw HTTP).
  - Validate and restrict any user-provided URIs.
- **Residual risk**: Low — BFF only connects to known Azure services.

### T-BFF-07: Dependency Vulnerability
- **Attack vector**: Known vulnerability in a Python dependency is exploited.
- **Impact**: Varies (RCE, data breach, DoS).
- **Likelihood**: Medium
- **Mitigations**:
  - `uv audit` in CI pipeline (via pip-audit).
  - Dependabot for Python dependency alerts.
  - Pin dependency versions via `uv.lock`.
  - Regular dependency updates.
- **Residual risk**: Low — Automated scanning and lock files reduce risk.

### T-BFF-08: Secret Exposure
- **Attack vector**: Secrets (API keys, connection strings) exposed in code, logs, or environment variables.
- **Impact**: Unauthorized access to Azure services.
- **Likelihood**: Medium
- **Mitigations**:
  - All secrets stored in Azure Key Vault.
  - Managed Identity for Key Vault access.
  - GitHub Secret Scanning in CI.
  - `.gitignore` excludes `.env` files.
  - Secret rotation policy.
- **Residual risk**: Low — Key Vault + Managed Identity eliminates most exposure vectors.

## Security Controls Summary
| Control | Status |
|---------|--------|
| Rate limiting middleware | This task |
| Bot detection middleware | This task |
| Input validation middleware | This task |
| Pydantic request models | Planned (Task 006) |
| Entra ID token validation | Planned (Task 008) |
| Security trimming | Planned (Task 020) |
| Key Vault integration | This task |
| CodeQL SAST | This task |
| Dependency scanning | This task |
| Container scanning | This task |
