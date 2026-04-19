# 018 - Phase 1 MVP: AI Chat Interface (Frontend)

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — AI-powered discovery through conversational interface
- [Product Charter](../apic_product_charter.md) — Enable AI-assisted workflows; reduce time to find APIs
- [Product Spec](../apic_portal_spec.md) — Chat UI requirements

## Overview

Build the AI-powered chat interface in the frontend that allows developers to discover and learn about APIs through natural language conversation. The chat connects to the BFF's OpenAI-powered RAG endpoints.

## Dependencies

- **005** — Frontend project setup (components, layout)
- **007** — Shared types package (chat models)
- **017** — OpenAI BFF integration (chat API endpoints)

## Implementation Details

### 1. Chat Components

```
app/chat/
├── page.tsx                # Full-page chat view
└── components/
    ├── ChatContainer.tsx         # Main chat container
    ├── ChatMessageList.tsx       # Scrollable message list
    ├── ChatMessage.tsx           # Individual message bubble
    ├── ChatInput.tsx             # Message input area
    ├── ChatCitations.tsx         # Citation links in messages
    ├── ChatSuggestions.tsx       # Suggested prompts
    ├── ChatTypingIndicator.tsx   # AI typing animation
    └── ChatSidePanel.tsx         # Collapsible panel for embedded chat
```

### 2. Full-Page Chat (`/chat`)

- Centered chat interface with message history
- Input area at bottom with send button
- Messages scroll from bottom to top (newest at bottom)
- Clear conversation button
- Suggested starter prompts when conversation is empty:
  - "What APIs are available for payment processing?"
  - "Show me APIs in production"
  - "Which APIs support GraphQL?"
  - "Help me find an API for user authentication"

### 3. Embedded Chat Panel

- Collapsible side panel accessible from any page via floating button
- Same chat functionality as full-page but in a compact panel
- Persists conversation as user navigates between pages
- Minimize/maximize toggle
- Panel slides in from the right side

### 4. Message Rendering

- **User messages**: Right-aligned, colored bubble
- **Assistant messages**: Left-aligned, rendered as markdown (support code blocks, lists, bold)
- **Citations**: Inline linked references to APIs (clicking opens API detail page)
- **Streaming**: Text appears incrementally as tokens arrive via SSE
- **Timestamps**: Subtle timestamp on each message
- **Copy button**: Copy assistant message text to clipboard

### 5. Chat Input

- Multi-line text area (auto-expand up to 4 lines)
- Send on Enter (Shift+Enter for new line)
- Send button with loading state
- Disabled while waiting for response
- Character count indicator near limits

### 6. Citations Component

- Citations displayed as clickable chips below the assistant message
- Each citation shows: API name, relevance indicator
- Clicking a citation navigates to the API detail page (`/catalog/:apiId`)
- Hover shows excerpt preview

### 7. Streaming Integration

- Connect to `POST /api/chat/stream` using `fetch()` and consume the streamed response via `ReadableStream`
- Render tokens incrementally in the message bubble as chunks arrive
- Show typing indicator until first token arrives
- Handle stream errors gracefully (retry the request when appropriate or show an error)

### 8. Session Management

- Store session ID in React state (or context)
- Session persists across page navigation (via React context provider)
- "New conversation" button creates a new session
- Session-level state managed in a ChatProvider context

### 9. Responsive Design

- Full-page chat: centered, max-width container
- Embedded panel: fixed-width right sidebar
- Mobile: full-screen overlay for embedded chat

## Testing & Acceptance Criteria

