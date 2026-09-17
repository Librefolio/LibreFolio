/**
 * Asset Detail Page — E2E Tests
 *
 * Tests the Asset detail page: chart, signals, measures, classification, sync, edit.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {readFileSync} from 'node:fs';
import {expect, test} from '../fixtures/playwright';
import type {Locator, Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {goToAssetDetailPage, goToAssetsPage} from './assets-helpers';
import {t} from '../fixtures/i18n-data';
import {schemas} from '../../src/lib/api/generated';

test.describe('Shared chart settings source contracts', () => {
    const fxPageSource = () => readFileSync(new URL('../../src/routes/(app)/fx/+page.svelte', import.meta.url), 'utf8');

    test('A3 FX adoption passes the translated Preview context without coupling to its local store alias', () => {
        const source = fxPageSource();
        const modal = source.match(/<ChartSettingsModal\b[\s\S]*?\/>/)?.[0];
        const axisContext = source.match(/let settingsAxisContext = \$derived\.by\(\(\) => \{[\s\S]*?\n    \}\);/)?.[0];
        const i18nImport = source.match(/import\s*\{\s*_\s*(?:as\s+([A-Za-z_$][\w$]*))?\s*\}\s*from\s*['"]\$lib\/i18n['"]/);

        expect(modal, 'FX ChartSettingsModal invocation').toBeDefined();
        expect(axisContext, 'FX settings axis context derivation').toBeDefined();
        expect(i18nImport, 'FX translation store import').toBeDefined();
        if (!modal || !axisContext || !i18nImport) return;

        const localStoreName = i18nImport[1] ?? '_';
        expect(modal).toContain('axisDomain="fx"');
        expect(modal).toContain('axisContext={settingsAxisContext}');
        expect(axisContext).toContain(`$${localStoreName}('common.preview')`);
    });

    test('inverted FX settings derive their axis label from the displayed card direction', () => {
        const source = fxPageSource();
        const axisContext = source.match(/let settingsAxisContext = \$derived\.by\(\(\) => \{[\s\S]*?\n    \}\);/)?.[0];

        expect(axisContext, 'FX settings axis context derivation').toBeDefined();
        if (!axisContext) return;

        expect(axisContext).toContain('const pair = pairs.find((item) => item.config.slug === settingsTargetSlug)');
        expect(axisContext).toMatch(/return\s+isCardInverted\(settingsTargetSlug\)\s*\?\s*`\$\{pair\.config\.quote\}\/\$\{pair\.config\.base\}`\s*:\s*`\$\{pair\.config\.base\}\/\$\{pair\.config\.quote\}`/);
    });
});

async function mockDetailAssetWithGlobalTransactions(page: Page, assetId: number, txCount: number) {
    const asset = {
        id: assetId,
        display_name: `Synthetic detail asset ${assetId}`,
        currency: 'EUR',
        asset_type: 'STOCK',
        active: true,
        has_metadata: false,
        provider_code: null,
        tx_count: txCount,
        // Deliberately zero: the displayed total is global and is not a promise
        // that this user can see any of the transactions behind it.
        tx_count_own: 0,
    };
    await page.route('**/api/v1/assets/query*', async (route) => {
        await route.fulfill({json: [asset]});
    });
    await page.route('**/api/v1/assets/prices/query', async (route) => {
        await route.fulfill({
            json: {
                items: [
                    {
                        asset_id: assetId,
                        prices: [],
                        events: [],
                        errors: [],
                        signals: [],
                    },
                ],
            },
        });
    });
    await page.route('**/api/v1/assets/prices/current', async (route) => {
        await route.fulfill({json: {results: [], success_count: 0, errors: []}});
    });
}

/**
 * Navigate to a *seeded* asset's detail page.
 *
 * This used to take the **first** card on the list. With four workers writing to one
 * database, "the first card" is whichever asset a neighbour created a second earlier —
 * typically one with no price history, so the ECharts canvas never mounts and the
 * failure reads like a chart regression. Apple is the suite's established "known asset
 * with price history" (tx-wac-bulk, tx-wac-formmodal, tx-commit-all-types all rely on
 * it), so naming it is both the ownership guarantee and the reason a chart exists to
 * assert on at all.
 *
 * Kept as one helper because the "Asset Detail Page" suite and other sibling suites in
 * this file (e.g. the live price flash tests below) can share it.
 */
async function goToSeededAssetDetail(page: import('@playwright/test').Page) {
    await goToAssetsPage(page);
    const card = page.locator('[data-testid^="asset-card-"]').filter({hasText: /Apple/i}).first();
    await expect(card, 'the seeded Apple asset must be on the list').toBeVisible({timeout: 10_000});
    await card.click();
    await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});
    await waitForSettled(page.getByTestId('asset-detail-page'), 20_000);
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
        await goToSeededAssetDetail(page);
        await expect(page.getByTestId('asset-detail-header')).toBeVisible();
        await expectAssetDetailChartCanvas(page);
    });

    test('global transaction count renders a clean filtered link without claiming row visibility', async ({page}) => {
        const assetId = 920_051;
        const globalCount = 29;
        await mockDetailAssetWithGlobalTransactions(page, assetId, globalCount);

        await goToAssetDetailPage(page, String(assetId));

        const link = page.getByTestId('asset-detail-transactions-link');
        await expect(link).toBeVisible();
        await expect(link).toHaveAttribute('href', `/transactions?asset_id=${assetId}`);
        await expect(link).toContainText(`(${globalCount})`);
        // The label itself must come from the real transactions.title catalogue
        // entry, not a hardcoded English guess and not a missing key like the old
        // `nav.transactions` (svelte-i18n renders a missing key as the literal key
        // string, so this also catches a regression back to that key by construction).
        await expect(link).toContainText(t('en', 'transactions.title'));
        await expect(link).not.toContainText('nav.transactions');
        await expect(link).not.toContainText('transactions.title');
        // Do not follow the link or assert transaction rows: tx_count is global,
        // while the transactions endpoint keeps enforcing the user's broker access.
    });

    // ========================================================================
    // Test 2: Filter bar with date range is visible
    // ========================================================================
    test('filter bar is visible', async ({page}) => {
        await goToSeededAssetDetail(page);
        await expect(page.getByTestId('asset-detail-filter-bar')).toBeVisible();
    });

    test('AI Export lives in the shared toolbar across Overview and Risk', async ({page}) => {
        // Two full `/risk/query` round-trips plus the AI Export menu. Risk is the
        // most expensive computation in the app and slows down further when four
        // workers share one backend, so the default 30s budget is not enough.
        test.setTimeout(120_000);
        await goToSeededAssetDetail(page);
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

        // The subject here is the toolbar, not the network. Waiting on
        // `POST /risk/query` made the test hostage to `queryRisk`'s cache: if the
        // same canonical request already went out during page load, the tab click
        // is served from memory and no request ever appears — the test then waits
        // for something that will never happen. Wait for the panel, which is the
        // state the assertions below actually need.
        await controls.getByTestId('asset-detail-tab-risk').click();
        await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 30_000});
        await expect(page.getByTestId('asset-detail-risk-loading')).toHaveCount(0);
        await expect(controls.getByTestId('asset-detail-tab-risk')).toHaveAttribute('aria-selected', 'true');
        await expect(toolbar).toBeVisible();
        await expect(toolbar.getByTestId('ai-export-button')).toBeVisible();
        await expect(page.getByTestId('risk-sync-button')).toHaveCount(0);
        await expect(page.getByTestId('risk-refresh-button')).toHaveCount(0);

        // The refresh *is* about the request: it must reach the server rather than
        // be answered from the cache, so here the network is the subject.
        const refreshedRiskRequest = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/risk/query');
        await toolbar.getByTestId('asset-detail-refresh-btn').click();
        await refreshedRiskRequest;
    });

    // ========================================================================
    // Test 3: Edit button opens modal (no effect_update_depth_exceeded)
    // ========================================================================
    test('edit button opens asset modal', async ({page}) => {
        await goToSeededAssetDetail(page);
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
        await goToSeededAssetDetail(page);
        await expect(page.getByTestId('asset-detail-sync-btn')).toBeVisible();
    });

    // ========================================================================
    // Test 5: Refresh button is visible
    // ========================================================================
    test('refresh button is visible', async ({page}) => {
        await goToSeededAssetDetail(page);
        await expect(page.getByTestId('asset-detail-refresh-btn')).toBeVisible();
    });

    // ========================================================================
    // Test 6: Signals panel toggle
    // ========================================================================
    test('signals panel toggles open/close', async ({page}) => {
        await goToSeededAssetDetail(page);
        const toggle = page.getByTestId('asset-detail-signals-toggle');
        await expect(toggle).toBeVisible();
        const panel = page.getByTestId('asset-detail-signals-panel');
        const openedByDefault = await panel.isVisible();

        await toggle.click();
        await expect(panel).toBeVisible({visible: !openedByDefault, timeout: 5_000});

        // Toggle back — the panel must return to where it started
        await toggle.click();
        await expect(panel).toBeVisible({visible: openedByDefault, timeout: 5_000});
    });

    test('risk signals render and beta requests only after selecting a comparison asset', async ({page}) => {
        await goToSeededAssetDetail(page);
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
        await goToSeededAssetDetail(page);
        const toggle = page.getByTestId('asset-detail-measures-toggle');
        await expect(toggle).toBeVisible();
        await toggle.click();
        await expect(page.getByTestId('asset-detail-measures-panel')).toBeVisible();
    });

    // ========================================================================
    // Test 8: Metadata/classification panel toggle
    // ========================================================================
    test('classification panel toggles', async ({page}) => {
        await goToSeededAssetDetail(page);
        const toggle = page.getByTestId('asset-detail-metadata-toggle');
        await expect(toggle).toBeVisible();
        await toggle.click();
        await expect(page.getByTestId('asset-detail-metadata-panel')).toBeVisible();
    });

    // ========================================================================
    // Test 9: Back button navigates back
    // ========================================================================
    test('back button navigates back to list', async ({page}) => {
        await goToSeededAssetDetail(page);
        const backBtn = page.getByTestId('asset-detail-back-btn');
        await expect(backBtn).toBeVisible();
        await backBtn.click();
        await expect(page.getByTestId('assets-page')).toBeVisible({timeout: 10_000});
    });

    // ========================================================================
    // Test 10: The gear button toggles the aesthetics panel above the chart.
    //
    // This replaces a `hasData ? expect(toggle).toBeVisible() : annotate-and-pass`
    // guard. On the seeded Apple asset the chart toolbar always renders (the
    // buttons live inside `{:else if lineData.length > 0}` and Apple has price
    // history), so the guard collapsed to re-asserting the very `isVisible()`
    // probe it had just run — and on any asset without data it passed having
    // exercised nothing. It now drives the real branch: opening the gear mounts
    // `asset-detail-aesthetics-panel`, closing it removes the node again.
    // ========================================================================
    test('aesthetics toggle opens and closes the aesthetics panel', async ({page}) => {
        await goToSeededAssetDetail(page);
        const toggle = page.getByTestId('asset-detail-aesthetics-toggle');
        await expect(toggle).toBeVisible();

        // `{#if showAesthetics}` — the panel is absent from the DOM until opened.
        const panel = page.getByTestId('asset-detail-aesthetics-panel');
        await expect(panel).toHaveCount(0);

        await toggle.click();
        await expect(panel).toBeVisible();

        await toggle.click();
        await expect(panel).toHaveCount(0);
    });

    // ========================================================================
    // Test 11: The pencil button opens the inline data editor, and pressing it
    // again returns to the chart. Same history as the aesthetics test above —
    // the previous version only re-asserted its own visibility probe.
    // ========================================================================
    test('edit-data button opens and closes the inline data editor', async ({page}) => {
        await goToSeededAssetDetail(page);
        const btn = page.getByTestId('asset-detail-editdata-btn');
        await expect(btn).toBeVisible();

        // `{#if showDataEditor}` — mounted only while the editor is open.
        const editor = page.getByTestId('asset-detail-editor-panel');
        await expect(editor).toHaveCount(0);

        await btn.click();
        await expect(editor).toBeVisible();

        await btn.click();
        await expect(editor).toHaveCount(0);
    });

    // ========================================================================
    // Test 12: The ruler button reveals the measures panel (and arms measure
    // mode via the chart). Unlike the aesthetics/editor panels the measures
    // panel is always in the DOM but carries the `hidden` class until
    // `showMeasures`, so this asserts on visibility rather than node count. It
    // is a distinct entry point from the `asset-detail-measures-toggle` header
    // exercised by the "measures panel toggles" test.
    // ========================================================================
    test('measure button reveals the measures panel', async ({page}) => {
        await goToSeededAssetDetail(page);
        const btn = page.getByTestId('asset-detail-measure-btn');
        await expect(btn).toBeVisible();

        const panel = page.getByTestId('asset-detail-measures-panel');
        await expect(panel).toBeHidden();

        await btn.click();
        await expect(panel).toBeVisible();
    });

    // NOTE: a former "currency selector is visible in filter bar" test was
    // removed here. It scoped its locator to `asset-detail-filter-bar`, but that
    // container holds only the DateRangePicker — the display-currency selector
    // lives in the separate `summary` snippet (AssetPriceSummary), which passes
    // no test id. The old locator therefore matched nothing (silent
    // annotate-and-pass) or, worse, matched a 3-letter date preset such as
    // "YTD"/"MAX" and asserted a date button was "the currency selector". Making
    // it honest would require a test hook on CurrencySearchSelect; reported
    // rather than fixed, per the campaign rule on product-surface changes.

    // ========================================================================
    // Test 14: Asset info shows type badge and name
    // ========================================================================
    test('asset info shows name and type', async ({page}) => {
        await goToSeededAssetDetail(page);
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
        await goToSeededAssetDetail(page);
        const syncBtn = page.getByTestId('asset-detail-sync-btn');
        await expect(syncBtn).toBeVisible();

        // Click sync — may show toast, spinner, or no-op if no provider
        await syncBtn.click();
        await waitForSettled(page.getByTestId('asset-detail-page'), 20_000);

        // Page should still be intact (no crash)
        await expect(page.getByTestId('asset-detail-page')).toBeVisible();
    });

    // ========================================================================
    // Test 16: Refresh button reloads data
    // ========================================================================
    test('refresh button reloads data without error', async ({page}) => {
        await goToSeededAssetDetail(page);
        const refreshBtn = page.getByTestId('asset-detail-refresh-btn');
        await expect(refreshBtn).toBeVisible();

        await refreshBtn.click();
        await waitForSettled(page.getByTestId('asset-detail-page'), 20_000);

        // Page should still be intact
        await expect(page.getByTestId('asset-detail-page')).toBeVisible();
        await expectAssetDetailChartCanvas(page);
    });

    // ========================================================================
    // Test 17: Chart-local Abs/% control
    // ========================================================================
    test('Abs/% control is chart-local and synchronizes page view mode', async ({page}) => {
        await goToSeededAssetDetail(page);
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

    test('calendar-return primary mode queries exact windows and restores price controls', async ({page}) => {
        test.setTimeout(180_000);
        const assetId = 920_060;
        const calendarInstanceId = 'asset-calendar-return';
        const calendarSignalCode = 'ASSET_CALENDAR_ROLLING_RETURN';
        const backendSignalCode = 'RISK_ROLLING_VOLATILITY';
        const calendarPresets = [
            {key: '1w', windowDays: 7},
            {key: '1m', windowDays: 30},
            {key: '3m', windowDays: 90},
            {key: '1y', windowDays: 365},
        ] as const;
        const readyPeer = {
            id: 920_061,
            display_name: 'Synthetic calendar peer Ready',
            currency: 'GBP',
            asset_type: 'STOCK',
            active: true,
            has_metadata: false,
            provider_code: null,
            tx_count: 0,
            tx_count_own: 0,
        };
        const readyPeerConversionError = 'synthetic-price-conversion-failure';
        const readyPeerEventOnlyConversionError = 'Missing FX rate USD->EUR for event on 2026-08-02';
        const readyPeerGenericConversionError = 'Conversion 1: No FX rate available for USD->EUR';
        const partialPeer = {
            id: 920_062,
            display_name: 'Synthetic calendar peer Partial',
            currency: 'GBP',
            asset_type: 'STOCK',
            active: true,
            has_metadata: false,
            provider_code: null,
            tx_count: 0,
            tx_count_own: 0,
        };
        const unavailablePeer = {
            id: 920_063,
            display_name: 'Synthetic calendar peer Unavailable',
            currency: 'JPY',
            asset_type: 'STOCK',
            active: true,
            has_metadata: false,
            provider_code: null,
            tx_count: 0,
            tx_count_own: 0,
        };
        const errorPeer = {
            id: 920_064,
            display_name: 'Synthetic calendar peer Error',
            currency: 'CHF',
            asset_type: 'STOCK',
            active: true,
            has_metadata: false,
            provider_code: null,
            tx_count: 0,
            tx_count_own: 0,
        };
        const invalidCalendarPeer = {
            id: 920_066,
            display_name: 'Synthetic calendar peer Invalid shape',
            currency: 'AUD',
            asset_type: 'STOCK',
            active: true,
            has_metadata: false,
            provider_code: null,
            tx_count: 0,
            tx_count_own: 0,
        };
        const replacementPeer = {
            id: 920_065,
            display_name: 'Synthetic calendar peer Replacement',
            currency: 'CAD',
            asset_type: 'STOCK',
            active: true,
            has_metadata: false,
            provider_code: null,
            tx_count: 0,
            tx_count_own: 0,
        };
        const sharedRoutePeer = {
            id: 920_067,
            display_name: 'Synthetic shared-route peer',
            currency: 'EUR',
            asset_type: 'STOCK',
            active: true,
            has_metadata: false,
            provider_code: 'MOCKASSET',
            tx_count: 0,
            tx_count_own: 0,
        };
        const comparisonPeers = [readyPeer, partialPeer, unavailablePeer, errorPeer, invalidCalendarPeer] as const;
        const availableComparisonPeers = [...comparisonPeers, replacementPeer, sharedRoutePeer] as const;
        const comparisonPeerIds = comparisonPeers.map((peer) => peer.id);
        const replacementPeerIds = [replacementPeer.id, partialPeer.id, unavailablePeer.id, errorPeer.id, invalidCalendarPeer.id];
        const sharedRoutePeerIds = [sharedRoutePeer.id, partialPeer.id, unavailablePeer.id, errorPeer.id, invalidCalendarPeer.id];
        const calendarErrorPeerIds = [errorPeer.id, invalidCalendarPeer.id].sort((left, right) => left - right).join(',');
        const comparisonPeerColors = new Map([
            [readyPeer.id, '#3b82f6'],
            [partialPeer.id, '#f59e0b'],
            [unavailablePeer.id, '#8b5cf6'],
            [errorPeer.id, '#10b981'],
            [invalidCalendarPeer.id, '#ef4444'],
        ]);
        type CalendarWindow = number;
        type CalendarWindowUnit = 'weeks' | 'months' | 'years';
        type SyntheticRange = {
            start: string;
            end: string;
            spanDays: number;
        };
        type CalendarSignalRequest = {
            instance_id?: string;
            signal_code?: string;
            params?: Record<string, unknown>;
        };
        type PriceQueryRequest = {
            asset_id?: number;
            date_range?: {start?: string; end?: string};
            include_price?: boolean;
            include_events?: boolean;
            target_currency?: string;
            signals?: CalendarSignalRequest[];
        };
        type FxConvertRequest = {
            from_amount: {code: string; amount: string};
            to: string;
            date_range: {start: string; end: string};
        };
        type AssetSyncRequest = {
            asset_id?: number;
            date_range?: {start?: string; end?: string};
        };
        type FxSyncRequest = {
            pairs?: unknown;
            start?: unknown;
            end?: unknown;
        };
        type CalendarPointFixture = {
            date: string;
            value: number | null;
            provenance: {
                status: 'available' | 'missing_reference' | 'invalid_current_price' | 'invalid_reference_price';
                reference_target_date: string;
                current_price_date: string;
                current_price_days_back: number;
                reference_price_date: string | null;
                reference_price_days_back: number | null;
                current_fx_date: string | null;
                current_fx_days_back: number | null;
                reference_fx_date: string | null;
                reference_fx_days_back: number | null;
            };
        };
        type CalendarSignalResultFixture = {
            instance_id: string;
            signal_code: string;
            normalized_params: {window_days: CalendarWindow};
            status: 'ok' | 'partial' | 'unavailable';
            series: Array<{
                key: 'calendar_return';
                points: CalendarPointFixture[];
                [key: string]: unknown;
            }>;
            [key: string]: unknown;
        };
        type DeferredCalendarOutcome = 'ready' | 'partial' | 'stale-sync' | 'i60g-stale' | 'i60g-rejected' | 'i60g-primary-unavailable' | 'i60g-primary-failed' | 'i60h-query-rejected' | 'i60h-main-omitted' | 'i60h-ready-peer-omitted' | 'i60h-peer-unavailable-contract';
        type DeferredResponse = {
            wait: Promise<void>;
            release: () => void;
        };
        type DeferredCalendarResponse = DeferredResponse & {
            outcome: DeferredCalendarOutcome;
        };
        type DeferredMainPriceResponse = DeferredResponse & {
            empty: boolean;
        };
        type DeferredPriceComparisonResponse = DeferredResponse & {
            range: SyntheticRange;
        };
        type DeferredFxSyncResponse = DeferredResponse & {
            slug: string;
            status: SyncStatusFixture;
        };
        type DeferredFxRefillResponse = DeferredResponse & {
            slug: string;
        };
        type SyncStatusFixture = 'ok' | 'partial' | 'failed' | 'skipped';
        const asset = {
            id: assetId,
            display_name: `Synthetic calendar-return asset ${assetId}`,
            currency: 'EUR',
            asset_type: 'STOCK',
            active: true,
            has_metadata: false,
            provider_code: 'MOCKASSET',
            tx_count: 0,
            tx_count_own: 0,
        };
        const readyPeerEventCurrency = 'USD';
        const readyPeerFxSlug = 'EUR-GBP';
        const readyPeerEventFxSlug = 'EUR-USD';
        const errorPeerFxSlug = [asset.currency, errorPeer.currency].sort().join('-');
        const readyPeerRequiredFxSlugs = [readyPeerFxSlug, readyPeerEventFxSlug] as const;
        const replacementPeerFxSlug = [asset.currency, replacementPeer.currency].sort().join('-');
        const configuredComparisonPeers = comparisonPeers;
        const configuredFxCurrencies = [...new Set([...configuredComparisonPeers.map((peer) => peer.currency), readyPeerEventCurrency])];
        const configuredFxSlugs = configuredFxCurrencies.map((currency) => [asset.currency, currency].sort().join('-')).sort();
        const pageSyncAssetIds = [assetId, ...comparisonPeerIds];
        const comparisonSignalConfigs = comparisonPeers.map((peer) => ({
            id: `calendar-peer-${peer.id}`,
            signalType: 'asset-comparison',
            params:
                peer.id === readyPeer.id
                    ? {
                          assetId: String(peer.id),
                          _conversionFailed: true,
                          _conversionError: readyPeerConversionError,
                      }
                    : {assetId: String(peer.id)},
            style: {
                color: comparisonPeerColors.get(peer.id) ?? '#64748b',
                lineWidth: 2,
                lineType: 'solid' as const,
                markerStart: null,
                markerEnd: null,
            },
        }));
        const seededChartSettings = {
            colorByBaseline: true,
            areaFill: true,
            gridLines: true,
            staleGradient: true,
            axisScales: {
                absolute: {mode: 'auto'},
                percentage: {mode: 'include0'},
                secondary: {},
            },
            signals: comparisonSignalConfigs,
        };
        const pricePoints = [
            {date: '2026-08-01', open: '100.00', high: '103.00', low: '99.00', close: '102.00', volume: '1000', currency: 'EUR'},
            {date: '2026-08-02', open: '102.00', high: '105.00', low: '101.00', close: '104.00', volume: '1100', currency: 'EUR'},
            {date: '2026-08-03', open: '104.00', high: '106.00', low: '102.00', close: '103.00', volume: '900', currency: 'EUR'},
        ];
        const i60gPricePoints = [
            {date: '2026-04-01', open: '100.00', high: '102.00', low: '99.00', close: '101.00', volume: '1000', currency: 'EUR'},
            {date: '2026-04-05', open: '101.00', high: '103.00', low: '100.00', close: '102.00', volume: '1010', currency: 'EUR'},
            {date: '2026-04-10', open: '102.00', high: '104.00', low: '101.00', close: '103.00', volume: '1020', currency: 'EUR'},
            {date: '2026-04-15', open: '103.00', high: '105.00', low: '102.00', close: '104.00', volume: '1030', currency: 'EUR'},
        ];
        const pageSyncPrePriceComparisonPoints = [
            {date: '2026-08-01', open: '900.00', high: '902.00', low: '899.00', close: '901.00', volume: '901', currency: 'EUR'},
            {date: '2026-08-02', open: '901.00', high: '903.00', low: '900.00', close: '902.00', volume: '902', currency: 'EUR'},
            {date: '2026-08-03', open: '902.00', high: '904.00', low: '901.00', close: '903.00', volume: '903', currency: 'EUR'},
        ];
        const pageSyncPostPriceComparisonPoints = [
            {date: '2026-08-01', open: '910.00', high: '912.00', low: '909.00', close: '911.00', volume: '911', currency: 'EUR'},
            {date: '2026-08-02', open: '911.00', high: '913.00', low: '910.00', close: '912.00', volume: '912', currency: 'EUR'},
            {date: '2026-08-03', open: '912.00', high: '914.00', low: '911.00', close: '913.00', volume: '913', currency: 'EUR'},
        ];
        const sharedRouteInitialMainPricePoints = [
            {date: '2026-08-01', open: '330.00', high: '332.00', low: '329.00', close: '331.00', volume: '331', currency: 'GBP'},
            {date: '2026-08-02', open: '331.00', high: '333.00', low: '330.00', close: '332.00', volume: '332', currency: 'GBP'},
            {date: '2026-08-03', open: '332.00', high: '334.00', low: '331.00', close: '333.00', volume: '333', currency: 'GBP'},
        ];
        const sharedRouteRefreshedMainPricePoints = [
            {date: '2026-08-01', open: '770.00', high: '772.00', low: '769.00', close: '771.00', volume: '771', currency: 'GBP'},
            {date: '2026-08-02', open: '771.00', high: '773.00', low: '770.00', close: '772.00', volume: '772', currency: 'GBP'},
            {date: '2026-08-03', open: '772.00', high: '778.00', low: '771.00', close: '777.00', volume: '777', currency: 'GBP'},
        ];
        const successorPriceComparisonPoints = [
            {date: '2026-05-05', open: '210.00', high: '213.00', low: '209.00', close: '212.00', volume: '2100', currency: 'EUR'},
            {date: '2026-08-01', open: '212.00', high: '215.00', low: '211.00', close: '214.00', volume: '2150', currency: 'EUR'},
            {date: '2026-08-03', open: '214.00', high: '216.00', low: '212.00', close: '215.00', volume: '2200', currency: 'EUR'},
        ];
        const successorReadyPriceComparisonPoints = [{date: '2026-06-15', open: '205.00', high: '208.00', low: '204.00', close: '207.00', volume: '2050', currency: readyPeer.currency}, ...successorPriceComparisonPoints];
        const staleReadyPriceComparisonPoints = [
            {date: '2026-08-01', open: '108.00', high: '109.00', low: '107.00', close: '108.50', volume: '180', currency: readyPeer.currency},
            {date: '2026-08-02', open: '109.00', high: '110.00', low: '108.00', close: '109.50', volume: '190', currency: asset.currency},
        ];
        const stalePriceComparisonPoints = [{date: '2026-08-02', open: '9.00', high: '10.00', low: '8.00', close: '9.50', volume: '90', currency: 'EUR'}];
        const successorReadyEvents = [
            {
                date: '2026-08-01',
                type: 'DIVIDEND',
                value: {amount: '1.00', code: 'EUR'},
                notes: null,
                id: 920_651,
                is_auto: false,
                original_value: {amount: '0.86', code: 'GBP'},
                fx_info: null,
            },
            {
                date: '2026-08-03',
                type: 'DIVIDEND',
                value: {amount: '1.10', code: 'EUR'},
                notes: null,
                id: 920_652,
                is_auto: false,
                original_value: {amount: '1.20', code: readyPeerEventCurrency},
                fx_info: null,
            },
        ];
        const stalePartialEvents = [
            {
                date: '2026-08-02',
                type: 'SPLIT',
                value: {amount: '2.00', code: 'GBP'},
                notes: null,
                id: 920_621,
                is_auto: false,
                original_value: null,
                fx_info: null,
            },
        ];
        const stalePriceComparisonError = 'synthetic-stale-price-conversion-failure';
        const longRange: SyntheticRange = {
            start: '2020-01-01',
            end: '2026-08-03',
            spanDays: 2406,
        };
        const exactBoundaryRange: SyntheticRange = {
            start: '2025-09-14',
            end: '2026-09-14',
            spanDays: 365,
        };
        const ninetyDayRange: SyntheticRange = {
            start: '2026-05-05',
            end: '2026-08-03',
            spanDays: 90,
        };
        const ninetyDayPriceSyncRange = {
            start: '2026-04-28',
            end: '2026-08-10',
        } as const;
        const ninetyDayCalendarSyncRange = {
            start: '2026-03-29',
            end: '2026-08-10',
        } as const;
        const longCalendarSyncRange = {
            start: '2019-11-25',
            end: '2026-08-10',
        } as const;
        const thirtyDayRange: SyntheticRange = {
            start: '2026-07-04',
            end: '2026-08-03',
            spanDays: 30,
        };
        const sixDayRange: SyntheticRange = {
            start: '2026-07-28',
            end: '2026-08-03',
            spanDays: 6,
        };
        const i60gRange: SyntheticRange = {
            start: '2026-04-01',
            end: '2026-04-15',
            spanDays: 14,
        };
        const i60gSuccessorRange: SyntheticRange = {
            start: i60gRange.start,
            end: '2026-04-14',
            spanDays: 13,
        };
        const i60gRejectedRange: SyntheticRange = {
            start: '2026-04-02',
            end: '2026-04-14',
            spanDays: 12,
        };
        const i60gPeerOnlyUnavailableRange: SyntheticRange = {
            start: '2026-04-03',
            end: '2026-04-13',
            spanDays: 10,
        };
        const i60gPeerOnlyFailedRange: SyntheticRange = {
            start: '2026-04-04',
            end: '2026-04-12',
            spanDays: 8,
        };
        const i60gContractRanges = [i60gRange, i60gSuccessorRange, i60gRejectedRange, i60gPeerOnlyUnavailableRange, i60gPeerOnlyFailedRange] as const;
        const deferredCalendarResponses = new Map<CalendarWindow, DeferredCalendarResponse>();
        let deferredPriceOnlyResponse: DeferredResponse | null = null;
        let deferredNextMainPriceResponse: DeferredMainPriceResponse | null = null;
        let deferredProvisionalMaxPriceComparisonResponse: DeferredResponse | null = null;
        let deferredNextPriceComparisonResponse: DeferredResponse | null = null;
        let deferredStalePriceComparisonResponse: DeferredPriceComparisonResponse | null = null;
        let deferredAssetSyncResponse: DeferredResponse | null = null;
        let deferredFxSyncResponse: DeferredResponse | null = null;
        const deferredFxSyncResponses = new Map<string, DeferredFxSyncResponse>();
        const deferredFxRefillResponses = new Map<string, DeferredFxRefillResponse>();
        let priceComparisonRaceActive = false;
        let priceComparisonRaceSuccessorServed = false;
        let priceComparisonSyncSucceeded = false;
        let pageSyncComparisonSnapshot: 'pre-sync' | 'post-sync' | null = null;
        let sharedRouteMainSnapshot: 'initial' | 'refreshed' | null = null;
        let restoringAcceptedPageSyncSnapshot = false;
        const missingFxConversionSlugs = new Set<string>();
        const fxRefillCounts = new Map<string, number>();
        let forceReadyPeerConversionFailure = false;
        let correctedPriceComparisonResponseCount = 0;
        let fxSyncRequestCount = 0;
        let nextFxSyncStatus: SyncStatusFixture = 'ok';
        let nextFxSyncStatusesBySlug: ReadonlyMap<string, SyncStatusFixture> | null = null;
        let assetSyncRequestCount = 0;
        let nextAssetSyncStatus: SyncStatusFixture = 'ok';
        let nextAssetSyncStatusesById: ReadonlyMap<number, SyncStatusFixture> | null = null;
        let fxRouteMutationRequestCount = 0;
        let calendarConversionGapErrors: string[] | null = null;
        let clearCalendarConversionGapOnAcceptedReadyRoutes = false;
        let exposeMissingComparisonEventRoutes = false;
        let fxConvertRequestCount = 0;
        const fxConvertRequests: FxConvertRequest[][] = [];
        let syntheticMaxResolutionSpanDays: number | null = null;
        let pendingAcceptedCurrentMaxStandaloneFxSyncRange: SyntheticRange | null = null;
        let priceQueryRequestCount = 0;
        let mainPriceRequestCount = 0;
        let priceComparisonRequestCount = 0;
        let sharedRoutePriceComparisonRequestCount = 0;
        const priceComparisonRequestCountsByRange = new Map<string, number>();
        let calendarRequestCount = 0;
        let backendSignalRequestCount = 0;

        const parseQueries = (raw: unknown): PriceQueryRequest[] => (Array.isArray(raw) ? (raw as PriceQueryRequest[]) : []);
        const matchesSingleFxSyncRequest = (raw: unknown, expectedSlug: string): boolean => {
            if (raw === null || typeof raw !== 'object') return false;
            const pairs = (raw as FxSyncRequest).pairs;
            return Array.isArray(pairs) && pairs.length === 1 && pairs[0] === expectedSlug;
        };
        const findCalendarSignal = (raw: unknown): CalendarSignalRequest | undefined =>
            parseQueries(raw)
                .flatMap((query) => query.signals ?? [])
                .find((signal) => signal.instance_id === calendarInstanceId && signal.signal_code === calendarSignalCode);
        const findBackendSignal = (raw: unknown): CalendarSignalRequest | undefined =>
            parseQueries(raw)
                .flatMap((query) => query.signals ?? [])
                .find((signal) => signal.signal_code === backendSignalCode);
        const matchesPriceComparisonRequest = (raw: unknown, expectedPeerIds: readonly number[], expectedRange?: Pick<SyntheticRange, 'start' | 'end'>, expectedTargetCurrency?: string): boolean => {
            const queries = parseQueries(raw);
            if (findCalendarSignal(queries)) return false;
            const requestedIds = queries.flatMap((query) => (query.asset_id === undefined ? [] : [query.asset_id])).sort((left, right) => left - right);
            const expectedIds = [...new Set(expectedPeerIds)].sort((left, right) => left - right);
            if (requestedIds.length !== expectedIds.length || requestedIds.some((id, index) => id !== expectedIds[index])) return false;
            return queries.every((query) => query.include_events === true && (!expectedRange || (query.date_range?.start === expectedRange.start && query.date_range.end === expectedRange.end)) && (expectedTargetCurrency === undefined || query.target_currency === expectedTargetCurrency));
        };
        const isCalendarWindow = (value: unknown): value is CalendarWindow => typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
        const createDeferredResponse = (): DeferredResponse => {
            let release!: () => void;
            const wait = new Promise<void>((resolve) => {
                release = () => resolve();
            });
            return {wait, release};
        };
        const deferCalendarResponse = (windowDays: CalendarWindow, outcome: DeferredCalendarOutcome): DeferredCalendarResponse => {
            const deferred = {outcome, ...createDeferredResponse()};
            deferredCalendarResponses.set(windowDays, deferred);
            return deferred;
        };
        const deferNextPriceOnlyResponse = (): DeferredResponse => {
            const deferred = createDeferredResponse();
            deferredPriceOnlyResponse = deferred;
            return deferred;
        };
        const deferNextMainPriceResponse = (empty = false): DeferredMainPriceResponse => {
            const deferred = {empty, ...createDeferredResponse()};
            deferredNextMainPriceResponse = deferred;
            return deferred;
        };
        const deferProvisionalMaxPriceComparisonResponse = (): DeferredResponse => {
            const deferred = createDeferredResponse();
            deferredProvisionalMaxPriceComparisonResponse = deferred;
            return deferred;
        };
        const deferNextPriceComparisonResponse = (): DeferredResponse => {
            const deferred = createDeferredResponse();
            deferredNextPriceComparisonResponse = deferred;
            return deferred;
        };
        const deferStalePriceComparisonResponse = (range: SyntheticRange, successorExpected: boolean): DeferredPriceComparisonResponse => {
            const deferred = {range, ...createDeferredResponse()};
            deferredStalePriceComparisonResponse = deferred;
            priceComparisonRaceActive = true;
            priceComparisonRaceSuccessorServed = !successorExpected;
            return deferred;
        };
        const deferNextAssetSyncResponse = (): DeferredResponse => {
            const deferred = createDeferredResponse();
            deferredAssetSyncResponse = deferred;
            return deferred;
        };
        const deferNextFxSyncResponse = (): DeferredResponse => {
            const deferred = createDeferredResponse();
            deferredFxSyncResponse = deferred;
            return deferred;
        };
        const deferFxSyncResponse = (slug: string, status: SyncStatusFixture): DeferredFxSyncResponse => {
            const deferred = {slug, status, ...createDeferredResponse()};
            deferredFxSyncResponses.set(slug, deferred);
            return deferred;
        };
        const deferFxRefillResponse = (slug: string): DeferredFxRefillResponse => {
            const deferred = {slug, ...createDeferredResponse()};
            deferredFxRefillResponses.set(slug, deferred);
            return deferred;
        };
        const subtractDays = (date: string, days: number): string => {
            const value = new Date(`${date}T00:00:00Z`);
            value.setUTCDate(value.getUTCDate() - days);
            return value.toISOString().slice(0, 10);
        };
        const addDays = (date: string, days: number): string => {
            const value = new Date(`${date}T00:00:00Z`);
            value.setUTCDate(value.getUTCDate() + days);
            return value.toISOString().slice(0, 10);
        };
        const withCurrentEventFxAvailability = (values: unknown[]): unknown[] => {
            if (!exposeMissingComparisonEventRoutes) return values;
            return values.map((rawEvent) => {
                if (rawEvent === null || typeof rawEvent !== 'object') return rawEvent;
                const event = rawEvent as {original_value?: unknown};
                if (event.original_value === null || typeof event.original_value !== 'object') return rawEvent;
                const originalValue = event.original_value as {code?: unknown};
                if (typeof originalValue.code !== 'string') return rawEvent;
                const slug = [asset.currency, originalValue.code].sort((left, right) => left.localeCompare(right)).join('-');
                return missingFxConversionSlugs.has(slug) ? {...rawEvent, value: {...originalValue}} : rawEvent;
            });
        };
        const calendarValuesForAsset = (responseAssetId: number, windowDays: CalendarWindow): [number, number] => {
            if (responseAssetId === readyPeer.id) return [13, 16];
            if (responseAssetId === partialPeer.id) return [23, 22];
            return [windowDays / 10, -windowDays / 20];
        };
        const buildCalendarResult = (windowDays: CalendarWindow, status: CalendarSignalResultFixture['status'] = 'ok', responseAssetId: number = assetId, requestedRange?: PriceQueryRequest['date_range']): CalendarSignalResultFixture => {
            const [startValue, endValue] = calendarValuesForAsset(responseAssetId, windowDays);
            const exactBoundaryDate = requestedRange?.start && requestedRange.end && subtractDays(requestedRange.end, windowDays) === requestedRange.start ? requestedRange.end : null;
            const readyFirstDate = responseAssetId === readyPeer.id && requestedRange?.start ? addDays(requestedRange.start, windowDays) : null;
            const requestedRangeEnd = requestedRange?.end;
            const readyRangeDates = readyFirstDate && requestedRangeEnd && readyFirstDate <= requestedRangeEnd ? [...new Set([readyFirstDate, '2026-08-01', '2026-08-02', requestedRangeEnd].filter((date) => date >= readyFirstDate && date <= requestedRangeEnd))].sort() : null;
            const readyRangePointSeeds = readyRangeDates?.map((date, index, dates) => ({date, value: index === dates.length - 1 ? endValue : startValue}));
            const syntheticRangeEnd = syntheticMaxResolutionSpanDays === null ? null : requestedRange?.end;
            const pointSeeds =
                readyRangePointSeeds ??
                (exactBoundaryDate
                    ? [{date: exactBoundaryDate, value: endValue}]
                    : syntheticRangeEnd
                      ? [
                            {date: subtractDays(syntheticRangeEnd, 1), value: startValue},
                            {date: syntheticRangeEnd, value: endValue},
                        ]
                      : [
                            {date: '2026-08-01', value: startValue},
                            {date: '2026-08-02', value: endValue},
                        ]);
            const points: CalendarPointFixture[] = pointSeeds.map(({date, value}, index) => {
                const referenceDate = subtractDays(date, windowDays);
                const isExactManualReviewPeerPoint = responseAssetId === readyPeer.id && windowDays === 365 && date === exactBoundaryRange.end && referenceDate === exactBoundaryRange.start;
                const currentPriceDaysBack = isExactManualReviewPeerPoint ? 3 : responseAssetId === assetId && index === 1 ? 1 : 0;
                const referencePriceDaysBack = responseAssetId === assetId && index === 1 ? 2 : 0;
                return {
                    date,
                    value,
                    provenance: {
                        status: 'available',
                        reference_target_date: referenceDate,
                        current_price_date: subtractDays(date, currentPriceDaysBack),
                        current_price_days_back: currentPriceDaysBack,
                        reference_price_date: subtractDays(referenceDate, referencePriceDaysBack),
                        reference_price_days_back: referencePriceDaysBack,
                        current_fx_date: null,
                        current_fx_days_back: null,
                        reference_fx_date: null,
                        reference_fx_days_back: null,
                    },
                };
            });
            const requestedPointCount = points.length + (status === 'partial' ? 1 : 0);
            const coverageRatio = points.length / requestedPointCount;

            return {
                instance_id: calendarInstanceId,
                signal_code: calendarSignalCode,
                implementation_version: '1.0.0',
                normalized_params: {window_days: windowDays},
                status,
                series: [
                    {
                        key: 'calendar_return',
                        label_key: 'signals.riskRollingReturn.output',
                        description_key: 'signals.riskRollingReturn.outputDescription',
                        semantic_id: 'calendar_rolling_return.value',
                        semantic_description: 'Price-only return over an exact calendar-day window.',
                        unit: 'percentage',
                        axis: {key: 'calendar_return', role: 'independent', minimum: null, maximum: null},
                        view_transform: 'none',
                        style: {color_role: 'primary', line_pattern: null, width_delta: 0, opacity: 1, fill_opacity: 0.2},
                        reference_levels: [{key: 'zero', label_key: 'signals.reference.zero', semantic: 'No price-only gain or loss.', value: 0}],
                        value_regions: [],
                        kind: 'line',
                        points,
                    },
                ],
                availability: {
                    domain_compatible: true,
                    can_compute: true,
                    missing_price_fields: [],
                    missing_event_types: [],
                    input_coverage: {
                        requested_points: requestedPointCount,
                        available_points: points.length,
                        contiguous_points: points.length,
                        observed_points: points.length,
                        backfilled_points: 0,
                        missing_points: requestedPointCount - points.length,
                        max_consecutive_missing_points: status === 'partial' ? 1 : 0,
                        internal_gap_count: 0,
                        coverage_ratio: coverageRatio,
                        field_coverage: {close: coverageRatio},
                        event_type_counts: {},
                        first_available_date: points.at(0)?.date ?? null,
                        last_available_date: points.at(-1)?.date ?? null,
                    },
                    required_points: windowDays,
                    warmup_complete: true,
                    partial_coverage_used: status === 'partial',
                    reason_code: status === 'partial' ? 'partial_input_coverage' : null,
                },
                warmup: {
                    requirement: {
                        minimum_points: 2,
                        stabilization_points: windowDays - 2,
                        total_points: windowDays,
                        normalized_tolerance: 0.000001,
                        full_history: false,
                    },
                    loaded_points: windowDays + points.length,
                    used_points: windowDays,
                    complete: true,
                },
                annotations: [],
                warnings:
                    status === 'partial'
                        ? [
                              {
                                  code: 'partial_input_coverage',
                                  message: 'Synthetic partial calendar-return coverage.',
                                  details: {},
                              },
                          ]
                        : [],
                error: null,
                risk_metadata: null,
                data_quality: null,
            };
        };
        const buildBackendSignalResult = (request: CalendarSignalRequest, requestedRange?: PriceQueryRequest['date_range']) => {
            if (!request.instance_id) {
                throw new Error(`Backend signal request is missing instance_id: ${JSON.stringify(request)}`);
            }
            const fixture = buildCalendarResult(7, 'ok', assetId, requestedRange);
            return {
                ...fixture,
                instance_id: request.instance_id,
                signal_code: backendSignalCode,
                normalized_params: {...(request.params ?? {})},
                series: fixture.series.map((series) => ({
                    ...series,
                    key: 'rolling_volatility',
                    label_key: 'signals.riskRollingVolatility.output',
                    description_key: 'signals.riskRollingVolatility.outputDescription',
                    semantic_id: 'rolling_realized_volatility.value',
                    semantic_description: 'Synthetic rolling volatility restored by the Price successor.',
                    axis: {key: 'risk_volatility', role: 'independent', minimum: 0, maximum: null},
                    reference_levels: [],
                    points: series.points.map((point, index) => ({
                        ...point,
                        value: 4 + index,
                    })),
                })),
            };
        };
        const buildSchemaValidCalendarInvalidResult = (windowDays: CalendarWindow, requestedRange?: PriceQueryRequest['date_range']) => {
            const result = buildCalendarResult(windowDays, 'ok', invalidCalendarPeer.id, requestedRange);
            return {
                ...result,
                // A generic signal result may use any series key. Calendar
                // extraction is stricter and requires `calendar_return`.
                series: result.series.map((series) => ({
                    ...series,
                    key: 'generic_output',
                })),
            };
        };
        const buildUnavailableCalendarResult = (windowDays: CalendarWindow) => ({
            instance_id: calendarInstanceId,
            signal_code: calendarSignalCode,
            implementation_version: '1.0.0',
            normalized_params: {window_days: windowDays},
            status: 'unavailable',
            series: [],
            availability: {
                domain_compatible: true,
                can_compute: false,
                missing_price_fields: [],
                missing_event_types: [],
                input_coverage: {
                    requested_points: 0,
                    available_points: 0,
                    contiguous_points: 0,
                    observed_points: 0,
                    backfilled_points: 0,
                    missing_points: 0,
                    max_consecutive_missing_points: 0,
                    internal_gap_count: 0,
                    coverage_ratio: 0,
                    field_coverage: {close: 0},
                    event_type_counts: {},
                    first_available_date: null,
                    last_available_date: null,
                },
                required_points: windowDays,
                warmup_complete: false,
                partial_coverage_used: false,
                reason_code: 'insufficient_history',
            },
            warmup: {
                requirement: {
                    minimum_points: 2,
                    stabilization_points: Math.max(0, windowDays - 2),
                    total_points: windowDays,
                    normalized_tolerance: 0.000001,
                    full_history: false,
                },
                loaded_points: 0,
                used_points: 0,
                complete: false,
            },
            annotations: [],
            warnings: [
                {
                    code: 'data_quality',
                    message: 'Synthetic unavailable calendar-return coverage.',
                    details: {},
                },
            ],
            error: null,
            risk_metadata: null,
            data_quality: null,
        });
        const buildMalformedUnavailableCalendarResult = (windowDays: CalendarWindow) => ({
            instance_id: calendarInstanceId,
            signal_code: calendarSignalCode,
            normalized_params: {window_days: windowDays},
            status: 'unavailable',
            series: [{key: 'calendar_return', points: []}],
        });
        const buildFxConversionGapCalendarResult = (windowDays: CalendarWindow) => {
            const unavailable = buildUnavailableCalendarResult(windowDays);
            return {
                ...unavailable,
                availability: {
                    ...unavailable.availability,
                    missing_price_fields: ['close'],
                    reason_code: 'missing_input_fields',
                },
                warnings: [
                    {
                        code: 'data_quality',
                        message: 'Synthetic missing close after FX conversion.',
                        details: {},
                    },
                ],
            };
        };
        const buildFailedCalendarResult = (windowDays: CalendarWindow, requestedRange?: PriceQueryRequest['date_range']) => {
            const result = buildCalendarResult(windowDays, 'ok', errorPeer.id, requestedRange);
            return {
                ...result,
                status: 'failed',
                series: [],
                annotations: [],
                warnings: [],
                error: {
                    code: 'compute_error',
                    message: 'Synthetic failed calendar-return calculation.',
                    details: {},
                    retryable: false,
                },
            };
        };
        const i60gAvailablePoint = (date: string, value: number, referenceDate: string, withFx = false): CalendarPointFixture => ({
            date,
            value,
            provenance: {
                status: 'available',
                reference_target_date: referenceDate,
                current_price_date: date,
                current_price_days_back: 0,
                reference_price_date: referenceDate,
                reference_price_days_back: 0,
                current_fx_date: withFx ? date : null,
                current_fx_days_back: withFx ? 0 : null,
                reference_fx_date: withFx ? referenceDate : null,
                reference_fx_days_back: withFx ? 0 : null,
            },
        });
        const i60gMissingReferencePoint = (date: string, referenceDate: string, withFx = false): CalendarPointFixture => ({
            date,
            value: null,
            provenance: {
                status: 'missing_reference',
                reference_target_date: referenceDate,
                current_price_date: date,
                current_price_days_back: 0,
                reference_price_date: withFx ? referenceDate : null,
                reference_price_days_back: withFx ? 0 : null,
                current_fx_date: withFx ? date : null,
                current_fx_days_back: withFx ? 0 : null,
                reference_fx_date: null,
                reference_fx_days_back: null,
            },
        });
        const buildI60GCalendarResult = (responseAssetId: number, requestedRange: PriceQueryRequest['date_range'], staleValues = false) => {
            if (typeof requestedRange?.start !== 'string' || typeof requestedRange.end !== 'string') {
                throw new Error(`I60G Calendar fixture requires a concrete selected range: ${JSON.stringify(requestedRange)}`);
            }
            const valueDelta = staleValues ? 1000 : 0;
            const withDelta = (point: CalendarPointFixture): CalendarPointFixture => ({
                ...point,
                value: point.value === null ? null : point.value + valueDelta,
            });
            const fixturePoints = new Map<number, CalendarPointFixture[]>([
                [assetId, [i60gAvailablePoint('2026-04-01', 7, '2026-03-25'), i60gAvailablePoint('2026-04-05', 7.4, '2026-03-29'), i60gMissingReferencePoint('2026-04-10', '2026-04-03'), i60gAvailablePoint('2026-04-15', 8.1, '2026-04-08')]],
                [readyPeer.id, [i60gAvailablePoint('2026-04-06', 16, '2026-03-30'), i60gAvailablePoint('2026-04-09', 17, '2026-04-02'), i60gAvailablePoint('2026-04-15', 18, '2026-04-08')]],
                [
                    partialPeer.id,
                    [
                        i60gAvailablePoint('2026-04-01', 21, '2026-03-25', true),
                        i60gAvailablePoint('2026-04-05', 22, '2026-03-29', true),
                        i60gMissingReferencePoint('2026-04-10', '2026-04-03', true),
                        i60gAvailablePoint('2026-04-12', 24, '2026-04-05', true),
                        i60gAvailablePoint('2026-04-15', 25, '2026-04-08', true),
                    ],
                ],
                [errorPeer.id, [i60gAvailablePoint('2026-04-11', 31, '2026-04-04'), i60gAvailablePoint('2026-04-13', 32, '2026-04-06'), i60gAvailablePoint('2026-04-15', 33, '2026-04-08')]],
            ]);
            const selectedPointCount = Math.round((Date.parse(`${requestedRange.end}T00:00:00Z`) - Date.parse(`${requestedRange.start}T00:00:00Z`)) / 86_400_000) + 1;

            if (responseAssetId === unavailablePeer.id) {
                const unavailable = buildUnavailableCalendarResult(7);
                return {
                    ...unavailable,
                    implementation_version: '1.3.0',
                    availability: {
                        ...unavailable.availability,
                        input_coverage: {
                            ...unavailable.availability.input_coverage,
                            requested_points: selectedPointCount,
                            missing_points: selectedPointCount,
                            max_consecutive_missing_points: selectedPointCount,
                        },
                        required_points: 7,
                        warmup_complete: true,
                        reason_code: 'undefined_metric',
                    },
                    warmup: {
                        requirement: {
                            minimum_points: 1,
                            stabilization_points: 6,
                            total_points: 7,
                            normalized_tolerance: 0.000001,
                            full_history: false,
                        },
                        loaded_points: 20,
                        used_points: 7,
                        complete: true,
                    },
                    warnings: [
                        {
                            code: 'undefined_metric_window',
                            message: 'Every selected I60G Calendar output is undefined.',
                            details: {
                                unavailable_points: selectedPointCount,
                                reasons: {invalid_current_price: selectedPointCount},
                            },
                        },
                    ],
                };
            }

            const allPoints = fixturePoints.get(responseAssetId);
            if (!allPoints) {
                throw new Error(`No I60G Calendar fixture is defined for asset ${responseAssetId}`);
            }
            const points = allPoints.filter((point) => point.date >= requestedRange.start! && point.date <= requestedRange.end!).map(withDelta);
            const availablePoints = points.filter((point) => point.value !== null);
            const reasonCode = responseAssetId === assetId ? 'partial_undefined_metric' : responseAssetId === readyPeer.id ? 'partial_input_coverage' : responseAssetId === partialPeer.id ? 'data_gap' : 'incomplete_warmup';
            const warningCode = responseAssetId === assetId ? 'undefined_metric_window' : reasonCode;
            const warmupComplete = reasonCode !== 'incomplete_warmup';
            const partialCoverageUsed = reasonCode === 'partial_input_coverage' || reasonCode === 'data_gap';
            const base = buildCalendarResult(7, 'partial', responseAssetId, requestedRange);
            return {
                ...base,
                implementation_version: '1.3.0',
                series: base.series.map((series) => ({
                    ...series,
                    semantic_description: 'Price-only return from the resolved value exactly N calendar days earlier.',
                    points,
                })),
                availability: {
                    ...base.availability,
                    input_coverage: {
                        ...base.availability.input_coverage,
                        requested_points: selectedPointCount,
                        available_points: availablePoints.length,
                        contiguous_points: availablePoints.length,
                        observed_points: availablePoints.length,
                        missing_points: selectedPointCount - availablePoints.length,
                        max_consecutive_missing_points: reasonCode === 'data_gap' ? 1 : selectedPointCount - availablePoints.length,
                        internal_gap_count: points.some((point) => point.value === null) ? 1 : 0,
                        coverage_ratio: availablePoints.length / selectedPointCount,
                        field_coverage: {close: availablePoints.length / selectedPointCount},
                        first_available_date: availablePoints.find((point) => point.value !== null)?.date ?? null,
                        last_available_date: [...availablePoints].reverse().find((point) => point.value !== null)?.date ?? null,
                    },
                    required_points: 7,
                    warmup_complete: warmupComplete,
                    partial_coverage_used: partialCoverageUsed,
                    reason_code: reasonCode,
                },
                warmup: {
                    requirement: {
                        minimum_points: 1,
                        stabilization_points: 6,
                        total_points: 7,
                        normalized_tolerance: 0.000001,
                        full_history: false,
                    },
                    loaded_points: 20,
                    used_points: warmupComplete ? 7 : 3,
                    complete: warmupComplete,
                },
                warnings: [
                    {
                        code: warningCode,
                        message: `Synthetic I60G Calendar cause ${reasonCode}.`,
                        details: {
                            selected_start_date: requestedRange.start,
                            selected_end_date: requestedRange.end,
                            excluded_points: selectedPointCount - availablePoints.length,
                            max_consecutive_missing_points: reasonCode === 'data_gap' ? 1 : selectedPointCount - availablePoints.length,
                        },
                    },
                ],
            };
        };
        const calendarRequestMatchesRange = (raw: unknown, windowDays: CalendarWindow, range: Pick<SyntheticRange, 'start' | 'end'>): boolean => {
            const queries = parseQueries(raw);
            const mainQuery = queries.find((query) => query.asset_id === assetId);
            return findCalendarSignal(queries)?.params?.window_days === windowDays && mainQuery?.date_range?.start === range.start && mainQuery.date_range.end === range.end;
        };
        const waitForCalendarResponse = (windowDays: CalendarWindow) =>
            page.waitForResponse(
                (response) => {
                    const request = response.request();
                    if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                    return findCalendarSignal(request.postDataJSON())?.params?.window_days === windowDays;
                },
                {timeout: 10_000},
            );
        const waitForCalendarResponseForRange = (windowDays: CalendarWindow, range: Pick<SyntheticRange, 'start' | 'end'>) =>
            page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/query' && calendarRequestMatchesRange(response.request().postDataJSON(), windowDays, range), {timeout: 10_000});
        const waitForCalendarRequest = (windowDays: CalendarWindow) =>
            page.waitForRequest(
                (request) => {
                    if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                    return findCalendarSignal(request.postDataJSON())?.params?.window_days === windowDays;
                },
                {timeout: 10_000},
            );
        const waitForCalendarRequestForRange = (windowDays: CalendarWindow, range: Pick<SyntheticRange, 'start' | 'end'>) =>
            page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/query' && calendarRequestMatchesRange(request.postDataJSON(), windowDays, range), {timeout: 10_000});
        const assertCalendarRequest = (raw: unknown, windowDays: CalendarWindow, expectedIncludePrice?: boolean) => {
            const query = parseQueries(raw).find((candidate) => candidate.asset_id === assetId);
            expect(query, `calendar request must target synthetic asset ${assetId}`).toBeDefined();
            if (expectedIncludePrice !== undefined) {
                expect(query?.include_price).toBe(expectedIncludePrice);
            }
            const signal = query?.signals?.find((candidate) => candidate.instance_id === calendarInstanceId && candidate.signal_code === calendarSignalCode);
            expect(signal).toMatchObject({
                instance_id: calendarInstanceId,
                signal_code: calendarSignalCode,
                params: {window_days: windowDays},
            });
        };
        const assertCalendarBulkRequest = (raw: unknown, windowDays: CalendarWindow, expectedPeerIds: readonly number[] = comparisonPeerIds, expectedTargetCurrency = asset.currency) => {
            const queries = parseQueries(raw);
            const expectedCalendarAssetIds = [assetId, ...new Set(expectedPeerIds)];
            const requestedAssetIds = queries.flatMap((query) => (query.asset_id === undefined ? [] : [query.asset_id])).sort((left, right) => left - right);
            expect(requestedAssetIds).toEqual([...expectedCalendarAssetIds].sort((left, right) => left - right));

            const mainQuery = queries.find((query) => query.asset_id === assetId);
            expect(mainQuery?.date_range).toBeDefined();
            for (const expectedAssetId of expectedCalendarAssetIds) {
                const query = queries.find((candidate) => candidate.asset_id === expectedAssetId);
                expect(query, `calendar bulk request must contain asset ${expectedAssetId}`).toBeDefined();
                expect(query?.date_range).toEqual(mainQuery?.date_range);
                const signal = query?.signals?.find((candidate) => candidate.instance_id === calendarInstanceId && candidate.signal_code === calendarSignalCode);
                expect(signal?.params?.window_days, `asset ${expectedAssetId} must use the shared calendar window`).toBe(windowDays);
                if (expectedAssetId !== assetId) {
                    expect(query, `peer ${expectedAssetId} must remain signal-only in the shared target currency`).toMatchObject({
                        include_price: false,
                        include_events: true,
                        target_currency: expectedTargetCurrency,
                    });
                }
            }
        };
        const assertPriceComparisonRequest = (raw: unknown, expectedPeerIds: readonly number[], expectedRange: Pick<SyntheticRange, 'start' | 'end'>, expectedTargetCurrency: string) => {
            expect(matchesPriceComparisonRequest(raw, expectedPeerIds, expectedRange, expectedTargetCurrency)).toBe(true);
            const queries = parseQueries(raw);
            for (const expectedPeerId of new Set(expectedPeerIds)) {
                const query = queries.find((candidate) => candidate.asset_id === expectedPeerId);
                expect(query, `price comparison request must contain peer ${expectedPeerId}`).toEqual({
                    asset_id: expectedPeerId,
                    date_range: {start: expectedRange.start, end: expectedRange.end},
                    include_events: true,
                    target_currency: expectedTargetCurrency,
                });
            }
        };
        const waitForPriceComparisonRequest = (expectedPeerIds: readonly number[], expectedRange: Pick<SyntheticRange, 'start' | 'end'>, expectedTargetCurrency: string) =>
            page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/query' && matchesPriceComparisonRequest(request.postDataJSON(), expectedPeerIds, expectedRange, expectedTargetCurrency), {timeout: 10_000});
        const waitForPriceComparisonResponse = (expectedPeerIds: readonly number[] = comparisonPeerIds, expectedRange?: Pick<SyntheticRange, 'start' | 'end'>, expectedTargetCurrency?: string) =>
            page.waitForResponse(
                (response) => {
                    const request = response.request();
                    if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                    return matchesPriceComparisonRequest(request.postDataJSON(), expectedPeerIds, expectedRange, expectedTargetCurrency);
                },
                {timeout: 10_000},
            );
        const waitForMainRangeResponse = (range: Pick<SyntheticRange, 'start' | 'end'>) =>
            page.waitForResponse(
                (response) => {
                    const request = response.request();
                    if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                    const mainQuery = parseQueries(request.postDataJSON()).find((query) => query.asset_id === assetId);
                    return mainQuery?.date_range?.start === range.start && mainQuery.date_range.end === range.end;
                },
                {timeout: 10_000},
            );
        const waitForMainPriceRequest = (range: Pick<SyntheticRange, 'start' | 'end'>) =>
            page.waitForRequest(
                (request) => {
                    if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                    const queries = parseQueries(request.postDataJSON());
                    const mainQuery = queries.find((query) => query.asset_id === assetId);
                    return findCalendarSignal(queries) === undefined && mainQuery?.date_range?.start === range.start && mainQuery.date_range.end === range.end;
                },
                {timeout: 10_000},
            );
        const waitForMainPriceResponse = (range: Pick<SyntheticRange, 'start' | 'end'>, expectedTargetCurrency?: string) =>
            page.waitForResponse(
                (response) => {
                    const request = response.request();
                    if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                    const queries = parseQueries(request.postDataJSON());
                    const mainQuery = queries.find((query) => query.asset_id === assetId);
                    return findCalendarSignal(queries) === undefined && mainQuery?.date_range?.start === range.start && mainQuery.date_range.end === range.end && (expectedTargetCurrency === undefined || (mainQuery.target_currency ?? '') === expectedTargetCurrency);
                },
                {timeout: 10_000},
            );
        const waitForBackendSignalRequest = (range?: Pick<SyntheticRange, 'start' | 'end'>) =>
            page.waitForRequest(
                (request) => {
                    if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                    const query = parseQueries(request.postDataJSON()).find((candidate) => candidate.asset_id === assetId);
                    return query?.signals?.some((signal) => signal.signal_code === backendSignalCode) === true && (!range || (query.date_range?.start === range.start && query.date_range.end === range.end));
                },
                {timeout: 10_000},
            );
        const waitForBackendSignalResponse = (range?: Pick<SyntheticRange, 'start' | 'end'>) =>
            page.waitForResponse(
                (response) => {
                    const request = response.request();
                    if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                    const query = parseQueries(request.postDataJSON()).find((candidate) => candidate.asset_id === assetId);
                    return query?.signals?.some((signal) => signal.signal_code === backendSignalCode) === true && (!range || (query.date_range?.start === range.start && query.date_range.end === range.end));
                },
                {timeout: 10_000},
            );
        const assertBackendSignalRequest = (raw: unknown, expectedInstanceId: string, expectedRange: Pick<SyntheticRange, 'start' | 'end'>) => {
            const query = parseQueries(raw).find((candidate) => candidate.asset_id === assetId);
            expect(query, `backend signal request must target synthetic asset ${assetId}`).toBeDefined();
            expect(query?.date_range).toEqual({start: expectedRange.start, end: expectedRange.end});
            expect(query?.signals?.find((signal) => signal.signal_code === backendSignalCode)).toEqual({
                instance_id: expectedInstanceId,
                signal_code: backendSignalCode,
                params: {window: 30},
            });
        };
        const assertMainDateRange = (raw: unknown, range: Pick<SyntheticRange, 'start' | 'end'>) => {
            const mainQuery = parseQueries(raw).find((query) => query.asset_id === assetId);
            expect(mainQuery, `range request must target synthetic asset ${assetId}`).toBeDefined();
            expect(mainQuery?.date_range).toEqual({
                start: range.start,
                end: range.end,
            });
        };
        const assertAssetSyncRequest = (raw: unknown, expectedAssetId: number, range: Pick<SyntheticRange, 'start' | 'end'>) => {
            expect(raw).toEqual([
                {
                    asset_id: expectedAssetId,
                    date_range: {
                        start: range.start,
                        end: range.end,
                    },
                },
            ]);
        };
        const assertFxSyncRequest = (raw: unknown, expectedPairs: readonly string[], range: Pick<SyntheticRange, 'start' | 'end'>) => {
            expect(raw).toEqual({
                pairs: [...expectedPairs],
                start: range.start,
                end: range.end,
            });
        };
        const expectedFxSyncResults = (pairs: readonly string[], status: SyncStatusFixture) => pairs.map((pair) => ({pair, status}));
        const readPersistedPairSettings = async (storageKey: string): Promise<Record<string, unknown> | null> =>
            page.evaluate(
                ({key, pairKey}) => {
                    const raw = localStorage.getItem(key);
                    if (!raw) return null;
                    const parsed = JSON.parse(raw) as {pairOverrides?: unknown};
                    if (!Array.isArray(parsed.pairOverrides)) return null;
                    for (const entry of parsed.pairOverrides) {
                        if (!Array.isArray(entry) || entry.length !== 2) continue;
                        const [storedPairKey, storedSettings] = entry;
                        if (storedPairKey === pairKey && storedSettings && typeof storedSettings === 'object') {
                            return storedSettings as Record<string, unknown>;
                        }
                    }
                    return null;
                },
                {key: storageKey, pairKey: `asset-${assetId}`},
            );
        const readMeasureRowIds = (container: Locator): Promise<string[]> =>
            container.getByRole('row', {includeHidden: true}).evaluateAll((rows) =>
                rows.flatMap((row) => {
                    const id = row.getAttribute('data-row-id');
                    return id === null ? [] : [id];
                }),
            );
        const readSignalCardTestIds = (container: Locator): Promise<string[]> =>
            container.getByTestId(/^signal-card-/).evaluateAll((cards) =>
                cards.flatMap((card) => {
                    const testId = card.getAttribute('data-testid');
                    return testId === null ? [] : [testId];
                }),
            );
        const selectCalendarUnit = async (trigger: Locator, target: CalendarWindowUnit): Promise<void> => {
            await trigger.click();
            await expect(trigger).toHaveAttribute('aria-expanded', 'true');
            await expect.poll(async () => (await trigger.getAttribute('aria-activedescendant')) ?? '').toContain('-option-');
            await trigger.press('Home');
            await expect(trigger).toHaveAttribute('aria-activedescendant', /-option-weeks$/);

            const visitedOptions = new Set<string>();
            while (true) {
                const activeDescendant = await trigger.getAttribute('aria-activedescendant');
                if (!activeDescendant || visitedOptions.has(activeDescendant)) break;
                if (activeDescendant?.endsWith(`-option-${target}`)) {
                    await trigger.press('Enter');
                    await expect(trigger).toHaveAttribute('aria-expanded', 'false');
                    return;
                }
                visitedOptions.add(activeDescendant);
                await trigger.press('ArrowDown');
                await expect.poll(async () => await trigger.getAttribute('aria-activedescendant')).not.toBe(activeDescendant);
            }
            throw new Error(`Calendar duration unit ${target} was not reachable through aria-activedescendant navigation`);
        };

        const staleFixturePoint = buildCalendarResult(30)
            .series.find((series) => series.key === 'calendar_return')
            ?.points.find((point) => point.date === '2026-08-02');
        expect(staleFixturePoint?.provenance).toMatchObject({
            reference_target_date: '2026-07-03',
            current_price_date: '2026-08-01',
            current_price_days_back: 1,
            reference_price_date: '2026-07-01',
            reference_price_days_back: 2,
        });
        expect(schemas.SignalResult.safeParse(buildSchemaValidCalendarInvalidResult(30)).success).toBe(true);
        expect(schemas.SignalResult.safeParse(buildFxConversionGapCalendarResult(30)).success).toBe(true);
        expect(schemas.SignalResult.safeParse(buildUnavailableCalendarResult(30)).success).toBe(true);
        expect(schemas.SignalResult.safeParse(buildMalformedUnavailableCalendarResult(30)).success).toBe(false);
        for (const i60gAssetId of [assetId, readyPeer.id, partialPeer.id, unavailablePeer.id, errorPeer.id]) {
            const parsed = schemas.SignalResult.safeParse(buildI60GCalendarResult(i60gAssetId, i60gRange));
            expect(parsed.success, `I60G Calendar fixture for asset ${i60gAssetId} must satisfy SignalResult`).toBe(true);
        }

        const meResponse = await page.request.get('/api/v1/auth/me');
        expect(meResponse.ok()).toBe(true);
        const mePayload = (await meResponse.json()) as {user?: {id?: unknown}};
        const userId = mePayload.user?.id;
        expect(userId, 'authenticated user id is required for the chart settings storage key').toEqual(expect.any(Number));
        if (typeof userId !== 'number' || !Number.isSafeInteger(userId)) {
            throw new Error('GET /api/v1/auth/me did not return a safe integer user id');
        }
        const chartSettingsStorageKey = `lf_${userId}_chartSettingsStore`;
        await page.evaluate(
            ({storageKey, pairKey, settings}) => {
                localStorage.setItem(
                    storageKey,
                    JSON.stringify({
                        version: 2,
                        globalSettings: {...settings, signals: []},
                        pairOverrides: [[pairKey, settings]],
                    }),
                );
            },
            {
                storageKey: chartSettingsStorageKey,
                pairKey: `asset-${assetId}`,
                settings: seededChartSettings,
            },
        );
        expect(await readPersistedPairSettings(chartSettingsStorageKey)).not.toHaveProperty('calendarReturnWindow');

        await page.route('**/api/v1/fx/providers/routes*', async (route) => {
            if (route.request().method() !== 'GET') {
                fxRouteMutationRequestCount += 1;
                await route.fulfill({
                    status: 500,
                    json: {detail: 'Unexpected FX route mutation from comparison Asset sync'},
                });
                return;
            }
            await route.fulfill({
                json: {
                    items: configuredFxCurrencies.map((currency, index) => ({
                        base: 'EUR',
                        quote: currency,
                        priority: index + 1,
                        chain_steps: [{from: 'EUR', to: currency, provider: 'MOCKFX'}],
                        is_chain: false,
                        providers_used: ['MOCKFX'],
                    })),
                },
            });
        });
        await page.route('**/api/v1/assets/query*', async (route) => {
            await route.fulfill({json: [asset, ...availableComparisonPeers]});
        });
        await page.route('**/api/v1/assets/provider/assignments*', async (route) => {
            await route.fulfill({
                json: [
                    {
                        asset_id: assetId,
                        provider_code: 'MOCKASSET',
                        identifier: `SYNTH-${assetId}`,
                        identifier_type: 'TICKER',
                        provider_params: {},
                        last_fetch_at: null,
                    },
                ],
            });
        });
        await page.route('**/api/v1/assets/prices/sync', async (route) => {
            expect(route.request().method()).toBe('POST');
            const requests = route.request().postDataJSON() as AssetSyncRequest[];
            const requestAssetIds = requests.flatMap((candidate) => (typeof candidate.asset_id === 'number' && Number.isSafeInteger(candidate.asset_id) ? [candidate.asset_id] : []));
            if (requests.length === 0 || requestAssetIds.length !== requests.length) {
                throw new Error(`Unexpected Asset sync payload: ${JSON.stringify(requests)}`);
            }
            const statusById = nextAssetSyncStatusesById;
            if (statusById && requestAssetIds.some((requestAssetId) => !statusById.has(requestAssetId))) {
                throw new Error(`Missing synthetic Asset sync status for payload: ${JSON.stringify(requests)}`);
            }
            const defaultStatus = nextAssetSyncStatus;
            const statusFor = (requestAssetId: number): SyncStatusFixture => statusById?.get(requestAssetId) ?? defaultStatus;
            const acceptedCount = requestAssetIds.filter((requestAssetId) => {
                const status = statusFor(requestAssetId);
                return status === 'ok' || status === 'partial';
            }).length;
            const accepted = acceptedCount === requestAssetIds.length;
            nextAssetSyncStatus = 'ok';
            nextAssetSyncStatusesById = null;
            assetSyncRequestCount += 1;
            const deferred = deferredAssetSyncResponse;
            deferredAssetSyncResponse = null;
            if (deferred) {
                await deferred.wait;
            }
            await route.fulfill({
                json: {
                    results: requestAssetIds.map((requestAssetId) => {
                        const status = statusFor(requestAssetId);
                        const resultAccepted = status === 'ok' || status === 'partial';
                        return {
                            asset_id: requestAssetId,
                            status,
                            points_fetched: resultAccepted ? 3 : 0,
                            points_changed: resultAccepted ? 3 : 0,
                            provider_used: resultAccepted ? 'MOCKASSET' : null,
                            changed_points: [],
                            events_fetched: resultAccepted ? 2 : 0,
                            events_changed: resultAccepted ? 2 : 0,
                            errors: resultAccepted ? [] : ['synthetic-asset-sync-failure'],
                        };
                    }),
                    success_count: acceptedCount,
                    errors: accepted ? [] : ['synthetic-asset-sync-failure'],
                },
            });
        });
        await page.route('**/api/v1/fx/currencies/sync', async (route) => {
            expect(route.request().method()).toBe('POST');
            fxSyncRequestCount += 1;
            const request = route.request().postDataJSON() as FxSyncRequest;
            const {pairs, start, end} = request;
            if (!Array.isArray(pairs) || !pairs.every((pair): pair is string => typeof pair === 'string') || typeof start !== 'string' || typeof end !== 'string') {
                throw new Error(`Unexpected FX sync payload: ${JSON.stringify(request)}`);
            }
            const requestedPairs = pairs;
            const perSlugDeferred = requestedPairs.length === 1 ? deferredFxSyncResponses.get(requestedPairs.at(0)!) : undefined;
            const statusBySlug = nextFxSyncStatusesBySlug;
            const defaultStatus = nextFxSyncStatus;
            if (!perSlugDeferred && statusBySlug && requestedPairs.some((pair) => !statusBySlug.has(pair))) {
                throw new Error(`Missing synthetic FX sync status for payload: ${JSON.stringify(request)}`);
            }
            const statusFor = (pair: string): SyncStatusFixture => perSlugDeferred?.status ?? statusBySlug?.get(pair) ?? defaultStatus;
            const acceptedPairs = requestedPairs.filter((pair) => {
                const status = statusFor(pair);
                return status === 'ok' || status === 'partial';
            });
            if (!perSlugDeferred) {
                nextFxSyncStatus = 'ok';
                nextFxSyncStatusesBySlug = null;
            }
            const deferred = perSlugDeferred ?? deferredFxSyncResponse;
            if (perSlugDeferred) {
                deferredFxSyncResponses.delete(perSlugDeferred.slug);
            } else {
                deferredFxSyncResponse = null;
            }
            if (deferred) {
                await deferred.wait;
            }
            if (acceptedPairs.length > 0) {
                priceComparisonSyncSucceeded = true;
                for (const slug of acceptedPairs) missingFxConversionSlugs.delete(slug);
                if (clearCalendarConversionGapOnAcceptedReadyRoutes && readyPeerRequiredFxSlugs.every((slug) => acceptedPairs.includes(slug))) {
                    calendarConversionGapErrors = null;
                    clearCalendarConversionGapOnAcceptedReadyRoutes = false;
                }
                if (requestedPairs.length === 1 && requestedPairs.includes(readyPeerFxSlug) && acceptedPairs.length === 1 && acceptedPairs.includes(readyPeerFxSlug) && start === 'min' && syntheticMaxResolutionSpanDays !== null) {
                    pendingAcceptedCurrentMaxStandaloneFxSyncRange = {
                        start: subtractDays(end, syntheticMaxResolutionSpanDays),
                        end,
                        spanDays: syntheticMaxResolutionSpanDays,
                    };
                }
            }
            await route.fulfill({
                json: {
                    results: requestedPairs.map((pair) => {
                        const status = statusFor(pair);
                        const accepted = status === 'ok' || status === 'partial';
                        return {
                            pair,
                            status,
                            points_fetched: accepted ? 2 : 0,
                            points_changed: accepted ? 2 : 0,
                            provider_used: accepted ? 'MOCKFX' : null,
                            message: status === 'failed' ? 'synthetic-fx-sync-failure' : status === 'skipped' ? 'synthetic-fx-sync-skipped' : null,
                            errors: status === 'failed' ? ['synthetic-fx-sync-failure'] : [],
                        };
                    }),
                    success_count: acceptedPairs.length,
                    date_range: {start, end},
                    total_points_changed: 2 * acceptedPairs.length,
                },
            });
        });
        await page.route('**/api/v1/fx/currencies/convert', async (route) => {
            expect(route.request().method()).toBe('POST');
            fxConvertRequestCount += 1;
            const requests = route.request().postDataJSON() as FxConvertRequest[];
            fxConvertRequests.push(requests);
            const requestedSlugs = [...new Set(requests.map((conversion) => [conversion.from_amount.code, conversion.to].sort().join('-')))];
            for (const slug of requestedSlugs) {
                fxRefillCounts.set(slug, (fxRefillCounts.get(slug) ?? 0) + 1);
                const deferred = deferredFxRefillResponses.get(slug);
                if (!deferred) continue;
                deferredFxRefillResponses.delete(slug);
                await deferred.wait;
            }
            if (!priceComparisonSyncSucceeded) {
                await route.fulfill({json: {results: [], success_count: 0, signal_results: []}});
                return;
            }
            const requestedSlugsIncludeMissing = requestedSlugs.some((slug) => missingFxConversionSlugs.has(slug));
            if (requestedSlugsIncludeMissing) {
                await route.fulfill({json: {results: [], success_count: 0, signal_results: []}});
                return;
            }
            const results = requests.map((conversion) => ({
                from_amount: conversion.from_amount,
                to_amount: {code: conversion.to, amount: conversion.from_amount.amount},
                conversion_date: conversion.date_range.end,
                rate: '1',
            }));
            await route.fulfill({
                json: {
                    results,
                    success_count: results.length,
                    signal_results: [],
                },
            });
        });
        await page.route('**/api/v1/assets/prices/query', async (route) => {
            priceQueryRequestCount += 1;
            const requests = parseQueries(route.request().postDataJSON());
            if (matchesPriceComparisonRequest(requests, comparisonPeerIds, undefined, asset.currency)) {
                priceComparisonRequestCount += 1;
                const range = requests.find((request) => request.asset_id === readyPeer.id)?.date_range;
                if (range?.start && range.end) {
                    const key = `${range.start}|${range.end}`;
                    priceComparisonRequestCountsByRange.set(key, (priceComparisonRequestCountsByRange.get(key) ?? 0) + 1);
                }
            }
            if (matchesPriceComparisonRequest(requests, sharedRoutePeerIds, undefined, 'GBP')) {
                sharedRoutePriceComparisonRequestCount += 1;
            }
            const requestedDeferredWindow = findCalendarSignal(requests)?.params?.window_days;
            if (isCalendarWindow(requestedDeferredWindow)) {
                calendarRequestCount += 1;
            }
            if (findBackendSignal(requests)) {
                backendSignalRequestCount += 1;
            }
            const isMainPriceRequest = requestedDeferredWindow === undefined && requests.some((request) => request.asset_id === assetId);
            if (isMainPriceRequest) {
                mainPriceRequestCount += 1;
            }
            const deferredWindow = isCalendarWindow(requestedDeferredWindow) && deferredCalendarResponses.has(requestedDeferredWindow) ? requestedDeferredWindow : undefined;
            const deferred = deferredWindow === undefined ? undefined : deferredCalendarResponses.get(deferredWindow);
            const deferredPriceOnly = requestedDeferredWindow === undefined && requests.some((request) => request.asset_id === assetId && request.include_price !== false) ? deferredPriceOnlyResponse : null;
            const deferredMainPrice = isMainPriceRequest ? deferredNextMainPriceResponse : null;
            const provisionalMaxComparisonRange = requests.find((request) => request.asset_id === readyPeer.id)?.date_range;
            const provisionalMaxPriceComparison =
                deferredProvisionalMaxPriceComparisonResponse &&
                requestedDeferredWindow === undefined &&
                requests.length === comparisonPeerIds.length &&
                typeof provisionalMaxComparisonRange?.end === 'string' &&
                matchesPriceComparisonRequest(
                    requests,
                    comparisonPeerIds,
                    {
                        start: '2000-01-01',
                        end: provisionalMaxComparisonRange.end,
                    },
                    asset.currency,
                )
                    ? deferredProvisionalMaxPriceComparisonResponse
                    : null;
            const deferredPriceComparison =
                requestedDeferredWindow === undefined &&
                deferredNextPriceComparisonResponse &&
                (matchesPriceComparisonRequest(requests, comparisonPeerIds, undefined, asset.currency) || matchesPriceComparisonRequest(requests, replacementPeerIds, undefined, asset.currency) || matchesPriceComparisonRequest(requests, sharedRoutePeerIds, undefined, 'GBP'))
                    ? deferredNextPriceComparisonResponse
                    : null;
            const stalePriceComparisonCandidate = priceComparisonRaceActive ? deferredStalePriceComparisonResponse : null;
            const isStalePriceComparison = stalePriceComparisonCandidate !== null && matchesPriceComparisonRequest(requests, comparisonPeerIds, stalePriceComparisonCandidate.range, asset.currency);
            const isSuccessorPriceComparison = priceComparisonRaceActive && !priceComparisonRaceSuccessorServed && matchesPriceComparisonRequest(requests, comparisonPeerIds, ninetyDayRange, asset.currency);
            const isCorrectedPriceComparison = !isStalePriceComparison && priceComparisonSyncSucceeded && matchesPriceComparisonRequest(requests, comparisonPeerIds, undefined, asset.currency);
            const priceComparisonRaceOutcome = isStalePriceComparison ? 'stale' : isSuccessorPriceComparison ? 'successor' : isCorrectedPriceComparison ? 'corrected' : null;
            const pendingMaxStandaloneRange = pendingAcceptedCurrentMaxStandaloneFxSyncRange;
            const acceptedCurrentMaxStandaloneFxSyncRange =
                pendingMaxStandaloneRange !== null && priceComparisonSyncSucceeded && priceComparisonRaceOutcome !== 'stale' && priceComparisonRaceOutcome !== 'successor' && matchesPriceComparisonRequest(requests, comparisonPeerIds, pendingMaxStandaloneRange, asset.currency)
                    ? pendingMaxStandaloneRange
                    : null;
            const acceptedCurrentMaxStandaloneEventDate = acceptedCurrentMaxStandaloneFxSyncRange === null ? null : (successorReadyEvents.find(({date}) => date >= acceptedCurrentMaxStandaloneFxSyncRange.start && date <= acceptedCurrentMaxStandaloneFxSyncRange.end)?.date ?? null);
            if (acceptedCurrentMaxStandaloneFxSyncRange !== null && acceptedCurrentMaxStandaloneEventDate === null) {
                throw new Error(`Accepted current MAX standalone FX-sync range ${acceptedCurrentMaxStandaloneFxSyncRange.start}..${acceptedCurrentMaxStandaloneFxSyncRange.end} contains no ready-peer event fixture`);
            }
            const acceptedCurrentMaxStandaloneMiddleDate =
                acceptedCurrentMaxStandaloneFxSyncRange !== null && acceptedCurrentMaxStandaloneEventDate !== null
                    ? acceptedCurrentMaxStandaloneEventDate === acceptedCurrentMaxStandaloneFxSyncRange.start || acceptedCurrentMaxStandaloneEventDate === acceptedCurrentMaxStandaloneFxSyncRange.end
                        ? addDays(acceptedCurrentMaxStandaloneFxSyncRange.start, 1)
                        : acceptedCurrentMaxStandaloneEventDate
                    : null;
            const stalePriceComparisonGate = isStalePriceComparison ? stalePriceComparisonCandidate : null;
            if (deferredPriceOnly) {
                deferredPriceOnlyResponse = null;
            }
            if (deferredMainPrice) {
                deferredNextMainPriceResponse = null;
            }
            if (provisionalMaxPriceComparison) {
                deferredProvisionalMaxPriceComparisonResponse = null;
            }
            if (deferredPriceComparison) {
                deferredNextPriceComparisonResponse = null;
            }
            if (stalePriceComparisonGate) {
                deferredStalePriceComparisonResponse = null;
            }
            if (acceptedCurrentMaxStandaloneFxSyncRange) {
                pendingAcceptedCurrentMaxStandaloneFxSyncRange = null;
            }
            if (priceComparisonRaceOutcome === 'successor') {
                priceComparisonRaceSuccessorServed = true;
            }
            if (isCorrectedPriceComparison) {
                correctedPriceComparisonResponseCount += 1;
            }
            if (deferred && deferredWindow !== undefined) {
                deferredCalendarResponses.delete(deferredWindow);
                await deferred.wait;
            }
            if (deferredPriceOnly) {
                await deferredPriceOnly.wait;
            }
            if (deferredMainPrice) {
                await deferredMainPrice.wait;
            }
            if (provisionalMaxPriceComparison) {
                await provisionalMaxPriceComparison.wait;
                await route.fulfill({
                    status: 503,
                    json: {detail: 'synthetic-provisional-max-comparison-rejection'},
                });
                return;
            }
            if (deferredPriceComparison) {
                await deferredPriceComparison.wait;
            }
            if (stalePriceComparisonGate) {
                await stalePriceComparisonGate.wait;
            }
            if (deferred?.outcome === 'i60h-query-rejected') {
                await route.fulfill({
                    status: 503,
                    json: {detail: 'synthetic-i60h-calendar-query-rejection'},
                });
                return;
            }
            const items = requests
                .map((request) => {
                    const responseAssetId = request.asset_id ?? assetId;
                    const calendarSignal = request.signals?.find((signal) => signal.instance_id === calendarInstanceId && signal.signal_code === calendarSignalCode);
                    const backendSignal = request.signals?.find((signal) => signal.signal_code === backendSignalCode);
                    const requestedWindow = calendarSignal?.params?.window_days;
                    if (calendarSignal && !isCalendarWindow(requestedWindow)) {
                        throw new Error(`Unexpected calendar window: ${String(requestedWindow)}`);
                    }
                    const isStaleForcedRefresh = responseAssetId === assetId && deferredWindow === 90 && requestedWindow === 90;
                    const isDeferredEmptyMainRefresh = responseAssetId === assetId && deferredMainPrice?.empty === true;
                    const staleSyncChartPayload = requestedWindow === deferredWindow && deferred?.outcome === 'stale-sync';
                    const isI60GSelectedRange = requestedWindow === 7 && i60gContractRanges.some((range) => request.date_range?.start === range.start && request.date_range?.end === range.end);
                    let signalResults: unknown[] = [];
                    if (calendarSignal && isCalendarWindow(requestedWindow)) {
                        if (deferred?.outcome === 'i60h-peer-unavailable-contract' && responseAssetId === readyPeer.id) {
                            signalResults = [buildUnavailableCalendarResult(requestedWindow)];
                        } else if (deferred?.outcome === 'i60h-peer-unavailable-contract' && responseAssetId === partialPeer.id) {
                            signalResults = [buildMalformedUnavailableCalendarResult(requestedWindow)];
                        } else if (isI60GSelectedRange && deferred?.outcome === 'i60g-rejected') {
                            signalResults = responseAssetId === assetId ? [buildFailedCalendarResult(requestedWindow, request.date_range)] : [buildUnavailableCalendarResult(requestedWindow)];
                        } else if (isI60GSelectedRange && deferred?.outcome === 'i60g-primary-unavailable' && responseAssetId === assetId) {
                            signalResults = [buildI60GCalendarResult(unavailablePeer.id, request.date_range)];
                        } else if (isI60GSelectedRange && deferred?.outcome === 'i60g-primary-failed' && responseAssetId === assetId) {
                            signalResults = [buildFailedCalendarResult(requestedWindow, request.date_range)];
                        } else if (isI60GSelectedRange && responseAssetId === invalidCalendarPeer.id) {
                            signalResults = [buildSchemaValidCalendarInvalidResult(requestedWindow, request.date_range)];
                        } else if (isI60GSelectedRange) {
                            signalResults = [buildI60GCalendarResult(responseAssetId, request.date_range, deferred?.outcome === 'i60g-stale')];
                        } else if (responseAssetId === readyPeer.id && calendarConversionGapErrors !== null) {
                            signalResults = [buildFxConversionGapCalendarResult(requestedWindow)];
                        } else if (responseAssetId === unavailablePeer.id) {
                            signalResults = [buildUnavailableCalendarResult(requestedWindow)];
                        } else if (responseAssetId === errorPeer.id) {
                            signalResults = [buildFailedCalendarResult(requestedWindow, request.date_range)];
                        } else if (responseAssetId === invalidCalendarPeer.id) {
                            signalResults = [buildSchemaValidCalendarInvalidResult(requestedWindow, request.date_range)];
                        } else {
                            const status = responseAssetId === partialPeer.id || (responseAssetId === assetId && requestedWindow === deferredWindow && deferred?.outcome === 'partial') ? 'partial' : 'ok';
                            signalResults = [buildCalendarResult(requestedWindow, status, responseAssetId, request.date_range)];
                        }
                    } else if (backendSignal && responseAssetId === assetId) {
                        signalResults = [buildBackendSignalResult(backendSignal, request.date_range)];
                    }
                    const rangeEnd = request.date_range?.end;
                    const responsePricePoints =
                        responseAssetId === assetId && isI60GSelectedRange
                            ? i60gPricePoints.filter((point) => point.date >= (request.date_range?.start ?? i60gRange.start) && point.date <= (request.date_range?.end ?? i60gRange.end))
                            : responseAssetId === assetId && request.target_currency === 'GBP' && sharedRouteMainSnapshot !== null
                              ? sharedRouteMainSnapshot === 'initial'
                                  ? sharedRouteInitialMainPricePoints
                                  : sharedRouteRefreshedMainPricePoints
                              : syntheticMaxResolutionSpanDays !== null && rangeEnd
                                ? [
                                      {...pricePoints[0], date: subtractDays(rangeEnd, syntheticMaxResolutionSpanDays)},
                                      {...pricePoints[1], date: subtractDays(rangeEnd, 1)},
                                      {...pricePoints[2], date: rangeEnd},
                                  ]
                                : pricePoints;
                    const comparisonPeer = availableComparisonPeers.find((peer) => peer.id === responseAssetId);
                    const comparisonFxSlug = comparisonPeer ? [asset.currency, comparisonPeer.currency].sort().join('-') : null;
                    const configuredPeerConversionMissing = !calendarSignal && comparisonPeer !== undefined && comparisonFxSlug !== null && missingFxConversionSlugs.has(comparisonFxSlug);
                    const carriesCurrentPriceComparison = priceComparisonRaceOutcome === 'successor' || priceComparisonRaceOutcome === 'corrected';
                    const currentComparisonPricePoints = syntheticMaxResolutionSpanDays === null ? successorPriceComparisonPoints : responsePricePoints;
                    let racePricePoints = responsePricePoints;
                    if (!calendarSignal && responseAssetId === readyPeer.id && pageSyncComparisonSnapshot !== null) {
                        racePricePoints = pageSyncComparisonSnapshot === 'pre-sync' ? pageSyncPrePriceComparisonPoints : pageSyncPostPriceComparisonPoints;
                    } else if (priceComparisonRaceOutcome === 'stale' && responseAssetId === readyPeer.id) {
                        racePricePoints = staleReadyPriceComparisonPoints;
                    } else if (priceComparisonRaceOutcome === 'stale' && responseAssetId === partialPeer.id) {
                        racePricePoints = stalePriceComparisonPoints;
                    } else if (priceComparisonRaceOutcome === 'successor' && responseAssetId === readyPeer.id) {
                        racePricePoints = successorReadyPriceComparisonPoints;
                    } else if (configuredPeerConversionMissing) {
                        racePricePoints = responsePricePoints.map((point) => ({...point, currency: comparisonPeer?.currency ?? asset.currency}));
                    } else if (forceReadyPeerConversionFailure && !calendarSignal && responseAssetId === readyPeer.id) {
                        racePricePoints = successorReadyPriceComparisonPoints;
                    } else if (carriesCurrentPriceComparison) {
                        racePricePoints = currentComparisonPricePoints;
                    }
                    const carriesRestoredAcceptedPageSyncSnapshot =
                        restoringAcceptedPageSyncSnapshot &&
                        !calendarSignal &&
                        request.include_events === true &&
                        request.include_price !== false &&
                        comparisonPeer !== undefined &&
                        request.target_currency === asset.currency &&
                        request.date_range?.start === ninetyDayRange.start &&
                        request.date_range.end === ninetyDayRange.end &&
                        pageSyncComparisonSnapshot === null &&
                        priceComparisonRaceOutcome === null &&
                        !forceReadyPeerConversionFailure &&
                        !configuredPeerConversionMissing &&
                        racePricePoints.length > 0;
                    const carriesAcceptedCurrentMaxStandaloneFxSyncSuccessor =
                        acceptedCurrentMaxStandaloneFxSyncRange !== null &&
                        acceptedCurrentMaxStandaloneMiddleDate !== null &&
                        !calendarSignal &&
                        request.include_events === true &&
                        request.include_price !== false &&
                        comparisonPeer !== undefined &&
                        request.target_currency === asset.currency &&
                        request.date_range?.start === acceptedCurrentMaxStandaloneFxSyncRange.start &&
                        request.date_range.end === acceptedCurrentMaxStandaloneFxSyncRange.end &&
                        pageSyncComparisonSnapshot === null &&
                        !forceReadyPeerConversionFailure &&
                        !configuredPeerConversionMissing;
                    if (carriesRestoredAcceptedPageSyncSnapshot) {
                        racePricePoints = successorPriceComparisonPoints;
                    } else if (carriesAcceptedCurrentMaxStandaloneFxSyncSuccessor && acceptedCurrentMaxStandaloneFxSyncRange && acceptedCurrentMaxStandaloneMiddleDate) {
                        racePricePoints = [
                            {...pricePoints[0], date: acceptedCurrentMaxStandaloneFxSyncRange.start},
                            {...pricePoints[1], date: acceptedCurrentMaxStandaloneMiddleDate},
                            {...pricePoints[2], date: acceptedCurrentMaxStandaloneFxSyncRange.end},
                        ];
                    }

                    let responseEvents: unknown[] = [];
                    if (staleSyncChartPayload && responseAssetId === partialPeer.id) {
                        responseEvents = stalePartialEvents;
                    } else if (!staleSyncChartPayload && calendarSignal && responseAssetId === readyPeer.id) {
                        responseEvents = successorReadyEvents;
                    } else if (!staleSyncChartPayload && (carriesCurrentPriceComparison || carriesRestoredAcceptedPageSyncSnapshot || carriesAcceptedCurrentMaxStandaloneFxSyncSuccessor) && responseAssetId === readyPeer.id) {
                        responseEvents =
                            carriesAcceptedCurrentMaxStandaloneFxSyncSuccessor && acceptedCurrentMaxStandaloneFxSyncRange && acceptedCurrentMaxStandaloneMiddleDate
                                ? successorReadyEvents.map((event, index) => ({
                                      ...event,
                                      date: index === 0 ? acceptedCurrentMaxStandaloneFxSyncRange.start : acceptedCurrentMaxStandaloneMiddleDate,
                                  }))
                                : successorReadyEvents;
                    } else if (!staleSyncChartPayload && priceComparisonRaceOutcome === 'stale' && responseAssetId === partialPeer.id) {
                        responseEvents = stalePartialEvents;
                    }
                    responseEvents = withCurrentEventFxAvailability(responseEvents);

                    let responseErrors: string[] = [];
                    if (configuredPeerConversionMissing) {
                        responseErrors = [`synthetic-price-conversion-failure-${comparisonFxSlug}`];
                    } else if (calendarSignal && responseAssetId === readyPeer.id && calendarConversionGapErrors !== null) {
                        responseErrors = [...calendarConversionGapErrors];
                    } else if (priceComparisonRaceOutcome === 'stale' && responseAssetId === partialPeer.id) {
                        responseErrors = [stalePriceComparisonError];
                    } else if (
                        !carriesRestoredAcceptedPageSyncSnapshot &&
                        !carriesAcceptedCurrentMaxStandaloneFxSyncSuccessor &&
                        !calendarSignal &&
                        responseAssetId === readyPeer.id &&
                        pageSyncComparisonSnapshot === null &&
                        (forceReadyPeerConversionFailure || priceComparisonRaceOutcome !== 'corrected')
                    ) {
                        responseErrors = [readyPeerConversionError];
                    }
                    return {
                        asset_id: responseAssetId,
                        // The stale forced refresh deliberately carries no prices:
                        // old code applied this payload and unmounted the active chart
                        // while the newer 365-day request was still pending.
                        prices: request.include_price === false || isStaleForcedRefresh || isDeferredEmptyMainRefresh ? [] : racePricePoints,
                        events: responseEvents,
                        errors: responseErrors,
                        signals: signalResults,
                    };
                })
                // Response order is deliberately unrelated to request order. Every
                // consumer must join by asset_id, never by array position.
                .reverse();
            const responseItems = deferred?.outcome === 'i60h-main-omitted' ? items.filter((item) => item.asset_id !== assetId) : deferred?.outcome === 'i60h-ready-peer-omitted' ? items.filter((item) => item.asset_id !== readyPeer.id) : items;
            await route.fulfill({json: {items: responseItems}});
        });
        await page.route('**/api/v1/assets/prices/current', async (route) => {
            await route.fulfill({json: {results: [], success_count: 0, errors: []}});
        });

        const initialComparisonGate = deferNextPriceComparisonResponse();
        const initialComparisonRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/query' && matchesPriceComparisonRequest(request.postDataJSON(), comparisonPeerIds, undefined, asset.currency), {
            timeout: 10_000,
        });
        const initialComparisonResponsePromise = waitForPriceComparisonResponse();
        await goToAssetDetailPage(page, String(assetId));
        const pageRoot = page.getByTestId('asset-detail-page');
        const controls = page.getByTestId('asset-detail-controls');
        const filterBar = controls.getByTestId('asset-detail-filter-bar');
        const chart = page.getByTestId('asset-detail-chart');
        const pricePrimary = chart.getByTestId('asset-chart-primary-price');
        const calendarPrimary = chart.getByTestId('asset-chart-primary-calendar-return');
        const pricePrimaryIcon = pricePrimary.getByTestId('asset-chart-primary-price-icon');
        const calendarPrimaryIcon = calendarPrimary.getByTestId('asset-chart-primary-calendar-return-icon');
        const editorButton = page.getByTestId('asset-detail-editdata-btn');
        const editorPanel = page.getByTestId('asset-detail-editor-panel');
        const editorSaveButton = page.getByTestId('asset-editor-save-btn');
        const measuresSection = page.getByTestId('asset-detail-measures-section');
        const measuresToggle = page.getByTestId('asset-detail-measures-toggle');
        const measuresPanel = page.getByTestId('asset-detail-measures-panel');
        const calendarMeasuresPanel = page.getByTestId('asset-detail-calendar-measures-panel');
        const refreshButton = page.getByTestId('asset-detail-refresh-btn');
        const aestheticsToggle = page.getByTestId('asset-detail-aesthetics-toggle');
        const aestheticsPanel = page.getByTestId('asset-detail-aesthetics-panel');
        const dateRangePicker = filterBar.getByTestId('date-range-picker-root');
        const dateRangeStartInput = dateRangePicker.getByTestId('date-range-input-start');
        const dateRangeEndInput = dateRangePicker.getByTestId('date-range-input-end');
        const readChartEventMarkerAssetLabels = async (): Promise<string[]> =>
            chart.evaluate(
                (root, knownAssetLabels) => {
                    type ChartHost = HTMLElement & {
                        __lfChart?: {
                            getOption: () => {series?: unknown};
                        };
                    };
                    const candidates = [root, ...root.querySelectorAll<HTMLElement>('*')];
                    const host = candidates.find((candidate) => typeof (candidate as ChartHost).__lfChart?.getOption === 'function') as ChartHost | undefined;
                    const series = host?.__lfChart?.getOption().series;
                    if (!Array.isArray(series)) return [];

                    const labels = new Set<string>();
                    for (const rawSeries of series) {
                        if (!rawSeries || typeof rawSeries !== 'object') continue;
                        const eventSeries = rawSeries as {type?: unknown; name?: unknown; data?: unknown};
                        if (eventSeries.type !== 'scatter') continue;
                        if (typeof eventSeries.name === 'string') {
                            for (const assetLabel of knownAssetLabels) {
                                if (eventSeries.name.startsWith(`Events: ${assetLabel} `)) labels.add(assetLabel);
                            }
                        }
                        if (!Array.isArray(eventSeries.data)) continue;
                        for (const rawPoint of eventSeries.data) {
                            if (!rawPoint || typeof rawPoint !== 'object') continue;
                            const point = rawPoint as {marker?: unknown; markers?: unknown};
                            const markers = Array.isArray(point.markers) ? point.markers : point.marker ? [point.marker] : [];
                            for (const rawMarker of markers) {
                                if (!rawMarker || typeof rawMarker !== 'object') continue;
                                const assetLabel = (rawMarker as {assetLabel?: unknown}).assetLabel;
                                if (typeof assetLabel === 'string') labels.add(assetLabel);
                            }
                        }
                    }
                    return [...labels].sort();
                },
                [readyPeer.display_name, partialPeer.display_name, replacementPeer.display_name],
            );
        const readChartComparisonLineLabels = async (): Promise<string[]> =>
            chart.evaluate(
                (root, knownAssetLabels) => {
                    type ChartHost = HTMLElement & {
                        __lfChart?: {
                            getOption: () => {series?: unknown};
                        };
                    };
                    const candidates = [root, ...root.querySelectorAll<HTMLElement>('*')];
                    const host = candidates.find((candidate) => typeof (candidate as ChartHost).__lfChart?.getOption === 'function') as ChartHost | undefined;
                    const series = host?.__lfChart?.getOption().series;
                    if (!Array.isArray(series)) return [];
                    return [
                        ...new Set(
                            series.flatMap((rawSeries) => {
                                if (!rawSeries || typeof rawSeries !== 'object') return [];
                                const candidate = rawSeries as {type?: unknown; name?: unknown; data?: unknown[]};
                                if (candidate.type !== 'line' || typeof candidate.name !== 'string' || !knownAssetLabels.includes(candidate.name)) return [];
                                return Array.isArray(candidate.data) && candidate.data.some((value) => value !== null && value !== undefined) ? [candidate.name] : [];
                            }),
                        ),
                    ].sort();
                },
                comparisonPeers.map((peer) => peer.display_name),
            );
        const readChartLineValues = async (seriesLabel: string): Promise<number[]> =>
            chart.evaluate((root, label) => {
                type ChartHost = HTMLElement & {
                    __lfChart?: {
                        getOption: () => {series?: unknown};
                    };
                };
                const candidates = [root, ...root.querySelectorAll<HTMLElement>('*')];
                const host = candidates.find((candidate) => typeof (candidate as ChartHost).__lfChart?.getOption === 'function') as ChartHost | undefined;
                const series = host?.__lfChart?.getOption().series;
                if (!Array.isArray(series)) return [];
                const match = series.find((rawSeries) => rawSeries !== null && typeof rawSeries === 'object' && (rawSeries as {type?: unknown}).type === 'line' && (rawSeries as {name?: unknown}).name === label) as {data?: unknown[]} | undefined;
                if (!Array.isArray(match?.data)) return [];
                return match.data.flatMap((rawValue) => {
                    const value = Array.isArray(rawValue) ? rawValue.at(-1) : rawValue !== null && typeof rawValue === 'object' && 'value' in rawValue ? (rawValue as {value?: unknown}).value : rawValue;
                    const numeric = Number(value);
                    return Number.isFinite(numeric) ? [numeric] : [];
                });
            }, seriesLabel);
        const readI60GCalendarChart = async () =>
            chart.evaluate(
                (root, peerLabels) => {
                    type ChartOption = {
                        xAxis?: unknown;
                        series?: unknown;
                    };
                    type ChartHost = HTMLElement & {
                        __lfChart?: {
                            getOption: () => ChartOption;
                        };
                    };
                    type LineSeries = {
                        type?: unknown;
                        name?: unknown;
                        data?: unknown;
                    };
                    const candidates = [root, ...root.querySelectorAll<HTMLElement>('*')];
                    const host = candidates.find((candidate) => typeof (candidate as ChartHost).__lfChart?.getOption === 'function') as ChartHost | undefined;
                    const option = host?.__lfChart?.getOption();
                    const rawAxes = Array.isArray(option?.xAxis) ? option.xAxis : option?.xAxis ? [option.xAxis] : [];
                    const categoryAxis = rawAxes.find((candidate) => candidate !== null && typeof candidate === 'object' && Array.isArray((candidate as {data?: unknown}).data)) as {data: unknown[]} | undefined;
                    const dates = categoryAxis?.data.flatMap((value) => (typeof value === 'string' ? [value] : [])) ?? [];
                    const lineSeries = Array.isArray(option?.series) ? option.series.filter((candidate): candidate is LineSeries => candidate !== null && typeof candidate === 'object' && (candidate as LineSeries).type === 'line' && typeof (candidate as LineSeries).name === 'string') : [];
                    const presentPeerLabels = [...new Set(lineSeries.flatMap((series) => (peerLabels.includes(series.name as string) ? [series.name as string] : [])))].sort();
                    const mainLabels = [
                        ...new Set(
                            lineSeries.flatMap((series) => {
                                const name = series.name as string;
                                return name !== '__baseline__' && !name.startsWith('Events: ') && !peerLabels.includes(name) ? [name] : [];
                            }),
                        ),
                    ];
                    if (mainLabels.length !== 1) {
                        throw new Error(`Expected one Calendar primary line label, received ${JSON.stringify(mainLabels)}`);
                    }
                    const readAlignedValues = (label: string): Array<number | null> => {
                        const values: Array<number | null> = dates.map(() => null);
                        for (const series of lineSeries.filter((candidate) => candidate.name === label)) {
                            if (!Array.isArray(series.data)) continue;
                            series.data.forEach((rawValue, index) => {
                                const tupleValue = Array.isArray(rawValue) ? rawValue.at(-1) : rawValue;
                                const value = tupleValue !== null && typeof tupleValue === 'object' && 'value' in tupleValue ? (tupleValue as {value?: unknown}).value : tupleValue;
                                const numeric = Number(value);
                                if (value !== null && value !== undefined && Number.isFinite(numeric)) values[index] = numeric;
                            });
                        }
                        return values;
                    };
                    return {
                        dates,
                        main: readAlignedValues(mainLabels.at(0)!),
                        peers: Object.fromEntries(peerLabels.map((label) => [label, readAlignedValues(label)])),
                        presentPeerLabels,
                    };
                },
                comparisonPeers.map((peer) => peer.display_name),
            );

        // A comparison Asset sync starts while the page's first comparison
        // request is still in flight. If neither leg is accepted, the sync has
        // changed no data and therefore must not invalidate that original
        // request. Releasing it must populate the signal without another user
        // action or successor request.
        const initialComparisonRequest = await initialComparisonRequestPromise;
        const initialComparisonQueries = parseQueries(initialComparisonRequest.postDataJSON());
        const initialReadyPeerQuery = initialComparisonQueries.find((query) => query.asset_id === readyPeer.id);
        expect(initialReadyPeerQuery).toMatchObject({
            asset_id: readyPeer.id,
            include_events: true,
            target_currency: asset.currency,
            date_range: {
                start: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
                end: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
            },
        });
        const initialComparisonRange = initialReadyPeerQuery?.date_range;
        if (typeof initialComparisonRange?.start !== 'string' || typeof initialComparisonRange.end !== 'string') {
            throw new Error('Initial comparison request did not carry one concrete date range');
        }
        const capturedInitialComparisonRange = {
            start: initialComparisonRange.start,
            end: initialComparisonRange.end,
        };
        const capturedInitialPriceSyncRange = {
            start: subtractDays(capturedInitialComparisonRange.start, 7),
            end: capturedInitialComparisonRange.end,
        };
        assertPriceComparisonRequest(initialComparisonRequest.postDataJSON(), comparisonPeerIds, capturedInitialComparisonRange, asset.currency);

        const firstLoadSignalsToggle = page.getByTestId('asset-detail-signals-toggle');
        const firstLoadSignalsPanel = page.getByTestId('asset-detail-signals-panel');
        await firstLoadSignalsToggle.click();
        await expect(firstLoadSignalsPanel).toBeVisible();
        const firstLoadReadySignalCard = firstLoadSignalsPanel.getByTestId(`signal-card-calendar-peer-${readyPeer.id}`);
        const firstLoadReadySync = firstLoadReadySignalCard.getByTestId(`signal-sync-asset-calendar-peer-${readyPeer.id}`);
        await expect(firstLoadReadySignalCard).toBeVisible();
        await expect(firstLoadReadySync).toBeEnabled();

        nextAssetSyncStatus = 'failed';
        nextFxSyncStatus = 'failed';
        const firstLoadPriceQueriesBeforeSync = priceQueryRequestCount;
        const firstLoadFxConversionsBeforeSync = fxConvertRequestCount;
        const firstLoadAssetSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const firstLoadAssetSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const firstLoadFxSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const firstLoadFxSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        await firstLoadReadySync.click();

        const firstLoadAssetSyncRequest = await firstLoadAssetSyncRequestPromise;
        assertAssetSyncRequest(firstLoadAssetSyncRequest.postDataJSON(), readyPeer.id, capturedInitialPriceSyncRange);
        const firstLoadFxSyncRequest = await firstLoadFxSyncRequestPromise;
        assertFxSyncRequest(firstLoadFxSyncRequest.postDataJSON(), [readyPeerFxSlug], capturedInitialPriceSyncRange);
        const firstLoadAssetSyncResponse = await firstLoadAssetSyncResponsePromise;
        expect(firstLoadAssetSyncResponse.ok()).toBe(true);
        expect(await firstLoadAssetSyncResponse.finished()).toBeNull();
        expect(await firstLoadAssetSyncResponse.json()).toMatchObject({
            success_count: 0,
            results: [{asset_id: readyPeer.id, status: 'failed'}],
        });
        const firstLoadFxSyncResponse = await firstLoadFxSyncResponsePromise;
        expect(firstLoadFxSyncResponse.ok()).toBe(true);
        expect(await firstLoadFxSyncResponse.finished()).toBeNull();
        expect(await firstLoadFxSyncResponse.json()).toMatchObject({
            success_count: 0,
            results: [{pair: readyPeerFxSlug, status: 'failed'}],
        });
        await expect(firstLoadReadySync).toBeEnabled();
        expect(priceQueryRequestCount).toBe(firstLoadPriceQueriesBeforeSync);
        expect(fxConvertRequestCount).toBe(firstLoadFxConversionsBeforeSync);
        expect(fxRouteMutationRequestCount).toBe(0);
        await expect(page.getByTestId('toast-error')).toHaveCount(2);

        initialComparisonGate.release();
        const initialComparisonResponse = await initialComparisonResponsePromise;
        expect(initialComparisonResponse.ok()).toBe(true);
        expect(await initialComparisonResponse.finished()).toBeNull();
        assertPriceComparisonRequest(initialComparisonResponse.request().postDataJSON(), comparisonPeerIds, capturedInitialComparisonRange, asset.currency);
        await expect(firstLoadReadySignalCard.getByRole('button', {name: '📈3', exact: true})).toBeVisible();
        await expect(firstLoadReadySignalCard.getByTestId('signal-loading')).toHaveCount(0);
        expect(priceQueryRequestCount).toBe(firstLoadPriceQueriesBeforeSync);
        await firstLoadSignalsToggle.click();
        await expect(firstLoadSignalsPanel).toBeHidden();

        const commitSyntheticRange = async (range: SyntheticRange, waitForComparison: boolean) => {
            await dateRangeStartInput.fill(range.start);
            await expect(dateRangeStartInput).toHaveValue(range.start);
            await dateRangeEndInput.fill(range.end);
            await expect(dateRangeEndInput).toHaveValue(range.end);

            const mainResponsePromise = waitForMainRangeResponse(range);
            const comparisonResponsePromise = waitForComparison ? waitForPriceComparisonResponse() : null;
            await dateRangeEndInput.press('Enter');

            const mainResponse = await mainResponsePromise;
            expect(mainResponse.ok()).toBe(true);
            expect(await mainResponse.finished()).toBeNull();
            assertMainDateRange(mainResponse.request().postDataJSON(), range);
            if (comparisonResponsePromise) {
                const comparisonResponse = await comparisonResponsePromise;
                expect(comparisonResponse.ok()).toBe(true);
                expect(await comparisonResponse.finished()).toBeNull();
            }

            await expect(dateRangePicker).toHaveAttribute('data-open', 'false');
            await expect(dateRangeStartInput).toHaveValue(range.start);
            await expect(dateRangeEndInput).toHaveValue(range.end);
            await expect(chart).toHaveAttribute('data-calendar-range-days', String(range.spanDays));
            return mainResponse.request();
        };

        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(pricePrimary).toHaveAttribute('aria-pressed', 'true');
        await expect(calendarPrimary).toHaveAttribute('aria-pressed', 'false');
        await expect(pricePrimaryIcon).toBeVisible();
        await expect(calendarPrimaryIcon).toBeVisible();
        await expect(dateRangePicker).toBeVisible();
        await expectAssetDetailChartCanvas(page);

        const longRangeCalendarRequestCount = calendarRequestCount;
        const longRangeRequest = await commitSyntheticRange(longRange, true);
        expect(findCalendarSignal(longRangeRequest.postDataJSON())).toBeUndefined();
        expect(calendarRequestCount).toBe(longRangeCalendarRequestCount);
        await expect(calendarPrimary).toBeEnabled();

        await editorButton.click();
        await expect(editorPanel).toBeVisible();
        await expect(editorSaveButton).toBeVisible();

        const editorCalendarResponse = waitForCalendarResponse(30);
        await calendarPrimary.click();
        await editorCalendarResponse;
        await expect(editorPanel).toHaveAttribute('aria-hidden', 'true');
        await expect(editorPanel).toHaveAttribute('inert', '');
        await expect(editorPanel).toBeHidden();
        await expect(editorSaveButton).toHaveAttribute('data-testid', 'asset-editor-save-btn');
        await expect(editorSaveButton).toBeHidden();

        await pricePrimary.click();
        await expect(editorPanel).toBeVisible();
        await expect(editorSaveButton).toBeVisible();
        await editorButton.click();
        await expect(editorPanel).toHaveCount(0);

        await measuresToggle.click();
        await expect(measuresSection).toBeVisible();
        await expect(measuresPanel).toBeVisible();

        const measuresCalendarResponse = waitForCalendarResponse(30);
        await calendarPrimary.click();
        await measuresCalendarResponse;
        await expect(measuresSection).toBeVisible();
        await expect(measuresSection).toHaveAttribute('data-mode', 'calendar-return');
        await expect(measuresPanel).toHaveAttribute('data-testid', 'asset-detail-measures-panel');
        await expect(measuresPanel).toHaveAttribute('aria-hidden', 'true');
        await expect(measuresPanel).toHaveAttribute('inert', '');
        await expect(measuresPanel).toBeHidden();
        await expect(calendarMeasuresPanel).toHaveAttribute('aria-hidden', 'true');
        await expect(calendarMeasuresPanel).toHaveAttribute('inert', '');
        await expect(calendarMeasuresPanel).toBeHidden();

        await pricePrimary.click();
        await expect(measuresSection).toBeVisible();
        await expect(measuresSection).toHaveAttribute('data-mode', 'price');
        await expect(measuresPanel).toBeVisible();
        await expect(calendarMeasuresPanel).toBeHidden();

        await page.getByTestId('asset-detail-add-measure-btn').click();
        const expectedPriceMeasureRowIds = ['main', ...comparisonPeers.map((peer) => `sig-${peer.display_name}`)].sort();
        await expect.poll(async () => (await readMeasureRowIds(measuresPanel)).sort()).toEqual(expectedPriceMeasureRowIds);
        await expect(measuresPanel.getByTestId('dt-header-deltaPct')).toBeVisible();
        await expect(measuresPanel.getByTestId('dt-header-days')).toHaveCount(0);

        await chart.getByTestId('chart-view-absolute').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'absolute');
        await chart.getByTestId('chart-type-candlestick').click();
        await expect(chart.getByTestId('candlestick-chart')).toBeVisible();

        const defaultResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const defaultRequest = (await defaultResponsePromise).request();
        assertCalendarRequest(defaultRequest.postDataJSON(), 30);
        assertCalendarBulkRequest(defaultRequest.postDataJSON(), 30);

        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', '30');
        await expect(chart).toHaveAttribute('data-window-kind', 'preset');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(calendarPrimary).toHaveAttribute('aria-pressed', 'true');
        await expect(pricePrimary).toHaveAttribute('aria-pressed', 'false');
        await expect(chart).toHaveAttribute('data-calendar-comparison-ready', String(readyPeer.id));
        await expect(chart).toHaveAttribute('data-calendar-comparison-partial', String(partialPeer.id));
        await expect(chart).toHaveAttribute('data-calendar-comparison-unavailable', String(unavailablePeer.id));
        await expect(chart).toHaveAttribute('data-calendar-comparison-error', calendarErrorPeerIds);
        await expect(filterBar.getByTestId('date-range-picker-root')).toBeVisible();
        await expectAssetDetailChartCanvas(page);

        for (const preset of calendarPresets) {
            const button = chart.getByTestId(`asset-calendar-window-${preset.key}`);
            await expect(button).toBeVisible();
            await expect(button).toHaveAttribute('aria-pressed', preset.windowDays === 30 ? 'true' : 'false');
        }
        const customWindowButton = chart.getByTestId('asset-calendar-window-custom');
        await expect(customWindowButton).toBeVisible();
        await expect(customWindowButton).toHaveAttribute('data-active', 'false');
        await expect(chart.getByTestId('chart-view-mode-toggle')).toBeHidden();
        await expect(chart.getByTestId('chart-type-line')).toBeHidden();
        await expect(chart.getByTestId('chart-type-candlestick')).toBeHidden();
        await expect(chart.getByTestId('candlestick-chart')).toBeHidden();
        await expect(page.getByTestId('asset-detail-editdata-btn')).toBeHidden();

        const signalsPanel = page.getByTestId('asset-detail-signals-panel');
        await page.getByTestId('asset-detail-signals-toggle').click();
        await expect(signalsPanel).toBeVisible();
        const comparisonSelectButton = signalsPanel.getByTestId('signals-comparison-select-button');
        await expect(comparisonSelectButton).toBeVisible();
        await expect(signalsPanel.getByTestId('signals-indicator-select-button')).toHaveCount(0);
        await expect(signalsPanel.getByTestId('signals-benchmark-select-button')).toHaveCount(0);
        await comparisonSelectButton.click();
        await expect(signalsPanel.getByTestId('signal-tree-option-asset-comparison')).toBeVisible();
        await expect(signalsPanel.getByTestId('signal-tree-option-fx-pair')).toHaveCount(0);
        await comparisonSelectButton.press('Escape');
        await expect(comparisonSelectButton).toHaveAttribute('aria-expanded', 'false');

        const selectComparisonAsset = async (signalId: string, targetAssetId: number): Promise<void> => {
            const param = signalsPanel.getByTestId(`signal-param-${signalId}-assetId`);
            const selectTestId = `signal-param-${signalId}-assetId-select`;
            const trigger = param.getByTestId(`${selectTestId}-trigger`);
            await expect(param).toBeVisible();
            await expect(param.getByTestId(selectTestId)).toBeVisible();
            await expect(async () => {
                if ((await trigger.getAttribute('aria-expanded')) !== 'true') {
                    await trigger.press('ArrowDown');
                }
                expect(await trigger.getAttribute('aria-expanded')).toBe('true');
            }).toPass({timeout: 3_000});
            const option = page.getByTestId(`search-select-option-${targetAssetId}`);
            await expect(option).toBeVisible();
            await option.click();
            await expect(trigger).toHaveAttribute('aria-expanded', 'false');
        };
        const activateComparisonAssetSync = async (signalId: string): Promise<void> => {
            const selectTrigger = signalsPanel.getByTestId(`signal-param-${signalId}-assetId-select-trigger`);
            await expect(selectTrigger).toBeVisible();
            await selectTrigger.focus();
            await expect(selectTrigger).toBeFocused();
            await page.keyboard.press('Tab');
            await expect
                .poll(() =>
                    page.evaluate(() => {
                        const active = document.activeElement;
                        return active instanceof HTMLButtonElement ? active.disabled : null;
                    }),
                )
                .toBe(false);
            await page.keyboard.press('Enter');
        };
        const expectFocusedAssetSyncIdle = async (signalId: string): Promise<void> => {
            await expect(signalsPanel.getByTestId(`signal-sync-asset-${signalId}`)).toBeEnabled();
        };

        const readySignalId = `calendar-peer-${readyPeer.id}`;
        const readySignalCard = signalsPanel.getByTestId(`signal-card-${readySignalId}`);
        const readySignalStyle = readySignalCard.getByTestId(`signal-style-${readySignalId}`);
        const styleToggle = readySignalStyle.getByRole('button');
        const stylePopover = readySignalStyle.getByTestId('signal-style-popover');
        const readySignalParam = readySignalCard.getByTestId(`signal-param-${readySignalId}-assetId`);
        const readySignalRemove = readySignalCard.getByTestId(`signal-remove-${readySignalId}`);
        const partialSignalCard = signalsPanel.getByTestId(`signal-card-calendar-peer-${partialPeer.id}`);
        const unavailableSignalCard = signalsPanel.getByTestId(`signal-card-calendar-peer-${unavailablePeer.id}`);
        const failedSignalCard = signalsPanel.getByTestId(`signal-card-calendar-peer-${errorPeer.id}`);
        const errorSignalId = `calendar-peer-${errorPeer.id}`;
        const invalidCalendarSignalCard = signalsPanel.getByTestId(`signal-card-calendar-peer-${invalidCalendarPeer.id}`);
        await expect(readySignalCard).toBeVisible();
        await expect(readySignalCard).toHaveAttribute('data-signal-type', 'asset-comparison');
        await expect(readySignalStyle).toBeVisible();
        await expect(readySignalParam).toBeVisible();
        await expect(readySignalRemove).toBeVisible();
        await expect(partialSignalCard).toBeVisible();
        await expect(unavailableSignalCard).toBeVisible();
        await expect(failedSignalCard).toBeVisible();
        await expect(invalidCalendarSignalCard).toBeVisible();

        const expectCalendarPeerDiagnostics = async (): Promise<void> => {
            await expect(readySignalCard.getByTestId('signal-loading')).toHaveCount(0);
            await expect(readySignalCard.getByTestId('signal-issue')).toHaveCount(0);

            const partialIssue = partialSignalCard.getByTestId('signal-issue');
            await expect(partialIssue).toBeVisible();
            await expect(partialIssue).toHaveAttribute('data-problem-code', 'partial_input_coverage');
            await expect(partialIssue).toHaveAttribute('data-severity', 'warning');

            const unavailableIssue = unavailableSignalCard.getByTestId('signal-issue');
            await expect(unavailableIssue).toBeVisible();
            await expect(unavailableIssue).toHaveAttribute('data-problem-code', 'insufficient_history');
            await expect(unavailableIssue).toHaveAttribute('data-severity', 'error');

            const failedIssue = failedSignalCard.getByTestId('signal-issue');
            await expect(failedIssue).toBeVisible();
            await expect(failedIssue).toHaveAttribute('data-problem-code', 'calculation_failed');
            await expect(failedIssue).toHaveAttribute('data-severity', 'error');

            const invalidCalendarIssue = invalidCalendarSignalCard.getByTestId('signal-issue');
            await expect(invalidCalendarIssue).toBeVisible();
            await expect(invalidCalendarIssue).toHaveAttribute('data-problem-code', 'result_missing');
            await expect(invalidCalendarIssue).toHaveAttribute('data-severity', 'error');
        };
        await expectCalendarPeerDiagnostics();
        const requiredFxIssues = page.getByTestId(/^data-quality-issue-FX_PAIR_/);
        await expect(requiredFxIssues).toHaveCount(0);

        // A Calendar peer whose price conversion failed reaches the backend as
        // missing `close`, but the actionable cause is the exact FX error on
        // the response item. The page must publish that typed cause instead of
        // leaking the generic signal-input diagnosis. Ordering is authoritative:
        // a later event-scoped error must not mask this first price error.
        calendarConversionGapErrors = [readyPeerConversionError, readyPeerEventOnlyConversionError];
        const conversionGapCalendarRequestCount = calendarRequestCount;
        const conversionGapResponsePromise = waitForCalendarResponse(30);
        await refreshButton.click();
        const conversionGapResponse = await conversionGapResponsePromise;
        expect(conversionGapResponse.ok()).toBe(true);
        expect(await conversionGapResponse.finished()).toBeNull();
        assertCalendarBulkRequest(conversionGapResponse.request().postDataJSON(), 30);
        expect(calendarRequestCount).toBe(conversionGapCalendarRequestCount + 1);
        const conversionGapPayload = (await conversionGapResponse.json()) as {items?: Array<{asset_id?: number; errors?: unknown[]}>};
        expect(conversionGapPayload.items?.find((item) => item.asset_id === readyPeer.id)?.errors).toEqual([readyPeerConversionError, readyPeerEventOnlyConversionError]);

        const conversionGapIssue = readySignalCard.getByTestId('signal-issue');
        await expect(conversionGapIssue).toBeVisible();
        await expect(conversionGapIssue).toHaveAttribute('data-problem-code', 'fx_conversion_unavailable');
        await expect(conversionGapIssue).not.toHaveAttribute('data-problem-code', 'missing_input_fields');
        await expect(conversionGapIssue).toHaveAttribute('data-severity', 'error');
        const priceRouteIssues = page.getByTestId('data-quality-issue-FX_PAIR_NO_DATA');
        await expect(priceRouteIssues).toHaveCount(1);
        await expect(priceRouteIssues.filter({hasText: readyPeer.currency})).toHaveCount(1);
        await expect(priceRouteIssues.filter({hasText: readyPeerEventCurrency})).toHaveCount(0);
        await conversionGapIssue.click();
        await expect(page.getByTestId('tooltip-content')).toHaveText(readyPeerConversionError);
        await page.getByTestId('asset-detail-header').click();
        await expect(page.getByTestId('tooltip-content')).toHaveCount(0);

        // An event-only FX miss is not evidence that the peer's price series
        // failed conversion. Even with a later generic conversion error, the
        // first event-scoped error keeps the signal's backend diagnosis.
        exposeMissingComparisonEventRoutes = true;
        missingFxConversionSlugs.clear();
        missingFxConversionSlugs.add(readyPeerEventFxSlug);
        calendarConversionGapErrors = [readyPeerEventOnlyConversionError, readyPeerGenericConversionError];
        const eventOnlyGapCalendarRequestCount = calendarRequestCount;
        const eventOnlyGapResponsePromise = waitForCalendarResponse(30);
        await refreshButton.click();
        const eventOnlyGapResponse = await eventOnlyGapResponsePromise;
        expect(eventOnlyGapResponse.ok()).toBe(true);
        expect(await eventOnlyGapResponse.finished()).toBeNull();
        assertCalendarBulkRequest(eventOnlyGapResponse.request().postDataJSON(), 30);
        expect(calendarRequestCount).toBe(eventOnlyGapCalendarRequestCount + 1);
        const eventOnlyGapPayload = (await eventOnlyGapResponse.json()) as {items?: Array<{asset_id?: number; errors?: unknown[]}>};
        expect(eventOnlyGapPayload.items?.find((item) => item.asset_id === readyPeer.id)?.errors).toEqual([readyPeerEventOnlyConversionError, readyPeerGenericConversionError]);

        const eventOnlyGapIssue = readySignalCard.getByTestId('signal-issue');
        await expect(eventOnlyGapIssue).toBeVisible();
        await expect(eventOnlyGapIssue).toHaveAttribute('data-problem-code', 'missing_input_fields');
        await expect(eventOnlyGapIssue).not.toHaveAttribute('data-problem-code', 'fx_conversion_unavailable');
        const eventRouteIssues = page.getByTestId('data-quality-issue-FX_PAIR_NO_DATA');
        await expect(eventRouteIssues).toHaveCount(1);
        await expect(eventRouteIssues.filter({hasText: readyPeerEventCurrency})).toHaveCount(1);
        await expect(eventRouteIssues.filter({hasText: readyPeer.currency})).toHaveCount(0);

        exposeMissingComparisonEventRoutes = false;
        missingFxConversionSlugs.clear();
        calendarConversionGapErrors = null;
        const restoredCalendarDiagnosticsPromise = waitForCalendarResponse(30);
        await refreshButton.click();
        const restoredCalendarDiagnostics = await restoredCalendarDiagnosticsPromise;
        expect(restoredCalendarDiagnostics.ok()).toBe(true);
        expect(await restoredCalendarDiagnostics.finished()).toBeNull();
        assertCalendarBulkRequest(restoredCalendarDiagnostics.request().postDataJSON(), 30);
        await expectCalendarPeerDiagnostics();

        const expectI60GCalendarDiagnostics = async (): Promise<void> => {
            await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
            await expect(chart).toHaveAttribute('data-window-days', '7');
            await expect(chart).toHaveAttribute('data-series-state', 'partial');
            await expect(chart).toHaveAttribute('data-calendar-primary-problem-code', 'partial_undefined_metric');
            await expect(chart).toHaveAttribute('data-calendar-primary-problem-status', 'partial');
            const primaryProblem = chart.getByTestId('asset-calendar-primary-problem');
            await expect(primaryProblem).toBeVisible();
            await expect(primaryProblem).toHaveAttribute('data-problem-code', 'partial_undefined_metric');
            await expect(primaryProblem).toHaveAttribute('data-problem-status', 'partial');
            await expect(chart).toHaveAttribute('data-calendar-comparison-ready', '');
            await expect(chart).toHaveAttribute('data-calendar-comparison-partial', [readyPeer.id, partialPeer.id, errorPeer.id].sort((left, right) => left - right).join(','));
            await expect(chart).toHaveAttribute('data-calendar-comparison-unavailable', String(unavailablePeer.id));
            await expect(chart).toHaveAttribute('data-calendar-comparison-error', String(invalidCalendarPeer.id));

            const expectedProblems = new Map([
                [readySignalCard, 'partial_input_coverage'],
                [partialSignalCard, 'data_gap'],
                [failedSignalCard, 'incomplete_warmup'],
                [unavailableSignalCard, 'undefined_metric'],
                [invalidCalendarSignalCard, 'result_missing'],
            ]);
            for (const [card, code] of expectedProblems) {
                await expect(card).toHaveAttribute('data-signal-type', 'asset-comparison');
                const issue = card.getByTestId('signal-issue');
                await expect(issue).toBeVisible();
                await expect(issue).toHaveAttribute('data-problem-code', code);
                await expect(issue).toHaveAttribute('data-severity', code === 'undefined_metric' || code === 'result_missing' ? 'error' : 'warning');
            }
        };
        const i60gWindowResponsePromise = waitForCalendarResponseForRange(7, longRange);
        await chart.getByTestId('asset-calendar-window-1w').click();
        const i60gWindowResponse = await i60gWindowResponsePromise;
        expect(i60gWindowResponse.ok()).toBe(true);
        expect(await i60gWindowResponse.finished()).toBeNull();
        const i60gWindowRequest = i60gWindowResponse.request();
        assertCalendarRequest(i60gWindowRequest.postDataJSON(), 7);
        assertCalendarBulkRequest(i60gWindowRequest.postDataJSON(), 7);
        assertMainDateRange(i60gWindowRequest.postDataJSON(), longRange);
        await expect(chart).toHaveAttribute('data-window-days', '7');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        const i60gResponsePromise = waitForCalendarResponseForRange(7, i60gRange);
        const i60gRequest = await commitSyntheticRange(i60gRange, false);
        const i60gResponse = await i60gResponsePromise;
        expect(i60gResponse.ok()).toBe(true);
        expect(await i60gResponse.finished()).toBeNull();
        assertCalendarRequest(i60gRequest.postDataJSON(), 7);
        assertCalendarBulkRequest(i60gRequest.postDataJSON(), 7);
        assertMainDateRange(i60gRequest.postDataJSON(), i60gRange);

        type I60GResponseItem = {
            asset_id?: number;
            signals?: Array<{
                instance_id?: string;
                signal_code?: string;
                status?: string;
                availability?: {reason_code?: string | null};
                error?: unknown;
                series?: Array<{key?: string; points?: CalendarPointFixture[]}>;
            }>;
        };
        const i60gPayload = (await i60gResponse.json()) as {items?: I60GResponseItem[]};
        const i60gSignalFor = (expectedAssetId: number) => {
            const item = i60gPayload.items?.find((candidate) => candidate.asset_id === expectedAssetId);
            const signal = item?.signals?.find((candidate) => candidate.instance_id === calendarInstanceId && candidate.signal_code === calendarSignalCode);
            expect(signal, `I60G Calendar response must contain signal data for asset ${expectedAssetId}`).toBeDefined();
            return signal;
        };
        const i60gPointsFor = (expectedAssetId: number): CalendarPointFixture[] => {
            const signal = i60gSignalFor(expectedAssetId);
            return signal?.series?.find((series) => series.key === 'calendar_return')?.points ?? [];
        };

        const i60gPrimarySignal = i60gSignalFor(assetId);
        expect(i60gPrimarySignal).toMatchObject({
            status: 'partial',
            availability: {reason_code: 'partial_undefined_metric'},
            error: null,
        });
        const i60gPrimaryPoints = i60gPointsFor(assetId);
        expect(i60gPrimaryPoints.map((point) => point.date)).toEqual(['2026-04-01', '2026-04-05', '2026-04-10', '2026-04-15']);
        expect(i60gPrimaryPoints.find((point) => point.date === i60gRange.start)).toEqual({
            date: i60gRange.start,
            value: 7,
            provenance: {
                status: 'available',
                reference_target_date: '2026-03-25',
                current_price_date: i60gRange.start,
                current_price_days_back: 0,
                reference_price_date: '2026-03-25',
                reference_price_days_back: 0,
                current_fx_date: null,
                current_fx_days_back: null,
                reference_fx_date: null,
                reference_fx_days_back: null,
            },
        });
        expect(i60gPrimaryPoints.every((point) => point.date >= i60gRange.start && point.date <= i60gRange.end)).toBe(true);

        expect(i60gSignalFor(readyPeer.id)).toMatchObject({
            status: 'partial',
            availability: {reason_code: 'partial_input_coverage'},
            error: null,
        });
        expect(i60gPointsFor(readyPeer.id).map((point) => point.date)).toEqual(['2026-04-06', '2026-04-09', '2026-04-15']);
        expect(i60gPointsFor(readyPeer.id).find((point) => point.date === '2026-04-06')?.provenance.reference_target_date).toBe('2026-03-30');

        expect(i60gSignalFor(errorPeer.id)).toMatchObject({
            status: 'partial',
            availability: {reason_code: 'incomplete_warmup'},
            error: null,
        });
        expect(i60gPointsFor(errorPeer.id).map((point) => point.date)).toEqual(['2026-04-11', '2026-04-13', '2026-04-15']);
        expect(i60gPointsFor(errorPeer.id).find((point) => point.date === '2026-04-11')?.provenance.reference_target_date).toBe('2026-04-04');

        expect(i60gSignalFor(partialPeer.id)).toMatchObject({
            status: 'partial',
            availability: {reason_code: 'data_gap'},
            error: null,
        });
        const i60gFxGapPoints = i60gPointsFor(partialPeer.id);
        expect(i60gFxGapPoints.map((point) => point.date)).toEqual(['2026-04-01', '2026-04-05', '2026-04-10', '2026-04-12', '2026-04-15']);
        expect(i60gFxGapPoints.some((point) => point.date === '2026-04-03')).toBe(false);
        expect(i60gFxGapPoints.find((point) => point.date === '2026-04-10')).toEqual({
            date: '2026-04-10',
            value: null,
            provenance: {
                status: 'missing_reference',
                reference_target_date: '2026-04-03',
                current_price_date: '2026-04-10',
                current_price_days_back: 0,
                reference_price_date: '2026-04-03',
                reference_price_days_back: 0,
                current_fx_date: '2026-04-10',
                current_fx_days_back: 0,
                reference_fx_date: null,
                reference_fx_days_back: null,
            },
        });

        expect(i60gSignalFor(unavailablePeer.id)).toMatchObject({
            status: 'unavailable',
            availability: {reason_code: 'undefined_metric'},
            error: null,
            series: [],
        });
        for (const expectedAssetId of [assetId, readyPeer.id, partialPeer.id, errorPeer.id]) {
            const outputDates = i60gPointsFor(expectedAssetId).map((point) => point.date);
            expect(outputDates).toEqual([...new Set(outputDates)].sort());
        }
        // The preceding broad synthetic range deliberately marked its sparse
        // price cache as covered. Force this new factual range once so the page
        // owns in-range price rows as well as the Calendar signal payload.
        const i60gPriceHydrationResponsePromise = waitForCalendarResponseForRange(7, i60gRange);
        await refreshButton.click();
        const i60gPriceHydrationResponse = await i60gPriceHydrationResponsePromise;
        expect(i60gPriceHydrationResponse.ok()).toBe(true);
        expect(await i60gPriceHydrationResponse.finished()).toBeNull();
        const i60gHydrationMainQuery = parseQueries(i60gPriceHydrationResponse.request().postDataJSON()).find((query) => query.asset_id === assetId);
        expect(i60gHydrationMainQuery).toMatchObject({
            asset_id: assetId,
            date_range: {start: i60gRange.start, end: i60gRange.end},
            include_price: true,
        });
        await expectI60GCalendarDiagnostics();

        // The held response owns the old full range and carries deliberately
        // impossible values. A concrete successor must keep every partial line,
        // problem code and date subset under its own newer ownership.
        const staleI60GGate = deferCalendarResponse(7, 'i60g-stale');
        const staleI60GRequestPromise = waitForCalendarRequestForRange(7, i60gRange);
        const staleI60GResponsePromise = waitForCalendarResponseForRange(7, i60gRange);
        await refreshButton.click();
        const staleI60GRequest = await staleI60GRequestPromise;
        assertCalendarBulkRequest(staleI60GRequest.postDataJSON(), 7);
        assertMainDateRange(staleI60GRequest.postDataJSON(), i60gRange);
        await expect(chart).toHaveAttribute('data-series-state', 'loading');

        const successorI60GResponsePromise = waitForCalendarResponseForRange(7, i60gSuccessorRange);
        const successorI60GRequest = await commitSyntheticRange(i60gSuccessorRange, false);
        const successorI60GResponse = await successorI60GResponsePromise;
        expect(successorI60GResponse.ok()).toBe(true);
        expect(await successorI60GResponse.finished()).toBeNull();
        assertCalendarBulkRequest(successorI60GRequest.postDataJSON(), 7);
        assertMainDateRange(successorI60GRequest.postDataJSON(), i60gSuccessorRange);
        await expectI60GCalendarDiagnostics();
        const successorI60GChart = await readI60GCalendarChart();

        staleI60GGate.release();
        const staleI60GResponse = await staleI60GResponsePromise;
        expect(staleI60GResponse.ok()).toBe(true);
        expect(await staleI60GResponse.finished()).toBeNull();
        const staleI60GPayload = (await staleI60GResponse.json()) as {items?: I60GResponseItem[]};
        const staleI60GPrimary = staleI60GPayload.items
            ?.find((item) => item.asset_id === assetId)
            ?.signals?.find((signal) => signal.instance_id === calendarInstanceId)
            ?.series?.find((series) => series.key === 'calendar_return')
            ?.points?.find((point) => point.date === i60gRange.start);
        expect(staleI60GPrimary?.value).toBe(1007);
        await expect.poll(readI60GCalendarChart).toEqual(successorI60GChart);
        await expect(dateRangeEndInput).toHaveValue(i60gSuccessorRange.end);
        await expectI60GCalendarDiagnostics();

        const restoredI60GResponsePromise = waitForCalendarResponseForRange(7, i60gRange);
        const restoredI60GRequest = await commitSyntheticRange(i60gRange, false);
        const restoredI60GResponse = await restoredI60GResponsePromise;
        expect(restoredI60GResponse.ok()).toBe(true);
        expect(await restoredI60GResponse.finished()).toBeNull();
        assertCalendarBulkRequest(restoredI60GRequest.postDataJSON(), 7);
        assertMainDateRange(restoredI60GRequest.postDataJSON(), i60gRange);
        await expectI60GCalendarDiagnostics();
        await expect.poll(readI60GCalendarChart).toEqual({
            dates: ['2026-04-01', '2026-04-05', '2026-04-06', '2026-04-09', '2026-04-10', '2026-04-11', '2026-04-12', '2026-04-13', '2026-04-15'],
            main: [7, 7.4, null, null, null, null, null, null, 8.1],
            peers: {
                [readyPeer.display_name]: [null, null, 16, 17, null, null, null, null, 18],
                [partialPeer.display_name]: [21, 22, null, null, null, null, 24, null, 25],
                [unavailablePeer.display_name]: [null, null, null, null, null, null, null, null, null],
                [errorPeer.display_name]: [null, null, null, null, null, 31, null, 32, 33],
                [invalidCalendarPeer.display_name]: [null, null, null, null, null, null, null, null, null],
            },
            presentPeerLabels: [readyPeer.display_name, partialPeer.display_name, errorPeer.display_name].sort(),
        });

        // Fingerprint A is factual and fully applied above. Start a distinct
        // range-owned fingerprint B and hold its typed failed result. The
        // loading transition itself must evict A's primary dates and peer map;
        // otherwise those stale peers can promote B from error to partial.
        const rejectedI60GGate = deferCalendarResponse(7, 'i60g-rejected');
        const rejectedI60GRequestPromise = waitForCalendarRequestForRange(7, i60gRejectedRange);
        const rejectedI60GResponsePromise = waitForCalendarResponseForRange(7, i60gRejectedRange);
        const rejectedI60GCommitPromise = commitSyntheticRange(i60gRejectedRange, false);
        const rejectedI60GRequest = await rejectedI60GRequestPromise;
        assertCalendarBulkRequest(rejectedI60GRequest.postDataJSON(), 7);
        assertMainDateRange(rejectedI60GRequest.postDataJSON(), i60gRejectedRange);
        await expect(page.getByTestId('asset-calendar-return-loading')).toBeVisible();
        await expect(chart).toHaveAttribute('data-series-state', 'loading');
        await expect(chart).toHaveAttribute('data-calendar-comparison-ready', '');
        await expect(chart).toHaveAttribute('data-calendar-comparison-partial', '');
        await expect(chart.locator('canvas')).toHaveCount(0);

        rejectedI60GGate.release();
        const rejectedI60GResponse = await rejectedI60GResponsePromise;
        expect(rejectedI60GResponse.ok()).toBe(true);
        expect(await rejectedI60GResponse.finished()).toBeNull();
        const rejectedI60GCommitRequest = await rejectedI60GCommitPromise;
        assertCalendarRequest(rejectedI60GCommitRequest.postDataJSON(), 7);
        assertMainDateRange(rejectedI60GCommitRequest.postDataJSON(), i60gRejectedRange);
        const rejectedI60GPayload = (await rejectedI60GResponse.json()) as {items?: I60GResponseItem[]};
        expect(rejectedI60GPayload.items?.find((item) => item.asset_id === assetId)?.signals?.find((signal) => signal.instance_id === calendarInstanceId && signal.signal_code === calendarSignalCode)).toMatchObject({
            status: 'failed',
            error: {
                code: 'compute_error',
                message: 'Synthetic failed calendar-return calculation.',
            },
        });
        await expect(page.getByTestId('asset-calendar-return-error')).toBeVisible();
        await expect(chart).toHaveAttribute('data-series-state', 'error');
        await expect(chart).toHaveAttribute('data-calendar-primary-problem-code', 'calculation_failed');
        await expect(chart).toHaveAttribute('data-calendar-primary-problem-status', 'failed');
        await expect(chart.getByTestId('asset-calendar-primary-problem')).toHaveAttribute('data-problem-code', 'calculation_failed');
        await expect(chart.getByTestId('asset-calendar-primary-problem')).toHaveAttribute('data-problem-status', 'failed');
        await expect(chart).toHaveAttribute('data-calendar-comparison-ready', '');
        await expect(chart).toHaveAttribute('data-calendar-comparison-partial', '');
        await expect(page.getByTestId('asset-calendar-return-partial')).toBeHidden();
        await expect(chart.locator('canvas')).toHaveCount(0);

        // A primary with zero factual outputs must not suppress a factual peer.
        // This same spec is registered for desktop and mobile, so the shared
        // structured assertions cover both layouts without screenshot inference.
        const peerOnlyUnavailableGate = deferCalendarResponse(7, 'i60g-primary-unavailable');
        const peerOnlyUnavailableResponsePromise = waitForCalendarResponseForRange(7, i60gPeerOnlyUnavailableRange);
        const peerOnlyUnavailableCommitPromise = commitSyntheticRange(i60gPeerOnlyUnavailableRange, false);
        peerOnlyUnavailableGate.release();
        const peerOnlyUnavailableResponse = await peerOnlyUnavailableResponsePromise;
        expect(peerOnlyUnavailableResponse.ok()).toBe(true);
        expect(await peerOnlyUnavailableResponse.finished()).toBeNull();
        const peerOnlyUnavailableRequest = await peerOnlyUnavailableCommitPromise;
        assertCalendarRequest(peerOnlyUnavailableRequest.postDataJSON(), 7);
        assertCalendarBulkRequest(peerOnlyUnavailableRequest.postDataJSON(), 7);
        assertMainDateRange(peerOnlyUnavailableRequest.postDataJSON(), i60gPeerOnlyUnavailableRange);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', '7');
        await expect(chart).toHaveAttribute('data-series-state', 'partial');
        await expect(chart).toHaveAttribute('data-calendar-primary-problem-code', 'undefined_metric');
        await expect(chart).toHaveAttribute('data-calendar-primary-problem-status', 'unavailable');
        await expect(chart).toHaveAttribute('data-calendar-comparison-ready', '');
        await expect(chart).toHaveAttribute('data-calendar-comparison-partial', [readyPeer.id, partialPeer.id, errorPeer.id].sort((left, right) => left - right).join(','));
        await expect(chart.getByTestId('asset-calendar-primary-problem')).toHaveAttribute('data-problem-code', 'undefined_metric');
        await expect(chart.getByTestId('asset-calendar-primary-problem')).toHaveAttribute('data-problem-status', 'unavailable');
        await expect(chart.getByTestId('asset-calendar-primary-problem')).toBeVisible();
        await expect(chart.getByTestId('asset-calendar-window-controls')).toBeVisible();
        await expect(calendarPrimary).toHaveAttribute('aria-pressed', 'true');
        await expectAssetDetailChartCanvas(page);
        const peerOnlyUnavailableChart = await readI60GCalendarChart();
        expect(peerOnlyUnavailableChart).toEqual({
            dates: ['2026-04-05', '2026-04-06', '2026-04-09', '2026-04-10', '2026-04-11', '2026-04-12', '2026-04-13'],
            main: [null, null, null, null, null, null, null],
            peers: {
                [readyPeer.display_name]: [null, 16, 17, null, null, null, null],
                [partialPeer.display_name]: [22, null, null, null, null, 24, null],
                [unavailablePeer.display_name]: [null, null, null, null, null, null, null],
                [errorPeer.display_name]: [null, null, null, null, 31, null, 32],
                [invalidCalendarPeer.display_name]: [null, null, null, null, null, null, null],
            },
            presentPeerLabels: [readyPeer.display_name, partialPeer.display_name, errorPeer.display_name].sort(),
        });
        expect(peerOnlyUnavailableChart.main.every((value) => value === null)).toBe(true);

        // A typed primary failure is likewise independent of factual peers:
        // peers keep the Calendar chart usable, while the primary error remains
        // exposed as its own structured problem rather than being discarded.
        const peerOnlyFailedGate = deferCalendarResponse(7, 'i60g-primary-failed');
        const peerOnlyFailedResponsePromise = waitForCalendarResponseForRange(7, i60gPeerOnlyFailedRange);
        const peerOnlyFailedCommitPromise = commitSyntheticRange(i60gPeerOnlyFailedRange, false);
        peerOnlyFailedGate.release();
        const peerOnlyFailedResponse = await peerOnlyFailedResponsePromise;
        expect(peerOnlyFailedResponse.ok()).toBe(true);
        expect(await peerOnlyFailedResponse.finished()).toBeNull();
        const peerOnlyFailedRequest = await peerOnlyFailedCommitPromise;
        assertCalendarRequest(peerOnlyFailedRequest.postDataJSON(), 7);
        assertCalendarBulkRequest(peerOnlyFailedRequest.postDataJSON(), 7);
        assertMainDateRange(peerOnlyFailedRequest.postDataJSON(), i60gPeerOnlyFailedRange);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', '7');
        await expect(chart).toHaveAttribute('data-series-state', 'partial');
        await expect(chart).toHaveAttribute('data-calendar-primary-problem-code', 'calculation_failed');
        await expect(chart).toHaveAttribute('data-calendar-primary-problem-status', 'failed');
        await expect(chart.getByTestId('asset-calendar-primary-problem')).toHaveAttribute('data-problem-code', 'calculation_failed');
        await expect(chart.getByTestId('asset-calendar-primary-problem')).toHaveAttribute('data-problem-status', 'failed');
        await expect(chart.getByTestId('asset-calendar-primary-problem')).toBeVisible();
        await expect(chart.getByTestId('asset-calendar-window-controls')).toBeVisible();
        await expectAssetDetailChartCanvas(page);
        const peerOnlyFailedChart = await readI60GCalendarChart();
        expect(peerOnlyFailedChart).toEqual({
            dates: ['2026-04-05', '2026-04-06', '2026-04-09', '2026-04-10', '2026-04-11', '2026-04-12'],
            main: [null, null, null, null, null, null],
            peers: {
                [readyPeer.display_name]: [null, 16, 17, null, null, null],
                [partialPeer.display_name]: [22, null, null, null, null, 24],
                [unavailablePeer.display_name]: [null, null, null, null, null, null],
                [errorPeer.display_name]: [null, null, null, null, 31, null],
                [invalidCalendarPeer.display_name]: [null, null, null, null, null, null],
            },
            presentPeerLabels: [readyPeer.display_name, partialPeer.display_name, errorPeer.display_name].sort(),
        });
        expect(peerOnlyFailedChart.main.every((value) => value === null)).toBe(true);

        const restoreAfterI60GResponsePromise = waitForCalendarResponseForRange(7, longRange);
        const restoreAfterI60GRequest = await commitSyntheticRange(longRange, false);
        const restoreAfterI60GResponse = await restoreAfterI60GResponsePromise;
        expect(restoreAfterI60GResponse.ok()).toBe(true);
        expect(await restoreAfterI60GResponse.finished()).toBeNull();
        assertCalendarBulkRequest(restoreAfterI60GRequest.postDataJSON(), 7);
        const restoreAfterI60GThirtyDayResponsePromise = waitForCalendarResponseForRange(30, longRange);
        await chart.getByTestId('asset-calendar-window-1m').click();
        const restoreAfterI60GThirtyDayResponse = await restoreAfterI60GThirtyDayResponsePromise;
        expect(restoreAfterI60GThirtyDayResponse.ok()).toBe(true);
        expect(await restoreAfterI60GThirtyDayResponse.finished()).toBeNull();
        assertCalendarBulkRequest(restoreAfterI60GThirtyDayResponse.request().postDataJSON(), 30);
        await expect(chart).toHaveAttribute('data-window-days', '30');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expectCalendarPeerDiagnostics();

        const readPersistedReadyPeerId = async (): Promise<unknown> => {
            const persisted = await readPersistedPairSettings(chartSettingsStorageKey);
            const persistedSignals = Array.isArray(persisted?.signals) ? persisted.signals : [];
            const readyConfig = persistedSignals.find((candidate): candidate is Record<string, unknown> => candidate !== null && typeof candidate === 'object' && (candidate as Record<string, unknown>).id === readySignalId);
            const params = readyConfig?.params;
            return params !== null && typeof params === 'object' ? (params as Record<string, unknown>).assetId : undefined;
        };
        const expectedPriceComparisonRuntimeMarkers = comparisonPeers.map((peer) => ({
            configId: `calendar-peer-${peer.id}`,
            assetId: String(peer.id),
            ownsConversionFailed: true,
            conversionFailed: false,
        }));
        const readPersistedPriceComparisonRuntimeMarkers = async () => {
            const persisted = await readPersistedPairSettings(chartSettingsStorageKey);
            const persistedSignals = Array.isArray(persisted?.signals) ? persisted.signals : [];
            return expectedPriceComparisonRuntimeMarkers.map(({configId}) => {
                const config = persistedSignals.find((candidate): candidate is Record<string, unknown> => candidate !== null && typeof candidate === 'object' && (candidate as Record<string, unknown>).id === configId);
                const rawParams = config?.params;
                const params = rawParams !== null && typeof rawParams === 'object' ? (rawParams as Record<string, unknown>) : null;
                return {
                    configId,
                    assetId: params?.assetId ?? null,
                    ownsConversionFailed: params !== null && Object.hasOwn(params, '_conversionFailed'),
                    conversionFailed: params?._conversionFailed ?? null,
                };
            });
        };
        const expectCurrentPriceComparisonData = async (): Promise<void> => {
            await expect.poll(readPersistedReadyPeerId).toBe(String(readyPeer.id));
            await expect(dateRangeStartInput).toHaveValue(ninetyDayRange.start);
            await expect(dateRangeEndInput).toHaveValue(ninetyDayRange.end);
            await expect(chart).toHaveAttribute('data-calendar-range-days', String(ninetyDayRange.spanDays));
            await expect(readySignalCard.getByRole('button', {name: '📈3', exact: true})).toBeVisible();
            await expect(readySignalCard.getByRole('button', {name: '💰2', exact: true})).toBeVisible();
            await expect(partialSignalCard.getByRole('button', {name: '📈3', exact: true})).toBeVisible();
            await expect(partialSignalCard.getByRole('button', {name: '✂️1', exact: true})).toHaveCount(0);
            await expect.poll(readChartEventMarkerAssetLabels).toContain(readyPeer.display_name);
        };
        const expectUnacceptedSyncPreservedComparisonState = async (): Promise<void> => {
            await expect.poll(readPersistedReadyPeerId).toBe(String(readyPeer.id));
            await expect(dateRangeStartInput).toHaveValue(ninetyDayRange.start);
            await expect(dateRangeEndInput).toHaveValue(ninetyDayRange.end);
            await expect(readySignalCard.getByRole('button', {name: '📈1', exact: true})).toBeVisible();
            await expect(readySignalCard.getByRole('button', {name: '💰2', exact: true})).toHaveCount(0);
            await expect(partialSignalCard.getByRole('button', {name: '📈1', exact: true})).toBeVisible();
            await expect(partialSignalCard.getByRole('button', {name: '✂️1', exact: true})).toBeVisible();
            await expect(readySignalCard.getByTestId(`signal-fx-sync-${readySignalId}`)).toBeVisible();
            await expect.poll(readChartEventMarkerAssetLabels).toContain(partialPeer.display_name);
        };
        const expectStandalonePreSyncComparisonState = async (): Promise<void> => {
            await expect(readySignalCard.getByRole('button', {name: '📈3', exact: true})).toBeVisible();
            await expect(readySignalCard.getByRole('button', {name: '💰2', exact: true})).toHaveCount(0);
            await expect(partialSignalCard.getByRole('button', {name: '📈3', exact: true})).toBeVisible();
            await expect(partialSignalCard.getByRole('button', {name: '✂️1', exact: true})).toHaveCount(0);
            await expect.poll(readChartEventMarkerAssetLabels).toEqual([]);
        };
        const expectSuccessorPriceComparisonState = async (): Promise<void> => {
            await expectCurrentPriceComparisonData();
            const currentPriceIssue = readySignalCard.getByTestId('signal-issue');
            await expect(currentPriceIssue).toBeVisible();
            await expect(currentPriceIssue).toHaveAttribute('data-severity', 'error');
            await expect(currentPriceIssue).not.toHaveAttribute('data-problem-code', /.+/);
            await expect(partialSignalCard.getByTestId('signal-issue')).toHaveCount(0);
            await expect(readySignalCard.getByTestId(`signal-fx-sync-${readySignalId}`)).toBeVisible();
            await expect(readySignalCard.getByTestId(`signal-fx-detail-${readySignalId}`)).toHaveCount(0);
            await expect(partialSignalCard.getByTestId(`signal-fx-detail-calendar-peer-${partialPeer.id}`)).toBeVisible();
            await expect(partialSignalCard.getByTestId(`signal-fx-sync-calendar-peer-${partialPeer.id}`)).toHaveCount(0);
            await expect(page.getByTestId('data-quality-issue-FX_PAIR_NO_DATA')).toBeVisible();
        };
        const expectCorrectedPriceComparisonState = async (): Promise<void> => {
            await expectCurrentPriceComparisonData();
            await expect(readySignalCard.getByTestId('signal-issue')).toHaveCount(0);
            await expect(partialSignalCard.getByTestId('signal-issue')).toHaveCount(0);
            await expect(readySignalCard.getByTestId(`signal-fx-sync-${readySignalId}`)).toHaveCount(0);
            await expect(readySignalCard.getByTestId(`signal-fx-detail-${readySignalId}`)).toBeVisible();
            await expect(partialSignalCard.getByTestId(`signal-fx-detail-calendar-peer-${partialPeer.id}`)).toBeVisible();
            await expect(partialSignalCard.getByTestId(`signal-fx-sync-calendar-peer-${partialPeer.id}`)).toHaveCount(0);
            await expect(page.getByTestId('data-quality-issue-FX_PAIR_NO_DATA')).toHaveCount(0);
            await expect(requiredFxIssues).toHaveCount(0);
        };

        // Hold the old Price comparison request after it captured the original
        // peer/range/currency fingerprint. Changing the range starts a
        // successor which must be the only response allowed to publish runtime
        // points, event summaries, or FX diagnostics.
        const stalePriceComparisonGate = deferStalePriceComparisonResponse(longRange, true);
        const stalePriceComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, longRange, asset.currency);
        const stalePriceComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, longRange, asset.currency);
        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await refreshButton.click();
        const stalePriceComparisonRequest = await stalePriceComparisonRequestPromise;
        assertPriceComparisonRequest(stalePriceComparisonRequest.postDataJSON(), comparisonPeerIds, longRange, asset.currency);
        const lineChartButton = chart.getByTestId('chart-type-line');
        await expect(lineChartButton).toBeVisible();
        await lineChartButton.click();
        await expect(chart.getByTestId('candlestick-chart')).toBeHidden();

        const successorPriceComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        const successorMainRangeRequest = await commitSyntheticRange(ninetyDayRange, true);
        const successorPriceComparisonResponse = await successorPriceComparisonResponsePromise;
        expect(successorPriceComparisonResponse.ok()).toBe(true);
        expect(await successorPriceComparisonResponse.finished()).toBeNull();
        assertMainDateRange(successorMainRangeRequest.postDataJSON(), ninetyDayRange);
        assertPriceComparisonRequest(successorPriceComparisonResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        expect(priceComparisonRaceSuccessorServed).toBe(true);
        await expectSuccessorPriceComparisonState();

        stalePriceComparisonGate.release();
        const stalePriceComparisonResponse = await stalePriceComparisonResponsePromise;
        expect(stalePriceComparisonResponse.ok()).toBe(true);
        expect(await stalePriceComparisonResponse.finished()).toBeNull();
        priceComparisonRaceActive = false;
        await expectSuccessorPriceComparisonState();

        const retainedPriceIssue = readySignalCard.getByTestId('signal-issue');
        await expect(retainedPriceIssue).toBeVisible();
        await expect(retainedPriceIssue).toHaveAttribute('data-severity', 'error');
        await expect(retainedPriceIssue).not.toHaveAttribute('data-problem-code', /.+/);
        await expect(page.getByTestId('data-quality-issue-FX_PAIR_NO_DATA')).toBeVisible();

        // A forced refresh must supersede, not join, a same-fingerprint
        // comparison already in flight. Hold both generations so the first
        // stale payload can be released while its forced successor is still
        // pending, and count the two main/comparison request pairs exactly.
        const ninetyDayComparisonRangeKey = `${ninetyDayRange.start}|${ninetyDayRange.end}`;
        const sameFingerprintPriceQueriesBefore = priceQueryRequestCount;
        const sameFingerprintMainRequestsBefore = mainPriceRequestCount;
        const sameFingerprintComparisonRequestsBefore = priceComparisonRequestCount;
        const sameFingerprintRangeRequestsBefore = priceComparisonRequestCountsByRange.get(ninetyDayComparisonRangeKey) ?? 0;
        const sameFingerprintCalendarRequestsBefore = calendarRequestCount;
        const preForcedRefreshComparisonGate = deferStalePriceComparisonResponse(ninetyDayRange, true);
        const preForcedRefreshMainRequestPromise = waitForMainPriceRequest(ninetyDayRange);
        const preForcedRefreshMainResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const preForcedRefreshComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const preForcedRefreshComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await refreshButton.click();

        const preForcedRefreshMainRequest = await preForcedRefreshMainRequestPromise;
        assertMainDateRange(preForcedRefreshMainRequest.postDataJSON(), ninetyDayRange);
        expect(findCalendarSignal(preForcedRefreshMainRequest.postDataJSON())).toBeUndefined();
        const preForcedRefreshMainResponse = await preForcedRefreshMainResponsePromise;
        expect(preForcedRefreshMainResponse.ok()).toBe(true);
        expect(await preForcedRefreshMainResponse.finished()).toBeNull();
        const preForcedRefreshComparisonRequest = await preForcedRefreshComparisonRequestPromise;
        assertPriceComparisonRequest(preForcedRefreshComparisonRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => priceComparisonRequestCountsByRange.get(ninetyDayComparisonRangeKey) ?? 0).toBe(sameFingerprintRangeRequestsBefore + 1);
        await expect(refreshButton).toBeEnabled();

        const forcedRefreshSuccessorGate = deferNextPriceComparisonResponse();
        const forcedRefreshMainRequestPromise = waitForMainPriceRequest(ninetyDayRange);
        const forcedRefreshMainResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const forcedRefreshSuccessorRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const forcedRefreshSuccessorResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await refreshButton.click();

        const forcedRefreshMainRequest = await forcedRefreshMainRequestPromise;
        assertMainDateRange(forcedRefreshMainRequest.postDataJSON(), ninetyDayRange);
        expect(findCalendarSignal(forcedRefreshMainRequest.postDataJSON())).toBeUndefined();
        const forcedRefreshMainResponse = await forcedRefreshMainResponsePromise;
        expect(forcedRefreshMainResponse.ok()).toBe(true);
        expect(await forcedRefreshMainResponse.finished()).toBeNull();
        const forcedRefreshSuccessorRequest = await forcedRefreshSuccessorRequestPromise;
        assertPriceComparisonRequest(forcedRefreshSuccessorRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => priceComparisonRequestCountsByRange.get(ninetyDayComparisonRangeKey) ?? 0).toBe(sameFingerprintRangeRequestsBefore + 2);
        expect(priceQueryRequestCount).toBe(sameFingerprintPriceQueriesBefore + 4);
        expect(mainPriceRequestCount).toBe(sameFingerprintMainRequestsBefore + 2);
        expect(priceComparisonRequestCount).toBe(sameFingerprintComparisonRequestsBefore + 2);
        expect(calendarRequestCount).toBe(sameFingerprintCalendarRequestsBefore);
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        preForcedRefreshComparisonGate.release();
        const preForcedRefreshComparisonResponse = await preForcedRefreshComparisonResponsePromise;
        expect(preForcedRefreshComparisonResponse.ok()).toBe(true);
        expect(await preForcedRefreshComparisonResponse.finished()).toBeNull();
        await expectSuccessorPriceComparisonState();

        forcedRefreshSuccessorGate.release();
        const forcedRefreshSuccessorResponse = await forcedRefreshSuccessorResponsePromise;
        expect(forcedRefreshSuccessorResponse.ok()).toBe(true);
        expect(await forcedRefreshSuccessorResponse.finished()).toBeNull();
        assertPriceComparisonRequest(forcedRefreshSuccessorResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        expect(priceQueryRequestCount).toBe(sameFingerprintPriceQueriesBefore + 4);
        expect(mainPriceRequestCount).toBe(sameFingerprintMainRequestsBefore + 2);
        expect(priceComparisonRequestCount).toBe(sameFingerprintComparisonRequestsBefore + 2);
        expect(priceComparisonRequestCountsByRange.get(ninetyDayComparisonRangeKey) ?? 0).toBe(sameFingerprintRangeRequestsBefore + 2);
        expect(calendarRequestCount).toBe(sameFingerprintCalendarRequestsBefore);
        priceComparisonRaceActive = false;
        await expectSuccessorPriceComparisonState();

        // The forced successor above has completed, and the focus round-trip
        // runs after its promise-settlement microtask clears the remembered
        // in-flight owner. A later non-force owner with the exact applied
        // fingerprint must still be a no-op; the two forced refreshes above
        // remain the only comparison requests in this range.
        await pricePrimary.focus();
        await expect(pricePrimary).toBeFocused();
        const appliedOrdinaryPriceQueriesBefore = priceQueryRequestCount;
        const appliedOrdinaryComparisonRequestsBefore = priceComparisonRequestCount;
        const appliedOrdinaryCalendarRequestsBefore = calendarRequestCount;
        const appliedOrdinaryCalendarResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const appliedOrdinaryCalendarResponse = await appliedOrdinaryCalendarResponsePromise;
        expect(appliedOrdinaryCalendarResponse.ok()).toBe(true);
        expect(await appliedOrdinaryCalendarResponse.finished()).toBeNull();
        assertCalendarBulkRequest(appliedOrdinaryCalendarResponse.request().postDataJSON(), 30);
        assertMainDateRange(appliedOrdinaryCalendarResponse.request().postDataJSON(), ninetyDayRange);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await pricePrimary.focus();
        await expect(pricePrimary).toBeFocused();
        expect(priceQueryRequestCount).toBe(appliedOrdinaryPriceQueriesBefore + 1);
        expect(priceComparisonRequestCount).toBe(appliedOrdinaryComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(appliedOrdinaryCalendarRequestsBefore + 1);
        await expectSuccessorPriceComparisonState();

        // Page Sync completes while Calendar owns the visible chart. Seed a
        // distinctive Price-only peer snapshot first, then prove the hidden
        // Price runtime is invalidated: returning to Price must issue exactly
        // one new comparison request and publish only the post-sync points.
        pageSyncComparisonSnapshot = 'pre-sync';
        priceComparisonSyncSucceeded = false;
        const pageSyncSeedPriceQueriesBefore = priceQueryRequestCount;
        const pageSyncSeedMainRequestsBefore = mainPriceRequestCount;
        const pageSyncSeedComparisonRequestsBefore = priceComparisonRequestCount;
        const pageSyncSeedCalendarRequestsBefore = calendarRequestCount;
        const pageSyncSeedComparisonGate = deferNextPriceComparisonResponse();
        const pageSyncSeedMainResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const pageSyncSeedComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const pageSyncSeedComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await refreshButton.click();
        const pageSyncSeedMainResponse = await pageSyncSeedMainResponsePromise;
        expect(pageSyncSeedMainResponse.ok()).toBe(true);
        expect(await pageSyncSeedMainResponse.finished()).toBeNull();
        assertMainDateRange(pageSyncSeedMainResponse.request().postDataJSON(), ninetyDayRange);
        const pageSyncSeedComparisonRequest = await pageSyncSeedComparisonRequestPromise;
        assertPriceComparisonRequest(pageSyncSeedComparisonRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => priceComparisonRequestCount).toBe(pageSyncSeedComparisonRequestsBefore + 1);
        pageSyncSeedComparisonGate.release();
        const pageSyncSeedComparisonResponse = await pageSyncSeedComparisonResponsePromise;
        expect(pageSyncSeedComparisonResponse.ok()).toBe(true);
        expect(await pageSyncSeedComparisonResponse.finished()).toBeNull();
        await expect.poll(() => readChartLineValues(readyPeer.display_name)).toEqual([901, 902, 903]);
        await chart.getByTestId('chart-view-percentage').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'percentage');
        await expect.poll(async () => (await readChartLineValues(readyPeer.display_name)).map((value) => Number(value.toFixed(6)))).toEqual([0, 0.110988, 0.221976]);
        await chart.getByTestId('chart-view-absolute').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'absolute');
        await expect.poll(() => readChartLineValues(readyPeer.display_name)).toEqual([901, 902, 903]);
        expect(priceQueryRequestCount).toBe(pageSyncSeedPriceQueriesBefore + 2);
        expect(mainPriceRequestCount).toBe(pageSyncSeedMainRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(pageSyncSeedComparisonRequestsBefore + 1);
        expect(calendarRequestCount).toBe(pageSyncSeedCalendarRequestsBefore);

        const pageSyncEnterCalendarResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const pageSyncEnterCalendarResponse = await pageSyncEnterCalendarResponsePromise;
        expect(pageSyncEnterCalendarResponse.ok()).toBe(true);
        expect(await pageSyncEnterCalendarResponse.finished()).toBeNull();
        assertCalendarBulkRequest(pageSyncEnterCalendarResponse.request().postDataJSON(), 30);
        assertMainDateRange(pageSyncEnterCalendarResponse.request().postDataJSON(), ninetyDayRange);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');

        pageSyncComparisonSnapshot = 'post-sync';
        nextAssetSyncStatus = 'ok';
        nextFxSyncStatus = 'partial';
        const pageSyncAssetRequestsBefore = assetSyncRequestCount;
        const pageSyncFxRequestsBefore = fxSyncRequestCount;
        const pageSyncFxConversionsBefore = fxConvertRequests.length;
        const pageSyncPriceQueriesBefore = priceQueryRequestCount;
        const pageSyncComparisonRequestsBefore = priceComparisonRequestCount;
        const pageSyncCalendarRequestsBefore = calendarRequestCount;
        const pageSyncRouteMutationsBefore = fxRouteMutationRequestCount;
        const pageSyncAssetRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const pageSyncAssetResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const pageSyncFxRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const pageSyncFxResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const pageSyncCalendarResponsePromise = waitForCalendarResponse(30);
        const pageSyncMetadataResponsePromise = page.waitForResponse((response) => response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/v1/assets/provider/assignments', {timeout: 10_000});
        const pageSyncButton = page.getByTestId('asset-detail-sync-btn');
        await expect(pageSyncButton).toBeEnabled();
        await pageSyncButton.click();
        const pageSyncModal = page.getByTestId('page-sync-modal');
        await expect(pageSyncModal).toBeVisible();
        const pageSyncStart = pageSyncModal.getByTestId('sync-modal-start');
        await expect(pageSyncStart).toBeEnabled();
        await pageSyncStart.click();

        const pageSyncAssetRequest = await pageSyncAssetRequestPromise;
        const pageSyncAssetQueries = parseQueries(pageSyncAssetRequest.postDataJSON());
        expect(pageSyncAssetQueries.map((query) => query.asset_id).sort((left, right) => Number(left) - Number(right))).toEqual([...pageSyncAssetIds].sort((left, right) => left - right));
        for (const query of pageSyncAssetQueries) {
            expect(query.date_range).toEqual({start: ninetyDayRange.start, end: ninetyDayRange.end});
        }
        const pageSyncFxRequest = await pageSyncFxRequestPromise;
        const pageSyncFxPayload = pageSyncFxRequest.postDataJSON() as FxSyncRequest;
        expect(Array.isArray(pageSyncFxPayload.pairs) ? [...pageSyncFxPayload.pairs].sort() : pageSyncFxPayload.pairs).toEqual(configuredFxSlugs);
        expect(new Set(pageSyncFxPayload.pairs as string[]).size).toBe(configuredFxSlugs.length);
        expect(pageSyncFxPayload).toMatchObject({
            start: ninetyDayRange.start,
            end: ninetyDayRange.end,
        });

        const pageSyncAssetResponse = await pageSyncAssetResponsePromise;
        expect(pageSyncAssetResponse.ok()).toBe(true);
        expect(await pageSyncAssetResponse.finished()).toBeNull();
        expect(await pageSyncAssetResponse.json()).toMatchObject({
            success_count: pageSyncAssetIds.length,
            results: pageSyncAssetIds.map((pageSyncAssetId) => ({asset_id: pageSyncAssetId, status: 'ok'})),
        });
        const pageSyncFxResponse = await pageSyncFxResponsePromise;
        expect(pageSyncFxResponse.ok()).toBe(true);
        expect(await pageSyncFxResponse.finished()).toBeNull();
        expect(await pageSyncFxResponse.json()).toMatchObject({
            success_count: configuredFxSlugs.length,
        });
        const pageSyncCalendarResponse = await pageSyncCalendarResponsePromise;
        expect(pageSyncCalendarResponse.ok()).toBe(true);
        expect(await pageSyncCalendarResponse.finished()).toBeNull();
        assertCalendarBulkRequest(pageSyncCalendarResponse.request().postDataJSON(), 30);
        assertMainDateRange(pageSyncCalendarResponse.request().postDataJSON(), ninetyDayRange);
        const pageSyncMetadataResponse = await pageSyncMetadataResponsePromise;
        expect(pageSyncMetadataResponse.ok()).toBe(true);
        expect(await pageSyncMetadataResponse.finished()).toBeNull();
        const pageSyncRefills = fxConvertRequests.slice(pageSyncFxConversionsBefore).flat();
        expect([...new Set(pageSyncRefills.map((request) => [request.from_amount.code, request.to].sort().join('-')))].sort()).toEqual(configuredFxSlugs);
        expect(pageSyncRefills.every((request) => request.date_range.start === ninetyDayRange.start && request.date_range.end === ninetyDayRange.end)).toBe(true);
        await expect(pageSyncModal.getByTestId('sync-modal-count')).toHaveAttribute('data-section-count', '2');
        const pageSyncAssetSection = pageSyncModal.locator('[data-testid="sync-section"][data-section-id="assets"]');
        const pageSyncFxSection = pageSyncModal.locator('[data-testid="sync-section"][data-section-id="fx"]');
        await expect(pageSyncAssetSection).toHaveAttribute('data-target-count', String(pageSyncAssetIds.length));
        await expect(pageSyncFxSection).toHaveAttribute('data-target-count', String(configuredFxSlugs.length));
        for (const slug of configuredFxSlugs) {
            await expect(pageSyncFxSection.locator(`[data-testid="sync-result-row"][data-row-id="${slug}"]`)).toHaveAttribute('data-status', 'partial');
        }
        await expect(pageSyncModal.getByTestId('sync-modal-results')).toHaveAttribute('data-success', String(pageSyncAssetIds.length));
        await expect(pageSyncModal.getByTestId('sync-modal-results')).toHaveAttribute('data-total', String(pageSyncAssetIds.length + configuredFxSlugs.length));
        expect(assetSyncRequestCount).toBe(pageSyncAssetRequestsBefore + 1);
        expect(fxSyncRequestCount).toBe(pageSyncFxRequestsBefore + 1);
        expect(priceQueryRequestCount).toBe(pageSyncPriceQueriesBefore + 1);
        expect(priceComparisonRequestCount).toBe(pageSyncComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(pageSyncCalendarRequestsBefore + 1);
        expect(fxRouteMutationRequestCount).toBe(pageSyncRouteMutationsBefore);
        await pageSyncModal.getByTestId('sync-modal-close').click();
        await expect(pageSyncModal).toBeHidden();

        const pageSyncPostComparisonGate = deferNextPriceComparisonResponse();
        const pageSyncPostComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const pageSyncPostComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        const pageSyncPriceQueriesBeforeReturn = priceQueryRequestCount;
        const pageSyncComparisonRequestsBeforeReturn = priceComparisonRequestCount;
        await pricePrimary.click();
        const pageSyncPostComparisonRequest = await pageSyncPostComparisonRequestPromise;
        assertPriceComparisonRequest(pageSyncPostComparisonRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        expect(priceQueryRequestCount).toBe(pageSyncPriceQueriesBeforeReturn + 1);
        expect(priceComparisonRequestCount).toBe(pageSyncComparisonRequestsBeforeReturn + 1);
        pageSyncPostComparisonGate.release();
        const pageSyncPostComparisonResponse = await pageSyncPostComparisonResponsePromise;
        expect(pageSyncPostComparisonResponse.ok()).toBe(true);
        expect(await pageSyncPostComparisonResponse.finished()).toBeNull();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect.poll(() => readChartLineValues(readyPeer.display_name)).toEqual([911, 912, 913]);
        const pageSyncPostValues = await readChartLineValues(readyPeer.display_name);
        for (const staleValue of [901, 902, 903]) {
            expect(pageSyncPostValues).not.toContain(staleValue);
        }
        await pricePrimary.focus();
        await expect(pricePrimary).toBeFocused();
        expect(priceQueryRequestCount).toBe(pageSyncPriceQueriesBeforeReturn + 1);
        expect(priceComparisonRequestCount).toBe(pageSyncComparisonRequestsBeforeReturn + 1);

        // Seed the original Price-only points again, then complete a second Page
        // Sync from Calendar with no accepted result. The Calendar refresh proves
        // the completion callback still ran, while returning to Price must reuse
        // this applied fingerprint without issuing a peer query.
        pageSyncComparisonSnapshot = 'pre-sync';
        priceComparisonSyncSucceeded = false;
        const unacceptedSeedPriceQueriesBefore = priceQueryRequestCount;
        const unacceptedSeedMainRequestsBefore = mainPriceRequestCount;
        const unacceptedSeedComparisonRequestsBefore = priceComparisonRequestCount;
        const unacceptedSeedCalendarRequestsBefore = calendarRequestCount;
        const unacceptedSeedComparisonGate = deferNextPriceComparisonResponse();
        const unacceptedSeedMainResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const unacceptedSeedComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const unacceptedSeedComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await refreshButton.click();
        const unacceptedSeedMainResponse = await unacceptedSeedMainResponsePromise;
        expect(unacceptedSeedMainResponse.ok()).toBe(true);
        expect(await unacceptedSeedMainResponse.finished()).toBeNull();
        assertMainDateRange(unacceptedSeedMainResponse.request().postDataJSON(), ninetyDayRange);
        const unacceptedSeedComparisonRequest = await unacceptedSeedComparisonRequestPromise;
        assertPriceComparisonRequest(unacceptedSeedComparisonRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => priceComparisonRequestCount).toBe(unacceptedSeedComparisonRequestsBefore + 1);
        unacceptedSeedComparisonGate.release();
        const unacceptedSeedComparisonResponse = await unacceptedSeedComparisonResponsePromise;
        expect(unacceptedSeedComparisonResponse.ok()).toBe(true);
        expect(await unacceptedSeedComparisonResponse.finished()).toBeNull();
        await expect.poll(() => readChartLineValues(readyPeer.display_name)).toEqual([901, 902, 903]);
        expect(priceQueryRequestCount).toBe(unacceptedSeedPriceQueriesBefore + 2);
        expect(mainPriceRequestCount).toBe(unacceptedSeedMainRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(unacceptedSeedComparisonRequestsBefore + 1);
        expect(calendarRequestCount).toBe(unacceptedSeedCalendarRequestsBefore);

        const unacceptedEnterCalendarResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const unacceptedEnterCalendarResponse = await unacceptedEnterCalendarResponsePromise;
        expect(unacceptedEnterCalendarResponse.ok()).toBe(true);
        expect(await unacceptedEnterCalendarResponse.finished()).toBeNull();
        assertCalendarBulkRequest(unacceptedEnterCalendarResponse.request().postDataJSON(), 30);
        assertMainDateRange(unacceptedEnterCalendarResponse.request().postDataJSON(), ninetyDayRange);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        pageSyncComparisonSnapshot = 'post-sync';
        const unacceptedStatusesById = new Map<number, SyncStatusFixture>([
            [assetId, 'skipped'],
            [readyPeer.id, 'failed'],
            [partialPeer.id, 'skipped'],
            [unavailablePeer.id, 'failed'],
            [errorPeer.id, 'skipped'],
            [invalidCalendarPeer.id, 'failed'],
        ]);
        const unacceptedFxStatusesBySlug = new Map<string, SyncStatusFixture>([
            ['AUD-EUR', 'failed'],
            ['CHF-EUR', 'skipped'],
            ['EUR-GBP', 'failed'],
            ['EUR-JPY', 'skipped'],
            ['EUR-USD', 'failed'],
        ]);
        expect([...unacceptedFxStatusesBySlug.keys()].sort()).toEqual(configuredFxSlugs);
        nextAssetSyncStatusesById = unacceptedStatusesById;
        nextFxSyncStatusesBySlug = unacceptedFxStatusesBySlug;
        const unacceptedAssetRequestsBefore = assetSyncRequestCount;
        const unacceptedFxRequestsBefore = fxSyncRequestCount;
        const unacceptedFxConversionsBefore = fxConvertRequestCount;
        const unacceptedPriceQueriesBefore = priceQueryRequestCount;
        const unacceptedComparisonRequestsBefore = priceComparisonRequestCount;
        const unacceptedCalendarRequestsBefore = calendarRequestCount;
        const unacceptedRouteMutationsBefore = fxRouteMutationRequestCount;
        const unacceptedAssetRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const unacceptedAssetResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const unacceptedFxRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const unacceptedFxResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const unacceptedCalendarResponsePromise = waitForCalendarResponse(30);
        const unacceptedMetadataResponsePromise = page.waitForResponse((response) => response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/v1/assets/provider/assignments', {timeout: 10_000});
        await expect(pageSyncButton).toBeEnabled();
        await pageSyncButton.click();
        await expect(pageSyncModal).toBeVisible();
        await expect(pageSyncStart).toBeEnabled();
        await expect(pageSyncModal.getByTestId('sync-modal-results')).toHaveCount(0);
        await pageSyncStart.click();

        const unacceptedAssetRequest = await unacceptedAssetRequestPromise;
        const unacceptedAssetQueries = parseQueries(unacceptedAssetRequest.postDataJSON());
        expect(unacceptedAssetQueries.map((query) => query.asset_id).sort((left, right) => Number(left) - Number(right))).toEqual([...pageSyncAssetIds].sort((left, right) => left - right));
        for (const query of unacceptedAssetQueries) {
            expect(query.date_range).toEqual({start: ninetyDayRange.start, end: ninetyDayRange.end});
        }
        const unacceptedFxRequest = await unacceptedFxRequestPromise;
        const unacceptedFxPayload = unacceptedFxRequest.postDataJSON() as FxSyncRequest;
        expect(Array.isArray(unacceptedFxPayload.pairs) ? [...unacceptedFxPayload.pairs].sort() : unacceptedFxPayload.pairs).toEqual(configuredFxSlugs);
        expect(unacceptedFxPayload).toMatchObject({
            start: ninetyDayRange.start,
            end: ninetyDayRange.end,
        });

        const unacceptedAssetResponse = await unacceptedAssetResponsePromise;
        expect(unacceptedAssetResponse.ok()).toBe(true);
        expect(await unacceptedAssetResponse.finished()).toBeNull();
        expect(await unacceptedAssetResponse.json()).toMatchObject({
            success_count: 0,
            results: pageSyncAssetIds.map((pageSyncAssetId) => ({
                asset_id: pageSyncAssetId,
                status: unacceptedStatusesById.get(pageSyncAssetId),
            })),
        });
        const unacceptedFxResponse = await unacceptedFxResponsePromise;
        expect(unacceptedFxResponse.ok()).toBe(true);
        expect(await unacceptedFxResponse.finished()).toBeNull();
        const unacceptedFxResponseBody = (await unacceptedFxResponse.json()) as {
            success_count: number;
            results: Array<{pair: string; status: SyncStatusFixture}>;
        };
        expect(unacceptedFxResponseBody.success_count).toBe(0);
        expect(unacceptedFxResponseBody.results.map(({pair, status}) => ({pair, status})).sort((left, right) => left.pair.localeCompare(right.pair))).toEqual([...unacceptedFxStatusesBySlug].map(([pair, status]) => ({pair, status})).sort((left, right) => left.pair.localeCompare(right.pair)));
        const unacceptedCalendarResponse = await unacceptedCalendarResponsePromise;
        expect(unacceptedCalendarResponse.ok()).toBe(true);
        expect(await unacceptedCalendarResponse.finished()).toBeNull();
        assertCalendarBulkRequest(unacceptedCalendarResponse.request().postDataJSON(), 30);
        assertMainDateRange(unacceptedCalendarResponse.request().postDataJSON(), ninetyDayRange);
        const unacceptedMetadataResponse = await unacceptedMetadataResponsePromise;
        expect(unacceptedMetadataResponse.ok()).toBe(true);
        expect(await unacceptedMetadataResponse.finished()).toBeNull();
        await expect(pageSyncModal.getByTestId('sync-modal-count')).toHaveAttribute('data-section-count', '2');
        await expect(pageSyncModal.getByTestId('sync-modal-results')).toHaveAttribute('data-success', '0');
        await expect(pageSyncModal.getByTestId('sync-modal-results')).toHaveAttribute('data-total', String(pageSyncAssetIds.length + configuredFxSlugs.length));
        const unacceptedAssetSection = pageSyncModal.locator('[data-testid="sync-section"][data-section-id="assets"]');
        const unacceptedFxSection = pageSyncModal.locator('[data-testid="sync-section"][data-section-id="fx"]');
        for (const [pageSyncAssetId, status] of unacceptedStatusesById) {
            await expect(unacceptedAssetSection.locator(`[data-testid="sync-result-row"][data-row-id="${pageSyncAssetId}"]`)).toHaveAttribute('data-status', status);
        }
        for (const [slug, status] of unacceptedFxStatusesBySlug) {
            await expect(unacceptedFxSection.locator(`[data-testid="sync-result-row"][data-row-id="${slug}"]`)).toHaveAttribute('data-status', status);
        }
        expect(assetSyncRequestCount).toBe(unacceptedAssetRequestsBefore + 1);
        expect(fxSyncRequestCount).toBe(unacceptedFxRequestsBefore + 1);
        const unacceptedFxRefills = fxConvertRequests.slice(unacceptedFxConversionsBefore).flat();
        expect(unacceptedFxRefills).toHaveLength(configuredFxSlugs.length);
        expect([...new Set(unacceptedFxRefills.map((request) => [request.from_amount.code, request.to].sort().join('-')))].sort()).toEqual(configuredFxSlugs);
        expect(unacceptedFxRefills.every((request) => request.date_range.start === ninetyDayRange.start && request.date_range.end === ninetyDayRange.end)).toBe(true);
        expect(priceQueryRequestCount).toBe(unacceptedPriceQueriesBefore + 1);
        expect(priceComparisonRequestCount).toBe(unacceptedComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(unacceptedCalendarRequestsBefore + 1);
        expect(fxRouteMutationRequestCount).toBe(unacceptedRouteMutationsBefore);
        await pageSyncModal.getByTestId('sync-modal-close').click();
        await expect(pageSyncModal).toBeHidden();

        const unacceptedPriceQueriesBeforeReturn = priceQueryRequestCount;
        const unacceptedComparisonRequestsBeforeReturn = priceComparisonRequestCount;
        const unacceptedCalendarRequestsBeforeReturn = calendarRequestCount;
        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await pricePrimary.focus();
        await expect(pricePrimary).toBeFocused();
        await expect.poll(() => readChartLineValues(readyPeer.display_name)).toEqual([901, 902, 903]);
        expect(priceQueryRequestCount).toBe(unacceptedPriceQueriesBeforeReturn);
        expect(priceComparisonRequestCount).toBe(unacceptedComparisonRequestsBeforeReturn);
        expect(calendarRequestCount).toBe(unacceptedCalendarRequestsBeforeReturn);
        const unacceptedReusedValues = await readChartLineValues(readyPeer.display_name);
        expect(unacceptedReusedValues).toEqual([901, 902, 903]);
        for (const refreshedValue of [911, 912, 913]) {
            expect(unacceptedReusedValues).not.toContain(refreshedValue);
        }
        pageSyncComparisonSnapshot = null;
        priceComparisonSyncSucceeded = false;

        // A peer-bearing fingerprint observed while the main Price line is
        // empty is not an applied result. Re-selecting the same preset after
        // changing the peer publishes the same range through the ordinary
        // non-force owner: once main data appears, that exact fingerprint must
        // fetch once.
        const emptyLinePriceQueriesBefore = priceQueryRequestCount;
        const emptyLineMainRequestsBefore = mainPriceRequestCount;
        const emptyLineComparisonRequestsBefore = priceComparisonRequestCount;
        const emptyLineCalendarRequestsBefore = calendarRequestCount;
        const emptyLineMainGate = deferNextMainPriceResponse(true);
        const isPresetMainRequest = (raw: unknown) => {
            const queries = parseQueries(raw);
            return findCalendarSignal(queries) === undefined && queries.some((query) => query.asset_id === assetId);
        };
        const emptyLineMainRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/query' && isPresetMainRequest(request.postDataJSON()), {timeout: 10_000});
        const emptyLineMainResponsePromise = page.waitForResponse(
            (response) => {
                const request = response.request();
                return request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/query' && isPresetMainRequest(request.postDataJSON());
            },
            {timeout: 10_000},
        );
        const threeMonthPreset = page.getByTestId('date-preset-3m');
        await expect(threeMonthPreset).toBeVisible();
        await threeMonthPreset.click();
        const emptyLineMainRequest = await emptyLineMainRequestPromise;
        const emptyLineMainQuery = parseQueries(emptyLineMainRequest.postDataJSON()).find((query) => query.asset_id === assetId);
        const emptyLineRangeStart = emptyLineMainQuery?.date_range?.start;
        const emptyLineRangeEnd = emptyLineMainQuery?.date_range?.end;
        if (typeof emptyLineRangeStart !== 'string' || typeof emptyLineRangeEnd !== 'string') {
            throw new Error('The 3M empty-line request did not contain a concrete main-price range.');
        }
        const emptyLineRange = {start: emptyLineRangeStart, end: emptyLineRangeEnd};
        emptyLineMainGate.release();
        const emptyLineMainResponse = await emptyLineMainResponsePromise;
        expect(emptyLineMainResponse.ok()).toBe(true);
        expect(await emptyLineMainResponse.finished()).toBeNull();
        const emptyLineMainItem = ((await emptyLineMainResponse.json()) as {items?: Array<{asset_id?: number; prices?: unknown[]}>}).items?.find((item) => item.asset_id === assetId);
        expect(emptyLineMainItem?.prices).toEqual([]);
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        expect(priceQueryRequestCount).toBe(emptyLinePriceQueriesBefore + 1);
        expect(mainPriceRequestCount).toBe(emptyLineMainRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(emptyLineComparisonRequestsBefore);

        await selectComparisonAsset(readySignalId, replacementPeer.id);
        await expect.poll(readPersistedReadyPeerId).toBe(String(replacementPeer.id));
        expect(priceQueryRequestCount).toBe(emptyLinePriceQueriesBefore + 1);
        expect(priceComparisonRequestCount).toBe(emptyLineComparisonRequestsBefore);

        const restoreEmptyLineMainResponsePromise = waitForMainPriceResponse(emptyLineRange);
        const fetchPreviouslyEmptyFingerprintResponsePromise = waitForPriceComparisonResponse(replacementPeerIds, emptyLineRange, asset.currency);
        await threeMonthPreset.click();
        const restoreEmptyLineMainResponse = await restoreEmptyLineMainResponsePromise;
        expect(restoreEmptyLineMainResponse.ok()).toBe(true);
        expect(await restoreEmptyLineMainResponse.finished()).toBeNull();
        assertMainDateRange(restoreEmptyLineMainResponse.request().postDataJSON(), emptyLineRange);
        const fetchPreviouslyEmptyFingerprintResponse = await fetchPreviouslyEmptyFingerprintResponsePromise;
        expect(fetchPreviouslyEmptyFingerprintResponse.ok()).toBe(true);
        expect(await fetchPreviouslyEmptyFingerprintResponse.finished()).toBeNull();
        assertPriceComparisonRequest(fetchPreviouslyEmptyFingerprintResponse.request().postDataJSON(), replacementPeerIds, emptyLineRange, asset.currency);
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        expect(priceQueryRequestCount).toBe(emptyLinePriceQueriesBefore + 3);
        expect(mainPriceRequestCount).toBe(emptyLineMainRequestsBefore + 2);
        expect(priceComparisonRequestCount).toBe(emptyLineComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(emptyLineCalendarRequestsBefore);

        forceReadyPeerConversionFailure = true;
        const restoreEmptyLinePeerResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, emptyLineRange, asset.currency);
        await selectComparisonAsset(readySignalId, readyPeer.id);
        const restoreEmptyLinePeerResponse = await restoreEmptyLinePeerResponsePromise;
        expect(restoreEmptyLinePeerResponse.ok()).toBe(true);
        expect(await restoreEmptyLinePeerResponse.finished()).toBeNull();
        assertPriceComparisonRequest(restoreEmptyLinePeerResponse.request().postDataJSON(), comparisonPeerIds, emptyLineRange, asset.currency);
        await expect.poll(readPersistedReadyPeerId).toBe(String(readyPeer.id));

        const restoreNinetyDayComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        const restoreNinetyDayMainRequest = await commitSyntheticRange(ninetyDayRange, false);
        const restoreNinetyDayComparisonResponse = await restoreNinetyDayComparisonResponsePromise;
        expect(restoreNinetyDayComparisonResponse.ok()).toBe(true);
        expect(await restoreNinetyDayComparisonResponse.finished()).toBeNull();
        assertMainDateRange(restoreNinetyDayMainRequest.postDataJSON(), ninetyDayRange);
        assertPriceComparisonRequest(restoreNinetyDayComparisonResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);

        // Presentation-only signal edits are compatible with an in-progress
        // refresh, as are runtime params injected by a comparison response.
        // Hold a non-force peer change at its comparison, start the refresh and
        // hold its main await, then let the older comparison inject runtime data
        // while the style editor replaces the persisted signal object. The
        // current owner must continue with exactly one forced successor.
        const cosmeticRefreshPriceQueriesBefore = priceQueryRequestCount;
        const cosmeticRefreshMainRequestsBefore = mainPriceRequestCount;
        const cosmeticRefreshComparisonRequestsBefore = priceComparisonRequestCount;
        const runtimeParamsComparisonGate = deferNextPriceComparisonResponse();
        const runtimeParamsComparisonRequestPromise = waitForPriceComparisonRequest(replacementPeerIds, ninetyDayRange, asset.currency);
        const runtimeParamsComparisonResponsePromise = waitForPriceComparisonResponse(replacementPeerIds, ninetyDayRange, asset.currency);
        await selectComparisonAsset(readySignalId, replacementPeer.id);
        const runtimeParamsComparisonRequest = await runtimeParamsComparisonRequestPromise;
        assertPriceComparisonRequest(runtimeParamsComparisonRequest.postDataJSON(), replacementPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(readPersistedReadyPeerId).toBe(String(replacementPeer.id));

        const cosmeticRefreshMainGate = deferNextMainPriceResponse();
        const cosmeticRefreshComparisonGate = deferNextPriceComparisonResponse();
        const cosmeticRefreshMainRequestPromise = waitForMainPriceRequest(ninetyDayRange);
        const cosmeticRefreshMainResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const cosmeticRefreshComparisonRequestPromise = waitForPriceComparisonRequest(replacementPeerIds, ninetyDayRange, asset.currency);
        await expect(refreshButton).toBeEnabled();
        await refreshButton.click();
        const cosmeticRefreshMainRequest = await cosmeticRefreshMainRequestPromise;
        assertMainDateRange(cosmeticRefreshMainRequest.postDataJSON(), ninetyDayRange);

        await expect(styleToggle, 'the visible comparison style must expose its line-style button').toBeVisible();
        await styleToggle.click();
        await expect(stylePopover).toBeVisible();
        await readySignalStyle.getByRole('button', {name: 'dashed', exact: true}).click();
        await expect
            .poll(async () => {
                const persisted = await readPersistedPairSettings(chartSettingsStorageKey);
                const persistedSignals = Array.isArray(persisted?.signals) ? persisted.signals : [];
                const readyConfig = persistedSignals.find((candidate): candidate is Record<string, unknown> => candidate !== null && typeof candidate === 'object' && (candidate as Record<string, unknown>).id === readySignalId);
                const style = readyConfig?.style;
                return style !== null && typeof style === 'object' ? (style as Record<string, unknown>).lineType : null;
            })
            .toBe('dashed');
        await page.keyboard.press('Escape');
        await expect(stylePopover).toHaveCount(0);
        expect(priceQueryRequestCount).toBe(cosmeticRefreshPriceQueriesBefore + 2);
        expect(mainPriceRequestCount).toBe(cosmeticRefreshMainRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(cosmeticRefreshComparisonRequestsBefore);

        runtimeParamsComparisonGate.release();
        const runtimeParamsComparisonResponse = await runtimeParamsComparisonResponsePromise;
        expect(runtimeParamsComparisonResponse.ok()).toBe(true);
        expect(await runtimeParamsComparisonResponse.finished()).toBeNull();
        assertPriceComparisonRequest(runtimeParamsComparisonResponse.request().postDataJSON(), replacementPeerIds, ninetyDayRange, asset.currency);
        await expect(readySignalCard.getByRole('button', {name: '📈3', exact: true})).toBeVisible();

        const cosmeticRefreshComparisonResponsePromise = waitForPriceComparisonResponse(replacementPeerIds, ninetyDayRange, asset.currency);
        cosmeticRefreshMainGate.release();
        const cosmeticRefreshMainResponse = await cosmeticRefreshMainResponsePromise;
        expect(cosmeticRefreshMainResponse.ok()).toBe(true);
        expect(await cosmeticRefreshMainResponse.finished()).toBeNull();
        const cosmeticRefreshComparisonRequest = await cosmeticRefreshComparisonRequestPromise;
        assertPriceComparisonRequest(cosmeticRefreshComparisonRequest.postDataJSON(), replacementPeerIds, ninetyDayRange, asset.currency);
        cosmeticRefreshComparisonGate.release();
        const cosmeticRefreshComparisonResponse = await cosmeticRefreshComparisonResponsePromise;
        expect(cosmeticRefreshComparisonResponse.ok()).toBe(true);
        expect(await cosmeticRefreshComparisonResponse.finished()).toBeNull();
        expect(priceQueryRequestCount).toBe(cosmeticRefreshPriceQueriesBefore + 3);
        expect(mainPriceRequestCount).toBe(cosmeticRefreshMainRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(cosmeticRefreshComparisonRequestsBefore);
        await expect(readySignalCard.getByRole('button', {name: '📈3', exact: true})).toBeVisible();

        const restoreCosmeticPeerResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await selectComparisonAsset(readySignalId, readyPeer.id);
        const restoreCosmeticPeerResponse = await restoreCosmeticPeerResponsePromise;
        expect(restoreCosmeticPeerResponse.ok()).toBe(true);
        expect(await restoreCosmeticPeerResponse.finished()).toBeNull();
        assertPriceComparisonRequest(restoreCosmeticPeerResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(readPersistedReadyPeerId).toBe(String(readyPeer.id));

        // Two refresh handlers may be admitted in the same browser task before
        // Svelte commits the loading-disabled button. The second operation owns
        // the workflow. Its successful comparison must survive the older empty
        // main response, and that stale response must not launch another forced
        // comparison after the newer promise has settled.
        const tokenRacePriceQueriesBefore = priceQueryRequestCount;
        const tokenRaceMainRequestsBefore = mainPriceRequestCount;
        const tokenRaceComparisonRequestsBefore = priceComparisonRequestCount;
        const staleTokenMainGate = deferNextMainPriceResponse(true);
        const currentTokenComparisonGate = deferNextPriceComparisonResponse();
        const currentTokenMainResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const currentTokenComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const currentTokenComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect(refreshButton).toBeEnabled();
        await refreshButton.evaluate((button) => {
            if (!(button instanceof HTMLButtonElement)) throw new Error('Asset refresh control is not a button');
            button.click();
            button.click();
        });

        await expect.poll(() => mainPriceRequestCount).toBe(tokenRaceMainRequestsBefore + 2);
        const currentTokenMainResponse = await currentTokenMainResponsePromise;
        expect(currentTokenMainResponse.ok()).toBe(true);
        expect(await currentTokenMainResponse.finished()).toBeNull();
        const currentTokenComparisonRequest = await currentTokenComparisonRequestPromise;
        assertPriceComparisonRequest(currentTokenComparisonRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        currentTokenComparisonGate.release();
        const currentTokenComparisonResponse = await currentTokenComparisonResponsePromise;
        expect(currentTokenComparisonResponse.ok()).toBe(true);
        expect(await currentTokenComparisonResponse.finished()).toBeNull();
        await expect.poll(readChartComparisonLineLabels).toEqual(expect.arrayContaining(comparisonPeers.map((peer) => peer.display_name)));
        expect(priceQueryRequestCount).toBe(tokenRacePriceQueriesBefore + 3);
        expect(mainPriceRequestCount).toBe(tokenRaceMainRequestsBefore + 2);
        expect(priceComparisonRequestCount).toBe(tokenRaceComparisonRequestsBefore + 1);

        const staleTokenMainResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        staleTokenMainGate.release();
        const staleTokenMainResponse = await staleTokenMainResponsePromise;
        expect(staleTokenMainResponse.ok()).toBe(true);
        expect(await staleTokenMainResponse.finished()).toBeNull();
        const staleTokenMainItem = ((await staleTokenMainResponse.json()) as {items?: Array<{asset_id?: number; prices?: unknown[]}>}).items?.find((item) => item.asset_id === assetId);
        expect(staleTokenMainItem?.prices).toEqual([]);
        await pricePrimary.focus();
        await expect(pricePrimary).toBeFocused();
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect.poll(readChartComparisonLineLabels).toEqual(expect.arrayContaining(comparisonPeers.map((peer) => peer.display_name)));
        expect(priceQueryRequestCount).toBe(tokenRacePriceQueriesBefore + 3);
        expect(mainPriceRequestCount).toBe(tokenRaceMainRequestsBefore + 2);
        expect(priceComparisonRequestCount).toBe(tokenRaceComparisonRequestsBefore + 1);

        // A computational signal edit is different: it retires the refresh
        // continuation. Let the replacement peer publish while the old main
        // request is held, then prove the old owner cannot force the captured
        // peer set back over it.
        const computationalRefreshPriceQueriesBefore = priceQueryRequestCount;
        const computationalRefreshComparisonRequestsBefore = priceComparisonRequestCount;
        const computationalRefreshMainGate = deferNextMainPriceResponse();
        const computationalRefreshMainRequestPromise = waitForMainPriceRequest(ninetyDayRange);
        const computationalRefreshMainResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const replacementDuringRefreshResponsePromise = waitForPriceComparisonResponse(replacementPeerIds, ninetyDayRange, asset.currency);
        await refreshButton.click();
        const computationalRefreshMainRequest = await computationalRefreshMainRequestPromise;
        assertMainDateRange(computationalRefreshMainRequest.postDataJSON(), ninetyDayRange);
        await selectComparisonAsset(readySignalId, replacementPeer.id);
        const replacementDuringRefreshResponse = await replacementDuringRefreshResponsePromise;
        expect(replacementDuringRefreshResponse.ok()).toBe(true);
        expect(await replacementDuringRefreshResponse.finished()).toBeNull();
        assertPriceComparisonRequest(replacementDuringRefreshResponse.request().postDataJSON(), replacementPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(readPersistedReadyPeerId).toBe(String(replacementPeer.id));
        await expect(readySignalCard.getByTestId('signal-loading')).toHaveCount(0);
        await expect(readySignalCard.getByRole('button', {name: '📈3', exact: true})).toBeVisible();
        await expect(readySignalCard.getByTestId(`signal-fx-create-${readySignalId}`)).toBeVisible();
        const computationalRefreshPriceQueriesAfterReplacement = priceQueryRequestCount;
        expect(computationalRefreshPriceQueriesAfterReplacement).toBe(computationalRefreshPriceQueriesBefore + 2);
        expect(priceComparisonRequestCount).toBe(computationalRefreshComparisonRequestsBefore);

        computationalRefreshMainGate.release();
        const computationalRefreshMainResponse = await computationalRefreshMainResponsePromise;
        expect(computationalRefreshMainResponse.ok()).toBe(true);
        expect(await computationalRefreshMainResponse.finished()).toBeNull();
        await pricePrimary.focus();
        await expect(pricePrimary).toBeFocused();
        await expect.poll(readPersistedReadyPeerId).toBe(String(replacementPeer.id));
        await expect(readySignalCard.getByTestId('signal-loading')).toHaveCount(0);
        await expect(readySignalCard.getByRole('button', {name: '📈3', exact: true})).toBeVisible();
        await expect(readySignalCard.getByTestId(`signal-fx-create-${readySignalId}`)).toBeVisible();
        expect(priceQueryRequestCount).toBe(computationalRefreshPriceQueriesAfterReplacement);
        expect(priceComparisonRequestCount).toBe(computationalRefreshComparisonRequestsBefore);

        const restoreComputationalPeerResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await selectComparisonAsset(readySignalId, readyPeer.id);
        const restoreComputationalPeerResponse = await restoreComputationalPeerResponsePromise;
        expect(restoreComputationalPeerResponse.ok()).toBe(true);
        expect(await restoreComputationalPeerResponse.finished()).toBeNull();
        assertPriceComparisonRequest(restoreComputationalPeerResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(readPersistedReadyPeerId).toBe(String(readyPeer.id));

        // Currency is part of the refresh owner as well. Close the signals
        // panel so the summary's unlabelled SearchSelect is the sole combobox,
        // publish a GBP successor, then release an empty EUR refresh response.
        // The stale owner may neither clear the GBP chart nor force an EUR
        // comparison.
        const staleCurrencyMainGate = deferNextMainPriceResponse(true);
        const staleCurrencyMainRequestPromise = waitForMainPriceRequest(ninetyDayRange);
        const staleCurrencyMainResponsePromise = waitForMainPriceResponse(ninetyDayRange, '');
        await refreshButton.click();
        const staleCurrencyMainRequest = await staleCurrencyMainRequestPromise;
        assertMainDateRange(staleCurrencyMainRequest.postDataJSON(), ninetyDayRange);
        await firstLoadSignalsToggle.click();
        await expect(firstLoadSignalsPanel).toBeHidden();

        const currencyTrigger = filterBar.getByRole('combobox');
        await expect(currencyTrigger).toHaveCount(1);
        const openCurrencySelect = async (): Promise<void> => {
            await expect(currencyTrigger).toBeEnabled();
            await expect(async () => {
                if ((await currencyTrigger.getAttribute('aria-expanded')) !== 'true') {
                    await currencyTrigger.press('ArrowDown');
                }
                expect(await currencyTrigger.getAttribute('aria-expanded')).toBe('true');
            }).toPass({timeout: 3_000});
        };
        const gbpMainResponsePromise = waitForMainPriceResponse(ninetyDayRange, 'GBP');
        const gbpComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, 'GBP');
        await openCurrencySelect();
        const gbpOption = page.getByTestId('search-select-option-GBP');
        await expect(gbpOption).toBeVisible();
        await gbpOption.click();
        await expect(currencyTrigger).toHaveAttribute('aria-expanded', 'false');
        const gbpMainResponse = await gbpMainResponsePromise;
        expect(gbpMainResponse.ok()).toBe(true);
        expect(await gbpMainResponse.finished()).toBeNull();
        const gbpComparisonResponse = await gbpComparisonResponsePromise;
        expect(gbpComparisonResponse.ok()).toBe(true);
        expect(await gbpComparisonResponse.finished()).toBeNull();
        assertPriceComparisonRequest(gbpComparisonResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, 'GBP');
        const priceQueriesAfterGbpSuccessor = priceQueryRequestCount;
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        staleCurrencyMainGate.release();
        const staleCurrencyMainResponse = await staleCurrencyMainResponsePromise;
        expect(staleCurrencyMainResponse.ok()).toBe(true);
        expect(await staleCurrencyMainResponse.finished()).toBeNull();
        const staleCurrencyMainItem = ((await staleCurrencyMainResponse.json()) as {items?: Array<{asset_id?: number; prices?: unknown[]}>}).items?.find((item) => item.asset_id === assetId);
        expect(staleCurrencyMainItem?.prices).toEqual([]);
        await expect(currencyTrigger).toContainText('GBP');
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        expect(priceQueryRequestCount).toBe(priceQueriesAfterGbpSuccessor);

        const eurMainResponsePromise = waitForMainPriceResponse(ninetyDayRange, '');
        const eurComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await openCurrencySelect();
        const eurOption = page.getByTestId('search-select-option-EUR');
        await expect(eurOption).toBeVisible();
        await eurOption.click();
        await expect(currencyTrigger).toHaveAttribute('aria-expanded', 'false');
        const eurMainResponse = await eurMainResponsePromise;
        expect(eurMainResponse.ok()).toBe(true);
        expect(await eurMainResponse.finished()).toBeNull();
        const eurComparisonResponse = await eurComparisonResponsePromise;
        expect(eurComparisonResponse.ok()).toBe(true);
        expect(await eurComparisonResponse.finished()).toBeNull();
        assertPriceComparisonRequest(eurComparisonResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await firstLoadSignalsToggle.click();
        await expect(firstLoadSignalsPanel).toBeVisible();
        forceReadyPeerConversionFailure = false;

        const readyFxSyncAction = readySignalCard.getByTestId(`signal-fx-sync-${readySignalId}`);
        const errorFxSyncAction = failedSignalCard.getByTestId(`signal-fx-sync-${errorSignalId}`);
        await expect(readyFxSyncAction).toBeVisible();
        await expect(readyFxSyncAction).toBeEnabled();

        // A skipped standalone FX sync is a completed request, not an accepted
        // data mutation. Keep a comparison load in flight and prove the sync
        // neither invalidates it nor launches replacement work; the pending
        // snapshot must still be allowed to publish when released.
        const skippedFxPreSyncGate = deferStalePriceComparisonResponse(ninetyDayRange, false);
        const skippedFxPreSyncComparisonsBefore = priceComparisonRequestCount;
        const skippedFxPreSyncRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const skippedFxPreSyncResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await refreshButton.click();
        const skippedFxPreSyncRequest = await skippedFxPreSyncRequestPromise;
        assertPriceComparisonRequest(skippedFxPreSyncRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => priceComparisonRequestCount).toBe(skippedFxPreSyncComparisonsBefore + 1);

        nextFxSyncStatus = 'skipped';
        const skippedFxSyncRequestsBefore = fxSyncRequestCount;
        const skippedFxComparisonRequestsBefore = priceComparisonRequestCount;
        const skippedFxCalendarRequestsBefore = calendarRequestCount;
        const skippedFxComparisonResponsesBefore = correctedPriceComparisonResponseCount;
        const skippedFxConvertRequestsBefore = fxConvertRequestCount;
        const skippedFxSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const skippedFxSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        await readyFxSyncAction.focus();
        await expect.poll(() => page.evaluate(() => document.activeElement?.getAttribute('data-testid'))).toBe(`signal-fx-sync-${readySignalId}`);
        await page.keyboard.press('Enter');

        const skippedFxSyncRequest = await skippedFxSyncRequestPromise;
        assertFxSyncRequest(skippedFxSyncRequest.postDataJSON(), [readyPeerFxSlug], ninetyDayRange);
        const skippedFxSyncResponse = await skippedFxSyncResponsePromise;
        expect(skippedFxSyncResponse.ok()).toBe(true);
        expect(await skippedFxSyncResponse.finished()).toBeNull();
        expect(await skippedFxSyncResponse.json()).toMatchObject({
            success_count: 0,
            results: [{pair: readyPeerFxSlug, status: 'skipped'}],
        });
        await expect(readyFxSyncAction).toBeEnabled();
        expect(fxSyncRequestCount).toBe(skippedFxSyncRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(skippedFxComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(skippedFxCalendarRequestsBefore);
        expect(correctedPriceComparisonResponseCount).toBe(skippedFxComparisonResponsesBefore);
        expect(fxConvertRequestCount).toBe(skippedFxConvertRequestsBefore);

        skippedFxPreSyncGate.release();
        const skippedFxPreSyncResponse = await skippedFxPreSyncResponsePromise;
        expect(skippedFxPreSyncResponse.ok()).toBe(true);
        expect(await skippedFxPreSyncResponse.finished()).toBeNull();
        priceComparisonRaceActive = false;
        expect(priceComparisonRequestCount).toBe(skippedFxComparisonRequestsBefore);
        expect(correctedPriceComparisonResponseCount).toBe(skippedFxComparisonResponsesBefore);
        await expectUnacceptedSyncPreservedComparisonState();

        // A transport-success response is not an accepted sync. Keep a
        // comparison load in flight, then return a real per-item `failed`
        // result. The failed sync must not invalidate that load or launch a
        // replacement: when released, its distinctive one-point/split-event
        // snapshot is still allowed to publish.
        const failedFxPreSyncGate = deferStalePriceComparisonResponse(ninetyDayRange, false);
        const failedFxPreSyncComparisonsBefore = priceComparisonRequestCount;
        const failedFxPreSyncRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const failedFxPreSyncResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await refreshButton.click();
        const failedFxPreSyncRequest = await failedFxPreSyncRequestPromise;
        assertPriceComparisonRequest(failedFxPreSyncRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => priceComparisonRequestCount).toBe(failedFxPreSyncComparisonsBefore + 1);

        await expect(page.getByTestId('toast-error')).toHaveCount(0);

        const failedFxSyncRequestsBefore = fxSyncRequestCount;
        const failedFxComparisonRequestsBefore = priceComparisonRequestCount;
        const failedFxCalendarRequestsBefore = calendarRequestCount;
        const failedFxComparisonResponsesBefore = correctedPriceComparisonResponseCount;
        const failedFxConvertRequestsBefore = fxConvertRequestCount;
        nextFxSyncStatus = 'failed';
        const failedFxSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const failedFxSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        await readyFxSyncAction.focus();
        await expect.poll(() => page.evaluate(() => document.activeElement?.getAttribute('data-testid'))).toBe(`signal-fx-sync-${readySignalId}`);
        await page.keyboard.press('Enter');
        const failedFxSyncRequest = await failedFxSyncRequestPromise;
        assertFxSyncRequest(failedFxSyncRequest.postDataJSON(), [readyPeerFxSlug], ninetyDayRange);
        const failedFxSyncResponse = await failedFxSyncResponsePromise;
        expect(failedFxSyncResponse.status()).toBe(200);
        expect(failedFxSyncResponse.ok()).toBe(true);
        expect(await failedFxSyncResponse.finished()).toBeNull();
        expect(await failedFxSyncResponse.json()).toMatchObject({
            success_count: 0,
            results: [{pair: readyPeerFxSlug, status: 'failed'}],
        });
        await expect(page.getByTestId('toast-error')).toBeVisible();
        expect(fxSyncRequestCount).toBe(failedFxSyncRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(failedFxComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(failedFxCalendarRequestsBefore);
        expect(correctedPriceComparisonResponseCount).toBe(failedFxComparisonResponsesBefore);
        expect(fxConvertRequestCount).toBe(failedFxConvertRequestsBefore);

        failedFxPreSyncGate.release();
        const failedFxPreSyncResponse = await failedFxPreSyncResponsePromise;
        expect(failedFxPreSyncResponse.ok()).toBe(true);
        expect(await failedFxPreSyncResponse.finished()).toBeNull();
        priceComparisonRaceActive = false;
        expect(priceComparisonRequestCount).toBe(failedFxComparisonRequestsBefore);
        expect(correctedPriceComparisonResponseCount).toBe(failedFxComparisonResponsesBefore);

        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expectUnacceptedSyncPreservedComparisonState();
        expect(priceComparisonRequestCount).toBe(failedFxComparisonRequestsBefore);
        expect(correctedPriceComparisonResponseCount).toBe(failedFxComparisonResponsesBefore);

        // An accepted standalone sync is still stale if the page context
        // changes while its response is pending. Change both concrete range
        // endpoints before releasing it: the old completion must not refill
        // the FX cache, invalidate comparison state, or launch a chart reload.
        const staleContextFxPairGate = deferNextFxSyncResponse();
        nextFxSyncStatus = 'partial';
        const staleContextFxPairRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const staleContextFxPairResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const staleContextFxPairConversionsBefore = fxConvertRequestCount;
        await readyFxSyncAction.focus();
        await expect.poll(() => page.evaluate(() => document.activeElement?.getAttribute('data-testid'))).toBe(`signal-fx-sync-${readySignalId}`);
        await page.keyboard.press('Enter');

        const staleContextFxPairRequest = await staleContextFxPairRequestPromise;
        assertFxSyncRequest(staleContextFxPairRequest.postDataJSON(), [readyPeerFxSlug], ninetyDayRange);
        forceReadyPeerConversionFailure = true;
        const changedStandaloneSyncContext = await commitSyntheticRange(thirtyDayRange, true);
        assertMainDateRange(changedStandaloneSyncContext.postDataJSON(), thirtyDayRange);
        await expect(readyFxSyncAction).toBeVisible();
        const staleContextFxPairPriceQueriesAfterContext = priceQueryRequestCount;
        const staleContextFxPairCalendarRequestsAfterContext = calendarRequestCount;

        staleContextFxPairGate.release();
        const staleContextFxPairResponse = await staleContextFxPairResponsePromise;
        expect(staleContextFxPairResponse.ok()).toBe(true);
        expect(await staleContextFxPairResponse.finished()).toBeNull();
        expect(await staleContextFxPairResponse.json()).toMatchObject({
            success_count: 1,
            results: [{pair: readyPeerFxSlug, status: 'partial'}],
        });
        await expect(readyFxSyncAction).toBeEnabled();
        expect(fxConvertRequestCount).toBe(staleContextFxPairConversionsBefore);
        expect(priceQueryRequestCount).toBe(staleContextFxPairPriceQueriesAfterContext);
        expect(calendarRequestCount).toBe(staleContextFxPairCalendarRequestsAfterContext);
        await expect(dateRangeStartInput).toHaveValue(thirtyDayRange.start);
        await expect(dateRangeEndInput).toHaveValue(thirtyDayRange.end);

        // Keep the fixture in its pre-sync conversion-failure state so the
        // same visible standalone action can exercise an accepted, current
        // completion next.
        priceComparisonSyncSucceeded = false;
        const restoredStandaloneSyncRange = await commitSyntheticRange(ninetyDayRange, true);
        assertMainDateRange(restoredStandaloneSyncRange.postDataJSON(), ninetyDayRange);
        forceReadyPeerConversionFailure = false;
        await expect(readyFxSyncAction).toBeVisible();
        await expect(readyFxSyncAction).toBeEnabled();
        await expectStandalonePreSyncComparisonState();

        // Start a forced Price comparison, switch through the already-loaded
        // Calendar view, and hold a different window request before returning
        // to Price. Once the standalone result is accepted, hold the first
        // post-acceptance await (the FX refill), then release both old
        // responses. Neither may publish while the refill is still pending:
        // handleSyncPair() must advance both generations synchronously before
        // awaiting ensureFxRangeLoaded().
        const preSyncPriceQueriesBefore = priceQueryRequestCount;
        const preSyncMainPriceRequestsBefore = mainPriceRequestCount;
        const preSyncComparisonRequestsBefore = priceComparisonRequestCount;
        const preSyncCalendarRequestsBefore = calendarRequestCount;
        const preSyncPriceComparisonGate = deferStalePriceComparisonResponse(ninetyDayRange, false);
        const preSyncMainPriceResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const preSyncPriceComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const preSyncPriceComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await refreshButton.click();
        const preSyncMainPriceResponse = await preSyncMainPriceResponsePromise;
        expect(preSyncMainPriceResponse.ok()).toBe(true);
        expect(await preSyncMainPriceResponse.finished()).toBeNull();
        assertMainDateRange(preSyncMainPriceResponse.request().postDataJSON(), ninetyDayRange);
        const preSyncPriceComparisonRequest = await preSyncPriceComparisonRequestPromise;
        assertPriceComparisonRequest(preSyncPriceComparisonRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => priceQueryRequestCount).toBe(preSyncPriceQueriesBefore + 2);
        expect(mainPriceRequestCount).toBe(preSyncMainPriceRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(preSyncComparisonRequestsBefore + 1);

        const preSyncChartGate = deferCalendarResponse(30, 'stale-sync');
        const preSyncChartRequestPromise = waitForCalendarRequest(30);
        const preSyncChartResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const preSyncChartRequest = await preSyncChartRequestPromise;
        assertCalendarBulkRequest(preSyncChartRequest.postDataJSON(), 30);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', '30');

        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        expect(priceQueryRequestCount).toBe(preSyncPriceQueriesBefore + 3);
        expect(mainPriceRequestCount).toBe(preSyncMainPriceRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(preSyncComparisonRequestsBefore + 1);
        expect(calendarRequestCount).toBe(preSyncCalendarRequestsBefore + 1);
        await expect(readySignalCard.getByRole('button', {name: '📈3', exact: true})).toBeVisible();
        await expect(readyFxSyncAction).toBeVisible();

        await expect(readyFxSyncAction).toBeVisible();
        await expect(readyFxSyncAction).toBeEnabled();
        const fxSyncRequestsBeforeSuccess = fxSyncRequestCount;
        const fxConvertRequestsBeforeSuccess = fxConvertRequestCount;
        const priceQueriesBeforeSuccess = priceQueryRequestCount;
        const mainPriceRequestsBeforeSuccess = mainPriceRequestCount;
        const priceComparisonRequestsBeforeSuccess = priceComparisonRequestCount;
        const calendarRequestsBeforeSuccess = calendarRequestCount;
        const correctedPriceComparisonResponsesBeforeSuccess = correctedPriceComparisonResponseCount;
        const acceptedFxRefillsBefore = fxRefillCounts.get(readyPeerFxSlug) ?? 0;
        const acceptedFxRefillGate = deferFxRefillResponse(readyPeerFxSlug);
        nextFxSyncStatus = 'partial';
        const fxSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const fxSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        await readyFxSyncAction.focus();
        await expect.poll(() => page.evaluate(() => document.activeElement?.getAttribute('data-testid'))).toBe(`signal-fx-sync-${readySignalId}`);
        await page.keyboard.press('Enter');

        const fxSyncRequest = await fxSyncRequestPromise;
        expect(fxSyncRequest.postDataJSON()).toEqual({
            pairs: [readyPeerFxSlug],
            start: ninetyDayRange.start,
            end: ninetyDayRange.end,
        });
        const fxSyncResponse = await fxSyncResponsePromise;
        expect(fxSyncResponse.ok()).toBe(true);
        expect(await fxSyncResponse.finished()).toBeNull();
        expect(await fxSyncResponse.json()).toMatchObject({
            success_count: 1,
            results: [{pair: readyPeerFxSlug, status: 'partial'}],
        });

        await expect.poll(() => fxRefillCounts.get(readyPeerFxSlug) ?? 0).toBe(acceptedFxRefillsBefore + 1);
        const standaloneCosmeticPriceQueriesBefore = priceQueryRequestCount;
        await expect(styleToggle, 'the visible comparison style must expose its line-style button').toBeVisible();
        await styleToggle.click();
        await expect(stylePopover).toBeVisible();
        await readySignalStyle.getByRole('button', {name: 'dotted', exact: true}).click();
        await expect
            .poll(async () => {
                const persisted = await readPersistedPairSettings(chartSettingsStorageKey);
                const persistedSignals = Array.isArray(persisted?.signals) ? persisted.signals : [];
                const readyConfig = persistedSignals.find((candidate): candidate is Record<string, unknown> => candidate !== null && typeof candidate === 'object' && (candidate as Record<string, unknown>).id === readySignalId);
                const style = readyConfig?.style;
                return style !== null && typeof style === 'object' ? (style as Record<string, unknown>).lineType : null;
            })
            .toBe('dotted');
        await page.keyboard.press('Escape');
        await expect(stylePopover).toHaveCount(0);
        expect(priceQueryRequestCount).toBe(standaloneCosmeticPriceQueriesBefore);

        preSyncChartGate.release();
        preSyncPriceComparisonGate.release();
        const preSyncChartResponse = await preSyncChartResponsePromise;
        expect(preSyncChartResponse.ok()).toBe(true);
        expect(await preSyncChartResponse.finished()).toBeNull();
        const preSyncPriceComparisonResponse = await preSyncPriceComparisonResponsePromise;
        expect(preSyncPriceComparisonResponse.ok()).toBe(true);
        expect(await preSyncPriceComparisonResponse.finished()).toBeNull();
        await pricePrimary.focus();
        await expect(pricePrimary).toBeFocused();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expectStandalonePreSyncComparisonState();
        expect(priceQueryRequestCount).toBe(priceQueriesBeforeSuccess);
        expect(mainPriceRequestCount).toBe(mainPriceRequestsBeforeSuccess);
        expect(priceComparisonRequestCount).toBe(priceComparisonRequestsBeforeSuccess);
        expect(calendarRequestCount).toBe(calendarRequestsBeforeSuccess);

        const standaloneSuccessorMainGate = deferNextMainPriceResponse();
        const standaloneSuccessorMainRequestPromise = waitForMainPriceRequest(ninetyDayRange);
        const standaloneSuccessorMainResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const standaloneSuccessorComparisonGate = deferNextPriceComparisonResponse();
        const correctedPriceComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const correctedPriceComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        acceptedFxRefillGate.release();
        const standaloneSuccessorMainRequest = await standaloneSuccessorMainRequestPromise;
        assertMainDateRange(standaloneSuccessorMainRequest.postDataJSON(), ninetyDayRange);
        expect(findCalendarSignal(standaloneSuccessorMainRequest.postDataJSON())).toBeUndefined();
        await expect.poll(() => priceQueryRequestCount).toBe(priceQueriesBeforeSuccess + 1);
        expect(mainPriceRequestCount).toBe(mainPriceRequestsBeforeSuccess + 1);
        expect(priceComparisonRequestCount).toBe(priceComparisonRequestsBeforeSuccess);
        expect(calendarRequestCount).toBe(calendarRequestsBeforeSuccess);
        await expect(pageRoot).toHaveAttribute('data-busy', 'true');
        await expect(chart).toHaveAttribute('data-series-state', 'loading');

        standaloneSuccessorMainGate.release();
        const standaloneSuccessorMainResponse = await standaloneSuccessorMainResponsePromise;
        expect(standaloneSuccessorMainResponse.ok()).toBe(true);
        expect(await standaloneSuccessorMainResponse.finished()).toBeNull();
        assertMainDateRange(standaloneSuccessorMainResponse.request().postDataJSON(), ninetyDayRange);
        const correctedPriceComparisonRequest = await correctedPriceComparisonRequestPromise;
        assertPriceComparisonRequest(correctedPriceComparisonRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => priceQueryRequestCount).toBe(priceQueriesBeforeSuccess + 2);
        expect(mainPriceRequestCount).toBe(mainPriceRequestsBeforeSuccess + 1);
        expect(priceComparisonRequestCount).toBe(priceComparisonRequestsBeforeSuccess + 1);
        expect(calendarRequestCount).toBe(calendarRequestsBeforeSuccess);
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        standaloneSuccessorComparisonGate.release();
        const correctedPriceComparisonResponse = await correctedPriceComparisonResponsePromise;
        expect(correctedPriceComparisonResponse.ok()).toBe(true);
        expect(await correctedPriceComparisonResponse.finished()).toBeNull();
        assertPriceComparisonRequest(correctedPriceComparisonResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        expect(fxSyncRequestCount).toBe(fxSyncRequestsBeforeSuccess + 1);
        expect(fxConvertRequestCount).toBe(fxConvertRequestsBeforeSuccess + 1);
        expect(fxConvertRequests.slice(fxConvertRequestsBeforeSuccess)).toEqual([
            [
                {
                    from_amount: {code: 'EUR', amount: '1'},
                    to: 'GBP',
                    date_range: {start: ninetyDayRange.start, end: ninetyDayRange.end},
                },
            ],
        ]);
        expect(correctedPriceComparisonResponseCount).toBe(correctedPriceComparisonResponsesBeforeSuccess + 1);
        expect(priceQueryRequestCount).toBe(priceQueriesBeforeSuccess + 2);
        expect(mainPriceRequestCount).toBe(mainPriceRequestsBeforeSuccess + 1);
        expect(priceComparisonRequestCount).toBe(priceComparisonRequestsBeforeSuccess + 1);
        expect(calendarRequestCount).toBe(calendarRequestsBeforeSuccess);
        await expect(page.getByTestId('toast-warning')).toBeVisible();
        await expectCorrectedPriceComparisonState();
        await expect.poll(readChartComparisonLineLabels).toEqual(expect.arrayContaining(comparisonPeers.map((peer) => peer.display_name)));

        priceComparisonRaceActive = false;
        await expectCorrectedPriceComparisonState();
        await expect(refreshButton).toBeEnabled();

        // Capture both legs of a comparison-asset sync, then move the page to
        // a different range and primary-mode context while neither response
        // can complete. Every configured dependency for this peer (its GBP
        // price currency and the USD original currency carried by one event)
        // must use the same captured range as the Asset leg. Once the new
        // context is settled, releasing the old accepted responses must not
        // launch or publish a stale comparison reload.
        const staleContextAssetSyncGate = deferNextAssetSyncResponse();
        const staleContextFxSyncGate = deferNextFxSyncResponse();
        nextAssetSyncStatus = 'ok';
        nextFxSyncStatus = 'partial';
        const staleContextAssetSyncRequestsBefore = assetSyncRequestCount;
        const staleContextFxSyncRequestsBefore = fxSyncRequestCount;
        const staleContextAssetRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const staleContextAssetResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const staleContextFxRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const staleContextFxResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        await activateComparisonAssetSync(readySignalId);

        const staleContextAssetRequest = await staleContextAssetRequestPromise;
        const staleContextFxRequest = await staleContextFxRequestPromise;
        assertAssetSyncRequest(staleContextAssetRequest.postDataJSON(), readyPeer.id, ninetyDayPriceSyncRange);
        assertFxSyncRequest(staleContextFxRequest.postDataJSON(), readyPeerRequiredFxSlugs, ninetyDayPriceSyncRange);
        expect(assetSyncRequestCount).toBe(staleContextAssetSyncRequestsBefore + 1);
        await expect.poll(() => fxSyncRequestCount).toBe(staleContextFxSyncRequestsBefore + 1);

        // The parent, rather than the foldable child, owns this in-flight
        // identity. A real collapse removes ChartSignalsSection; reopening it
        // must project the same disabled/spinning action from the page-owned
        // set. HTMLButtonElement.click() is a genuine disabled activation (not
        // a Playwright force click), so it must not admit a duplicate request.
        const pendingAssetSyncAction = readySignalCard.getByTestId(`signal-sync-asset-${readySignalId}`);
        await expect(pendingAssetSyncAction).toBeDisabled();
        await expect(pendingAssetSyncAction.locator('svg')).toHaveClass(/animate-spin/);
        await firstLoadSignalsToggle.click();
        await expect(firstLoadSignalsToggle).toHaveAttribute('aria-expanded', 'false');
        await expect(firstLoadSignalsPanel).toHaveCount(0);
        await firstLoadSignalsToggle.click();
        await expect(firstLoadSignalsToggle).toHaveAttribute('aria-expanded', 'true');
        await expect(firstLoadSignalsPanel).toBeVisible();
        const remountedAssetSyncAction = firstLoadSignalsPanel.getByTestId(`signal-sync-asset-${readySignalId}`);
        await expect(remountedAssetSyncAction).toBeDisabled();
        await expect(remountedAssetSyncAction.locator('svg')).toHaveClass(/animate-spin/);
        await remountedAssetSyncAction.evaluate((button) => {
            if (!(button instanceof HTMLButtonElement)) throw new Error('Comparison Asset sync control is not a button');
            button.click();
        });
        expect(assetSyncRequestCount).toBe(staleContextAssetSyncRequestsBefore + 1);
        expect(fxSyncRequestCount).toBe(staleContextFxSyncRequestsBefore + 1);

        const changedRangeRequest = await commitSyntheticRange(thirtyDayRange, true);
        assertMainDateRange(changedRangeRequest.postDataJSON(), thirtyDayRange);
        const changedContextCalendarResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const changedContextCalendarResponse = await changedContextCalendarResponsePromise;
        expect(changedContextCalendarResponse.ok()).toBe(true);
        expect(await changedContextCalendarResponse.finished()).toBeNull();
        assertCalendarBulkRequest(changedContextCalendarResponse.request().postDataJSON(), 30);
        assertMainDateRange(changedContextCalendarResponse.request().postDataJSON(), thirtyDayRange);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(dateRangeStartInput).toHaveValue(thirtyDayRange.start);
        await expect(dateRangeEndInput).toHaveValue(thirtyDayRange.end);
        await expect(chart).toHaveAttribute('data-calendar-range-days', String(thirtyDayRange.spanDays));
        await expectCalendarPeerDiagnostics();

        const staleCompletionPriceQueriesBefore = priceQueryRequestCount;
        const staleCompletionCalendarRequestsBefore = calendarRequestCount;
        const staleCompletionComparisonResponsesBefore = correctedPriceComparisonResponseCount;
        const staleCompletionFxConversionsBefore = fxConvertRequestCount;
        staleContextAssetSyncGate.release();
        staleContextFxSyncGate.release();

        const staleContextAssetResponse = await staleContextAssetResponsePromise;
        expect(staleContextAssetResponse.ok()).toBe(true);
        expect(await staleContextAssetResponse.finished()).toBeNull();
        expect(await staleContextAssetResponse.json()).toMatchObject({
            success_count: 1,
            results: [{asset_id: readyPeer.id, status: 'ok'}],
        });
        const staleContextFxResponse = await staleContextFxResponsePromise;
        expect(staleContextFxResponse.ok()).toBe(true);
        expect(await staleContextFxResponse.finished()).toBeNull();
        expect(await staleContextFxResponse.json()).toMatchObject({
            success_count: readyPeerRequiredFxSlugs.length,
            results: expectedFxSyncResults(readyPeerRequiredFxSlugs, 'partial'),
        });
        await expectFocusedAssetSyncIdle(readySignalId);
        expect(priceQueryRequestCount).toBe(staleCompletionPriceQueriesBefore);
        expect(calendarRequestCount).toBe(staleCompletionCalendarRequestsBefore);
        expect(correctedPriceComparisonResponseCount).toBe(staleCompletionComparisonResponsesBefore);
        expect(fxConvertRequestCount).toBe(staleCompletionFxConversionsBefore);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(dateRangeStartInput).toHaveValue(thirtyDayRange.start);
        await expect(dateRangeEndInput).toHaveValue(thirtyDayRange.end);
        await expect(chart).toHaveAttribute('data-calendar-range-days', String(thirtyDayRange.spanDays));
        await expectCalendarPeerDiagnostics();

        const restoreNinetyDayCalendarRequest = await commitSyntheticRange(ninetyDayRange, false);
        assertCalendarRequest(restoreNinetyDayCalendarRequest.postDataJSON(), 30);
        assertCalendarBulkRequest(restoreNinetyDayCalendarRequest.postDataJSON(), 30);
        assertMainDateRange(restoreNinetyDayCalendarRequest.postDataJSON(), ninetyDayRange);
        const restoreNinetyDayPriceComparisonPromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await pricePrimary.click();
        const restoreNinetyDayPriceComparison = await restoreNinetyDayPriceComparisonPromise;
        expect(restoreNinetyDayPriceComparison.ok()).toBe(true);
        expect(await restoreNinetyDayPriceComparison.finished()).toBeNull();
        assertPriceComparisonRequest(restoreNinetyDayPriceComparison.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expectCorrectedPriceComparisonState();

        // Retain a same-range Calendar chart request, return to Price, and
        // retain its local comparison too. With Asset accepted and FX failed,
        // the accepted leg must invalidate both old generations and start one
        // guarded Price chart successor followed by one forced local
        // comparison successor.
        const preAssetSyncPriceQueriesBefore = priceQueryRequestCount;
        const preAssetSyncMainPriceRequestsBefore = mainPriceRequestCount;
        const preAssetSyncComparisonRequestsBefore = priceComparisonRequestCount;
        const preAssetSyncCalendarRequestsBefore = calendarRequestCount;
        const preAssetSyncPriceComparisonGate = deferStalePriceComparisonResponse(ninetyDayRange, false);
        const preAssetSyncMainPriceResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const preAssetSyncPriceComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const preAssetSyncPriceComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await refreshButton.click();
        const preAssetSyncMainPriceResponse = await preAssetSyncMainPriceResponsePromise;
        expect(preAssetSyncMainPriceResponse.ok()).toBe(true);
        expect(await preAssetSyncMainPriceResponse.finished()).toBeNull();
        assertMainDateRange(preAssetSyncMainPriceResponse.request().postDataJSON(), ninetyDayRange);
        const preAssetSyncPriceComparisonRequest = await preAssetSyncPriceComparisonRequestPromise;
        assertPriceComparisonRequest(preAssetSyncPriceComparisonRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);

        const preAssetSyncChartGate = deferCalendarResponse(30, 'stale-sync');
        const preAssetSyncChartRequestPromise = waitForCalendarRequest(30);
        const preAssetSyncChartResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const preAssetSyncChartRequest = await preAssetSyncChartRequestPromise;
        assertCalendarBulkRequest(preAssetSyncChartRequest.postDataJSON(), 30);
        assertMainDateRange(preAssetSyncChartRequest.postDataJSON(), ninetyDayRange);

        await pricePrimary.click();
        await expect.poll(() => priceQueryRequestCount).toBe(preAssetSyncPriceQueriesBefore + 3);
        expect(mainPriceRequestCount).toBe(preAssetSyncMainPriceRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(preAssetSyncComparisonRequestsBefore + 1);
        expect(calendarRequestCount).toBe(preAssetSyncCalendarRequestsBefore + 1);
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expectCorrectedPriceComparisonState();

        nextAssetSyncStatus = 'ok';
        nextFxSyncStatus = 'failed';
        const assetSyncRequestsBefore = assetSyncRequestCount;
        const fxSyncRequestsBeforeAssetSync = fxSyncRequestCount;
        const priceQueriesBeforeAssetSync = priceQueryRequestCount;
        const mainPriceRequestsBeforeAssetSync = mainPriceRequestCount;
        const priceComparisonRequestsBeforeAssetSync = priceComparisonRequestCount;
        const calendarRequestsBeforeAssetSync = calendarRequestCount;
        const correctedPriceComparisonResponsesBeforeAssetSync = correctedPriceComparisonResponseCount;
        const fxConvertRequestsBeforeAssetSync = fxConvertRequestCount;
        const assetOnlySuccessorMainGate = deferNextMainPriceResponse();
        const assetOnlySuccessorMainRequestPromise = waitForMainPriceRequest(ninetyDayRange);
        const assetOnlySuccessorMainResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const assetOnlySuccessorComparisonGate = deferNextPriceComparisonResponse();
        const assetOnlySuccessorComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const assetOnlySuccessorComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        const assetSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const assetSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const assetFxSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const assetFxSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        await activateComparisonAssetSync(readySignalId);

        const assetSyncRequest = await assetSyncRequestPromise;
        assertAssetSyncRequest(assetSyncRequest.postDataJSON(), readyPeer.id, ninetyDayPriceSyncRange);
        const assetSyncResponse = await assetSyncResponsePromise;
        expect(assetSyncResponse.ok()).toBe(true);
        expect(await assetSyncResponse.finished()).toBeNull();
        expect(await assetSyncResponse.json()).toMatchObject({
            success_count: 1,
            results: [{asset_id: readyPeer.id, status: 'ok'}],
        });
        const assetFxSyncRequest = await assetFxSyncRequestPromise;
        expect(readyPeerRequiredFxSlugs).toEqual(['EUR-GBP', 'EUR-USD']);
        assertFxSyncRequest(assetFxSyncRequest.postDataJSON(), readyPeerRequiredFxSlugs, ninetyDayPriceSyncRange);
        const assetFxSyncResponse = await assetFxSyncResponsePromise;
        expect(assetFxSyncResponse.ok()).toBe(true);
        expect(await assetFxSyncResponse.finished()).toBeNull();
        expect(await assetFxSyncResponse.json()).toMatchObject({
            success_count: 0,
            results: expectedFxSyncResults(readyPeerRequiredFxSlugs, 'failed'),
        });
        await expect(page.getByTestId('toast-success')).toBeVisible();

        const assetOnlySuccessorMainRequest = await assetOnlySuccessorMainRequestPromise;
        assertMainDateRange(assetOnlySuccessorMainRequest.postDataJSON(), ninetyDayRange);
        expect(findCalendarSignal(assetOnlySuccessorMainRequest.postDataJSON())).toBeUndefined();
        expect(assetSyncRequestCount).toBe(assetSyncRequestsBefore + 1);
        expect(fxSyncRequestCount).toBe(fxSyncRequestsBeforeAssetSync + 1);
        expect(fxRouteMutationRequestCount).toBe(0);
        await expect.poll(() => priceQueryRequestCount).toBe(priceQueriesBeforeAssetSync + 1);
        expect(mainPriceRequestCount).toBe(mainPriceRequestsBeforeAssetSync + 1);
        expect(priceComparisonRequestCount).toBe(priceComparisonRequestsBeforeAssetSync);
        expect(calendarRequestCount).toBe(calendarRequestsBeforeAssetSync);
        expect(fxConvertRequestCount).toBe(fxConvertRequestsBeforeAssetSync);

        // Axis-only settings replace the persisted settings/signals objects
        // while the accepted coordinated sync is awaiting its guarded Price
        // successor. They are presentation state, so they must not stale the
        // sync or prevent that successor from publishing.
        await aestheticsToggle.click();
        await expect(aestheticsPanel).toBeVisible();
        const coordinatedAxisRow = aestheticsPanel.getByTestId('chart-axis-row-primary-absolute');
        await expect(coordinatedAxisRow).toBeVisible();
        await coordinatedAxisRow.getByTestId('chart-axis-primary-absolute-custom').click();
        const coordinatedAxisMin = coordinatedAxisRow.getByTestId('chart-axis-primary-absolute-min');
        const coordinatedAxisMax = coordinatedAxisRow.getByTestId('chart-axis-primary-absolute-max');
        await coordinatedAxisMin.fill('75');
        await expect(coordinatedAxisMin).toHaveValue('75');
        await coordinatedAxisMax.fill('250');
        await expect(coordinatedAxisMax).toHaveValue('250');
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                axisScales: {
                    absolute: {mode: 'custom', min: 75, max: 250},
                },
            });
        expect(priceQueryRequestCount).toBe(priceQueriesBeforeAssetSync + 1);
        expect(mainPriceRequestCount).toBe(mainPriceRequestsBeforeAssetSync + 1);
        expect(priceComparisonRequestCount).toBe(priceComparisonRequestsBeforeAssetSync);

        // Both retained responses complete while the guarded successor is
        // still pending. Their stale chart/events/diagnostics must not publish.
        preAssetSyncChartGate.release();
        preAssetSyncPriceComparisonGate.release();
        const preAssetSyncChartResponse = await preAssetSyncChartResponsePromise;
        expect(preAssetSyncChartResponse.ok()).toBe(true);
        expect(await preAssetSyncChartResponse.finished()).toBeNull();
        const preAssetSyncPriceComparisonResponse = await preAssetSyncPriceComparisonResponsePromise;
        expect(preAssetSyncPriceComparisonResponse.ok()).toBe(true);
        expect(await preAssetSyncPriceComparisonResponse.finished()).toBeNull();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expectCorrectedPriceComparisonState();
        expect(priceQueryRequestCount).toBe(priceQueriesBeforeAssetSync + 1);
        expect(mainPriceRequestCount).toBe(mainPriceRequestsBeforeAssetSync + 1);
        expect(priceComparisonRequestCount).toBe(priceComparisonRequestsBeforeAssetSync);
        expect(calendarRequestCount).toBe(calendarRequestsBeforeAssetSync);

        assetOnlySuccessorMainGate.release();
        const assetOnlySuccessorMainResponse = await assetOnlySuccessorMainResponsePromise;
        expect(assetOnlySuccessorMainResponse.ok()).toBe(true);
        expect(await assetOnlySuccessorMainResponse.finished()).toBeNull();
        assertMainDateRange(assetOnlySuccessorMainResponse.request().postDataJSON(), ninetyDayRange);
        const assetOnlySuccessorComparisonRequest = await assetOnlySuccessorComparisonRequestPromise;
        assertPriceComparisonRequest(assetOnlySuccessorComparisonRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => priceQueryRequestCount).toBe(priceQueriesBeforeAssetSync + 2);
        expect(mainPriceRequestCount).toBe(mainPriceRequestsBeforeAssetSync + 1);
        expect(priceComparisonRequestCount).toBe(priceComparisonRequestsBeforeAssetSync + 1);
        expect(calendarRequestCount).toBe(calendarRequestsBeforeAssetSync);
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        assetOnlySuccessorComparisonGate.release();
        const assetOnlySuccessorComparisonResponse = await assetOnlySuccessorComparisonResponsePromise;
        expect(assetOnlySuccessorComparisonResponse.ok()).toBe(true);
        expect(await assetOnlySuccessorComparisonResponse.finished()).toBeNull();
        assertPriceComparisonRequest(assetOnlySuccessorComparisonResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        expect(correctedPriceComparisonResponseCount).toBe(correctedPriceComparisonResponsesBeforeAssetSync + 1);
        expect(priceQueryRequestCount).toBe(priceQueriesBeforeAssetSync + 2);
        expect(mainPriceRequestCount).toBe(mainPriceRequestsBeforeAssetSync + 1);
        expect(priceComparisonRequestCount).toBe(priceComparisonRequestsBeforeAssetSync + 1);
        expect(calendarRequestCount).toBe(calendarRequestsBeforeAssetSync);
        expect(fxConvertRequestCount).toBe(fxConvertRequestsBeforeAssetSync);
        priceComparisonRaceActive = false;
        await expectCorrectedPriceComparisonState();
        await expect.poll(readChartComparisonLineLabels).toEqual(expect.arrayContaining(comparisonPeers.map((peer) => peer.display_name)));
        await expect(refreshButton).toBeEnabled();
        await coordinatedAxisRow.getByTestId('chart-axis-primary-absolute-auto').click();
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                axisScales: {
                    absolute: {mode: 'auto'},
                },
            });
        await aestheticsToggle.click();
        await expect(aestheticsPanel).toBeHidden();

        // Asset failed + FX accepted: retain same-range Calendar chart and
        // Price comparison work, accept the FX leg, and hold its first cache
        // refill. The accepted leg must invalidate both retained generations
        // before that await, so releasing the old payloads while the refill is
        // blocked cannot replace the current chart/comparison state.
        const fxOnlyPreSyncPriceQueriesBefore = priceQueryRequestCount;
        const fxOnlyPreSyncMainPriceRequestsBefore = mainPriceRequestCount;
        const fxOnlyPreSyncComparisonRequestsBefore = priceComparisonRequestCount;
        const fxOnlyPreSyncCalendarRequestsBefore = calendarRequestCount;
        const fxOnlyPreSyncComparisonGate = deferStalePriceComparisonResponse(ninetyDayRange, false);
        const fxOnlyPreSyncMainPriceResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const fxOnlyPreSyncComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const fxOnlyPreSyncComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await refreshButton.click();
        const fxOnlyPreSyncMainPriceResponse = await fxOnlyPreSyncMainPriceResponsePromise;
        expect(fxOnlyPreSyncMainPriceResponse.ok()).toBe(true);
        expect(await fxOnlyPreSyncMainPriceResponse.finished()).toBeNull();
        assertMainDateRange(fxOnlyPreSyncMainPriceResponse.request().postDataJSON(), ninetyDayRange);
        const fxOnlyPreSyncComparisonRequest = await fxOnlyPreSyncComparisonRequestPromise;
        assertPriceComparisonRequest(fxOnlyPreSyncComparisonRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);

        const fxOnlyPreSyncChartGate = deferCalendarResponse(30, 'stale-sync');
        const fxOnlyPreSyncChartRequestPromise = waitForCalendarRequest(30);
        const fxOnlyPreSyncChartResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const fxOnlyPreSyncChartRequest = await fxOnlyPreSyncChartRequestPromise;
        assertCalendarBulkRequest(fxOnlyPreSyncChartRequest.postDataJSON(), 30);

        await pricePrimary.click();
        await expect.poll(() => priceQueryRequestCount).toBe(fxOnlyPreSyncPriceQueriesBefore + 3);
        expect(mainPriceRequestCount).toBe(fxOnlyPreSyncMainPriceRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(fxOnlyPreSyncComparisonRequestsBefore + 1);
        expect(calendarRequestCount).toBe(fxOnlyPreSyncCalendarRequestsBefore + 1);
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');

        nextAssetSyncStatus = 'failed';
        nextFxSyncStatus = 'partial';
        const fxOnlyAssetSyncRequestsBefore = assetSyncRequestCount;
        const fxOnlyFxSyncRequestsBefore = fxSyncRequestCount;
        const fxOnlyPriceQueryRequestsBefore = priceQueryRequestCount;
        const fxOnlyMainPriceRequestsBefore = mainPriceRequestCount;
        const fxOnlyComparisonRequestsBefore = priceComparisonRequestCount;
        const fxOnlyCalendarRequestsBefore = calendarRequestCount;
        const fxOnlyCorrectedResponsesBefore = correctedPriceComparisonResponseCount;
        const fxOnlyConvertRequestsBefore = fxConvertRequestCount;
        const fxOnlyReadyRefillsBefore = fxRefillCounts.get(readyPeerFxSlug) ?? 0;
        const fxOnlyFirstRefillGate = deferFxRefillResponse(readyPeerFxSlug);
        const fxOnlyAssetSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const fxOnlyAssetSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const fxOnlyFxSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const fxOnlyFxSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        await activateComparisonAssetSync(readySignalId);

        const fxOnlyAssetSyncRequest = await fxOnlyAssetSyncRequestPromise;
        assertAssetSyncRequest(fxOnlyAssetSyncRequest.postDataJSON(), readyPeer.id, ninetyDayPriceSyncRange);
        const fxOnlyAssetSyncResponse = await fxOnlyAssetSyncResponsePromise;
        expect(fxOnlyAssetSyncResponse.ok()).toBe(true);
        expect(await fxOnlyAssetSyncResponse.finished()).toBeNull();
        expect(await fxOnlyAssetSyncResponse.json()).toMatchObject({
            success_count: 0,
            results: [{asset_id: readyPeer.id, status: 'failed'}],
        });

        const fxOnlyFxSyncRequest = await fxOnlyFxSyncRequestPromise;
        assertFxSyncRequest(fxOnlyFxSyncRequest.postDataJSON(), readyPeerRequiredFxSlugs, ninetyDayPriceSyncRange);
        const fxOnlyFxSyncResponse = await fxOnlyFxSyncResponsePromise;
        expect(fxOnlyFxSyncResponse.ok()).toBe(true);
        expect(await fxOnlyFxSyncResponse.finished()).toBeNull();
        expect(await fxOnlyFxSyncResponse.json()).toMatchObject({
            success_count: readyPeerRequiredFxSlugs.length,
            results: expectedFxSyncResults(readyPeerRequiredFxSlugs, 'partial'),
        });

        await expect.poll(() => fxRefillCounts.get(readyPeerFxSlug) ?? 0).toBe(fxOnlyReadyRefillsBefore + 1);
        fxOnlyPreSyncChartGate.release();
        fxOnlyPreSyncComparisonGate.release();
        const fxOnlyPreSyncChartResponse = await fxOnlyPreSyncChartResponsePromise;
        expect(fxOnlyPreSyncChartResponse.ok()).toBe(true);
        expect(await fxOnlyPreSyncChartResponse.finished()).toBeNull();
        const fxOnlyPreSyncComparisonResponse = await fxOnlyPreSyncComparisonResponsePromise;
        expect(fxOnlyPreSyncComparisonResponse.ok()).toBe(true);
        expect(await fxOnlyPreSyncComparisonResponse.finished()).toBeNull();
        await pricePrimary.focus();
        await expect(pricePrimary).toBeFocused();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect.poll(readChartEventMarkerAssetLabels).toContain(readyPeer.display_name);
        await expect.poll(readChartEventMarkerAssetLabels).not.toContain(partialPeer.display_name);
        await expectCorrectedPriceComparisonState();
        expect(priceQueryRequestCount).toBe(fxOnlyPriceQueryRequestsBefore);
        expect(mainPriceRequestCount).toBe(fxOnlyMainPriceRequestsBefore);
        expect(priceComparisonRequestCount).toBe(fxOnlyComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(fxOnlyCalendarRequestsBefore);

        const fxOnlySuccessorMainGate = deferNextMainPriceResponse();
        const fxOnlySuccessorMainRequestPromise = waitForMainPriceRequest(ninetyDayRange);
        const fxOnlySuccessorMainResponsePromise = waitForMainPriceResponse(ninetyDayRange);
        const fxOnlySuccessorComparisonGate = deferNextPriceComparisonResponse();
        const fxOnlyComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const fxOnlyComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        fxOnlyFirstRefillGate.release();
        const fxOnlySuccessorMainRequest = await fxOnlySuccessorMainRequestPromise;
        assertMainDateRange(fxOnlySuccessorMainRequest.postDataJSON(), ninetyDayRange);
        expect(findCalendarSignal(fxOnlySuccessorMainRequest.postDataJSON())).toBeUndefined();
        await expect.poll(() => priceQueryRequestCount).toBe(fxOnlyPriceQueryRequestsBefore + 1);
        expect(mainPriceRequestCount).toBe(fxOnlyMainPriceRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(fxOnlyComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(fxOnlyCalendarRequestsBefore);

        fxOnlySuccessorMainGate.release();
        const fxOnlySuccessorMainResponse = await fxOnlySuccessorMainResponsePromise;
        expect(fxOnlySuccessorMainResponse.ok()).toBe(true);
        expect(await fxOnlySuccessorMainResponse.finished()).toBeNull();
        assertMainDateRange(fxOnlySuccessorMainResponse.request().postDataJSON(), ninetyDayRange);
        const fxOnlyComparisonRequest = await fxOnlyComparisonRequestPromise;
        assertPriceComparisonRequest(fxOnlyComparisonRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => priceQueryRequestCount).toBe(fxOnlyPriceQueryRequestsBefore + 2);
        expect(mainPriceRequestCount).toBe(fxOnlyMainPriceRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(fxOnlyComparisonRequestsBefore + 1);
        expect(calendarRequestCount).toBe(fxOnlyCalendarRequestsBefore);
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        fxOnlySuccessorComparisonGate.release();
        const fxOnlyComparisonResponse = await fxOnlyComparisonResponsePromise;
        expect(fxOnlyComparisonResponse.ok()).toBe(true);
        expect(await fxOnlyComparisonResponse.finished()).toBeNull();
        assertPriceComparisonRequest(fxOnlyComparisonResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        expect(assetSyncRequestCount).toBe(fxOnlyAssetSyncRequestsBefore + 1);
        expect(fxSyncRequestCount).toBe(fxOnlyFxSyncRequestsBefore + 1);
        expect(fxRouteMutationRequestCount).toBe(0);
        expect(priceQueryRequestCount).toBe(fxOnlyPriceQueryRequestsBefore + 2);
        expect(mainPriceRequestCount).toBe(fxOnlyMainPriceRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(fxOnlyComparisonRequestsBefore + 1);
        expect(calendarRequestCount).toBe(fxOnlyCalendarRequestsBefore);
        expect(correctedPriceComparisonResponseCount).toBe(fxOnlyCorrectedResponsesBefore + 1);
        expect(fxConvertRequestCount).toBe(fxOnlyConvertRequestsBefore + readyPeerRequiredFxSlugs.length);
        priceComparisonRaceActive = false;

        await expect.poll(readChartComparisonLineLabels).toEqual(expect.arrayContaining(comparisonPeers.map((peer) => peer.display_name)));
        await expectCorrectedPriceComparisonState();
        const restoreAfterFxOnlyCalendarResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const restoreAfterFxOnlyCalendarResponse = await restoreAfterFxOnlyCalendarResponsePromise;
        expect(restoreAfterFxOnlyCalendarResponse.ok()).toBe(true);
        expect(await restoreAfterFxOnlyCalendarResponse.finished()).toBeNull();
        assertCalendarBulkRequest(restoreAfterFxOnlyCalendarResponse.request().postDataJSON(), 30);
        const restoreAfterFxOnlyPriceQueries = priceQueryRequestCount;
        const restoreAfterFxOnlyComparisonRequests = priceComparisonRequestCount;
        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await pricePrimary.focus();
        await expect(pricePrimary).toBeFocused();
        expect(priceQueryRequestCount).toBe(restoreAfterFxOnlyPriceQueries);
        expect(priceComparisonRequestCount).toBe(restoreAfterFxOnlyComparisonRequests);
        await expectCorrectedPriceComparisonState();
        await expectFocusedAssetSyncIdle(readySignalId);

        // Standalone generations are keyed by slug, not globally. Recreate
        // two independently actionable comparison failures in the unchanged
        // ninety-day Price context, start both syncs, and resolve CHF before GBP. The CHF
        // completion must refill, reload, and publish while GBP is still
        // pending; then GBP must do the same without erasing the CHF line.
        missingFxConversionSlugs.clear();
        missingFxConversionSlugs.add(readyPeerFxSlug);
        missingFxConversionSlugs.add(errorPeerFxSlug);
        const twoSlugInitialComparisonsBefore = priceComparisonRequestCount;
        const twoSlugInitialGate = deferNextPriceComparisonResponse();
        const twoSlugInitialMainPromise = waitForMainRangeResponse(ninetyDayRange);
        const twoSlugInitialComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
        const twoSlugInitialComparisonPromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await refreshButton.click();
        const twoSlugInitialMain = await twoSlugInitialMainPromise;
        expect(twoSlugInitialMain.ok()).toBe(true);
        expect(await twoSlugInitialMain.finished()).toBeNull();
        assertMainDateRange(twoSlugInitialMain.request().postDataJSON(), ninetyDayRange);
        const twoSlugInitialComparisonRequest = await twoSlugInitialComparisonRequestPromise;
        assertPriceComparisonRequest(twoSlugInitialComparisonRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => priceComparisonRequestCount).toBe(twoSlugInitialComparisonsBefore + 1);
        twoSlugInitialGate.release();
        const twoSlugInitialComparison = await twoSlugInitialComparisonPromise;
        expect(twoSlugInitialComparison.ok()).toBe(true);
        expect(await twoSlugInitialComparison.finished()).toBeNull();
        assertPriceComparisonRequest(twoSlugInitialComparison.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        const twoSlugInitialPayload = (await twoSlugInitialComparison.json()) as {
            items?: Array<{asset_id?: number; prices?: Array<{currency?: string}>; errors?: unknown[]}>;
        };
        for (const [peerId, currency, slug] of [
            [readyPeer.id, readyPeer.currency, readyPeerFxSlug],
            [errorPeer.id, errorPeer.currency, errorPeerFxSlug],
        ] as const) {
            const item = twoSlugInitialPayload.items?.find((candidate) => candidate.asset_id === peerId);
            expect(item, `comparison response must contain peer ${peerId}`).toBeDefined();
            expect(item?.prices).toHaveLength(pricePoints.length);
            expect(new Set(item?.prices?.map((point) => point.currency))).toEqual(new Set([currency]));
            expect(item?.errors).toEqual([`synthetic-price-conversion-failure-${slug}`]);
        }
        await expect(readyFxSyncAction).toBeVisible();
        await expect(errorFxSyncAction).toBeVisible();
        await expect(readyFxSyncAction).toBeEnabled();
        await expect(errorFxSyncAction).toBeEnabled();

        const readySlugSyncGate = deferFxSyncResponse(readyPeerFxSlug, 'partial');
        const errorSlugSyncGate = deferFxSyncResponse(errorPeerFxSlug, 'ok');
        const readySlugSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync' && matchesSingleFxSyncRequest(request.postDataJSON(), readyPeerFxSlug), {timeout: 10_000});
        const errorSlugSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync' && matchesSingleFxSyncRequest(request.postDataJSON(), errorPeerFxSlug), {timeout: 10_000});
        const readySlugSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync' && matchesSingleFxSyncRequest(response.request().postDataJSON(), readyPeerFxSlug), {timeout: 10_000});
        const errorSlugSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync' && matchesSingleFxSyncRequest(response.request().postDataJSON(), errorPeerFxSlug), {timeout: 10_000});
        await readyFxSyncAction.focus();
        await expect(readyFxSyncAction).toBeFocused();
        await readyFxSyncAction.press('Enter');
        await errorFxSyncAction.focus();
        await expect(errorFxSyncAction).toBeFocused();
        await errorFxSyncAction.press('Enter');
        const readySlugSyncRequest = await readySlugSyncRequestPromise;
        const errorSlugSyncRequest = await errorSlugSyncRequestPromise;
        assertFxSyncRequest(readySlugSyncRequest.postDataJSON(), [readyPeerFxSlug], ninetyDayRange);
        assertFxSyncRequest(errorSlugSyncRequest.postDataJSON(), [errorPeerFxSlug], ninetyDayRange);

        const errorSlugRefillsBefore = fxRefillCounts.get(errorPeerFxSlug) ?? 0;
        const errorSlugMainReloadPromise = waitForMainRangeResponse(ninetyDayRange);
        const errorSlugComparisonReloadPromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        errorSlugSyncGate.release();
        const errorSlugSyncResponse = await errorSlugSyncResponsePromise;
        expect(errorSlugSyncResponse.ok()).toBe(true);
        expect(await errorSlugSyncResponse.finished()).toBeNull();
        expect(await errorSlugSyncResponse.json()).toMatchObject({
            success_count: 1,
            results: [{pair: errorPeerFxSlug, status: 'ok'}],
        });
        const errorSlugMainReload = await errorSlugMainReloadPromise;
        expect(errorSlugMainReload.ok()).toBe(true);
        expect(await errorSlugMainReload.finished()).toBeNull();
        assertMainDateRange(errorSlugMainReload.request().postDataJSON(), ninetyDayRange);
        const errorSlugComparisonReload = await errorSlugComparisonReloadPromise;
        expect(errorSlugComparisonReload.ok()).toBe(true);
        expect(await errorSlugComparisonReload.finished()).toBeNull();
        assertPriceComparisonRequest(errorSlugComparisonReload.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => fxRefillCounts.get(errorPeerFxSlug) ?? 0).toBe(errorSlugRefillsBefore + 1);
        await expect.poll(readChartComparisonLineLabels).toContain(errorPeer.display_name);
        await expect(errorFxSyncAction).toHaveCount(0);
        await expect(readyFxSyncAction).toBeVisible();
        expect(missingFxConversionSlugs).toEqual(new Set([readyPeerFxSlug]));

        const readySlugRefillsBefore = fxRefillCounts.get(readyPeerFxSlug) ?? 0;
        const readySlugMainReloadPromise = waitForMainRangeResponse(ninetyDayRange);
        const readySlugComparisonReloadPromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        readySlugSyncGate.release();
        const readySlugSyncResponse = await readySlugSyncResponsePromise;
        expect(readySlugSyncResponse.ok()).toBe(true);
        expect(await readySlugSyncResponse.finished()).toBeNull();
        expect(await readySlugSyncResponse.json()).toMatchObject({
            success_count: 1,
            results: [{pair: readyPeerFxSlug, status: 'partial'}],
        });
        const readySlugMainReload = await readySlugMainReloadPromise;
        expect(readySlugMainReload.ok()).toBe(true);
        expect(await readySlugMainReload.finished()).toBeNull();
        assertMainDateRange(readySlugMainReload.request().postDataJSON(), ninetyDayRange);
        const readySlugComparisonReload = await readySlugComparisonReloadPromise;
        expect(readySlugComparisonReload.ok()).toBe(true);
        expect(await readySlugComparisonReload.finished()).toBeNull();
        assertPriceComparisonRequest(readySlugComparisonReload.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expect.poll(() => fxRefillCounts.get(readyPeerFxSlug) ?? 0).toBe(readySlugRefillsBefore + 1);
        await expect.poll(readChartComparisonLineLabels).toEqual(expect.arrayContaining([readyPeer.display_name, errorPeer.display_name]));
        await expect(readyFxSyncAction).toHaveCount(0);
        await expect(errorFxSyncAction).toHaveCount(0);
        expect(missingFxConversionSlugs).toEqual(new Set());
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(dateRangeStartInput).toHaveValue(ninetyDayRange.start);
        await expect(dateRangeEndInput).toHaveValue(ninetyDayRange.end);
        await expectCorrectedPriceComparisonState();

        await test.step('I60H new Calendar fingerprint reloads matching Price authority when shared event runtime is absent', async () => {
            const expectedOwnedPriceLineLabels = comparisonPeers.map((peer) => peer.display_name).sort();
            await expect(chart).toHaveAttribute('data-primary-mode', 'price');
            await expectCorrectedPriceComparisonState();
            for (const card of [readySignalCard, partialSignalCard, unavailableSignalCard, failedSignalCard, invalidCalendarSignalCard]) {
                await expect(card.getByTestId('signal-loading')).toHaveCount(0);
                await expect(card.getByRole('button', {name: '📈3', exact: true})).toBeVisible();
            }
            await expect(readySignalCard.getByRole('button', {name: '💰2', exact: true})).toBeVisible();
            await expect.poll(readChartComparisonLineLabels).toEqual(expectedOwnedPriceLineLabels);
            await expect.poll(readChartEventMarkerAssetLabels).toEqual([readyPeer.display_name]);
            await expect(readySignalCard.getByTestId(`signal-fx-detail-${readySignalId}`)).toBeVisible();
            await expect(requiredFxIssues).toHaveCount(0);

            const currentCalendarResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            await calendarPrimary.click();
            const currentCalendarResponse = await currentCalendarResponsePromise;
            expect(currentCalendarResponse.ok()).toBe(true);
            expect(await currentCalendarResponse.finished()).toBeNull();
            assertCalendarBulkRequest(currentCalendarResponse.request().postDataJSON(), 30);
            assertMainDateRange(currentCalendarResponse.request().postDataJSON(), ninetyDayRange);
            await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
            await expect(chart).toHaveAttribute('data-window-days', '30');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');

            const heldNewCalendarFingerprint = deferCalendarResponse(90, 'ready');
            const heldCalendarRequestPromise = waitForCalendarRequestForRange(90, ninetyDayRange);
            const heldCalendarResponsePromise = waitForCalendarResponseForRange(90, ninetyDayRange);
            await chart.getByTestId('asset-calendar-window-3m').click();
            const heldCalendarRequest = await heldCalendarRequestPromise;
            assertCalendarBulkRequest(heldCalendarRequest.postDataJSON(), 90);
            assertMainDateRange(heldCalendarRequest.postDataJSON(), ninetyDayRange);
            await expect(chart).toHaveAttribute('data-window-days', '90');
            await expect(chart).toHaveAttribute('data-series-state', 'loading');
            await expect(chart).toHaveAttribute('data-calendar-comparison-ready', '');
            await expect(chart).toHaveAttribute('data-calendar-comparison-partial', '');
            await expect(chart).toHaveAttribute('data-calendar-comparison-unavailable', '');
            await expect(chart).toHaveAttribute('data-calendar-comparison-error', '');
            await expect.poll(readPersistedPriceComparisonRuntimeMarkers).toEqual(expectedPriceComparisonRuntimeMarkers);
            await expect(readySignalCard.getByRole('button', {name: '💰2', exact: true})).toHaveCount(0);
            await expect.poll(readChartEventMarkerAssetLabels).toEqual([]);

            const comparisonRangeKey = `${ninetyDayRange.start}|${ninetyDayRange.end}`;
            const priceQueriesBeforeReturn = priceQueryRequestCount;
            const mainRequestsBeforeReturn = mainPriceRequestCount;
            const comparisonRequestsBeforeReturn = priceComparisonRequestCount;
            const rangeRequestsBeforeReturn = priceComparisonRequestCountsByRange.get(comparisonRangeKey) ?? 0;
            const calendarRequestsBeforeReturn = calendarRequestCount;
            const correctedResponsesBeforeReturn = correctedPriceComparisonResponseCount;
            const priceReloadRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, ninetyDayRange, asset.currency);
            const priceReloadResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
            await pricePrimary.click();
            const priceReloadRequest = await priceReloadRequestPromise;
            assertPriceComparisonRequest(priceReloadRequest.postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
            const priceReloadResponse = await priceReloadResponsePromise;
            expect(priceReloadResponse.request()).toBe(priceReloadRequest);
            expect(priceReloadResponse.ok()).toBe(true);
            expect(await priceReloadResponse.finished()).toBeNull();
            assertPriceComparisonRequest(priceReloadResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
            await expect(chart).toHaveAttribute('data-primary-mode', 'price');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');
            await expectCorrectedPriceComparisonState();
            await expect.poll(readChartComparisonLineLabels).toEqual(expectedOwnedPriceLineLabels);
            await expect.poll(readChartEventMarkerAssetLabels).toEqual([readyPeer.display_name]);
            await expect.poll(readPersistedPriceComparisonRuntimeMarkers).toEqual(expectedPriceComparisonRuntimeMarkers);
            expect(priceQueryRequestCount).toBe(priceQueriesBeforeReturn + 1);
            expect(mainPriceRequestCount).toBe(mainRequestsBeforeReturn);
            expect(priceComparisonRequestCount).toBe(comparisonRequestsBeforeReturn + 1);
            expect(priceComparisonRequestCountsByRange.get(comparisonRangeKey) ?? 0).toBe(rangeRequestsBeforeReturn + 1);
            expect(calendarRequestCount).toBe(calendarRequestsBeforeReturn);
            expect(correctedPriceComparisonResponseCount).toBe(correctedResponsesBeforeReturn + 1);

            heldNewCalendarFingerprint.release();
            const heldCalendarResponse = await heldCalendarResponsePromise;
            expect(heldCalendarResponse.ok()).toBe(true);
            expect(await heldCalendarResponse.finished()).toBeNull();
            expect(heldCalendarResponse.request()).toBe(heldCalendarRequest);
            assertCalendarBulkRequest(heldCalendarResponse.request().postDataJSON(), 90);
            assertMainDateRange(heldCalendarResponse.request().postDataJSON(), ninetyDayRange);
            await expect(chart).toHaveAttribute('data-primary-mode', 'price');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');
            await expectCorrectedPriceComparisonState();
            await expect.poll(readChartComparisonLineLabels).toEqual(expectedOwnedPriceLineLabels);
            await expect.poll(readChartEventMarkerAssetLabels).toEqual([readyPeer.display_name]);
            await expect.poll(readPersistedPriceComparisonRuntimeMarkers).toEqual(expectedPriceComparisonRuntimeMarkers);
            expect(priceComparisonRequestCount).toBe(comparisonRequestsBeforeReturn + 1);
            expect(priceComparisonRequestCountsByRange.get(comparisonRangeKey) ?? 0).toBe(rangeRequestsBeforeReturn + 1);
            expect(correctedPriceComparisonResponseCount).toBe(correctedResponsesBeforeReturn + 1);

            const restoreNinetyDayCalendarResponsePromise = waitForCalendarResponseForRange(90, ninetyDayRange);
            await calendarPrimary.click();
            const restoreNinetyDayCalendarResponse = await restoreNinetyDayCalendarResponsePromise;
            expect(restoreNinetyDayCalendarResponse.ok()).toBe(true);
            expect(await restoreNinetyDayCalendarResponse.finished()).toBeNull();
            assertCalendarBulkRequest(restoreNinetyDayCalendarResponse.request().postDataJSON(), 90);
            assertMainDateRange(restoreNinetyDayCalendarResponse.request().postDataJSON(), ninetyDayRange);

            const restoreThirtyDayCalendarResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            await chart.getByTestId('asset-calendar-window-1m').click();
            const restoreThirtyDayCalendarResponse = await restoreThirtyDayCalendarResponsePromise;
            expect(restoreThirtyDayCalendarResponse.ok()).toBe(true);
            expect(await restoreThirtyDayCalendarResponse.finished()).toBeNull();
            assertCalendarBulkRequest(restoreThirtyDayCalendarResponse.request().postDataJSON(), 30);
            assertMainDateRange(restoreThirtyDayCalendarResponse.request().postDataJSON(), ninetyDayRange);
            await expect(chart).toHaveAttribute('data-window-days', '30');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');

            const comparisonRequestsBeforeRestoredPrice = priceComparisonRequestCount;
            const rangeRequestsBeforeRestoredPrice = priceComparisonRequestCountsByRange.get(comparisonRangeKey) ?? 0;
            await pricePrimary.click();
            await expect(chart).toHaveAttribute('data-primary-mode', 'price');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');
            await pricePrimary.focus();
            await expect(pricePrimary).toBeFocused();
            expect(priceComparisonRequestCount).toBe(comparisonRequestsBeforeRestoredPrice);
            expect(priceComparisonRequestCountsByRange.get(comparisonRangeKey) ?? 0).toBe(rangeRequestsBeforeRestoredPrice);
            await expectCorrectedPriceComparisonState();
            await expect.poll(readPersistedPriceComparisonRuntimeMarkers).toEqual(expectedPriceComparisonRuntimeMarkers);
        });

        await test.step('I60H malformed unavailable drops stale peer while typed unavailable retains factual peer line', async () => {
            const enterCalendarResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            await calendarPrimary.click();
            const enterCalendarResponse = await enterCalendarResponsePromise;
            expect(enterCalendarResponse.ok()).toBe(true);
            expect(await enterCalendarResponse.finished()).toBeNull();
            assertCalendarBulkRequest(enterCalendarResponse.request().postDataJSON(), 30);
            assertMainDateRange(enterCalendarResponse.request().postDataJSON(), ninetyDayRange);
            await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
            await expect(chart).toHaveAttribute('data-window-days', '30');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');

            const factualSnapshot = await readI60GCalendarChart();
            const factualTypedPeerValues = factualSnapshot.peers[readyPeer.display_name];
            const factualMalformedPeerValues = factualSnapshot.peers[partialPeer.display_name];
            expect(factualSnapshot.presentPeerLabels).toEqual(expect.arrayContaining([readyPeer.display_name, partialPeer.display_name]));
            expect(factualTypedPeerValues, `Calendar chart must begin with factual values for typed-unavailable peer ${readyPeer.id}`).toBeDefined();
            expect(factualTypedPeerValues?.some((value) => value !== null)).toBe(true);
            expect(factualMalformedPeerValues, `Calendar chart must begin with factual values for malformed-unavailable peer ${partialPeer.id}`).toBeDefined();
            expect(factualMalformedPeerValues?.some((value) => value !== null)).toBe(true);

            const unavailableContractGate = deferCalendarResponse(30, 'i60h-peer-unavailable-contract');
            const unavailableContractRequestPromise = waitForCalendarRequestForRange(30, ninetyDayRange);
            const unavailableContractResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            const calendarRequestsBeforeUnavailableContract = calendarRequestCount;
            await refreshButton.click();
            const unavailableContractRequest = await unavailableContractRequestPromise;
            assertCalendarBulkRequest(unavailableContractRequest.postDataJSON(), 30);
            assertMainDateRange(unavailableContractRequest.postDataJSON(), ninetyDayRange);
            expect(calendarRequestCount).toBe(calendarRequestsBeforeUnavailableContract + 1);
            await expect(chart).toHaveAttribute('data-series-state', 'loading');

            unavailableContractGate.release();
            const unavailableContractResponse = await unavailableContractResponsePromise;
            expect(unavailableContractResponse.ok()).toBe(true);
            expect(await unavailableContractResponse.finished()).toBeNull();
            expect(unavailableContractResponse.request()).toBe(unavailableContractRequest);
            const unavailableContractPayload = (await unavailableContractResponse.json()) as {
                items?: Array<{asset_id?: number; signals?: unknown[]}>;
            };
            const typedUnavailableResult = unavailableContractPayload.items?.find((item) => item.asset_id === readyPeer.id)?.signals?.find((signal) => signal !== null && typeof signal === 'object' && (signal as Record<string, unknown>).instance_id === calendarInstanceId);
            const malformedUnavailableResult = unavailableContractPayload.items?.find((item) => item.asset_id === partialPeer.id)?.signals?.find((signal) => signal !== null && typeof signal === 'object' && (signal as Record<string, unknown>).instance_id === calendarInstanceId);
            expect(typedUnavailableResult, `Calendar response must contain typed-unavailable peer ${readyPeer.id}`).toBeDefined();
            expect(malformedUnavailableResult, `Calendar response must contain malformed-unavailable peer ${partialPeer.id}`).toBeDefined();
            expect(schemas.SignalResult.safeParse(typedUnavailableResult).success).toBe(true);
            expect(schemas.SignalResult.safeParse(malformedUnavailableResult).success).toBe(false);

            await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
            await expect(chart).toHaveAttribute('data-window-days', '30');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');
            await expect(chart).toHaveAttribute('data-calendar-comparison-ready', String(readyPeer.id));
            await expect(chart).toHaveAttribute('data-calendar-comparison-partial', '');
            await expect(chart).toHaveAttribute('data-calendar-comparison-unavailable', String(unavailablePeer.id));
            await expect(chart).toHaveAttribute('data-calendar-comparison-error', [partialPeer.id, errorPeer.id, invalidCalendarPeer.id].sort((left, right) => left - right).join(','));
            await expect(readySignalCard.getByTestId('signal-issue')).toHaveAttribute('data-problem-code', 'insufficient_history');
            await expect(partialSignalCard.getByTestId('signal-issue')).toHaveAttribute('data-problem-code', 'result_missing');
            await expect
                .poll(async () => {
                    const current = await readI60GCalendarChart();
                    return {
                        typedPresent: current.presentPeerLabels.includes(readyPeer.display_name),
                        typedValues: current.peers[readyPeer.display_name],
                        malformedPresent: current.presentPeerLabels.includes(partialPeer.display_name),
                        malformedValues: current.peers[partialPeer.display_name],
                    };
                })
                .toEqual({
                    typedPresent: true,
                    typedValues: factualTypedPeerValues,
                    malformedPresent: false,
                    malformedValues: factualSnapshot.dates.map(() => null),
                });

            const restoreCalendarResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            await refreshButton.click();
            const restoreCalendarResponse = await restoreCalendarResponsePromise;
            expect(restoreCalendarResponse.ok()).toBe(true);
            expect(await restoreCalendarResponse.finished()).toBeNull();
            assertCalendarBulkRequest(restoreCalendarResponse.request().postDataJSON(), 30);
            assertMainDateRange(restoreCalendarResponse.request().postDataJSON(), ninetyDayRange);
            await expectCalendarPeerDiagnostics();

            const comparisonRequestsBeforeRestoredPrice = priceComparisonRequestCount;
            await pricePrimary.click();
            await expect(chart).toHaveAttribute('data-primary-mode', 'price');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');
            expect(priceComparisonRequestCount).toBe(comparisonRequestsBeforeRestoredPrice);
            await expectCorrectedPriceComparisonState();
        });

        const i60hNoDataIssues = page.getByTestId('data-quality-issue-FX_PAIR_NO_DATA');
        const i60hReadySignalIssue = readySignalCard.getByTestId('signal-issue');
        const stableRequestJson = (value: unknown) =>
            JSON.stringify(value, (_key, nested) => {
                if (nested === null || typeof nested !== 'object' || Array.isArray(nested)) return nested;
                return Object.fromEntries(Object.entries(nested as Record<string, unknown>).sort(([left], [right]) => left.localeCompare(right)));
            });
        const ownedI60HCalendarRequestBody = (expectedPeerIds: readonly number[], mainIncludePrice: boolean): PriceQueryRequest[] => {
            const calendarSignal = {
                instance_id: calendarInstanceId,
                signal_code: calendarSignalCode,
                params: {window_days: 30},
            };
            return [
                {
                    asset_id: assetId,
                    date_range: {start: ninetyDayRange.start, end: ninetyDayRange.end},
                    include_price: mainIncludePrice,
                    include_events: true,
                    signals: [calendarSignal],
                },
                ...expectedPeerIds.map((peerId) => ({
                    asset_id: peerId,
                    date_range: {start: ninetyDayRange.start, end: ninetyDayRange.end},
                    include_price: false,
                    include_events: true,
                    target_currency: asset.currency,
                    signals: [calendarSignal],
                })),
            ];
        };
        const armOwnedI60HCalendarExchange = (expectedPeerIds: readonly number[], expectedMainIncludePrice?: boolean) => {
            const requestPromise = page.waitForRequest(
                (request) => {
                    if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                    const body = request.postDataJSON();
                    const mainIncludePrice = expectedMainIncludePrice ?? parseQueries(body).find((query) => query.asset_id === assetId)?.include_price;
                    return typeof mainIncludePrice === 'boolean' && stableRequestJson(body) === stableRequestJson(ownedI60HCalendarRequestBody(expectedPeerIds, mainIncludePrice));
                },
                {timeout: 10_000},
            );
            const responsePromise = page.waitForResponse(async (response) => response.request() === (await requestPromise), {timeout: 10_000});
            return Promise.all([requestPromise, responsePromise]).then(([request, response]) => ({request, response}));
        };
        const selectOwnedI60HCalendarPeer = async (targetPeerId: number, expectedPeerIds: readonly number[]): Promise<void> => {
            const exchangePromise = armOwnedI60HCalendarExchange(expectedPeerIds);
            await selectComparisonAsset(readySignalId, targetPeerId);
            const {request, response} = await exchangePromise;
            expect(response.request()).toBe(request);
            expect(response.ok()).toBe(true);
            expect(await response.finished()).toBeNull();
            assertCalendarBulkRequest(request.postDataJSON(), 30, expectedPeerIds);
            assertMainDateRange(request.postDataJSON(), ninetyDayRange);
            await expect.poll(readPersistedReadyPeerId).toBe(String(targetPeerId));
            await expect(pageRoot).toHaveAttribute('data-busy', 'false');
            await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
            await expect(chart).toHaveAttribute('data-window-days', '30');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');
            await expect(chart).toHaveAttribute('data-calendar-comparison-ready', String(targetPeerId));
        };
        const seedCurrentI60HCalendarFailure = async (): Promise<void> => {
            exposeMissingComparisonEventRoutes = false;
            missingFxConversionSlugs.clear();
            calendarConversionGapErrors = null;

            await expect(pageRoot).toHaveAttribute('data-busy', 'false');
            await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
            await expect(chart).toHaveAttribute('data-window-days', '30');
            await expect(dateRangeStartInput).toHaveValue(ninetyDayRange.start);
            await expect(dateRangeEndInput).toHaveValue(ninetyDayRange.end);
            await expect.poll(readPersistedReadyPeerId).toEqual(expect.any(String));
            if ((await readPersistedReadyPeerId()) === String(readyPeer.id)) {
                await selectOwnedI60HCalendarPeer(replacementPeer.id, replacementPeerIds);
            }
            await selectOwnedI60HCalendarPeer(readyPeer.id, comparisonPeerIds);
            await expect(chart).toHaveAttribute('data-calendar-comparison-ready', String(readyPeer.id));
            await expect
                .poll(async () => {
                    const current = await readI60GCalendarChart();
                    return {
                        present: current.presentPeerLabels.includes(readyPeer.display_name),
                        hasValues: current.peers[readyPeer.display_name]?.some((value) => value !== null) === true,
                    };
                })
                .toEqual({present: true, hasValues: true});

            exposeMissingComparisonEventRoutes = true;
            missingFxConversionSlugs.clear();
            missingFxConversionSlugs.add(readyPeerEventFxSlug);
            calendarConversionGapErrors = [readyPeerConversionError];

            const exchangePromise = armOwnedI60HCalendarExchange(comparisonPeerIds, true);
            await refreshButton.click();
            const {request, response} = await exchangePromise;
            expect(response.request()).toBe(request);
            expect(response.ok()).toBe(true);
            expect(await response.finished()).toBeNull();
            expect(request.postDataJSON()).toEqual(ownedI60HCalendarRequestBody(comparisonPeerIds, true));
            assertCalendarBulkRequest(request.postDataJSON(), 30);
            assertMainDateRange(request.postDataJSON(), ninetyDayRange);
            const payload = (await response.json()) as {
                items?: Array<{
                    asset_id?: number;
                    errors?: unknown[];
                    signals?: Array<{instance_id?: string; signal_code?: string; status?: string; availability?: {reason_code?: string | null}}>;
                }>;
            };
            const readyPeerItem = payload.items?.find((item) => item.asset_id === readyPeer.id);
            expect(readyPeerItem, `same-fingerprint Calendar response must contain owned peer ${readyPeer.id}`).toBeDefined();
            expect(readyPeerItem?.errors).toEqual([readyPeerConversionError]);
            expect(readyPeerItem?.signals?.find((signal) => signal.instance_id === calendarInstanceId && signal.signal_code === calendarSignalCode)).toMatchObject({
                status: 'unavailable',
                availability: {reason_code: 'missing_input_fields'},
            });

            await expect(i60hNoDataIssues).toHaveCount(2);
            await expect(i60hReadySignalIssue).toBeVisible();
            await expect(i60hReadySignalIssue).toHaveAttribute('data-problem-code', 'fx_conversion_unavailable');
            await expect(i60hReadySignalIssue).toHaveAttribute('data-severity', 'error');
            await expect(pageRoot).toHaveAttribute('data-busy', 'false');
            await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
            await expect(chart).toHaveAttribute('data-window-days', '30');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');
            await expectAssetDetailChartCanvas(page);
            await expect
                .poll(async () => {
                    const current = await readI60GCalendarChart();
                    return {
                        present: current.presentPeerLabels.includes(readyPeer.display_name),
                        hasValues: current.peers[readyPeer.display_name]?.some((value) => value !== null) === true,
                    };
                })
                .toEqual({present: true, hasValues: true});
            const snapshot = await readI60GCalendarChart();
            expect(snapshot.dates.length).toBeGreaterThan(0);
            expect(snapshot.main.some((value) => value !== null)).toBe(true);
            expect(snapshot.presentPeerLabels).toContain(readyPeer.display_name);
            const readyPeerValues = snapshot.peers[readyPeer.display_name];
            expect(readyPeerValues, `Calendar chart must own a series slot for peer ${readyPeer.id}`).toBeDefined();
            expect(readyPeerValues?.some((value) => value !== null)).toBe(true);
            await expect.poll(readChartEventMarkerAssetLabels).toEqual([]);
        };
        const beginAcceptedI60HCalendarSync = async (outcome: Extract<DeferredCalendarOutcome, 'i60h-query-rejected' | 'i60h-main-omitted'>) => {
            const calendarGate = deferCalendarResponse(30, outcome);
            const calendarRequestsBefore = calendarRequestCount;
            nextAssetSyncStatus = 'ok';
            nextFxSyncStatusesBySlug = new Map([
                [readyPeerFxSlug, 'ok'],
                [readyPeerEventFxSlug, 'partial'],
            ]);
            clearCalendarConversionGapOnAcceptedReadyRoutes = true;

            const assetRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
            const assetResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
            const fxRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
            const fxResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
            const calendarRequestPromise = waitForCalendarRequestForRange(30, ninetyDayRange);
            const calendarResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            await activateComparisonAssetSync(readySignalId);

            const assetRequest = await assetRequestPromise;
            const fxRequest = await fxRequestPromise;
            assertAssetSyncRequest(assetRequest.postDataJSON(), readyPeer.id, ninetyDayCalendarSyncRange);
            assertFxSyncRequest(fxRequest.postDataJSON(), readyPeerRequiredFxSlugs, ninetyDayCalendarSyncRange);

            const assetResponse = await assetResponsePromise;
            expect(assetResponse.ok()).toBe(true);
            expect(await assetResponse.finished()).toBeNull();
            expect(await assetResponse.json()).toMatchObject({
                success_count: 1,
                results: [{asset_id: readyPeer.id, status: 'ok'}],
            });
            const fxResponse = await fxResponsePromise;
            expect(fxResponse.ok()).toBe(true);
            expect(await fxResponse.finished()).toBeNull();
            expect(await fxResponse.json()).toMatchObject({
                success_count: readyPeerRequiredFxSlugs.length,
                results: [
                    {pair: readyPeerFxSlug, status: 'ok'},
                    {pair: readyPeerEventFxSlug, status: 'partial'},
                ],
            });

            const calendarRequest = await calendarRequestPromise;
            assertCalendarBulkRequest(calendarRequest.postDataJSON(), 30);
            assertMainDateRange(calendarRequest.postDataJSON(), ninetyDayRange);
            await expect.poll(() => calendarRequestCount).toBe(calendarRequestsBefore + 1);
            await expect(i60hNoDataIssues).toHaveCount(2);
            await expect(i60hReadySignalIssue).toHaveCount(0);
            await expect(readySignalCard.getByTestId('signal-loading')).toBeVisible();
            return {calendarGate, calendarResponsePromise};
        };
        const expectI60HCalendarDataClearedWithDiagnosticsRetained = async (): Promise<void> => {
            await expect(page.getByTestId('asset-calendar-return-error')).toBeVisible();
            await expect(page.getByTestId('asset-calendar-return-partial')).toBeHidden();
            await expect(chart).toHaveAttribute('data-series-state', 'error');
            await expect(chart).toHaveAttribute('data-calendar-comparison-ready', '');
            await expect(chart).toHaveAttribute('data-calendar-comparison-partial', '');
            await expect(chart).toHaveAttribute('data-calendar-comparison-unavailable', '');
            await expect(chart).toHaveAttribute('data-calendar-comparison-error', '');
            await expect(chart.locator('canvas')).toHaveCount(0);
            await expect.poll(readChartComparisonLineLabels).toEqual([]);
            await expect.poll(readChartEventMarkerAssetLabels).toEqual([]);
            await expect(i60hNoDataIssues).toHaveCount(2);
            await expect(i60hNoDataIssues.filter({hasText: readyPeer.currency})).toHaveCount(1);
            await expect(i60hNoDataIssues.filter({hasText: readyPeerEventCurrency})).toHaveCount(1);
            await expect(i60hReadySignalIssue).toBeVisible();
            await expect(i60hReadySignalIssue).toHaveAttribute('data-problem-code', 'fx_conversion_unavailable');
            await expect(i60hReadySignalIssue).toHaveAttribute('data-severity', 'error');
        };

        await test.step('I60H rejected same-fingerprint authoritative Calendar reload clears data but retains typed FX diagnostics', async () => {
            const enterCalendarResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            await calendarPrimary.click();
            const enterCalendarResponse = await enterCalendarResponsePromise;
            expect(enterCalendarResponse.ok()).toBe(true);
            expect(await enterCalendarResponse.finished()).toBeNull();
            assertCalendarBulkRequest(enterCalendarResponse.request().postDataJSON(), 30);
            assertMainDateRange(enterCalendarResponse.request().postDataJSON(), ninetyDayRange);
            await seedCurrentI60HCalendarFailure();

            const {calendarGate, calendarResponsePromise} = await beginAcceptedI60HCalendarSync('i60h-query-rejected');
            calendarGate.release();
            const rejectedResponse = await calendarResponsePromise;
            expect(rejectedResponse.ok()).toBe(false);
            expect(rejectedResponse.status()).toBe(503);
            expect(await rejectedResponse.finished()).toBeNull();
            expect(await rejectedResponse.json()).toEqual({detail: 'synthetic-i60h-calendar-query-rejection'});
            await expectI60HCalendarDataClearedWithDiagnosticsRetained();
        });

        await test.step('I60H same-fingerprint main omission clears data while different-fingerprint loading clears diagnostics', async () => {
            await seedCurrentI60HCalendarFailure();

            const {calendarGate, calendarResponsePromise} = await beginAcceptedI60HCalendarSync('i60h-main-omitted');
            calendarGate.release();
            const omittedResponse = await calendarResponsePromise;
            expect(omittedResponse.ok()).toBe(true);
            expect(await omittedResponse.finished()).toBeNull();
            const omittedPayload = (await omittedResponse.json()) as {items?: Array<{asset_id?: number}>};
            expect(omittedPayload.items?.some((item) => item.asset_id === assetId)).toBe(false);
            expect(new Set(omittedPayload.items?.flatMap((item) => (item.asset_id === undefined ? [] : [item.asset_id])))).toEqual(new Set(comparisonPeerIds));
            await expectI60HCalendarDataClearedWithDiagnosticsRetained();

            const successorFingerprintGate = deferCalendarResponse(90, 'ready');
            const successorFingerprintRequestPromise = waitForCalendarRequestForRange(90, ninetyDayRange);
            const successorFingerprintResponsePromise = waitForCalendarResponseForRange(90, ninetyDayRange);
            await chart.getByTestId('asset-calendar-window-3m').click();
            const successorFingerprintRequest = await successorFingerprintRequestPromise;
            assertCalendarBulkRequest(successorFingerprintRequest.postDataJSON(), 90);
            assertMainDateRange(successorFingerprintRequest.postDataJSON(), ninetyDayRange);
            await expect(chart).toHaveAttribute('data-series-state', 'loading');
            await expect(chart).toHaveAttribute('data-calendar-comparison-ready', '');
            await expect(chart).toHaveAttribute('data-calendar-comparison-partial', '');
            await expect(chart).toHaveAttribute('data-calendar-comparison-unavailable', '');
            await expect(chart).toHaveAttribute('data-calendar-comparison-error', '');
            await expect(chart.locator('canvas')).toHaveCount(0);
            await expect.poll(readChartComparisonLineLabels).toEqual([]);
            await expect.poll(readChartEventMarkerAssetLabels).toEqual([]);
            await expect(i60hNoDataIssues).toHaveCount(0);
            await expect(i60hReadySignalIssue).toHaveCount(0);

            successorFingerprintGate.release();
            const successorFingerprintResponse = await successorFingerprintResponsePromise;
            expect(successorFingerprintResponse.ok()).toBe(true);
            expect(await successorFingerprintResponse.finished()).toBeNull();
            await expect(chart).toHaveAttribute('data-window-days', '90');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');

            const restoreThirtyDayWindowResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            await chart.getByTestId('asset-calendar-window-1m').click();
            const restoreThirtyDayWindowResponse = await restoreThirtyDayWindowResponsePromise;
            expect(restoreThirtyDayWindowResponse.ok()).toBe(true);
            expect(await restoreThirtyDayWindowResponse.finished()).toBeNull();
            assertCalendarBulkRequest(restoreThirtyDayWindowResponse.request().postDataJSON(), 30);
            assertMainDateRange(restoreThirtyDayWindowResponse.request().postDataJSON(), ninetyDayRange);

            exposeMissingComparisonEventRoutes = false;
            missingFxConversionSlugs.clear();
            calendarConversionGapErrors = null;
            const restorePriceComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
            await pricePrimary.click();
            const restorePriceComparisonResponse = await restorePriceComparisonResponsePromise;
            expect(restorePriceComparisonResponse.ok()).toBe(true);
            expect(await restorePriceComparisonResponse.finished()).toBeNull();
            assertPriceComparisonRequest(restorePriceComparisonResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
            await expectCorrectedPriceComparisonState();
        });

        await test.step('I60H missing current peer preserves its price-FX failure until a present peer authoritatively clears it', async () => {
            const enterCalendarResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            await calendarPrimary.click();
            const enterCalendarResponse = await enterCalendarResponsePromise;
            expect(enterCalendarResponse.ok()).toBe(true);
            expect(await enterCalendarResponse.finished()).toBeNull();
            assertCalendarBulkRequest(enterCalendarResponse.request().postDataJSON(), 30);
            assertMainDateRange(enterCalendarResponse.request().postDataJSON(), ninetyDayRange);
            await seedCurrentI60HCalendarFailure();

            const omittedPeerGate = deferCalendarResponse(30, 'i60h-ready-peer-omitted');
            const omittedPeerCalendarRequestsBefore = calendarRequestCount;
            const omittedPeerRequestPromise = waitForCalendarRequestForRange(30, ninetyDayRange);
            const omittedPeerResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            await refreshButton.click();
            const omittedPeerRequest = await omittedPeerRequestPromise;
            assertCalendarBulkRequest(omittedPeerRequest.postDataJSON(), 30);
            assertMainDateRange(omittedPeerRequest.postDataJSON(), ninetyDayRange);
            expect(calendarRequestCount).toBe(omittedPeerCalendarRequestsBefore + 1);
            omittedPeerGate.release();

            const omittedPeerResponse = await omittedPeerResponsePromise;
            expect(omittedPeerResponse.ok()).toBe(true);
            expect(await omittedPeerResponse.finished()).toBeNull();
            const omittedPeerPayload = (await omittedPeerResponse.json()) as {items?: Array<{asset_id?: number}>};
            expect(omittedPeerPayload.items?.some((item) => item.asset_id === assetId)).toBe(true);
            expect(omittedPeerPayload.items?.some((item) => item.asset_id === readyPeer.id)).toBe(false);
            expect(new Set(omittedPeerPayload.items?.flatMap((item) => (item.asset_id === undefined ? [] : [item.asset_id])))).toEqual(new Set([assetId, ...comparisonPeerIds.filter((peerId) => peerId !== readyPeer.id)]));

            await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
            await expect(chart).toHaveAttribute('data-window-days', '30');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');
            await expectAssetDetailChartCanvas(page);
            const omittedPeerSnapshot = await readI60GCalendarChart();
            expect(omittedPeerSnapshot.main.some((value) => value !== null)).toBe(true);
            expect(omittedPeerSnapshot.presentPeerLabels).not.toContain(readyPeer.display_name);
            const omittedReadyPeerValues = omittedPeerSnapshot.peers[readyPeer.display_name];
            expect(omittedReadyPeerValues, `Calendar chart must retain the owned peer ${readyPeer.id} slot while omitting its stale line`).toBeDefined();
            expect(omittedReadyPeerValues?.every((value) => value === null)).toBe(true);
            await expect(i60hReadySignalIssue).toBeVisible();
            await expect(i60hReadySignalIssue).toHaveAttribute('data-problem-code', 'result_missing');
            await expect(i60hReadySignalIssue).toHaveAttribute('data-severity', 'error');
            await expect(i60hNoDataIssues).toHaveCount(1);
            await expect(i60hNoDataIssues.filter({hasText: readyPeer.currency})).toHaveCount(1);
            await expect(i60hNoDataIssues.filter({hasText: readyPeerEventCurrency})).toHaveCount(0);

            // Leave the independently owned event dependency failed. The next
            // response can therefore clear only the peer price-FX route.
            expect(missingFxConversionSlugs).toEqual(new Set([readyPeerEventFxSlug]));
            calendarConversionGapErrors = null;
            const presentPeerCalendarRequestsBefore = calendarRequestCount;
            const presentPeerResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            await refreshButton.click();
            const presentPeerResponse = await presentPeerResponsePromise;
            expect(presentPeerResponse.ok()).toBe(true);
            expect(await presentPeerResponse.finished()).toBeNull();
            assertCalendarBulkRequest(presentPeerResponse.request().postDataJSON(), 30);
            assertMainDateRange(presentPeerResponse.request().postDataJSON(), ninetyDayRange);
            expect(calendarRequestCount).toBe(presentPeerCalendarRequestsBefore + 1);
            const presentPeerPayload = (await presentPeerResponse.json()) as {
                items?: Array<{asset_id?: number; errors?: unknown[]; signals?: Array<{instance_id?: string; signal_code?: string; status?: string}>}>;
            };
            const presentPeerItem = presentPeerPayload.items?.find((item) => item.asset_id === readyPeer.id);
            expect(presentPeerItem, `authoritative Calendar response must contain owned peer ${readyPeer.id}`).toBeDefined();
            expect(presentPeerItem?.errors).toEqual([]);
            expect(presentPeerItem?.signals?.find((signal) => signal.instance_id === calendarInstanceId && signal.signal_code === calendarSignalCode)).toMatchObject({status: 'ok'});

            await expect(chart).toHaveAttribute('data-calendar-comparison-ready', String(readyPeer.id));
            await expect(i60hReadySignalIssue).toHaveCount(0);
            await expect(i60hNoDataIssues).toHaveCount(1);
            await expect(i60hNoDataIssues.filter({hasText: readyPeer.currency})).toHaveCount(0);
            await expect(i60hNoDataIssues.filter({hasText: readyPeerEventCurrency})).toHaveCount(1);
            const presentPeerSnapshot = await readI60GCalendarChart();
            expect(presentPeerSnapshot.presentPeerLabels).toContain(readyPeer.display_name);
            const presentReadyPeerValues = presentPeerSnapshot.peers[readyPeer.display_name];
            expect(presentReadyPeerValues, `authoritative Calendar response must restore peer ${readyPeer.id}'s plotted line`).toBeDefined();
            expect(presentReadyPeerValues?.some((value) => value !== null)).toBe(true);

            exposeMissingComparisonEventRoutes = false;
            missingFxConversionSlugs.clear();
            calendarConversionGapErrors = null;
            const correctedPriceResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
            await pricePrimary.click();
            const correctedPriceResponse = await correctedPriceResponsePromise;
            expect(correctedPriceResponse.ok()).toBe(true);
            expect(await correctedPriceResponse.finished()).toBeNull();
            assertPriceComparisonRequest(correctedPriceResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
            await expect(chart).toHaveAttribute('data-primary-mode', 'price');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');
            await expectCorrectedPriceComparisonState();
        });

        await test.step('I60H coordinated Calendar sync waits for every accepted configured FX route before clearing typed banners', async () => {
            const enterLifecycleCalendarResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            await calendarPrimary.click();
            const enterLifecycleCalendarResponse = await enterLifecycleCalendarResponsePromise;
            expect(enterLifecycleCalendarResponse.ok()).toBe(true);
            expect(await enterLifecycleCalendarResponse.finished()).toBeNull();
            assertCalendarBulkRequest(enterLifecycleCalendarResponse.request().postDataJSON(), 30);
            assertMainDateRange(enterLifecycleCalendarResponse.request().postDataJSON(), ninetyDayRange);
            await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');

            exposeMissingComparisonEventRoutes = true;
            missingFxConversionSlugs.add(readyPeerFxSlug);
            missingFxConversionSlugs.add(readyPeerEventFxSlug);
            calendarConversionGapErrors = [readyPeerConversionError];
            const lifecycleFailureResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            await refreshButton.click();
            const lifecycleFailureResponse = await lifecycleFailureResponsePromise;
            expect(lifecycleFailureResponse.ok()).toBe(true);
            expect(await lifecycleFailureResponse.finished()).toBeNull();
            assertCalendarBulkRequest(lifecycleFailureResponse.request().postDataJSON(), 30);
            assertMainDateRange(lifecycleFailureResponse.request().postDataJSON(), ninetyDayRange);

            const lifecycleNoDataIssues = page.getByTestId('data-quality-issue-FX_PAIR_NO_DATA');
            await expect(lifecycleNoDataIssues).toHaveCount(2);
            const lifecycleSignalIssue = readySignalCard.getByTestId('signal-issue');
            await expect(lifecycleSignalIssue).toBeVisible();
            await expect(lifecycleSignalIssue).toHaveAttribute('data-problem-code', 'fx_conversion_unavailable');
            await expect(page.getByTestId('data-quality-issue-FX_PAIR_MISSING')).toHaveCount(0);

            const documentOwnerToken = 'i60h-current-document';
            await page.evaluate((token) => {
                (window as Window & {__lfI60hDocumentOwner?: string}).__lfI60hDocumentOwner = token;
            }, documentOwnerToken);

            const lifecycleAssetGate = deferNextAssetSyncResponse();
            const lifecycleFxGate = deferNextFxSyncResponse();
            const lifecyclePriceFxRefillGate = deferFxRefillResponse(readyPeerFxSlug);
            const lifecycleEventFxRefillGate = deferFxRefillResponse(readyPeerEventFxSlug);
            nextAssetSyncStatus = 'ok';
            nextFxSyncStatusesBySlug = new Map([
                [readyPeerFxSlug, 'ok'],
                [readyPeerEventFxSlug, 'partial'],
            ]);
            clearCalendarConversionGapOnAcceptedReadyRoutes = true;
            const lifecycleAssetSyncRequestsBefore = assetSyncRequestCount;
            const lifecycleFxSyncRequestsBefore = fxSyncRequestCount;
            const lifecycleCalendarRequestsBefore = calendarRequestCount;
            const lifecyclePriceComparisonRequestsBefore = priceComparisonRequestCount;
            const lifecycleFxConversionsBefore = fxConvertRequestCount;
            const lifecycleRouteMutationsBefore = fxRouteMutationRequestCount;
            const lifecyclePriceFxRefillsBefore = fxRefillCounts.get(readyPeerFxSlug) ?? 0;
            const lifecycleEventFxRefillsBefore = fxRefillCounts.get(readyPeerEventFxSlug) ?? 0;
            const lifecycleRequiredFxSlugs = new Set<string>(readyPeerRequiredFxSlugs);
            const lifecycleSyncRefillCalls = () =>
                fxConvertRequests.slice(lifecycleFxConversionsBefore).filter((requests) => {
                    if (requests.length !== 1) return false;
                    const request = requests[0];
                    if (!request) return false;
                    const slug = [request.from_amount.code, request.to].sort().join('-');
                    return request.from_amount.amount === '1' && lifecycleRequiredFxSlugs.has(slug) && request.date_range.start === ninetyDayCalendarSyncRange.start && request.date_range.end === ninetyDayCalendarSyncRange.end;
                });
            const lifecycleAssetRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
            const lifecycleAssetResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
            const lifecycleFxRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
            const lifecycleFxResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
            await activateComparisonAssetSync(readySignalId);

            const lifecycleAssetRequest = await lifecycleAssetRequestPromise;
            const lifecycleFxRequest = await lifecycleFxRequestPromise;
            assertAssetSyncRequest(lifecycleAssetRequest.postDataJSON(), readyPeer.id, ninetyDayCalendarSyncRange);
            assertFxSyncRequest(lifecycleFxRequest.postDataJSON(), readyPeerRequiredFxSlugs, ninetyDayCalendarSyncRange);
            expect(readyPeerRequiredFxSlugs).toEqual([readyPeerFxSlug, readyPeerEventFxSlug]);

            lifecycleAssetGate.release();
            const lifecycleAssetResponse = await lifecycleAssetResponsePromise;
            expect(lifecycleAssetResponse.ok()).toBe(true);
            expect(await lifecycleAssetResponse.finished()).toBeNull();
            expect(await lifecycleAssetResponse.json()).toMatchObject({
                success_count: 1,
                results: [{asset_id: readyPeer.id, status: 'ok'}],
            });
            await expect(lifecycleNoDataIssues).toHaveCount(2);
            await expect(lifecycleSignalIssue).toHaveAttribute('data-problem-code', 'fx_conversion_unavailable');
            expect(calendarRequestCount).toBe(lifecycleCalendarRequestsBefore);
            expect(priceComparisonRequestCount).toBe(lifecyclePriceComparisonRequestsBefore);
            expect(lifecycleSyncRefillCalls()).toHaveLength(0);

            lifecycleFxGate.release();
            const lifecycleFxResponse = await lifecycleFxResponsePromise;
            expect(lifecycleFxResponse.ok()).toBe(true);
            expect(await lifecycleFxResponse.finished()).toBeNull();
            expect(await lifecycleFxResponse.json()).toMatchObject({
                success_count: readyPeerRequiredFxSlugs.length,
                results: [
                    {pair: readyPeerFxSlug, status: 'ok'},
                    {pair: readyPeerEventFxSlug, status: 'partial'},
                ],
            });
            await expect.poll(() => fxRefillCounts.get(readyPeerFxSlug) ?? 0).toBe(lifecyclePriceFxRefillsBefore + 1);
            await expect(lifecycleNoDataIssues).toHaveCount(2);
            expect(calendarRequestCount).toBe(lifecycleCalendarRequestsBefore);
            expect(priceComparisonRequestCount).toBe(lifecyclePriceComparisonRequestsBefore);

            lifecyclePriceFxRefillGate.release();
            await expect.poll(() => fxRefillCounts.get(readyPeerEventFxSlug) ?? 0).toBe(lifecycleEventFxRefillsBefore + 1);
            await expect(lifecycleNoDataIssues).toHaveCount(2);
            expect(calendarRequestCount).toBe(lifecycleCalendarRequestsBefore);
            expect(priceComparisonRequestCount).toBe(lifecyclePriceComparisonRequestsBefore);

            const lifecycleCalendarReloadPromise = waitForCalendarResponseForRange(30, ninetyDayRange);
            lifecycleEventFxRefillGate.release();
            const lifecycleCalendarReload = await lifecycleCalendarReloadPromise;
            expect(lifecycleCalendarReload.ok()).toBe(true);
            expect(await lifecycleCalendarReload.finished()).toBeNull();
            assertCalendarBulkRequest(lifecycleCalendarReload.request().postDataJSON(), 30);
            assertMainDateRange(lifecycleCalendarReload.request().postDataJSON(), ninetyDayRange);
            expect(calendarRequestCount).toBe(lifecycleCalendarRequestsBefore + 1);
            expect(priceComparisonRequestCount).toBe(lifecyclePriceComparisonRequestsBefore);
            expect(assetSyncRequestCount).toBe(lifecycleAssetSyncRequestsBefore + 1);
            expect(fxSyncRequestCount).toBe(lifecycleFxSyncRequestsBefore + 1);
            expect(fxRouteMutationRequestCount).toBe(lifecycleRouteMutationsBefore);
            const lifecycleRefills = lifecycleSyncRefillCalls().flat();
            expect(lifecycleRefills).toHaveLength(readyPeerRequiredFxSlugs.length);
            expect([...new Set(lifecycleRefills.map((request) => [request.from_amount.code, request.to].sort().join('-')))].sort()).toEqual([...readyPeerRequiredFxSlugs]);
            expect(lifecycleRefills.every((request) => request.date_range.start === ninetyDayCalendarSyncRange.start && request.date_range.end === ninetyDayCalendarSyncRange.end)).toBe(true);
            await expect(lifecycleNoDataIssues).toHaveCount(0);
            await expect(requiredFxIssues).toHaveCount(0);
            await expect(lifecycleSignalIssue).toHaveCount(0);
            expect(await page.evaluate(() => (window as Window & {__lfI60hDocumentOwner?: string}).__lfI60hDocumentOwner)).toBe(documentOwnerToken);

            const lifecyclePriceComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
            await pricePrimary.click();
            const lifecyclePriceComparisonResponse = await lifecyclePriceComparisonResponsePromise;
            expect(lifecyclePriceComparisonResponse.ok()).toBe(true);
            expect(await lifecyclePriceComparisonResponse.finished()).toBeNull();
            assertPriceComparisonRequest(lifecyclePriceComparisonResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
            await expect(chart).toHaveAttribute('data-primary-mode', 'price');
            await expect(lifecycleNoDataIssues).toHaveCount(0);
            await expect(requiredFxIssues).toHaveCount(0);
            expect(await page.evaluate(() => (window as Window & {__lfI60hDocumentOwner?: string}).__lfI60hDocumentOwner)).toBe(documentOwnerToken);
        });

        await test.step('I60H failed and skipped required routes retain Price data-quality banners', async () => {
            missingFxConversionSlugs.add(readyPeerFxSlug);
            missingFxConversionSlugs.add(readyPeerEventFxSlug);
            const failedRouteSeedMainPromise = waitForMainPriceResponse(ninetyDayRange);
            const failedRouteSeedComparisonPromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
            await refreshButton.click();
            const failedRouteSeedMain = await failedRouteSeedMainPromise;
            expect(failedRouteSeedMain.ok()).toBe(true);
            expect(await failedRouteSeedMain.finished()).toBeNull();
            assertMainDateRange(failedRouteSeedMain.request().postDataJSON(), ninetyDayRange);
            const failedRouteSeedComparison = await failedRouteSeedComparisonPromise;
            expect(failedRouteSeedComparison.ok()).toBe(true);
            expect(await failedRouteSeedComparison.finished()).toBeNull();
            assertPriceComparisonRequest(failedRouteSeedComparison.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);

            const failedRouteIssues = page.getByTestId('data-quality-issue-FX_PAIR_NO_DATA');
            await expect(failedRouteIssues).toHaveCount(2);
            nextAssetSyncStatus = 'ok';
            nextFxSyncStatusesBySlug = new Map([
                [readyPeerFxSlug, 'failed'],
                [readyPeerEventFxSlug, 'skipped'],
            ]);
            const failedRouteFxConversionsBefore = fxConvertRequestCount;
            const failedRouteMutationsBefore = fxRouteMutationRequestCount;
            const failedRouteAssetRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
            const failedRouteAssetResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
            const failedRouteFxRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
            const failedRouteFxResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
            const failedRouteMainReloadPromise = waitForMainPriceResponse(ninetyDayRange);
            const failedRouteComparisonReloadPromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
            await activateComparisonAssetSync(readySignalId);

            const failedRouteAssetRequest = await failedRouteAssetRequestPromise;
            const failedRouteFxRequest = await failedRouteFxRequestPromise;
            assertAssetSyncRequest(failedRouteAssetRequest.postDataJSON(), readyPeer.id, ninetyDayPriceSyncRange);
            assertFxSyncRequest(failedRouteFxRequest.postDataJSON(), readyPeerRequiredFxSlugs, ninetyDayPriceSyncRange);
            const failedRouteAssetResponse = await failedRouteAssetResponsePromise;
            expect(failedRouteAssetResponse.ok()).toBe(true);
            expect(await failedRouteAssetResponse.finished()).toBeNull();
            expect(await failedRouteAssetResponse.json()).toMatchObject({
                success_count: 1,
                results: [{asset_id: readyPeer.id, status: 'ok'}],
            });
            const failedRouteFxResponse = await failedRouteFxResponsePromise;
            expect(failedRouteFxResponse.ok()).toBe(true);
            expect(await failedRouteFxResponse.finished()).toBeNull();
            expect(await failedRouteFxResponse.json()).toMatchObject({
                success_count: 0,
                results: [
                    {pair: readyPeerFxSlug, status: 'failed'},
                    {pair: readyPeerEventFxSlug, status: 'skipped'},
                ],
            });
            const failedRouteMainReload = await failedRouteMainReloadPromise;
            expect(failedRouteMainReload.ok()).toBe(true);
            expect(await failedRouteMainReload.finished()).toBeNull();
            assertMainDateRange(failedRouteMainReload.request().postDataJSON(), ninetyDayRange);
            const failedRouteComparisonReload = await failedRouteComparisonReloadPromise;
            expect(failedRouteComparisonReload.ok()).toBe(true);
            expect(await failedRouteComparisonReload.finished()).toBeNull();
            assertPriceComparisonRequest(failedRouteComparisonReload.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
            await expect(failedRouteIssues).toHaveCount(2);
            await expect(readySignalCard.getByTestId('signal-issue')).toBeVisible();
            expect(fxConvertRequestCount).toBe(failedRouteFxConversionsBefore);
            expect(fxRouteMutationRequestCount).toBe(failedRouteMutationsBefore);
            await expectFocusedAssetSyncIdle(readySignalId);
        });

        await test.step('I60H stale coordinated completion cannot clear or reload the current range', async () => {
            const staleLifecycleAssetGate = deferNextAssetSyncResponse();
            const staleLifecycleFxGate = deferNextFxSyncResponse();
            nextAssetSyncStatus = 'ok';
            nextFxSyncStatusesBySlug = new Map([
                [readyPeerFxSlug, 'ok'],
                [readyPeerEventFxSlug, 'partial'],
            ]);
            const staleLifecycleAssetRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
            const staleLifecycleAssetResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
            const staleLifecycleFxRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
            const staleLifecycleFxResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
            await activateComparisonAssetSync(readySignalId);

            const staleLifecycleAssetRequest = await staleLifecycleAssetRequestPromise;
            const staleLifecycleFxRequest = await staleLifecycleFxRequestPromise;
            assertAssetSyncRequest(staleLifecycleAssetRequest.postDataJSON(), readyPeer.id, ninetyDayPriceSyncRange);
            assertFxSyncRequest(staleLifecycleFxRequest.postDataJSON(), readyPeerRequiredFxSlugs, ninetyDayPriceSyncRange);

            const staleLifecycleRangeRequest = await commitSyntheticRange(thirtyDayRange, true);
            assertMainDateRange(staleLifecycleRangeRequest.postDataJSON(), thirtyDayRange);
            const staleLifecycleIssues = page.getByTestId('data-quality-issue-FX_PAIR_NO_DATA');
            await expect(staleLifecycleIssues).toHaveCount(2);
            const staleLifecyclePriceQueriesAfterContext = priceQueryRequestCount;
            const staleLifecycleComparisonRequestsAfterContext = priceComparisonRequestCount;
            const staleLifecycleCalendarRequestsAfterContext = calendarRequestCount;
            const staleLifecycleFxConversionsAfterContext = fxConvertRequestCount;
            const staleLifecycleRouteMutationsAfterContext = fxRouteMutationRequestCount;

            staleLifecycleAssetGate.release();
            const staleLifecycleAssetResponse = await staleLifecycleAssetResponsePromise;
            expect(staleLifecycleAssetResponse.ok()).toBe(true);
            expect(await staleLifecycleAssetResponse.finished()).toBeNull();
            await expect(staleLifecycleIssues).toHaveCount(2);
            expect(priceQueryRequestCount).toBe(staleLifecyclePriceQueriesAfterContext);
            expect(priceComparisonRequestCount).toBe(staleLifecycleComparisonRequestsAfterContext);
            expect(calendarRequestCount).toBe(staleLifecycleCalendarRequestsAfterContext);
            expect(fxConvertRequestCount).toBe(staleLifecycleFxConversionsAfterContext);

            staleLifecycleFxGate.release();
            const staleLifecycleFxResponse = await staleLifecycleFxResponsePromise;
            expect(staleLifecycleFxResponse.ok()).toBe(true);
            expect(await staleLifecycleFxResponse.finished()).toBeNull();
            expect(await staleLifecycleFxResponse.json()).toMatchObject({
                success_count: readyPeerRequiredFxSlugs.length,
                results: [
                    {pair: readyPeerFxSlug, status: 'ok'},
                    {pair: readyPeerEventFxSlug, status: 'partial'},
                ],
            });
            await expectFocusedAssetSyncIdle(readySignalId);
            await expect(staleLifecycleIssues).toHaveCount(2);
            await expect(dateRangeStartInput).toHaveValue(thirtyDayRange.start);
            await expect(dateRangeEndInput).toHaveValue(thirtyDayRange.end);
            expect(priceQueryRequestCount).toBe(staleLifecyclePriceQueriesAfterContext);
            expect(priceComparisonRequestCount).toBe(staleLifecycleComparisonRequestsAfterContext);
            expect(calendarRequestCount).toBe(staleLifecycleCalendarRequestsAfterContext);
            expect(fxConvertRequestCount).toBe(staleLifecycleFxConversionsAfterContext);
            expect(fxRouteMutationRequestCount).toBe(staleLifecycleRouteMutationsAfterContext);

            exposeMissingComparisonEventRoutes = false;
            missingFxConversionSlugs.clear();
            const restoreLifecycleComparisonPromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
            const restoreLifecycleRangeRequest = await commitSyntheticRange(ninetyDayRange, true);
            const restoreLifecycleComparison = await restoreLifecycleComparisonPromise;
            expect(restoreLifecycleComparison.ok()).toBe(true);
            expect(await restoreLifecycleComparison.finished()).toBeNull();
            assertMainDateRange(restoreLifecycleRangeRequest.postDataJSON(), ninetyDayRange);
            assertPriceComparisonRequest(restoreLifecycleComparison.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
            await expect(staleLifecycleIssues).toHaveCount(0);
            await expect(requiredFxIssues).toHaveCount(0);
            await expectCorrectedPriceComparisonState();
        });

        // The main Asset and this peer are both native EUR while the display
        // currency is GBP, so both depend on the already-configured EUR-GBP
        // route. An accepted peer FX sync must invalidate the main price cache:
        // its successor carries include_price=true and applies the refreshed
        // conversion before the one peer successor is allowed to publish.
        const selectSharedRouteComparisonPromise = waitForPriceComparisonResponse(sharedRoutePeerIds, ninetyDayRange, asset.currency);
        await selectComparisonAsset(readySignalId, sharedRoutePeer.id);
        const selectSharedRouteComparison = await selectSharedRouteComparisonPromise;
        expect(selectSharedRouteComparison.ok()).toBe(true);
        expect(await selectSharedRouteComparison.finished()).toBeNull();
        assertPriceComparisonRequest(selectSharedRouteComparison.request().postDataJSON(), sharedRoutePeerIds, ninetyDayRange, asset.currency);
        await expect.poll(readPersistedReadyPeerId).toBe(String(sharedRoutePeer.id));

        sharedRouteMainSnapshot = 'initial';
        const sharedRouteInitialMainResponsePromise = waitForMainPriceResponse(ninetyDayRange, 'GBP');
        const sharedRouteInitialComparisonResponsePromise = waitForPriceComparisonResponse(sharedRoutePeerIds, ninetyDayRange, 'GBP');
        await openCurrencySelect();
        const sharedRouteGbpOption = page.getByTestId('search-select-option-GBP');
        await expect(sharedRouteGbpOption).toBeVisible();
        await sharedRouteGbpOption.click();
        await expect(currencyTrigger).toHaveAttribute('aria-expanded', 'false');
        const sharedRouteInitialMainResponse = await sharedRouteInitialMainResponsePromise;
        expect(sharedRouteInitialMainResponse.ok()).toBe(true);
        expect(await sharedRouteInitialMainResponse.finished()).toBeNull();
        const sharedRouteInitialMainQuery = parseQueries(sharedRouteInitialMainResponse.request().postDataJSON()).find((query) => query.asset_id === assetId);
        expect(sharedRouteInitialMainQuery).toMatchObject({
            asset_id: assetId,
            date_range: {start: ninetyDayRange.start, end: ninetyDayRange.end},
            target_currency: 'GBP',
        });
        const sharedRouteInitialComparisonResponse = await sharedRouteInitialComparisonResponsePromise;
        expect(sharedRouteInitialComparisonResponse.ok()).toBe(true);
        expect(await sharedRouteInitialComparisonResponse.finished()).toBeNull();
        assertPriceComparisonRequest(sharedRouteInitialComparisonResponse.request().postDataJSON(), sharedRoutePeerIds, ninetyDayRange, 'GBP');
        await expect(page.getByTestId('asset-detail-live-price')).toHaveText('333.00');
        await expect.poll(() => readChartLineValues(asset.display_name)).toEqual([331, 332, 333]);

        nextAssetSyncStatus = 'ok';
        nextFxSyncStatus = 'partial';
        const sharedRouteAssetSyncRequestsBefore = assetSyncRequestCount;
        const sharedRouteFxSyncRequestsBefore = fxSyncRequestCount;
        const sharedRouteFxConvertRequestsBefore = fxConvertRequestCount;
        const sharedRoutePriceQueriesBefore = priceQueryRequestCount;
        const sharedRouteMainRequestsBefore = mainPriceRequestCount;
        const sharedRouteComparisonRequestsBefore = sharedRoutePriceComparisonRequestCount;
        const sharedRouteTrackedComparisonRequestsBefore = priceComparisonRequestCount;
        const sharedRouteMutationsBefore = fxRouteMutationRequestCount;
        const sharedRouteMainGate = deferNextMainPriceResponse();
        const sharedRouteComparisonGate = deferNextPriceComparisonResponse();
        const sharedRouteAssetSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const sharedRouteAssetSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const sharedRouteFxSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const sharedRouteFxSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const sharedRouteMainRequestPromise = waitForMainPriceRequest(ninetyDayRange);
        const sharedRouteMainResponsePromise = waitForMainPriceResponse(ninetyDayRange, 'GBP');
        const sharedRouteComparisonRequestPromise = waitForPriceComparisonRequest(sharedRoutePeerIds, ninetyDayRange, 'GBP');
        const sharedRouteComparisonResponsePromise = waitForPriceComparisonResponse(sharedRoutePeerIds, ninetyDayRange, 'GBP');
        const sharedRouteSyncAction = readySignalCard.getByTestId(`signal-sync-asset-${readySignalId}`);
        await expect(sharedRouteSyncAction).toBeEnabled();
        await sharedRouteSyncAction.click();

        const sharedRouteAssetSyncRequest = await sharedRouteAssetSyncRequestPromise;
        assertAssetSyncRequest(sharedRouteAssetSyncRequest.postDataJSON(), sharedRoutePeer.id, ninetyDayPriceSyncRange);
        const sharedRouteFxSyncRequest = await sharedRouteFxSyncRequestPromise;
        assertFxSyncRequest(sharedRouteFxSyncRequest.postDataJSON(), [readyPeerFxSlug], ninetyDayPriceSyncRange);
        const sharedRouteAssetSyncResponse = await sharedRouteAssetSyncResponsePromise;
        expect(sharedRouteAssetSyncResponse.ok()).toBe(true);
        expect(await sharedRouteAssetSyncResponse.finished()).toBeNull();
        expect(await sharedRouteAssetSyncResponse.json()).toMatchObject({
            success_count: 1,
            results: [{asset_id: sharedRoutePeer.id, status: 'ok'}],
        });
        const sharedRouteFxSyncResponse = await sharedRouteFxSyncResponsePromise;
        expect(sharedRouteFxSyncResponse.ok()).toBe(true);
        expect(await sharedRouteFxSyncResponse.finished()).toBeNull();
        expect(await sharedRouteFxSyncResponse.json()).toMatchObject({
            success_count: 1,
            results: [{pair: readyPeerFxSlug, status: 'partial'}],
        });

        const sharedRouteMainRequest = await sharedRouteMainRequestPromise;
        const sharedRouteMainQuery = parseQueries(sharedRouteMainRequest.postDataJSON()).find((query) => query.asset_id === assetId);
        expect(sharedRouteMainQuery).toMatchObject({
            asset_id: assetId,
            date_range: {start: ninetyDayRange.start, end: ninetyDayRange.end},
            include_price: true,
            target_currency: 'GBP',
        });
        await expect.poll(() => priceQueryRequestCount).toBe(sharedRoutePriceQueriesBefore + 1);
        await expect.poll(() => mainPriceRequestCount).toBe(sharedRouteMainRequestsBefore + 1);
        expect(sharedRoutePriceComparisonRequestCount).toBe(sharedRouteComparisonRequestsBefore);
        await expect(page.getByTestId('asset-detail-live-price')).toHaveText('333.00');

        sharedRouteMainSnapshot = 'refreshed';
        sharedRouteMainGate.release();
        const sharedRouteMainResponse = await sharedRouteMainResponsePromise;
        expect(sharedRouteMainResponse.ok()).toBe(true);
        expect(await sharedRouteMainResponse.finished()).toBeNull();
        const sharedRouteMainItem = ((await sharedRouteMainResponse.json()) as {items?: Array<{asset_id?: number; prices?: Array<{close?: string}>}>}).items?.find((item) => item.asset_id === assetId);
        expect(sharedRouteMainItem?.prices?.map((point) => point.close)).toEqual(['771.00', '772.00', '777.00']);
        const sharedRouteComparisonRequest = await sharedRouteComparisonRequestPromise;
        assertPriceComparisonRequest(sharedRouteComparisonRequest.postDataJSON(), sharedRoutePeerIds, ninetyDayRange, 'GBP');
        await expect.poll(() => priceQueryRequestCount).toBe(sharedRoutePriceQueriesBefore + 2);
        expect(mainPriceRequestCount).toBe(sharedRouteMainRequestsBefore + 1);
        await expect.poll(() => sharedRoutePriceComparisonRequestCount).toBe(sharedRouteComparisonRequestsBefore + 1);
        sharedRouteComparisonGate.release();
        const sharedRouteComparisonResponse = await sharedRouteComparisonResponsePromise;
        expect(sharedRouteComparisonResponse.ok()).toBe(true);
        expect(await sharedRouteComparisonResponse.finished()).toBeNull();
        await expect(sharedRouteSyncAction).toBeEnabled();
        await expect(page.getByTestId('asset-detail-live-price')).toHaveText('777.00');
        await expect.poll(() => readChartLineValues(asset.display_name)).toEqual([771, 772, 777]);
        expect(assetSyncRequestCount).toBe(sharedRouteAssetSyncRequestsBefore + 1);
        expect(fxSyncRequestCount).toBe(sharedRouteFxSyncRequestsBefore + 1);
        expect(fxConvertRequestCount).toBe(sharedRouteFxConvertRequestsBefore + 1);
        expect(priceQueryRequestCount).toBe(sharedRoutePriceQueriesBefore + 2);
        expect(mainPriceRequestCount).toBe(sharedRouteMainRequestsBefore + 1);
        expect(sharedRoutePriceComparisonRequestCount).toBe(sharedRouteComparisonRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(sharedRouteTrackedComparisonRequestsBefore);
        expect(fxRouteMutationRequestCount).toBe(sharedRouteMutationsBefore);
        await pricePrimary.focus();
        await expect(pricePrimary).toBeFocused();
        expect(priceQueryRequestCount).toBe(sharedRoutePriceQueriesBefore + 2);
        expect(sharedRoutePriceComparisonRequestCount).toBe(sharedRouteComparisonRequestsBefore + 1);

        // In GBP Calendar mode the main Asset and the active EUR peer share
        // the same already-configured EUR/GBP route. PageSync must deduplicate
        // that primary/peer dependency and omit the unconfigured direct routes.
        const sharedRouteCalendarResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
        await calendarPrimary.click();
        const sharedRouteCalendarResponse = await sharedRouteCalendarResponsePromise;
        expect(sharedRouteCalendarResponse.ok()).toBe(true);
        expect(await sharedRouteCalendarResponse.finished()).toBeNull();
        assertCalendarBulkRequest(sharedRouteCalendarResponse.request().postDataJSON(), 30, sharedRoutePeerIds, 'GBP');
        assertMainDateRange(sharedRouteCalendarResponse.request().postDataJSON(), ninetyDayRange);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');

        const sharedRoutePageSyncAssetIds = [assetId, ...sharedRoutePeerIds];
        const sharedRoutePageSyncAssetStatuses = new Map<number, SyncStatusFixture>(sharedRoutePageSyncAssetIds.map((pageSyncAssetId) => [pageSyncAssetId, 'failed']));
        nextAssetSyncStatusesById = sharedRoutePageSyncAssetStatuses;
        nextFxSyncStatusesBySlug = new Map([[readyPeerFxSlug, 'skipped']]);
        priceComparisonSyncSucceeded = false;
        const sharedRoutePageSyncAssetRequestsBefore = assetSyncRequestCount;
        const sharedRoutePageSyncFxRequestsBefore = fxSyncRequestCount;
        const sharedRoutePageSyncFxConversionsBefore = fxConvertRequestCount;
        const sharedRoutePageSyncMutationsBefore = fxRouteMutationRequestCount;
        const sharedRoutePageSyncAssetRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const sharedRoutePageSyncAssetResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const sharedRoutePageSyncFxRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const sharedRoutePageSyncFxResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const sharedRoutePageSyncCalendarResponsePromise = waitForCalendarResponseForRange(30, ninetyDayRange);
        const sharedRoutePageSyncMetadataResponsePromise = page.waitForResponse((response) => response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/v1/assets/provider/assignments', {timeout: 10_000});
        await expect(pageSyncButton).toBeEnabled();
        await pageSyncButton.click();
        await expect(pageSyncModal).toBeVisible();
        await expect(pageSyncStart).toBeEnabled();
        await pageSyncStart.click();

        const sharedRoutePageSyncAssetRequest = await sharedRoutePageSyncAssetRequestPromise;
        const sharedRoutePageSyncAssetQueries = parseQueries(sharedRoutePageSyncAssetRequest.postDataJSON());
        expect(sharedRoutePageSyncAssetQueries.map((query) => query.asset_id).sort((left, right) => Number(left) - Number(right))).toEqual([...sharedRoutePageSyncAssetIds].sort((left, right) => left - right));
        expect(sharedRoutePageSyncAssetQueries.every((query) => query.date_range?.start === ninetyDayRange.start && query.date_range.end === ninetyDayRange.end)).toBe(true);
        const sharedRoutePageSyncFxRequest = await sharedRoutePageSyncFxRequestPromise;
        expect(sharedRoutePageSyncFxRequest.postDataJSON()).toEqual({
            pairs: [readyPeerFxSlug],
            start: ninetyDayRange.start,
            end: ninetyDayRange.end,
        });
        const sharedRoutePageSyncAssetResponse = await sharedRoutePageSyncAssetResponsePromise;
        expect(sharedRoutePageSyncAssetResponse.ok()).toBe(true);
        expect(await sharedRoutePageSyncAssetResponse.finished()).toBeNull();
        const sharedRoutePageSyncFxResponse = await sharedRoutePageSyncFxResponsePromise;
        expect(sharedRoutePageSyncFxResponse.ok()).toBe(true);
        expect(await sharedRoutePageSyncFxResponse.finished()).toBeNull();
        expect(await sharedRoutePageSyncFxResponse.json()).toMatchObject({
            success_count: 0,
            results: [{pair: readyPeerFxSlug, status: 'skipped'}],
        });
        const sharedRoutePageSyncCalendarReload = await sharedRoutePageSyncCalendarResponsePromise;
        expect(sharedRoutePageSyncCalendarReload.ok()).toBe(true);
        expect(await sharedRoutePageSyncCalendarReload.finished()).toBeNull();
        assertCalendarBulkRequest(sharedRoutePageSyncCalendarReload.request().postDataJSON(), 30, sharedRoutePeerIds, 'GBP');
        const sharedRoutePageSyncMetadataResponse = await sharedRoutePageSyncMetadataResponsePromise;
        expect(sharedRoutePageSyncMetadataResponse.ok()).toBe(true);
        expect(await sharedRoutePageSyncMetadataResponse.finished()).toBeNull();
        const sharedRoutePageSyncFxSection = pageSyncModal.locator('[data-testid="sync-section"][data-section-id="fx"]');
        await expect(sharedRoutePageSyncFxSection).toHaveAttribute('data-target-count', '1');
        await expect(sharedRoutePageSyncFxSection.locator(`[data-testid="sync-result-row"][data-row-id="${readyPeerFxSlug}"]`)).toHaveAttribute('data-status', 'skipped');
        expect(assetSyncRequestCount).toBe(sharedRoutePageSyncAssetRequestsBefore + 1);
        expect(fxSyncRequestCount).toBe(sharedRoutePageSyncFxRequestsBefore + 1);
        expect(fxConvertRequests.slice(sharedRoutePageSyncFxConversionsBefore)).toEqual([
            [
                {
                    from_amount: {code: 'EUR', amount: '1'},
                    to: 'GBP',
                    date_range: {start: ninetyDayRange.start, end: ninetyDayRange.end},
                },
            ],
        ]);
        expect(fxRouteMutationRequestCount).toBe(sharedRoutePageSyncMutationsBefore);
        await pageSyncModal.getByTestId('sync-modal-close').click();
        await expect(pageSyncModal).toBeHidden();

        const sharedRoutePageSyncPriceQueriesBeforeReturn = priceQueryRequestCount;
        const sharedRoutePageSyncComparisonRequestsBeforeReturn = sharedRoutePriceComparisonRequestCount;
        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect.poll(() => readChartLineValues(asset.display_name)).toEqual([771, 772, 777]);
        expect(priceQueryRequestCount).toBe(sharedRoutePageSyncPriceQueriesBeforeReturn);
        expect(sharedRoutePriceComparisonRequestCount).toBe(sharedRoutePageSyncComparisonRequestsBeforeReturn);

        const restoreSharedRoutePeerResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, 'GBP');
        await selectComparisonAsset(readySignalId, readyPeer.id);
        const restoreSharedRoutePeerResponse = await restoreSharedRoutePeerResponsePromise;
        expect(restoreSharedRoutePeerResponse.ok()).toBe(true);
        expect(await restoreSharedRoutePeerResponse.finished()).toBeNull();
        assertPriceComparisonRequest(restoreSharedRoutePeerResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, 'GBP');
        await expect.poll(readPersistedReadyPeerId).toBe(String(readyPeer.id));

        sharedRouteMainSnapshot = null;
        restoringAcceptedPageSyncSnapshot = true;
        const restoreSharedRouteMainResponsePromise = waitForMainPriceResponse(ninetyDayRange, '');
        const restoreSharedRouteComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, ninetyDayRange, asset.currency);
        await openCurrencySelect();
        const restoreSharedRouteEurOption = page.getByTestId('search-select-option-EUR');
        await expect(restoreSharedRouteEurOption).toBeVisible();
        await restoreSharedRouteEurOption.click();
        await expect(currencyTrigger).toHaveAttribute('aria-expanded', 'false');
        const restoreSharedRouteMainResponse = await restoreSharedRouteMainResponsePromise;
        expect(restoreSharedRouteMainResponse.ok()).toBe(true);
        expect(await restoreSharedRouteMainResponse.finished()).toBeNull();
        const restoreSharedRouteComparisonResponse = await restoreSharedRouteComparisonResponsePromise;
        restoringAcceptedPageSyncSnapshot = false;
        priceComparisonSyncSucceeded = true;
        expect(restoreSharedRouteComparisonResponse.ok()).toBe(true);
        expect(await restoreSharedRouteComparisonResponse.finished()).toBeNull();
        assertPriceComparisonRequest(restoreSharedRouteComparisonResponse.request().postDataJSON(), comparisonPeerIds, ninetyDayRange, asset.currency);
        await expectCorrectedPriceComparisonState();
        expect(fxRouteMutationRequestCount).toBe(sharedRouteMutationsBefore);

        // Neither per-item result was accepted. Completion is observed through
        // the native sync button becoming enabled again; only after that
        // barrier is it meaningful to assert that no conversion or comparison
        // successor was launched and that the applied data remains visible.
        nextAssetSyncStatus = 'failed';
        nextFxSyncStatus = 'failed';
        const bothFailedAssetSyncRequestsBefore = assetSyncRequestCount;
        const bothFailedFxSyncRequestsBefore = fxSyncRequestCount;
        const bothFailedPriceQueryRequestsBefore = priceQueryRequestCount;
        const bothFailedCalendarRequestsBefore = calendarRequestCount;
        const bothFailedCorrectedResponsesBefore = correctedPriceComparisonResponseCount;
        const bothFailedConvertRequestsBefore = fxConvertRequestCount;
        const bothFailedAssetSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const bothFailedAssetSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const bothFailedFxSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const bothFailedFxSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        await activateComparisonAssetSync(readySignalId);

        const bothFailedAssetSyncRequest = await bothFailedAssetSyncRequestPromise;
        assertAssetSyncRequest(bothFailedAssetSyncRequest.postDataJSON(), readyPeer.id, ninetyDayPriceSyncRange);
        const bothFailedAssetSyncResponse = await bothFailedAssetSyncResponsePromise;
        expect(bothFailedAssetSyncResponse.ok()).toBe(true);
        expect(await bothFailedAssetSyncResponse.finished()).toBeNull();
        expect(await bothFailedAssetSyncResponse.json()).toMatchObject({
            success_count: 0,
            results: [{asset_id: readyPeer.id, status: 'failed'}],
        });

        const bothFailedFxSyncRequest = await bothFailedFxSyncRequestPromise;
        assertFxSyncRequest(bothFailedFxSyncRequest.postDataJSON(), readyPeerRequiredFxSlugs, ninetyDayPriceSyncRange);
        const bothFailedFxSyncResponse = await bothFailedFxSyncResponsePromise;
        expect(bothFailedFxSyncResponse.ok()).toBe(true);
        expect(await bothFailedFxSyncResponse.finished()).toBeNull();
        expect(await bothFailedFxSyncResponse.json()).toMatchObject({
            success_count: 0,
            results: expectedFxSyncResults(readyPeerRequiredFxSlugs, 'failed'),
        });

        await expectFocusedAssetSyncIdle(readySignalId);
        expect(assetSyncRequestCount).toBe(bothFailedAssetSyncRequestsBefore + 1);
        expect(fxSyncRequestCount).toBe(bothFailedFxSyncRequestsBefore + 1);
        expect(fxRouteMutationRequestCount).toBe(0);
        expect(priceQueryRequestCount).toBe(bothFailedPriceQueryRequestsBefore);
        expect(calendarRequestCount).toBe(bothFailedCalendarRequestsBefore);
        expect(correctedPriceComparisonResponseCount).toBe(bothFailedCorrectedResponsesBefore);
        expect(fxConvertRequestCount).toBe(bothFailedConvertRequestsBefore);
        await expectCorrectedPriceComparisonState();

        const restoreCalendarDiagnosticsResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const restoreCalendarDiagnosticsRequest = (await restoreCalendarDiagnosticsResponsePromise).request();
        assertCalendarBulkRequest(restoreCalendarDiagnosticsRequest.postDataJSON(), 30);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expectCalendarPeerDiagnostics();
        await expect(requiredFxIssues).toHaveCount(0);

        const exactRangeRequest = await commitSyntheticRange(exactBoundaryRange, false);
        assertCalendarRequest(exactRangeRequest.postDataJSON(), 30);
        assertCalendarBulkRequest(exactRangeRequest.postDataJSON(), 30);
        assertMainDateRange(exactRangeRequest.postDataJSON(), exactBoundaryRange);

        const exactBoundaryResponsePromise = waitForCalendarResponse(365);
        await chart.getByTestId('asset-calendar-window-1y').click();
        const exactBoundaryResponse = await exactBoundaryResponsePromise;
        expect(exactBoundaryResponse.ok()).toBe(true);
        expect(await exactBoundaryResponse.finished()).toBeNull();
        const exactBoundaryRequest = exactBoundaryResponse.request();
        assertCalendarRequest(exactBoundaryRequest.postDataJSON(), 365);
        assertCalendarBulkRequest(exactBoundaryRequest.postDataJSON(), 365);
        assertMainDateRange(exactBoundaryRequest.postDataJSON(), exactBoundaryRange);

        const exactBoundaryPayload = (await exactBoundaryResponse.json()) as {
            items?: Array<{
                asset_id?: number;
                prices?: unknown[];
                events?: unknown[];
                errors?: unknown[];
                signals?: CalendarSignalResultFixture[];
            }>;
        };
        const exactBoundaryPeer = exactBoundaryPayload.items?.find((item) => item.asset_id === readyPeer.id);
        expect(exactBoundaryPeer, `calendar response must contain ready peer ${readyPeer.id}`).toMatchObject({
            asset_id: readyPeer.id,
            prices: [],
            events: successorReadyEvents,
            errors: [],
        });
        const exactBoundaryPeerSignal = exactBoundaryPeer?.signals?.find((signal) => signal.instance_id === calendarInstanceId && signal.signal_code === calendarSignalCode);
        expect(exactBoundaryPeerSignal).toMatchObject({
            status: 'ok',
            normalized_params: {window_days: 365},
            warnings: [],
            error: null,
        });
        const exactBoundaryPeerSeries = exactBoundaryPeerSignal?.series.find((series) => series.key === 'calendar_return');
        expect(exactBoundaryPeerSeries?.points).toEqual([
            {
                date: exactBoundaryRange.end,
                value: 16,
                provenance: {
                    status: 'available',
                    reference_target_date: exactBoundaryRange.start,
                    current_price_date: '2026-09-11',
                    current_price_days_back: 3,
                    reference_price_date: exactBoundaryRange.start,
                    reference_price_days_back: 0,
                    current_fx_date: null,
                    current_fx_days_back: null,
                    reference_fx_date: null,
                    reference_fx_days_back: null,
                },
            },
        ]);
        await expect(chart).toHaveAttribute('data-window-days', '365');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(chart).toHaveAttribute('data-calendar-comparison-ready', String(readyPeer.id));
        await expect(chart).toHaveAttribute('data-calendar-comparison-partial', String(partialPeer.id));
        await expect(chart).toHaveAttribute('data-calendar-comparison-unavailable', String(unavailablePeer.id));
        await expect(chart).toHaveAttribute('data-calendar-comparison-error', calendarErrorPeerIds);
        await expectCalendarPeerDiagnostics();

        const restoreLongRangeRequest = await commitSyntheticRange(longRange, false);
        assertCalendarRequest(restoreLongRangeRequest.postDataJSON(), 365);
        assertCalendarBulkRequest(restoreLongRangeRequest.postDataJSON(), 365);
        assertMainDateRange(restoreLongRangeRequest.postDataJSON(), longRange);
        const restoreBoundaryOneMonthResponsePromise = waitForCalendarResponse(30);
        await chart.getByTestId('asset-calendar-window-1m').click();
        const restoreBoundaryOneMonthRequest = (await restoreBoundaryOneMonthResponsePromise).request();
        assertCalendarRequest(restoreBoundaryOneMonthRequest.postDataJSON(), 30);
        assertCalendarBulkRequest(restoreBoundaryOneMonthRequest.postDataJSON(), 30);
        assertMainDateRange(restoreBoundaryOneMonthRequest.postDataJSON(), longRange);
        await expect(chart).toHaveAttribute('data-window-days', '30');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expectCalendarPeerDiagnostics();

        // A request whose peer identity is still current may finish after a
        // style-only signal edit. This proves the fingerprint is deliberately
        // about Calendar peers, not object identity, and that the main
        // Calendar snapshot is still allowed to reach ready.
        const samePeerCalendarGate = deferCalendarResponse(7, 'ready');
        const samePeerCalendarRequestPromise = waitForCalendarRequest(7);
        const samePeerCalendarResponsePromise = waitForCalendarResponse(7);
        const samePeerCalendarRequestCount = calendarRequestCount;
        await chart.getByTestId('asset-calendar-window-1w').click();
        const samePeerCalendarRequest = await samePeerCalendarRequestPromise;
        assertCalendarBulkRequest(samePeerCalendarRequest.postDataJSON(), 7);
        expect(calendarRequestCount).toBe(samePeerCalendarRequestCount + 1);

        await expect(styleToggle, 'the visible comparison style must expose its line-style button').toBeVisible();
        await styleToggle.click();
        await expect(stylePopover).toBeVisible();
        await readySignalStyle.getByRole('button', {name: 'dashed', exact: true}).click();
        await expect
            .poll(async () => {
                const persisted = await readPersistedPairSettings(chartSettingsStorageKey);
                const persistedSignals = Array.isArray(persisted?.signals) ? persisted.signals : [];
                const readyConfig = persistedSignals.find((candidate): candidate is Record<string, unknown> => candidate !== null && typeof candidate === 'object' && (candidate as Record<string, unknown>).id === readySignalId);
                const style = readyConfig?.style;
                return style !== null && typeof style === 'object' ? (style as Record<string, unknown>).lineType : null;
            })
            .toBe('dashed');
        await page.keyboard.press('Escape');
        await expect(stylePopover).toHaveCount(0);
        expect(calendarRequestCount).toBe(samePeerCalendarRequestCount + 1);

        samePeerCalendarGate.release();
        const samePeerCalendarResponse = await samePeerCalendarResponsePromise;
        expect(samePeerCalendarResponse.ok()).toBe(true);
        expect(await samePeerCalendarResponse.finished()).toBeNull();
        assertCalendarBulkRequest(samePeerCalendarResponse.request().postDataJSON(), 7);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', '7');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(chart).toHaveAttribute('data-calendar-comparison-ready', String(readyPeer.id));
        await expect(chart).toHaveAttribute('data-calendar-comparison-partial', String(partialPeer.id));
        await expectAssetDetailChartCanvas(page);

        const restoreRaceWindowResponsePromise = waitForCalendarResponse(30);
        await chart.getByTestId('asset-calendar-window-1m').click();
        const restoreRaceWindowRequest = (await restoreRaceWindowResponsePromise).request();
        assertCalendarBulkRequest(restoreRaceWindowRequest.postDataJSON(), 30);
        await expect(chart).toHaveAttribute('data-window-days', '30');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        // Earlier sync assertions deliberately leave several actionable toasts
        // on screen. Dismiss each observed toast and wait for its keyed outro
        // before opening the asset selector, otherwise the stack can intercept
        // the option click for longer than the oldest toast's own lifetime.
        const toastDismissButtons = page.getByTestId('toast-dismiss');
        while (true) {
            const countBeforeDismiss = await toastDismissButtons.count();
            if (countBeforeDismiss === 0) break;
            await toastDismissButtons.first().click();
            await expect.poll(() => toastDismissButtons.count()).toBeLessThan(countBeforeDismiss);
        }
        await expect(page.getByTestId(/^toast-(?:error|info|success|warning)$/)).toHaveCount(0);

        // Hold a Calendar response containing the old peer's return series and
        // dividend events. Price mode does not supersede the Calendar request,
        // so its main snapshot may still finish; changing the peer in Price,
        // however, changes the captured Calendar-peer fingerprint. The late
        // payload must therefore be barred from restoring old peer
        // views/problems/events (including ECharts scatter markers).
        const staleCalendarPeerGate = deferCalendarResponse(7, 'ready');
        const staleCalendarPeerRequestPromise = waitForCalendarRequest(7);
        const staleCalendarPeerResponsePromise = waitForCalendarResponse(7);
        await chart.getByTestId('asset-calendar-window-1w').click();
        const staleCalendarPeerRequest = await staleCalendarPeerRequestPromise;
        assertCalendarBulkRequest(staleCalendarPeerRequest.postDataJSON(), 7);
        await expect(chart).toHaveAttribute('data-series-state', 'loading');

        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(readySignalCard.getByRole('button', {name: '💰2', exact: true})).toBeVisible();
        await expect.poll(readChartEventMarkerAssetLabels).toContain(readyPeer.display_name);

        const calendarRequestsBeforePricePeerReplacement = calendarRequestCount;
        const replacementPriceResponsePromise = waitForPriceComparisonResponse(replacementPeerIds, longRange, asset.currency);
        await selectComparisonAsset(readySignalId, replacementPeer.id);
        const replacementPriceResponse = await replacementPriceResponsePromise;
        expect(replacementPriceResponse.ok()).toBe(true);
        expect(await replacementPriceResponse.finished()).toBeNull();
        assertPriceComparisonRequest(replacementPriceResponse.request().postDataJSON(), replacementPeerIds, longRange, asset.currency);
        expect(calendarRequestCount).toBe(calendarRequestsBeforePricePeerReplacement);
        await expect.poll(readPersistedReadyPeerId).toBe(String(replacementPeer.id));
        await expect(readySignalCard.getByRole('button', {name: '📈3', exact: true})).toBeVisible();
        await expect(readySignalCard.getByRole('button', {name: '💰2', exact: true})).toHaveCount(0);
        await expectAssetDetailChartCanvas(page);
        await expect.poll(readChartEventMarkerAssetLabels).toEqual([]);

        staleCalendarPeerGate.release();
        const staleCalendarPeerResponse = await staleCalendarPeerResponsePromise;
        expect(staleCalendarPeerResponse.ok()).toBe(true);
        expect(await staleCalendarPeerResponse.finished()).toBeNull();
        assertCalendarBulkRequest(staleCalendarPeerResponse.request().postDataJSON(), 7);
        const staleCalendarPeerPayload = (await staleCalendarPeerResponse.json()) as {items?: Array<{asset_id?: number; events?: unknown[]}>};
        expect(staleCalendarPeerPayload.items?.find((item) => item.asset_id === readyPeer.id)?.events).toEqual(successorReadyEvents);
        await expect.poll(readPersistedReadyPeerId).toBe(String(replacementPeer.id));
        await expect(readySignalCard.getByRole('button', {name: '💰2', exact: true})).toHaveCount(0);
        await expect.poll(readChartEventMarkerAssetLabels).toEqual([]);

        const replacementCalendarResponsePromise = waitForCalendarResponse(7);
        await calendarPrimary.click();
        const replacementCalendarRequest = (await replacementCalendarResponsePromise).request();
        assertCalendarBulkRequest(replacementCalendarRequest.postDataJSON(), 7, replacementPeerIds);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(chart).toHaveAttribute('data-calendar-comparison-ready', String(replacementPeer.id));
        await expect(chart).toHaveAttribute('data-calendar-comparison-partial', String(partialPeer.id));

        const restoreReplacementWindowResponsePromise = waitForCalendarResponse(30);
        await chart.getByTestId('asset-calendar-window-1m').click();
        const restoreReplacementWindowRequest = (await restoreReplacementWindowResponsePromise).request();
        assertCalendarBulkRequest(restoreReplacementWindowRequest.postDataJSON(), 30, replacementPeerIds);
        await expect(chart).toHaveAttribute('data-window-days', '30');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        // CAD/EUR is intentionally absent from the configured route fixture.
        // Syncing that peer may still call the Asset endpoint, but it must not
        // register the missing pair or send an FX sync implicitly.
        expect(configuredFxSlugs).not.toContain(replacementPeerFxSlug);
        nextAssetSyncStatus = 'failed';
        const missingPairAssetSyncRequestsBefore = assetSyncRequestCount;
        const missingPairFxSyncRequestsBefore = fxSyncRequestCount;
        const missingPairPriceQueryRequestsBefore = priceQueryRequestCount;
        const missingPairCalendarRequestsBefore = calendarRequestCount;
        const missingPairAssetSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const missingPairAssetSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        await activateComparisonAssetSync(readySignalId);

        const missingPairAssetSyncRequest = await missingPairAssetSyncRequestPromise;
        expect(missingPairAssetSyncRequest.postDataJSON()).toEqual([
            {
                asset_id: replacementPeer.id,
                date_range: {
                    start: longCalendarSyncRange.start,
                    end: longCalendarSyncRange.end,
                },
            },
        ]);
        const missingPairAssetSyncResponse = await missingPairAssetSyncResponsePromise;
        expect(missingPairAssetSyncResponse.ok()).toBe(true);
        expect(await missingPairAssetSyncResponse.finished()).toBeNull();
        expect(await missingPairAssetSyncResponse.json()).toMatchObject({
            success_count: 0,
            results: [{asset_id: replacementPeer.id, status: 'failed'}],
        });
        await expectFocusedAssetSyncIdle(readySignalId);
        expect(assetSyncRequestCount).toBe(missingPairAssetSyncRequestsBefore + 1);
        expect(fxSyncRequestCount).toBe(missingPairFxSyncRequestsBefore);
        expect(fxRouteMutationRequestCount).toBe(0);
        expect(priceQueryRequestCount).toBe(missingPairPriceQueryRequestsBefore);
        expect(calendarRequestCount).toBe(missingPairCalendarRequestsBefore);
        await expect(chart).toHaveAttribute('data-calendar-comparison-ready', String(replacementPeer.id));
        await expect(chart).toHaveAttribute('data-calendar-comparison-partial', String(partialPeer.id));

        // Top-bar Calendar sync uses only routes that already exist for the
        // active facts. The missing CAD/EUR remediation remains a separate user
        // action, and the removed ready peer's USD event route is no longer owned.
        const replacementPageSyncAssetIds = [assetId, ...replacementPeerIds];
        const replacementPageSyncFxSlugs = configuredFxSlugs.filter((slug) => slug !== readyPeerEventFxSlug);
        expect(replacementPageSyncFxSlugs).not.toContain(replacementPeerFxSlug);
        const replacementPageSyncAssetStatuses = new Map<number, SyncStatusFixture>(replacementPageSyncAssetIds.map((pageSyncAssetId, index) => [pageSyncAssetId, index % 2 === 0 ? 'failed' : 'skipped']));
        const replacementPageSyncFxStatuses = new Map<string, SyncStatusFixture>(replacementPageSyncFxSlugs.map((slug, index) => [slug, index % 2 === 0 ? 'skipped' : 'failed']));
        nextAssetSyncStatusesById = replacementPageSyncAssetStatuses;
        nextFxSyncStatusesBySlug = replacementPageSyncFxStatuses;
        priceComparisonSyncSucceeded = false;
        const replacementPageSyncAssetRequestsBefore = assetSyncRequestCount;
        const replacementPageSyncFxRequestsBefore = fxSyncRequestCount;
        const replacementPageSyncFxConversionsBefore = fxConvertRequestCount;
        const replacementPageSyncRouteMutationsBefore = fxRouteMutationRequestCount;
        const replacementPageSyncAssetRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const replacementPageSyncAssetResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const replacementPageSyncFxRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const replacementPageSyncFxResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const replacementPageSyncCalendarResponsePromise = waitForCalendarResponseForRange(30, longRange);
        const replacementPageSyncMetadataResponsePromise = page.waitForResponse((response) => response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/v1/assets/provider/assignments', {timeout: 10_000});
        await expect(pageSyncButton).toBeEnabled();
        await pageSyncButton.click();
        await expect(pageSyncModal).toBeVisible();
        await expect(pageSyncStart).toBeEnabled();
        await pageSyncStart.click();

        const replacementPageSyncAssetRequest = await replacementPageSyncAssetRequestPromise;
        const replacementPageSyncAssetQueries = parseQueries(replacementPageSyncAssetRequest.postDataJSON());
        expect(replacementPageSyncAssetQueries.map((query) => query.asset_id).sort((left, right) => Number(left) - Number(right))).toEqual([...replacementPageSyncAssetIds].sort((left, right) => left - right));
        expect(replacementPageSyncAssetQueries.every((query) => query.date_range?.start === longRange.start && query.date_range.end === longRange.end)).toBe(true);
        const replacementPageSyncFxRequest = await replacementPageSyncFxRequestPromise;
        const replacementPageSyncFxPayload = replacementPageSyncFxRequest.postDataJSON() as FxSyncRequest;
        expect(Array.isArray(replacementPageSyncFxPayload.pairs) ? [...replacementPageSyncFxPayload.pairs].sort() : replacementPageSyncFxPayload.pairs).toEqual(replacementPageSyncFxSlugs);
        expect(replacementPageSyncFxPayload).toMatchObject({
            start: longRange.start,
            end: longRange.end,
        });
        expect(replacementPageSyncFxPayload.pairs).not.toContain(replacementPeerFxSlug);
        expect(replacementPageSyncFxPayload.pairs).not.toContain(readyPeerEventFxSlug);

        const replacementPageSyncAssetResponse = await replacementPageSyncAssetResponsePromise;
        expect(replacementPageSyncAssetResponse.ok()).toBe(true);
        expect(await replacementPageSyncAssetResponse.finished()).toBeNull();
        const replacementPageSyncFxResponse = await replacementPageSyncFxResponsePromise;
        expect(replacementPageSyncFxResponse.ok()).toBe(true);
        expect(await replacementPageSyncFxResponse.finished()).toBeNull();
        const replacementPageSyncCalendarResponse = await replacementPageSyncCalendarResponsePromise;
        expect(replacementPageSyncCalendarResponse.ok()).toBe(true);
        expect(await replacementPageSyncCalendarResponse.finished()).toBeNull();
        assertCalendarBulkRequest(replacementPageSyncCalendarResponse.request().postDataJSON(), 30, replacementPeerIds);
        assertMainDateRange(replacementPageSyncCalendarResponse.request().postDataJSON(), longRange);
        const replacementPageSyncMetadataResponse = await replacementPageSyncMetadataResponsePromise;
        expect(replacementPageSyncMetadataResponse.ok()).toBe(true);
        expect(await replacementPageSyncMetadataResponse.finished()).toBeNull();
        const replacementPageSyncFxSection = pageSyncModal.locator('[data-testid="sync-section"][data-section-id="fx"]');
        await expect(replacementPageSyncFxSection).toHaveAttribute('data-target-count', String(replacementPageSyncFxSlugs.length));
        for (const [slug, status] of replacementPageSyncFxStatuses) {
            await expect(replacementPageSyncFxSection.locator(`[data-testid="sync-result-row"][data-row-id="${slug}"]`)).toHaveAttribute('data-status', status);
        }
        expect(assetSyncRequestCount).toBe(replacementPageSyncAssetRequestsBefore + 1);
        expect(fxSyncRequestCount).toBe(replacementPageSyncFxRequestsBefore + 1);
        const replacementPageSyncFxRefillCalls = fxConvertRequests.slice(replacementPageSyncFxConversionsBefore);
        expect(replacementPageSyncFxRefillCalls).toHaveLength(4);
        expect(replacementPageSyncFxRefillCalls.every((requests) => requests.length === 1)).toBe(true);
        const replacementPageSyncFxRefills = replacementPageSyncFxRefillCalls.flat();
        expect(replacementPageSyncFxRefills).toHaveLength(4);
        const replacementPageSyncFxRefillSlugs = replacementPageSyncFxRefills.map((request) => [request.from_amount.code, request.to].sort().join('-')).sort();
        expect(replacementPageSyncFxRefillSlugs).toEqual([...replacementPageSyncFxSlugs].sort());
        expect(new Set(replacementPageSyncFxRefillSlugs).size).toBe(replacementPageSyncFxRefillSlugs.length);
        for (const refill of replacementPageSyncFxRefills) {
            expect(refill.date_range).toEqual({start: longRange.start, end: longRange.end});
        }
        expect(replacementPageSyncFxRefillSlugs).not.toContain(replacementPeerFxSlug);
        expect(replacementPageSyncFxRefillSlugs).not.toContain(readyPeerEventFxSlug);
        expect(fxConvertRequestCount).toBe(replacementPageSyncFxConversionsBefore + 4);
        expect(fxRouteMutationRequestCount).toBe(replacementPageSyncRouteMutationsBefore);
        await expect(chart).toHaveAttribute('data-calendar-comparison-ready', String(replacementPeer.id));
        await expect(chart).toHaveAttribute('data-calendar-comparison-partial', String(partialPeer.id));
        await pageSyncModal.getByTestId('sync-modal-close').click();
        await expect(pageSyncModal).toBeHidden();

        const restoreReadyCalendarRequestCount = calendarRequestCount;
        const restoreReadyResponsePromise = waitForCalendarResponse(30);
        await selectComparisonAsset(readySignalId, readyPeer.id);
        const restoreReadyRequest = (await restoreReadyResponsePromise).request();
        assertCalendarBulkRequest(restoreReadyRequest.postDataJSON(), 30);
        expect(calendarRequestCount).toBe(restoreReadyCalendarRequestCount + 1);
        await expect(chart).toHaveAttribute('data-calendar-comparison-ready', String(readyPeer.id));
        await expect(chart).toHaveAttribute('data-calendar-comparison-partial', String(partialPeer.id));

        const startDeferredAcceptedComparisonSync = async () => {
            const assetGate = deferNextAssetSyncResponse();
            const fxGate = deferNextFxSyncResponse();
            nextAssetSyncStatus = 'ok';
            nextFxSyncStatus = 'partial';
            const assetRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
            const assetResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
            const fxRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
            const fxResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
            await activateComparisonAssetSync(readySignalId);

            const assetRequest = await assetRequestPromise;
            const fxRequest = await fxRequestPromise;
            assertAssetSyncRequest(assetRequest.postDataJSON(), readyPeer.id, longCalendarSyncRange);
            assertFxSyncRequest(fxRequest.postDataJSON(), readyPeerRequiredFxSlugs, longCalendarSyncRange);

            return async () => {
                assetGate.release();
                fxGate.release();
                const assetResponse = await assetResponsePromise;
                expect(assetResponse.ok()).toBe(true);
                expect(await assetResponse.finished()).toBeNull();
                expect(await assetResponse.json()).toMatchObject({
                    success_count: 1,
                    results: [{asset_id: readyPeer.id, status: 'ok'}],
                });
                const fxResponse = await fxResponsePromise;
                expect(fxResponse.ok()).toBe(true);
                expect(await fxResponse.finished()).toBeNull();
                expect(await fxResponse.json()).toMatchObject({
                    success_count: readyPeerRequiredFxSlugs.length,
                    results: expectedFxSyncResults(readyPeerRequiredFxSlugs, 'partial'),
                });
                await expectFocusedAssetSyncIdle(readySignalId);
            };
        };

        const signalCardsBeforeAdd = await readSignalCardTestIds(signalsPanel);
        const finishAddGuardSync = await startDeferredAcceptedComparisonSync();
        const addGuardPriceQueriesBefore = priceQueryRequestCount;
        const addCalendarRequestCount = calendarRequestCount;
        await comparisonSelectButton.click();
        await expect(signalsPanel.getByTestId('signal-tree-option-asset-comparison')).toBeVisible();
        await signalsPanel.getByTestId('signal-tree-option-asset-comparison').click();
        await expect.poll(async () => (await readSignalCardTestIds(signalsPanel)).length).toBe(signalCardsBeforeAdd.length + 1);
        const signalCardsAfterAdd = await readSignalCardTestIds(signalsPanel);
        const addedCardTestIds = new Set(signalCardsAfterAdd.filter((testId) => !signalCardsBeforeAdd.includes(testId)));
        expect(addedCardTestIds.size).toBe(1);
        const addedCardTestId = addedCardTestIds.values().next().value;
        if (!addedCardTestId) {
            throw new Error('Adding an Asset comparison did not create one identifiable signal card');
        }
        const addedSignalId = addedCardTestId.slice('signal-card-'.length);
        const addedSignalCard = signalsPanel.getByTestId(addedCardTestId);
        await expect(addedSignalCard).toBeVisible();
        await expect(addedSignalCard).toHaveAttribute('data-signal-type', 'asset-comparison');
        await expect(addedSignalCard.getByTestId(`signal-param-${addedSignalId}-assetId`)).toBeVisible();
        await expect(addedSignalCard.getByTestId(`signal-style-${addedSignalId}`)).toBeVisible();
        const addedSignalRemove = addedSignalCard.getByTestId(`signal-remove-${addedSignalId}`);
        await expect(addedSignalRemove).toBeVisible();
        expect(priceQueryRequestCount).toBe(addGuardPriceQueriesBefore);
        expect(calendarRequestCount).toBe(addCalendarRequestCount);
        await finishAddGuardSync();
        expect(priceQueryRequestCount).toBe(addGuardPriceQueriesBefore);
        expect(calendarRequestCount).toBe(addCalendarRequestCount);

        const addedPeerIds = [...comparisonPeerIds, replacementPeer.id];
        const finishParamGuardSync = await startDeferredAcceptedComparisonSync();
        const addedResponsePromise = waitForCalendarResponse(30);
        await selectComparisonAsset(addedSignalId, replacementPeer.id);
        const addedRequest = (await addedResponsePromise).request();
        assertCalendarBulkRequest(addedRequest.postDataJSON(), 30, addedPeerIds);
        expect(calendarRequestCount).toBe(addCalendarRequestCount + 1);
        await expect(chart).toHaveAttribute('data-calendar-comparison-ready', `${readyPeer.id},${replacementPeer.id}`);
        await expect(chart).toHaveAttribute('data-calendar-comparison-partial', String(partialPeer.id));
        const paramGuardPriceQueriesAfterChange = priceQueryRequestCount;
        const paramGuardCalendarRequestsAfterChange = calendarRequestCount;
        await finishParamGuardSync();
        expect(priceQueryRequestCount).toBe(paramGuardPriceQueriesAfterChange);
        expect(calendarRequestCount).toBe(paramGuardCalendarRequestsAfterChange);

        const finishRemoveGuardSync = await startDeferredAcceptedComparisonSync();
        const removeCalendarRequestCount = calendarRequestCount;
        const removedResponsePromise = waitForCalendarResponse(30);
        await addedSignalRemove.click();
        const removedRequest = (await removedResponsePromise).request();
        assertCalendarBulkRequest(removedRequest.postDataJSON(), 30);
        expect(calendarRequestCount).toBe(removeCalendarRequestCount + 1);
        await expect.poll(async () => await readSignalCardTestIds(signalsPanel)).toEqual(signalCardsBeforeAdd);
        await expect(chart).toHaveAttribute('data-calendar-comparison-ready', String(readyPeer.id));
        await expect(chart).toHaveAttribute('data-calendar-comparison-partial', String(partialPeer.id));
        const removeGuardPriceQueriesAfterChange = priceQueryRequestCount;
        const removeGuardCalendarRequestsAfterChange = calendarRequestCount;
        await finishRemoveGuardSync();
        expect(priceQueryRequestCount).toBe(removeGuardPriceQueriesAfterChange);
        expect(calendarRequestCount).toBe(removeGuardCalendarRequestsAfterChange);

        await aestheticsToggle.click();
        await expect(aestheticsPanel).toBeVisible();
        const baselineSwitch = aestheticsPanel.getByTestId('chart-aesthetic-baseline');
        const areaFillSwitch = aestheticsPanel.getByTestId('chart-aesthetic-area-fill');
        const gridLinesSwitch = aestheticsPanel.getByTestId('chart-aesthetic-grid-lines');
        const staleGradientSwitch = aestheticsPanel.getByTestId('chart-aesthetic-stale-gradient');
        for (const aestheticsSwitch of [baselineSwitch, areaFillSwitch, gridLinesSwitch, staleGradientSwitch]) {
            await expect(aestheticsSwitch).toBeVisible();
            await expect(aestheticsSwitch).toBeEnabled();
            await expect(aestheticsSwitch).toHaveAttribute('aria-pressed', 'true');
        }
        const percentageAxisRow = aestheticsPanel.getByTestId('chart-axis-row-primary-percentage');
        await expect(percentageAxisRow).toBeVisible();
        await expect(aestheticsPanel.getByTestId('chart-axis-row-primary-absolute')).toHaveCount(0);
        await percentageAxisRow.getByTestId('chart-axis-primary-percentage-custom').click();
        const percentageAxisMin = percentageAxisRow.getByTestId('chart-axis-primary-percentage-min');
        const percentageAxisMax = percentageAxisRow.getByTestId('chart-axis-primary-percentage-max');
        await expect(percentageAxisMin).toBeVisible();
        await expect(percentageAxisMax).toBeVisible();
        if ((page.viewportSize()?.width ?? Number.POSITIVE_INFINITY) <= 768) {
            for (const input of [percentageAxisMin, percentageAxisMax]) {
                const typography = await input.evaluate((element) => {
                    const inputStyle = getComputedStyle(element);
                    const parentStyle = element.parentElement ? getComputedStyle(element.parentElement) : null;
                    return {
                        fontFamily: inputStyle.fontFamily,
                        inheritedFontFamily: parentStyle?.fontFamily ?? null,
                        fontSize: inputStyle.fontSize,
                        lineHeight: inputStyle.lineHeight,
                    };
                });
                expect(typography).toEqual({
                    fontFamily: typography.inheritedFontFamily,
                    inheritedFontFamily: typography.inheritedFontFamily,
                    fontSize: '16px',
                    lineHeight: '20px',
                });
            }
        }
        await percentageAxisMin.fill('-25');
        await expect(percentageAxisMin).toHaveValue('-25');
        await percentageAxisMax.fill('75');
        await expect(percentageAxisMax).toHaveValue('75');
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                axisScales: {
                    percentage: {mode: 'custom', min: -25, max: 75},
                },
            });

        await expect(measuresSection).toHaveAttribute('data-mode', 'calendar-return');
        await expect(measuresPanel).toBeHidden();
        await expect(measuresPanel.getByTestId('dt-header-deltaPct')).toHaveCount(1);
        await page.getByTestId('asset-detail-add-measure-btn').click();
        await expect(calendarMeasuresPanel).toBeVisible();
        await expect(calendarMeasuresPanel.getByTestId('dt-header-valueStart')).toBeVisible();
        await expect(calendarMeasuresPanel.getByTestId('dt-header-valueEnd')).toBeVisible();
        await expect(calendarMeasuresPanel.getByTestId('dt-header-deltaAbs')).toBeVisible();
        await expect(calendarMeasuresPanel.getByTestId('dt-header-days')).toBeVisible();
        await expect(calendarMeasuresPanel.getByTestId('dt-header-deltaPct')).toHaveCount(0);
        await expect(calendarMeasuresPanel.getByTestId('dt-header-annualizedPct')).toHaveCount(0);

        const expectedCalendarMeasureRowIds = ['main', `sig-${readyPeer.display_name}`, `sig-${partialPeer.display_name}`].sort();
        await expect.poll(async () => (await readMeasureRowIds(calendarMeasuresPanel)).sort()).toEqual(expectedCalendarMeasureRowIds);

        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(measuresSection).toHaveAttribute('data-mode', 'price');
        await expect(measuresPanel).toBeVisible();
        await expect(calendarMeasuresPanel).toBeHidden();
        await expect.poll(async () => (await readMeasureRowIds(measuresPanel)).sort()).toEqual(expectedPriceMeasureRowIds);
        await expect.poll(async () => (await readMeasureRowIds(calendarMeasuresPanel)).sort()).toEqual(expectedCalendarMeasureRowIds);
        await expect(aestheticsPanel.getByTestId('chart-axis-row-primary-absolute')).toBeVisible();
        await expect(aestheticsPanel.getByTestId('chart-axis-row-primary-percentage')).toHaveCount(0);

        await chart.getByTestId('chart-view-percentage').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'percentage');
        await expect(percentageAxisRow).toBeVisible();
        await expect(percentageAxisMin).toHaveValue('-25');
        await expect(percentageAxisMax).toHaveValue('75');

        await chart.getByTestId('chart-view-absolute').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'absolute');
        await expect(aestheticsPanel.getByTestId('chart-axis-row-primary-absolute')).toBeVisible();
        await expect(aestheticsPanel.getByTestId('chart-axis-row-primary-percentage')).toHaveCount(0);

        const returnWithMountedMeasuresResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const returnWithMountedMeasuresRequest = (await returnWithMountedMeasuresResponsePromise).request();
        assertCalendarBulkRequest(returnWithMountedMeasuresRequest.postDataJSON(), 30);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(measuresSection).toHaveAttribute('data-mode', 'calendar-return');
        await expect(measuresPanel).toBeHidden();
        await expect(calendarMeasuresPanel).toBeVisible();
        await expect(percentageAxisRow).toBeVisible();
        await expect(percentageAxisMin).toHaveValue('-25');
        await expect(percentageAxisMax).toHaveValue('75');

        await percentageAxisRow.getByTestId('chart-axis-primary-percentage-include0').click();
        await expect(percentageAxisMin).toHaveCount(0);
        await expect(percentageAxisMax).toHaveCount(0);
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                axisScales: {
                    percentage: {mode: 'include0'},
                },
            });

        const sevenDayResponsePromise = waitForCalendarResponse(7);
        await chart.getByTestId('asset-calendar-window-1w').click();
        const sevenDayRequest = (await sevenDayResponsePromise).request();
        assertCalendarRequest(sevenDayRequest.postDataJSON(), 7);
        assertCalendarBulkRequest(sevenDayRequest.postDataJSON(), 7);
        await expect(chart).toHaveAttribute('data-window-days', '7');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(chart.getByTestId('asset-calendar-window-1w')).toHaveAttribute('aria-pressed', 'true');

        const thirtyDayResponsePromise = waitForCalendarResponse(30);
        await chart.getByTestId('asset-calendar-window-1m').click();
        const thirtyDayRequest = (await thirtyDayResponsePromise).request();
        assertCalendarRequest(thirtyDayRequest.postDataJSON(), 30);
        assertCalendarBulkRequest(thirtyDayRequest.postDataJSON(), 30);
        await expect(chart).toHaveAttribute('data-window-days', '30');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(chart.getByTestId('asset-calendar-window-1m')).toHaveAttribute('aria-pressed', 'true');
        await expect(chart.getByTestId('asset-calendar-window-1w')).toHaveAttribute('aria-pressed', 'false');
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                calendarReturnWindow: {
                    kind: 'preset',
                    preset: '1m',
                    customAmount: 3,
                    customUnit: 'years',
                },
            });

        const rememberedCustomResponsePromise = waitForCalendarResponse(1095);
        await customWindowButton.click();
        const rememberedCustomRequest = (await rememberedCustomResponsePromise).request();
        assertCalendarBulkRequest(rememberedCustomRequest.postDataJSON(), 1095);
        assertMainDateRange(rememberedCustomRequest.postDataJSON(), longRange);
        await expect(chart).toHaveAttribute('data-window-kind', 'custom');
        await expect(chart).toHaveAttribute('data-window-days', '1095');
        await expect(chart).toHaveAttribute('data-window-amount', '3');
        await expect(chart).toHaveAttribute('data-window-unit', 'years');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                calendarReturnWindow: {
                    kind: 'custom',
                    preset: '1m',
                    customAmount: 3,
                    customUnit: 'years',
                },
            });

        const customAmount = chart.getByTestId('asset-calendar-custom-amount');
        const customUnit = chart.getByTestId('asset-calendar-custom-unit-button');
        await expect(customAmount).toHaveValue('3');
        await expect(customUnit).toBeVisible();

        const twoYearsResponsePromise = waitForCalendarResponse(730);
        await customAmount.fill('2');
        const twoYearsRequest = (await twoYearsResponsePromise).request();
        assertCalendarBulkRequest(twoYearsRequest.postDataJSON(), 730);
        assertMainDateRange(twoYearsRequest.postDataJSON(), longRange);
        await expect(chart).toHaveAttribute('data-window-days', '730');
        await expect(chart).toHaveAttribute('data-window-amount', '2');
        await expect(chart).toHaveAttribute('data-window-unit', 'years');

        const weeksResponsePromise = waitForCalendarResponse(14);
        await selectCalendarUnit(customUnit, 'weeks');
        const weeksRequest = (await weeksResponsePromise).request();
        assertCalendarBulkRequest(weeksRequest.postDataJSON(), 14);
        await expect(chart).toHaveAttribute('data-window-days', '14');
        await expect(chart).toHaveAttribute('data-window-unit', 'weeks');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        const monthsResponsePromise = waitForCalendarResponse(60);
        await selectCalendarUnit(customUnit, 'months');
        const monthsRequest = (await monthsResponsePromise).request();
        assertCalendarBulkRequest(monthsRequest.postDataJSON(), 60);
        await expect(chart).toHaveAttribute('data-window-days', '60');
        await expect(chart).toHaveAttribute('data-window-unit', 'months');
        await expect(chart).toHaveAttribute('data-window-kind', 'custom');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        const threeMonthsResponsePromise = waitForCalendarResponse(90);
        await customAmount.fill('3');
        const threeMonthsRequest = (await threeMonthsResponsePromise).request();
        assertCalendarBulkRequest(threeMonthsRequest.postDataJSON(), 90);
        await expect(chart).toHaveAttribute('data-window-days', '90');
        await expect(chart).toHaveAttribute('data-window-amount', '3');
        await expect(chart).toHaveAttribute('data-window-unit', 'months');

        const yearsResponsePromise = waitForCalendarResponse(1095);
        await selectCalendarUnit(customUnit, 'years');
        const yearsRequest = (await yearsResponsePromise).request();
        assertCalendarBulkRequest(yearsRequest.postDataJSON(), 1095);
        assertMainDateRange(yearsRequest.postDataJSON(), longRange);
        await expect(chart).toHaveAttribute('data-window-days', '1095');
        await expect(chart).toHaveAttribute('data-window-unit', 'years');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        await customUnit.press('Escape');
        await expect(customWindowButton).toBeVisible();
        await expect(customWindowButton).toHaveAttribute('data-active', 'true');
        await customWindowButton.click();
        await expect(customAmount).toHaveValue('3');

        const invalidPriceQueryCount = priceQueryRequestCount;
        const invalidCalendarRequestCount = calendarRequestCount;
        await customAmount.fill('0');
        await expect(customAmount).toHaveAttribute('aria-invalid', 'true');
        await expect(chart).toHaveAttribute('data-window-days', '1095');
        await expect(chart).toHaveAttribute('data-window-amount', '3');
        expect(priceQueryRequestCount).toBe(invalidPriceQueryCount);
        expect(calendarRequestCount).toBe(invalidCalendarRequestCount);
        const validAfterInvalidResponsePromise = waitForCalendarResponse(1460);
        await customAmount.fill('4');
        const validAfterInvalidRequest = (await validAfterInvalidResponsePromise).request();
        assertCalendarBulkRequest(validAfterInvalidRequest.postDataJSON(), 1460);
        assertMainDateRange(validAfterInvalidRequest.postDataJSON(), longRange);
        await expect(chart).toHaveAttribute('data-window-days', '1460');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        expect(priceQueryRequestCount).toBe(invalidPriceQueryCount + 1);
        expect(calendarRequestCount).toBe(invalidCalendarRequestCount + 1);
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                calendarReturnWindow: {
                    kind: 'custom',
                    preset: '1m',
                    customAmount: 4,
                    customUnit: 'years',
                },
            });

        await customAmount.press('Escape');
        await expect(customWindowButton).toBeVisible();
        await expect(customWindowButton).toHaveAttribute('data-active', 'true');
        await customWindowButton.click();
        await expect(customAmount).toHaveValue('4');

        // Seven converted years are 2,555 days, beyond the visible range's
        // 2,406 elapsed days. N is an input-history distance, not a visibility
        // constraint, so the exact positive N remains valid and is requested.
        const longCustomPriceQueryCount = priceQueryRequestCount;
        const longCustomCalendarRequestCount = calendarRequestCount;
        const sevenYearsResponsePromise = waitForCalendarResponse(2555);
        await customAmount.fill('7');
        const sevenYearsRequest = (await sevenYearsResponsePromise).request();
        assertCalendarBulkRequest(sevenYearsRequest.postDataJSON(), 2555);
        assertMainDateRange(sevenYearsRequest.postDataJSON(), longRange);
        await expect(customAmount).toHaveValue('7');
        await expect(customAmount).toHaveAttribute('aria-invalid', 'false');
        await expect(chart).toHaveAttribute('data-window-days', '2555');
        await expect(chart).toHaveAttribute('data-window-amount', '7');
        await expect(chart).toHaveAttribute('data-window-unit', 'years');

        await customAmount.press('Escape');
        await expect(customWindowButton).toBeVisible();
        await expect(customWindowButton).toHaveAttribute('data-active', 'true');
        await expect(chart).toHaveAttribute('data-window-days', '2555');
        await expect(chart).toHaveAttribute('data-window-amount', '7');
        await expect(chart).toHaveAttribute('data-window-unit', 'years');
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                calendarReturnWindow: {
                    kind: 'custom',
                    preset: '1m',
                    customAmount: 7,
                    customUnit: 'years',
                },
            });
        expect(priceQueryRequestCount).toBe(longCustomPriceQueryCount + 1);
        expect(calendarRequestCount).toBe(longCustomCalendarRequestCount + 1);

        const restoredThreeYearsResponsePromise = waitForCalendarResponse(1095);
        await customWindowButton.click();
        await expect(customAmount).toHaveValue('7');
        await customAmount.fill('3');
        const restoredThreeYearsRequest = (await restoredThreeYearsResponsePromise).request();
        assertCalendarBulkRequest(restoredThreeYearsRequest.postDataJSON(), 1095);
        assertMainDateRange(restoredThreeYearsRequest.postDataJSON(), longRange);
        await expect(chart).toHaveAttribute('data-window-days', '1095');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        expect(priceQueryRequestCount).toBe(longCustomPriceQueryCount + 2);
        expect(calendarRequestCount).toBe(longCustomCalendarRequestCount + 2);

        await customAmount.press('Escape');
        await expect(customWindowButton).toBeVisible();
        await expect(customWindowButton).toHaveAttribute('data-active', 'true');
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                calendarReturnWindow: {
                    kind: 'custom',
                    preset: '1m',
                    customAmount: 3,
                    customUnit: 'years',
                },
            });

        const returnMeasureStartInput = calendarMeasuresPanel.getByTestId('date-range-input-start');
        const returnMeasureEndInput = calendarMeasuresPanel.getByTestId('date-range-input-end');
        await expect(calendarMeasuresPanel).toBeVisible();
        await expect.poll(async () => (await readMeasureRowIds(calendarMeasuresPanel)).sort()).toEqual(expectedCalendarMeasureRowIds);
        await expect(returnMeasureStartInput).toHaveValue('2026-08-01');
        await expect(returnMeasureEndInput).toHaveValue('2026-08-02');
        const returnMeasureSourceSnapshot = {
            rowIds: (await readMeasureRowIds(calendarMeasuresPanel)).sort(),
            startDate: await returnMeasureStartInput.inputValue(),
            endDate: await returnMeasureEndInput.inputValue(),
        };
        const expectReturnMeasureSourceSnapshot = async (): Promise<void> => {
            await expect.poll(async () => (await readMeasureRowIds(calendarMeasuresPanel)).sort()).toEqual(returnMeasureSourceSnapshot.rowIds);
            await expect(returnMeasureStartInput).toHaveValue(returnMeasureSourceSnapshot.startDate);
            await expect(returnMeasureEndInput).toHaveValue(returnMeasureSourceSnapshot.endDate);
        };

        // This race owns a completed Return measure. It is intentionally
        // separate from the later Calendar→Price busy-state race, whose
        // contract is that a request without a successor remains current.
        const returnMeasureRefreshCount = calendarRequestCount;
        const returnMeasureRefreshGate = deferCalendarResponse(1095, 'ready');
        const returnMeasureRefreshRequestPromise = waitForCalendarRequest(1095);
        const returnMeasureRefreshResponsePromise = waitForCalendarResponse(1095);
        await refreshButton.click();
        const returnMeasureRefreshRequest = await returnMeasureRefreshRequestPromise;
        assertCalendarRequest(returnMeasureRefreshRequest.postDataJSON(), 1095, true);
        assertCalendarBulkRequest(returnMeasureRefreshRequest.postDataJSON(), 1095);
        assertMainDateRange(returnMeasureRefreshRequest.postDataJSON(), longRange);
        expect(calendarRequestCount).toBe(returnMeasureRefreshCount + 1);

        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(measuresSection).toHaveAttribute('data-mode', 'price');
        await expect(calendarMeasuresPanel).toHaveAttribute('aria-hidden', 'true');
        await expect(calendarMeasuresPanel).toHaveAttribute('inert', '');
        await expect(calendarMeasuresPanel).toBeHidden();
        await expectReturnMeasureSourceSnapshot();

        const returnMeasureComparisonRequestCount = priceComparisonRequestCount;
        returnMeasureRefreshGate.release();
        const returnMeasureRefreshResponse = await returnMeasureRefreshResponsePromise;
        expect(returnMeasureRefreshResponse.ok()).toBe(true);
        expect(await returnMeasureRefreshResponse.finished()).toBeNull();

        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        expect(priceComparisonRequestCount).toBe(returnMeasureComparisonRequestCount);
        await expect(measuresSection).toHaveAttribute('data-mode', 'price');
        await expect(calendarMeasuresPanel).toHaveAttribute('aria-hidden', 'true');
        await expect(calendarMeasuresPanel).toHaveAttribute('inert', '');
        await expect(calendarMeasuresPanel).toBeHidden();
        await expectReturnMeasureSourceSnapshot();

        const reloadedComparisonResponsePromise = waitForPriceComparisonResponse();
        await page.reload();
        await expect(pageRoot).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
        await reloadedComparisonResponsePromise;
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(pricePrimary).toHaveAttribute('aria-pressed', 'true');
        await expect(calendarPrimary).toHaveAttribute('aria-pressed', 'false');
        await expect(chart.getByTestId('chart-view-mode-toggle')).toBeVisible();
        await expect(dateRangePicker).toBeVisible();
        await expect(dateRangeStartInput).toHaveValue(longRange.start);
        await expect(dateRangeEndInput).toHaveValue(longRange.end);
        await expect(chart).toHaveAttribute('data-calendar-range-days', String(longRange.spanDays));
        await chart.getByTestId('chart-view-absolute').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'absolute');
        await chart.getByTestId('chart-type-candlestick').click();
        await expect(chart.getByTestId('candlestick-chart')).toBeVisible();

        const restoredCustomResponsePromise = waitForCalendarResponse(1095);
        await calendarPrimary.click();
        const restoredCustomRequest = (await restoredCustomResponsePromise).request();
        assertCalendarBulkRequest(restoredCustomRequest.postDataJSON(), 1095);
        assertMainDateRange(restoredCustomRequest.postDataJSON(), longRange);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-kind', 'custom');
        await expect(chart).toHaveAttribute('data-window-days', '1095');
        await expect(chart).toHaveAttribute('data-window-amount', '3');
        await expect(chart).toHaveAttribute('data-window-unit', 'years');
        await expect(chart.getByTestId('asset-calendar-window-custom')).toHaveAttribute('data-active', 'true');

        // Shrinking the visible span does not rewrite the selected 3Y history
        // distance. Every positive preset remains available because the
        // backend may resolve factual references before the visible start.
        const ninetyDayCustomRequest = await commitSyntheticRange(ninetyDayRange, false);
        assertCalendarRequest(ninetyDayCustomRequest.postDataJSON(), 1095);
        assertCalendarBulkRequest(ninetyDayCustomRequest.postDataJSON(), 1095);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-kind', 'custom');
        await expect(chart).toHaveAttribute('data-window-days', '1095');
        await expect(chart).toHaveAttribute('data-window-amount', '3');
        await expect(chart).toHaveAttribute('data-window-unit', 'years');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        for (const preset of calendarPresets) {
            await expect(chart.getByTestId(`asset-calendar-window-${preset.key}`)).toBeVisible();
            await expect(chart.getByTestId(`asset-calendar-window-${preset.key}`)).toBeEnabled();
        }
        await expect(customWindowButton).toBeVisible();
        await expect(customWindowButton).toHaveAttribute('data-active', 'true');
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                calendarReturnWindow: {
                    kind: 'custom',
                    preset: '1m',
                    customAmount: 3,
                    customUnit: 'years',
                },
            });

        const thirtyDayCustomRequest = await commitSyntheticRange(thirtyDayRange, false);
        assertCalendarRequest(thirtyDayCustomRequest.postDataJSON(), 1095);
        assertCalendarBulkRequest(thirtyDayCustomRequest.postDataJSON(), 1095);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-kind', 'custom');
        await expect(chart).toHaveAttribute('data-window-days', '1095');
        await expect(chart).toHaveAttribute('data-window-amount', '3');
        await expect(chart).toHaveAttribute('data-window-unit', 'years');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        for (const preset of calendarPresets) {
            await expect(chart.getByTestId(`asset-calendar-window-${preset.key}`)).toBeVisible();
            await expect(chart.getByTestId(`asset-calendar-window-${preset.key}`)).toBeEnabled();
        }
        await expect(customWindowButton).toHaveAttribute('data-active', 'true');
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                calendarReturnWindow: {
                    kind: 'custom',
                    preset: '1m',
                    customAmount: 3,
                    customUnit: 'years',
                },
            });

        // Merely opening and cancelling the still-valid 3Y editor emits no
        // request and leaves the exact N persisted.
        const narrowedCustomPriceQueryCount = priceQueryRequestCount;
        const narrowedCustomCalendarRequestCount = calendarRequestCount;
        await customWindowButton.click();
        await expect(customAmount).toHaveValue('3');
        await expect(customAmount).toHaveAttribute('aria-invalid', 'false');
        await expect(chart).toHaveAttribute('data-window-kind', 'custom');
        await expect(chart).toHaveAttribute('data-window-days', '1095');
        await customAmount.press('Escape');
        await expect(customWindowButton).toBeVisible();
        await expect(customWindowButton).toHaveAttribute('data-active', 'true');
        await expect(chart).toHaveAttribute('data-window-kind', 'custom');
        await expect(chart).toHaveAttribute('data-window-days', '1095');
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                calendarReturnWindow: {
                    kind: 'custom',
                    preset: '1m',
                    customAmount: 3,
                    customUnit: 'years',
                },
            });
        expect(priceQueryRequestCount).toBe(narrowedCustomPriceQueryCount);
        expect(calendarRequestCount).toBe(narrowedCustomCalendarRequestCount);

        // A six-day visible span still requests the selected positive 1,095-day
        // history distance. The factual returns are inside the selected span;
        // their resolved reference dates deliberately precede its start.
        const sixDayResponsePromise = waitForCalendarResponseForRange(1095, sixDayRange);
        const sixDayPriceQueriesBefore = priceQueryRequestCount;
        const sixDayMainRequestsBefore = mainPriceRequestCount;
        const sixDayComparisonRequestsBefore = priceComparisonRequestCount;
        const sixDayCalendarRequestsBefore = calendarRequestCount;
        const sixDayBackendRequestsBefore = backendSignalRequestCount;
        const sixDayRequest = await commitSyntheticRange(sixDayRange, false);
        const sixDayResponse = await sixDayResponsePromise;
        expect(sixDayResponse.ok()).toBe(true);
        expect(await sixDayResponse.finished()).toBeNull();
        assertCalendarRequest(sixDayRequest.postDataJSON(), 1095);
        assertCalendarBulkRequest(sixDayRequest.postDataJSON(), 1095);
        assertMainDateRange(sixDayRequest.postDataJSON(), sixDayRange);
        const sixDayPayload = (await sixDayResponse.json()) as {items?: I60GResponseItem[]};
        const sixDayPrimaryPoints =
            sixDayPayload.items
                ?.find((item) => item.asset_id === assetId)
                ?.signals?.find((signal) => signal.instance_id === calendarInstanceId && signal.signal_code === calendarSignalCode)
                ?.series?.find((series) => series.key === 'calendar_return')?.points ?? [];
        expect(sixDayPrimaryPoints.map((point) => point.date)).toEqual(['2026-08-01', '2026-08-02']);
        expect(sixDayPrimaryPoints.map((point) => point.value)).toEqual([109.5, -54.75]);
        expect(sixDayPrimaryPoints.every((point) => point.date >= sixDayRange.start && point.date <= sixDayRange.end)).toBe(true);
        expect(sixDayPrimaryPoints.every((point) => point.provenance.reference_target_date < sixDayRange.start)).toBe(true);
        expect(priceQueryRequestCount).toBe(sixDayPriceQueriesBefore + 1);
        expect(mainPriceRequestCount).toBe(sixDayMainRequestsBefore);
        expect(priceComparisonRequestCount).toBe(sixDayComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(sixDayCalendarRequestsBefore + 1);
        expect(backendSignalRequestCount).toBe(sixDayBackendRequestsBefore);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-kind', 'custom');
        await expect(chart).toHaveAttribute('data-window-days', '1095');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(pricePrimary).toHaveAttribute('aria-pressed', 'false');
        await expect(calendarPrimary).toHaveAttribute('aria-pressed', 'true');
        await expect(calendarPrimary).toBeEnabled();
        await expect(chart.getByTestId('asset-calendar-window-controls')).toBeVisible();
        await expect.poll(readI60GCalendarChart).toEqual({
            dates: ['2026-08-01', '2026-08-02'],
            main: [109.5, -54.75],
            peers: {
                [readyPeer.display_name]: [13, 16],
                [partialPeer.display_name]: [23, 22],
                [unavailablePeer.display_name]: [null, null],
                [errorPeer.display_name]: [null, null],
                [invalidCalendarPeer.display_name]: [null, null],
            },
            presentPeerLabels: [readyPeer.display_name, partialPeer.display_name].sort(),
        });

        const restoredLongRangeRequest = await commitSyntheticRange(longRange, false);
        assertCalendarRequest(restoredLongRangeRequest.postDataJSON(), 1095);
        assertCalendarBulkRequest(restoredLongRangeRequest.postDataJSON(), 1095);
        assertMainDateRange(restoredLongRangeRequest.postDataJSON(), longRange);
        await expect(calendarPrimary).toBeEnabled();

        const restoreOneMonthResponsePromise = waitForCalendarResponse(30);
        await chart.getByTestId('asset-calendar-window-1m').click();
        const restoreOneMonthRequest = (await restoreOneMonthResponsePromise).request();
        assertCalendarBulkRequest(restoreOneMonthRequest.postDataJSON(), 30);
        assertMainDateRange(restoreOneMonthRequest.postDataJSON(), longRange);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-kind', 'preset');
        await expect(chart).toHaveAttribute('data-window-days', '30');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        const loadingNotice = page.getByTestId('asset-calendar-return-loading');

        // Switching presentation modes must not invalidate the shared price/events
        // request when no successor request exists. This deferred 30-day response
        // is distinct from the empty-price stale 90-day response exercised below.
        const modeSwitchComparisonRequestsBefore = priceComparisonRequestCount;
        const modeSwitchRefreshGate = deferCalendarResponse(30, 'ready');
        const modeSwitchRefreshRequestPromise = waitForCalendarRequest(30);
        await refreshButton.click();
        const modeSwitchRefreshRequest = await modeSwitchRefreshRequestPromise;
        assertCalendarRequest(modeSwitchRefreshRequest.postDataJSON(), 30, true);
        assertCalendarBulkRequest(modeSwitchRefreshRequest.postDataJSON(), 30);

        const modeSwitchRefreshResponsePromise = waitForCalendarResponse(30);
        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(pricePrimary).toHaveAttribute('aria-pressed', 'true');
        await expect(calendarPrimary).toHaveAttribute('aria-pressed', 'false');
        await expect(chart).toHaveAttribute('data-series-state', 'loading');
        await expect(pageRoot).toHaveAttribute('data-busy', 'true');
        await expect(refreshButton).toBeDisabled();
        await expectAssetDetailChartCanvas(page);

        modeSwitchRefreshGate.release();
        const modeSwitchRefreshResponse = await modeSwitchRefreshResponsePromise;
        expect(modeSwitchRefreshResponse.ok()).toBe(true);
        expect(await modeSwitchRefreshResponse.finished()).toBeNull();

        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(pricePrimary).toHaveAttribute('aria-pressed', 'true');
        await expect(calendarPrimary).toHaveAttribute('aria-pressed', 'false');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await expect(refreshButton).toBeEnabled();
        await expectAssetDetailChartCanvas(page);
        expect(priceComparisonRequestCount).toBe(modeSwitchComparisonRequestsBefore);

        const restoredCalendarResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const restoredCalendarRequest = (await restoredCalendarResponsePromise).request();
        assertCalendarRequest(restoredCalendarRequest.postDataJSON(), 30);
        assertCalendarBulkRequest(restoredCalendarRequest.postDataJSON(), 30);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', '30');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        const ninetyDayResponsePromise = waitForCalendarResponse(90);
        await chart.getByTestId('asset-calendar-window-3m').click();
        const ninetyDayRequest = (await ninetyDayResponsePromise).request();
        assertCalendarRequest(ninetyDayRequest.postDataJSON(), 90);
        assertCalendarBulkRequest(ninetyDayRequest.postDataJSON(), 90);
        await expect(chart).toHaveAttribute('data-window-days', '90');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(chart.getByTestId('asset-calendar-window-3m')).toHaveAttribute('aria-pressed', 'true');
        await expect(chart.getByTestId('asset-calendar-window-1m')).toHaveAttribute('aria-pressed', 'false');

        const staleRefreshGate = deferCalendarResponse(90, 'ready');
        const staleRefreshRequestPromise = waitForCalendarRequest(90);
        await refreshButton.click();
        const staleRefreshRequest = await staleRefreshRequestPromise;
        assertCalendarRequest(staleRefreshRequest.postDataJSON(), 90, true);
        assertCalendarBulkRequest(staleRefreshRequest.postDataJSON(), 90);
        await expect(chart).toHaveAttribute('data-window-days', '90');
        await expect(chart).toHaveAttribute('data-series-state', 'loading');
        await expect(pageRoot).toHaveAttribute('data-busy', 'true');
        await expect(loadingNotice).toBeVisible();
        await expect(refreshButton).toBeDisabled();

        const latestPartialGate = deferCalendarResponse(365, 'partial');
        const latestPartialRequestPromise = waitForCalendarRequest(365);
        await chart.getByTestId('asset-calendar-window-1y').click();
        const latestPartialRequest = await latestPartialRequestPromise;
        assertCalendarRequest(latestPartialRequest.postDataJSON(), 365, true);
        assertCalendarBulkRequest(latestPartialRequest.postDataJSON(), 365);
        await expect(chart).toHaveAttribute('data-window-days', '365');
        await expect(chart).toHaveAttribute('data-series-state', 'loading');
        await expect(pageRoot).toHaveAttribute('data-busy', 'true');
        await expect(loadingNotice).toBeVisible();

        const staleRefreshResponsePromise = waitForCalendarResponse(90);
        staleRefreshGate.release();
        const staleRefreshResponse = await staleRefreshResponsePromise;
        expect(staleRefreshResponse.ok()).toBe(true);
        expect(await staleRefreshResponse.finished()).toBeNull();

        // The newer response is still gated. These retrying UI assertions expose
        // both stale chart-data replacement and stale loading finalization.
        await expect(chart).toHaveAttribute('data-window-days', '365');
        await expect(chart).toHaveAttribute('data-series-state', 'loading');
        await expect(chart.getByTestId('asset-calendar-window-controls')).toBeVisible();
        await expect(chart.getByTestId('asset-calendar-window-1y')).toHaveAttribute('aria-pressed', 'true');
        await expect(chart.getByTestId('asset-calendar-window-3m')).toHaveAttribute('aria-pressed', 'false');
        await expect(pageRoot).toHaveAttribute('data-busy', 'true');
        await expect(loadingNotice).toBeVisible();
        await expect(refreshButton).toBeDisabled();

        const latestPartialResponsePromise = waitForCalendarResponse(365);
        latestPartialGate.release();
        const latestPartialResponse = await latestPartialResponsePromise;
        expect(latestPartialResponse.ok()).toBe(true);
        expect(await latestPartialResponse.finished()).toBeNull();

        const partialProblem = chart.getByTestId('asset-calendar-primary-problem');
        await expect(chart).toHaveAttribute('data-window-days', '365');
        await expect(chart).toHaveAttribute('data-series-state', 'partial');
        await expect(chart).toHaveAttribute('data-calendar-primary-problem-code', 'partial_input_coverage');
        await expect(chart).toHaveAttribute('data-calendar-primary-problem-status', 'partial');
        await expect(chart.getByTestId('asset-calendar-window-1y')).toHaveAttribute('aria-pressed', 'true');
        await expect(partialProblem).toBeVisible();
        await expect(partialProblem).toHaveAttribute('data-problem-code', 'partial_input_coverage');
        await expect(partialProblem).toHaveAttribute('data-problem-status', 'partial');
        await expectAssetDetailChartCanvas(page);
        await expect(page.getByTestId('asset-calendar-return-error')).toBeHidden();
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await expect(loadingNotice).toBeHidden();
        await expect(refreshButton).toBeEnabled();

        const riskTab = controls.getByTestId('asset-detail-tab-risk');
        const overviewTab = controls.getByTestId('asset-detail-tab-overview');
        await expect(riskTab).toBeVisible();
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await riskTab.click();
        await expect(riskTab).toHaveAttribute('aria-selected', 'true');

        await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible();
        const configureSignals = page.getByTestId('asset-risk-configure-signals');
        await expect(configureSignals).toBeVisible();
        await configureSignals.click();

        await expect(overviewTab).toHaveAttribute('aria-selected', 'true');
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(pricePrimary).toHaveAttribute('aria-pressed', 'true');
        const signalsToggle = page.getByTestId('asset-detail-signals-toggle');
        await expect(signalsToggle).toBeVisible();
        await expect(signalsToggle).toHaveAttribute('aria-expanded', 'true');
        await expect(page.getByTestId('asset-detail-signals-panel')).toBeVisible();
        await expect(signalsToggle).toBeInViewport();

        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(pricePrimary).toHaveAttribute('aria-pressed', 'true');
        await expect(calendarPrimary).toHaveAttribute('aria-pressed', 'false');
        await expect(chart).toHaveAttribute('data-view-mode', 'absolute');
        await expect(chart.getByTestId('chart-view-mode-toggle')).toBeVisible();
        await expect(chart.getByTestId('chart-view-absolute')).toHaveAttribute('aria-pressed', 'true');
        await expect(chart.getByTestId('chart-type-line')).toBeVisible();
        await expect(chart.getByTestId('chart-type-candlestick')).toBeVisible();
        await expect(chart.getByTestId('candlestick-chart')).toBeVisible();
        await expect(page.getByTestId('asset-detail-editdata-btn')).toBeVisible();
        await aestheticsToggle.click();
        await expect(aestheticsPanel).toBeVisible();
        await expect(aestheticsPanel.getByTestId('chart-axis-row-primary-absolute')).toBeVisible();
        await expect(aestheticsPanel.getByTestId('chart-axis-row-primary-percentage')).toHaveCount(0);
        await expectAssetDetailChartCanvas(page);

        // MAX begins life as the broad `min` sentinel. Keep that Price request
        // in flight, enter Return with the saved 1Y window (valid against the
        // provisional span), then return to Price before the Calendar request
        // reveals only 45 real days. Resolution must force the concrete Price
        // comparison without rewriting the independently valid 1Y Calendar N.
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                calendarReturnWindow: {
                    kind: 'preset',
                    preset: '1y',
                    customAmount: 3,
                    customUnit: 'years',
                },
            });

        const resolvedMaxSpanDays = 45;
        syntheticMaxResolutionSpanDays = resolvedMaxSpanDays;
        const provisionalMaxPriceGate = deferNextPriceOnlyResponse();
        const provisionalMaxPriceRequestPromise = page.waitForRequest(
            (request) => {
                if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                const queries = parseQueries(request.postDataJSON());
                const mainQuery = queries.find((query) => query.asset_id === assetId);
                return findCalendarSignal(queries) === undefined && mainQuery?.include_price !== false && mainQuery?.date_range?.start === '2000-01-01';
            },
            {timeout: 10_000},
        );
        const maxPreset = dateRangePicker.getByTestId('date-preset-max');
        await expect(maxPreset).toBeVisible();
        await maxPreset.click();
        const provisionalMaxPriceRequest = await provisionalMaxPriceRequestPromise;
        const provisionalMaxMainQuery = parseQueries(provisionalMaxPriceRequest.postDataJSON()).find((query) => query.asset_id === assetId);
        const provisionalMaxEnd = provisionalMaxMainQuery?.date_range?.end;
        expect(provisionalMaxMainQuery?.date_range?.start).toBe('2000-01-01');
        expect(provisionalMaxEnd).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        if (!provisionalMaxEnd) {
            throw new Error('The provisional MAX request did not include a concrete end date');
        }
        const concreteMaxRange: SyntheticRange = {
            start: subtractDays(provisionalMaxEnd, resolvedMaxSpanDays),
            end: provisionalMaxEnd,
            spanDays: resolvedMaxSpanDays,
        };
        const concreteMaxCalendarRefillRange = {
            start: subtractDays(concreteMaxRange.start, 365 + 7),
            end: concreteMaxRange.end,
        } as const;
        await expect(maxPreset).toHaveAttribute('data-active', 'true');
        await expect.poll(async () => Number(await chart.getAttribute('data-calendar-range-days'))).toBeGreaterThan(365);
        await expect(calendarPrimary).toBeEnabled();

        const overlongCalendarGate = deferCalendarResponse(365, 'ready');
        const provisionalMaxCalendarRequestCount = calendarRequestCount;
        const overlongCalendarRequestPromise = waitForCalendarRequest(365);
        const overlongCalendarResponsePromise = waitForCalendarResponse(365);
        await calendarPrimary.click();
        const overlongCalendarRequest = await overlongCalendarRequestPromise;
        assertCalendarRequest(overlongCalendarRequest.postDataJSON(), 365, true);
        assertCalendarBulkRequest(overlongCalendarRequest.postDataJSON(), 365);
        expect(parseQueries(overlongCalendarRequest.postDataJSON()).find((query) => query.asset_id === assetId)?.date_range).toEqual({
            start: '2000-01-01',
            end: provisionalMaxEnd,
        });
        expect(calendarRequestCount).toBe(provisionalMaxCalendarRequestCount + 1);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', '365');
        await expect(chart).toHaveAttribute('data-series-state', 'loading');
        await expect(pageRoot).toHaveAttribute('data-busy', 'true');

        // Returning to Price starts a comparison against the still-provisional
        // MAX range while the Calendar request that will reveal the concrete
        // first date remains gated.
        const provisionalMaxComparisonGate = deferProvisionalMaxPriceComparisonResponse();
        const provisionalMaxComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, {start: '2000-01-01', end: provisionalMaxEnd}, asset.currency);
        await pricePrimary.click();
        const provisionalMaxComparisonRequest = await provisionalMaxComparisonRequestPromise;
        assertPriceComparisonRequest(provisionalMaxComparisonRequest.postDataJSON(), comparisonPeerIds, {start: '2000-01-01', end: provisionalMaxEnd}, asset.currency);
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(chart).toHaveAttribute('data-series-state', 'loading');

        const concreteMaxComparisonRangeKey = `${concreteMaxRange.start}|${concreteMaxRange.end}`;
        const forcedConcreteMaxComparisonRequestCount = priceComparisonRequestCountsByRange.get(concreteMaxComparisonRangeKey) ?? 0;
        const forcedConcreteMaxComparisonGate = deferNextPriceComparisonResponse();
        const forcedConcreteMaxComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, concreteMaxRange, asset.currency);

        // Resolve MAX while Price is active. resolveMaxStartFromChartData()
        // must reject the provisional comparison and force exactly one
        // concrete-range successor.
        overlongCalendarGate.release();
        const overlongCalendarResponse = await overlongCalendarResponsePromise;
        expect(overlongCalendarResponse.ok()).toBe(true);
        expect(await overlongCalendarResponse.finished()).toBeNull();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        const forcedConcreteMaxComparisonRequest = await forcedConcreteMaxComparisonRequestPromise;
        assertPriceComparisonRequest(forcedConcreteMaxComparisonRequest.postDataJSON(), comparisonPeerIds, concreteMaxRange, asset.currency);
        await expect.poll(() => priceComparisonRequestCountsByRange.get(concreteMaxComparisonRangeKey) ?? 0).toBe(forcedConcreteMaxComparisonRequestCount + 1);

        // The original Price request is already superseded by the Calendar
        // request. Let it finish only after the forced successor is in flight,
        // so handleDateRangeChange deterministically joins that successor
        // rather than starting another concrete comparison.
        const provisionalMaxPriceResponsePromise = page.waitForResponse(
            (response) => {
                const request = response.request();
                if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                const queries = parseQueries(request.postDataJSON());
                const mainQuery = queries.find((query) => query.asset_id === assetId);
                return findCalendarSignal(queries) === undefined && mainQuery?.include_price !== false && mainQuery?.date_range?.start === '2000-01-01';
            },
            {timeout: 10_000},
        );
        provisionalMaxPriceGate.release();
        const provisionalMaxPriceResponse = await provisionalMaxPriceResponsePromise;
        expect(provisionalMaxPriceResponse.ok()).toBe(true);
        expect(await provisionalMaxPriceResponse.finished()).toBeNull();

        // Exercise an explicit non-force call with the exact same concrete
        // fingerprint while the forced request is still gated. Returning from
        // Calendar to Price invokes maybeLoadComparison(force=false)
        // synchronously; it must join the in-flight successor and issue no
        // second concrete-range request.
        const maxJoinPriceQueriesBefore = priceQueryRequestCount;
        const maxJoinComparisonRequestsBefore = priceComparisonRequestCount;
        const maxJoinCalendarRequestsBefore = calendarRequestCount;
        const maxJoinCalendarResponsePromise = waitForCalendarResponse(365);
        await calendarPrimary.click();
        const maxJoinCalendarResponse = await maxJoinCalendarResponsePromise;
        expect(maxJoinCalendarResponse.ok()).toBe(true);
        expect(await maxJoinCalendarResponse.finished()).toBeNull();
        assertCalendarRequest(maxJoinCalendarResponse.request().postDataJSON(), 365, false);
        assertCalendarBulkRequest(maxJoinCalendarResponse.request().postDataJSON(), 365);
        assertMainDateRange(maxJoinCalendarResponse.request().postDataJSON(), concreteMaxRange);
        expect(priceQueryRequestCount).toBe(maxJoinPriceQueriesBefore + 1);
        expect(priceComparisonRequestCount).toBe(maxJoinComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(maxJoinCalendarRequestsBefore + 1);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        expect(priceQueryRequestCount).toBe(maxJoinPriceQueriesBefore + 1);
        expect(priceComparisonRequestCount).toBe(maxJoinComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(maxJoinCalendarRequestsBefore + 1);
        expect(priceComparisonRequestCountsByRange.get(concreteMaxComparisonRangeKey) ?? 0).toBe(forcedConcreteMaxComparisonRequestCount + 1);

        // Refreshing Price/MAX re-arms the broad sentinel. Its main response
        // resolves the concrete range and auto-schedules one forced comparison
        // successor. handleRefresh() must join that owned successor rather
        // than issuing a second same-fingerprint request.
        const maxRefreshPriceQueriesBefore = priceQueryRequestCount;
        const maxRefreshMainRequestsBefore = mainPriceRequestCount;
        const maxRefreshComparisonRequestsBefore = priceComparisonRequestCount;
        const maxRefreshRangeRequestsBefore = priceComparisonRequestCountsByRange.get(concreteMaxComparisonRangeKey) ?? 0;
        const maxRefreshCalendarRequestsBefore = calendarRequestCount;
        const maxRefreshMainGate = deferNextMainPriceResponse();
        const maxRefreshMainRequestPromise = page.waitForRequest(
            (request) => {
                if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                const queries = parseQueries(request.postDataJSON());
                const mainQuery = queries.find((query) => query.asset_id === assetId);
                return findCalendarSignal(queries) === undefined && mainQuery?.date_range?.start === '2000-01-01' && mainQuery.date_range.end === concreteMaxRange.end;
            },
            {timeout: 10_000},
        );
        const maxRefreshMainResponsePromise = page.waitForResponse(
            (response) => {
                const request = response.request();
                if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                const queries = parseQueries(request.postDataJSON());
                const mainQuery = queries.find((query) => query.asset_id === assetId);
                return findCalendarSignal(queries) === undefined && mainQuery?.date_range?.start === '2000-01-01' && mainQuery.date_range.end === concreteMaxRange.end;
            },
            {timeout: 10_000},
        );
        const maxRefreshComparisonGate = deferNextPriceComparisonResponse();
        const maxRefreshComparisonRequestPromise = waitForPriceComparisonRequest(comparisonPeerIds, concreteMaxRange, asset.currency);
        await refreshButton.click();
        const maxRefreshMainRequest = await maxRefreshMainRequestPromise;
        expect(parseQueries(maxRefreshMainRequest.postDataJSON()).find((query) => query.asset_id === assetId)?.date_range).toEqual({
            start: '2000-01-01',
            end: concreteMaxRange.end,
        });
        expect(priceQueryRequestCount).toBe(maxRefreshPriceQueriesBefore + 1);
        expect(mainPriceRequestCount).toBe(maxRefreshMainRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(maxRefreshComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(maxRefreshCalendarRequestsBefore);
        await expect(pageRoot).toHaveAttribute('data-busy', 'true');

        maxRefreshMainGate.release();
        const maxRefreshMainResponse = await maxRefreshMainResponsePromise;
        expect(maxRefreshMainResponse.ok()).toBe(true);
        expect(await maxRefreshMainResponse.finished()).toBeNull();
        const maxRefreshComparisonRequest = await maxRefreshComparisonRequestPromise;
        assertPriceComparisonRequest(maxRefreshComparisonRequest.postDataJSON(), comparisonPeerIds, concreteMaxRange, asset.currency);
        await expect.poll(() => priceComparisonRequestCountsByRange.get(concreteMaxComparisonRangeKey) ?? 0).toBe(maxRefreshRangeRequestsBefore + 1);
        expect(priceQueryRequestCount).toBe(maxRefreshPriceQueriesBefore + 2);
        expect(mainPriceRequestCount).toBe(maxRefreshMainRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(maxRefreshComparisonRequestsBefore + 1);
        expect(calendarRequestCount).toBe(maxRefreshCalendarRequestsBefore);

        const maxRefreshComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, concreteMaxRange, asset.currency);
        maxRefreshComparisonGate.release();
        const maxRefreshComparisonResponse = await maxRefreshComparisonResponsePromise;
        expect(maxRefreshComparisonResponse.ok()).toBe(true);
        expect(await maxRefreshComparisonResponse.finished()).toBeNull();
        await expect.poll(readChartComparisonLineLabels).toEqual(expect.arrayContaining(comparisonPeers.map((peer) => peer.display_name)));
        expect(priceQueryRequestCount).toBe(maxRefreshPriceQueriesBefore + 2);
        expect(mainPriceRequestCount).toBe(maxRefreshMainRequestsBefore + 1);
        expect(priceComparisonRequestCount).toBe(maxRefreshComparisonRequestsBefore + 1);
        expect(priceComparisonRequestCountsByRange.get(concreteMaxComparisonRangeKey) ?? 0).toBe(maxRefreshRangeRequestsBefore + 1);
        expect(calendarRequestCount).toBe(maxRefreshCalendarRequestsBefore);

        const forcedConcreteMaxComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, concreteMaxRange, asset.currency);
        forcedConcreteMaxComparisonGate.release();
        const forcedConcreteMaxComparisonResponse = await forcedConcreteMaxComparisonResponsePromise;
        expect(forcedConcreteMaxComparisonResponse.ok()).toBe(true);
        expect(await forcedConcreteMaxComparisonResponse.finished()).toBeNull();
        await expect.poll(() => priceComparisonRequestCountsByRange.get(concreteMaxComparisonRangeKey) ?? 0).toBe(forcedConcreteMaxComparisonRequestCount + 2);
        await expect(dateRangeStartInput).toHaveValue(concreteMaxRange.start);
        await expect(dateRangeEndInput).toHaveValue(concreteMaxRange.end);
        await expect(chart).toHaveAttribute('data-calendar-range-days', String(concreteMaxRange.spanDays));
        await expect.poll(readChartComparisonLineLabels).toEqual(expect.arrayContaining(comparisonPeers.map((peer) => peer.display_name)));

        const provisionalMaxComparisonResponsePromise = waitForPriceComparisonResponse(comparisonPeerIds, {start: '2000-01-01', end: provisionalMaxEnd}, asset.currency);
        provisionalMaxComparisonGate.release();
        const provisionalMaxComparisonResponse = await provisionalMaxComparisonResponsePromise;
        expect(provisionalMaxComparisonResponse.status()).toBe(503);
        expect(provisionalMaxComparisonResponse.ok()).toBe(false);
        expect(await provisionalMaxComparisonResponse.finished()).toBeNull();
        expect(await provisionalMaxComparisonResponse.json()).toEqual({
            detail: 'synthetic-provisional-max-comparison-rejection',
        });
        await pricePrimary.focus();
        await expect(pricePrimary).toBeFocused();
        await expect.poll(() => priceComparisonRequestCountsByRange.get(concreteMaxComparisonRangeKey) ?? 0).toBe(forcedConcreteMaxComparisonRequestCount + 2);
        await expect.poll(readChartComparisonLineLabels).toEqual(expect.arrayContaining(comparisonPeers.map((peer) => peer.display_name)));

        const concreteMaxCalendarGate = deferCalendarResponse(365, 'ready');
        const concreteMaxCalendarRequestPromise = waitForCalendarRequest(365);
        const concreteMaxCalendarResponsePromise = waitForCalendarResponse(365);
        const successorCalendarRequestCount = calendarRequestCount;
        await calendarPrimary.click();
        const concreteMaxCalendarRequest = await concreteMaxCalendarRequestPromise;
        assertCalendarRequest(concreteMaxCalendarRequest.postDataJSON(), 365, false);
        assertCalendarBulkRequest(concreteMaxCalendarRequest.postDataJSON(), 365);
        assertMainDateRange(concreteMaxCalendarRequest.postDataJSON(), concreteMaxRange);
        await expect.poll(() => calendarRequestCount).toBe(successorCalendarRequestCount + 1);

        await expect(maxPreset).toHaveAttribute('data-active', 'true');
        await expect(dateRangeStartInput).toHaveValue(concreteMaxRange.start);
        await expect(dateRangeEndInput).toHaveValue(concreteMaxRange.end);
        await expect(chart).toHaveAttribute('data-calendar-range-days', String(concreteMaxRange.spanDays));
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-kind', 'preset');
        await expect(chart).toHaveAttribute('data-window-days', '365');
        await expect(chart).toHaveAttribute('data-series-state', 'loading');
        await expect(pageRoot).toHaveAttribute('data-busy', 'true');
        await expect(loadingNotice).toBeVisible();
        await expect(partialProblem).toBeHidden();
        for (const preset of calendarPresets) {
            await expect(chart.getByTestId(`asset-calendar-window-${preset.key}`)).toBeVisible();
        }
        await expect(chart.getByTestId('asset-calendar-window-1y')).toHaveAttribute('aria-pressed', 'true');
        await expect
            .poll(async () => await readPersistedPairSettings(chartSettingsStorageKey))
            .toMatchObject({
                calendarReturnWindow: {
                    kind: 'preset',
                    preset: '1y',
                    customAmount: 3,
                    customUnit: 'years',
                },
            });

        concreteMaxCalendarGate.release();
        const concreteMaxCalendarResponse = await concreteMaxCalendarResponsePromise;
        expect(concreteMaxCalendarResponse.ok()).toBe(true);
        expect(await concreteMaxCalendarResponse.finished()).toBeNull();
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(loadingNotice).toBeHidden();
        await expectAssetDetailChartCanvas(page);
        expect(priceComparisonRequestCountsByRange.get(concreteMaxComparisonRangeKey) ?? 0).toBe(forcedConcreteMaxComparisonRequestCount + 2);
        expect(calendarRequestCount).toBe(successorCalendarRequestCount + 1);

        // The Price/MAX auto-successor has now applied and its remembered
        // promise has cleared. Returning to Price is a later non-force owner
        // of that exact concrete fingerprint, so it must reuse the applied
        // result. The forced MAX refresh above remains the sole +1 refresh
        // request; this round trip adds only its Calendar query.
        const appliedMaxPriceQueriesBefore = priceQueryRequestCount;
        const appliedMaxComparisonRequestsBefore = priceComparisonRequestCount;
        const appliedMaxCalendarRequestsBefore = calendarRequestCount;
        await pricePrimary.click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await pricePrimary.focus();
        await expect(pricePrimary).toBeFocused();
        expect(priceQueryRequestCount).toBe(appliedMaxPriceQueriesBefore);
        expect(priceComparisonRequestCount).toBe(appliedMaxComparisonRequestsBefore);
        expect(priceComparisonRequestCountsByRange.get(concreteMaxComparisonRangeKey) ?? 0).toBe(forcedConcreteMaxComparisonRequestCount + 2);

        const restoreAppliedMaxCalendarResponsePromise = waitForCalendarResponse(365);
        await calendarPrimary.click();
        const restoreAppliedMaxCalendarResponse = await restoreAppliedMaxCalendarResponsePromise;
        expect(restoreAppliedMaxCalendarResponse.ok()).toBe(true);
        expect(await restoreAppliedMaxCalendarResponse.finished()).toBeNull();
        assertCalendarBulkRequest(restoreAppliedMaxCalendarResponse.request().postDataJSON(), 365);
        assertMainDateRange(restoreAppliedMaxCalendarResponse.request().postDataJSON(), concreteMaxRange);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        expect(priceQueryRequestCount).toBe(appliedMaxPriceQueriesBefore + 1);
        expect(priceComparisonRequestCount).toBe(appliedMaxComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(appliedMaxCalendarRequestsBefore + 1);

        // MAX keeps the public sync contract sentinel-based, while the
        // invalidated client-side FX stores must be refilled over the concrete
        // range resolved from chart data. Capture all three request surfaces:
        // Asset sync, bulk FX sync, and each post-sync FX conversion refill.
        nextAssetSyncStatus = 'failed';
        nextFxSyncStatus = 'partial';
        const maxAssetSyncRequestsBefore = assetSyncRequestCount;
        const maxFxSyncRequestsBefore = fxSyncRequestCount;
        const maxFxConvertRequestsBefore = fxConvertRequests.length;
        const maxCalendarRequestsBeforeSync = calendarRequestCount;
        const maxAssetSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const maxAssetSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/assets/prices/sync', {timeout: 10_000});
        const maxFxSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const maxFxSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const maxCalendarReloadResponsePromise = waitForCalendarResponse(365);
        await activateComparisonAssetSync(readySignalId);

        const maxAssetSyncRequest = await maxAssetSyncRequestPromise;
        expect(maxAssetSyncRequest.postDataJSON()).toEqual([
            {
                asset_id: readyPeer.id,
                date_range: {
                    start: 'min',
                    end: concreteMaxRange.end,
                },
            },
        ]);
        const maxFxSyncRequest = await maxFxSyncRequestPromise;
        expect(maxFxSyncRequest.postDataJSON()).toEqual({
            pairs: ['EUR-GBP', 'EUR-USD'],
            start: 'min',
            end: concreteMaxRange.end,
        });

        const maxAssetSyncResponse = await maxAssetSyncResponsePromise;
        expect(maxAssetSyncResponse.ok()).toBe(true);
        expect(await maxAssetSyncResponse.finished()).toBeNull();
        expect(await maxAssetSyncResponse.json()).toMatchObject({
            success_count: 0,
            results: [{asset_id: readyPeer.id, status: 'failed'}],
        });
        const maxFxSyncResponse = await maxFxSyncResponsePromise;
        expect(maxFxSyncResponse.ok()).toBe(true);
        expect(await maxFxSyncResponse.finished()).toBeNull();
        expect(await maxFxSyncResponse.json()).toMatchObject({
            success_count: readyPeerRequiredFxSlugs.length,
            results: expectedFxSyncResults(readyPeerRequiredFxSlugs, 'partial'),
        });

        const maxCalendarReloadResponse = await maxCalendarReloadResponsePromise;
        expect(maxCalendarReloadResponse.ok()).toBe(true);
        expect(await maxCalendarReloadResponse.finished()).toBeNull();
        assertCalendarBulkRequest(maxCalendarReloadResponse.request().postDataJSON(), 365);
        assertMainDateRange(maxCalendarReloadResponse.request().postDataJSON(), concreteMaxRange);
        await expectFocusedAssetSyncIdle(readySignalId);

        const maxFxRefillRequests = fxConvertRequests.slice(maxFxConvertRequestsBefore);
        expect(maxFxRefillRequests).toEqual([
            [
                {
                    from_amount: {code: 'EUR', amount: '1'},
                    to: 'GBP',
                    date_range: concreteMaxCalendarRefillRange,
                },
            ],
            [
                {
                    from_amount: {code: 'EUR', amount: '1'},
                    to: 'USD',
                    date_range: concreteMaxCalendarRefillRange,
                },
            ],
        ]);
        expect(maxFxRefillRequests.flatMap((requests) => requests.map((request) => request.date_range.start))).not.toContain('min');
        expect(assetSyncRequestCount).toBe(maxAssetSyncRequestsBefore + 1);
        expect(fxSyncRequestCount).toBe(maxFxSyncRequestsBefore + 1);
        expect(fxConvertRequestCount).toBe(maxFxConvertRequestsBefore + readyPeerRequiredFxSlugs.length);
        expect(calendarRequestCount).toBe(maxCalendarRequestsBeforeSync + 1);
        expect(fxRouteMutationRequestCount).toBe(0);
        await expect(maxPreset).toHaveAttribute('data-active', 'true');
        await expect(dateRangeStartInput).toHaveValue(concreteMaxRange.start);
        await expect(dateRangeEndInput).toHaveValue(concreteMaxRange.end);

        // Exercise the standalone handleSyncPair path under MAX as well. Its
        // backend contract keeps the public `min` sentinel, while the
        // invalidated FX store and both chart reloads must use the concrete
        // ISO range already resolved from the MAX price snapshot.
        priceComparisonSyncSucceeded = false;
        forceReadyPeerConversionFailure = true;
        const maxStandaloneInitialComparisonPromise = waitForPriceComparisonResponse(comparisonPeerIds, concreteMaxRange, asset.currency);
        await pricePrimary.click();
        const maxStandaloneInitialComparison = await maxStandaloneInitialComparisonPromise;
        expect(maxStandaloneInitialComparison.ok()).toBe(true);
        expect(await maxStandaloneInitialComparison.finished()).toBeNull();
        assertPriceComparisonRequest(maxStandaloneInitialComparison.request().postDataJSON(), comparisonPeerIds, concreteMaxRange, asset.currency);
        await expect(lineChartButton).toBeVisible();
        await lineChartButton.click();
        await expect(chart.getByTestId('candlestick-chart')).toBeHidden();
        forceReadyPeerConversionFailure = false;
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(readyFxSyncAction).toBeVisible();
        await expect(readyFxSyncAction).toBeEnabled();

        nextFxSyncStatus = 'partial';
        const maxStandaloneAssetSyncRequestsBefore = assetSyncRequestCount;
        const maxStandaloneFxSyncRequestsBefore = fxSyncRequestCount;
        const maxStandaloneFxConversionsBefore = fxConvertRequests.length;
        const maxStandaloneCalendarRequestsBefore = calendarRequestCount;
        const maxStandaloneFxSyncRequestPromise = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const maxStandaloneFxSyncResponsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/fx/currencies/sync', {timeout: 10_000});
        const maxStandaloneMainReloadPromise = waitForMainRangeResponse(concreteMaxRange);
        const maxStandaloneComparisonReloadPromise = waitForPriceComparisonResponse(comparisonPeerIds, concreteMaxRange, asset.currency);
        await readyFxSyncAction.focus();
        await expect(readyFxSyncAction).toBeFocused();
        await expect(readyFxSyncAction).toBeEnabled();
        await readyFxSyncAction.press('Enter');

        const maxStandaloneFxSyncRequest = await maxStandaloneFxSyncRequestPromise;
        expect(maxStandaloneFxSyncRequest.postDataJSON()).toEqual({
            pairs: [readyPeerFxSlug],
            start: 'min',
            end: concreteMaxRange.end,
        });
        const maxStandaloneFxSyncResponse = await maxStandaloneFxSyncResponsePromise;
        expect(maxStandaloneFxSyncResponse.ok()).toBe(true);
        expect(await maxStandaloneFxSyncResponse.finished()).toBeNull();
        expect(await maxStandaloneFxSyncResponse.json()).toMatchObject({
            success_count: 1,
            results: [{pair: readyPeerFxSlug, status: 'partial'}],
        });

        const maxStandaloneMainReload = await maxStandaloneMainReloadPromise;
        expect(maxStandaloneMainReload.ok()).toBe(true);
        expect(await maxStandaloneMainReload.finished()).toBeNull();
        assertMainDateRange(maxStandaloneMainReload.request().postDataJSON(), concreteMaxRange);
        const maxStandaloneComparisonReload = await maxStandaloneComparisonReloadPromise;
        expect(maxStandaloneComparisonReload.ok()).toBe(true);
        expect(await maxStandaloneComparisonReload.finished()).toBeNull();
        assertPriceComparisonRequest(maxStandaloneComparisonReload.request().postDataJSON(), comparisonPeerIds, concreteMaxRange, asset.currency);

        expect(fxConvertRequests.slice(maxStandaloneFxConversionsBefore)).toEqual([
            [
                {
                    from_amount: {code: 'EUR', amount: '1'},
                    to: 'GBP',
                    date_range: {start: concreteMaxRange.start, end: concreteMaxRange.end},
                },
            ],
        ]);
        expect(assetSyncRequestCount).toBe(maxStandaloneAssetSyncRequestsBefore);
        expect(fxSyncRequestCount).toBe(maxStandaloneFxSyncRequestsBefore + 1);
        expect(fxConvertRequestCount).toBe(maxStandaloneFxConversionsBefore + 1);
        expect(calendarRequestCount).toBe(maxStandaloneCalendarRequestsBefore);
        await expect(maxPreset).toHaveAttribute('data-active', 'true');
        await expect(dateRangeStartInput).toHaveValue(concreteMaxRange.start);
        await expect(dateRangeEndInput).toHaveValue(concreteMaxRange.end);
        await expect(readySignalCard.getByRole('button', {name: '📈3', exact: true})).toBeVisible();
        await expect(readySignalCard.getByRole('button', {name: '💰2', exact: true})).toBeVisible();
        await expect(readySignalCard.getByTestId('signal-issue')).toHaveCount(0);
        await expect(readyFxSyncAction).toHaveCount(0);
        await expect(readySignalCard.getByTestId(`signal-fx-detail-${readySignalId}`)).toBeVisible();
        await expect.poll(readChartEventMarkerAssetLabels).toContain(readyPeer.display_name);

        // Add one real backend-computed signal through the existing settings
        // controls. The next Calendar/MAX resolution uses this card to prove
        // that the forced Price successor restores both the overlay result and
        // its diagnostics rather than refreshing comparisons alone.
        const finalToastDismissButtons = page.getByTestId('toast-dismiss');
        while (true) {
            const countBeforeDismiss = await finalToastDismissButtons.count();
            if (countBeforeDismiss === 0) break;
            await finalToastDismissButtons.first().click();
            await expect.poll(() => finalToastDismissButtons.count()).toBeLessThan(countBeforeDismiss);
        }
        await expect(page.getByTestId(/^toast-(?:error|info|success|warning)$/)).toHaveCount(0);

        const signalCardsBeforeBackendAdd = await readSignalCardTestIds(signalsPanel);
        const backendAddRequestPromise = waitForBackendSignalRequest(concreteMaxRange);
        const backendAddResponsePromise = waitForBackendSignalResponse(concreteMaxRange);
        await signalsPanel.getByTestId('signals-indicator-select-button').click();
        await signalsPanel.getByTestId('signal-tree-group-risk').click();
        await expect(signalsPanel.getByTestId('signal-tree-option-risk-rolling-volatility')).toBeVisible();
        await signalsPanel.getByTestId('signal-tree-option-risk-rolling-volatility').click();
        const backendAddRequest = await backendAddRequestPromise;
        await expect
            .poll(async () => {
                const currentCards = await readSignalCardTestIds(signalsPanel);
                return currentCards.filter((testId) => !signalCardsBeforeBackendAdd.includes(testId));
            })
            .toHaveLength(1);
        const backendSignalCards = (await readSignalCardTestIds(signalsPanel)).filter((testId) => !signalCardsBeforeBackendAdd.includes(testId));
        const backendSignalCardTestId = backendSignalCards[0];
        if (!backendSignalCardTestId) {
            throw new Error('Adding rolling volatility did not create one identifiable signal card');
        }
        const backendSignalId = backendSignalCardTestId.slice('signal-card-'.length);
        assertBackendSignalRequest(backendAddRequest.postDataJSON(), backendSignalId, concreteMaxRange);
        const backendAddResponse = await backendAddResponsePromise;
        expect(backendAddResponse.ok()).toBe(true);
        expect(await backendAddResponse.finished()).toBeNull();
        const backendSignalCard = signalsPanel.getByTestId(backendSignalCardTestId);
        await expect(backendSignalCard).toHaveAttribute('data-signal-type', 'risk-rolling-volatility');
        await expect(backendSignalCard.getByTestId('signal-loading')).toHaveCount(0);
        const backendSignalIssue = backendSignalCard.getByTestId('signal-issue');
        await expect(backendSignalIssue).toBeVisible();
        await expect(backendSignalIssue).toHaveAttribute('data-severity', 'warning');
        await expect(backendSignalIssue).not.toHaveAttribute('data-problem-code', /.+/);
        await expect(backendSignalCard.getByRole('button', {name: '📈2', exact: true})).toBeVisible();

        const enterShortMaxCalendarResponsePromise = waitForCalendarResponse(365);
        await calendarPrimary.click();
        const enterShortMaxCalendarResponse = await enterShortMaxCalendarResponsePromise;
        expect(enterShortMaxCalendarResponse.ok()).toBe(true);
        expect(await enterShortMaxCalendarResponse.finished()).toBeNull();
        assertCalendarBulkRequest(enterShortMaxCalendarResponse.request().postDataJSON(), 365);
        assertMainDateRange(enterShortMaxCalendarResponse.request().postDataJSON(), concreteMaxRange);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', '365');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        const shortMaxRange: SyntheticRange = {
            start: subtractDays(concreteMaxRange.end, 6),
            end: concreteMaxRange.end,
            spanDays: 6,
        };
        syntheticMaxResolutionSpanDays = shortMaxRange.spanDays;
        const shortMaxCalendarGate = deferCalendarResponse(365, 'ready');
        const shortMaxPriceQueriesBefore = priceQueryRequestCount;
        const shortMaxMainRequestsBefore = mainPriceRequestCount;
        const shortMaxComparisonRequestsBefore = priceComparisonRequestCount;
        const shortMaxCalendarRequestsBefore = calendarRequestCount;
        const shortMaxBackendRequestsBefore = backendSignalRequestCount;
        const shortMaxCalendarRequestPromise = waitForCalendarRequest(365);
        const shortMaxCalendarResponsePromise = waitForCalendarResponse(365);

        await refreshButton.click();
        const shortMaxCalendarRequest = await shortMaxCalendarRequestPromise;
        assertCalendarRequest(shortMaxCalendarRequest.postDataJSON(), 365, true);
        expect(parseQueries(shortMaxCalendarRequest.postDataJSON()).find((query) => query.asset_id === assetId)?.date_range).toEqual({
            start: '2000-01-01',
            end: shortMaxRange.end,
        });
        expect(priceQueryRequestCount).toBe(shortMaxPriceQueriesBefore + 1);
        expect(mainPriceRequestCount).toBe(shortMaxMainRequestsBefore);
        expect(priceComparisonRequestCount).toBe(shortMaxComparisonRequestsBefore);
        expect(calendarRequestCount).toBe(shortMaxCalendarRequestsBefore + 1);
        expect(backendSignalRequestCount).toBe(shortMaxBackendRequestsBefore);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-series-state', 'loading');
        await expect(pageRoot).toHaveAttribute('data-busy', 'true');

        shortMaxCalendarGate.release();
        const shortMaxCalendarResponse = await shortMaxCalendarResponsePromise;
        expect(shortMaxCalendarResponse.ok()).toBe(true);
        expect(await shortMaxCalendarResponse.finished()).toBeNull();
        const shortMaxPayload = (await shortMaxCalendarResponse.json()) as {items?: I60GResponseItem[]};
        const shortMaxPrimaryPoints =
            shortMaxPayload.items
                ?.find((item) => item.asset_id === assetId)
                ?.signals?.find((signal) => signal.instance_id === calendarInstanceId && signal.signal_code === calendarSignalCode)
                ?.series?.find((series) => series.key === 'calendar_return')?.points ?? [];
        expect(shortMaxPrimaryPoints.map((point) => point.date)).toEqual([subtractDays(shortMaxRange.end, 1), shortMaxRange.end]);
        expect(shortMaxPrimaryPoints.map((point) => point.value)).toEqual([36.5, -18.25]);
        expect(shortMaxPrimaryPoints.every((point) => point.date >= shortMaxRange.start && point.date <= shortMaxRange.end)).toBe(true);
        expect(shortMaxPrimaryPoints.every((point) => point.provenance.reference_target_date < shortMaxRange.start)).toBe(true);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(pricePrimary).toHaveAttribute('aria-pressed', 'false');
        await expect(calendarPrimary).toHaveAttribute('aria-pressed', 'true');
        await expect(calendarPrimary).toBeEnabled();
        await expect(dateRangeStartInput).toHaveValue(shortMaxRange.start);
        await expect(dateRangeEndInput).toHaveValue(shortMaxRange.end);
        await expect(chart).toHaveAttribute('data-calendar-range-days', String(shortMaxRange.spanDays));
        await expect(chart).toHaveAttribute('data-window-days', '365');
        await expect(chart.getByTestId('asset-calendar-window-controls')).toBeVisible();
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect.poll(readI60GCalendarChart).toEqual({
            dates: [addDays('2000-01-01', 365), '2026-08-01', '2026-08-02', subtractDays(shortMaxRange.end, 1), shortMaxRange.end],
            main: [null, null, null, 36.5, -18.25],
            peers: {
                [readyPeer.display_name]: [13, 13, 13, null, 16],
                [partialPeer.display_name]: [null, null, null, 23, 22],
                [unavailablePeer.display_name]: [null, null, null, null, null],
                [errorPeer.display_name]: [null, null, null, null, null],
                [invalidCalendarPeer.display_name]: [null, null, null, null, null],
            },
            presentPeerLabels: [readyPeer.display_name, partialPeer.display_name].sort(),
        });
        expect(priceQueryRequestCount).toBeGreaterThanOrEqual(shortMaxPriceQueriesBefore + 1);
        expect(mainPriceRequestCount).toBe(shortMaxMainRequestsBefore);
        expect(priceComparisonRequestCount).toBe(shortMaxComparisonRequestsBefore);
        expect(calendarRequestCount).toBeGreaterThanOrEqual(shortMaxCalendarRequestsBefore + 1);
        expect(backendSignalRequestCount).toBe(shortMaxBackendRequestsBefore);
        syntheticMaxResolutionSpanDays = null;
    });

    // ========================================================================
    // Test 18: Chart type toggle — Line → Candlestick → Line
    // ========================================================================
    test('chart type toggle switches between line and candlestick', async ({page}) => {
        await goToSeededAssetDetail(page);

        // Wait for chart data to load (button only renders when data is available)
        const candleBtn = page.getByTestId('chart-type-candlestick');
        const lineBtn = page.getByTestId('chart-type-line');
        await expect(candleBtn).toBeVisible({timeout: 10_000});
        await expect(candleBtn).not.toBeDisabled();

        // Switch to candlestick
        await candleBtn.click();

        // Candlestick chart container must appear inside asset-detail-chart
        const chartWrapper = page.getByTestId('asset-detail-chart');
        await expect(chartWrapper.getByTestId('candlestick-chart')).toBeVisible({timeout: 5000});

        // Switch back to line — candlestick div disappears
        await lineBtn.click();
        await expect(chartWrapper.getByTestId('candlestick-chart')).not.toBeVisible();
    });

    // ========================================================================
    // Test 19: Candlestick renders without JS error
    // ========================================================================
    test('candlestick chart renders without console errors', async ({page}) => {
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));

        await goToSeededAssetDetail(page);
        await page.getByTestId('chart-type-candlestick').click();

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
        await goToSeededAssetDetail(page);

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
        await goToSeededAssetDetail(page);

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
        await goToSeededAssetDetail(page);

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
        await goToSeededAssetDetail(page);

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
