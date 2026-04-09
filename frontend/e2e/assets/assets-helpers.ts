/**
 * Assets E2E Test Helpers
 *
 * Shared utility functions for Asset E2E tests.
 * Follows the pattern established by fx-helpers.ts.
 */

import {expect} from '@playwright/test';
import {navigateTo} from '../fixtures/auth-helpers';

export const API_BASE = '/api/v1';

/**
 * Navigate to Assets list page and wait for content to load.
 */
export async function goToAssetsPage(page: import('@playwright/test').Page) {
    await navigateTo(page, '/assets');
    await page.waitForSelector('[data-testid="assets-page"]', {timeout: 15_000});
    // Wait for loading to complete (skeleton → content)
    await page.waitForTimeout(1000);
}

/**
 * Navigate to Asset detail page by asset ID.
 */
export async function goToAssetDetailPage(page: import('@playwright/test').Page, assetId: string) {
    await navigateTo(page, `/assets/${assetId}`);
    await page.waitForSelector('[data-testid="asset-detail-page"]', {timeout: 15_000});
    await page.waitForTimeout(1000);
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

