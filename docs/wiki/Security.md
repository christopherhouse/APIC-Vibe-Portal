# Security

## Overview

Security is layered across the entire stack: Entra ID for authentication, RBAC for authorization, Managed Identity for secrets, and multiple scanning tools in CI/CD.

## Trust Boundaries

```
Internet ──► Frontend (Next.js)   — Public-facing; all input untrusted
   │
   ▼
Frontend ──► BFF (FastAPI)        — Authenticated; valid Entra JWT required
   │
   ▼
BFF ──► Azure Services            — Private; Managed Identity (UAMI) only
   │
   ▼
BFF ──► Foundry Agents            — Internal; inputs sanitized; auth enforced
```

## Threat Model

Three component-level threat models cover the full attack surface:

| Component              | Document                                   | Key Risks                                                                    |
| ---------------------- | ------------------------------------------ | ---------------------------------------------------------------------------- |
| Frontend (Next.js SPA) | `docs/security/frontend-threat-model.md`   | XSS, CSRF, token theft, client-side data exposure                            |
| BFF (Python/FastAPI)   | `docs/security/bff-threat-model.md`        | API abuse, injection, unauthorized access, token bypass                      |
| Agent & Data Paths     | `docs/security/agent-data-threat-model.md` | Prompt injection, data poisoning, PII leakage, unauthorized agent invocation |

See `docs/security/threat-model-overview.md` for the cross-cutting overview.

## Threat Actors

| Actor                    | Motivation                               | Capability                          |
| ------------------------ | ---------------------------------------- | ----------------------------------- |
| External attacker        | Data theft, service disruption           | Network access, automated tooling   |
| Malicious insider        | Data exfiltration, privilege escalation  | Authenticated access, org knowledge |
| Automated bot            | API abuse, credential stuffing, scraping | High-volume requests, evasion       |
| Compromised supply chain | Backdoor, data theft                     | Code execution via dependencies     |

## Security Controls

| Control               | Implementation                        | Where                                      |
| --------------------- | ------------------------------------- | ------------------------------------------ |
| Authentication        | Entra ID JWTs                         | BFF middleware                             |
| Authorization         | RBAC App Roles                        | BFF `require_role()`, frontend `AuthGuard` |
| Input validation      | Pydantic (BFF), Zod (frontend)        | Request handling                           |
| Rate limiting         | BFF middleware                        | All API routes                             |
| Secret management     | Azure Key Vault + Managed Identity    | No embedded secrets                        |
| SAST                  | GitHub CodeQL                         | CI/CD                                      |
| Dependency scanning   | Dependabot + `npm audit` + `uv audit` | CI/CD                                      |
| Container scanning    | Trivy                                 | CI/CD                                      |
| Secret scanning       | GitHub Secret Scanning                | Repository-level                           |
| Encryption in transit | TLS 1.2+                              | Azure-managed (Container Apps)             |
| Encryption at rest    | Azure-managed keys                    | All storage services                       |
| Observability         | Application Insights                  | All containers                             |

## Identity — User-Assigned Managed Identities

Each Container App has its own UAMI (least-privilege):

| UAMI                                             | Permissions                                                                                  |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Frontend (`{prefix}-id-frontend-{env}-{suffix}`) | AcrPull on ACR only                                                                          |
| BFF (`{prefix}-id-bff-{env}-{suffix}`)           | AcrPull on ACR + RBAC on Key Vault, API Center, AI Search, OpenAI, Cosmos DB, Foundry, Redis |

**Redis authentication**: Entra MI tokens only. Access keys are disabled (`disableAccessKeyAuthentication: true`).

## Data Classification

| Data Type            | Classification | Storage                     | Protection                         |
| -------------------- | -------------- | --------------------------- | ---------------------------------- |
| API metadata         | Internal       | API Center, AI Search       | RBAC, security trimming            |
| User identity        | Confidential   | Entra ID tokens (transient) | Token encryption, secure cookies   |
| Chat sessions        | Internal       | Cosmos DB                   | Encryption at rest, RBAC           |
| Governance snapshots | Internal       | Cosmos DB                   | Encryption at rest, RBAC           |
| Analytics data       | Internal       | Cosmos DB                   | Encryption at rest, RBAC           |
| AI prompts/responses | Internal       | Transient (memory only)     | No PII in logs, input sanitization |

## Compliance

- **Data residency**: All Azure resources in configured region
- **Principle of least privilege**: Enforced via RBAC and UAMI
- **Audit trail**: All auth events logged to Application Insights
- **Secret rotation**: 90-day rotation for service principals, 1-year for certificates
- **Soft delete**: All Cosmos DB data classes support soft delete before purge

## Security Policy

See `docs/security/security-policy.md` for the full security policy.

See `docs/security/incident-response.md` for the incident response playbook.

See `SECURITY.md` in the repository root for vulnerability disclosure.

## Secure Coding Guidelines

See `docs/security/secure-coding-guidelines.md` for language-specific guidelines (Python, TypeScript).

Key rules:

- Never commit secrets or credentials
- Validate all inputs (Pydantic models in BFF, Zod in frontend)
- Sanitize AI prompts before sending to agents
- Use parameterized queries for any database operations
- Never log PII or secrets

## Related

- [[Authentication and RBAC]] — Entra ID and role setup
- [[Architecture]] — Security model and UAMI details
- [[Data Architecture]] — PII handling and data retention
