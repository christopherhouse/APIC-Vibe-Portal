import { test, expect, type Page } from '@playwright/test';
import type { SearchResultItem, BffSearchResponse, SuggestResponse } from '@/lib/search-api';
import { ApiKind, ApiLifecycle } from '@apic-vibe-portal/shared';

// ---------------------------------------------------------------------------
// Mock helpers
// ---------------------------------------------------------------------------

function makeMockResult(id: string, overrides: Partial<SearchResultItem> = {}): SearchResultItem {
  return {
    apiId: id,
    apiName: `api-${id}`,
    title: `Search API ${id}`,
    description: `Description for search API ${id}.`,
    kind: ApiKind.REST,
    lifecycleStage: ApiLifecycle.Production,
    score: 0.9,
    ...overrides,
  };
}

function makeMockSearchResponse(
  count: number,
  overrides: Partial<BffSearchResponse> = {}
): BffSearchResponse {
  const results = Array.from({ length: count }, (_, i) => makeMockResult(String(i + 1)));
  return {
    results,
    totalCount: count,
    facets: {
      kind: [
        { value: 'rest', count: count },
        { value: 'graphql', count: 0 },
      ],
      lifecycle: [
        { value: 'production', count: count },
        { value: 'development', count: 0 },
      ],
      tags: [],
    },
    queryDuration: 42,
    ...overrides,
  };
}

async function mockSearchApi(page: Page, response: BffSearchResponse) {
  await page.route('**/api/search', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });
}

async function mockSuggestApi(page: Page, suggestions: SuggestResponse['suggestions']) {
  await page.route('**/api/search/suggest*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ suggestions }),
    });
  });
}

// Mock catalog API (needed for pages that include the header which uses catalog)
async function mockCatalogApi(page: Page) {
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
}

// ---------------------------------------------------------------------------
// Search Input Tests
// ---------------------------------------------------------------------------

test.describe('Search Input', () => {
  test('search bar is visible in the header', async ({ page }) => {
    await mockCatalogApi(page);
    await page.goto('/catalog');

    const searchInput = page.getByRole('combobox', { name: /search/i });
    await expect(searchInput).toBeVisible();
  });

  test('typing in the search bar updates the input value', async ({ page }) => {
    await mockCatalogApi(page);
    await mockSuggestApi(page, []);
    await page.goto('/catalog');

    const searchInput = page.getByRole('combobox', { name: /search/i });
    await searchInput.fill('petstore');
    await expect(searchInput).toHaveValue('petstore');
  });

  test('pressing Enter in search bar navigates to /search page', async ({ page }) => {
    await mockCatalogApi(page);
    await mockSearchApi(page, makeMockSearchResponse(0));
    await mockSuggestApi(page, []);
    await page.goto('/catalog');

    const searchInput = page.getByRole('combobox', { name: /search/i });
    await searchInput.fill('petstore');
    await searchInput.press('Enter');

    await expect(page).toHaveURL(/\/search\?q=petstore/);
  });

  test('clear button resets the search input', async ({ page }) => {
    await mockCatalogApi(page);
    await mockSuggestApi(page, []);
    await page.goto('/catalog');

    const searchInput = page.getByRole('combobox', { name: /search/i });
    await searchInput.fill('test query');

    const clearButton = page.getByRole('button', { name: /clear search/i });
    await expect(clearButton).toBeVisible();
    await clearButton.click();

    await expect(searchInput).toHaveValue('');
  });
});

// ---------------------------------------------------------------------------
// Autocomplete Tests
// ---------------------------------------------------------------------------

