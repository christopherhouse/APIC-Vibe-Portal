/**
 * E2E tests for the Admin — Agent Management UI.
 *
 * Uses page.route() to mock the BFF admin agent endpoints and
 * page.addInitScript() to inject a mock Portal.Admin user so the
 * sidebar admin nav and page content render correctly without a live
 * Entra ID session.
 *
 * Covers:
 *  - Non-admin user sees Access Denied
 *  - Admin user loads the agent list
 *  - Admin user opens the Details dialog
 *  - Admin user opens the Test dialog
 */

import { test, expect, type Page } from '@playwright/test';
import type {
  AgentInfo,
  AgentDetail,
  AgentStats,
  AgentTestResponse,
} from '../../lib/admin-agent-api';
import * as path from 'node:path';
import * as fs from 'node:fs';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuthUser {
  name: string;
  email: string;
  id: string;
  roles: string[];
}

const ADMIN_USER: AuthUser = {
  name: 'Alice Admin',
  email: 'alice@contoso.com',
  id: 'user-admin-1',
  roles: ['Portal.Admin'],
};

const REGULAR_USER: AuthUser = {
  name: 'Bob Developer',
  email: 'bob@contoso.com',
  id: 'user-dev-1',
  roles: ['Portal.User'],
};

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_AGENTS: AgentInfo[] = [
  {
    agentId: 'api_discovery',
    name: 'Api Discovery',
    description: 'Helps users discover, search, and explore APIs in the catalog.',
    status: 'active',
    registeredAt: '2026-01-15T10:00:00Z',
  },
  {
    agentId: 'governance',
    name: 'Governance',
    description: 'Evaluates APIs against governance rules and compliance policies.',
    status: 'active',
    registeredAt: '2026-01-15T10:00:00Z',
  },
];

const MOCK_AGENT_DETAIL: AgentDetail = {
  agentId: 'api_discovery',
  name: 'Api Discovery',
  description: 'Helps users discover, search, and explore APIs in the catalog.',
  status: 'active',
  registeredAt: '2026-01-15T10:00:00Z',
  configuration: { name: 'api_discovery', description: 'Helps users discover...' },
  capabilities: ['query_processing', 'tool_calling', 'api_search', 'api_details', 'api_comparison'],
};

const MOCK_AGENT_STATS: AgentStats = {
  agentId: 'api_discovery',
  queriesHandled: 42,
  avgResponseTimeMs: 1230.5,
  successRate: 98.5,
  lastUsedAt: '2026-04-20T12:00:00Z',
};

const MOCK_TEST_RESPONSE: AgentTestResponse = {
  agentId: 'api_discovery',
  query: 'Find payment APIs',
  response: 'I found 3 payment APIs in the catalog.',
  responseTimeMs: 750,
  success: true,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const SCREENSHOT_DIR = path.join('/tmp', 'admin-agents-screenshots');

function ensureScreenshotDir() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function screenshotPath(name: string): string {
  return path.join(SCREENSHOT_DIR, `${name}.png`);
}

async function setMockUser(page: Page, user: AuthUser | null) {
  await page.addInitScript((u) => {
    (window as Window & { __PLAYWRIGHT_USER__?: typeof u }).__PLAYWRIGHT_USER__ = u ?? undefined;
  }, user);
}

async function mockAgentRoutes(page: Page, agents: AgentInfo[] = MOCK_AGENTS) {
  // GET /api/admin/agents → list
  await page.route('**/api/admin/agents', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(agents),
      });
    } else {
      await route.continue();
    }
  });

  // GET /api/admin/agents/:id → detail
  await page.route('**/api/admin/agents/api_discovery', async (route) => {
    if (
      route.request().method() === 'GET' &&
      !route.request().url().includes('/stats') &&
      !route.request().url().includes('/test')
    ) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_AGENT_DETAIL),
      });
    } else {
      await route.continue();
    }
  });

  // GET /api/admin/agents/:id/stats
  await page.route('**/api/admin/agents/*/stats', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_AGENT_STATS),
    });
  });

  // POST /api/admin/agents/:id/test
  await page.route('**/api/admin/agents/*/test', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_TEST_RESPONSE),
      });
    } else {
      await route.continue();
    }
  });
}

// ---------------------------------------------------------------------------
// Tests: Access Denied
// ---------------------------------------------------------------------------

test.describe('Admin Agents — Access Denied', () => {
  test('non-admin user sees Access Denied', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, REGULAR_USER);
    await page.goto('/admin/agents');

    await expect(page.getByText(/access denied/i)).toBeVisible();
    await expect(page.getByText(/Portal\.Admin/)).toBeVisible();

    await page.screenshot({ path: screenshotPath('access-denied-regular-user'), fullPage: true });
  });

  test('unauthenticated user sees Access Denied', async ({ page }) => {
    ensureScreenshotDir();
    await page.goto('/admin/agents');

    await expect(page.getByText(/access denied/i)).toBeVisible();

    await page.screenshot({ path: screenshotPath('access-denied-no-user'), fullPage: true });
  });
});

// ---------------------------------------------------------------------------
// Tests: Agent list
// ---------------------------------------------------------------------------

test.describe('Admin Agents — agent list', () => {
  test('admin user sees Agent Management page with agent cards', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAgentRoutes(page);

    await page.goto('/admin/agents');

    await expect(page.getByRole('heading', { name: /agent management/i })).toBeVisible();
    await expect(page.getByText('Api Discovery')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Governance' })).toBeVisible();

    await page.screenshot({ path: screenshotPath('agents-list'), fullPage: true });
  });

  test('shows empty state when no agents registered', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAgentRoutes(page, []);

    await page.goto('/admin/agents');

    await expect(page.getByRole('heading', { name: /agent management/i })).toBeVisible();
    await expect(page.getByText(/no agents registered/i)).toBeVisible();

    await page.screenshot({ path: screenshotPath('agents-empty'), fullPage: true });
  });
});

// ---------------------------------------------------------------------------
// Tests: Details dialog
// ---------------------------------------------------------------------------

test.describe('Admin Agents — Details dialog', () => {
  test('opens Details dialog when View Details is clicked', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAgentRoutes(page);

    await page.goto('/admin/agents');

    await expect(page.getByText('Api Discovery')).toBeVisible();

    // Click "View Details" for first agent
    await page
      .getByRole('button', { name: /view details/i })
      .first()
      .click();

    // Dialog should open with agent information
    await expect(page.getByRole('dialog')).toBeVisible();

    await page.screenshot({ path: screenshotPath('details-dialog-open'), fullPage: false });
  });
});

// ---------------------------------------------------------------------------
// Tests: Test dialog
// ---------------------------------------------------------------------------

test.describe('Admin Agents — Test dialog', () => {
  test('opens Test dialog when Test button is clicked', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAgentRoutes(page);

    await page.goto('/admin/agents');

    await expect(page.getByText('Api Discovery')).toBeVisible();

    // Click "Test" for first agent card
    await page
      .getByRole('button', { name: /^test$/i })
      .first()
      .click();

    // Dialog should open
    await expect(page.getByRole('dialog')).toBeVisible();

    await page.screenshot({ path: screenshotPath('test-dialog-open'), fullPage: false });
  });
});
