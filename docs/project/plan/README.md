# APIC Vibe Portal AI — Implementation Plan

## Overview

This directory contains the phased implementation plan for the APIC Vibe Portal AI — a next-generation, AI-powered API portal built on Azure API Center, Azure AI Search, Azure OpenAI, Foundry Agent Service, and Azure Container Apps.

The plan is organized into **32 sequential tasks** across **4 phases**, from initial scaffolding through to launch readiness. Each task document includes implementation details, testing criteria, and a ready-to-use prompt for coding agents.

> **📋 These are living documents.** Each task document tracks its own status and is updated with implementation notes, technical decisions, and validation results as work progresses. Check the status column below or the status banner at the top of each task document for current progress.

## Source Documents

| Document                                         | Description                                         |
| ------------------------------------------------ | --------------------------------------------------- |
| [Product Charter](../apic_product_charter.md)    | Purpose, vision, goals, scope, and phased timeline  |
| [Architecture Document](../apic_architecture.md) | Components, key decisions, security, and deployment |
| [Product Spec](../apic_portal_spec.md)           | Feature specifications                              |

---

## Phase Summary

### 🏗️ Sprint Zero — Foundation (Tasks 001–003)

Establish the repository, infrastructure, and CI/CD pipeline that all subsequent work builds upon.

### 🚀 Phase 1 — MVP (Tasks 004–021)

Deliver the core API portal: catalog browsing, search, AI chat, authentication, and observability.

### 🔍 Phase 2 — Governance + Compare (Tasks 022–027)

Add multi-agent intelligence, governance dashboards, and API comparison features.

### 📊 Phase 3 — Analytics & Polish (Tasks 028–032)

Complete usage analytics, metadata scoring, performance optimization, and launch preparation.

---

## Task Index

### Status Legend

| Icon | Meaning     |
| ---- | ----------- |
| 🔲   | Not Started |
| 🔄   | In Progress |
| ✅   | Complete    |
| ⚠️   | Blocked     |

### Sprint Zero — Foundation

| #                                                    | Task                                           | Status | Key Dependencies |
| ---------------------------------------------------- | ---------------------------------------------- | ------ | ---------------- |
| [001](001-sprint-zero-repo-scaffolding.md)           | Repository Scaffolding & GitHub Copilot Assets | ✅     | —                |
| [002](002-sprint-zero-azure-infra-bicep.md)          | Azure Infrastructure as Code (Bicep)           | ✅     | 001              |
| [003](003-sprint-zero-cicd-pipeline.md)              | CI/CD Pipeline with GitHub Actions             | ✅     | 001, 002         |
| [004](004-security-baseline-secure-sdlc-controls.md) | Security Baseline & Secure SDLC Controls       | ✅     | 001, 002, 003    |

### Phase 1 — MVP

| #                                                  | Task                                            | Status | Key Dependencies             |
| -------------------------------------------------- | ----------------------------------------------- | ------ | ---------------------------- |
| [005](005-frontend-nextjs-setup.md)                | Next.js Frontend Project Setup                  | ✅     | 001, 004                     |
| [006](006-bff-api-setup.md)                        | BFF API Project Setup                           | ✅     | 001, 004                     |
| [007](007-shared-types-package.md)                 | Shared Types & Utilities Package                | ✅     | 001, 005, 006                |
| [008](008-entra-id-authentication.md)              | Entra ID Authentication Integration             | 🔲     | 002, 005, 006                |
| [009](009-api-center-data-layer.md)                | Azure API Center Data Layer Integration         | 🔲     | 002, 006, 007                |
| [010](010-bff-api-catalog-endpoints.md)            | BFF API Catalog Endpoints                       | 🔲     | 006, 007, 009                |
| [011](011-frontend-api-catalog-page.md)            | API Catalog Listing Page (Frontend)             | 🔲     | 005, 007, 010                |
| [012](012-frontend-api-detail-page.md)             | API Detail View Page (Frontend)                 | 🔲     | 005, 007, 010, 011           |
| [013](013-ai-search-index-setup.md)                | Azure AI Search Index Setup & Indexing Pipeline | 🔲     | 002, 006, 009                |
| [014](014-search-api-implementation.md)            | Search API Implementation (BFF)                 | 🔲     | 006, 007, 013                |
| [015](015-frontend-search-ui.md)                   | Search UI (Frontend)                            | 🔲     | 005, 007, 014                |
| [016](016-persistence-data-governance-baseline.md) | Persistence & Data Governance Baseline          | 🔲     | 002, 006, 007, 008, 013, 014 |
| [017](017-openai-integration.md)                   | Azure OpenAI Service Integration (BFF)          | 🔲     | 002, 006, 007, 013, 014      |
| [018](018-frontend-chat-ui.md)                     | AI Chat Interface (Frontend)                    | 🔲     | 005, 007, 017                |
| [019](019-observability-app-insights.md)           | Application Insights Observability              | 🔲     | 002, 005, 006                |
| [020](020-security-trimming.md)                    | Security Trimming Implementation                | 🔲     | 009, 014, 017, 008           |
| [021](021-e2e-testing-mvp-polish.md)               | End-to-End Integration Testing & MVP Polish     | 🔲     | 001–020                      |

### Phase 2 — Governance + Compare

