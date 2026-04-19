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
    const main = page.locator('main');

    await expect(main.getByRole('heading', { name: /AI Assistant/i })).toBeVisible();
    await expect(main.getByTestId('chat-input')).toBeVisible();
    await expect(main.getByTestId('send-button')).toBeVisible();
  });

  test('shows suggested starter prompts on empty conversation', async ({ page }) => {
    await page.goto('/chat');
    const main = page.locator('main');

    await expect(main.getByTestId('chat-suggestions')).toBeVisible();
    await expect(main.getByText('Show me APIs in production')).toBeVisible();
    await expect(main.getByText('Which APIs support GraphQL?')).toBeVisible();
  });

  test('clicking a suggested prompt sends the message', async ({ page }) => {
    await mockChatStream(page, { content: 'Here are production APIs.' });
    await page.goto('/chat');
    const main = page.locator('main');

    await main.getByText('Show me APIs in production').click();

    // The prompt should appear as a user message
    await expect(main.getByText('Show me APIs in production')).toBeVisible();
    // The suggestions should disappear
    await expect(main.getByTestId('chat-suggestions')).not.toBeVisible({ timeout: 5000 });
  });

  test('user can type and send a message', async ({ page }) => {
    await mockChatStream(page, { content: 'I found 5 payment APIs.' });
    await page.goto('/chat');
    const main = page.locator('main');

    const input = main.getByTestId('chat-input');
    await input.fill('What payment APIs are available?');
    await main.getByTestId('send-button').click();

    // User message should be visible
    await expect(main.getByText('What payment APIs are available?')).toBeVisible();

    // Assistant response should appear
    await expect(main.getByText(/I found 5 payment APIs/)).toBeVisible({ timeout: 10000 });
  });

  test('send button is disabled when input is empty', async ({ page }) => {
    await page.goto('/chat');
    const main = page.locator('main');

    const sendButton = main.getByTestId('send-button');
    await expect(sendButton).toBeDisabled();

    // After typing something it should be enabled
    await main.getByTestId('chat-input').fill('Hello');
    await expect(sendButton).not.toBeDisabled();
  });

  test('"New conversation" button resets the chat', async ({ page }) => {
    await mockChatStream(page, { content: 'Hello there!' });
    await page.goto('/chat');
    const main = page.locator('main');

    // Send a message to create some conversation history
    await main.getByTestId('chat-input').fill('Hi');
    await main.getByTestId('send-button').click();
    await expect(main.getByText('Hi')).toBeVisible();

    // Click new conversation button
    await main.getByTestId('new-conversation-button').click();

    // Suggestions should reappear (conversation reset)
    await expect(main.getByTestId('chat-suggestions')).toBeVisible({ timeout: 5000 });
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
    const panel = page.getByTestId('chat-side-panel');
    await expect(panel.getByText('AI Assistant')).toBeVisible({ timeout: 5000 });
    // Chat input should also be visible in the panel
    await expect(panel.getByTestId('chat-input')).toBeVisible();
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
    const panel = page.getByTestId('chat-side-panel');
    await panel.getByTestId('chat-input').fill('What REST APIs are there?');
    await panel.getByTestId('send-button').click();

    // Wait for the user message to appear
    await expect(panel.getByText('What REST APIs are there?')).toBeVisible({ timeout: 5000 });

    // Navigate to chat page via client-side navigation (preserves React state)
    const mainNav = page.getByRole('navigation', { name: /main navigation/i });
    await mainNav.getByText('AI Assistant').click();
    await expect(page).toHaveURL(/\/chat/);
    const main = page.locator('main');

    // The conversation should have persisted (message history in context)
    // The chat page shows message history from context
    await expect(main.getByText('What REST APIs are there?')).toBeVisible({ timeout: 5000 });
  });
});
