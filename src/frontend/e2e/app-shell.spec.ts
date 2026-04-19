import { test, expect } from '@playwright/test';

test.describe('Application Shell', () => {
  test('homepage redirects to catalog page', async ({ page }) => {
    // Mock the catalog API to avoid fetch errors
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
    await page.goto('/');
    await expect(page).toHaveURL(/\/catalog/);
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
  });

  test('header displays app title and search bar', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('APIC Vibe Portal', { exact: true })).toBeVisible();
    await expect(page.getByPlaceholder(/search apis/i)).toBeVisible();
  });

  test('sidebar navigation is visible with main nav items', async ({ page }) => {
    await page.goto('/');
    const mainNav = page.getByRole('navigation', { name: /main navigation/i });
    await expect(mainNav).toBeVisible();
    await expect(mainNav.getByText('Home')).toBeVisible();
    await expect(mainNav.getByText('API Catalog')).toBeVisible();
    await expect(mainNav.getByText('AI Assistant')).toBeVisible();
  });

  test('sidebar shows secondary nav items', async ({ page }) => {
    await page.goto('/');
    const secondaryNav = page.getByRole('navigation', { name: /secondary navigation/i });
    await expect(secondaryNav).toBeVisible();
    await expect(secondaryNav.getByText('Settings')).toBeVisible();
    await expect(secondaryNav.getByText('Help')).toBeVisible();
  });

  test('footer is visible with copyright text', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText(/apic vibe portal.*powered by azure api center/i)).toBeVisible();
  });

  test('hamburger button collapses and expands the sidebar', async ({ page }) => {
    await page.goto('/');

    // Sidebar starts expanded — nav labels are visible
    await expect(page.getByText('Home')).toBeVisible();
    await expect(page.getByText('API Catalog')).toBeVisible();

    // Click hamburger to collapse
    await page.getByRole('button', { name: /toggle navigation/i }).click();

    // Nav labels should no longer be visible (collapsed to icon-only)
    await expect(page.getByText('Home')).not.toBeVisible();
    await expect(page.getByText('API Catalog')).not.toBeVisible();

    // Click hamburger again to expand
    await page.getByRole('button', { name: /toggle navigation/i }).click();

    // Nav labels should be visible again
    await expect(page.getByText('Home')).toBeVisible();
    await expect(page.getByText('API Catalog')).toBeVisible();
  });
});