| #                                        | Task                                         | Status | Key Dependencies        |
| ---------------------------------------- | -------------------------------------------- | ------ | ----------------------- |
| [022](022-foundry-agent-setup.md)        | Foundry Agent Service Setup & First Agent    | 🔲     | 002, 006, 017, 014, 020 |
| [023](023-governance-agent.md)           | Governance & Compliance Agent                | 🔲     | 022, 009                |
| [024](024-api-comparison-feature.md)     | API Comparison Feature                       | 🔲     | 009, 010, 012, 022, 023 |
| [025](025-governance-dashboard-ui.md)    | Governance Dashboard UI                      | 🔲     | 005, 023, 010, 008, 020 |
| [026](026-multi-agent-orchestration.md)  | Multi-Agent Orchestration & Agent Management | 🔲     | 022, 023, 008           |
| [027](027-phase2-integration-testing.md) | Phase 2 Integration Testing & Polish         | 🔲     | 021, 022–026            |

### Phase 3 — Analytics & Polish

| #                                       | Task                                                        | Status | Key Dependencies        |
| --------------------------------------- | ----------------------------------------------------------- | ------ | ----------------------- |
| [028](028-analytics-data-collection.md) | Usage Analytics Data Collection                             | 🔲     | 019, 006, 008           |
| [029](029-analytics-dashboard.md)       | Analytics Dashboard                                         | 🔲     | 005, 028, 008           |
| [030](030-metadata-completeness.md)     | Metadata Completeness Scoring & Recommendations             | 🔲     | 009, 023, 017, 012, 025 |
| [031](031-performance-accessibility.md) | Performance Optimization & Accessibility                    | 🔲     | All previous            |
| [032](032-final-integration-launch.md)  | Final Integration Testing, Documentation & Launch Readiness | 🔲     | All previous            |

---

## Dependency Graph

```
001 ─┬─ 002 ─── 003
     │       ╲
     │        ╲─── 004 (Security Baseline)
     │              ╲
     ├─ 005          ╲──────────────────────── 008 (Entra ID Auth), 019
     │    ╲
     ├─ 006 ─── 007
     │            ╲
     │             ╲─── 009 ─── 010 ─── 011 ─── 012
     │                   ╲
     │                    ╲── 013 ── 014 ─── 015
     │                             ╲      ╲
     │                              ╲      ╲── 016 (Persistence Baseline)
     │                               ╲           ╲
     │                                ╲── 017 ─── 018
     │
     └── 020 (requires 009, 014, 017, 008)
              ╲
               ╲── 021 (MVP complete)
                     ╲
                      022 (requires 014, 020) ─── 023 ─── 025
                        ╲                          ╲       ╲
                         ╲── 024 (requires 023)     ╲      026
                              ╲                       ╲    ╱
                               ╲── 027 (Phase 2 complete)
                                     ╲
                                      028 ─── 029
                                        ╲
                                         030 (requires 012, 025)
                                           ╲
                                            031 ─── 032 (Launch ready)
```

---

## How to Use This Plan

### For Project Managers

1. Use the **Status** column in the task index above to track progress at a glance
2. Open any task document to see detailed implementation notes, decisions, and validation results
3. Respect the dependency order — tasks cannot begin until their dependencies are complete
4. Within a phase, independent tasks can run in parallel (e.g., 004 and 005; 009 and 011)

### For Developers

1. Read the task document for your assigned step
2. Review the referenced source documents for context
3. Use the **Coding Agent Prompt** at the bottom of each task to bootstrap implementation
4. Follow the **Testing & Acceptance Criteria** to validate your work
5. **Update the task document** when work begins, progresses, and completes (see below)

### For Coding Agents

1. You will receive a prompt referencing a specific task document
2. Read the full task specification at the referenced path
3. Implement the described features, following the detailed specifications
4. Validate against the acceptance criteria before marking complete
5. **Update the task document** as a final step (instructions are in the Coding Agent Prompt)

---

## Living Document Process

Each task document is a **living document** that tracks its own lifecycle. Here's how to update them:

### Status Transitions

```
🔲 Not Started  →  🔄 In Progress  →  ✅ Complete
                         ↓
                    ⚠️ Blocked (with notes on blocker)
```

### When Starting a Task

1. Change the status banner at the top of the task document:
   ```
   > **🔄 Status: In Progress**
   ```
2. Add a row to the **Status History** table with the start date
3. Update the status in this README's task index table to `🔄`

### During Implementation

1. Record significant **Technical Decisions** as they are made
2. Note any **Deviations from Plan** with rationale
3. Update the **Status History** table with meaningful milestones

### When Completing a Task

1. Change the status banner at the top of the task document:
   ```
   > **✅ Status: Complete**
   ```
2. Add a final row to the **Status History** table with the completion date
3. Fill in **Validation Results** with test outcomes, coverage, and any metrics
4. Check off completed items in the **Testing & Acceptance Criteria** checklist
5. Update the status in this README's task index table to `✅`

---

## Parallel Execution Opportunities

Within the dependency constraints, certain tasks can be executed in parallel:

| Parallel Group   | Tasks                               | Notes                                                                |
| ---------------- | ----------------------------------- | -------------------------------------------------------------------- |
| Sprint Zero      | 004, 005, 006 (after 001, 002, 003) | Security baseline, frontend and BFF setup can happen simultaneously  |
| Data Layer       | 009, 013 (after 006, 007)           | API Center and AI Search setup are independent                       |
| Frontend Pages   | 011, 012 (after 010)                | Catalog and detail pages can be built together                       |
| Search + Chat    | 014/015, 017/018 (after 013)        | Search and chat paths are independent (note: 017 depends on 014)     |
| Cross-cutting    | 008, 019 (after 005, 006)           | Auth and observability are independent                               |
| Phase 2 Features | 023, 024 (after 022)                | Governance and comparison are independent (note: 024 depends on 023) |
| Phase 3 Features | 028/029, 030 (after dependencies)   | Analytics and metadata scoring are independent                       |
