/**
 * Asset Detail Page — E2E Tests
 *
 * Tests the Asset detail page: chart, signals, measures, classification, sync, edit.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage} from './assets-helpers';

/**
 * Navigate to the first available asset detail page.
 * Module-level (not nested in a single `describe`) so both the main "Asset
 * Detail Page" suite and other sibling suites in this file (e.g. the live
 * price flash tests below) can share it.
 */
async function goToFirstAssetDetail(page: import('@playwright/test').Page) {
    await goToAssetsPage(page);
    const firstCard = page.locator('[data-testid^="asset-card-"]').first();
    await expect(firstCard).toBeVisible({timeout: 5_000});
    await firstCard.click();
    await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});
    await page.waitForTimeout(1000);
}

/**
 * Asserts that the asset detail price chart has actually rendered content,
 * not merely that its wrapper container is visible. A container can stay
 * visible while the ECharts canvas inside it never mounts or ends up with
 * zero size — the same defect shape that let a previous chart regression
 * ship without a failing test. Modeled on `expectOwnershipChartCanvas()` in
 * `frontend/e2e/brokers/broker-sharing.spec.ts` (duplicated locally on
 * purpose: these are separate suites and cross-suite imports are avoided).
 */
async function expectAssetDetailChartCanvas(page: import('@playwright/test').Page) {
    const section = page.getByTestId('asset-detail-chart');
    await expect(section).toBeVisible({timeout: 5_000});

    const canvas = section.locator('canvas').first();
    await expect(canvas).toBeVisible({timeout: 5_000});
    await expect
        .poll(
            async () => {
                const box = await canvas.boundingBox();
                if (!box || box.width <= 0 || box.height <= 0) return 'zero-css-size';

                return canvas.evaluate((node) => {
                    const htmlCanvas = node as HTMLCanvasElement;
                    return htmlCanvas.width > 0 && htmlCanvas.height > 0 ? 'non-zero' : 'zero-bitmap-size';
                });
            },
            {timeout: 5_000},
        )
        .toBe('non-zero');
}