test.describe('Autocomplete', () => {
  test('autocomplete dropdown appears after typing 2+ characters', async ({ page }) => {
    await mockCatalogApi(page);
    await mockSuggestApi(page, [
      { apiId: 'api-1', title: 'Petstore API', description: 'Manage pets', kind: ApiKind.REST },
    ]);
    await page.goto('/catalog');

    const searchInput = page.getByRole('combobox', { name: /search/i });
    await searchInput.fill('pe');

    // Wait for the debounce and the dropdown to appear
    await expect(page.getByTestId('suggestion-api-1')).toBeVisible({ timeout: 5000 });
  });

  test('autocomplete does NOT appear for single character', async ({ page }) => {
    await mockCatalogApi(page);
    await mockSuggestApi(page, [
      { apiId: 'api-1', title: 'Petstore API', description: 'Manage pets', kind: ApiKind.REST },
    ]);
    await page.goto('/catalog');

    const searchInput = page.getByRole('combobox', { name: /search/i });
    await searchInput.fill('p');
    // Wait a moment for any debounce
    await page.waitForTimeout(500);

    await expect(page.getByRole('listbox')).not.toBeVisible();
  });

  test('clicking a suggestion navigates to the catalog API detail page', async ({ page }) => {
    await mockCatalogApi(page);
    await mockSuggestApi(page, [
      {
        apiId: 'api-42',
        title: 'Payment API',
        description: 'Process payments',
        kind: ApiKind.REST,
      },
    ]);
    await page.goto('/catalog');

    const searchInput = page.getByRole('combobox', { name: /search/i });
    await searchInput.fill('pay');

    await expect(page.getByTestId('suggestion-api-42')).toBeVisible({ timeout: 5000 });
    await page.getByTestId('suggestion-api-42').click();

    await expect(page).toHaveURL(/\/catalog\/api-42/);
  });

  test('keyboard navigation selects suggestions', async ({ page }) => {
    await mockCatalogApi(page);
    await mockSuggestApi(page, [
      { apiId: 'api-1', title: 'First API', description: 'First', kind: ApiKind.REST },
      { apiId: 'api-2', title: 'Second API', description: 'Second', kind: ApiKind.REST },
    ]);
    await page.goto('/catalog');

    const searchInput = page.getByRole('combobox', { name: /search/i });
    await searchInput.fill('api');

    await expect(page.getByTestId('suggestion-api-1')).toBeVisible({ timeout: 5000 });

    // Navigate to first item
    await searchInput.press('ArrowDown');
    // Select it
    await searchInput.press('Enter');

    await expect(page).toHaveURL(/\/catalog\/api-1/);
  });
});

// ---------------------------------------------------------------------------
// Search Results Page Tests
// ---------------------------------------------------------------------------

test.describe('Search Results Page', () => {
  test('displays search results for a query', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(3));
    await page.goto('/search?q=test');

    await expect(page.getByRole('heading', { name: /search/i })).toBeVisible();
    await expect(page.getByTestId('search-summary')).toBeVisible();
    await expect(page.getByTestId('search-result-1')).toBeVisible();
    await expect(page.getByTestId('search-result-2')).toBeVisible();
    await expect(page.getByTestId('search-result-3')).toBeVisible();
  });

  test('shows query in the search summary', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(5));
    await page.goto('/search?q=petstore');

    await expect(page.getByTestId('search-summary')).toContainText('petstore');
    await expect(page.getByTestId('search-summary')).toContainText('5');
  });

  test('clicking a result card navigates to the catalog detail', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(2));
    await page.goto('/search?q=api');

    await expect(page.getByTestId('search-result-1')).toBeVisible();
    await page.getByTestId('search-result-1').click();

    await expect(page).toHaveURL(/\/catalog\/1/);
  });

  test('shows semantic caption when present in results', async ({ page }) => {
    const response = makeMockSearchResponse(1);
    response.results[0].semanticCaption = 'AI-generated summary for this API.';
    await mockSearchApi(page, response);

    await page.goto('/search?q=api');
    await expect(page.getByTestId('semantic-caption')).toBeVisible();
    await expect(page.getByTestId('semantic-caption')).toContainText(
      'AI-generated summary for this API.'
    );
  });

  test('shows empty query prompt when no q param', async ({ page }) => {
    await page.goto('/search');
    await expect(page.getByText(/Enter a search query/i)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// No Results State Tests
// ---------------------------------------------------------------------------

test.describe('No Results State', () => {
  test('shows no-results state when search returns empty', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(0));
    await page.goto('/search?q=xyznonexistent');

    await expect(page.getByTestId('no-results')).toBeVisible();
    await expect(page.getByText(/No APIs found/)).toBeVisible();
  });

  test('no-results state includes browse catalog link', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(0));
    await page.goto('/search?q=xyznonexistent');

    await expect(page.getByRole('link', { name: /browse catalog/i })).toBeVisible();
  });

  test('clicking browse catalog navigates to /catalog', async ({ page }) => {
    await mockCatalogApi(page);
    await mockSearchApi(page, makeMockSearchResponse(0));
    await page.goto('/search?q=xyznonexistent');

    await page.getByRole('link', { name: /browse catalog/i }).click();
    await expect(page).toHaveURL(/\/catalog/);
  });
});

