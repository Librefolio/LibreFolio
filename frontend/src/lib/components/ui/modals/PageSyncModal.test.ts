// @vitest-environment jsdom
/**
 * PageSyncModal — component test (Vitest + jsdom).
 *
 * The asset-detail page syncs two unrelated things at once: the prices of the
 * assets on screen and the FX pairs their currencies need. PageSyncModal is the
 * only place in the app that builds *two* SyncSections, so it is the only place
 * where "run them in parallel and keep the answers apart" is actually exercised —
 * one endpoint per section, one row snippet per section, and a section that has to
 * disappear entirely when its list is empty (a same-currency page has no pairs; a
 * page whose assets have no provider has nothing to price).
 *
 * Both endpoints are mocked at `$lib/api`, for the same reason as the other two
 * wrappers: the subject is the translation between the wire shape and
 * `SyncResult[]`, and the failure modes that matter — one endpoint down while the
 * other answers, a response missing its optional counters — cannot be produced from
 * a browser on demand.
 *
 * Asserted on `data-testid`/`data-*` and on values injected here. The section
 * headings are translated and are never read; sections are addressed by
 * `data-section-id`.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

vi.mock('$lib/api', () => ({
    zodiosApi: {
        sync_prices_bulk_api_v1_assets_prices_sync_post: vi.fn(),
        sync_rates_api_v1_fx_currencies_sync_post: vi.fn(),
        // Exactly one asset provider carries an icon, so both halves of the badge
        // — image and code text — are reachable from this file.
        list_providers_api_v1_assets_provider_get: vi.fn().mockResolvedValue([{code: 'stooq', name: 'Stooq', icon_url: '/icons/providers/stooq.png'}]),
    },
}));
// The open-effect warms the FX provider cache; not the subject of this file, but
// the cache backs the FX badge, so one provider is given an icon there too.
vi.mock('$lib/stores/currencyGraphStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/currencyGraphStore')>()),
    getCurrencyGraph: vi.fn().mockResolvedValue(undefined),
    getCachedFxProviders: vi.fn(() => [{code: 'ecb', name: 'ECB', icon_url: '/icons/fx/ecb.png'}]),
}));

import PageSyncModal from './PageSyncModal.svelte';
import {zodiosApi} from '$lib/api';

const syncPrices = vi.mocked(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post);
const syncRates = vi.mocked(zodiosApi.sync_rates_api_v1_fx_currencies_sync_post);

type WireResult = Record<string, unknown>;

function assetsRespond(...results: WireResult[]) {
    syncPrices.mockResolvedValue({results} as never);
}

function fxResponds(...results: WireResult[]) {
    syncRates.mockResolvedValue({results} as never);
}

function asset(id: number, over: Record<string, unknown> = {}) {
    return {id, display_name: `Asset ${id}`, provider_code: 'yfinance', ...over};
}

function mount(props: Record<string, unknown> = {}) {
    const onsynced = vi.fn();
    const onclose = vi.fn();
    return {onsynced, onclose, ...render(PageSyncModal, {open: true, dateStart: '2024-03-01', dateEnd: '2024-03-31', assets: [asset(1)], fxPairs: ['EUR-USD'], onsynced, onclose, ...props})};
}

function sectionOf(id: string): HTMLElement {
    const el = document.querySelector<HTMLElement>(`[data-testid="sync-section"][data-section-id="${id}"]`);
    if (!el) throw new Error(`no rendered section ${id}`);
    return el;
}

function rowOf(id: string): HTMLElement {
    const el = document.querySelector<HTMLElement>(`[data-testid="sync-result-row"][data-row-id="${id}"]`);
    if (!el) throw new Error(`no result row for ${id}; present: ${rowIds().join(', ') || '(none)'}`);
    return el;
}

function rowIds(scope: ParentNode = document): string[] {
    return [...scope.querySelectorAll<HTMLElement>('[data-testid="sync-result-row"]')].map((r) => r.getAttribute('data-row-id') ?? '');
}

function num(el: Element | null, attr: string): number {
    return Number(el?.getAttribute(attr));
}

function summary() {
    const el = screen.getByTestId('sync-modal-results');
    return {success: num(el, 'data-success'), total: num(el, 'data-total'), failed: num(el, 'data-failed'), fetched: num(el, 'data-fetched'), changed: num(el, 'data-changed')};
}

function errorBanner(): HTMLElement | null {
    return [...document.querySelectorAll<HTMLElement>('[data-testid="info-banner-error"]')].find((el) => !el.closest('[data-testid="sync-modal-results"]')) ?? null;
}

async function startSync() {
    await fireEvent.click(screen.getByTestId('sync-modal-start'));
}

async function settled() {
    await waitFor(() => expect(screen.getByTestId('sync-modal-body')).toHaveAttribute('data-busy', 'false'));
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    syncPrices.mockReset();
    syncRates.mockReset();
});

// =========================================================================
// How many sections there are
// =========================================================================

describe('PageSyncModal — the two sections', () => {
    it('builds both sections and aggregates their counts', async () => {
        assetsRespond();
        fxResponds();
        mount({assets: [asset(1), asset(2)], fxPairs: ['EUR-USD', 'EUR-GBP', 'USD-CHF']});

        expect(screen.getByTestId('page-sync-modal')).toBeInTheDocument();
        expect(num(screen.getByTestId('sync-modal-count'), 'data-section-count')).toBe(2);
        expect(num(screen.getByTestId('sync-modal-count'), 'data-item-count')).toBe(5);
    });

    it('drops the FX section when the page needs no conversion', async () => {
        assetsRespond({asset_id: 1, status: 'ok', points_fetched: 3, points_changed: 3});
        mount({assets: [asset(1)], fxPairs: []});

        expect(num(screen.getByTestId('sync-modal-count'), 'data-section-count')).toBe(1);

        await startSync();
        await settled();

        // The empty section is never called and never rendered.
        expect(syncRates).not.toHaveBeenCalled();
        expect(sectionOf('assets')).toBeInTheDocument();
        expect(document.querySelector('[data-testid="sync-section"][data-section-id="fx"]')).toBeNull();
    });

    it('drops the assets section when nothing on the page has a provider', async () => {
        fxResponds({pair: 'EUR-USD', status: 'ok', points_fetched: 2, points_changed: 2});
        mount({assets: [asset(1, {provider_code: null})], fxPairs: ['EUR-USD']});

        expect(num(screen.getByTestId('sync-modal-count'), 'data-item-count')).toBe(1);

        await startSync();
        await settled();

        expect(syncPrices).not.toHaveBeenCalled();
        expect(sectionOf('fx')).toBeInTheDocument();
        expect(document.querySelector('[data-testid="sync-section"][data-section-id="assets"]')).toBeNull();
    });

    it('has nothing to start when both lists are empty', async () => {
        mount({assets: [], fxPairs: []});

        expect(num(screen.getByTestId('sync-modal-count'), 'data-item-count')).toBe(0);
        expect(num(screen.getByTestId('sync-modal-count'), 'data-section-count')).toBe(0);
        expect(screen.getByTestId('sync-modal-start')).toBeDisabled();
    });
});

// =========================================================================
// Running both at once
// =========================================================================

describe('PageSyncModal — running both sections', () => {
    it('calls each endpoint with its own payload and files the answers separately', async () => {
        assetsRespond({asset_id: 1, status: 'ok', points_fetched: 10, points_changed: 4}, {asset_id: 2, status: 'ok', points_fetched: 6, points_changed: 0});
        fxResponds({pair: 'EUR-USD', status: 'ok', points_fetched: 20, points_changed: 3});
        const {onsynced} = mount({assets: [asset(1), asset(2), asset(3, {provider_code: null})], fxPairs: ['EUR-USD'], dateStart: '2021-01-01', dateEnd: '2021-03-31'});

        await startSync();
        await settled();

        expect(syncPrices).toHaveBeenCalledWith(
            [
                {asset_id: 1, date_range: {start: '2021-01-01', end: '2021-03-31'}},
                {asset_id: 2, date_range: {start: '2021-01-01', end: '2021-03-31'}},
            ],
            {timeout: 120_000},
        );
        expect(syncRates).toHaveBeenCalledWith({pairs: ['EUR-USD'], start: '2021-01-01', end: '2021-03-31'}, {timeout: 120_000});

        // Asset rows in the asset section, pair rows in the FX section, no crossover.
        expect(rowIds(sectionOf('assets')).sort()).toEqual(['1', '2']);
        expect(rowIds(sectionOf('fx'))).toEqual(['EUR-USD']);
        expect(summary()).toMatchObject({success: 3, total: 3, fetched: 36, changed: 7});
        expect(onsynced).toHaveBeenCalledTimes(1);
    });

    it('keeps the successful section when the other one is down', async () => {
        assetsRespond({asset_id: 1, status: 'ok', points_fetched: 10, points_changed: 4});
        syncRates.mockRejectedValue({response: {data: {detail: 'fx provider unreachable'}}});
        mount({assets: [asset(1)], fxPairs: ['EUR-USD', 'EUR-GBP']});

        await startSync();
        await settled();

        // The asset half survives; the FX half becomes one failed row per pair.
        expect(rowOf('1')).toHaveAttribute('data-status', 'ok');
        expect(rowIds(sectionOf('fx')).sort()).toEqual(['EUR-GBP', 'EUR-USD']);
        expect(rowOf('EUR-USD')).toHaveAttribute('data-status', 'failed');
        expect(errorBanner()).toHaveTextContent('fx provider unreachable');
        expect(summary()).toMatchObject({success: 1, total: 3, failed: 2});
    });

    it('retries a failed pair through the FX endpoint alone', async () => {
        assetsRespond({asset_id: 1, status: 'ok', points_fetched: 10, points_changed: 4});
        syncRates.mockResolvedValueOnce({results: [{pair: 'EUR-USD', status: 'failed', errors: ['no data for range']}]} as never);
        syncRates.mockResolvedValueOnce({results: [{pair: 'EUR-USD', status: 'ok', points_fetched: 7, points_changed: 7}]} as never);
        mount({assets: [asset(1)], fxPairs: ['EUR-USD']});

        await startSync();
        await settled();
        expect(rowOf('EUR-USD')).toHaveAttribute('data-status', 'failed');
        expect(rowOf('EUR-USD')).toHaveTextContent('no data for range');

        await fireEvent.click(within(rowOf('EUR-USD')).getByTestId('sync-retry-row'));
        await waitFor(() => expect(rowOf('EUR-USD')).toHaveAttribute('data-status', 'ok'));

        // The asset endpoint is untouched: a retry stays inside its own section.
        expect(syncPrices).toHaveBeenCalledTimes(1);
        expect(syncRates).toHaveBeenNthCalledWith(2, {pairs: ['EUR-USD'], start: '2024-03-01', end: '2024-03-31'}, {timeout: 120_000});
    });

    it('retries the failures of both sections in one press, each to its own endpoint', async () => {
        syncPrices.mockResolvedValueOnce({results: [{asset_id: 1, status: 'failed', errors: ['symbol delisted']}]} as never);
        syncPrices.mockResolvedValueOnce({results: [{asset_id: 1, status: 'ok', points_fetched: 9, points_changed: 9}]} as never);
        syncRates.mockResolvedValueOnce({results: [{pair: 'EUR-USD', status: 'partial', points_fetched: 1, points_changed: 1}]} as never);
        syncRates.mockResolvedValueOnce({results: [{pair: 'EUR-USD', status: 'ok', points_fetched: 20, points_changed: 20}]} as never);
        mount({assets: [asset(1)], fxPairs: ['EUR-USD']});

        await startSync();
        await settled();
        expect(summary().failed).toBe(2);

        await fireEvent.click(screen.getByTestId('sync-modal-retry-failed'));
        await waitFor(() => expect(summary().failed).toBe(0));

        expect(syncPrices).toHaveBeenNthCalledWith(2, [{asset_id: 1, date_range: {start: '2024-03-01', end: '2024-03-31'}}], {timeout: 120_000});
        expect(syncRates).toHaveBeenNthCalledWith(2, {pairs: ['EUR-USD'], start: '2024-03-01', end: '2024-03-31'}, {timeout: 120_000});
        expect(summary()).toMatchObject({success: 2, total: 2});
    });
});

// =========================================================================
// The two row shapes
// =========================================================================

describe('PageSyncModal — asset rows', () => {
    it('shows prices, corporate events and the provider badge', async () => {
        assetsRespond({asset_id: 1, status: 'ok', points_fetched: 12, points_changed: 3, events_fetched: 2, events_changed: 1, provider_used: 'justetf', elapsed_ms: 450});
        mount({assets: [asset(1)], fxPairs: []});

        await startSync();
        await settled();

        const row = rowOf('1');
        expect(row).toHaveTextContent('Asset 1');
        expect(row).toHaveTextContent('12↓ 3Δ');
        expect(row).toHaveTextContent('2↓ 1Δ');
        expect(within(row).getByTitle('justetf')).toHaveTextContent('justetf');
    });

    it('falls back to the asset-type icon when the asset has none of its own', async () => {
        assetsRespond({asset_id: 1, status: 'ok', points_fetched: 1, points_changed: 1}, {asset_id: 2, status: 'ok', points_fetched: 1, points_changed: 1});
        mount({assets: [asset(1, {icon_url: '/icons/acme.png'}), asset(2, {asset_type: 'ETF'})], fxPairs: []});

        await startSync();
        await settled();

        expect(rowOf('1').querySelector('img')).toHaveAttribute('src', '/icons/acme.png');
        // Type icons are a fixed path map, not a translation.
        expect(rowOf('2').querySelector('img')).toHaveAttribute('src', '/icons/asset-types/etf.png');
    });

    it('shows the message of a skipped asset and the first error of a failed one', async () => {
        assetsRespond({asset_id: 1, status: 'skipped', message: 'no trading days in range'}, {asset_id: 2, status: 'failed', errors: ['upstream 502', 'and the retry also failed']});
        mount({assets: [asset(1), asset(2)], fxPairs: []});

        await startSync();
        await settled();

        expect(rowOf('1')).toHaveTextContent('no trading days in range');
        expect(rowOf('2')).toHaveTextContent('upstream 502');
        expect(summary()).toMatchObject({success: 0, total: 2, failed: 1});
    });

    it('names a row it has no asset for by its id', async () => {
        assetsRespond({asset_id: 404, status: 'ok', points_fetched: 1, points_changed: 1});
        mount({assets: [asset(1)], fxPairs: []});

        await startSync();
        await settled();

        expect(rowOf('404')).toHaveTextContent('Asset #404');
    });
});

describe('PageSyncModal — FX rows', () => {
    it('shows the counters and one badge per chain leg', async () => {
        fxResponds({pair: 'RON-JPY', status: 'ok', points_fetched: 15, points_changed: 15, provider_used: 'CHAIN:ecb+frankfurter', elapsed_ms: 2500});
        mount({assets: [], fxPairs: ['RON-JPY']});

        await startSync();
        await settled();

        const row = rowOf('RON-JPY');
        expect(row).toHaveTextContent('15↓ 15Δ');
        expect(within(row).getByTitle('ecb')).toBeInTheDocument();
        expect(within(row).getByTitle('frankfurter')).toBeInTheDocument();
    });

    it('draws a badge as its icon when the cache knows the provider, and as its code when it does not', async () => {
        assetsRespond({asset_id: 1, status: 'ok', points_fetched: 1, points_changed: 1, provider_used: 'stooq'});
        fxResponds({pair: 'RON-JPY', status: 'ok', points_fetched: 1, points_changed: 1, provider_used: 'CHAIN:ecb+frankfurter'});
        mount({assets: [asset(1)], fxPairs: ['RON-JPY']});

        await startSync();
        await settled();

        // Each section reads its own cache: assets from the provider catalogue,
        // FX from the currency graph. Both fall back to the bare code.
        expect(within(rowOf('1')).getByTitle('stooq').querySelector('img')).toHaveAttribute('src', '/icons/providers/stooq.png');
        expect(within(rowOf('RON-JPY')).getByTitle('ecb').querySelector('img')).toHaveAttribute('src', '/icons/fx/ecb.png');
        expect(within(rowOf('RON-JPY')).getByTitle('frankfurter').querySelector('img')).toBeNull();
        expect(within(rowOf('RON-JPY')).getByTitle('frankfurter')).toHaveTextContent('frankfurter');
    });

    it('shows a skipped message and a failed error, and offers a retry only on the failure', async () => {
        fxResponds({pair: 'EUR-USD', status: 'skipped', message: 'rates already complete'}, {pair: 'EUR-GBP', status: 'failed', message: 'provider returned nothing'});
        mount({assets: [], fxPairs: ['EUR-USD', 'EUR-GBP']});

        await startSync();
        await settled();

        expect(rowOf('EUR-USD')).toHaveTextContent('rates already complete');
        expect(within(rowOf('EUR-USD')).queryByTestId('sync-retry-row')).toBeNull();
        expect(rowOf('EUR-GBP')).toHaveTextContent('provider returned nothing');
        expect(within(rowOf('EUR-GBP')).getByTestId('sync-retry-row')).toBeInTheDocument();
    });

    /**
     * ⚠ Minor inconsistency, pinned rather than fixed — see the report. Both row
     * snippets here use one if/else-if chain, so `partial` matches the first arm
     * (counters) and the error arm is never reached: a partial result shows a retry
     * button and no reason for it. AssetSyncModal, doing the same job on the same
     * data, uses separate blocks and shows both.
     */
    it('says nothing about why a partial result was partial', async () => {
        fxResponds({pair: 'EUR-USD', status: 'partial', points_fetched: 2, points_changed: 2, errors: ['only 2 of 30 days available']});
        mount({assets: [], fxPairs: ['EUR-USD']});

        await startSync();
        await settled();

        expect(rowOf('EUR-USD')).toHaveAttribute('data-status', 'partial');
        expect(rowOf('EUR-USD')).toHaveTextContent('2↓ 2Δ');
        expect(rowOf('EUR-USD')).not.toHaveTextContent('only 2 of 30 days available');
        // The control to fix it is there, unexplained.
        expect(within(rowOf('EUR-USD')).getByTestId('sync-retry-row')).toBeInTheDocument();
    });
});

