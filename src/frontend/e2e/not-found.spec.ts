import { test, expect } from '@playwright/test';

test.describe('404 Not Found', () => {
  test('shows 404 page for non-existent routes', async ({ page }) => {
    await page.goto('/this-page-does-not-exist');
    await expect(page.getByText('404')).toBeVisible();
    await expect(page.getByText(/page not found/i)).toBeVisible();
    await expect(page.getByText(/does not exist or has been moved/i)).toBeVisible();
  });

  test('404 page has a link back to homepage', async ({ page }) => {
    await page.goto('/this-page-does-not-exist');
    const homeLink = page.getByRole('link', { name: /go to homepage/i });
    await expect(homeLink).toBeVisible();
  });
});
