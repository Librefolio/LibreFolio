/**
 * FX E2E Test Helpers
 *
 * Shared utility functions for FX E2E tests.
 * Recovered and adapted from the old fx-routes.spec.ts.
 */

import {expect} from '@playwright/test';
import {navigateTo} from '../fixtures/auth-helpers';

export const API_BASE = '/api/v1';

/**
 * Navigate to FX page and wait for content to load.
 */
export async function goToFxPage(page: import('@playwright/test').Page) {
    await navigateTo(page, '/fx');
    await page.waitForSelector('[data-testid="fx-page"]', {timeout: 15_000});
    // Wait for loading to complete (skeleton → content)
    await page.waitForTimeout(1000);
}

/**
 * Open Add Pair modal.
 */
export async function openAddPairModal(page: import('@playwright/test').Page) {
    await page.getByTestId('fx-add-pair-button').click();
    await expect(page.getByTestId('fx-add-pair-modal')).toBeVisible({timeout: 3000});
}

/**
 * Select a currency in a CurrencySearchSelect by typing and clicking option.
 * @param page - The Playwright page
 * @param container - The parent container that wraps the CurrencySearchSelect
 * @param currencyCode - ISO currency code to search for (e.g. "EUR")
 */
export async function selectCurrency(page: import('@playwright/test').Page, container: import('@playwright/test').Locator, currencyCode: string) {
    // Click the combobox trigger to open dropdown
    await container.locator('[role="combobox"]').click();
    await page.waitForTimeout(200);

    // Type currency code in search input
    const searchInput = container.locator('input[type="text"]');
    await searchInput.fill(currencyCode);
    await page.waitForTimeout(500); // Wait for search results

    // Click the matching option in the listbox
    const listbox = page.locator('[role="listbox"]');
    await expect(listbox).toBeVisible({timeout: 3000});

    // Find option that contains the currency code
    const option = listbox.locator('[role="option"]').filter({hasText: currencyCode}).first();
    await option.click();
    await page.waitForTimeout(200);
}

/**
 * Navigate to FX detail page for a given pair slug.
 */
export async function goToFxDetailPage(page: import('@playwright/test').Page, pairSlug: string) {
    await navigateTo(page, `/fx/${pairSlug}`);
    await page.waitForSelector('[data-testid="fx-detail-page"]', {timeout: 15_000});
    await page.waitForTimeout(1000);
}
