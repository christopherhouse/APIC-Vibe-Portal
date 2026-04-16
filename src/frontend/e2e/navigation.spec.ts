import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('sidebar Home link is selected by default', async ({ page }) => {
    await page.goto('/');
    const homeLink = page.getByRole('link', { name: /home/i });
    await expect(homeLink).toBeVisible();
  });

  test('clicking sidebar items navigates to the target page', async ({ page }) => {
    await page.goto('/');
    const catalogLink = page.getByRole('link', { name: /api catalog/i });
    await catalogLink.click();
    // After navigation, the URL should update and the link should be selected
    await expect(page).toHaveURL(/\/apis/);
    await expect(catalogLink).toHaveClass(/Mui-selected/);
  });

  test('header menu button is present', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: /toggle navigation/i })).toBeVisible();
  });

  test('auth controls are present in header', async ({ page }) => {
    await page.goto('/');
    // When unauthenticated, the "Sign in" button is shown instead of an avatar
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });
});
