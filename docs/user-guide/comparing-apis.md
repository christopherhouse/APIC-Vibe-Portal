# Comparing APIs

The API Comparison feature lets you compare two or more APIs side by side, helping you make informed decisions about which API best suits your needs.

## Accessing the Comparison Page

Navigate to **Compare** in the left sidebar, or go directly to `/compare`.

## How to Compare APIs

### Step 1: Select APIs

Use the **API selector** dropdowns to choose the APIs you want to compare. Start by selecting at least two APIs. You can compare up to 4 APIs simultaneously.

### Step 2: View the Comparison Table

Once you have selected your APIs, the comparison table populates automatically with:

| Attribute            | Description                              |
| -------------------- | ---------------------------------------- |
| **API Type**         | REST, GraphQL, gRPC, etc.                |
| **Lifecycle Stage**  | Production, Development, Deprecated      |
| **Latest Version**   | Most recent version identifier           |
| **Deployments**      | Number of active deployment environments |
| **Governance Score** | Compliance and quality score (0–100)     |
| **Contacts**         | Owning team contact information          |
| **License**          | Usage license                            |

### Step 3: Read the Comparison

Differences between APIs are visually highlighted. Attributes where one API is clearly better (e.g., higher governance score, production lifecycle) may be highlighted in green.

## AI-Powered Comparison Analysis

After the comparison table loads, you can click **"Ask AI to analyze"** (or use the floating chat button) to get an AI-generated summary:

- Strengths and weaknesses of each API
- Recommendation for your specific use case
- Key differences in versioning or lifecycle

**Example prompt to the AI:**

```
Based on the comparison, which API should I use for a mobile payment app?
```

## Comparison Tips

- **Check lifecycle stage first** — Prefer Production APIs for any live system
- **Review governance scores** — APIs with scores below 70 may have compliance gaps
- **Compare versions** — If both APIs have the same functionality, the one with a newer version may be more actively maintained
- **Check deployments** — An API with a production deployment URL is ready to use

## Sharing a Comparison

The comparison state is stored in the URL. You can copy the browser URL and share it with teammates to show them the same comparison.

## Comparing Versions of the Same API

On an individual **API Detail** page, navigate to the **Versions** tab to see all available versions. Click a version to view its specification and then use the chat to ask:

```
What changed between v1 and v2 of the Payments API?
```

## Related Guides

- **[Getting Started](getting-started.md)**
- **[Using the AI Chat](using-ai-chat.md)**
- **[Understanding Governance](understanding-governance.md)**
