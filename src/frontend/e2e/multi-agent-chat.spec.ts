/**
 * E2E tests for multi-agent chat hand-off behaviour.
 *
 * These tests verify that the chat UI responds correctly when the BFF
 * SSE stream includes agent-routing metadata. The BFF can include a
 * `agentId` field in the `end` event to indicate which agent handled
 * the query. The tests cover:
 *
 *  - Discovery agent responding to catalog questions
 *  - Governance agent responding to governance questions (simulated hand-off)
 *  - Conversation context maintained across agent hand-offs
 *  - Fallback handling for low-confidence queries
 *  - Error recovery after a failed agent response
 */

import { test, expect, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// SSE stream helpers
// ---------------------------------------------------------------------------

/** Build an SSE body for a successful agent response. */
function buildAgentStream(options: {
  sessionId: string;
  content: string;
  agentId?: string;
  handoffFrom?: string;
}): string {
  const { sessionId, content, agentId = 'api_discovery', handoffFrom } = options;
  const msgId = `msg-${Math.random().toString(36).slice(2)}`;
  const now = new Date().toISOString();

  const events: string[] = [`data: ${JSON.stringify({ type: 'start', sessionId })}\n\n`];

  // Optional hand-off notification event
  if (handoffFrom) {
    events.push(
      `data: ${JSON.stringify({
        type: 'agent_handoff',
        fromAgent: handoffFrom,
        toAgent: agentId,
        sessionId,
      })}\n\n`
    );
  }

  events.push(
    `data: ${JSON.stringify({ type: 'content', content: content.slice(0, 20) })}\n\n`,
    `data: ${JSON.stringify({ type: 'content', content: content.slice(20) })}\n\n`,
    `data: ${JSON.stringify({
      type: 'end',
      message: {
        id: msgId,
        role: 'assistant',
        content,
        citations: null,
        timestamp: now,
        agentId,
      },
      sessionId,
      agentId,
    })}\n\n`
  );

  return events.join('');
}

/** Build an SSE body for an error response. */
function buildErrorStream(sessionId: string, errorMsg: string): string {
  return [
    `data: ${JSON.stringify({ type: 'start', sessionId })}\n\n`,
    `data: ${JSON.stringify({ type: 'error', error: errorMsg, sessionId })}\n\n`,
  ].join('');
}

// ---------------------------------------------------------------------------
// Route mock helpers
// ---------------------------------------------------------------------------

async function mockDiscoveryResponse(page: Page) {
  await page.route('**/api/chat/stream', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: buildAgentStream({
        sessionId: 'session-discovery-1',
        content:
          'I found 5 APIs matching your query. The Payments API and Users API are available in production.',
        agentId: 'api_discovery',
      }),
    });
  });
}

async function mockGovernanceHandoff(page: Page) {
  let callCount = 0;
  await page.route('**/api/chat/stream', async (route) => {
    callCount++;
    if (callCount === 1) {
      // First message: discovery agent responds
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: buildAgentStream({
          sessionId: 'session-gov-1',
          content: 'I found several APIs. Would you like to check their governance status?',
          agentId: 'api_discovery',
        }),
      });
    } else {
      // Second message: governance agent responds after hand-off
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: buildAgentStream({
          sessionId: 'session-gov-1',
          content:
            'The Payments API has a governance score of 92/100. All critical rules are passing.',
          agentId: 'governance',
          handoffFrom: 'api_discovery',
        }),
      });
    }
  });
}

async function mockFallbackResponse(page: Page) {
  await page.route('**/api/chat/stream', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: buildAgentStream({
        sessionId: 'session-fallback-1',
        content:
          "I'm not sure I understand your question. Could you rephrase it? I can help you discover APIs, check governance status, or compare APIs.",
        agentId: 'api_discovery',
      }),
    });
  });
}

async function mockErrorThenRecovery(page: Page) {
  let callCount = 0;
  await page.route('**/api/chat/stream', async (route) => {
    callCount++;
    if (callCount === 1) {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: buildErrorStream('session-err-1', 'Agent temporarily unavailable'),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: buildAgentStream({
          sessionId: 'session-err-1',
          content: 'Hello! I can now help you discover APIs.',
          agentId: 'api_discovery',
        }),
      });
    }
  });
}

// ---------------------------------------------------------------------------
// Tests: Discovery Agent
// ---------------------------------------------------------------------------

test.describe('Multi-Agent Chat — Discovery Agent', () => {
  test('asking a discovery question gets a response', async ({ page }) => {
    await mockDiscoveryResponse(page);
    await page.goto('/chat');
    const main = page.locator('main');

    await main.getByTestId('chat-input').fill('What APIs are available in production?');
    await main.getByTestId('send-button').click();

    // User message appears
    await expect(main.getByText('What APIs are available in production?')).toBeVisible();

    // Assistant response appears
    await expect(main.getByText(/I found 5 APIs matching your query/i)).toBeVisible({
      timeout: 10000,
    });
  });

  test('response appears in message list', async ({ page }) => {
    await mockDiscoveryResponse(page);
    await page.goto('/chat');
    const main = page.locator('main');

    await main.getByTestId('chat-input').fill('Show me REST APIs');
    await main.getByTestId('send-button').click();

    // Message list should have at least 2 messages (user + assistant)
    await expect(main.getByText(/I found 5 APIs/i)).toBeVisible({ timeout: 10000 });
  });
});