// =========================================================================
// Wire shape → SyncResult
// =========================================================================

describe('PageSyncModal — the optional halves of the wire shape', () => {
    it('reads a missing counter as zero rather than as nothing', async () => {
        // Neither endpoint sends the optional counters; both must still render a
        // complete row, and the aggregate must stay a number.
        assetsRespond({asset_id: 1, status: 'ok'});
        fxResponds({pair: 'EUR-USD', status: 'ok'});
        mount({assets: [asset(1)], fxPairs: ['EUR-USD']});

        await startSync();
        await settled();

        expect(rowOf('1')).toHaveTextContent('0↓ 0Δ');
        expect(rowOf('EUR-USD')).toHaveTextContent('0↓ 0Δ');
        expect(summary()).toMatchObject({success: 2, total: 2, fetched: 0, changed: 0});
    });

    it('hides the corporate-events group unless something was fetched, and defaults its delta', async () => {
        assetsRespond({asset_id: 1, status: 'ok', points_fetched: 4, points_changed: 1, events_fetched: 0}, {asset_id: 2, status: 'ok', points_fetched: 4, points_changed: 1, events_fetched: 3});
        mount({assets: [asset(1), asset(2)], fxPairs: []});

        await startSync();
        await settled();

        // Asset 1: prices only. Asset 2: an events group whose delta is absent ⇒ 0.
        expect(rowOf('1').querySelectorAll('span.inline-flex')).toHaveLength(1);
        expect(rowOf('2').querySelectorAll('span.inline-flex')).toHaveLength(2);
        expect(rowOf('2')).toHaveTextContent('3↓ 0Δ');
    });

    it('falls back to the message when a failure carries no error list', async () => {
        assetsRespond({asset_id: 1, status: 'failed', message: 'provider disabled for this asset'});
        mount({assets: [asset(1)], fxPairs: []});

        await startSync();
        await settled();

        // `errors ?? []` is what keeps `.length` from throwing on the absent field.
        expect(rowOf('1')).toHaveAttribute('data-status', 'failed');
        expect(rowOf('1')).toHaveTextContent('provider disabled for this asset');
    });

    /**
     * ⚠ Pinned defect — see the report. A 200 whose body has no `results` key is
     * indistinguishable from a sync that did nothing: no row, no summary, no error,
     * and `onsynced` still fires, so the page reloads itself over unchanged data.
     */
    it('reports a body with no results as an uneventful success', async () => {
        syncPrices.mockResolvedValue({} as never);
        const {onsynced} = mount({assets: [asset(1)], fxPairs: []});

        await startSync();
        await settled();

        expect(rowIds()).toEqual([]);
        expect(screen.queryByTestId('sync-modal-results')).toBeNull();
        expect(errorBanner()).toBeNull();
        expect(onsynced).toHaveBeenCalledTimes(1);
    });
});