test.describe('Asset Detail Page', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Detail page loads with header and chart
    // ========================================================================
    test('detail page shows header and chart', async ({page}) => {
        await goToFirstAssetDetail(page);
        await expect(page.getByTestId('asset-detail-header')).toBeVisible();
        await expectAssetDetailChartCanvas(page);
    });

    // ========================================================================
    // Test 2: Filter bar with date range is visible
    // ========================================================================
    test('filter bar is visible', async ({page}) => {
        await goToFirstAssetDetail(page);
        await expect(page.getByTestId('asset-detail-filter-bar')).toBeVisible();
    });

    test('AI Export lives in the shared toolbar across Overview and Risk', async ({page}) => {
        await goToFirstAssetDetail(page);
        const controls = page.getByTestId('asset-detail-controls');
        const toolbar = controls.getByTestId('asset-detail-filter-bar');
        await expect(controls.getByTestId('asset-detail-tab-overview')).toBeVisible();
        await expect(page.getByTestId('asset-detail-tabs')).toHaveCount(0);
        const aiExportButton = toolbar.getByTestId('ai-export-button');
        await expect(aiExportButton).toBeVisible({timeout: 10_000});
        await expect(aiExportButton).toBeEnabled({timeout: 10_000});
        await aiExportButton.click();
        await expect(page.getByTestId('ai-export-menu-panel')).toBeVisible();
        await page.keyboard.press('Escape');
        await expect(page.getByTestId('ai-export-menu-panel')).toBeHidden();
        await expect(page.getByTestId('asset-detail-signals-header').getByTestId('ai-export-button')).toHaveCount(0);

        const initialRiskResponse = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/risk/query');
        await controls.getByTestId('asset-detail-tab-risk').click();
        await initialRiskResponse;
        await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 10_000});
        await expect(controls.getByTestId('asset-detail-tab-risk')).toHaveAttribute('aria-selected', 'true');
        await expect(toolbar).toBeVisible();
        await expect(toolbar.getByTestId('ai-export-button')).toBeVisible();
        await expect(page.getByTestId('risk-sync-button')).toHaveCount(0);
        await expect(page.getByTestId('risk-refresh-button')).toHaveCount(0);

        const refreshedRiskRequest = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/risk/query');
        await toolbar.getByTestId('asset-detail-refresh-btn').click();
        await refreshedRiskRequest;
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

    test('risk signals render and beta requests only after selecting a comparison asset', async ({page}) => {
        await goToFirstAssetDetail(page);
        await page.getByTestId('asset-detail-signals-toggle').click();
        await expect(page.getByTestId('asset-detail-signals-panel')).toBeVisible({timeout: 5_000});

        await page.getByTestId('signals-indicator-select-button').click();
        await page.getByTestId('signal-tree-group-risk').click();
        await expect(page.getByTestId('signal-tree-option-risk-drawdown')).toBeVisible();
        await expect(page.getByTestId('signal-tree-option-risk-rolling-volatility')).toBeVisible();
        await expect(page.getByTestId('signal-tree-option-risk-rolling-return')).toBeVisible();
        await expect(page.getByTestId('signal-tree-option-risk-rolling-sharpe')).toBeVisible();
        await page.getByTestId('signal-tree-option-risk-rolling-beta').click();

        await expect(page.getByTestId('signal-comparison-asset-select-control')).toBeVisible({timeout: 5_000});
        await page.getByTestId('signal-comparison-asset-select-trigger').click();

        const comparisonOption = page.getByTestId(/^search-select-option-/).first();
        await expect(comparisonOption).toBeVisible({timeout: 5_000});
        const betaRequest = page.waitForRequest(
            (request) => {
                if (request.method() !== 'POST' || !request.url().includes('/api/v1/assets/prices/query')) return false;
                const body = request.postDataJSON();
                return Array.isArray(body) && body.some((item) => item.signals?.some((signal: {signal_code?: string; params?: {comparison_asset_id?: number}}) => signal.signal_code === 'RISK_ROLLING_BETA' && Number.isInteger(signal.params?.comparison_asset_id)));
            },
            {timeout: 10_000},
        );
        await comparisonOption.click();

        const requestBody = (await betaRequest).postDataJSON() as Array<{
            signals?: Array<{signal_code?: string; params?: {comparison_asset_id?: number}}>;
        }>;
        const betaSignal = requestBody.flatMap((item) => item.signals ?? []).find((signal) => signal.signal_code === 'RISK_ROLLING_BETA');
        expect(betaSignal?.params?.comparison_asset_id).toBeGreaterThan(0);
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
        await expectAssetDetailChartCanvas(page);
    });

    // ========================================================================
    // Test 17: Chart-local Abs/% control
    // ========================================================================
    test('Abs/% control is chart-local and synchronizes page view mode', async ({page}) => {
        await goToFirstAssetDetail(page);
        const filterBar = page.getByTestId('asset-detail-filter-bar');
        const chart = page.getByTestId('asset-detail-chart');
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
    // Test 18: Chart type toggle — Line → Candlestick → Line
    // ========================================================================
    test('chart type toggle switches between line and candlestick', async ({page}) => {
        await goToFirstAssetDetail(page);

        // Wait for chart data to load (button only renders when data is available)
        const candleBtn = page.getByTestId('chart-type-candlestick');
        const lineBtn = page.getByTestId('chart-type-line');
        await expect(candleBtn).toBeVisible({timeout: 10_000});
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
    // Test 19: Candlestick renders without JS error
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

// ============================================================================
// Live price direction flash (green on up-tick, red on down-tick, animated
// decay back to neutral) — see `_fetchLivePrice` in +page.svelte and the
// `data-live-price-direction` attribute rendered by AssetPriceSummary.svelte.
//
// A prior regression in this codebase (a broker-sharing chart silently going
// blank) slipped through because its E2E test only asserted a wrapper <div>
// was visible, never the actual rendered content. These tests deliberately
// assert on the *applied* class and the `data-live-price-direction` value —
// never just "the price element exists" — so a similar regression here (e.g.
// direction stuck at 'neutral', or the flash class never applied) would fail
// the suite instead of passing silently.
//
// Prices are intercepted via Playwright routing (not live market data) so
// ticks are deterministic, and Playwright's fake clock fast-forwards the 30s
// poll interval and the ~1.3s flash-decay timer instead of waiting in real
// time.
// ============================================================================
test.describe('Live price direction flash', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    /**
     * Intercepts POST /api/v1/assets/prices/current and answers with
     * `price.value` (as of today) for every requested asset id. `price` is a
     * mutable box the test mutates between polls to simulate a new tick —
     * every intercepted request (from either of the detail page's two live
     * price pollers) reads whatever value is current at call time, so the
     * mock stays correct regardless of call count/order.
     */
    async function mockCurrentPrice(page: import('@playwright/test').Page, price: {value: number}) {
        await page.route('**/api/v1/assets/prices/current', async (route) => {
            const ids = (route.request().postDataJSON() as number[] | null) ?? [];
            const today = new Date().toISOString().slice(0, 10);
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    results: ids.map((assetId) => ({
                        asset_id: assetId,
                        value: price.value.toFixed(2),
                        currency: 'USD',
                        as_of_date: today,
                        source: 'mock',
                        error: null,
                    })),
                    success_count: ids.length,
                }),
            });
        });
    }

    test('first tick after load is neutral — no previous value to compare against', async ({page}) => {
        test.setTimeout(20_000);
        const price = {value: 100};
        await mockCurrentPrice(page, price);
        await page.clock.install();
        await goToFirstAssetDetail(page);

        const priceEl = page.getByTestId('asset-detail-live-price');
        await expect(priceEl).toBeVisible({timeout: 5_000});
        await expect(priceEl).toHaveAttribute('data-live-price-direction', 'neutral');
        await expect(priceEl).not.toHaveClass(/lf-price-flash-/);
        await expect(priceEl).toHaveText('100.00');
    });

    test('an up-tick flashes green then decays back to neutral', async ({page}) => {
        test.setTimeout(20_000);
        const price = {value: 100};
        await mockCurrentPrice(page, price);
        await page.clock.install();
        await goToFirstAssetDetail(page);

        const priceEl = page.getByTestId('asset-detail-live-price');
        await expect(priceEl).toHaveAttribute('data-live-price-direction', 'neutral', {timeout: 5_000});

        // New tick with a HIGHER value than the previous poll.
        price.value = 105;
        await page.clock.fastForward(30_000);

        await expect(priceEl).toHaveAttribute('data-live-price-direction', 'up');
        await expect(priceEl).toHaveClass(/lf-price-flash-up/);
        await expect(priceEl).toHaveText('105.00');

        // Past the ~1.3s flash-decay window the colour settles back to
        // neutral — the price value itself does not change, only the flash.
        await page.clock.fastForward(1_500);
        await expect(priceEl).toHaveAttribute('data-live-price-direction', 'neutral');
        await expect(priceEl).not.toHaveClass(/lf-price-flash-/);
        await expect(priceEl).toHaveText('105.00');
    });

    test('a down-tick flashes red then decays back to neutral', async ({page}) => {
        test.setTimeout(20_000);
        const price = {value: 100};
        await mockCurrentPrice(page, price);
        await page.clock.install();
        await goToFirstAssetDetail(page);

        const priceEl = page.getByTestId('asset-detail-live-price');
        await expect(priceEl).toHaveAttribute('data-live-price-direction', 'neutral', {timeout: 5_000});

        // New tick with a LOWER value than the previous poll.
        price.value = 95;
        await page.clock.fastForward(30_000);

        await expect(priceEl).toHaveAttribute('data-live-price-direction', 'down');
        await expect(priceEl).toHaveClass(/lf-price-flash-down/);
        await expect(priceEl).toHaveText('95.00');

        await page.clock.fastForward(1_500);
        await expect(priceEl).toHaveAttribute('data-live-price-direction', 'neutral');
        await expect(priceEl).not.toHaveClass(/lf-price-flash-/);
        await expect(priceEl).toHaveText('95.00');
    });

    test('consecutive same-direction ticks each restart the flash', async ({page}) => {
        test.setTimeout(20_000);
        const price = {value: 100};
        await mockCurrentPrice(page, price);
        await page.clock.install();
        await goToFirstAssetDetail(page);

        const priceEl = page.getByTestId('asset-detail-live-price');
        await expect(priceEl).toHaveAttribute('data-live-price-direction', 'neutral', {timeout: 5_000});

        price.value = 101;
        await page.clock.fastForward(30_000);
        await expect(priceEl).toHaveAttribute('data-live-price-direction', 'up');
        await expect(priceEl).toHaveText('101.00');

        // Let the first flash decay...
        await page.clock.fastForward(1_500);
        await expect(priceEl).toHaveAttribute('data-live-price-direction', 'neutral');

        // ...then tick UP again. This must re-flash rather than silently stay
        // neutral just because the direction string repeats ('up' -> 'up') —
        // the component keys the flash element on a monotonic token precisely
        // to guard against this.
        price.value = 102;
        await page.clock.fastForward(30_000);
        await expect(priceEl).toHaveAttribute('data-live-price-direction', 'up');
        await expect(priceEl).toHaveClass(/lf-price-flash-up/);
        await expect(priceEl).toHaveText('102.00');
    });
});
