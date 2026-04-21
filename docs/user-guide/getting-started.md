# Getting Started with APIC Vibe Portal AI

Welcome to the **APIC Vibe Portal AI** — your AI-powered gateway to discovering, understanding, and using APIs faster. This guide will help you get up and running quickly.

## What Is APIC Vibe Portal AI?

The portal is an intelligent API discovery platform that combines:

- **Azure API Center** — a structured catalog of all APIs available in your organization
- **Azure AI Search** — hybrid semantic + keyword search across API metadata
- **Azure OpenAI + Foundry Agents** — an AI assistant that answers questions about APIs and guides you toward the right one
- **Governance dashboards** — compliance and quality scores to help you choose reliable APIs
- **Comparison tools** — side-by-side API comparison to support informed decisions

## Prerequisites

Before using the portal, ensure you have:

1. **An organizational account** — the portal uses Microsoft Entra ID (Azure AD) for authentication
2. A web browser (Chrome, Edge, Firefox, or Safari)
3. The portal URL provided by your administrator

## Signing In

1. Navigate to the portal URL in your browser
2. Click **Sign in** in the top-right corner
3. You will be redirected to the Microsoft Entra ID sign-in page
4. Enter your organizational email and password (or use SSO if configured)
5. After successful authentication, you will be redirected back to the portal

> **Note**: If your organization uses multi-factor authentication (MFA), you will be prompted during sign-in.

## The Portal Layout

After signing in, you will see:

- **Sidebar (left)**: Navigation links to all portal sections
- **Header (top)**: Search bar, and your user avatar/menu
- **Main content area**: The current page content

### Navigation Sections

| Section                  | Description                                  |
| ------------------------ | -------------------------------------------- |
| API Catalog              | Browse all registered APIs                   |
| Search                   | Full-text and semantic API search            |
| AI Assistant             | Chat with the AI to find and understand APIs |
| Governance               | API compliance and quality scores            |
| Compare                  | Side-by-side API comparison                  |
| Analytics (Admin)        | Usage analytics dashboard (admin only)       |
| Agent Management (Admin) | Manage AI agents (admin only)                |

## Quick Start: Find an API in 3 Steps

### Step 1: Search for the API you need

Use the **search bar** at the top of any page to type keywords:

```
payment processing
```

Press **Enter** or click the search icon. You'll see ranked results with relevance scores.

### Step 2: Explore the API detail

Click any result to open the **API Detail** page, where you can view:

- **Overview**: Description, lifecycle stage, contacts
- **Versions**: Available API versions
- **Specification**: OpenAPI spec viewer with all endpoints
- **Deployments**: Live deployment URLs

### Step 3: Get AI assistance

Click the **AI Assistant button** (bottom-right floating button) on any page to open the chat panel. Ask questions like:

- _"Which payment APIs support REST?"_
- _"What's the latest version of the Orders API?"_
- _"Compare the Users API and the Identity API"_

## Next Steps

- **[Searching for APIs](searching-apis.md)** — advanced search techniques
- **[Using the AI Chat](using-ai-chat.md)** — getting the most from the AI assistant
- **[Comparing APIs](comparing-apis.md)** — side-by-side comparison guide
- **[Understanding Governance](understanding-governance.md)** — compliance scores explained
