/**
 * E2E tests for the Admin — API Center Backup UI.
 *
 * Mocks the BFF backup endpoints with `page.route()` and injects a Portal.Admin
 * user via `page.addInitScript()` so the admin sidebar nav and page content
 * render correctly without a live Entra ID session.
 */

import { test, expect, type Page } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';
import type {
  BackupListResponse,
  BackupSummary,
  BackupDownloadResponse,
} from '../../lib/backup-api';

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

const MOCK_BACKUP: BackupSummary = {
  backupId: 'apic-backup-2026-04-28T12-00-00Z',
  sourceServiceName: 'apic-test',
  timestamp: '2026-04-28T12:00:00Z',
  blobName: 'apic-backup-2026-04-28T12-00-00Z.zip',
  sizeBytes: 4096,
  sizeFormatted: '4.0 KB',
  counts: { apis: 2, versions: 2, definitions: 2, deployments: 2, environments: 1 },
  retentionTiers: ['hourly', 'daily'],
  status: 'completed',
  durationMs: 1234,
};

const MOCK_LIST: BackupListResponse = {
  data: [MOCK_BACKUP],
  pagination: { continuationToken: null, hasMore: false },
};

const MOCK_DOWNLOAD: BackupDownloadResponse = {
  backupId: MOCK_BACKUP.backupId,
  downloadUrl: 'https://fake.blob.example.com/backup.zip?sas=token',
  expiresAt: '2026-04-28T13:00:00Z',
};

const SCREENSHOT_DIR = path.join('/tmp', 'admin-backup-screenshots');
function ensureScreenshotDir() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}
function screenshotPath(name: string) {
  return path.join(SCREENSHOT_DIR, `${name}.png`);
}

async function setMockUser(page: Page, user: AuthUser | null) {
  await page.addInitScript((u) => {
    (window as Window & { __PLAYWRIGHT_USER__?: typeof u }).__PLAYWRIGHT_USER__ = u ?? undefined;
  }, user);
}

async function mockBackupRoutes(page: Page, response: BackupListResponse = MOCK_LIST) {
  await page.route('**/api/admin/backups*', async (route) => {
    const url = route.request().url();
    if (url.includes('/download')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_DOWNLOAD),
      });
      return;
    }
    if (/\/api\/admin\/backups\/[^/?]+(\?|$)/.test(url)) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_BACKUP),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });
}

test.describe('Admin Backup — Access control', () => {
  test('non-admin user sees Access Denied', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, REGULAR_USER);
    await page.goto('/admin/backup');

    await expect(page.getByText(/access denied/i)).toBeVisible();
    await page.screenshot({ path: screenshotPath('access-denied'), fullPage: true });
  });
});

test.describe('Admin Backup — Listing', () => {
  test('admin sees the backup table populated', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockBackupRoutes(page);

    await page.goto('/admin/backup');

    await expect(page.getByRole('heading', { name: /api center backups/i })).toBeVisible();
    await expect(page.getByTestId(`backup-row-${MOCK_BACKUP.backupId}`)).toBeVisible();
    await expect(page.getByText(MOCK_BACKUP.backupId)).toBeVisible();
    await expect(page.getByText('4.0 KB')).toBeVisible();
    await page.screenshot({ path: screenshotPath('backup-list'), fullPage: true });
  });

  test('admin sees the empty state when no backups exist', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockBackupRoutes(page, {
      data: [],
      pagination: { continuationToken: null, hasMore: false },
    });

    await page.goto('/admin/backup');

    await expect(page.getByTestId('backup-empty')).toBeVisible();
    await page.screenshot({ path: screenshotPath('backup-empty'), fullPage: true });
  });
});

test.describe('Admin Backup — Download', () => {
  test('clicking download requests a SAS URL and opens it in a new tab', async ({
    page,
    context,
  }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockBackupRoutes(page);

    await page.goto('/admin/backup');
    await expect(page.getByTestId(`backup-row-${MOCK_BACKUP.backupId}`)).toBeVisible();

    const downloadRequest = page.waitForRequest((req) =>
      req.url().includes(`/api/admin/backups/${MOCK_BACKUP.backupId}/download`)
    );
    const popupPromise = context.waitForEvent('page', { timeout: 5000 }).catch(() => null);

    await page.getByLabel(`Download ${MOCK_BACKUP.backupId}`).click();

    await downloadRequest;

    // The popup may be blocked in headless mode — the snackbar success message
    // is the deterministic signal that the SAS exchange succeeded.
    await expect(page.getByTestId('backup-snackbar')).toContainText(/Download started/i);
    await popupPromise;
    await page.screenshot({ path: screenshotPath('backup-download'), fullPage: true });
  });

  test('shows error snackbar when backup storage is not configured (503)', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    // Custom routing: list returns OK, download returns 503
    await page.route('**/api/admin/backups*', async (route) => {
      const url = route.request().url();
      if (url.includes('/download')) {
        await route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: {
              code: 'BACKUP_NOT_CONFIGURED',
              message: 'Backup storage is not configured for this environment',
            },
          }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_LIST),
      });
    });

    await page.goto('/admin/backup');
    await expect(page.getByTestId(`backup-row-${MOCK_BACKUP.backupId}`)).toBeVisible();

    await page.getByLabel(`Download ${MOCK_BACKUP.backupId}`).click();

    await expect(page.getByTestId('backup-snackbar')).toContainText(
      /BACKUP_NOT_CONFIGURED|not configured/i
    );
    await page.screenshot({ path: screenshotPath('backup-download-503'), fullPage: true });
  });
});
