/**
 * Assets E2E Test Helpers
 *
 * Shared utility functions for Asset E2E tests.
 * Follows the pattern established by fx-helpers.ts.
 */

import {expect} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';

export const API_BASE = '/api/v1';

/**
 * Navigate to Assets list page and wait for content to load.
 */
export async function goToAssetsPage(page: import('@playwright/test').Page) {
    await navigateTo(page, '/assets');
    await page.waitForSelector('[data-testid="assets-page"]', {timeout: 15_000});
    // The page loads in two waves — list, then per-row prices — and says so via `data-busy`.
    await page.waitForSelector('[data-testid="assets-page"][data-busy="false"]', {timeout: 20_000});
}

/**
 * Navigate to Asset detail page by asset ID.
 */
export async function goToAssetDetailPage(page: import('@playwright/test').Page, assetId: string) {
    await navigateTo(page, `/assets/${assetId}`);
    await page.waitForSelector('[data-testid="asset-detail-page"]', {timeout: 15_000});
    // The page says when it has finished loading; don't guess a duration for it.
    await page.waitForSelector('[data-testid="asset-detail-page"][data-busy="false"]', {timeout: 20_000});
}

/**
 * Navigate to a specific asset detail page by searching for its name.
 * Searches in the asset list, clicks the matching card, and waits for the detail page.
 *
 * @param page - Playwright page
 * @param assetName - Display name to search for (e.g. "Apple")
 */
export async function navigateToAssetByName(page: import('@playwright/test').Page, assetName: string) {
    // Type in search input to filter
    const searchInput = page.getByTestId('assets-search-input');
    if (await searchInput.isVisible({timeout: 3000}).catch(() => false)) {
        await searchInput.fill(assetName);
        await page.waitForTimeout(800);
    }

    // Click the first matching card
    const card = page.locator('[data-testid^="asset-card-"]').first();
    if (await card.isVisible({timeout: 3000}).catch(() => false)) {
        await card.click();
    } else {
        // Fallback: try table row
        const row = page.locator('[data-testid^="asset-row-"]').first();
        if (await row.isVisible({timeout: 2000}).catch(() => false)) {
            await row.click();
        }
    }

    await page.waitForSelector('[data-testid="asset-detail-page"]', {timeout: 20_000});
    // Wait for ECharts canvas to render
    await page.waitForSelector('canvas', {timeout: 18_000}).catch(() => null);
    await page.waitForTimeout(1500);
}

/**
 * Open the Create Asset modal from the list page.
 */
export async function openCreateAssetModal(page: import('@playwright/test').Page) {
    await page.getByTestId('assets-add-button').click();
    await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});
}

/**
 * Open the Edit Asset modal from the detail page.
 */
export async function openEditAssetModal(page: import('@playwright/test').Page) {
    await page.getByTestId('asset-detail-edit-btn').click();
    await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});
}
