# APIC Vibe Portal AI — Wiki

Welcome to the **APIC Vibe Portal AI** wiki — the central hub for project documentation.

## What Is This?

An **AI-powered API portal** built on Azure services. Developers can discover, understand, and use APIs faster through multi-agent AI assistance — natural language search, AI chat, governance insights, and API comparison.

## Quick Navigation

| Page                        | Description                                                 |
| --------------------------- | ----------------------------------------------------------- |
| [[Architecture]]            | System design, components, data flow, and key decisions     |
| [[Getting Started]]         | Prerequisites and local development setup                   |
| [[CI-CD Pipeline]]          | GitHub Actions workflows, environments, and deployment      |
| [[Authentication and RBAC]] | Entra ID setup, app roles, and route protection             |
| [[Security]]                | Threat model overview, data classification, and controls    |
| [[Implementation Plan]]     | Phased roadmap and task status (Sprint Zero → Phase 3)      |
| [[Data Architecture]]       | Cosmos DB strategy, retention, PII handling, and indexing   |
| [[Caching]]                 | Azure Cache for Redis — TTLs, authentication, and fallback  |
| [[Runtime Configuration]]   | Environment-based MSAL config (build-once, deploy-anywhere) |
| [[Load Testing]]            | Azure Load Testing / JMeter setup                           |
| [[Contributing]]            | Branch strategy, coding conventions, and quality gates      |

## Tech Stack at a Glance

| Layer         | Technology                                                      |
| ------------- | --------------------------------------------------------------- |
| Frontend      | Next.js 16 (App Router) · React 19 · TypeScript 6 · Material UI |
| BFF           | Python 3.14 · FastAPI · UV package manager                      |
| AI            | Azure OpenAI · Foundry Agent Service (multi-agent)              |
| Search        | Azure AI Search (hybrid + semantic ranking)                     |
| API Catalog   | Azure API Center                                                |
| Persistence   | Azure Cosmos DB (serverless)                                    |
| Cache         | Azure Cache for Redis                                           |
| Observability | Azure Application Insights                                      |
| Hosting       | Azure Container Apps · Azure Container Registry                 |
| Security      | Entra ID · RBAC · Azure Key Vault · Managed Identity            |

## Implementation Status

| Phase                        | Scope                                          | Status         |
| ---------------------------- | ---------------------------------------------- | -------------- |
| Sprint Zero (001–004)        | Repo, infra, CI/CD, security baseline          | ✅ Complete    |
| Phase 1 MVP (005–021)        | Catalog, search, AI chat, auth, observability  | ✅ Complete    |
| Phase 2 Governance (022–027) | Multi-agent, governance dashboard, API compare | 🔄 In Progress |
| Phase 3 Analytics (028–032)  | Usage analytics, metadata scoring, launch      | 🔲 Not Started |

> For the detailed task-by-task breakdown, see [[Implementation Plan]].

---

_Built with ❤️ using Azure AI services._
