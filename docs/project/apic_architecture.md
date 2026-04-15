# APIC Vibe Portal AI - Architecture Document

## Overview

Multi-agent API portal built on:

- Azure API Center
- Azure AI Search
- Azure OpenAI
- Foundry Agent Service
- Azure Container Apps
- Azure Cosmos DB (serverless)

## Architecture Diagram

Browser -> Next.js -> BFF (Python/FastAPI) -> APIC + AI Search + Foundry Agents + Cosmos DB

## Components

- Frontend (Next.js SPA)
- Backend (BFF) — Python 3.14, FastAPI, managed with UV
- Agent Layer (Foundry)
- Search Layer (AI Search)
- Observability (App Insights)
- Persistence (Cosmos DB serverless — chat sessions, governance snapshots, analytics)

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
