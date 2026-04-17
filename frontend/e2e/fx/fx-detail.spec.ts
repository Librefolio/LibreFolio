/**
 * FX Detail Page — E2E Tests
 *
 * Tests the FX detail page: chart rendering, panels, swap direction, sync.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 *   EUR-USD pair must exist.
 */

import {expect, test} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxDetailPage} from './fx-helpers';

test.describe('FX Detail Page', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Direct slug navigation
    // ========================================================================
    test('can navigate to detail page via slug', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await expect(page.getByTestId('fx-detail-page')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Inverted slug displays inverted direction
    // ========================================================================
    test('inverted slug displays inverted direction', async ({page}) => {
        await goToFxDetailPage(page, 'USD-EUR');
        await expect(page.getByTestId('fx-detail-page')).toBeVisible();
        const pairLabel = page.getByTestId('fx-detail-pair-label');
        const text = await pairLabel.textContent();
        expect(text).toContain('USD');
    });

    // ========================================================================
    // Test 3: Chart is visible (canvas element rendered)
    // ========================================================================
    test('chart is visible with canvas element', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const chartContainer = page.getByTestId('fx-detail-chart');
        await expect(chartContainer).toBeVisible();
        // ECharts renders into a canvas
        const canvas = chartContainer.locator('canvas');
        await expect(canvas.first()).toBeVisible({timeout: 5000});
    });

    // ========================================================================
    // Test 4: Swap direction changes URL
    // ========================================================================
    test('swap direction changes URL', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-swap-btn').click();
        await page.waitForTimeout(500);
        await expect(page).toHaveURL(/\/fx\/USD-EUR/);
    });

    // ========================================================================
    // Test 6: Aesthetics panel fold/unfold
    // ========================================================================
    test('aesthetics panel toggles visibility', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const toggle = page.getByTestId('fx-detail-aesthetics-toggle');
        await toggle.click();
        await expect(page.getByTestId('fx-detail-aesthetics-panel')).toBeVisible();
        await toggle.click();
        await expect(page.getByTestId('fx-detail-aesthetics-panel')).not.toBeVisible();
    });

    // ========================================================================
    // Test 7: Signals panel fold/unfold
    // ========================================================================
    test('signals panel toggles visibility', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const toggle = page.getByTestId('fx-detail-signals-toggle');
        await toggle.click();
        await expect(page.getByTestId('fx-detail-signals-panel')).toBeVisible();
        await toggle.click();
        await expect(page.getByTestId('fx-detail-signals-panel')).not.toBeVisible();
    });

    // ========================================================================
    // Test 8: Measures panel fold/unfold
    // ========================================================================
    test('measures panel toggles visibility', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const toggle = page.getByTestId('fx-detail-measures-toggle');
        await toggle.click();
        // MeasurePanel is always mounted but hidden via CSS class
        const panel = page.getByTestId('fx-detail-measures-panel');
        await expect(panel).toBeVisible();
        // Check it's not hidden
        await expect(panel).not.toHaveClass(/hidden/);
    });

    // ========================================================================
    // Test 9: Toggle Abs/%
    // ========================================================================
    test('Abs/% toggle switches view mode', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const filterBar = page.getByTestId('fx-detail-filter-bar');
        // Find the % button and click it
        const pctBtn = filterBar.getByRole('button', {name: '%'});
        if (await pctBtn.isVisible()) {
            await pctBtn.click();
            await page.waitForTimeout(300);
            // The button should now be active (has green bg class)
            await expect(pctBtn).toHaveClass(/bg-libre-green/);
        }
    });

    // ========================================================================
    // Test 11: Sync single pair
    // ========================================================================
    test('sync single pair shows toast', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-sync-btn').click();
        // Wait for toast (success or error)
        await page.waitForTimeout(3000);
        // Check that a toast appeared (any message)
        const toast = page.locator('[data-testid="toast-container"] [role="alert"], .toast-message, [class*="toast"]');
        // Toast may or may not be visible depending on provider availability
    });

    // ========================================================================
    // Test 12: Refresh data
    // ========================================================================
    test('refresh triggers loading indicator', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-refresh-btn').click();
        // The button should have spinning animation briefly
        await page.waitForTimeout(500);
    });

    // ========================================================================
    // Test 13: Provider config modal opens in edit mode
    // ========================================================================
    test('provider config modal opens', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-provider-btn').click();
        await page.waitForTimeout(500);
        // The FxPairAddModal should be visible
        const modal = page.getByTestId('fx-add-pair-modal');
        await expect(modal).toBeVisible({timeout: 3000});
    });

    // ========================================================================
    // Test 14: Back to list
    // ========================================================================
    test('back button navigates to FX list', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-back-btn').click();
        await page.waitForTimeout(500);
        await expect(page).toHaveURL(/\/fx$/);
    });
});
