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
import type {Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {goToAssetDetailPage, goToAssetsPage} from './assets-helpers';
import {t} from '../fixtures/i18n-data';

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
        const assetId = 920_060;
        const calendarInstanceId = 'asset-calendar-return';
        const calendarSignalCode = 'ASSET_CALENDAR_ROLLING_RETURN';
        const calendarWindows = [7, 30, 90, 365] as const;
        type CalendarWindow = (typeof calendarWindows)[number];
        type CalendarSignalRequest = {
            instance_id?: string;
            signal_code?: string;
            params?: {window_days?: unknown};
        };
        type PriceQueryRequest = {
            asset_id?: number;
            include_price?: boolean;
            signals?: CalendarSignalRequest[];
        };
        type CalendarPointFixture = {
            date: string;
            value: number;
            provenance: {
                status: 'available';
                reference_target_date: string;
                current_price_date: string;
                current_price_days_back: number;
                reference_price_date: string;
                reference_price_days_back: number;
                current_fx_date: null;
                current_fx_days_back: null;
                reference_fx_date: null;
                reference_fx_days_back: null;
            };
        };
        type CalendarSignalResultFixture = {
            instance_id: string;
            signal_code: string;
            normalized_params: {window_days: CalendarWindow};
            status: 'ok' | 'partial';
            series: Array<{
                key: 'calendar_return';
                points: CalendarPointFixture[];
                [key: string]: unknown;
            }>;
            [key: string]: unknown;
        };
        type DeferredCalendarOutcome = 'ready' | 'partial';
        type DeferredCalendarResponse = {
            outcome: DeferredCalendarOutcome;
            wait: Promise<void>;
            release: () => void;
        };

        const asset = {
            id: assetId,
            display_name: `Synthetic calendar-return asset ${assetId}`,
            currency: 'EUR',
            asset_type: 'STOCK',
            active: true,
            has_metadata: false,
            provider_code: null,
            tx_count: 0,
            tx_count_own: 0,
        };
        const pricePoints = [
            {date: '2026-08-01', open: '100.00', high: '103.00', low: '99.00', close: '102.00', volume: '1000', currency: 'EUR'},
            {date: '2026-08-02', open: '102.00', high: '105.00', low: '101.00', close: '104.00', volume: '1100', currency: 'EUR'},
            {date: '2026-08-03', open: '104.00', high: '106.00', low: '102.00', close: '103.00', volume: '900', currency: 'EUR'},
        ];
        const deferredCalendarResponses = new Map<CalendarWindow, DeferredCalendarResponse>();

        const parseQueries = (raw: unknown): PriceQueryRequest[] => (Array.isArray(raw) ? (raw as PriceQueryRequest[]) : []);
        const findCalendarSignal = (raw: unknown): CalendarSignalRequest | undefined =>
            parseQueries(raw)
                .flatMap((query) => query.signals ?? [])
                .find((signal) => signal.instance_id === calendarInstanceId && signal.signal_code === calendarSignalCode);
        const isCalendarWindow = (value: unknown): value is CalendarWindow => calendarWindows.some((windowDays) => windowDays === value);
        const deferCalendarResponse = (windowDays: CalendarWindow, outcome: DeferredCalendarOutcome): DeferredCalendarResponse => {
            let release!: () => void;
            const wait = new Promise<void>((resolve) => {
                release = () => resolve();
            });
            const deferred = {outcome, wait, release};
            deferredCalendarResponses.set(windowDays, deferred);
            return deferred;
        };
        const subtractDays = (date: string, days: number): string => {
            const value = new Date(`${date}T00:00:00Z`);
            value.setUTCDate(value.getUTCDate() - days);
            return value.toISOString().slice(0, 10);
        };
        const buildCalendarResult = (windowDays: CalendarWindow, status: CalendarSignalResultFixture['status'] = 'ok'): CalendarSignalResultFixture => {
            const points: CalendarPointFixture[] = [
                {date: '2026-08-01', value: windowDays / 10},
                {date: '2026-08-02', value: -windowDays / 20},
            ].map(({date, value}) => {
                const referenceDate = subtractDays(date, windowDays);
                return {
                    date,
                    value,
                    provenance: {
                        status: 'available',
                        reference_target_date: referenceDate,
                        current_price_date: date,
                        current_price_days_back: 0,
                        reference_price_date: referenceDate,
                        reference_price_days_back: 0,
                        current_fx_date: null,
                        current_fx_days_back: null,
                        reference_fx_date: null,
                        reference_fx_days_back: null,
                    },
                };
            });

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
                        requested_points: points.length,
                        available_points: points.length,
                        contiguous_points: points.length,
                        observed_points: points.length,
                        backfilled_points: 0,
                        missing_points: 0,
                        max_consecutive_missing_points: 0,
                        internal_gap_count: 0,
                        coverage_ratio: 1,
                        field_coverage: {close: 1},
                        event_type_counts: {},
                        first_available_date: '2026-08-01',
                        last_available_date: '2026-08-02',
                    },
                    required_points: 2,
                    warmup_complete: true,
                    partial_coverage_used: status === 'partial',
                    reason_code: null,
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
                warnings: [],
                error: null,
                risk_metadata: null,
                data_quality: null,
            };
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
        const waitForCalendarRequest = (windowDays: CalendarWindow) =>
            page.waitForRequest(
                (request) => {
                    if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return false;
                    return findCalendarSignal(request.postDataJSON())?.params?.window_days === windowDays;
                },
                {timeout: 10_000},
            );
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

        await page.route('**/api/v1/assets/query*', async (route) => {
            await route.fulfill({json: [asset]});
        });
        await page.route('**/api/v1/assets/prices/query', async (route) => {
            const requests = parseQueries(route.request().postDataJSON());
            const requestedDeferredWindow = findCalendarSignal(requests)?.params?.window_days;
            const deferredWindow = isCalendarWindow(requestedDeferredWindow) && deferredCalendarResponses.has(requestedDeferredWindow) ? requestedDeferredWindow : undefined;
            const deferred = deferredWindow === undefined ? undefined : deferredCalendarResponses.get(deferredWindow);
            if (deferred && deferredWindow !== undefined) {
                deferredCalendarResponses.delete(deferredWindow);
                await deferred.wait;
            }
            const items = requests.map((request) => {
                const calendarSignal = request.signals?.find((signal) => signal.instance_id === calendarInstanceId && signal.signal_code === calendarSignalCode);
                const requestedWindow = calendarSignal?.params?.window_days;
                if (calendarSignal && !isCalendarWindow(requestedWindow)) {
                    throw new Error(`Unexpected calendar window: ${String(requestedWindow)}`);
                }
                const isStaleForcedRefresh = deferredWindow === 90 && requestedWindow === 90;
                return {
                    asset_id: request.asset_id ?? assetId,
                    // The stale forced refresh deliberately carries no prices:
                    // old code applied this payload and unmounted the active chart
                    // while the newer 365-day request was still pending.
                    prices: request.include_price === false || isStaleForcedRefresh ? [] : pricePoints,
                    events: [],
                    errors: [],
                    signals: calendarSignal && isCalendarWindow(requestedWindow) ? [buildCalendarResult(requestedWindow, requestedWindow === deferredWindow && deferred?.outcome === 'partial' ? 'partial' : 'ok')] : [],
                };
            });
            await route.fulfill({json: {items}});
        });
        await page.route('**/api/v1/assets/prices/current', async (route) => {
            await route.fulfill({json: {results: [], success_count: 0, errors: []}});
        });

        await goToAssetDetailPage(page, String(assetId));
        const pageRoot = page.getByTestId('asset-detail-page');
        const controls = page.getByTestId('asset-detail-controls');
        const chart = page.getByTestId('asset-detail-chart');
        const pricePrimary = chart.getByTestId('asset-chart-primary-price');
        const calendarPrimary = chart.getByTestId('asset-chart-primary-calendar-return');
        const editorButton = page.getByTestId('asset-detail-editdata-btn');
        const editorPanel = page.getByTestId('asset-detail-editor-panel');
        const editorSaveButton = page.getByTestId('asset-editor-save-btn');
        const measuresSection = page.getByTestId('asset-detail-measures-section');
        const measuresToggle = page.getByTestId('asset-detail-measures-toggle');
        const measuresPanel = page.getByTestId('asset-detail-measures-panel');

        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(pricePrimary).toHaveAttribute('aria-pressed', 'true');
        await expect(calendarPrimary).toHaveAttribute('aria-pressed', 'false');
        await expectAssetDetailChartCanvas(page);

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
        await expect(measuresSection).toHaveAttribute('aria-hidden', 'true');
        await expect(measuresSection).toHaveAttribute('inert', '');
        await expect(measuresSection).toBeHidden();
        await expect(measuresPanel).toHaveAttribute('data-testid', 'asset-detail-measures-panel');
        await expect(measuresPanel).toBeHidden();

        await pricePrimary.click();
        await expect(measuresSection).toBeVisible();
        await expect(measuresPanel).toBeVisible();

        await chart.getByTestId('chart-view-absolute').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'absolute');
        await chart.getByTestId('chart-type-candlestick').click();
        await expect(chart.getByTestId('candlestick-chart')).toBeVisible();

        const defaultResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const defaultRequest = (await defaultResponsePromise).request();
        assertCalendarRequest(defaultRequest.postDataJSON(), 30);

        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', '30');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(calendarPrimary).toHaveAttribute('aria-pressed', 'true');
        await expect(pricePrimary).toHaveAttribute('aria-pressed', 'false');
        await expectAssetDetailChartCanvas(page);

        await expect(chart.getByTestId(/^asset-calendar-window-/)).toHaveCount(calendarWindows.length);
        for (const windowDays of calendarWindows) {
            const button = chart.getByTestId(`asset-calendar-window-${windowDays}`);
            await expect(button).toBeVisible();
            await expect(button).toHaveAttribute('aria-pressed', windowDays === 30 ? 'true' : 'false');
        }
        await expect(chart.getByTestId('chart-view-mode-toggle')).toBeHidden();
        await expect(chart.getByTestId('chart-type-line')).toBeHidden();
        await expect(chart.getByTestId('chart-type-candlestick')).toBeHidden();
        await expect(chart.getByTestId('candlestick-chart')).toBeHidden();
        await expect(page.getByTestId('asset-detail-editdata-btn')).toBeHidden();

        const refreshButton = page.getByTestId('asset-detail-refresh-btn');
        const loadingNotice = page.getByTestId('asset-calendar-return-loading');

        // Switching presentation modes must not invalidate the shared price/events
        // request when no successor request exists. This deferred 30-day response
        // is distinct from the empty-price stale 90-day response exercised below.
        const modeSwitchRefreshGate = deferCalendarResponse(30, 'ready');
        const modeSwitchRefreshRequestPromise = waitForCalendarRequest(30);
        await refreshButton.click();
        const modeSwitchRefreshRequest = await modeSwitchRefreshRequestPromise;
        assertCalendarRequest(modeSwitchRefreshRequest.postDataJSON(), 30, true);

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

        const restoredCalendarResponsePromise = waitForCalendarResponse(30);
        await calendarPrimary.click();
        const restoredCalendarRequest = (await restoredCalendarResponsePromise).request();
        assertCalendarRequest(restoredCalendarRequest.postDataJSON(), 30);
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', '30');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');

        const ninetyDayResponsePromise = waitForCalendarResponse(90);
        await chart.getByTestId('asset-calendar-window-90').click();
        const ninetyDayRequest = (await ninetyDayResponsePromise).request();
        assertCalendarRequest(ninetyDayRequest.postDataJSON(), 90);
        await expect(chart).toHaveAttribute('data-window-days', '90');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(chart.getByTestId('asset-calendar-window-90')).toHaveAttribute('aria-pressed', 'true');
        await expect(chart.getByTestId('asset-calendar-window-30')).toHaveAttribute('aria-pressed', 'false');

        const staleRefreshGate = deferCalendarResponse(90, 'ready');
        const staleRefreshRequestPromise = waitForCalendarRequest(90);
        await refreshButton.click();
        const staleRefreshRequest = await staleRefreshRequestPromise;
        assertCalendarRequest(staleRefreshRequest.postDataJSON(), 90, true);
        await expect(chart).toHaveAttribute('data-window-days', '90');
        await expect(chart).toHaveAttribute('data-series-state', 'loading');
        await expect(pageRoot).toHaveAttribute('data-busy', 'true');
        await expect(loadingNotice).toBeVisible();
        await expect(refreshButton).toBeDisabled();

        const latestPartialGate = deferCalendarResponse(365, 'partial');
        const latestPartialRequestPromise = waitForCalendarRequest(365);
        await chart.getByTestId('asset-calendar-window-365').click();
        const latestPartialRequest = await latestPartialRequestPromise;
        assertCalendarRequest(latestPartialRequest.postDataJSON(), 365, true);
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
        await expect(chart.getByTestId('asset-calendar-window-365')).toHaveAttribute('aria-pressed', 'true');
        await expect(chart.getByTestId('asset-calendar-window-90')).toHaveAttribute('aria-pressed', 'false');
        await expect(pageRoot).toHaveAttribute('data-busy', 'true');
        await expect(loadingNotice).toBeVisible();
        await expect(refreshButton).toBeDisabled();

        const latestPartialResponsePromise = waitForCalendarResponse(365);
        latestPartialGate.release();
        const latestPartialResponse = await latestPartialResponsePromise;
        expect(latestPartialResponse.ok()).toBe(true);
        expect(await latestPartialResponse.finished()).toBeNull();

        const partialNotice = page.getByTestId('asset-calendar-return-partial');
        await expect(chart).toHaveAttribute('data-window-days', '365');
        await expect(chart).toHaveAttribute('data-series-state', 'partial');
        await expect(chart.getByTestId('asset-calendar-window-365')).toHaveAttribute('aria-pressed', 'true');
        await expect(partialNotice).toBeVisible();
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
        await expectAssetDetailChartCanvas(page);
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
