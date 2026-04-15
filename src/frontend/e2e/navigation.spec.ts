import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('sidebar Home item is selected by default', async ({ page }) => {
    await page.goto('/');
    const homeButton = page.getByRole('button', { name: /home/i });
    await expect(homeButton).toBeVisible();
  });

  test('clicking sidebar items updates selection', async ({ page }) => {
    await page.goto('/');
    const catalogButton = page.getByRole('button', { name: /api catalog/i });
    await catalogButton.click();
    // The button should now be selected (MUI adds Mui-selected class)
    await expect(catalogButton).toHaveClass(/Mui-selected/);
  });

  test('header menu button is present', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: /toggle navigation/i })).toBeVisible();
  });

  test('user avatar is present in header', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByLabel('user avatar')).toBeVisible();
  });
});
