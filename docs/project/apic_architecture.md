# APIC Vibe Portal AI - Architecture Document

## Overview
Multi-agent API portal built on:
- Azure API Center
- Azure AI Search
- Azure OpenAI
- Foundry Agent Service
- Azure Container Apps

## Architecture Diagram
Browser -> Next.js -> BFF -> APIC + AI Search + Foundry Agents

## Components
- Frontend (Next.js SPA)
- Backend (BFF)
- Agent Layer (Foundry)
- Search Layer (AI Search)
- Observability (App Insights)

## Key Decisions
- BFF required for orchestration
- Hybrid search for retrieval
- Multi-agent design

## Security
- Entra ID
- RBAC + security trimming

## Deployment
- Azure Container Apps
- ACR
- Key Vault
