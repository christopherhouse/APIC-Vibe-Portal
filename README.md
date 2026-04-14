# APIC Vibe Portal AI

An **AI-powered API portal** built on Azure services, designed to help developers discover, understand, and use APIs faster through multi-agent AI assistance.

## 🏗️ Architecture

```mermaid
graph TB
    Browser[🌐 Browser]
    NextJS[⚛️ Next.js Frontend]
    BFF[🐍 FastAPI BFF]
    APIC[📚 Azure API Center]
    Search[🔍 Azure AI Search]
    Foundry[🤖 Foundry Agents]
    Cosmos[💾 Cosmos DB]
    Insights[📊 App Insights]

    Browser --> NextJS
    NextJS --> BFF
    BFF --> APIC
    BFF --> Search
    BFF --> Foundry
    BFF --> Cosmos
    NextJS -.-> Insights
    BFF -.-> Insights
```

**Components:**
- **Frontend**: Next.js 16 SPA with TypeScript 6.0
- **BFF**: Python 3.14 + FastAPI backend (managed with UV)
- **AI Layer**: Azure OpenAI + Foundry Agent Service
- **Search**: Azure AI Search (hybrid search)
- **Catalog**: Azure API Center
- **Persistence**: Azure Cosmos DB (serverless)
- **Observability**: Azure Application Insights
- **Deployment**: Azure Container Apps

For detailed architecture, see [docs/project/apic_architecture.md](docs/project/apic_architecture.md).

## 🚀 Getting Started

### Prerequisites

- **Node.js** >= 24 (see `.nvmrc`)
- **Python** 3.14 (see `.python-version`)
- **UV** (Python package manager) — [Install UV](https://github.com/astral-sh/uv)
- **npm** >= 10
- **Azure CLI** (for deployment)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/christopherhouse/APIC-Vibe-Portal.git
   cd APIC-Vibe-Portal
   ```

2. **Install frontend and shared dependencies**
   ```bash
   npm install
   ```

3. **Install BFF dependencies**
   ```bash
   cd src/bff
   uv sync
   cd ../..
   ```

### Development

#### Run Frontend (Next.js)
```bash
npm run dev --workspace=@apic-vibe-portal/frontend
```

#### Run BFF (FastAPI)
```bash
cd src/bff
uv run fastapi dev
```

#### Lint
```bash
# Frontend + Shared
npm run lint

# BFF
cd src/bff
uv run ruff check .
```

#### Format
```bash
# Frontend + Shared
npm run format

# BFF
cd src/bff
uv run ruff format .
```

#### Test
```bash
# Frontend + Shared
npm run test

# BFF
cd src/bff
uv run pytest
```

#### Build
```bash
# Frontend + Shared
npm run build
```

## 📂 Repository Structure

```
/
├── src/
│   ├── frontend/          # Next.js 16 SPA
│   ├── bff/               # Python 3.14 + FastAPI BFF
│   └── shared/            # Shared TypeScript types/utilities
├── infra/                 # Bicep IaC templates
├── .github/
│   ├── workflows/         # CI/CD pipelines
│   ├── copilot-instructions.md
│   ├── agents/            # Custom Copilot agents
│   ├── copilot/
│   │   └── mcp.json       # MCP server configuration
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   └── project/           # Project documentation
├── scripts/               # Developer helper scripts
├── .editorconfig
├── .gitignore
├── .nvmrc                 # Node.js version (24)
├── .python-version        # Python version (3.14)
├── package.json           # Root workspace config
└── README.md
```

## 📚 Documentation

- **[Product Charter](docs/project/apic_product_charter.md)** — Vision, goals, and timeline
- **[Architecture](docs/project/apic_architecture.md)** — Component overview and design
- **[Product Spec](docs/project/apic_portal_spec.md)** — Feature requirements
- **[Implementation Plan](docs/project/plan/README.md)** — Phased development plan

## 🔧 Tech Stack

### Frontend
- Next.js 16 (App Router)
- React 19
- TypeScript 6.0 (strict mode)
- ESLint + Prettier
- Jest + React Testing Library + Playwright

### Backend (BFF)
- Python 3.14
- FastAPI
- UV (package manager)
- Ruff (linting + formatting)
- pytest

### Azure Services
- Azure API Center
- Azure AI Search
- Azure OpenAI
- Foundry Agent Service
- Azure Cosmos DB (serverless)
- Azure Container Apps
- Azure Application Insights
- Azure Key Vault
- Azure Container Registry

## 🤖 GitHub Copilot Integration

This project includes custom GitHub Copilot agents and instructions:

- **Copilot Instructions**: [.github/copilot-instructions.md](.github/copilot-instructions.md)
- **Custom Agents**:
  - `api-portal-architect` — Architecture and design decisions
  - `azure-infra-agent` — Bicep templates and Azure resources
  - `frontend-agent` — Next.js and React development
  - `bff-agent` — FastAPI and Azure SDK integration
  - `tech-writer-agent` — Documentation writing

### MCP Servers
Available Model Context Protocol servers:
- **Microsoft Learn** — Azure SDK docs and best practices
- **Context7** — Up-to-date library documentation
- **Next.js DevTools** — Next.js development tooling
- **Snyk** — Security vulnerability scanning

## 🔒 Security

- **Authentication**: Entra ID (Azure AD)
- **Authorization**: RBAC with security trimming
- **Secrets**: Azure Key Vault (never commit secrets!)
- **Scanning**: Snyk for dependency vulnerabilities

## 🧪 Testing

- **Frontend**: Jest + React Testing Library (unit/component), Playwright (E2E)
- **BFF**: pytest (unit + integration)
- **Coverage Target**: >80% for business logic

## 🚢 Deployment

Deploy to Azure Container Apps via GitHub Actions:

1. Build Docker images for frontend and BFF
2. Push to Azure Container Registry
3. Deploy to Azure Container Apps
4. Infrastructure managed via Bicep templates

See `.github/workflows/` for CI/CD pipelines.

## 🤝 Contributing

1. Check the [implementation plan](docs/project/plan/README.md) for current tasks
2. Create a branch from `main`
3. Make changes following coding conventions (see `.github/copilot-instructions.md`)
4. Write tests for new functionality
5. Run linting and tests locally
6. Create a PR using the template

## 📝 License

See [LICENSE](LICENSE) for details.

---

**Built with ❤️ using Azure AI services**
