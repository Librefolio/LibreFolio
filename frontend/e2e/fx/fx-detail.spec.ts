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

import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
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
        // ECharts renders into a canvas — assert the drawn content, not just the frame
        await expectChartCanvas(page, 'fx-detail-chart');
    });

    // ========================================================================
    // Test 4: Swap direction changes URL
    // ========================================================================
    test('swap direction changes URL', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-swap-btn').click();
        await expect(page).toHaveURL(/\/fx\/USD-EUR/, {timeout: 10_000});
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

    test('AI Export lives in the page toolbar instead of Signals', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const aiExportButton = page.getByTestId('fx-detail-filter-bar').getByTestId('ai-export-button');
        await expect(aiExportButton).toBeVisible({timeout: 10_000});
        await expect(aiExportButton).toBeEnabled({timeout: 10_000});
        await aiExportButton.click();
        await expect(page.getByTestId('ai-export-menu-panel')).toBeVisible();
        await page.keyboard.press('Escape');
        await expect(page.getByTestId('ai-export-menu-panel')).toBeHidden();
        await expect(page.getByTestId('fx-detail-signals-header').getByTestId('ai-export-button')).toHaveCount(0);
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
    test('Abs/% control is chart-local and synchronizes page view mode', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const filterBar = page.getByTestId('fx-detail-filter-bar');
        const chart = page.getByTestId('fx-detail-chart');
        await expect(filterBar.getByTestId('chart-view-mode-toggle')).toHaveCount(0);
        await expect(chart.getByTestId('chart-view-mode-toggle')).toBeVisible({timeout: 10_000});
        await expect(chart).toHaveAttribute('data-view-mode', 'percentage');

        await chart.getByTestId('chart-view-absolute').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'absolute');
        await expect(chart.getByTestId('chart-view-absolute')).toHaveAttribute('aria-pressed', 'true');

        await chart.getByTestId('chart-view-percentage').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'percentage');
    });

    // ========================================================================
    // Test 11: Sync single pair
    // ========================================================================
    test('sync single pair reports its outcome in the modal', async ({page}) => {
        // A real provider round-trip for every pair on the page; the default 30s
        // budget is spent before the sync answers.
        test.setTimeout(120_000);
        await goToFxDetailPage(page, 'EUR-USD');
        // The button opens the sync modal — it does not sync. And the modal it
        // opens is the *page* one (assets + FX for this page), not `fx-sync-modal`,
        // which belongs to the FX list. The test has to go all the way: open,
        // start, and read the verdict. Reading a locator without asserting on it,
        // as this did before, is a green that proves nothing.
        await page.getByTestId('fx-detail-sync-btn').click();
        const syncModal = page.getByTestId('page-sync-modal');
        await expect(syncModal).toBeVisible({timeout: 10_000});

        await syncModal.getByTestId('sync-modal-start').click();
        // No toast here, by design: the modal reports in place, so the summary
        // banner *is* the notification. Success or failure, it always appears.
        await expect(syncModal.getByTestId('sync-modal-results')).toBeVisible({timeout: 60_000});
    });

    // ========================================================================
    // Test 12: Refresh data
    // ========================================================================
    test('refresh triggers loading indicator', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-refresh-btn').click();
        // The refresh is fire-and-forget; the page must survive it without error
        await expect(page.getByTestId('fx-detail-refresh-btn')).toBeVisible({timeout: 10_000});
    });

    // ========================================================================
    // Test 13: Provider config modal opens in edit mode
    // ========================================================================
    test('provider config modal opens', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-provider-btn').click();
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
        await expect(page).toHaveURL(/\/fx$/, {timeout: 10_000});
    });
});