// ---------------------------------------------------------------------------
// Filtering Tests
// ---------------------------------------------------------------------------

test.describe('Search Filtering', () => {
  test('search page renders filter sidebar', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(3));
    await page.goto('/search?q=api');

    await expect(page.getByTestId('search-filters')).toBeVisible();
  });

  test('applying lifecycle filter updates the URL', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(3));
    await page.goto('/search?q=api');

    await page.getByLabel('Filter by Production').click();
    await expect(page).toHaveURL(/lifecycle=production/);
  });

  test('applying kind filter updates the URL', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(3));
    await page.goto('/search?q=api');

    await page.getByLabel('Filter by REST').click();
    await expect(page).toHaveURL(/kind=rest/);
  });

  test('filter state is preserved in URL (shareability)', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(3));
    await page.goto('/search?q=api&lifecycle=production');

    const productionRadio = page.getByRole('radio', { name: 'Filter by Production' });
    await expect(productionRadio).toBeChecked();
  });

  test('facet counts are displayed when search returns facets', async ({ page }) => {
    const response = makeMockSearchResponse(5);
    response.facets.kind = [{ value: 'rest', count: 5 }];
    await mockSearchApi(page, response);

    await page.goto('/search?q=api');
    await expect(page.getByTestId('facet-kind-rest')).toBeVisible();
  });

  test('clear all removes filters from URL', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(3));
    await page.goto('/search?q=api&lifecycle=production&kind=rest');

    await page.getByText('Clear all').click();
    await expect(page).not.toHaveURL(/lifecycle/);
    await expect(page).not.toHaveURL(/kind/);
  });
});

// ---------------------------------------------------------------------------
// Search Mode Toggle Tests
// ---------------------------------------------------------------------------

test.describe('Search Mode Toggle', () => {
  test('mode toggle is visible on search results page', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(3));
    await page.goto('/search?q=api');

    await expect(page.getByTestId('search-mode-toggle')).toBeVisible();
  });

  test('default mode is hybrid', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(3));
    await page.goto('/search?q=api');

    const hybridBtn = page.getByRole('button', { name: /hybrid search mode/i });
    await expect(hybridBtn).toHaveAttribute('aria-pressed', 'true');
  });

  test('switching to keyword mode updates URL', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(3));
    await page.goto('/search?q=api');

    await page.getByRole('button', { name: /keyword search mode/i }).click();
    await expect(page).toHaveURL(/mode=keyword/);
  });

  test('mode from URL is pre-selected', async ({ page }) => {
    await mockSearchApi(page, makeMockSearchResponse(3));
    await page.goto('/search?q=api&mode=semantic');

    const semanticBtn = page.getByRole('button', { name: /semantic search mode/i });
    await expect(semanticBtn).toHaveAttribute('aria-pressed', 'true');
  });
});