- [ ] Full-page chat at `/chat` renders correctly
- [ ] User can type and send messages
- [ ] Assistant responses appear with streaming text
- [ ] Citations are clickable and navigate to API detail pages
- [ ] Markdown rendering in assistant messages (code blocks, lists, etc.)
- [ ] Suggested prompts appear in empty conversation
- [ ] Embedded chat panel opens/closes from floating button
- [ ] Conversation persists when navigating between pages
- [ ] "New conversation" resets the chat
- [ ] Typing indicator shows while waiting for response
- [ ] Copy button copies message text to clipboard
- [ ] All components have unit tests
- [ ] Responsive layout works on mobile, tablet, and desktop
- [ ] Playwright e2e tests added in `src/frontend/e2e/chat.spec.ts` covering chat page rendering, message sending, suggested prompts, and embedded panel interaction

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author  | Notes                                                             |
| ---------- | -------------- | ------- | ----------------------------------------------------------------- |
| —          | 🔲 Not Started | —       | Task created                                                      |
| 2026-04-19 | ✅ Complete    | copilot | Full chat UI implemented with all components, tests, and e2e spec |

### Technical Decisions

- **react-markdown** added as a dependency for proper markdown rendering of assistant messages (code blocks, lists, bold/italic). A lightweight Jest mock is used in unit tests to avoid ESM compatibility issues.
- **ChatProvider** context wraps the root layout so conversation state persists across all page navigations (catalog → chat → back).
- **SSE streaming** is consumed via `fetch()` + `ReadableStream` in `lib/chat-api.ts`. Tokens are applied incrementally to a message placeholder via React state.
- **Floating Action Button (FAB)** is used for the embedded side panel toggle, fixed bottom-right, visible on all pages.
- **Persistent drawer** (`variant="persistent"`) used for the side panel on desktop; **temporary** drawer used on mobile for a full-screen overlay experience.
- **`slotProps.htmlInput`** used instead of deprecated `inputProps` for MUI v9 TextField.
- **`sx={{ textAlign: 'center' }}`** used instead of the deprecated `textAlign` prop on Typography in MUI v9.

### Deviations from Plan

- The typing indicator is shown only when the last assistant message is an empty placeholder (content `""`), rather than as a separate component before the placeholder appears. This is simpler and avoids race conditions.
- The `ChatSidePanel` uses a MUI `Drawer` with `variant="persistent"` on desktop (instead of a purely custom slide-in), which integrates better with the MUI layout system.
- Citation URLs that are not `/catalog/<id>` paths are navigated to directly via `router.push()` rather than treated as external links (consistent with SPA navigation).

### Validation Results

- **Unit tests**: 44 tests across 8 test files — all pass (`npm run test --workspace=@apic-vibe-portal/frontend -- --testPathPattern="chat"`)
- **Build**: `npm run build --workspace=@apic-vibe-portal/frontend` succeeds; `/chat` route renders as a static page
- **Lint**: `npm run lint --workspace=@apic-vibe-portal/frontend` passes with zero errors
- **Format**: `npm run format:check` passes with zero warnings
- **E2E tests**: Playwright tests added in `src/frontend/e2e/chat.spec.ts` covering:
  - Chat page rendering and heading
  - Suggested starter prompts display and selection
  - Typing and sending messages
  - Send button disabled state
  - New conversation reset
  - FAB visibility on catalog page
  - Panel open/close via FAB
  - Conversation persistence across navigation

## Coding Agent Prompt

```text
**Task**: Implement plan step 018 — AI Chat Interface.

Read the full task specification at `docs/project/plan/018-frontend-chat-ui.md`.

Reference `docs/project/plan/017-openai-integration.md` for the BFF chat API contract (endpoints, request/response shapes, SSE streaming), `docs/project/plan/005-frontend-nextjs-setup.md` for the frontend structure, and `docs/project/plan/007-shared-types-package.md` for the chat types.

Build the full-page chat view at `/chat` and an embedded collapsible chat side panel accessible from all pages. Implement message rendering with markdown support, SSE streaming integration, citation chips that link to API detail pages, suggested starter prompts, session management via React context, and responsive layout.

Write unit tests for all components. Add Playwright e2e tests in `src/frontend/e2e/chat.spec.ts` covering chat page rendering, message sending, suggested prompts, and embedded panel interaction. Verify the build succeeds, linting passes, and all tests pass (including `npm run test:e2e`).

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/018-frontend-chat-ui.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
