# Threat Model Overview — APIC Vibe Portal AI

## Purpose

This document provides a high-level overview of the APIC Vibe Portal AI threat model. It identifies the primary attack surfaces, threat actors, and cross-cutting security controls. Detailed threat models for each component are linked below.

## Component Threat Models

| Component              | Document                                                 | Key Risks                                                                    |
| ---------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Frontend (Next.js SPA) | [frontend-threat-model.md](frontend-threat-model.md)     | XSS, CSRF, token theft, client-side data exposure                            |
| BFF (Python/FastAPI)   | [bff-threat-model.md](bff-threat-model.md)               | API abuse, injection, unauthorized access, token bypass                      |
| Agent & Data Paths     | [agent-data-threat-model.md](agent-data-threat-model.md) | Prompt injection, data poisoning, PII leakage, unauthorized agent invocation |

## Architecture Context

```
Browser ──► Next.js SPA ──► BFF (FastAPI) ──► Azure API Center
                                           ──► Azure AI Search
                                           ──► Foundry Agent Service
                                           ──► Azure Cosmos DB
                                           ──► Azure OpenAI
```

## Threat Actors

| Actor                    | Motivation                               | Capability                                     |
| ------------------------ | ---------------------------------------- | ---------------------------------------------- |
| External attacker        | Data theft, service disruption           | Network access, automated tooling              |
| Malicious insider        | Data exfiltration, privilege escalation  | Authenticated access, organizational knowledge |
| Automated bot            | API abuse, credential stuffing, scraping | High-volume requests, evasion techniques       |
| Compromised supply chain | Backdoor access, data theft              | Code execution via dependencies                |

## Trust Boundaries

1. **Internet ↔ Frontend** — Public-facing boundary; all client input is untrusted.
2. **Frontend ↔ BFF** — Authenticated boundary; requests must carry valid Entra ID tokens.
3. **BFF ↔ Azure Services** — Private boundary; BFF authenticates via Managed Identity.
4. **BFF ↔ Foundry Agents** — Internal boundary; agent invocations must be authorized and inputs sanitized.

## Cross-Cutting Security Controls

| Control               | Implementation                        | Status                    |
| --------------------- | ------------------------------------- | ------------------------- |
| Authentication        | Entra ID (Azure AD)                   | Planned (Task 008)        |
| Authorization         | RBAC + security trimming              | Planned (Task 020)        |
| Input validation      | Pydantic models (BFF), Zod (frontend) | This task                 |
| Rate limiting         | BFF middleware                        | This task                 |
| Bot detection         | BFF middleware                        | This task                 |
| Secret management     | Azure Key Vault + Managed Identity    | This task                 |
| SAST scanning         | GitHub CodeQL                         | This task                 |
| Dependency scanning   | Dependabot + npm/uv audit             | This task                 |
| Container scanning    | Trivy                                 | This task                 |
| Secret scanning       | GitHub Secret Scanning                | This task                 |
| Encryption in transit | TLS 1.2+ (Azure-managed)              | Infrastructure (Task 002) |
| Encryption at rest    | Azure-managed keys                    | Infrastructure (Task 002) |
| Logging & monitoring  | Application Insights                  | Planned (Task 019)        |

## Data Classification

| Data Type            | Classification | Storage                     | Protection                         |
| -------------------- | -------------- | --------------------------- | ---------------------------------- |
| API metadata         | Internal       | API Center, AI Search       | RBAC, security trimming            |
| User identity        | Confidential   | Entra ID tokens (transient) | Token encryption, secure cookies   |
| Chat sessions        | Internal       | Cosmos DB                   | Encryption at rest, RBAC           |
| Governance snapshots | Internal       | Cosmos DB                   | Encryption at rest, RBAC           |
| Analytics data       | Internal       | Cosmos DB                   | Encryption at rest, RBAC           |
| AI prompts/responses | Internal       | Transient (memory)          | No PII in logs, input sanitization |

## Compliance Considerations

- **Data residency**: All Azure resources deployed in configured region.
- **Access control**: Principle of least privilege enforced via RBAC.
- **Audit trail**: All authentication events logged to Application Insights.
- **Secret rotation**: 90-day rotation for service principals, 1-year for certificates.

## Review Schedule

This threat model should be reviewed:

- When new components or services are added
- When authentication or authorization mechanisms change
- When new data types are introduced
- At minimum, quarterly
