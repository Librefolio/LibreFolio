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
// The row copies the full error through this helper; jsdom has neither a
// clipboard nor `execCommand`, and what the row promises is "the whole text
// leaves the row", not how it travels.
vi.mock('$lib/utils/clipboard', () => ({writeExportToClipboard: vi.fn()}));
// The open-effect warms the FX provider cache; not the subject of this file, but
// the cache backs the FX badge, so one provider is given an icon there too.
vi.mock('$lib/stores/currencyGraphStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/currencyGraphStore')>()),
    getCurrencyGraph: vi.fn().mockResolvedValue(undefined),
    getCachedFxProviders: vi.fn(() => [{code: 'ecb', name: 'ECB', icon_url: '/icons/fx/ecb.png'}]),
}));

import PageSyncModal from './PageSyncModal.svelte';
import {zodiosApi} from '$lib/api';
import {writeExportToClipboard} from '$lib/utils/clipboard';

const syncPrices = vi.mocked(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post);
const syncRates = vi.mocked(zodiosApi.sync_rates_api_v1_fx_currencies_sync_post);
const copied = vi.mocked(writeExportToClipboard);

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
    copied.mockClear();
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
});

// =========================================================================
// The row itself, now that the four are one
// =========================================================================

describe('PageSyncModal — the shared result row', () => {
    /**
     * The single fact about the row that belongs to this modal: it draws two
     * sections, and until the four hand-written rows became one they did not
     * behave alike — the FX side offered no way to read an error it had
     * truncated, and no way to copy it. What the row does with a result now has
     * one owner, in SyncResultRow.test.ts; what stays here is that *both*
     * sections get that row and not a variation on it.
     */
    it('gives both sections the same row, error and copy gesture alike', async () => {
        fxResponds({pair: 'EUR-USD', status: 'failed', errors: ['pair first', 'pair second']});
        assetsRespond({asset_id: 1, status: 'partial', points_fetched: 1, points_changed: 1, errors: ['asset first', 'asset second']});
        mount({assets: [asset(1)], fxPairs: ['EUR-USD']});

        await startSync();
        await settled();

        const fxError = within(rowOf('EUR-USD')).getByTestId('sync-row-error');
        const assetError = within(rowOf('1')).getByTestId('sync-row-error');
        expect(fxError).toHaveTextContent('pair first');
        expect(assetError).toHaveTextContent('asset first');

        // Visible: the first line only. Copied: all of them — in both sections,
        // and on a `partial`, which is a status the FX row used to leave mute.
        await fireEvent.dblClick(fxError);
        expect(copied).toHaveBeenLastCalledWith('pair first; pair second', expect.anything(), expect.anything());
        await fireEvent.dblClick(assetError);
        expect(copied).toHaveBeenLastCalledWith('asset first; asset second', expect.anything(), expect.anything());
        expect(copied).toHaveBeenCalledTimes(2);
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

    /**
     * `(r.results ?? [])` keeps the mapper from throwing on a body with no
     * `results`; SyncModalBase then does the rest, turning every id it asked about
     * and got no word on into a failed row. Both endpoints are answered that way
     * here, so both sections have to behave the same.
     */
    it('turns a body with no results into a failed row in each section', async () => {
        syncPrices.mockResolvedValue({} as never);
        syncRates.mockResolvedValue({} as never);
        const {onsynced} = mount({assets: [asset(1), asset(2)], fxPairs: ['EUR-USD']});

        await startSync();
        await settled();

        expect(rowIds(sectionOf('assets')).sort()).toEqual(['1', '2']);
        expect(rowIds(sectionOf('fx'))).toEqual(['EUR-USD']);
        for (const id of ['1', '2', 'EUR-USD']) expect(rowOf(id)).toHaveAttribute('data-status', 'failed');
        // Every section's counters agree with what it was asked to do.
        expect(num(sectionOf('assets'), 'data-result-count')).toBe(num(sectionOf('assets'), 'data-target-count'));
        expect(num(sectionOf('fx'), 'data-result-count')).toBe(num(sectionOf('fx'), 'data-target-count'));
        // Reported per row, not as a global error: both calls did succeed.
        expect(errorBanner()).toBeNull();
        expect(summary()).toMatchObject({success: 0, total: 3, failed: 3});
        // The parent is told the run finished anyway — the user's decision.
        expect(onsynced).toHaveBeenCalledTimes(1);
    });
});
