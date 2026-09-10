/**
 * FX Add Pair Modal — E2E Tests
 *
 * Tests for FX pair creation modal: currency selection, route discovery, save.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxPage, openAddPairModal, selectCurrency} from './fx-helpers';

test.describe('FX Add Pair Modal', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test.describe('Creation feedback', () => {
        // The entire FX configuration/rate surface below is browser-context local.
        // No POST reaches the shared database, and no real provider is contacted.
        const slug = 'EUR-GBP';
        const range = {start: '2024-03-01', end: '2024-03-31'};

        for (const {mode, leaveBeforeSync, detailRace} of [
            {mode: 'provider', leaveBeforeSync: false, detailRace: 'none'},
            {mode: 'manual', leaveBeforeSync: false, detailRace: 'none'},
            {mode: 'provider', leaveBeforeSync: true, detailRace: 'none'},
            {mode: 'provider', leaveBeforeSync: false, detailRace: 'stale-data'},
            {mode: 'provider', leaveBeforeSync: false, detailRace: 'stale-error'},
            {mode: 'provider', leaveBeforeSync: false, detailRace: 'refresh-error'},
        ] as const) {
            test(`${mode} creation closes promptly and links to its owned pair${leaveBeforeSync ? ' after leaving FX' : ''}${detailRace !== 'none' ? ` with early detail ${detailRace}` : ''}`, async ({page}) => {
                const {eventSeq, waitForEvent} = await import('../fixtures/app-events');
                const routeItem = {
                    base: 'EUR',
                    quote: 'GBP',
                    priority: mode === 'provider' ? 1 : 999,
                    chain_steps: [{from: 'EUR', to: 'GBP', provider: mode === 'provider' ? 'MOCKFX' : 'MANUAL'}],
                };
                const readItem = {...routeItem, is_chain: false, providers_used: [routeItem.chain_steps[0].provider]};
                let configured = false;
                let syncReleased = false;
                const createdBodies: unknown[] = [];
                const syncBodies: unknown[] = [];
                const rateReads: Array<{afterSync: boolean; body: unknown}> = [];
                const initialListReads: unknown[] = [];
                const initialDetailReads: unknown[] = [];
                let enteringDetail = false;
                let releaseSync!: () => void;
                const syncGate = new Promise<void>((resolve) => {
                    releaseSync = resolve;
                });
                let releaseInitialList!: () => void;
                const initialListGate = new Promise<void>((resolve) => {
                    releaseInitialList = resolve;
                });
                let releaseOldDetail!: () => void;
                const oldDetailGate = new Promise<void>((resolve) => {
                    releaseOldDetail = resolve;
                });

                await page.route('**/api/v1/fx/providers', async (route) => {
                    await route.fulfill({
                        json: [
                            {
                                code: 'MOCKFX',
                                name: 'Owned creation provider',
                                base_currency: 'EUR',
                                base_currencies: ['EUR'],
                                target_currencies: ['GBP'],
                                description: 'Browser-local deterministic fixture',
                            },
                        ],
                    });
                });
                await page.route('**/api/v1/fx/providers/routes', async (route) => {
                    if (route.request().method() === 'GET') {
                        await route.fulfill({json: {items: configured ? [readItem] : []}});
                        return;
                    }
                    expect(route.request().method()).toBe('POST');
                    const body = route.request().postDataJSON();
                    createdBodies.push(body);
                    expect(body).toEqual([routeItem]);
                    configured = true;
                    await route.fulfill({json: {results: [{...readItem, success: true, action: 'created'}], success_count: 1, error_count: 0}});
                });
                await page.route('**/api/v1/fx/currencies/sync', async (route) => {
                    const body = route.request().postDataJSON();
                    syncBodies.push(body);
                    expect(body).toEqual({pairs: [slug], ...range});
                    await syncGate;
                    syncReleased = true;
                    await route.fulfill({
                        json: {
                            results: [{pair: slug, status: 'ok', points_fetched: 1, points_changed: 1, provider_used: 'MOCKFX'}],
                            success_count: 1,
                            date_range: range,
                            total_points_changed: 1,
                        },
                    });
                });
                await page.route('**/api/v1/fx/currencies/convert', async (route) => {
                    const body = route.request().postDataJSON();
                    rateReads.push({afterSync: syncReleased, body});
                    // This fixture owns the complete FX route list, so every
                    // conversion must address that pair, never an unrelated row.
                    for (const request of body) {
                        expect([request.from_amount.code, request.to].sort()).toEqual(['EUR', 'GBP']);
                        expect(request.date_range).toEqual(range);
                    }
                    if (detailRace !== 'none' && !syncReleased) {
                        if (!enteringDetail) {
                            initialListReads.push(body);
                            // Keep the initial cache range unpopulated until the
                            // detail page really starts its own initial read.
                            await initialListGate;
                            await route.fulfill({json: {results: [], success_count: 0, signal_results: []}});
                        } else {
                            initialDetailReads.push(body);
                            // This is specifically the no-signal gap path which
                            // used to merge through ensureFxRangeLoaded before
                            // the detail component could reject an old response.
                            expect(body).toEqual([{from_amount: {code: 'EUR', amount: '1'}, to: 'GBP', date_range: range}]);
                            await oldDetailGate;
                            if (detailRace === 'stale-error') {
                                await route.fulfill({status: 404, json: {detail: 'owned-pre-sync-no-rates'}});
                            } else {
                                await route.fulfill({
                                    json: {
                                        results: [{from_amount: {code: 'EUR', amount: '1'}, to_amount: {code: 'GBP', amount: '0.12'}, conversion_date: range.end, rate: '0.12'}],
                                        success_count: 1,
                                        signal_results: [],
                                    },
                                });
                            }
                        }
                        return;
                    }
                    if (detailRace === 'refresh-error' && syncReleased) {
                        await route.fulfill({status: 503, json: {detail: 'owned-post-sync-refresh-unavailable'}});
                        return;
                    }
                    await route.fulfill({
                        json: {
                            results: syncReleased ? [{from_amount: {code: 'EUR', amount: '1'}, to_amount: {code: 'GBP', amount: '0.85'}, conversion_date: range.end, rate: '0.85'}] : [],
                            success_count: syncReleased ? 1 : 0,
                            signal_results: [],
                        },
                    });
                });

                try {
                    // Authentication is provided by the enclosing beforeEach.
                    await page.goto(`/fx?start=${range.start}&end=${range.end}`);
                    const fxPage = page.getByTestId('fx-page');
                    await expect(fxPage).toBeVisible();
                    await expect(fxPage).toHaveAttribute('data-busy', 'false');
                    await page.getByTestId('view-mode-grid').click();
                    await openAddPairModal(page);
                    const modal = page.getByTestId('fx-add-pair-modal');

                    // Address each instance, and close its options before opening
                    // the next: SearchSelect option IDs are shared by kind.
                    // Quote first avoids the base selector's automatic "open the
                    // empty quote" focus shortcut overlapping two dropdowns.
                    const quote = modal.getByTestId('fx-add-pair-quote');
                    await quote.getByRole('combobox').click();
                    await quote.locator('input[type="text"]').fill('GBP');
                    await page.getByTestId('search-select-option-GBP').click();
                    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0);
                    const base = modal.getByTestId('fx-add-pair-base');
                    await base.getByRole('combobox').click();
                    await base.locator('input[type="text"]').fill('EUR');
                    await page.getByTestId('search-select-option-EUR').click();
                    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0);

                    await expect(modal.getByTestId('fx-route-picker-toggle')).toBeVisible();
                    if (mode === 'provider') {
                        await modal.getByTestId('fx-route-picker-toggle').click();
                        await modal.getByTestId('fx-route-direct-MOCKFX').click();
                        await expect(modal.getByTestId('fx-route-selected')).toHaveAttribute('data-route-key', 'EUR-GBP:MOCKFX');
                    }
                    const since = await eventSeq(page);
                    const creationRequest = page.waitForRequest((request) => request.url().endsWith('/api/v1/fx/providers/routes') && request.method() === 'POST');
                    await modal.getByTestId('fx-add-pair-save').click();
                    expect((await creationRequest).postDataJSON()).toEqual([routeItem]);
                    await expect(modal).toBeHidden();
                    const created = await waitForEvent(page, 'fx.pair.created', {since});
                    expect(created.detail).toMatchObject({slug, pairs: [slug], hasRealProvider: mode === 'provider', autoSyncStarted: mode === 'provider'});
                    if (detailRace === 'none') await expect(fxPage).toHaveAttribute('data-busy', 'false');

                    const success = page.getByTestId('toast-success').filter({has: page.getByTestId('toast-fx-link').filter({hasText: 'EUR / GBP'})});
                    const completionToast = detailRace === 'refresh-error' ? page.getByTestId('toast-warning').filter({has: page.getByTestId('toast-fx-link').filter({hasText: 'EUR / GBP'})}) : success;
                    if (mode === 'provider') {
                        await expect.poll(() => syncBodies.length).toBe(1);
                        // The request is blocked by this test, not merely slow.
                        // Creation is already visible while no synced toast exists.
                        await expect(page.getByTestId(`fx-card-${slug}`)).toBeVisible();
                        await expect(success).toHaveCount(0);
                        const detail = page.getByTestId('fx-detail-page');
                        let discardedBefore = 0;
                        if (detailRace !== 'none') {
                            await expect.poll(() => initialListReads.length).toBe(1);
                            enteringDetail = true;
                            await page.getByTestId(`fx-card-${slug}`).click();
                            await expect(detail).toBeVisible();
                            await expect(detail).toHaveAttribute('data-chart-pair', slug);
                            await expect.poll(() => initialDetailReads.length).toBe(1);
                            await expect(detail).toHaveAttribute('data-busy', 'true');
                            await expect(detail).toHaveAttribute('data-chart-last-rate', '');
                            await expect(detail).toHaveAttribute('data-discarded-chart-loads', /^\d+$/);
                            discardedBefore = Number(await detail.getAttribute('data-discarded-chart-loads'));
                            // Let creation's old list refresh finish. The detail
                            // response remains held through the entire sync.
                            releaseInitialList();
                        }
                        if (leaveBeforeSync) {
                            const {openMobileMenu} = await import('../fixtures/auth-helpers');
                            await openMobileMenu(page);
                            // A native SPA navigation unmounts the host, not the
                            // browser runtime holding the detached sync request.
                            await page.getByTestId('sidebar-user-avatar').click();
                            await expect(page.getByTestId('settings-page')).toBeVisible();
                            await expect(fxPage).toBeHidden();
                        }
                        const readsBefore = rateReads.length;
                        releaseSync();
                        await expect(completionToast).toBeVisible();
                        const synced = await waitForEvent(page, 'fx.pair.creation-sync-completed', {since});
                        expect(synced.detail).toMatchObject({slug, pairs: [slug], ...range, outcome: 'ok', configurationSaved: true});
                        if (detailRace === 'refresh-error') {
                            expect(synced.detail).toMatchObject({
                                callbackErrors: expect.arrayContaining([expect.objectContaining({phase: 'completion', message: expect.any(String)})]),
                            });
                            await expect(completionToast).toHaveCount(1);
                            await expect(success).toHaveCount(0);
                        }
                        if (leaveBeforeSync) {
                            // The completion event is emitted after the captured
                            // callback settles: no clock-based absence assertion.
                            expect(rateReads).toHaveLength(readsBefore);
                            await expect(page.getByTestId('settings-page')).toBeVisible();
                        } else if (detailRace === 'none') {
                            // Refresh is the subject: a pre-sync creation refresh
                            // cannot satisfy this post-sync request barrier.
                            await expect.poll(() => rateReads.slice(readsBefore).filter((read) => read.afterSync).length).toBeGreaterThan(0);
                            await expect(fxPage).toHaveAttribute('data-busy', 'false');
                        } else {
                            const freshRate = detailRace === 'refresh-error' ? '' : '0.85';
                            await expect(detail).toHaveAttribute('data-chart-last-rate', freshRate);
                            await expect(detail).toHaveAttribute('data-busy', 'false');
                            await expect(completionToast).toHaveCount(1);
                            await expect(completionToast.getByTestId('toast-fx-link')).toHaveAttribute('href', `/fx/${slug}`);
                            expect(syncBodies).toEqual([{pairs: [slug], ...range}]);
                            expect(rateReads.filter((read) => read.afterSync)).toHaveLength(1);
                            releaseOldDetail();
                            // Response-finished alone is not an application
                            // barrier. This counter moves only after the stale
                            // HTTP success/catch handler actually rejects it.
                            await expect.poll(async () => Number(await detail.getAttribute('data-discarded-chart-loads'))).toBeGreaterThan(discardedBefore);
                            await expect(detail).toHaveAttribute('data-chart-pair', slug);
                            await expect(detail).toHaveAttribute('data-chart-last-rate', freshRate);
                            await expect(detail).toHaveAttribute('data-busy', 'false');

                            if (detailRace !== 'refresh-error') {
                                // A freshly mounted detail reads the shared store,
                                // not the previous component's chartData. No new
                                // conversion may repair an overwritten cached value.
                                const readsBeforeReentry = rateReads.length;
                                await detail.getByTestId('fx-detail-back-btn').click();
                                await expect(fxPage).toBeVisible();
                                await expect(fxPage).toHaveAttribute('data-busy', 'false');
                                await page.getByTestId(`fx-card-${slug}`).click();
                                await expect(detail).toBeVisible();
                                await expect(detail).toHaveAttribute('data-chart-pair', slug);
                                await expect(detail).toHaveAttribute('data-chart-last-rate', '0.85');
                                await expect(detail).toHaveAttribute('data-busy', 'false');
                                expect(rateReads).toHaveLength(readsBeforeReentry);
                            }
                        }
                    } else {
                        await expect(success).toBeVisible();
                        const completed = await waitForEvent(page, 'fx.pair.creation-completed', {since});
                        expect(completed.detail).toMatchObject({slug, autoSyncStarted: false});
                        expect(syncBodies).toEqual([]);
                    }
                    const ownedCreationEvents = await page.evaluate(
                        ({since, slug}) => {
                            const events = (window as unknown as {__lf?: {events?: Array<{seq: number; name: string; detail?: {slug?: string}}>}}).__lf?.events ?? [];
                            return events.filter((event) => event.seq > since && event.name === 'fx.pair.created' && event.detail?.slug === slug).length;
                        },
                        {since, slug},
                    );
                    expect(ownedCreationEvents).toBe(1);
                    expect(createdBodies).toEqual([[routeItem]]);
                    expect(syncBodies).toEqual(mode === 'provider' ? [{pairs: [slug], ...range}] : []);
                    if (detailRace === 'none') {
                        await expect(success).toHaveCount(1);
                        const link = success.getByTestId('toast-fx-link');
                        await expect(link).toHaveAttribute('href', `/fx/${slug}`);
                        // Late-entry cases own pointer navigation; the early
                        // race proves refresh without relying on another click.
                        // Do not make cache re-entry race a toast expiry timer.
                        await link.click();
                        await expect(page).toHaveURL(new RegExp(`/fx/${slug}(?:\\?|$)`));
                        await expect(page.getByTestId('fx-detail-page')).toBeVisible();
                    }
                } finally {
                    releaseSync();
                    releaseInitialList();
                    releaseOldDetail();
                    await page.unrouteAll({behavior: 'wait'});
                }
            });
        }
    });

    // ========================================================================
    // Test 1: Open modal
    // ========================================================================
    test('can open add pair modal', async ({page}) => {
        await goToFxPage(page);
        await openAddPairModal(page);
        await expect(page.getByTestId('fx-add-pair-modal')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Two currency selects visible
    // ========================================================================
    test('modal has two currency selects', async ({page}) => {
        await goToFxPage(page);
        await openAddPairModal(page);
        const modal = page.getByTestId('fx-add-pair-modal');
        const comboboxes = modal.locator('[role="combobox"]');
        const count = await comboboxes.count();
        expect(count).toBeGreaterThanOrEqual(2);
    });

    // ========================================================================
    // Test 3: Save disabled without currencies
    // ========================================================================
    test('save button is disabled without currencies selected', async ({page}) => {
        await goToFxPage(page);
        await openAddPairModal(page);
        const saveBtn = page.getByTestId('fx-add-pair-save');
        await expect(saveBtn).toBeDisabled();
    });

    // ========================================================================
    // Test 4: Close via Escape (no dirty state)
    // ========================================================================
    test('escape closes modal when not dirty', async ({page}) => {
        await goToFxPage(page);
        await openAddPairModal(page);
        await page.keyboard.press('Escape');
        await expect(page.getByTestId('fx-add-pair-modal')).not.toBeVisible();
    });

    // ========================================================================
    // Test 5: Selecting currencies shows route section
    // ========================================================================
    test('selecting currencies shows route section', async ({page}) => {
        await page.route('**/api/v1/fx/providers', async (route) => {
            expect(route.request().method()).toBe('GET');
            await route.fulfill({
                json: [
                    {
                        code: 'MOCKFX',
                        name: 'Owned route provider',
                        base_currency: 'EUR',
                        base_currencies: ['EUR'],
                        target_currencies: ['CAD'],
                        description: 'Browser-local deterministic fixture',
                    },
                ],
            });
        });
        await page.route('**/api/v1/fx/providers/routes', async (route) => {
            expect(route.request().method()).toBe('GET');
            await route.fulfill({json: {items: []}});
        });
        try {
            await goToFxPage(page);
            await openAddPairModal(page);
            const modal = page.getByTestId('fx-add-pair-modal');

            // Quote first avoids the base selector's automatic "open the empty
            // quote" focus shortcut overlapping two dropdown interactions.
            const quoteContainer = modal.getByTestId('fx-add-pair-quote');
            await expect(quoteContainer).toBeVisible();
            await selectCurrency(page, quoteContainer, 'CAD');

            const baseContainer = modal.getByTestId('fx-add-pair-base');
            await expect(baseContainer).toBeVisible();
            await selectCurrency(page, baseContainer, 'EUR');

            // Route section should appear
            await expect(modal.getByTestId('fx-route-select')).toBeVisible({timeout: 5000});
        } finally {
            await page.unrouteAll({behavior: 'wait'});
        }
    });
});
