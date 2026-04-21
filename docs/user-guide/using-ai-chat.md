# Using the AI Chat Assistant

The AI Chat Assistant is the most powerful way to discover and understand APIs in the portal. Powered by **Azure OpenAI** and **Foundry Agent Service**, it can answer complex questions, compare APIs, explain technical details, and provide governance insights.

## How to Access the Chat

### Full-Page Chat

Navigate to `/chat` via the sidebar link **"AI Assistant"** for the full-screen chat experience.

### Floating Chat Panel

On any page, click the **AI Assistant button** (💬 icon in the bottom-right corner) to open a slide-in panel without leaving your current page. This is ideal when you are browsing the catalog and have a quick question.

## Starting a Conversation

### Starter Prompts

When you first open the chat, you will see suggested starter prompts such as:

- _"Show me APIs in production"_
- _"What payment APIs are available?"_
- _"Explain REST vs GraphQL APIs"_

Click any suggestion to send it as your first message.

### Typing Your Own Question

Click the text input at the bottom of the chat panel, type your question, and press **Enter** (or click the **Send** button).

## What You Can Ask

### API Discovery

```
Which APIs support credit card processing?
Show me all production REST APIs.
Find APIs related to user management.
```

### API Understanding

```
What does the Payments API v2 do?
What endpoints does the Orders API provide?
Explain the authentication model for the Identity API.
```

### Governance and Compliance

```
What is the governance score of the Users API?
Which APIs have critical compliance failures?
What should I fix to improve the Orders API score?
```

### API Comparison

```
Compare the Payments API and the Billing API.
What are the differences between v1 and v2 of the Orders API?
Which API is better suited for a mobile app: REST or GraphQL?
```

### Technical Guidance

```
How do I authenticate with the Payments API?
Give me a code example for calling the Orders API.
What rate limits apply to the AI Search API?
```

## Understanding AI Responses

### Citations

When the AI references specific APIs, it may include **citation links** in the response. Click a citation link to navigate directly to the API detail page.

### Response Accuracy

The AI uses information from your organization's API catalog and governance system. It does not have access to the internet. If information is not in the catalog, the AI will tell you.

### Multi-Turn Conversations

The AI remembers the context of the conversation. You can follow up without repeating yourself:

```
User: Tell me about the Payments API.
AI: [describes the API]
User: What version should I use in production?
AI: [continues the context from the previous answer]
```

## Best Practices

1. **Be specific** — Include the API name if you know it: _"What's the base URL for the Payments API?"_
2. **Ask follow-up questions** — The AI understands conversation context
3. **Use natural language** — You don't need to use technical jargon
4. **Ask for examples** — The AI can generate code snippets
5. **Ask about governance** — Use the AI to understand compliance requirements before adopting an API

## Limitations

- The AI operates within the scope of your organization's API catalog
- It cannot retrieve information from the internet
- Very large OpenAPI specifications may be summarized rather than fully analyzed
- The AI cannot make changes to the catalog or APIs

## Clearing a Chat Session

Each page load starts a fresh conversation. To start over, refresh the page or navigate away and back.

## Related Guides

- **[Getting Started](getting-started.md)**
- **[Searching for APIs](searching-apis.md)**
- **[Comparing APIs](comparing-apis.md)**
- **[Understanding Governance](understanding-governance.md)**
