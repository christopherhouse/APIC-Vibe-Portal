# Searching for APIs

The APIC Vibe Portal AI provides a powerful hybrid search experience that combines full-text keyword matching with semantic understanding. This guide explains how to get the best results.

## The Search Bar

The search bar is visible in the header on every page. You can:

- Type keywords and press **Enter** to go to the full search results page
- Use the autocomplete suggestions that appear as you type (click a suggestion to navigate directly to that API)

## Search Results Page

Navigate to `/search?q=your+query` or use the search bar to reach the full search page.

### Results Layout

Each result card shows:

- **API title** and type badge (REST / GraphQL)
- **Description** excerpt
- **Lifecycle stage** (Production / Development / Deprecated)
- **Relevance score** — how closely the API matches your query

### Filtering Results

Use the filter panel on the left to narrow results by:

| Filter    | Options                                  |
| --------- | ---------------------------------------- |
| Lifecycle | Production, Development, Deprecated      |
| API Type  | REST, GraphQL                            |
| Tags      | Any tags applied to APIs in your catalog |

Filters update the URL so you can **share** a filtered search with colleagues.

### Sorting Results

Click the **Sort by** dropdown to order results by:

- **Relevance** (default) — most semantically relevant first
- **Name A–Z / Z–A** — alphabetical order
- **Last Updated (newest)** — most recently updated first

## Search Tips

### Keyword Search

Enter exact terms to find APIs containing those words:

```
payment REST production
```

### Semantic / Natural-Language Search

The portal uses Azure AI Search semantic ranking, so you can describe what you need in plain English:

```
API for processing credit card payments
```

```
user authentication and profile management
```

### Combining Keywords and Filters

You can combine a keyword query with filters:

1. Search for `orders`
2. Then filter by **Lifecycle: Production** to see only production-ready APIs

### Autocomplete Suggestions

As you type in the search bar, up to 5 suggestions appear. These are matched against API titles and descriptions. Use arrow keys to navigate suggestions, or click to navigate directly to the API detail page.

## Understanding Relevance Scores

Each result is assigned a relevance score between 0 and 1:

| Score   | Meaning                                        |
| ------- | ---------------------------------------------- |
| 0.9–1.0 | Excellent match — title contains your keywords |
| 0.7–0.9 | Good match — strong semantic similarity        |
| 0.5–0.7 | Partial match — some overlap                   |
| < 0.5   | Weak match                                     |

Higher-scored results appear first.

## No Results?

If no results are found:

1. **Check your spelling** — try alternative terms
2. **Broaden your query** — fewer, more general keywords
3. **Clear filters** — some filter combinations may be too restrictive
4. **Use the AI chat** — ask the AI assistant to help you find the right API

> **Tip**: The AI assistant on the `/chat` page can handle more complex queries like _"Find an API that handles both payments and refunds."_

## Related Guides

- **[Getting Started](getting-started.md)**
- **[Using the AI Chat](using-ai-chat.md)**
- **[Comparing APIs](comparing-apis.md)**
