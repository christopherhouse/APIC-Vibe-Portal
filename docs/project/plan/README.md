# APIC Vibe Portal AI — Implementation Plan

## Overview
This directory contains the phased implementation plan for the APIC Vibe Portal AI — a next-generation, AI-powered API portal built on Azure API Center, Azure AI Search, Azure OpenAI, Foundry Agent Service, and Azure Container Apps.

The plan is organized into **30 sequential tasks** across **4 phases**, from initial scaffolding through to launch readiness. Each task document includes implementation details, testing criteria, and a ready-to-use prompt for coding agents.

## Source Documents
| Document | Description |
|----------|-------------|
| [Product Charter](../apic_product_charter.md) | Purpose, vision, goals, scope, and phased timeline |
| [Architecture Document](../apic_architecture.md) | Components, key decisions, security, and deployment |
| [Product Spec](../apic_portal_spec.md) | Feature specifications |

---

## Phase Summary

### 🏗️ Sprint Zero — Foundation (Tasks 001–003)
Establish the repository, infrastructure, and CI/CD pipeline that all subsequent work builds upon.

### 🚀 Phase 1 — MVP (Tasks 004–019)
Deliver the core API portal: catalog browsing, search, AI chat, authentication, and observability.

### 🔍 Phase 2 — Governance + Compare (Tasks 020–025)
Add multi-agent intelligence, governance dashboards, and API comparison features.

### 📊 Phase 3 — Analytics & Polish (Tasks 026–030)
Complete usage analytics, metadata scoring, performance optimization, and launch preparation.

---

## Task Index

### Sprint Zero — Foundation
| # | Task | Key Dependencies |
|---|------|-----------------|
| [001](001-sprint-zero-repo-scaffolding.md) | Repository Scaffolding & GitHub Copilot Assets | — |
| [002](002-sprint-zero-azure-infra-bicep.md) | Azure Infrastructure as Code (Bicep) | 001 |
| [003](003-sprint-zero-cicd-pipeline.md) | CI/CD Pipeline with GitHub Actions | 001, 002 |

### Phase 1 — MVP
| # | Task | Key Dependencies |
|---|------|-----------------|
| [004](004-frontend-nextjs-setup.md) | Next.js Frontend Project Setup | 001 |
| [005](005-bff-api-setup.md) | BFF API Project Setup | 001 |
| [006](006-shared-types-package.md) | Shared Types & Utilities Package | 001, 004, 005 |
| [007](007-api-center-data-layer.md) | Azure API Center Data Layer Integration | 002, 005, 006 |
| [008](008-bff-api-catalog-endpoints.md) | BFF API Catalog Endpoints | 005, 006, 007 |
| [009](009-frontend-api-catalog-page.md) | API Catalog Listing Page (Frontend) | 004, 006, 008 |
| [010](010-frontend-api-detail-page.md) | API Detail View Page (Frontend) | 004, 006, 008, 009 |
| [011](011-ai-search-index-setup.md) | Azure AI Search Index Setup & Indexing Pipeline | 002, 005, 007 |
| [012](012-search-api-implementation.md) | Search API Implementation (BFF) | 005, 006, 011 |
| [013](013-frontend-search-ui.md) | Search UI (Frontend) | 004, 006, 012 |
| [014](014-openai-integration.md) | Azure OpenAI Service Integration (BFF) | 002, 005, 006, 011 |
| [015](015-frontend-chat-ui.md) | AI Chat Interface (Frontend) | 004, 006, 014 |
| [016](016-entra-id-authentication.md) | Entra ID Authentication Integration | 002, 004, 005 |
| [017](017-observability-app-insights.md) | Application Insights Observability | 002, 004, 005 |
| [018](018-security-trimming.md) | Security Trimming Implementation | 007, 012, 014, 016 |
| [019](019-e2e-testing-mvp-polish.md) | End-to-End Integration Testing & MVP Polish | 001–018 |

### Phase 2 — Governance + Compare
| # | Task | Key Dependencies |
|---|------|-----------------|
| [020](020-foundry-agent-setup.md) | Foundry Agent Service Setup & First Agent | 002, 005, 014 |
| [021](021-governance-agent.md) | Governance & Compliance Agent | 020, 007 |
| [022](022-api-comparison-feature.md) | API Comparison Feature | 007, 008, 010, 020 |
| [023](023-governance-dashboard-ui.md) | Governance Dashboard UI | 004, 021, 008 |
| [024](024-multi-agent-orchestration.md) | Multi-Agent Orchestration & Agent Management | 020, 021, 016 |
| [025](025-phase2-integration-testing.md) | Phase 2 Integration Testing & Polish | 019, 020–024 |

### Phase 3 — Analytics & Polish
| # | Task | Key Dependencies |
|---|------|-----------------|
| [026](026-analytics-data-collection.md) | Usage Analytics Data Collection | 017, 005, 016 |
| [027](027-analytics-dashboard.md) | Analytics Dashboard | 004, 026, 016 |
| [028](028-metadata-completeness.md) | Metadata Completeness Scoring & Recommendations | 007, 021, 014 |
| [029](029-performance-accessibility.md) | Performance Optimization & Accessibility | All previous |
| [030](030-final-integration-launch.md) | Final Integration Testing, Documentation & Launch Readiness | All previous |

---

## Dependency Graph

```
001 ─┬─ 002 ─── 003
     │       ╲
     ├─ 004   ╲──────────────────────── 016, 017
     │    ╲
     ├─ 005 ─── 006 ─── 007 ─── 008 ─── 009 ─── 010
     │                ╲           ╲
     │                 ╲── 011 ── 012 ─── 013
     │                       ╲
     │                        ╲── 014 ─── 015
     │
     └── 018 (requires 007, 012, 014, 016)
              ╲
               ╲── 019 (MVP complete)
                     ╲
                      020 ─── 021 ─── 023
                        ╲              ╲
                         ╲── 022       024
                              ╲       ╱
                               ╲── 025 (Phase 2 complete)
                                     ╲
                                      026 ─── 027
                                        ╲
                                         028
                                           ╲
                                            029 ─── 030 (Launch ready)
```

---

## How to Use This Plan

### For Project Managers
1. Use this index to track progress across all 30 tasks
2. Respect the dependency order — tasks cannot begin until their dependencies are complete
3. Within a phase, independent tasks can run in parallel (e.g., 004 and 005; 009 and 011)

### For Developers
1. Read the task document for your assigned step
2. Review the referenced source documents for context
3. Use the **Coding Agent Prompt** at the bottom of each task to bootstrap implementation
4. Follow the **Testing & Acceptance Criteria** to validate your work

### For Coding Agents
1. You will receive a prompt referencing a specific task document
2. Read the full task specification at the referenced path
3. Implement the described features, following the detailed specifications
4. Validate against the acceptance criteria before marking complete

---

## Parallel Execution Opportunities

Within the dependency constraints, certain tasks can be executed in parallel:

| Parallel Group | Tasks | Notes |
|---------------|-------|-------|
| Sprint Zero | 004, 005 (after 001) | Frontend and BFF setup can happen simultaneously |
| Data Layer | 007, 011 (after 005, 006) | API Center and AI Search setup are independent |
| Frontend Pages | 009, 010 (after 008) | Catalog and detail pages can be built together |
| Search + Chat | 012/013, 014/015 (after 011) | Search and chat paths are independent |
| Cross-cutting | 016, 017 (after 004, 005) | Auth and observability are independent |
| Phase 2 Features | 021, 022 (after 020) | Governance and comparison are independent |
| Phase 3 Features | 026/027, 028 (after dependencies) | Analytics and metadata scoring are independent |
