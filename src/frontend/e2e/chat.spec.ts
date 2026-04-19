import { test, expect } from '@playwright/test';

/**
 * Mock the BFF chat stream endpoint to return a simple SSE sequence.
 */
async function mockChatStream(
  page: Parameters<Parameters<typeof test>[1]>[0],
  options: {
    sessionId?: string;
    content?: string;
    error?: string;
  } = {}
) {
  const sessionId = options.sessionId ?? 'test-session-1';
  const content = options.content ?? 'Hello! I can help you discover APIs.';

  await page.route('**/api/chat/stream', async (route) => {
    if (options.error) {
      // Simulate an error event
      const body = [
        `data: ${JSON.stringify({ type: 'start', sessionId })}\n\n`,
        `data: ${JSON.stringify({ type: 'error', error: options.error, sessionId })}\n\n`,
      ].join('');
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body,
      });
      return;
    }

    // Simulate a streaming response with a start, content, and end event
    const msgId = 'test-msg-1';
    const now = new Date().toISOString();
    const body = [
      `data: ${JSON.stringify({ type: 'start', sessionId })}\n\n`,
      `data: ${JSON.stringify({ type: 'content', content: content.slice(0, 10) })}\n\n`,
      `data: ${JSON.stringify({ type: 'content', content: content.slice(10) })}\n\n`,
      `data: ${JSON.stringify({
        type: 'end',
        message: { id: msgId, role: 'assistant', content, citations: null, timestamp: now },
        sessionId,
      })}\n\n`,
    ].join('');

    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body,
    });
  });
}

test.describe('Chat Page', () => {
  test('renders the /chat page with heading and input', async ({ page }) => {
    await page.goto('/chat');

    await expect(page.getByRole('heading', { name: /AI Assistant/i })).toBeVisible();
    await expect(page.getByTestId('chat-input')).toBeVisible();
    await expect(page.getByTestId('send-button')).toBeVisible();
  });

  test('shows suggested starter prompts on empty conversation', async ({ page }) => {
    await page.goto('/chat');

    await expect(page.getByTestId('chat-suggestions')).toBeVisible();
    await expect(page.getByText('Show me APIs in production')).toBeVisible();
    await expect(page.getByText('Which APIs support GraphQL?')).toBeVisible();
  });

  test('clicking a suggested prompt sends the message', async ({ page }) => {
    await mockChatStream(page, { content: 'Here are production APIs.' });
    await page.goto('/chat');

    await page.getByText('Show me APIs in production').click();

    // The prompt should appear as a user message
    await expect(page.getByText('Show me APIs in production')).toBeVisible();
    // The suggestions should disappear
    await expect(page.getByTestId('chat-suggestions')).not.toBeVisible({ timeout: 5000 });
  });

  test('user can type and send a message', async ({ page }) => {
    await mockChatStream(page, { content: 'I found 5 payment APIs.' });
    await page.goto('/chat');

    const input = page.getByTestId('chat-input');
    await input.fill('What payment APIs are available?');
    await page.getByTestId('send-button').click();

    // User message should be visible
    await expect(page.getByText('What payment APIs are available?')).toBeVisible();

    // Assistant response should appear
    await expect(page.getByText(/I found 5 payment APIs/)).toBeVisible({ timeout: 10000 });
  });

  test('send button is disabled when input is empty', async ({ page }) => {
    await page.goto('/chat');

    const sendButton = page.getByTestId('send-button');
    await expect(sendButton).toBeDisabled();

    // After typing something it should be enabled
    await page.getByTestId('chat-input').fill('Hello');
    await expect(sendButton).not.toBeDisabled();
  });

  test('"New conversation" button resets the chat', async ({ page }) => {
    await mockChatStream(page, { content: 'Hello there!' });
    await page.goto('/chat');

    // Send a message to create some conversation history
    await page.getByTestId('chat-input').fill('Hi');
    await page.getByTestId('send-button').click();
    await expect(page.getByText('Hi')).toBeVisible();

    // Click new conversation button
    await page.getByTestId('new-conversation-button').click();

    // Suggestions should reappear (conversation reset)
    await expect(page.getByTestId('chat-suggestions')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Chat Side Panel', () => {
  test('floating action button is visible on catalog page', async ({ page }) => {
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
    await expect(page.getByTestId('chat-fab')).toBeVisible();
  });

  test('clicking FAB opens the side panel', async ({ page }) => {
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

    // Panel should be visible with AI Assistant heading
    await expect(page.getByText('AI Assistant')).toBeVisible({ timeout: 5000 });
    // Chat input should also be visible in the panel
    await expect(page.getByTestId('chat-input')).toBeVisible();
  });

  test('panel chat persists conversation when navigating between pages', async ({ page }) => {
    await mockChatStream(page, { content: 'REST APIs are great for web services.' });

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

    // Open the panel on catalog page and send a message
    await page.goto('/catalog');
    await page.getByTestId('chat-fab').click();
    await page.getByTestId('chat-input').fill('What REST APIs are there?');
    await page.getByTestId('send-button').click();

    // Wait for the user message to appear
    await expect(page.getByText('What REST APIs are there?')).toBeVisible({ timeout: 5000 });

    // Navigate to a different page
    await page.goto('/chat');

    // The conversation should have persisted (message history in context)
    // The chat page shows message history from context
    await expect(page.getByText('What REST APIs are there?')).toBeVisible({ timeout: 5000 });
  });
});
