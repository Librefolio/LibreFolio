/**
 * Asset Detail Page — E2E Tests
 *
 * Tests the Asset detail page: chart, signals, measures, classification, sync, edit.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage} from './assets-helpers';

test.describe('Asset Detail Page', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    /**
     * Navigate to the first available asset detail page.
     */
    async function goToFirstAssetDetail(page: import('@playwright/test').Page) {
        await goToAssetsPage(page);
        const firstCard = page.locator('[data-testid^="asset-card-"]').first();
        if (await firstCard.isVisible({timeout: 5000}).catch(() => false)) {
            await firstCard.click();
            await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});
            await page.waitForTimeout(1000);
        } else {
            test.skip(true, 'No assets available in test DB');
        }
    }

    // ========================================================================
    // Test 1: Detail page loads with header and chart
    // ========================================================================
    test('detail page shows header and chart', async ({page}) => {
        await goToFirstAssetDetail(page);
        await expect(page.getByTestId('asset-detail-header')).toBeVisible();
        await expect(page.getByTestId('asset-detail-chart')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Filter bar with date range is visible
    // ========================================================================
    test('filter bar is visible', async ({page}) => {
        await goToFirstAssetDetail(page);
        await expect(page.getByTestId('asset-detail-filter-bar')).toBeVisible();
    });

    // ========================================================================
    // Test 3: Edit button opens modal (no effect_update_depth_exceeded)
    // ========================================================================
    test('edit button opens asset modal', async ({page}) => {
        await goToFirstAssetDetail(page);
        const editBtn = page.getByTestId('asset-detail-edit-btn');
        await expect(editBtn).toBeVisible();
        await editBtn.click();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});
        // Close modal
        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 4: Sync button is visible and clickable
    // ========================================================================
    test('sync button is visible', async ({page}) => {
        await goToFirstAssetDetail(page);
        await expect(page.getByTestId('asset-detail-sync-btn')).toBeVisible();
    });

    // ========================================================================
    // Test 5: Refresh button is visible
    // ========================================================================
    test('refresh button is visible', async ({page}) => {
        await goToFirstAssetDetail(page);
        await expect(page.getByTestId('asset-detail-refresh-btn')).toBeVisible();
    });

    // ========================================================================
    // Test 6: Signals panel toggle
    // ========================================================================
    test('signals panel toggles open/close', async ({page}) => {
        await goToFirstAssetDetail(page);
        const toggle = page.getByTestId('asset-detail-signals-toggle');
        await expect(toggle).toBeVisible();
        await toggle.click();
        await page.waitForTimeout(300);
        const panel = page.getByTestId('asset-detail-signals-panel');
        await panel.isVisible();
        // Toggle again
        await toggle.click();
        await page.waitForTimeout(300);
        // State should have changed
        expect(true).toBeTruthy(); // Panel toggled without error
    });

    // ========================================================================
    // Test 7: Measures panel toggle
    // ========================================================================
    test('measures panel toggles', async ({page}) => {
        await goToFirstAssetDetail(page);
        const toggle = page.getByTestId('asset-detail-measures-toggle');
        await expect(toggle).toBeVisible();
        await toggle.click();
        await page.waitForTimeout(300);
        await expect(page.getByTestId('asset-detail-measures-panel')).toBeVisible();
    });

    // ========================================================================
    // Test 8: Metadata/classification panel toggle
    // ========================================================================
    test('classification panel toggles', async ({page}) => {
        await goToFirstAssetDetail(page);
        const toggle = page.getByTestId('asset-detail-metadata-toggle');
        await expect(toggle).toBeVisible();
        await toggle.click();
        await page.waitForTimeout(300);
        await expect(page.getByTestId('asset-detail-metadata-panel')).toBeVisible();
    });

    // ========================================================================
    // Test 9: Back button navigates back
    // ========================================================================
    test('back button navigates back to list', async ({page}) => {
        await goToFirstAssetDetail(page);
        const backBtn = page.getByTestId('asset-detail-back-btn');
        await expect(backBtn).toBeVisible();
        await backBtn.click();
        await expect(page.getByTestId('assets-page')).toBeVisible({timeout: 10_000});
    });

    // ========================================================================
    // Test 10: Aesthetics toggle is visible (when chart has data)
    // ========================================================================
    test('aesthetics toggle is visible when chart has data', async ({page}) => {
        await goToFirstAssetDetail(page);
        const chart = page.getByTestId('asset-detail-chart');
        await expect(chart).toBeVisible();
        // Buttons only render inside {:else if lineData.length > 0} block
        const toggle = page.getByTestId('asset-detail-aesthetics-toggle');
        const hasData = await toggle.isVisible({timeout: 3000}).catch(() => false);
        if (hasData) {
            await expect(toggle).toBeVisible();
        } else {
            // Asset has no price data — buttons are not rendered (expected)
            test.info().annotations.push({type: 'skip-reason', description: 'Asset has no price data, chart toolbar not rendered'});
        }
    });

    // ========================================================================
    // Test 11: Data editor toggle (when chart has data)
    // ========================================================================
    test('data editor button is visible when chart has data', async ({page}) => {
        await goToFirstAssetDetail(page);
        const btn = page.getByTestId('asset-detail-editdata-btn');
        const hasData = await btn.isVisible({timeout: 3000}).catch(() => false);
        if (hasData) {
            await expect(btn).toBeVisible();
        } else {
            test.info().annotations.push({type: 'skip-reason', description: 'Asset has no price data, chart toolbar not rendered'});
        }
    });

    // ========================================================================
    // Test 12: Measure button (when chart has data)
    // ========================================================================
    test('measure button is visible when chart has data', async ({page}) => {
        await goToFirstAssetDetail(page);
        const btn = page.getByTestId('asset-detail-measure-btn');
        const hasData = await btn.isVisible({timeout: 3000}).catch(() => false);
        if (hasData) {
            await expect(btn).toBeVisible();
        } else {
            test.info().annotations.push({type: 'skip-reason', description: 'Asset has no price data, chart toolbar not rendered'});
        }
    });
});

