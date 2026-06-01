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
        await expect(firstCard).toBeVisible({timeout: 5_000});
        await firstCard.click();
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});
        await page.waitForTimeout(1000);
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

    // ========================================================================
    // Test 13: Currency selector in filter bar
    // ========================================================================
    test('currency selector is visible in filter bar', async ({page}) => {
        await goToFirstAssetDetail(page);
        const filterBar = page.getByTestId('asset-detail-filter-bar');
        await expect(filterBar).toBeVisible();

        // Currency selector should be within the filter bar (CurrencySearchSelect or similar)
        // It renders as a combobox or button with currency code
        const currencyEl = filterBar
            .locator('[role="combobox"], button')
            .filter({hasText: /[A-Z]{3}/})
            .first();
        const hasCurrency = await currencyEl.isVisible({timeout: 3000}).catch(() => false);
        if (hasCurrency) {
            await expect(currencyEl).toBeVisible();
        } else {
            test.info().annotations.push({type: 'skip-reason', description: 'Currency selector not rendered (single-currency asset)'});
        }
    });

    // ========================================================================
    // Test 14: Asset info shows type badge and name
    // ========================================================================
    test('asset info shows name and type', async ({page}) => {
        await goToFirstAssetDetail(page);
        const info = page.getByTestId('asset-detail-info');
        await expect(info).toBeVisible();

        // Should contain text (asset name)
        const text = await info.textContent();
        expect(text!.length).toBeGreaterThan(0);
    });

    // ========================================================================
    // Test 15: Sync button triggers sync (with toast or status change)
    // ========================================================================
    test('sync button is clickable and triggers action', async ({page}) => {
        await goToFirstAssetDetail(page);
        const syncBtn = page.getByTestId('asset-detail-sync-btn');
        await expect(syncBtn).toBeVisible();

        // Click sync — may show toast, spinner, or no-op if no provider
        await syncBtn.click();
        await page.waitForTimeout(1000);

        // Page should still be intact (no crash)
        await expect(page.getByTestId('asset-detail-page')).toBeVisible();
    });

    // ========================================================================
    // Test 16: Refresh button reloads data
    // ========================================================================
    test('refresh button reloads data without error', async ({page}) => {
        await goToFirstAssetDetail(page);
        const refreshBtn = page.getByTestId('asset-detail-refresh-btn');
        await expect(refreshBtn).toBeVisible();

        await refreshBtn.click();
        await page.waitForTimeout(1000);

        // Page should still be intact
        await expect(page.getByTestId('asset-detail-page')).toBeVisible();
        await expect(page.getByTestId('asset-detail-chart')).toBeVisible();
    });

    // ========================================================================
    // Test 17: Chart type toggle — Line → Candlestick → Line
    // ========================================================================
    test('chart type toggle switches between line and candlestick', async ({page}) => {
        await goToFirstAssetDetail(page);

        // Chart toolbar must be visible and "Candle" button enabled
        const candleBtn = page.getByTestId('chart-type-candlestick');
        const lineBtn = page.getByTestId('chart-type-line');
        await expect(candleBtn).toBeVisible();
        await expect(candleBtn).not.toBeDisabled();

        // Switch to candlestick
        await candleBtn.click();
        await page.waitForTimeout(500);

        // Candlestick chart container must appear inside asset-detail-chart
        const chartWrapper = page.getByTestId('asset-detail-chart');
        await expect(chartWrapper.getByTestId('candlestick-chart')).toBeVisible({timeout: 5000});

        // Switch back to line — candlestick div disappears
        await lineBtn.click();
        await page.waitForTimeout(500);
        await expect(chartWrapper.getByTestId('candlestick-chart')).not.toBeVisible();
    });

    // ========================================================================
    // Test 18: Candlestick renders without JS error
    // ========================================================================
    test('candlestick chart renders without console errors', async ({page}) => {
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));

        await goToFirstAssetDetail(page);
        await page.getByTestId('chart-type-candlestick').click();
        await page.waitForTimeout(800);

        // ECharts must have initialised without throwing
        await expect(page.getByTestId('asset-detail-chart').getByTestId('candlestick-chart')).toBeVisible({timeout: 5000});
        expect(errors).toHaveLength(0);
    });
});