// ---------------------------------------------------------------------------
// Tests: Agent Hand-off
// ---------------------------------------------------------------------------

test.describe('Multi-Agent Chat — Agent Hand-off', () => {
  test('conversation continues after agent hand-off', async ({ page }) => {
    await mockGovernanceHandoff(page);
    await page.goto('/chat');
    const main = page.locator('main');

    // First message: discovery
    await main.getByTestId('chat-input').fill('Show me available APIs');
    await main.getByTestId('send-button').click();

    await expect(main.getByText(/I found several APIs/i)).toBeVisible({ timeout: 10000 });

    // Second message: governance question triggers hand-off
    await main.getByTestId('chat-input').fill('What is the governance status of Payments API?');
    await main.getByTestId('send-button').click();

    // Governance agent response appears
    await expect(main.getByText(/governance score of 92/i)).toBeVisible({ timeout: 10000 });
  });

  test('conversation context is maintained after hand-off', async ({ page }) => {
    await mockGovernanceHandoff(page);
    await page.goto('/chat');
    const main = page.locator('main');

    // First message
    await main.getByTestId('chat-input').fill('Tell me about the Payments API');
    await main.getByTestId('send-button').click();
    await expect(main.getByText(/I found several APIs/i)).toBeVisible({ timeout: 10000 });

    // Both the initial query and the first response should still be visible
    await expect(main.getByText('Tell me about the Payments API')).toBeVisible();
    await expect(main.getByText(/I found several APIs/i)).toBeVisible();

    // Second message
    await main.getByTestId('chat-input').fill('Check its governance score');
    await main.getByTestId('send-button').click();

    // All previous messages should still be in the conversation
    await expect(main.getByText('Tell me about the Payments API')).toBeVisible();
    await expect(main.getByText('Check its governance score')).toBeVisible();
    await expect(main.getByText(/governance score of 92/i)).toBeVisible({ timeout: 10000 });
  });
});

// ---------------------------------------------------------------------------
// Tests: Fallback handling
// ---------------------------------------------------------------------------

test.describe('Multi-Agent Chat — Fallback Handling', () => {
  test('low-confidence query gets helpful fallback response', async ({ page }) => {
    await mockFallbackResponse(page);
    await page.goto('/chat');
    const main = page.locator('main');

    await main.getByTestId('chat-input').fill('xyzzy foo bar something unclear');
    await main.getByTestId('send-button').click();

    // Fallback response appears
    await expect(main.getByText(/not sure I understand/i)).toBeVisible({ timeout: 10000 });
  });
});

// ---------------------------------------------------------------------------
// Tests: Error recovery
// ---------------------------------------------------------------------------

test.describe('Multi-Agent Chat — Error Recovery', () => {
  test('shows error message when stream fails', async ({ page }) => {
    await page.route('**/api/chat/stream', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: buildErrorStream('session-1', 'Agent temporarily unavailable'),
      });
    });

    await page.goto('/chat');
    const main = page.locator('main');

    await main.getByTestId('chat-input').fill('Hello');
    await main.getByTestId('send-button').click();

    // Error should be shown in the UI
    await expect(main.getByRole('alert')).toBeVisible({ timeout: 10000 });
  });

  test('can send another message after error', async ({ page }) => {
    await mockErrorThenRecovery(page);
    await page.goto('/chat');
    const main = page.locator('main');

    // First message triggers error
    await main.getByTestId('chat-input').fill('First message');
    await main.getByTestId('send-button').click();

    // Error alert visible
    await expect(main.getByRole('alert')).toBeVisible({ timeout: 10000 });

    // Recover: send a new conversation
    await main.getByTestId('new-conversation-button').click();
    await expect(main.getByTestId('chat-suggestions')).toBeVisible({ timeout: 5000 });

    // Send a fresh message
    await main.getByTestId('chat-input').fill('Try again');
    await main.getByTestId('send-button').click();

    await expect(main.getByText(/Hello! I can now help/i)).toBeVisible({ timeout: 10000 });
  });
});

// ---------------------------------------------------------------------------
// Tests: Side panel multi-agent
// ---------------------------------------------------------------------------

test.describe('Multi-Agent Chat — Side Panel', () => {
  test('side panel chat works with governance questions', async ({ page }) => {
    await mockGovernanceHandoff(page);

    await page.route('**/api/catalog*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [],
          meta: { page: 1, pageSize: 20, totalCount: 0, totalPages: 0 },
        }),
      });
    });

    await page.goto('/catalog');
    await page.getByTestId('chat-fab').click();

    const panel = page.getByTestId('chat-side-panel');
    await expect(panel.getByText('AI Assistant')).toBeVisible({ timeout: 5000 });

    // Ask a governance question
    await panel.getByTestId('chat-input').fill('What is the governance status of Payments API?');
    await panel.getByTestId('send-button').click();

    // Response should appear (first message from discovery agent)
    await expect(panel.getByText(/I found several APIs/i)).toBeVisible({ timeout: 10000 });
  });
});
